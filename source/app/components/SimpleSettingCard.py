from PyQt5.QtCore import *
from PyQt5.QtWidgets import QHBoxLayout

from qfluentwidgets import ComboBox, SwitchButton, CaptionLabel, CardWidget, ToolTipFilter, ToolTipPosition, PushButton


class SimpleSettingCard(CardWidget):
    """基础设置卡片类"""

    def __init__(self, title, content, parent=None):
        super().__init__(parent)
        self.title = title
        self.content = content
        self.setup_ui()

    def setup_ui(self):
        self.cardlayout = QHBoxLayout(self)
        self.cardlayout.setContentsMargins(16, 10, 8, 10)
        self.cardlayout.setSpacing(8)
        self.label = CaptionLabel(self)
        self.label.setText(self.title)
        self.cardlayout.addWidget(self.label)

        self.cardlayout.addStretch(1)

        self.setToolTip(self.content)
        self.installEventFilter(ToolTipFilter(self, 100, ToolTipPosition.BOTTOM))


class ComboBoxSimpleSettingCard(SimpleSettingCard):
    """下拉框设置卡片"""
    valueChanged = pyqtSignal(str)

    def __init__(self, title, content, items=None, parent=None):
        super().__init__(title, content, parent)
        self.items = items or []
        self.setup_combobox()

    def setup_combobox(self):
        self.comboBox = ComboBox(self)
        self.comboBox.addItems(self.items)
        self.comboBox.setMaxVisibleItems(6)
        self.comboBox.currentTextChanged.connect(self.valueChanged)
        self.cardlayout.addWidget(self.comboBox)

    def setValue(self, value):
        self.comboBox.setCurrentIndex(self.items.index(value))

    def value(self):
        return self.comboBox.currentText()


class SwitchButtonSimpleSettingCard(SimpleSettingCard):
    """开关设置卡片"""
    checkedChanged = pyqtSignal(bool)

    def __init__(self, title, content, parent=None):
        super().__init__(title, content, parent)
        self.setup_switch()

    def setup_switch(self):
        self.switchButton = SwitchButton(self)
        self.switchButton.setOnText(self.tr("开"))
        self.switchButton.setOffText(self.tr("关"))
        self.switchButton.checkedChanged.connect(self.checkedChanged)
        self.cardlayout.addWidget(self.switchButton)

        self.clicked.connect(lambda: self.setChecked(not self.isChecked()))

    def setChecked(self, checked):
        self.switchButton.setChecked(checked)

    def isChecked(self):
        return self.switchButton.isChecked()

class PushButtonSimpleSettingCard(SimpleSettingCard):
    """简单按键"""
    def __init__(self, title, content, parent=None):
        super().__init__(title, content, parent)
        self.setup_button()
    
    def setup_button(self):
        self.pushButton = PushButton(self)
        self.cardlayout.addWidget(self.pushButton)
    
    def setButtonText(self, new_value: str):
        self.pushButton.setText(new_value)