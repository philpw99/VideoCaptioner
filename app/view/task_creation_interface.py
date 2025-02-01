# -*- coding: utf-8 -*-
import os
from pathlib import Path
import sys
from urllib.parse import urlparse, ParseResult

from PyQt5.QtCore import pyqtSignal, Qt, QStandardPaths
from PyQt5.QtGui import QPixmap, QDragEnterEvent, QDropEvent
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QApplication, QLabel, QFileDialog, QMessageBox
from qfluentwidgets import LineEdit, ProgressBar, PushButton, InfoBar, InfoBarPosition, BodyLabel, ToolButton, HyperlinkButton
from qfluentwidgets import FluentIcon, FluentStyleSheet, ComboBoxSettingCard, SwitchSettingCard
from qfluentwidgets import FluentIcon as FIF

from ..common.config import cfg, Language, LanguageSerializer
from ..components.SimpleSettingCard import ComboBoxSimpleSettingCard, SwitchButtonSimpleSettingCard
from ..core.entities import SupportedAudioFormats, SupportedVideoFormats, OutputSubtitleFormatEnum, SubtitleLayoutEnum
from ..core.entities import TargetLanguageEnum, TranscribeModelEnum, Task, TranslateMethodEnum, LANGUAGES
from ..core.thread.create_task_thread import CreateTaskThread
from ..config import APPDATA_PATH, ASSETS_PATH, VERSION
from ..components.WhisperSettingDialog import WhisperSettingDialog
from ..components.WhisperAPISettingDialog import WhisperAPISettingDialog
from .log_window import LogWindow
from ..common.signal_bus import signalBus
from ..components.FasterWhisperSettingDialog import FasterWhisperSettingDialog
from ..components.EnumComboBoxSettingCard import EnumComboBoxSettingCard
from ..core.utils.test_opanai import test_openai


LOGO_PATH = ASSETS_PATH / "logo.png"

class TaskCreationInterface(QWidget):
    """
    任务创建界面类，用于创建和配置任务。
    """
    finished = pyqtSignal(Task)  # 该信号用于在任务创建完成后通知主窗口

    def __init__(self, parent=None):
        super().__init__(parent)
        self.task = None
        self.log_window = None

        self.setObjectName("TaskCreationInterface")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAcceptDrops(True)

        self.setup_ui()
        self.setup_values()
        self.setup_signals()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setObjectName("main_layout")
        self.main_layout.setSpacing(0)

        self.setup_config_layout()
        self.setup_logo()
        self.setup_search_layout()
        self.setup_status_layout()
        self.setup_info_label()

    def setup_config_layout(self):
        self.config_layout1 = QHBoxLayout()
        self.config_layout1.setObjectName("config_layout")
        self.config_layout1.setSpacing(20)

        # 创建转录模型卡片和设置按钮的容器
        transcription_container = QWidget()
        transcription_layout = QHBoxLayout(transcription_container)
        transcription_layout.setContentsMargins(0, 0, 0, 0)
        transcription_layout.setSpacing(10)

        # 创建转录模型卡片
        self.transcription_model_card = ComboBoxSimpleSettingCard(
            self.tr("转录模型"),
            self.tr("语音转换的模型"),
            [model.value for model in TranscribeModelEnum],
            self
        )
        
        # 创建设置按钮
        self.whisper_setting_button = ToolButton(FluentIcon.SETTING)
        self.whisper_setting_button.setFixedSize(32, 32)
        self.whisper_setting_button.clicked.connect(self.show_whisper_settings)
        transcription_layout.addWidget(self.transcription_model_card)
        transcription_layout.addWidget(self.whisper_setting_button)
        transcription_container.setLayout(transcription_layout)

        # 创建视频合成开关
        self.video_synthesis_card = SwitchButtonSimpleSettingCard(
            self.tr("字幕视频合成"),
            self.tr("是否把字幕合成到视频里面。"),
            self
        )

        # 创建软硬字幕开关，这需要打开视频合成开关
        self.soft_subtitle_card = SwitchButtonSimpleSettingCard(
            self.tr("软字幕"),
            self.tr("是否合成软字幕视频，关掉则会合成硬字幕"),
            self
        )


        # 创建字幕翻译方式卡片
        self.translation_method_card = ComboBoxSimpleSettingCard(
            self.tr("字幕翻译方式"),
            self.tr("选择字幕翻译方式，或者不翻译。"),
            [enum.value for enum in TranslateMethodEnum],
            self
        )

        self.config_layout1.addWidget(transcription_container)
        self.config_layout1.addWidget(self.video_synthesis_card)
        self.config_layout1.addWidget(self.soft_subtitle_card)
        self.config_layout1.addWidget(self.translation_method_card)
        
        config_container1 = QWidget()
        config_container1.setLayout(self.config_layout1)
        config_container1.setFixedHeight(70)
        
        # =========== Second Line of Config Layout ==============
        # 创建目标语言卡片
        self.target_language_card = ComboBoxSimpleSettingCard(
            self.tr("Translate Target"),
            self.tr("The final language you want to translate into."),
            [model.value for model in TargetLanguageEnum],
            self
        )
        
        self.target_format_card = ComboBoxSimpleSettingCard(
            self.tr("字幕输出格式"),
            self.tr("字幕文件的后缀名"),
            [enum.value for enum in OutputSubtitleFormatEnum],
            self
        )
        
        self.subtitle_layout_card = ComboBoxSimpleSettingCard(
            self.tr("字幕布局"),
            self.tr("原文在上，译文在上，或者其它布局"),
            [enum.value for enum in SubtitleLayoutEnum],
            self
        )

        self.config_layout2 = QHBoxLayout()
        self.config_layout2.setObjectName("config_layout2")
        self.config_layout2.setSpacing(20)
        self.config_layout2.addWidget(self.target_language_card)
        self.config_layout2.addWidget(self.target_format_card)
        self.config_layout2.addWidget(self.subtitle_layout_card)
        
        config_container2 = QWidget()
        config_container2.setLayout(self.config_layout2)
        config_container2.setFixedHeight(70)
        
        self.main_layout.addWidget(config_container1)
        self.main_layout.addWidget(config_container2)
        # self.main_layout.addSpacing(20)

    def setup_logo(self):
        self.logo_label = QLabel(self)
        self.logo_pixmap = QPixmap(str(LOGO_PATH))
        self.logo_pixmap = self.logo_pixmap.scaled(
            150, 150, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )

        self.logo_label.setPixmap(self.logo_pixmap)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.logo_label)
        self.main_layout.addSpacing(30)

    def setup_search_layout(self):
        self.search_layout = QHBoxLayout()
        self.search_layout.setContentsMargins(80, 0, 80, 0)
        self.search_input = LineEdit(self)
        self.search_input.setPlaceholderText(self.tr("请拖拽文件或输入视频URL"))
        self.search_input.setFixedHeight(40)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.focusOutEvent = lambda e: super(LineEdit, self.search_input).focusOutEvent(e)
        self.search_input.paintEvent = lambda e: super(LineEdit, self.search_input).paintEvent(e)
        self.search_input.setStyleSheet(self.search_input.styleSheet() + """
            QLineEdit {
                border-radius: 18px;
                padding: 0 20px;
                background-color: transparent;
                border: 1px solid rgba(255,255, 255, 0.08);
            }
            QLineEdit:focus[transparent=true] {
                border: 1px solid rgba(47,141, 99, 0.48);
            }
            
        """)
        self.start_button = ToolButton(FluentIcon.FOLDER, self)
        self.start_button.setFixedSize(40, 40)
        self.start_button.setStyleSheet(self.start_button.styleSheet() + """
            QToolButton {
                border-radius: 20px;
                background-color: #2F8D63;
            }
            QToolButton:hover {
                background-color: #2E805C;
            }
            QToolButton:pressed {
                background-color: #2E905C;
            }
        """)
        self.search_layout.addWidget(self.search_input)
        self.search_layout.addWidget(self.start_button)
        self.search_layout.setSpacing(10)
        self.main_layout.addLayout(self.search_layout)
        self.main_layout.addSpacing(50)

    def setup_status_layout(self):
        self.status_layout = QVBoxLayout()
        self.status_layout.setContentsMargins(50, 0, 30, 5)
        self.status_layout.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter)
        self.status_label = BodyLabel(self.tr("准备就绪"), self)
        self.status_label.setStyleSheet("font-size: 14px; color: #888888;")
        self.status_layout.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignCenter)
        self.progress_bar = ProgressBar(self)
        self.status_label.hide()
        self.progress_bar.hide()
        self.progress_bar.setFixedWidth(300)
        self.status_layout.addWidget(self.progress_bar, 0, Qt.AlignmentFlag.AlignCenter)

        self.main_layout.addStretch(1)
        self.main_layout.addLayout(self.status_layout)

    def setup_info_label(self):
        # 创建底部容器
        bottom_container = QWidget()
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建日志按钮
        self.log_button = HyperlinkButton(url="", text=self.tr("查看日志"), parent=self)
        self.log_button.setStyleSheet(self.log_button.styleSheet() + """
            QPushButton {
                font-size: 12px;
                color: #2F8D63;
                text-decoration: underline;
            }
        """)
        # 添加版权信息标签
        self.info_label = BodyLabel(self.tr(f"©VideoCaptioner {VERSION} • By Weifeng"), self)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("font-size: 12px; color: #888888;")
        
        # 创建语言转换按钮
        self.languageCard = ComboBoxSettingCard(
            cfg.language,
            FIF.LANGUAGE,
            self.tr('语言'),
            self.tr('设置您偏好的界面语言'),
            texts=['简体中文', '繁體中文', 'English', self.tr('使用系统设置')],
            parent=self
        )
        self.languageCard.setFixedHeight(70)
        
        # 将组件添加到底部布局
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.info_label)
        bottom_layout.addWidget(self.log_button)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.languageCard)        
        
        self.main_layout.addStretch()
        self.main_layout.addWidget(bottom_container)

    def setup_signals(self):
        # Local
        self.start_button.clicked.connect(self.on_start_clicked)
        self.search_input.textChanged.connect(self.on_search_input_changed)
        self.log_button.clicked.connect(self.show_log_window)

        # Local to signalBus
        self.transcription_model_card.comboBox.currentTextChanged.connect(
            signalBus.on_transcription_model_changed
        )
        self.translation_method_card.comboBox.currentTextChanged.connect(
            signalBus.on_translation_method_changed
        )
        self.video_synthesis_card.switchButton.checkedChanged.connect(
            signalBus.on_need_video_changed
        )
        self.soft_subtitle_card.switchButton.checkedChanged.connect(
            signalBus.on_soft_subtitle_changed
        )
        self.subtitle_layout_card.comboBox.currentTextChanged.connect(
            signalBus.on_subtitle_layout_changed
        )
        self.target_language_card.comboBox.currentTextChanged.connect(
            signalBus.on_target_language_changed
        )
        self.languageCard.comboBox.currentTextChanged.connect(
            signalBus.on_language_changed
        )
        
        
        # Signal bus to local
        signalBus.soft_subtitle_changed.connect(self.on_soft_subtitle_changed)
        signalBus.subtitle_layout_changed.connect(self.on_subtitle_layout_changed)
        signalBus.need_video_changed.connect(self.on_video_synthesis_changed)
        signalBus.translation_method_changed.connect(self.on_translate_method_changed)
        signalBus.transcription_model_changed.connect(self.on_transcription_model_changed)
        signalBus.target_language_changed.connect(self.on_target_language_changed)
        signalBus.language_changed.connect(self.on_language_changed)

    def on_subtitle_layout_changed(self, value: str):
        enum = SubtitleLayoutEnum(value)
        if cfg.subtitle_layout.value != enum:
            cfg.set(cfg.subtitle_layout, enum, True)    # Save the new setting
        comboBox = self.subtitle_layout_card.comboBox
        if comboBox.currentText() != enum.value:
            comboBox.setCurrentText(enum.value)


    def on_translate_method_changed(self, value: str):
        """当字幕翻译方式改变时触发"""
        # Set configItem to the new enum
        enum = TranslateMethodEnum(value)
        if cfg.translate_method.value != enum:
            cfg.set(cfg.translate_method, enum, True)
        comboBox = self.translation_method_card.comboBox
        if comboBox.currentText() != enum.value:
            comboBox.setCurrentText(enum.value)

        if enum == TranslateMethodEnum.NONE:
            self.soft_subtitle_card.setDisabled(True)
            self.target_language_card.setDisabled(True)
            self.subtitle_layout_card.setDisabled(True)
        else:
            self.soft_subtitle_card.setDisabled(False)
            self.target_language_card.setDisabled(False)
            self.subtitle_layout_card.setDisabled(False)

    def on_soft_subtitle_changed(self, enable: bool):
        if cfg.soft_subtitle.value != enable:
            cfg.set(cfg.soft_subtitle, enable, True)    # Save it.
        switch = self.soft_subtitle_card.switchButton
        if switch.isChecked() != enable:
            switch.setChecked(enable)
        
    def on_video_synthesis_changed(self, enable: bool):
        if cfg.need_video.value != enable:
            cfg.set(cfg.need_video, enable, True)       # Save it.
        switch = self.video_synthesis_card.switchButton
        if switch.isChecked() != enable:
            switch.setChecked(enable)
        self.soft_subtitle_card.setEnabled(enable)

    def on_target_language_changed(self, language: str):
        enum = TargetLanguageEnum(language)
        if cfg.target_language.value != enum:
            cfg.set(cfg.target_language, enum, True)
        comboBox = self.target_language_card.comboBox
        if comboBox.currentText() != enum.value:
            comboBox.setCurrentText(enum.value)

    def on_transcription_model_changed(self, value: str):
        """当转录模型改变时触发"""
        enum = TranscribeModelEnum(value)
        if cfg.transcribe_model.value != enum:
            cfg.set(cfg.transcribe_model, enum, True)
        comboBox = self.transcription_model_card.comboBox
        if comboBox.currentText != enum.value:
            comboBox.setCurrentText(enum.value)
        self.whisper_setting_button.setVisible( self.is_using_whisper())
            

    def setup_values(self):
        self.transcription_model_card.comboBox.setCurrentText(cfg.transcribe_model.value.value)
        self.translation_method_card.comboBox.setCurrentText(cfg.translate_method.value.value)
        self.video_synthesis_card.setChecked(cfg.need_video.value)
        self.soft_subtitle_card.setChecked( cfg.soft_subtitle.value )
        if not cfg.need_video.value:
            self.soft_subtitle_card.setDisabled(True)
        self.target_language_card.comboBox.setCurrentText(cfg.target_language.value.value)
        self.target_format_card.comboBox.setCurrentText(cfg.subtitle_output_format.value.value)
        self.subtitle_layout_card.comboBox.setCurrentText(cfg.subtitle_layout.value.value)

       
        self.search_input.setText("")
        self.whisper_setting_button.setVisible( self.is_using_whisper())

        if self.is_base_url_needed() and not cfg.api_base.value:
            InfoBar.warning(
                self.tr("警告，需要配置 Base URL！"),
                self.tr("你需要去设置中配置自己的Base URL，API Key和LLM Model。"),
                duration=10000,
                parent=self,
                position=InfoBarPosition.BOTTOM_RIGHT
        )

    def is_base_url_needed(self) -> bool:
        # Find out if LLM model will be used.
        if cfg.translate_method.value in [
            TranslateMethodEnum.OPTIMIZE,
            TranslateMethodEnum.SINGLE_SENTENCE
            ] or (self.is_using_whisper() and cfg.faster_whisper_one_word.value):  # Using one word transcribe
            return True

    def is_using_whisper(self) -> bool:
        return  cfg.transcribe_model.value in [
                TranscribeModelEnum.WHISPER,
                TranscribeModelEnum.WHISPER_API,
                TranscribeModelEnum.FASTER_WHISPER,
            ]
        

    def show_whisper_settings(self):
        """显示Whisper设置对话框"""
        match cfg.transcribe_model.value:
            case TranscribeModelEnum.WHISPER:
                if WhisperSettingDialog(self.window()).exec_():
                    return True
            case TranscribeModelEnum.WHISPER_API:
                if WhisperAPISettingDialog(self.window()).exec_():
                    return True
            case TranscribeModelEnum.FASTER_WHISPER:
                if FasterWhisperSettingDialog(self.window()).exec_():
                    return True
        return False

    def on_start_clicked(self):
        if self.start_button._icon == FluentIcon.FOLDER:
            if cfg.last_open_dir.value != "":
                open_path = cfg.last_open_dir.value
            else:
                open_path = QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)
            
            file_dialog = QFileDialog()
            file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)

            # 构建文件过滤器
            video_formats = " ".join(f"*.{fmt.value}" for fmt in SupportedVideoFormats)
            audio_formats = " ".join(f"*.{fmt.value}" for fmt in SupportedAudioFormats)
            filter_str = f"{self.tr('媒体文件')} ({video_formats} {audio_formats});;{self.tr('视频文件')} ({video_formats});;{self.tr('音频文件')} ({audio_formats})"
            file_path, _ = file_dialog.getOpenFileName(self, self.tr("选择媒体文件"), open_path, filter_str)
            if file_path:
                # Save this file's directory for later use
                file_dir = str( Path(file_path).parent )
                if file_dir != cfg.last_open_dir.value:
                    cfg.set(cfg.last_open_dir, file_dir,True)   # Set and save.
                
                self.search_input.setText(file_path)                
            return

        # Start to excute the task, but check base url first.
        if self.is_base_url_needed():
            # Need to use LLM features in this task.
            if not cfg.api_base.value:
                InfoBar.error(
                    self.tr("警告，需要配置 Base URL！"),
                    self.tr("你需要去设置中配置自己的Base URL，API Key和LLM Model。"),
                    duration=10000,
                    parent=self,
                    position=InfoBarPosition.TOP_RIGHT
                )
                return
            ok, _ = test_openai(cfg.api_base.value, cfg.api_key.value, cfg.model.value)
            if not ok:
                InfoBar.error(
                    self.tr("The LLM is not working."),
                    self.tr(f"Access to {cfg.api_base.value} failed. Check your LLM connection please."),
                    duration=10000,
                    parent=self,
                    position=InfoBarPosition.TOP_RIGHT
                )
                return

        """
        # There is no need to show faster whisper's settings again.
        need_whisper_settings = cfg.transcribe_model.value in [
            TranscribeModelEnum.WHISPER, 
            TranscribeModelEnum.WHISPER_API,
            TranscribeModelEnum.FASTER_WHISPER
        ]

        
        if need_whisper_settings and not self.show_whisper_settings():
            return
        """
            
        self.process()

    def on_search_input_changed(self):
        if self.search_input.text():
            self.start_button.setIcon(FluentIcon.PLAY)
        else:
            self.start_button.setIcon(FluentIcon.FOLDER)

    def dragEnterEvent(self, event: QDragEnterEvent):
        event.accept() if event.mimeData().hasUrls() else event.ignore()

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for file in files:
            file_path = Path(file)
            if not os.path.isfile(file_path):
                continue

            # 检查文件格式是否支持
            supported_formats = {fmt.value for fmt in SupportedVideoFormats} | {fmt.value for fmt in
                                                                                SupportedAudioFormats}
            if file_path.suffix[1:] in supported_formats:
                self.search_input.setText(file)
                self.status_label.setText(self.tr("导入成功"))
                InfoBar.success(
                    self.tr("导入成功"),
                    self.tr("导入媒体文件成功"),
                    duration=1500,
                    parent=self
                )
                break
            else:
                InfoBar.error(
                    self.tr(f"格式错误: ") + file_path.suffix,
                    self.tr("不支持该文件格式"),
                    duration=3000,
                    parent=self
                )

    def create_task(self):
        search_input = self.search_input.text()
        if os.path.isfile(search_input):
            self._process_file(search_input)
        elif self._is_valid_url(search_input):
            self._process_url(search_input)
        else:
            InfoBar.error(
                self.tr("错误"),
                self.tr("请输入有效的文件路径或视频URL"),
                duration=3000,
                parent=self
            )

    def _is_valid_url(self, url):
        try:
            result: ParseResult = urlparse(url)
            return result.scheme in ('http', 'https') and bool(result.netloc)
        except ValueError:
            return False

    def _process_file(self, file_path: str):
        need_translate = cfg.translate_method.value != TranslateMethodEnum.NONE
        
        if cfg.need_video.value:
            task_type = Task.Type.SUBTITLE      # Save it to video, with translate or not
        elif not need_translate:
            task_type = Task.Type.TRANSCRIBE    # No translate and no synthesis
        else:
            task_type = Task.Type.TRANSLATE     # Save translated sub files only
        
        self.create_task_thread = CreateTaskThread(
            file_path,
            task_type,
            need_translate=need_translate,
            translate_method= cfg.translate_method.value,
            soft_sub=cfg.soft_subtitle.value,
            need_video=cfg.need_video.value,
            )
        
        self.create_task_thread.finished.connect(self.on_create_task_finished)
        self.create_task_thread.progress.connect(self.on_create_task_progress)
        self.create_task_thread.start()

    def _process_url(self, url):
        # 检测 cookies.txt 文件
        cookiefile_path = APPDATA_PATH / "cookies.txt"
        if not cookiefile_path.exists():
            InfoBar.warning(
                self.tr("警告"),
                self.tr("建议配置cookies.txt文件，以可以下载高清视频"),
                duration=5000,
                parent=self
            )
        
        need_translate = cfg.translate_method.value == TranslateMethodEnum.NONE
        
        self.create_task_thread = CreateTaskThread(
            None,
            Task.Type.URL,
            need_translate=need_translate,
            translate_method= cfg.translate_method.value,
            soft_sub=cfg.soft_subtitle.value,
            need_video=cfg.need_video.value,
            url=url
            )
        
        self.create_task_thread.finished.connect(self.on_create_task_finished)
        self.create_task_thread.progress.connect(self.on_create_task_progress)
        self.create_task_thread.error.connect(self.on_create_task_error)
        self.create_task_thread.start()

    def on_create_task_finished(self, task: Task):
        self.task = task
        if self.task.status == Task.Status.PENDING:
            self.finished.emit(task)
        InfoBar.success(
            self.tr("任务创建成功"),
            self.tr("开始自动处理..."),
            duration=2000,
            position=InfoBarPosition.BOTTOM,
            parent=self.parent()
        )

    def on_create_task_progress(self, value, status):
        self.progress_bar.show()
        self.status_label.show()
        self.progress_bar.setValue(value)
        self.status_label.setText(status)

    def on_create_task_error(self, error):
        InfoBar.error(
            self.tr("错误"),
            self.tr(error),
            duration=5000,
            parent=self
        )

    def set_task(self, task):
        self.task = task
        self.update_info()

    def update_info(self):
        if self.task:
            self.search_input.setText(self.task.file_path)

    def process(self):
        search_input = self.search_input.text()

        if os.path.isfile(search_input):
            self._process_file(search_input)
        elif self._is_valid_url(search_input):
            self._process_url(search_input)
        else:
            InfoBar.error(
                self.tr("错误"),
                self.tr("请输入音视频文件路径或URL"),
                duration=3000,
                parent=self
            )


    def on_language_changed(self, language: str):
        if language == self.tr('使用系统设置'):
            locale = ""
        else:
            locale = LANGUAGES[language]
        
        ls = LanguageSerializer()
        lang = ls.deserialize(locale)
        if cfg.language.value != lang:
            cfg.set(cfg.language, lang, True)  # Set and save
        comboBox = self.languageCard.comboBox
        if comboBox.currentText() != language:
            comboBox.setCurrentText(language)
        """ 显示重启提示 """
        InfoBar.success(
            self.tr('更新成功 :' + language),
            self.tr('配置将在重启后生效'),
            duration=5000,
            parent=self
        )

    def show_log_window(self):
        """显示日志窗口"""
        if self.log_window is None:
            self.log_window = LogWindow()
        if self.log_window.isHidden():
            self.log_window.show()
        else:
            self.log_window.activateWindow()

if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    window = TaskCreationInterface()
    window.show()
    sys.exit(app.exec_())
