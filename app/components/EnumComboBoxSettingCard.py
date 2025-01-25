from typing import Union, List
from enum import Enum

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from qfluentwidgets import SettingCard, ComboBox
from qfluentwidgets.common.config import ConfigItem, qconfig

class EnumComboBoxSettingCard(SettingCard):
    """ 针对多语言的Enum选项设计的下拉框设置卡片 """
    currentTextChanged = pyqtSignal(str)

    def __init__(self, configItem: ConfigItem, icon: Union[str, QIcon], title: str,
                 content: str = None, enums: Enum = None, parent=None):
        super().__init__(icon, title, content, parent)

        self.configItem = configItem
        self.enums = enums

        # 创建可编辑的组合框
        self.comboBox = ComboBox(self)
        if self.enums:
            for item in enums:
                # Add the value to comboBox, but not the key
                # It will show the translated text
                self.comboBox.addItem( item.value )

        # 设置布局
        self.hBoxLayout.addWidget(self.comboBox, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(16)

        # 设置最小宽度
        self.comboBox.setMinimumWidth(100)

        # 设置初始值
        itemEnum = qconfig.get(configItem) # It's the enum, not the name or value
        self.comboBox.setText(itemEnum.value)
        # self.setValue(itemEnum.value)    # Set the text to translated value
        
        # 连接信号
        self.comboBox.currentTextChanged.connect(self.__onTextChanged)
        configItem.valueChanged.connect(self.comboBox.setText)

    def __onTextChanged(self, text: str):
        """ 当文本改变时触发 """
        self.setValue(text)
        self.currentTextChanged.emit(text)

    def setValue(self, value: str):
        """ 设置值 """
        enum = self.enums(value)    # Get the enum from value
        qconfig.set(self.configItem, enum)
        self.comboBox.setText(value)


    def addItems(self, items: List[Enum]):
        """ 添加选项 """
        # Here the items should be enums, not str
        for item in items:
            self.comboBox.addItem(item.value)

    def setItems(self, items: List[Enum]):
        """ 重新设置选项列表 """
        self.comboBox.clear()
        # self.items = items
        for item in items:
            self.comboBox.addItem(item.value)
