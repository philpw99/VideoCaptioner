import datetime
import os
from pathlib import Path
import asyncio
from typing import Dict

from PyQt5.QtCore import QThread, pyqtSignal, QSettings

from ..subtitle_processor.optimizer import SubtitleOptimizer
from ..subtitle_processor.summarizer import SubtitleSummarizer
from ..subtitle_processor.gtranslator import googleTranslate
from ..bk_asr.ASRData import from_subtitle_file
from ..entities import Task, TranslateMethodEnum
from ..subtitle_processor.spliter import merge_segments
from ..utils.test_opanai import test_openai
from ..utils.logger import setup_logger
from ...common.config import cfg, mutTranslating

# 配置日志
logger = setup_logger("subtitle_optimization_thread")

FREE_API_CONFIGS = {
    "ddg": {
        "base_url": "http://ddg.bkfeng.top/v1",
        "api_key": "Hey-man-This-free-server-is-convenient-for-beginners-Please-do-not-use-for-personal-use-Server-just-has-limited-concurrency",
        "llm_model": "gpt-4o-mini",
        "thread_num": 5,
        "batch_size": 10
    },
    "zhipu": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "api_key": "c96c2f6ce767136cdddc3fef1692c1de.H27sLU4GwuUVqPn5",
        "llm_model": "glm-4-flash",
        "thread_num": 10,
        "batch_size": 10
    }
}

class SubtitleOptimizationThread(QThread):
    finished = pyqtSignal(Task)
    progress = pyqtSignal(int, str)
    update = pyqtSignal(dict)
    update_all = pyqtSignal(dict)
    error = pyqtSignal(str)
    MAX_DAILY_LLM_CALLS = 50

    def __init__(self, task: Task):
        super().__init__()
        self.task: Task = task
        self.subtitle_length = 0
        self.finished_subtitle_length = 0
        self.custom_prompt_text = ""
        self.llm_result_logger = None

    def set_custom_prompt_text(self, text: str):
        self.custom_prompt_text = text

    def _setup_api_config(self):
        """设置API配置，返回base_url, api_key, llm_model, thread_num, batch_size"""
        if not test_openai(self.task.base_url, self.task.api_key, self.task.llm_model)[0]:
            raise Exception(self.tr("OpenAI API 测试失败, 请检查设置"))
        return (self.task.base_url, self.task.api_key, self.task.llm_model, 
                self.task.thread_num, self.task.batch_size)
        

    def run(self):
        try:
            logger.info(f"\n===========字幕优化/翻译任务开始===========")
            logger.info(f"时间：{datetime.datetime.now()}")
            
            # 获取API配置
            if self.task.translate_method != TranslateMethodEnum.GOOGLE:
                print("translate method:" + str(self.task.translate_method.value))
                self.progress.emit(2, self.tr("开始验证API配置..."))
                base_url, api_key, llm_model, thread_num, batch_size = self._setup_api_config()
                logger.info(f"使用 {llm_model} 作为LLM模型")
                os.environ['OPENAI_BASE_URL'] = base_url
                os.environ['OPENAI_API_KEY'] = api_key

            str_path = self.task.original_subtitle_save_path
            result_subtitle_save_path = self.task.result_subtitle_save_path
            target_language = self.task.target_language
            need_summarize = True if cfg.translate_method.value == TranslateMethodEnum.OPTIMIZE else False
            subtitle_style_srt = self.task.subtitle_style_srt
            subtitle_layout = self.task.subtitle_layout
            need_split=self.task.need_split
            need_remove_punctuation = cfg.needs_remove_punctuation.value

            # 检查
            assert str_path is not None, self.tr("字幕文件路径为空")
            assert Path(str_path).exists(), self.tr("字幕文件路径不存在")
            assert Path(str_path).suffix in ['.srt', '.vtt', '.ass'], self.tr("字幕文件格式不支持")

            # 锁定翻译独占权
            if not mutTranslating.tryLock(1):
                self.task.status = Task.Status.WAITINGTRANSLATE
                self.progress.emit(5, self.tr("等待优化/翻译字幕"))
                logger.info("有别的任务在进行优化/翻译字幕，等待其完成")
                mutTranslating.lock()  # Wait forever
            
            if self.task.translate_method == TranslateMethodEnum.OPTIMIZE:
                self.task.status = Task.Status.OPTIMIZING
                self.progress.emit(10, self.tr("开始优化字幕..."))

                self.llm_result_logger = setup_logger("llm_result", 
                                                    info_fmt="%(message)s",
                                                    log_file=str(Path(str_path).parent / '优化日志.log'),
                                                    console_output=False)

            asr_data = from_subtitle_file(str_path)

            """
            # 检查是否需要合并重新断句
            # Right now this will be done right after transcribing.
            if asr_data.is_word_timestamp():
                self.progress.emit(15, self.tr("字幕断句..."))
                logger.info("正在字幕断句...")
                asr_data = merge_segments(asr_data, model=llm_model, 
                                        num_threads=thread_num, 
                                        max_word_count_cjk=max_word_count_cjk, 
                                        max_word_count_english=max_word_count_english)
                asr_data.save(save_path=split_path)
                self.update_all.emit(asr_data.to_json())
            """

            # 制作成请求llm接口的格式 {{"1": "original_subtitle"},...}
            subtitle_json = {str(k): v["original_subtitle"] for k, v in asr_data.to_json().items()}
            self.subtitle_length = len(subtitle_json)
            
            match self.task.translate_method:
                case TranslateMethodEnum.OPTIMIZE:
                    summarize_result = self.custom_prompt_text.strip()
                    self.progress.emit(20, self.tr("总结字幕..."))
                    if need_summarize and not summarize_result:
                        summarizer = SubtitleSummarizer(model=llm_model)
                        summarize_result = summarizer.summarize(asr_data.to_txt())
                    logger.info(f"总结字幕内容:{summarize_result}")
                    

                    self.progress.emit(30, self.tr("优化+翻译..."))
                    logger.info("正在优化+翻译...")
                    need_reflect = False if "glm-4-flash" in llm_model.lower() else True
                    self.optimizer = SubtitleOptimizer(
                        summary_content=summarize_result,
                        model=llm_model,
                        target_language=target_language,
                        batch_num=batch_size,
                        thread_num=thread_num,
                        llm_result_logger=self.llm_result_logger,
                        need_remove_punctuation=need_remove_punctuation,
                        cjk_only=True
                    )
                    translate_result = self.optimizer.optimizer_multi_thread(subtitle_json, translate=True,
                                                                                reflect=need_reflect,
                                                                                callback=self.callback)

                case TranslateMethodEnum.SINGLE_SENTENCE:
                    self.progress.emit(30, self.tr("批量翻译单句字幕..."))
                    logger.info("正在批量翻译单句字幕...")
                    self.optimizer = SubtitleOptimizer(
                        model=llm_model,
                        batch_num=batch_size,
                        # thread_num=thread_num,
                        thread_num=1,
                        llm_result_logger=self.llm_result_logger
                    )
                    translate_result = self.optimizer.translate_single_batch(subtitle_json, callback=self.callback)
                case TranslateMethodEnum.GOOGLE:
                    self.progress.emit(30, self.tr("批量谷歌翻译字幕..."))
                    logger.info("正在批量谷歌翻译字幕...")

                    
                    translate_result = asyncio.run(googleTranslate(subtitle_json, callback=self.callback))
                    
            # 加入优化或者翻译后的字幕
            for i, subtitle_text in translate_result.items():
                seg = asr_data.segments[int(i) - 1]
                seg.text = seg.text + "\n" + subtitle_text

            # 保存字幕
            if result_subtitle_save_path.endswith(".ass"):
                asr_data.to_ass(style_str=subtitle_style_srt, layout=subtitle_layout, save_path=result_subtitle_save_path)
            else:
                asr_data.save(save_path=result_subtitle_save_path, ass_style=subtitle_style_srt,
                                layout=subtitle_layout)
            logger.info(f"字幕优化/翻译完成，保存到 {result_subtitle_save_path}")

            # 保存srt文件
            if self.task.video_info and self.task.need_video:
                save_srt_path = Path(self.task.work_dir) / f"VideoSub_{Path(self.task.video_info.file_name).stem}.srt"
                asr_data.to_srt(save_path=str(save_srt_path), layout=subtitle_layout)

            # stop the llm logging in working dir
            if self.llm_result_logger:
                for handler in self.llm_result_logger.handlers:
                    if handler.close:   # Has close method
                        handler.close()
                    self.llm_result_logger.removeHandler(handler)
                
            self.progress.emit(100, self.tr("优化/翻译完成"))
            logger.info("优化/翻译完成")
            self.finished.emit(self.task)
            mutTranslating.unlock()
        except Exception as e:
            logger.exception(f"优化失败: {str(e)}")
            self.error.emit(str(e))
            self.progress.emit(100, self.tr("优化失败"))
            if self.llm_result_logger:
                for handler in self.llm_result_logger.handlers:
                    if handler.close: # Has close method
                        handler.close()
                    self.llm_result_logger.removeHandler(handler)
            mutTranslating.unlock()

    def callback(self, result: Dict):
        self.finished_subtitle_length += len(result)
        progress_num = int((self.finished_subtitle_length / self.subtitle_length) * 70) + 30
        self.progress.emit(progress_num, self.tr("{0}% 处理字幕").format(progress_num))
        self.update.emit(result)

    def stop(self):
        mutTranslating.unlock()
        if hasattr(self, 'optimizer'):
            self.optimizer.stop()
        self.terminate()