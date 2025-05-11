import time, os
import re, shutil
from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal, QMutexLocker
from ..bk_asr.ASRData import split_line


from ..bk_asr import (
    JianYingASR,
    KuaiShouASR, 
    BcutASR,
    WhisperASR,
    WhisperAPI,
    FasterWhisperASR
)
from ..bk_asr.ASRData import ASRData, from_subtitle_file
from ..subtitle_processor.spliter import merge_segments
from ..entities import Task, TranscribeModelEnum, SubtitleLayoutEnum, WHISPER_LANGUAGES
from ..utils.video_utils import video2audio
from ..utils.logger import setup_logger
from ..utils.test_opanai import test_openai
from ...config import MODEL_PATH
from ...common.config import cfg, mutAudioRecording, mutTranscribing
from ...core.thread.subtitle_optimization_thread import FREE_API_CONFIGS

logger = setup_logger("transcript_thread")

class TranscriptThread(QThread):
    finished = pyqtSignal(Task)
    progress = pyqtSignal(int, str)
    error = pyqtSignal(str)
    
    ASR_MODELS = {
        TranscribeModelEnum.JIANYING: JianYingASR,
        # TranscribeModelEnum.KUAISHOU: KuaiShouASR,
        TranscribeModelEnum.BIJIAN: BcutASR,
        TranscribeModelEnum.WHISPER: WhisperASR,
        TranscribeModelEnum.WHISPER_API: WhisperAPI,
        TranscribeModelEnum.FASTER_WHISPER: FasterWhisperASR,
    }

    def __init__(self, task: Task):
        super().__init__()
        self.task = task

    def run(self):
        try:
            logger.info(f"\n===========转录任务开始===========")
            logger.info(f"时间：{time.strftime("%d %b %Y %H:%M:%S")}")
            # 检查是否已经存在字幕文件
            # 不能跳过，因为如果有两个同名的视频文件，就需要生成和覆盖旧的字幕
            """
            if Path(self.task.original_subtitle_save_path).exists():
                logger.info("字幕文件已存在，跳过转录")
                self.progress.emit(100, self.tr("字幕已存在"))
                self.finished.emit(self.task)
                return
            """

            video_path = Path(self.task.file_path)
            if not video_path:
                logger.error("视频路径不能为空")
                raise ValueError(self.tr("视频路径不能为空"))

            # Create the work dir just in case.
            Path(self.task.work_dir).mkdir(parents=True, exist_ok=True)
            
            if self.task.type == Task.Type.URL and self.task.url_subtitle_file \
                and Path(self.task.url_subtitle_file).exists():
                # Have subtitle already downloaded from Internet.
                logger.info(f"已下载字幕文件，直接调用：{self.task.url_subtitle_file}")

                asr_data = from_subtitle_file(self.task.url_subtitle_file)
            else:
                # 没有直接字幕可用，用音频转换功能生成 asr_data
                # 如果音频在制作中，等待
                if mutAudioRecording.tryLock(1):
                    mutAudioRecording.unlock()
                else:
                    # Some task is doing audio recoding.
                    self.progress.emit(0, self.tr("等待其他音频处理结束"))
                    self.task.status = Task.Status.WAITINGAUDIO
                        
                with QMutexLocker(mutAudioRecording):
                    if not self.task.allow_running[0]:
                        logger.error("音频转换前中断")
                        raise RuntimeError(self.tr("音频转换前中断"))
                    # 转换为音频
                    self.progress.emit(5, self.tr("转换音频中"))
                    logger.info("开始转换音频")
                    self.task.status = Task.Status.TRANSCODING

                    audio_save_path = Path(self.task.audio_save_path)
                    if audio_save_path.exists():
                        # There is already a wave file with same name.
                        os.remove(audio_save_path)
                
                    is_success = video2audio(str(video_path),
                                            output_file=str(audio_save_path),
                                            format= self.task.audio_format,
                                            allow_running=self.task.allow_running,
                                            audio_track = self.task.audio_track,
                                            )

                if not is_success:
                    logger.error("音频转换失败")
                    raise RuntimeError(self.tr("音频转换失败"))

                # 如果音频在转录中，等待
                if mutTranscribing.tryLock(1):
                    mutTranscribing.unlock()
                else:
                    # Some task is doing transcribing.
                    self.progress.emit(0, self.tr("等待其他转录结束"))
                    self.task.status = Task.Status.WAITINGTRANSCRIBE

                with QMutexLocker(mutTranscribing):
                    if not self.task.allow_running[0]:
                        logger.error("语音转录前中断")
                        raise RuntimeError(self.tr("转录前中断"))

                    self.task.status = Task.Status.TRANSCRIBING
                    self.progress.emit(20, self.tr("语音转录中"))
                    logger.info("开始语音转录")

                    # 获取ASR模型
                    asr_class = self.ASR_MODELS.get(self.task.transcribe_model) # Use the Enum instead of Enum.value
                    if not asr_class:
                        logger.error("无效的转录模型: %s", str(self.task.transcribe_model.value))
                        raise ValueError(self.tr("无效的转录模型: ") + str(self.task.transcribe_model.value))  # 检查转录模型是否有效

                    # 执行转录
                    args = {
                        "use_cache": self.task.use_asr_cache,
                        "need_word_time_stamp": self.task.need_word_time_stamp,
                        "allow_running": self.task.allow_running,
                    }
                    
                    match self.task.transcribe_model:
                        case TranscribeModelEnum.WHISPER:
                            args["language"] = self.task.transcribe_language
                            args["whisper_model"] = self.task.whisper_model
                            args["use_cache"] = False
                            args["need_word_time_stamp"] = True
                            self.asr = WhisperASR(self.task.audio_save_path, **args)
                        case TranscribeModelEnum.WHISPER_API:
                            args["language"] = self.task.transcribe_language
                            args["whisper_model"] = self.task.whisper_api_model
                            args["api_key"] = self.task.whisper_api_key
                            args["base_url"] = self.task.whisper_api_base
                            args["prompt"] = self.task.whisper_api_prompt
                            args["use_cache"] = False
                            args["need_word_time_stamp"] = True
                            self.asr = WhisperAPI(self.task.audio_save_path, **args)
                        case TranscribeModelEnum.FASTER_WHISPER:
                            args["faster_whisper_path"] = cfg.faster_whisper_program.value
                            args["whisper_model"] = self.task.faster_whisper_model.value
                            args["model_dir"] = str(MODEL_PATH)
                            args["language"] = self.task.transcribe_language
                            args["device"] = self.task.faster_whisper_device
                            args["vad_filter"] = self.task.faster_whisper_vad_filter
                            args["vad_threshold"] = self.task.faster_whisper_vad_threshold
                            args["vad_method"] = self.task.faster_whisper_vad_method.value
                            args["ff_mdx_kim2"] = self.task.faster_whisper_ff_mdx_kim2
                            args["one_word"] = self.task.faster_whisper_one_word
                            args["prompt"] = self.task.faster_whisper_prompt
                            args["use_cache"] = False

                            if self.task.faster_whisper_one_word:
                                args["one_word"] = True
                            else:
                                args["sentence"] = True
                                # No more max line width limit. The line will be devided later.
                                # if self.task.transcribe_language in ["zh", "ja", "ko"] and not self.isFasterWhisperTranslate():
                                #     args["max_line_width"] = int(self.task.max_word_count_cjk)
                                #     args["max_comma_cent"] = 50
                                #     args["max_comma"] = 5
                                # else:
                                #     args["max_line_width"] = int(self.task.max_word_count_english*8)
                                #     args["max_comma_cent"] = 50
                                #     args["max_comma"] = 20
                        
                            args["translate_to_english"] = self.task.faster_whisper_translate_to_english
                            args["repetition_penalty"] = self.task.faster_whisper_repetion_penalty
                            
                            if cfg.faster_whisper_multilingal.value:
                                args["multilingual"] = True

                            if cfg.faster_whisper_RTX_5000_fix.value:
                                args["rtx5000fix"] = True

                            self.asr = FasterWhisperASR(self.task.audio_save_path, **args )
                        case TranscribeModelEnum.BIJIAN:
                            self.asr = BcutASR(self.task.audio_save_path, **args)
                        case TranscribeModelEnum.JIANYING:
                            self.asr = JianYingASR(self.task.audio_save_path, **args)
                        case _:
                            raise ValueError(self.tr("无效的转录模型: ") + str(self.task.transcribe_model.value))
                    
                    asr_data = self.asr.run(callback=self.progress_callback)
                    # 音频转换成 asr_data 结束

            if not self.task.allow_running[0]:
                logger.error("字幕断句前中断")
                raise RuntimeError(self.tr("字幕断句前中断"))
                
            if asr_data.is_word_timestamp():
                # The data is in words, use LLM to merge them.
                asr_data = self.merge_words(asr_data)
                if not self.task.allow_running[0]:
                    raise RuntimeError(self.tr("智能断句被中断"))
                if not asr_data:
                    # word merging failed
                    raise ValueError(self.tr("智能断句失败，请检查你的大模型Base URL和API Key是否有效。"))

            # Check if asr_data needs to add minimum length
            if cfg.subtitle_enable_sentence_minimum_time.value:
                asr_data.add_minimum_len(cfg.subtitle_sentence_minimum_time.value)
            
            # If time offset is not zero, adjust the timestamps
            if cfg.time_offset.value != 0:
                for seg in asr_data.segments:
                    seg.start_time += cfg.time_offset.value
                    seg.end_time += cfg.time_offset.value
            
            # Remove punctuation if needed.
            if cfg.needs_remove_punctuation.value:
                re_punctuation = re.compile( r'[,.!?;:，。！？；：、]+$')
                for seg in asr_data.segments:
                    seg.text = re.sub(re_punctuation, "", seg.text)
                        
            # Split lines according to settings
            for seg in asr_data.segments:
                seg.text = split_line(seg.text, cfg.max_char_count_english.value, cfg.max_char_count_cjk.value)
            
            # 保存字幕文件
            if not self.task.allow_running[0]:
                logger.error("字幕保存前中断")
                return
            # original_subtitle_path = Path(self.task.original_subtitle_save_path)
            # original_subtitle_path.parent.mkdir(parents=True, exist_ok=True)
            asr_data.to_srt(save_path=self.task.original_subtitle_save_path)
            logger.info("源字幕文件已保存到: %s", self.task.original_subtitle_save_path)
            
            if self.task.result_subtitle_save_path:
                if self.task.type == Task.Type.TRANSCRIBE \
                    or ( self.task.type == Task.Type.SUBTITLE and not self.task.need_translate) :
                    # Make a copy to result dir as well, if this is only a transcribe task, or a video syntheis without translation task.
                    asr_data.save(
                        save_path=self.task.result_subtitle_save_path,
                        ass_style=self.task.subtitle_style_srt,
                        layout=SubtitleLayoutEnum.ONLY_ORIGINAL,
                    )
                    logger.info("目的字幕文件已保存到: %s", self.task.result_subtitle_save_path)
                        
            # 删除音频文件 和 封面
            try:
                audio_save_path.unlink()
                thumbnail_path = Path(self.task.video_info.thumbnail_path)
                if thumbnail_path.exists():
                    thumbnail_path.unlink()
            except Exception as e:
                logger.error("删除音频文件或封面失败: %s", str(e))

            self.progress.emit(100, self.tr("转录完成"))
            self.finished.emit(self.task)

        except Exception as e:
            logger.exception("转录过程中发生错误: %s", str(e))
            self.task.status = Task.Status.FAILED
            self.error.emit(str(e))
            self.progress.emit(100, self.tr("转录失败"))

    def progress_callback(self, value, message):
        progress = min(20 + (value * 0.8), 100)
        self.progress.emit(int(progress), message)

    def _setup_api_config(self):
        """设置API配置，返回base_url, api_key, llm_model, thread_num, batch_size"""
        logger.info(f"base: {self.task.base_url} key:{self.task.api_key} model:{self.task.llm_model}")
        if not test_openai(self.task.base_url, self.task.api_key, self.task.llm_model)[0]:
            raise Exception(self.tr("OpenAI API 测试失败, 请检查设置"))
        return (self.task.base_url, self.task.api_key, self.task.llm_model, 
                self.task.thread_num, self.task.batch_size)

    def merge_words(self, asr_data: ASRData) -> ASRData:
        logger.info(f"\n===========字幕断句任务开始===========")
            
        # 获取API配置
        try:
            self.progress.emit(80, self.tr("开始验证API配置..."))
            base_url, api_key, llm_model, thread_num, batch_size = self._setup_api_config()
            logger.info(f"使用 {llm_model} 作为LLM模型")
            os.environ['OPENAI_BASE_URL'] = base_url
            os.environ['OPENAI_API_KEY'] = api_key
            
            self.progress.emit(85, self.tr("字幕断句..."))
            logger.info("正在字幕断句...")
            # 用大模型进行字幕断句和合并。
            asr_data = merge_segments(asr_data, model=llm_model,
                                      merge_by_rules=False, 
                                      allow_running=self.task.allow_running)
            return asr_data     
        except Exception as e:
            logger.exception(f"断句失败: {str(e)}")
            self.error.emit(str(e))
            self.progress.emit(100, self.tr("断句失败"))
  
    # Is the current config is using FasterWhipser and translate to English?
    def isFasterWhisperTranslate(self):
        return cfg.transcribe_model.value == TranscribeModelEnum.FASTER_WHISPER and cfg.faster_whisper_translate_to_english.value

