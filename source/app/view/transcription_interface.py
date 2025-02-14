# -*- coding: utf-8 -*-

import datetime
import os
import sys
import subprocess
from pathlib import Path

from PyQt5.QtCore import *
from PyQt5.QtGui import QPixmap, QFont, QDragEnterEvent, QDropEvent, QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QApplication, QLabel, QPlainTextEdit
from qfluentwidgets import CardWidget, PrimaryPushButton, PushButton, InfoBar, BodyLabel, PillPushButton, setFont, \
        ProgressRing, InfoBarPosition
from qfluentwidgets.common.config import isDarkTheme

from ..components.FasterWhisperSettingDialog import FasterWhisperSettingDialog
from ..components.WhisperSettingDialog import WhisperSettingDialog
from ..components.WhisperAPISettingDialog import WhisperAPISettingDialog
from ..config import RESOURCE_PATH
from ..core.thread.create_task_thread import CreateTaskThread
from ..common.config import cfg
from ..core.entities import LANGUAGES, Task, VideoInfo, WHISPER_LANGUAGES, NOT_RUNNING_TASKS
from ..core.entities import SupportedVideoFormats, SupportedAudioFormats
from ..core.thread.transcript_thread import TranscriptThread
from ..core.entities import TranscribeModelEnum
from ..common.signal_bus import signalBus

DEFAULT_THUMBNAIL_PATH = RESOURCE_PATH / "assets" / "default_thumbnail.jpg"

class ProcessLogInfoCard(CardWidget):
    console_line = pyqtSignal(Task)
    task: Task|None = None
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_signals()
    
    def setup_ui(self):
        self.cardLayout = QVBoxLayout(self)
        self.cardLayout.setContentsMargins(20,15,20,15)
        self.setup_log_toolbar_layout()
        # Log area
        self.process_log = QPlainTextEdit(self)
        self.process_log.setReadOnly(True)
        self.process_log.setMinimumWidth(200)
        text_color = "#cccccc" if isDarkTheme() else "#000000"
        self.process_log.setStyleSheet(f"QPlainTextEdit{{background:transparent; font-size:12px; color:{text_color}}}")
        self.cardLayout.addWidget(self.process_log)

    def setup_log_toolbar_layout(self):
        # Layout for log
        self.log_toolbar_layout = QHBoxLayout()
        self.log_label = BodyLabel(self)
        self.log_clear_button = PushButton(self.tr("Clear"),self)

        self.log_toolbar_layout.addWidget(self.log_label)
        self.log_toolbar_layout.addStretch(1)
        self.log_toolbar_layout.addWidget(self.log_clear_button)
        self.log_label.setText(self.tr("程序日志:"))

        self.cardLayout.addLayout(self.log_toolbar_layout)


    
    def addLine(self, text: str):
        # After adding a message
        self.process_log.appendPlainText(text)
        self.process_log.verticalScrollBar().setValue(self.process_log.verticalScrollBar().maximum())

    def clearLog(self):
        self.process_log.clear()

    def setup_signals(self):
        self.log_clear_button.clicked.connect(self.clearLog)
        # Let other thread send lines to the log
        signalBus.app_log_signal.connect(self.addLine)

class VideoInfoCard(CardWidget):
    finished = pyqtSignal(Task)
    task: Task|None = None
    transcript_thread = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.task = None
        self.setup_ui()
        self.setup_signals()

    def setup_ui(self):
        self.setFixedHeight(150)
        self.cardlayout = QHBoxLayout(self)
        self.cardlayout.setContentsMargins(20, 15, 20, 15)
        self.cardlayout.setSpacing(20)

        self.setup_thumbnail()
        self.setup_info_layout()
        self.setup_button_layout()

    def setup_thumbnail(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        default_thumbnail_path = os.path.join(DEFAULT_THUMBNAIL_PATH)

        self.video_thumbnail = QLabel(self)
        self.video_thumbnail.setFixedSize(208, 117)
        self.video_thumbnail.setStyleSheet("background-color: #1E1F22;")
        self.video_thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        pixmap = QPixmap(default_thumbnail_path).scaled(
            self.video_thumbnail.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.video_thumbnail.setPixmap(pixmap)
        self.cardlayout.addWidget(self.video_thumbnail, 0, Qt.AlignmentFlag.AlignLeft)

    def setup_info_layout(self):
        self.info_layout = QVBoxLayout()
        self.info_layout.setContentsMargins(3, 8, 3, 8)
        self.info_layout.setSpacing(10)

        self.video_title = BodyLabel(self.tr("请拖入音频或视频文件"), self)
        self.video_title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        self.video_title.setWordWrap(True)
        self.info_layout.addWidget(self.video_title, alignment=Qt.AlignmentFlag.AlignTop)

        self.details_layout = QHBoxLayout()
        self.details_layout.setSpacing(15)

        self.resolution_info = self.create_pill_button(self.tr("画质"), 130)
        self.file_size_info = self.create_pill_button(self.tr("文件大小"), 130)
        self.duration_info = self.create_pill_button(self.tr("时长"), 130)

        self.progress_ring = ProgressRing(self)
        self.progress_ring.setFixedSize(20, 20)
        self.progress_ring.setStrokeWidth(4)
        self.progress_ring.hide()

        self.details_layout.addWidget(self.resolution_info)
        self.details_layout.addWidget(self.file_size_info)
        self.details_layout.addWidget(self.duration_info)
        self.details_layout.addWidget(self.progress_ring)
        self.details_layout.addStretch(1)
        self.info_layout.addLayout(self.details_layout)
        self.cardlayout.addLayout(self.info_layout)

    def create_pill_button(self, text, width):
        button = PillPushButton(text, self)
        button.setCheckable(False)
        setFont(button, 11)
        button.setFixedWidth(width)
        return button

    def setup_button_layout(self):
        self.button_layout = QVBoxLayout()
        self.open_folder_button = PushButton(self.tr("打开文件夹"), self)
        self.start_button = PrimaryPushButton(self.tr("开始转录"), self)
        self.cancel_button = PushButton(self.tr("取消"), self)
        self.button_layout.addWidget(self.open_folder_button)
        self.button_layout.addWidget(self.start_button)
        self.button_layout.addWidget(self.cancel_button)

        self.start_button.setDisabled(True)
        self.cancel_button.setDisabled(True)

        button_widget = QWidget()
        button_widget.setLayout(self.button_layout)
        button_widget.setFixedWidth(130)
        self.cardlayout.addWidget(button_widget)

    def update_info(self, video_info: VideoInfo):
        """更新视频信息显示"""
        self.video_title.setText(video_info.file_name.rsplit('.', 1)[0])
        self.resolution_info.setText(self.tr("画质: ") + f"{video_info.width}x{video_info.height}")
        file_size_mb = os.path.getsize(self.task.file_path) / 1024 / 1024
        self.file_size_info.setText(self.tr("大小: ") + f"{file_size_mb:.1f} MB")
        duration = datetime.timedelta(seconds=int(video_info.duration_seconds))
        self.duration_info.setText(self.tr("时长: ") + f"{duration}")
        self.start_button.setDisabled(False)
        self.update_thumbnail(video_info.thumbnail_path)

    def update_thumbnail(self, thumbnail_path):
        """更新视频缩略图"""
        if not cfg.no_thumbnail.value:
            # It's ok to set the thumbnail.
            if not Path(thumbnail_path).exists():
                thumbnail_path = RESOURCE_PATH / "assets" / "audio-thumbnail.png"

            pixmap = QPixmap(str(thumbnail_path)).scaled(
                self.video_thumbnail.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.video_thumbnail.setPixmap(pixmap)

    def setup_signals(self):
        self.start_button.clicked.connect(self.on_start_button_clicked)
        self.open_folder_button.clicked.connect(self.on_open_folder_clicked)
        self.cancel_button.clicked.connect(self.on_cancel_clicked)

    def show_whisper_settings(self):
        """显示Whisper设置对话框"""
        match cfg.transcribe_model.value.value:
            case TranscribeModelEnum.WHISPER.value:
                dialog = WhisperSettingDialog(self.window())
                if dialog.exec_():
                    return True
            case TranscribeModelEnum.WHISPER_API.value:
                dialog = WhisperAPISettingDialog(self.window())
                if dialog.exec_():
                    return True
            case TranscribeModelEnum.FASTER_WHISPER.value:
                dialog = FasterWhisperSettingDialog(self.window())
                if dialog.exec_():
                    return True
            case _:
                return False

    def on_start_button_clicked(self):
        """开始转录按钮点击事件"""
        if self.task.status == Task.Status.TRANSCRIBING:
            need_whisper_settings = cfg.transcribe_model.value.value in [
                TranscribeModelEnum.WHISPER.value,
                TranscribeModelEnum.WHISPER_API.value,
                TranscribeModelEnum.FASTER_WHISPER.value
            ]
            if need_whisper_settings and not self.show_whisper_settings():
                return
        self.progress_ring.show()
        self.progress_ring.setValue(100)
        self.start_transcription()

    def on_cancel_clicked(self):
        self.transcript_thread.allow_running[0] = False
        self.cancel_button.setDisabled(True)
        self.start_button.setEnabled(True)

    def on_open_folder_clicked(self):
        """打开文件夹按钮点击事件"""
        if self.task and self.task.work_dir:
            original_subtitle_save_path = Path(self.task.original_subtitle_save_path)
            target_path = str(original_subtitle_save_path.parent if original_subtitle_save_path.exists() else Path(self.task.work_dir))
            if sys.platform == "win32":
                os.startfile(target_path)
            elif sys.platform == "darwin":  # macOS
                subprocess.run(["open", target_path])
            else:  # Linux
                subprocess.run(["xdg-open", target_path])
        else:
            InfoBar.warning(
                self.tr("警告"),
                self.tr("没有可用的字幕文件夹"),
                duration=2000,
                parent=self
            )

    def start_transcription(self):
        """开始转录过程"""
        self.start_button.setDisabled(True)
        self.cancel_button.setEnabled(True)
        if not self.transcript_thread:
            # Never run before
            self.transcript_thread = TranscriptThread(self.task)
        else:
            # Canceled before. Allow it run again.
            self.transcript_thread.allow_running[0] = True
        self.transcript_thread.finished.connect(self.on_transcript_finished)
        self.transcript_thread.progress.connect(self.on_transcript_progress)
        self.transcript_thread.error.connect(self.on_transcript_error)
        self.transcript_thread.start()

    def on_transcript_progress(self, value, message):
        """更新转录进度"""
        self.start_button.setText(message)
        self.progress_ring.setValue(value)


    def on_transcript_error(self, error):
        """处理转录错误"""
        self.start_button.setEnabled(True)
        self.start_button.setText(self.tr("重新转录"))
        self.start_button.setEnabled(True)
        InfoBar.error(
            self.tr("转录失败"),
            self.tr(error),
            duration=3000,
            parent=self.parent().parent()
        )

    def on_transcript_finished(self, task):
        """转录完成处理"""
        self.start_button.setEnabled(True)
        self.start_button.setText(self.tr("转录完成"))
        if self.task.status not in NOT_RUNNING_TASKS:
            self.finished.emit(task)

    def reset_ui(self):
        """重置UI状态"""
        self.start_button.setDisabled(False)
        self.start_button.setText(self.tr("开始转录"))
        self.progress_ring.setValue(100)

    def set_task(self, task):
        """设置任务并更新UI"""
        self.task = task
        self.update_info(self.task.video_info)
        self.reset_ui()
    
    def stop(self):
        if hasattr(self, 'transcript_thread'):
            if self.transcript_thread:
                self.transcript_thread.quit()
            #self.transcript_thread.terminate()


class TranscriptionInterface(QWidget):
    """转录界面类,用于显示视频信息和转录进度"""
    finished = pyqtSignal(Task)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAcceptDrops(True)
        self.task = None

        self._init_ui()
        self._setup_signals()

    def _init_ui(self):
        """初始化UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setObjectName("main_layout")
        self.main_layout.setSpacing(20)
        self.process_log_card = ProcessLogInfoCard(self)
        self.video_info_card = VideoInfoCard(self)

        self.main_layout.addWidget(self.video_info_card)
        self.main_layout.addWidget(self.process_log_card)

    def _setup_signals(self):
        """设置信号连接"""
        self.video_info_card.finished.connect(self._on_transcript_finished)

    def _on_transcript_finished(self, task):
        """转录完成处理"""
        self.finished.emit(task)
        InfoBar.success(
            self.tr("转录完成"),
            self.tr("开始字幕优化..."),
            duration=3000,
            position=InfoBarPosition.BOTTOM,
            parent=self.parent()
        )

    def create_task(self, file_path):
        """创建任务"""
        self.create_task_thread = CreateTaskThread(file_path, Task.Type.TRANSCRIBE)
        self.create_task_thread.finished.connect(self.set_task)
        self.create_task_thread.start()

    def set_task(self, task: Task):
        """设置任务并更新UI"""
        self.task = task
        self.update_info()

    def update_info(self):
        """更新页面信息"""
        self.video_info_card.set_task(self.task)

    def process(self):
        """主处理函数"""
        self.video_info_card.start_transcription()

    def dragEnterEvent(self, event):
        """拖拽进入事件处理"""
        event.accept() if event.mimeData().hasUrls() else event.ignore()

    def dropEvent(self, event: QDropEvent):
        """拖拽放下事件处理"""
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for file_path in files:
            if not os.path.isfile(file_path):
                continue

            file_ext = os.path.splitext(file_path)[1][1:].lower()

            # 检查文件格式是否支持
            supported_formats = {fmt.value for fmt in SupportedVideoFormats} | {fmt.value for fmt in
                                                                                SupportedAudioFormats}
            is_supported = file_ext in supported_formats

            if is_supported:
                self.create_task(file_path)
                InfoBar.success(
                    self.tr("导入成功"),
                    self.tr("开始语音转文字"),
                    duration=3000,
                    parent=self
                )
                break
            else:
                InfoBar.error(
                    self.tr(f"格式错误") + file_ext,
                    self.tr(f"请拖入音频或视频文件"),
                    duration=3000,
                    parent=self
                )

    def closeEvent(self, event):
        self.video_info_card.stop()
        super().closeEvent(event)

if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    window = TranscriptionInterface()
    window.show()
    sys.exit(app.exec_())
