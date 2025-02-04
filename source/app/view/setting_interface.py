import webbrowser, json
from typing import Dict
from urllib.parse import urlparse
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QThread
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QWidget, QLabel, QFileDialog
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import InfoBar
from qfluentwidgets import (SettingCardGroup, SwitchSettingCard, OptionsSettingCard, PushSettingCard,
                            HyperlinkCard, PrimaryPushSettingCard, ScrollArea,
                            ComboBoxSettingCard, ExpandLayout, CustomColorSettingCard, RangeSettingCard,
                            setTheme, setThemeColor )

from app.components.WhisperAPISettingDialog import WhisperAPISettingDialog
from app.config import VERSION, YEAR, AUTHOR, HELP_URL, FEEDBACK_URL, RELEASE_URL, APPDATA_PATH
from app.core.entities import TranscribeModelEnum, SubtitleLayoutEnum, TranslateMethodEnum
from ..common.config import cfg
from ..components.EditComboBoxSettingCard import EditComboBoxSettingCard
from ..components.EnumComboBoxSettingCard import EnumComboBoxSettingCard
from ..components.LineEditSettingCard import LineEditSettingCard
from ..components.MySettingCard import SaveSettingComboCard
from ..core.utils.test_opanai import test_openai, get_openai_models
from ..components.WhisperSettingDialog import WhisperSettingDialog
from ..components.FasterWhisperSettingDialog import FasterWhisperSettingDialog
from ..common.signal_bus import signalBus


class SettingInterface(ScrollArea):
    """ 设置界面 """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle(self.tr("设置"))

        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)

        # 头部的设置标签
        self.settingLabel = QLabel(self.tr("设置"), self)

        # 转录配置
        self.transcribeGroup = SettingCardGroup(self.tr("转录配置"), self.scrollWidget)
        self.transcribeModelCard = ComboBoxSettingCard(
            cfg.transcribe_model,
            FIF.MICROPHONE,
            self.tr('转录模型'),
            self.tr('语音转换文字要使用的转录模型'),
            texts=[ model.value for model in TranscribeModelEnum ],
            parent=self.transcribeGroup
        )
        self.whisperSettingCard = HyperlinkCard(
            '',
            self.tr('打开 Whisper 设置'),
            FIF.LANGUAGE,
            self.tr('Whisper 设置'),
            self.tr('配置 Whisper 模型和转录语言'),
            self.transcribeGroup
        )

        # LLM 配置
        self.llmGroup = SettingCardGroup(self.tr("LLM 配置"), self.scrollWidget)
        self.apiKeyCard = LineEditSettingCard(
            cfg.api_key,
            FIF.FINGERPRINT,
            self.tr("API Key"),
            self.tr("Input your API Key"),
            "sk-",
            self.llmGroup
        )
        self.apiBaseCard = LineEditSettingCard(
            cfg.api_base,
            FIF.LINK,
            self.tr("Base URL"),
            self.tr("Input OpenAI compatible Base URL ( Needs /v1 in the end. )"),
            "https://api.openai.com/v1",
            self.llmGroup
        )
        self.modelCard = EditComboBoxSettingCard(
            cfg.model,
            FIF.ROBOT,
            self.tr("模型"),
            self.tr("Enter your model here. Click on \"Check Connection\" below will fill out model list automatically."),
            ["gpt-4o", "gpt-4o-mini"],
            self.llmGroup
        )
        self.checkLLMConnectionCard = PushSettingCard(
            self.tr("检查连接"),
            FIF.LINK,
            self.tr("检查 LLM 连接"),
            self.tr("Click here to verify whether API link working or not, and fetch model list."),
            self.llmGroup
        )
        self.batchSizeCard = RangeSettingCard(
            cfg.batch_size,
            FIF.ALIGNMENT,
            self.tr('批处理大小'),
            self.tr('优化翻译下，每批处理字幕的数量，建议为 10 的倍数'),
            parent=self.llmGroup
        )
        self.threadNumCard = RangeSettingCard(
            cfg.thread_num,
            FIF.SPEED_HIGH,
            self.tr('线程数'),
            self.tr('优化翻译下，模型并行处理的数量，模型服务商允许的情况下建议尽可能大'),
            parent=self.llmGroup
        )
        self.saveLLMSettingsCard = SaveSettingComboCard(
            FIF.SAVE,
            self.tr("Save LLM Settings"),
            self.tr("Save current LLM Settings to use in the future."),
            parent=self.llmGroup
        )

        # 翻译与优化配置
        self.translateGroup = SettingCardGroup(self.tr("翻译与优化"), self.scrollWidget)
        
        self.subtitleTranslateCard = EnumComboBoxSettingCard(
            cfg.translate_method,
            FIF.SPEAKERS,
            self.tr('字幕翻译'),
            self.tr('是否对转录生成的字幕进行翻译/或者不翻译。优化翻译和单句翻译需要配置Base URL，谷歌翻译则不需要。'),
            TranslateMethodEnum,
            self.translateGroup
        )
        
        self.targetLanguageCard = ComboBoxSettingCard(
            cfg.target_language,
            FIF.LANGUAGE,
            self.tr('目标语言'),
            self.tr('Choose subtitle\'s target translate language'),
            texts=[lang.value for lang in cfg.target_language.validator.options],
            parent=self.translateGroup
        )

        # 字幕配置
        self.subtitleGroup = SettingCardGroup(self.tr("字幕配置"), self.scrollWidget)
        self.subtitleStyleCard = HyperlinkCard(
            "",
            self.tr('修改'),
            FIF.FONT,
            self.tr('字幕样式'),
            self.tr('Choose subtitle\'s style ( color, size, font ... etc.)'),
            self.subtitleGroup
        )
        self.subtitleLayoutCard = EnumComboBoxSettingCard(
            cfg.subtitle_layout,
            FIF.FONT,
            self.tr('字幕布局'),
            self.tr('Choose subtitle\'s layout ( Show Original or Translated or both )'),
            SubtitleLayoutEnum,
            self.subtitleGroup
        )

        # 保存字幕格式
        self.saveSubtitleFormatCard = ComboBoxSettingCard(
            cfg.subtitle_output_format,
            FIF.FONT,
            self.tr('Target Subtitle Format'),
            self.tr('The format for saving the final subtitle and video systhesis. Use ASS format if you want to see text styles.'),
            texts=[format.value for format in cfg.subtitle_output_format.validator.options],
            parent=self.subtitleGroup
        )
        # 字幕文件的前缀和后缀
        self.saveSubtitlePrefixCard = LineEditSettingCard(
            cfg.subtitle_file_prefix,
            FIF.TAG,
            self.tr("Subtitle File Name Prefix"),
            self.tr("Add this string to the front of the subtitle file name."),
            "",
            self.subtitleGroup
        )
        self.saveSubtitleSuffixCard = LineEditSettingCard(
            cfg.subtitle_file_suffix,
            FIF.TAG,
            self.tr("Subtitle File Name Suffix"),
            self.tr("Add this string to the end of the subtitle file name."),
            "",
            self.subtitleGroup
        )

        # 字幕句子最少时长
        self.enableSubtitleSentenceMinimumTimeCard = SwitchSettingCard(
            FIF.CHECKBOX,
            self.tr('Enable Minimum Subtitle Sentence Time'),
            self.tr('Enable the feature to add time to subtitle sentences so they won\'t be too short. '),
            cfg.subtitle_enable_sentence_minimum_time,
            self.subtitleGroup
        )
        
        self.SubtitleSentenceMinimumTimeCard = RangeSettingCard(
            cfg.subtitle_sentence_minimum_time,
            FIF.STOP_WATCH,
            self.tr('Mimimum Subtitle Sentence Time'),
            self.tr('In milliseconds, the minimum time each sentence should at least have.'),
            self.subtitleGroup
        )

        self.SubtitleTimeOffsetCard = RangeSettingCard(
            cfg.time_offset,
            FIF.STOP_WATCH,
            self.tr('Subtitle Time Offset'),
            self.tr('In milliseconds, the offset to apply to all subtitle timings.'),
            self.subtitleGroup
        )

        # 视频合成配置
        self.videoGroup = SettingCardGroup(self.tr("视频合成配置"), self.scrollWidget)

        self.needVideoCard = SwitchSettingCard(
            FIF.VIDEO,
            self.tr('Need to sythesis video'),
            self.tr('Do you want to combine the original video and subtitle into a new video.'),
            cfg.need_video,
            self.videoGroup
        )

        # 开启软字幕
        self.softSubtitleCard = SwitchSettingCard(
            FIF.FONT,
            self.tr('Soft Subtitles'),
            self.tr('When synthesising video, add the subtitle as a new track, instead of hard-coding it into video.'),
            cfg.soft_subtitle,
            self.videoGroup
        )
        
        self.subtitleVerticalOffsetCard = RangeSettingCard(
            cfg.subtitle_vertical_offset,
            FIF.MOVE,
            self.tr('Vertical Offset for Subtitles'),
            self.tr('In pixels, the vertical offset to apply to all subtitle positions.'),
            self.videoGroup
        )

        self.videoPortraitCard = SwitchSettingCard(
            FIF.PHOTO,
            self.tr("Generate Portrait Video"),
            self.tr("When synthsizing video, generate a portrait video. When it's off it will generate a landscape video."),
            cfg.portrait,
            self.videoGroup
        )

        self.videoPortraitBackgroundCard = LineEditSettingCard(
            cfg.portrait_background,
            FIF.FOLDER,
            self.tr("Portrait or Landscape Picture Background"),
            self.tr("When generating a landscape-to-portrait video, or vice versa, add a picture background to it."),
            "",
            self.videoGroup
        )

        self.zoomVideoCard = RangeSettingCard(
            cfg.zoom_video,
            FIF.ZOOM_IN,
            self.tr("Video Zoom Percentage"),
            self.tr("The scale percent for video zooming in landscape-to-portrait videos."),
            self.videoGroup
        )

        self.zoomSubtitleCard = RangeSettingCard(
            cfg.zoom_subtitle,
            FIF.ZOOM,
            self.tr("Subtitle Zoom Percentage"),
            self.tr("The scale percent for subtitle zooming in the generated video."),
            self.videoGroup
        )
        
        # 保存配置
        self.saveGroup = SettingCardGroup(self.tr("保存配置"), self.scrollWidget)
        self.savePathCard = PushSettingCard(
            self.tr('工作文件夹'),
            FIF.SAVE,
            self.tr("工作目录路径"),
            cfg.get(cfg.work_dir),
            self.saveGroup
        )

        # 个性化
        self.personalGroup = SettingCardGroup(
            self.tr('个性化'), self.scrollWidget)
        self.themeCard = OptionsSettingCard(
            cfg.themeMode,
            FIF.BRUSH,
            self.tr('应用主题'),
            self.tr("更改应用程序的外观"),
            texts=[
                self.tr('浅色'), self.tr('深色'),
                self.tr('使用系统设置')
            ],
            parent=self.personalGroup
        )
        self.themeColorCard = CustomColorSettingCard(
            cfg.themeColor,
            FIF.PALETTE,
            self.tr('主题颜色'),
            self.tr('更改应用程序的主题颜色'),
            self.personalGroup
        )
        self.zoomCard = OptionsSettingCard(
            cfg.dpiScale,
            FIF.ZOOM,
            self.tr("界面缩放"),
            self.tr("更改小部件和字体的大小"),
            texts=["100%", "125%", "150%", "175%", "200%",
                   self.tr("使用系统设置")
                   ],
            parent=self.personalGroup
        )
        self.languageCard = ComboBoxSettingCard(
            cfg.language,
            FIF.LANGUAGE,
            self.tr('语言'),
            self.tr('设置您偏好的界面语言'),
            texts=['简体中文', '繁體中文', 'English', self.tr('使用系统设置')],
            parent=self.personalGroup
        )
        
        self.noThumbnailCard = SwitchSettingCard(
            FIF.PHOTO,
            self.tr("No Thumbnails"),
            self.tr("Don't show thumbnails for NSFW reasons."),
            cfg.no_thumbnail,
            parent=self.personalGroup
        )

        # 应用信息
        self.aboutGroup = SettingCardGroup(self.tr('关于'), self.scrollWidget)
        self.helpCard = HyperlinkCard(
            HELP_URL,
            self.tr('打开帮助页面'),
            FIF.HELP,
            self.tr('帮助'),
            self.tr('发现新功能并了解有关VideoCaptioner的使用技巧'),
            self.aboutGroup
        )
        self.feedbackCard = PrimaryPushSettingCard(
            self.tr('提供反馈'),
            FIF.FEEDBACK,
            self.tr('提供反馈'),
            self.tr('提供反馈帮助我们改进VideoCaptioner'),
            self.aboutGroup
        )
        self.aboutCard = PrimaryPushSettingCard(
            self.tr('检查更新'),
            FIF.INFO,
            self.tr('关于'),
            '© ' + self.tr('版权所有') + f" {YEAR}, {AUTHOR}. " +
            self.tr('版本') + " " + VERSION,
            self.aboutGroup
        )

        self.__initWidget()

    def __initWidget(self):
        self.resize(1000, 800)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(0, 80, 0, 20)
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setObjectName('settingInterface')

        # 初始化样式表
        self.scrollWidget.setObjectName('scrollWidget')
        self.settingLabel.setObjectName('settingLabel')

        self.setStyleSheet("""        
            SettingInterface, #scrollWidget {
                background-color: transparent;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QLabel#settingLabel {
                font: 33px 'Microsoft YaHei';
                background-color: transparent;
                color: white;
            }
        """)

        # 初始化布局
        self.__initLayout()
        self.__connectSignalToSlot()
        self.load_llm_list()

    def __initLayout(self):
        self.settingLabel.move(36, 30)

        # 添加卡片到组
        self.transcribeGroup.addSettingCards([self.transcribeModelCard,
            self.whisperSettingCard])

        self.llmGroup.addSettingCards([self.apiKeyCard,
            self.apiBaseCard, self.modelCard, self.checkLLMConnectionCard,
            self.batchSizeCard, self.threadNumCard, self.saveLLMSettingsCard])

        self.translateGroup.addSettingCards([self.subtitleTranslateCard,
            self.targetLanguageCard,])
        
        self.subtitleGroup.addSettingCards([self.subtitleStyleCard, self.subtitleLayoutCard,
            self.saveSubtitleFormatCard, self.saveSubtitlePrefixCard,
            self.saveSubtitleSuffixCard, self.enableSubtitleSentenceMinimumTimeCard,
            self.SubtitleSentenceMinimumTimeCard, self.SubtitleTimeOffsetCard])

        self.videoGroup.addSettingCards([self.needVideoCard, self.softSubtitleCard,
            self.subtitleVerticalOffsetCard, self.videoPortraitCard,
            self.videoPortraitBackgroundCard, self.zoomVideoCard, self.zoomSubtitleCard])

        self.saveGroup.addSettingCard(self.savePathCard)

        self.personalGroup.addSettingCards([self.themeCard, self.themeColorCard,
            self.zoomCard, self.languageCard, self.noThumbnailCard])

        self.aboutGroup.addSettingCards([self.helpCard, self.feedbackCard, self.aboutCard])

        # 将设置卡片组添加到布局
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(36, 10, 36, 0)
        self.expandLayout.addWidget(self.transcribeGroup)
        self.expandLayout.addWidget(self.llmGroup)
        self.expandLayout.addWidget(self.translateGroup)
        self.expandLayout.addWidget(self.subtitleGroup)
        self.expandLayout.addWidget(self.videoGroup)
        self.expandLayout.addWidget(self.saveGroup)
        self.expandLayout.addWidget(self.personalGroup)
        self.expandLayout.addWidget(self.aboutGroup)

    def __connectSignalToSlot(self):
        """ 连接信号与槽 """
        cfg.appRestartSig.connect(self.__showRestartTooltip)

        # Whisper 设置
        self.whisperSettingCard.linkButton.clicked.connect(self.show_whisper_settings)

        # 检查 LLM 连接
        self.checkLLMConnectionCard.clicked.connect(self.checkLLMConnection)
        
        # 保存 LLM 设定
        self.saveLLMSettingsCard.saveClicked.connect(self.save_llm_settings)
        
        # 删除 LLM 设定
        self.saveLLMSettingsCard.deleteClicked.connect(self.delete_llm_list)

        # 载入 LLM 设定
        self.saveLLMSettingsCard.textChanged.connect(self.load_llm_settings)

        # 保存路径
        self.savePathCard.clicked.connect(self.__onsavePathCardClicked)
        
        # 字幕样式修改跳转
        self.subtitleStyleCard.linkButton.clicked.connect(
            lambda: self.window().switchTo(self.window().subtitleStyleInterface))

        # 个性化
        self.themeCard.optionChanged.connect(lambda ci: setTheme(cfg.get(ci)))
        self.themeColorCard.colorChanged.connect(setThemeColor)

        # 反馈
        self.feedbackCard.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(FEEDBACK_URL)))

        # 关于
        self.aboutCard.clicked.connect(self.checkUpdate)

        # 全局 signalBus

        # Local to signalBus
        self.subtitleLayoutCard.comboBox.currentTextChanged.connect(signalBus.on_subtitle_layout_changed)
        self.subtitleTranslateCard.comboBox.currentTextChanged.connect(signalBus.on_translation_method_changed)
        self.targetLanguageCard.comboBox.currentTextChanged.connect(signalBus.on_target_language_changed)
        self.softSubtitleCard.checkedChanged.connect(signalBus.on_soft_subtitle_changed)
        self.needVideoCard.checkedChanged.connect(signalBus.on_need_video_changed)
        # self.languageCard.comboBox.currentTextChanged.connect(signalBus.on_language_changed)
        
        # signalBus to local
        signalBus.subtitle_layout_changed.connect(self.subtitleLayoutCard.comboBox.setCurrentText)
        signalBus.translation_method_changed.connect(self.on_translation_method_changed)
        signalBus.target_language_changed.connect(self.targetLanguageCard.comboBox.setCurrentText)
        signalBus.language_changed.connect(self.languageCard.comboBox.setCurrentText)
        signalBus.need_video_changed.connect(self.needVideoCard.switchButton.setChecked)
        signalBus.soft_subtitle_changed.connect(self.softSubtitleCard.switchButton.setChecked)
        signalBus.transcription_model_changed.connect(self.transcribeModelCard.comboBox.setCurrentText)

    def on_translation_method_changed(self,text):
        # print(f"text type:{type(text)}")
        comboBox = self.subtitleTranslateCard.comboBox
        if comboBox.currentText() != text:
            comboBox.setCurrentText(text)

    def delete_llm_list(self):
        # Delete current llm settings in the combo box.
        comboBox = self.saveLLMSettingsCard.comboBox
        key = comboBox.currentText()
        save_file = APPDATA_PATH / "llm.json"
        if not save_file.exists():
            InfoBar.error(self.tr("File llm.json not exist!"),
                          self.tr("Cannot find the llm.json file."),
                          duration=5000,
                          parent=self,
                          )
            comboBox.clear()
            return
        with open(save_file,"r") as f:
            data_json: Dict = json.load(f)
        
        if len(data_json) == 0:
            return
        data_json.pop(key)
        # Save the new dict
        with open(save_file, "w") as f:
            json.dump(data_json, f, indent=4)

        comboBox.clear()
        if len(data_json) > 0:
            comboBox.addItems(list(data_json))
            # Load the current settings
            key = comboBox.currentText()
            setting_json = data_json[key]
            if not setting_json:
                InfoBar.error(self.tr(f"Error getting {key} settings"),
                              self.tr(f"Cannot get {key} settings from AppData/llm.json"),
                              duration=5000,
                              parent=self,
                              )
                return
            self.apiBaseCard.setValue(setting_json["BaseURL"])
            self.apiKeyCard.setValue(setting_json["ApiKey"])
            self.batchSizeCard.setValue(setting_json["BatchSize"])
            self.threadNumCard.setValue(setting_json["ThreadNum"])
            
        
        InfoBar.info(self.tr("LLM entry deleted."),
                     self.tr(f"The settings of {key} was deleted."),
                     duration=5000,
                     parent=self
        )
        
            
    
    def load_llm_list(self):
        save_file = APPDATA_PATH / "llm.json"
        if not save_file.exists():
            return
        with open(save_file,"r") as f:
            data_json = json.load(f)
        
        comboBox = self.saveLLMSettingsCard.comboBox
        comboBox.clear()
        comboBox.addItems(list(data_json))   # list(data_json) will list all keys in Dict
   
    def save_llm_settings(self):
        # 显示 llm 保存对话框
        if not cfg.api_base.value:
            return
        oBaseUrl = urlparse(cfg.api_base.value)
        if not oBaseUrl or not oBaseUrl.hostname:
            return
        
        setting_json = {"BaseURL": cfg.api_base.value,
                        "ApiKey": cfg.api_key.value, 
                        "BatchSize": cfg.batch_size.value,
                        "ThreadNum": cfg.thread_num.value,
                        }
        
        save_file = APPDATA_PATH / "llm.json"
        if save_file.exists():
            with open(save_file, "r") as f:
                data = f.read()
                data_json = json.loads(data)
        else:
            data_json = {}
        
        with open(save_file, "w") as f:
            data_json[oBaseUrl.hostname] = setting_json   # The key is the host name
            json.dump(data_json, f, indent=4)

        # Update the list
        self.saveLLMSettingsCard.comboBox.clear()
        self.saveLLMSettingsCard.comboBox.addItems(list(data_json))
        self.saveLLMSettingsCard.comboBox.setCurrentText(oBaseUrl.hostname)
        
        InfoBar.info(self.tr("LLM settings saved."),
                     self.tr(f"The LLM settings for {oBaseUrl.hostname} was saved."),
                     duration=5000,
                     parent=self,
                     )
        
    def load_llm_settings(self, host):
        save_file = APPDATA_PATH / "llm.json"
        with open(save_file,"r") as f:
            data = f.read()
        if not data:
            InfoBar.error(self.tr("Error Reading llm.json"), self.tr("Cannot open LLM settins file: AppData/llm.json"))
            return
        setting_json = json.loads(data)[host]
        if not setting_json:
            InfoBar.error(self.tr(f"Error getting {host} settings"), self.tr(f"Cannot get {host} settings from AppData/llm.json") )
            return
        self.apiBaseCard.setValue(setting_json["BaseURL"])
        self.apiKeyCard.setValue(setting_json["ApiKey"])
        self.batchSizeCard.setValue(setting_json["BatchSize"])
        self.threadNumCard.setValue(setting_json["ThreadNum"])
        
        
    def show_whisper_settings(self):
        """显示Whisper设置对话框"""
        match self.transcribeModelCard.comboBox.currentText():
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
                else:
                    InfoBar.error(
                        self.tr('错误'),
                        self.tr('请先选择Whisper转录模型'),
                        duration=3000,
                        parent=self
                    )
        return False
    
    def __showRestartTooltip(self):
        """ 显示重启提示 """
        InfoBar.success(
            self.tr('更新成功'),
            self.tr('配置将在重启后生效'),
            duration=1500,
            parent=self
        )

    def __onsavePathCardClicked(self):
        """ 处理保存路径卡片点击事件 """
        folder = QFileDialog.getExistingDirectory(self, self.tr("选择文件夹"), "./")
        if not folder or cfg.get(cfg.work_dir) == folder:
            return
        cfg.set(cfg.work_dir, folder)
        self.savePathCard.setContent(folder)

    def checkLLMConnection(self):
        """ 检查 LLM 连接 """
        # 检查 API Base 是否属于网址
        api_base = self.apiBaseCard.lineEdit.text()
        if not api_base.startswith("http"):
            InfoBar.error(
                self.tr('错误'),
                self.tr('请输入正确的 API Base, 含有 /v1'),
                duration=3000,
                parent=self
            )
            return

        # 禁用检查按钮，显示加载状态
        self.checkLLMConnectionCard.button.setEnabled(False)
        self.checkLLMConnectionCard.button.setText(self.tr("正在检查..."))

        # 创建并启动线程
        self.connection_thread = LLMConnectionThread(
            api_base,
            self.apiKeyCard.lineEdit.text(),
            self.modelCard.comboBox.currentText()
        )
        self.connection_thread.finished.connect(self.onConnectionCheckFinished)
        self.connection_thread.error.connect(self.onConnectionCheckError)
        self.connection_thread.start()
    
    def onConnectionCheckError(self, message):
        """ 处理连接检查错误事件 """
        self.checkLLMConnectionCard.button.setEnabled(True)
        self.checkLLMConnectionCard.button.setText(self.tr("检查连接"))
        InfoBar.error(
            self.tr('LLM 连接测试错误'),
            message,
            duration=3000,
            parent=self
        )

    def onConnectionCheckFinished(self, is_success, message, models):
        """ 处理连接检查完成事件 """
        self.checkLLMConnectionCard.button.setEnabled(True)
        self.checkLLMConnectionCard.button.setText(self.tr("检查连接"))
        if models:
            temp = self.modelCard.comboBox.currentText()
            self.modelCard.setItems(models)
            self.modelCard.comboBox.setCurrentText(temp)
            InfoBar.success(
                self.tr('获取模型列表成功:'),
                self.tr('一共') + str(len(models)) + self.tr('个模型'),
                duration=3000,
                parent=self
            )
        if not is_success:
            InfoBar.error(
                self.tr('LLM 连接测试错误'),
                message,
                duration=3000,
                parent=self
            )
        else:
            InfoBar.success(
                self.tr('LLM 连接测试成功'),
                message,
                duration=3000,
                parent=self
            )

    def checkUpdate(self):
        webbrowser.open(RELEASE_URL)

class LLMConnectionThread(QThread):
    finished = pyqtSignal(bool, str, list)
    error = pyqtSignal(str)

    def __init__(self, api_base, api_key, model):
        super().__init__()
        self.api_base = api_base
        self.api_key = api_key
        self.model = model

    def run(self):
        """ 查 LLM 连接并获取模型列表 """
        try:
            is_success, message = test_openai(self.api_base, self.api_key, self.model)
            models = get_openai_models(self.api_base, self.api_key)
            print(models)
            self.finished.emit(is_success, message, models)
        except Exception as e:
            self.error.emit(str(e))
