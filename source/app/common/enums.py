# Set the enums to new translated values
from enum import Enum
from qfluentwidgets import ConfigValidator, ConfigSerializer

class EnumOptionsValidator(ConfigValidator):
    """ Enum Options validator """

    def __init__(self, enumClass: Enum):
        if not enumClass or len(enumClass) == 0:
            raise ValueError("The `enums` can't be empty.")
        self.options = list(enumClass)

    def validate(self, enum):
        if isinstance(enum, Enum): # It's enum
            result = enum in self.options
            return result 
        return False

    def correct(self, enum):
        if isinstance(enum, Enum):  # It's enum
            if self.validate(enum):
                return enum
            else:
                return self.options[0]
        else:   # It's other value
            return self.options[0]
            

class EnumExSerializer(ConfigSerializer):
    """ enumeration class serializer for multi-language """
    # It use names to serialize instead of values

    def __init__(self, enumClass):
        self.enumClass = enumClass

    def serialize(self, item):
        # From configItem.value to name
        return item.name

    def deserialize(self, name):
        # From name to configItem.value, which is an Enum
        return self.enumClass[name]
