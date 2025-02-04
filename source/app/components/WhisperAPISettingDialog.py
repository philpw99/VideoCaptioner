from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget
from qfluentwidgets import (MessageBoxBase, BodyLabel, 
                          SettingCardGroup, InfoBar, InfoBarPosition)
from qfluentwidgets import FluentIcon as FIF, ComboBoxSettingCard

from ..common.config import cfg
from ..core.entities import TranscribeLanguageEnum
from ..components.LineEditSettingCard import LineEditSettingCard
from ..components.EditComboBoxSettingCard import EditComboBoxSettingCard

class WhisperAPISettingDialog(MessageBoxBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.titleLabel = BodyLabel(self.tr('Whisper API 设置'), self)
        
        # 创建设置卡片组
        self.settingGroup = SettingCardGroup(self.tr("API设置"), self)
        
        # API Base URL
        self.base_url_card = LineEditSettingCard(
            cfg.whisper_api_base,
            FIF.LINK,
            self.tr("API Base URL"),
            self.tr("输入 Whisper API Base URL"),
            "https://api.openai.com/v1",
            self.settingGroup
        )
        
        # API Key
        self.api_key_card = LineEditSettingCard(
            cfg.whisper_api_key,
            FIF.FINGERPRINT,
            self.tr("API Key"),
            self.tr("输入 Whisper API Key"),
            "sk-",
            self.settingGroup
        )
        
        # Model
        self.model_card = EditComboBoxSettingCard(
            cfg.whisper_api_model,
            FIF.ROBOT,
            self.tr("Whisper 模型"),
            self.tr("选择或输入 Whisper 模型名称"),
            ["whisper-large-v3", "whisper-large-v3-turbo", "whisper-1"],
            self.settingGroup
        )
        
        # Language
        self.language_card = ComboBoxSettingCard(
            cfg.transcribe_language,
            FIF.LANGUAGE,
            self.tr("原语言"),
            self.tr("音频的原语言"),
            [lang.value for lang in TranscribeLanguageEnum],
            self.settingGroup
        )
        self.language_card.comboBox.setMaxVisibleItems(6)
        
        # Prompt
        self.prompt_card = LineEditSettingCard(
            cfg.whisper_api_prompt,
            FIF.CHAT,
            self.tr("提示词"),
            self.tr("可选的提示词,默认空"),
            "",
            self.settingGroup
        )

        # 设置最小宽度
        self.base_url_card.lineEdit.setMinimumWidth(200)
        self.api_key_card.lineEdit.setMinimumWidth(200)
        self.model_card.comboBox.setMinimumWidth(200)
        self.language_card.comboBox.setMinimumWidth(200)
        self.prompt_card.lineEdit.setMinimumWidth(200)

        # 添加到布局
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addSpacing(20)
        
        # 添加设置卡片到组
        self.settingGroup.addSettingCard(self.base_url_card)
        self.settingGroup.addSettingCard(self.api_key_card)
        self.settingGroup.addSettingCard(self.model_card)
        self.settingGroup.addSettingCard(self.language_card)
        self.settingGroup.addSettingCard(self.prompt_card)
        
        # 添加设置组到布局
        self.viewLayout.addWidget(self.settingGroup)

        # 设置按钮文本
        self.yesButton.setText(self.tr('确定'))
        self.cancelButton.setText(self.tr('取消'))
        
        # 设置最小宽度
        self.widget.setMinimumWidth(500)
        
        # 连接信号
        self.yesButton.clicked.connect(self.__onYesButtonClicked)

    def __onYesButtonClicked(self):
        if not cfg.whisper_api_key.value or not cfg.whisper_api_base.value:
            InfoBar.warning(
                title=self.tr('警告'),
                content=self.tr('API设置不完整'),
                parent=self.window(),
                duration=3000,
                position=InfoBarPosition.BOTTOM
            )
        else:
            self.accept()
            InfoBar.success(
                self.tr("设置已保存"),
                self.tr("Whisper API 设置已更新"),
                duration=3000,
                parent=self.window(),
                position=InfoBarPosition.BOTTOM
            )
            if cfg.transcribe_language.value == TranscribeLanguageEnum.JAPANESE:
                InfoBar.warning(
                    self.tr("请注意身体！！"),
                    self.tr("小心肝儿,注意身体哦~"),
                    duration=2000,
                    parent=self.window(),
                    position=InfoBarPosition.BOTTOM
                )
