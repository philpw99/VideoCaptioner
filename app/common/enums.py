# Set the enums to new translated values
from enum import Enum
from PyQt5.QtCore import QObject
from qfluentwidgets import ConfigValidator, ConfigSerializer
from ..core.entities import SubtitleLayoutEnum, TodoWhenDoneEnum, Task, BatchTaskTypeEnum, TranslateMethodEnum

class EnumOptionsValidator(ConfigValidator):
    """ Enum Options validator """

    def __init__(self, enumClass: Enum):
        if not enumClass or len(enumClass) == 0:
            raise ValueError("The `enums` can't be empty.")

        if issubclass(enumClass, Enum):
            self.enumClass = enumClass
        else:
            self.enums = None

    def validate(self, enum):
        return enum in self.enumClass

    def correct(self, enum):
        return enum if self.validate(enum) else list(self.enumClass)[0]

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

def Enums_Translate():
    qoEnums = QObject()
    BatchTaskTypeEnum.TRANSCRIBE.setValue( qoEnums.tr("Create Transcription from Audio/Video") )
    BatchTaskTypeEnum.TRANSLATE.setValue( qoEnums.tr("Transcribe + Translate Audio/Video") )
    BatchTaskTypeEnum.SOFT.setValue( qoEnums.tr("Create Soft Subtitle Video") )
    BatchTaskTypeEnum.HARD.setValue( qoEnums.tr("Create Hard Subtitle Video") )
    
    SubtitleLayoutEnum.ONLY_ORIGINAL.setValue( qoEnums.tr("Original Only") )
    SubtitleLayoutEnum.ONLY_TRANSLATE.setValue( qoEnums.tr("Translated Only") )
    SubtitleLayoutEnum.ORIGINAL_ON_TOP.setValue( qoEnums.tr("Original on Top") )
    SubtitleLayoutEnum.TRANSLATE_ON_TOP.setValue( qoEnums.tr("Translated on Top"))
    
    TranslateMethodEnum.OPTIMIZE.setValue( qoEnums.tr("Optimize Translate") )
    TranslateMethodEnum.GOOGLE.setValue( qoEnums.tr("Google Translate") )
    TranslateMethodEnum.SINGLE_SENTENCE.setValue( qoEnums.tr("Single Sentence Translate") )
    TranslateMethodEnum.NONE.setValue( qoEnums.tr("No Translation") )

    TodoWhenDoneEnum.NOTHING.setValue( qoEnums.tr("Nothing"))
    TodoWhenDoneEnum.EXIT.setValue( qoEnums.tr("Exit The Program"))
    TodoWhenDoneEnum.SHUTDOWN.setValue( qoEnums.tr("Shutdown The Computer"))
    TodoWhenDoneEnum.SUSPEND.setValue( qoEnums.tr("Suspend The Computer"))
    
    Task.Status.CANCELED.setValue( qoEnums.tr("Canceled"))
    Task.Status.COMPLETED.setValue( qoEnums.tr("Completed"))
    Task.Status.DOWNLOADING.setValue( qoEnums.tr("Downloading"))
    Task.Status.FAILED.setValue( qoEnums.tr("Failed"))
    Task.Status.GENERATING.setValue( qoEnums.tr("Generating"))
    Task.Status.OPTIMIZING.setValue( qoEnums.tr("Optimizing"))
    Task.Status.PENDING.setValue( qoEnums.tr("Pending"))
    Task.Status.SYNTHESIZING.setValue( qoEnums.tr("Synthesizing"))
    Task.Status.TRANSCODING.setValue( qoEnums.tr("Transcoding"))
    Task.Status.TRANSLATING.setValue( qoEnums.tr("Translating"))
    Task.Status.WAITINGAUDIO.setValue( qoEnums.tr("Waiting for audio transcoding"))
    Task.Status.WAITINGTRANSLATE.setValue( qoEnums.tr("Waiting for translating."))
    Task.Status.WAITINGSYNTHESIS.setValue( qoEnums.tr("Waiting for video synthesis"))
    Task.Status.WAITINGTRANSCRIBE.setValue( qoEnums.tr("Waiting for transcripting"))

    Task.Source.FILE_IMPORT.setValue( qoEnums.tr("File Import"))
    Task.Source.URL_IMPORT.setValue( qoEnums.tr("URL Import"))
    
    Task.Type.SUBTITLE.setValue( qoEnums.tr("Add Subtitle To Video"))
    Task.Type.SYNTHESIS.setValue( qoEnums.tr("Combine Subtitle with Video"))
    Task.Type.TRANSCRIBE.setValue( qoEnums.tr("Get Subtitle From Video/Audio"))
    Task.Type.TRANSLATE.setValue(qoEnums.tr("Add Translated Sub To Video"))
    Task.Type.URL.setValue( qoEnums.tr("Download Video from URL then Add Subtitle"))