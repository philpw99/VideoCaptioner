from typing import Union, List
from enum import Enum

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from qfluentwidgets import SettingCard, ComboBox
from qfluentwidgets.common.config import ConfigItem, qconfig , ConfigValidator, ConfigSerializer


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
        self.hBoxLayout.addWidget(self.comboBox, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        # 设置最小宽度
        self.comboBox.setMinimumWidth(100)

        # 设置初始值
        name = qconfig.get(configItem) # It's the key, not the value
        self.setValue(enums[name].value)    # Set the text to translated value
        
        # 连接信号
        self.comboBox.currentTextChanged.connect(self.__onTextChanged)
        configItem.valueChanged.connect(self.comboBox.setText)

    def __onTextChanged(self, text: str):
        """ 当文本改变时触发 """
        self.setValue(text)
        self.currentTextChanged.emit(text)

    def setValue(self, value: str):
        """ 设置值 """
        key = self.getKey(value)    # Get the name from Enum by value
        qconfig.set(self.configItem, key)
        self.comboBox.setText(value)

    def addItems(self, items: List[str]):
        """ 添加选项 """
        for item in items:
            self.comboBox.addItem(item)

    def setItems(self, items: List[str]):
        """ 重新设置选项列表 """
        self.comboBox.clear()
        self.items = items
        for item in items:
            self.comboBox.addItem(item)

    def getKey(self, value) -> str:
        # Get the key str from value str
        for item in self.enums:
            if item.value == value:
                return item.name
        return ""


class EnumOptionsValidator(ConfigValidator):
    """ Enum Options validator """

    def __init__(self, enums: Enum):

        if type(enums) == type(Enum):
            self.names = list(item.name for item in enums)
        else:
            self.names = []

    def validate(self, value):
        return value in self.names

    def correct(self, value):
        return value if self.validate(value) else self.names[0]

class EnumExSerializer(ConfigSerializer):
    """ enumeration class serializer for multi-language """

    def __init__(self, enumClass):
        self.enumClass = enumClass

    def serialize(self, key):
        # From configItem.value to text
        return key

    def deserialize(self, name):
        # From text to configItem.value
        return name