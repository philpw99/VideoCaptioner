import datetime
from PyQt5.QtCore import QThread, pyqtSignal

from .subtitle_optimization_thread import SubtitleOptimizationThread
from .transcript_thread import TranscriptThread
from .video_synthesis_thread import VideoSynthesisThread
from ...core.entities import Task
from ..utils.logger import setup_logger
from ..utils.temp_folder import TempFolder

logger = setup_logger("subtitle_pipeline_thread")

class SubtitlePipelineThread(QThread):
    """字幕处理全流程线程，包含:
    1. 转录生成字幕
    2. 字幕优化/翻译
    3. 视频合成
    """
    progress = pyqtSignal(int, str)  # 进度值, 进度描述
    finished = pyqtSignal(Task)
    error = pyqtSignal(str)

    def __init__(self, task: Task):
        super().__init__()
        self.task = task
        self.has_error = False

    def run(self):
        # Reset the task's "allow running" attribute
        self.task.allow_running[0] = True
        old_file = None
        try:
            def handle_error(error_msg):
                logger.error("pipeline 发生错误: %s", error_msg)
                self.has_error = True
                self.error.emit(error_msg)

            # 文件名是否过长
            shorten = False
            if len(self.task.file_path) > 200 and self.task.file_path[1] == ":":
                # 1. over 200 char long. 2. Need to be local, not network files
                old_file = self.task.file_path
                temp_path = TempFolder()
                shorten, new_file = temp_path.create_temp_folder(self.task.file_path)
                if shorten:
                    self.task.file_path = new_file

            # 1. 转录生成字幕
            # self.task.status = Task.Status.TRANSCRIBING
            logger.info(f"\n===========任务开始===========")
            logger.info(f"时间：{datetime.datetime.now()}")
            logger.info("开始转录")
            self.progress.emit(0, self.tr("开始转录"))
            transcript_thread = TranscriptThread(self.task)
            transcript_thread.progress.connect(lambda value, msg: self.progress.emit(int(value * 0.4), msg))
            transcript_thread.error.connect(handle_error)
            transcript_thread.run()

            if self.has_error:
                logger.info("转录过程中发生错误，终止流程")
                if old_file:
                    self.task.file_path = old_file
                return

            # 2. 字幕优化/翻译
            # self.task.status = Task.Status.TRANSLATING
            if self.task.need_translate:
                self.progress.emit(40, self.tr("开始优化+翻译字幕"))
                optimization_thread = SubtitleOptimizationThread(self.task)
                optimization_thread.progress.connect(lambda value, msg: self.progress.emit(int(40 + value * 0.2), msg))
                optimization_thread.error.connect(handle_error)
                optimization_thread.run()

                if self.has_error:
                    if old_file:
                        self.task.file_path = old_file
                    logger.info("字幕优化/翻译过程中发生错误，终止流程")
                    return
            
            # 3. 视频合成
            # self.task.status = Task.Status.GENERATING
            if self.task.need_video:
                self.progress.emit(80, self.tr("开始合成视频"))
                synthesis_thread = VideoSynthesisThread(self.task)
                synthesis_thread.progress.connect(lambda value, msg: self.progress.emit(int(70 + value * 0.3), msg))
                synthesis_thread.error.connect(handle_error)
                synthesis_thread.run()

                if self.has_error:
                    if old_file:
                        self.task.file_path = old_file
                    logger.info("视频合成过程中发生错误，终止流程")
                    return

            self.task.status = Task.Status.COMPLETED
            logger.info("处理完成")
            self.progress.emit(100, self.tr("处理完成"))
            self.finished.emit(self.task)
            if old_file:
                self.task.file_path = old_file
                temp_path.remove_temp_folder()

        except Exception as e:
            if old_file:
                self.task.file_path = old_file
                temp_path.remove_temp_folder()
            self.task.status = Task.Status.FAILED
            logger.exception("处理失败: %s", str(e))
            self.error.emit(str(e))
