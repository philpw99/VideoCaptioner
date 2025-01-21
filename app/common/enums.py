# Set the enums to new translated values
from PyQt5.QtCore import QObject
from ..core.entities import SubtitleLayoutEnum, InternetTranslateEnum, TodoWhenDoneEnum, Task, BatchTaskTypeEnum

def Enums_Translate():
    qoEnums = QObject()
    BatchTaskTypeEnum.TRANSCRIBE._value_ = qoEnums.tr("Create Subtitle from Audio/Video")
    BatchTaskTypeEnum.SOFT._value_ = qoEnums.tr("Create Soft Subtitle Video")
    BatchTaskTypeEnum.HARD._value_ = qoEnums.tr("Create Hard Subtitle Video")
    
    SubtitleLayoutEnum.ONLY_ORIGINAL._value_ = qoEnums.tr("Original Only")
    SubtitleLayoutEnum.ONLY_TRANSLATE._value_ = qoEnums.tr("Translated Only")
    SubtitleLayoutEnum.ORIGINAL_ON_TOP._value_ = qoEnums.tr("Original on Top")
    SubtitleLayoutEnum.TRANSLATE_ON_TOP._value_ = qoEnums.tr("Translated on Top")

    InternetTranslateEnum.GOOGLE._value_ = qoEnums.tr("Google Translate")
    
    TodoWhenDoneEnum.NOTHING._value_ = qoEnums.tr("Nothing")
    TodoWhenDoneEnum.EXIT._value_ = qoEnums.tr("Exit The Program")
    TodoWhenDoneEnum.SHUTDOWN._value_ = qoEnums.tr("Shutdown The Computer")
    TodoWhenDoneEnum.SUSPEND._value_ = qoEnums.tr("Suspend The Computer")
    
    Task.Status.CANCELED._value_ = qoEnums.tr("Canceled")
    Task.Status.COMPLETED._value_ = qoEnums.tr("Completed")
    Task.Status.DOWNLOADING._value_ = qoEnums.tr("Downloading")
    Task.Status.FAILED._value_ = qoEnums.tr("Failed")
    Task.Status.GENERATING._value_ = qoEnums.tr("Generating")
    Task.Status.OPTIMIZING._value_ = qoEnums.tr("Optimizing")
    Task.Status.PENDING._value_ = qoEnums.tr("Pending")
    Task.Status.SYNTHESIZING._value_ = qoEnums.tr("Synthesizing")
    Task.Status.TRANSCODING._value_ = qoEnums.tr("Transcoding")
    Task.Status.TRANSLATING._value_ = qoEnums.tr("Translating")
    Task.Status.WAITINGAUDIO._value_ = qoEnums.tr("Waiting for audio transcoding")
    Task.Status.WAITINGOPTIMIZE._value_ = qoEnums.tr("Waiting for optimization")
    Task.Status.WAITINGSYNTHESIS._value_ = qoEnums.tr("Waiting for video synthesis")
    Task.Status.WAITINGTRANSCRIBE._value_ = qoEnums.tr("Waiting for transcripting")

    Task.Source.FILE_IMPORT._value_ = qoEnums.tr("File Import")
    Task.Source.URL_IMPORT._value_ = qoEnums.tr("URL Import")
    
    Task.Type.OPTIMIZE._value_ = qoEnums.tr("Optimize + Translate Subtitles")
    Task.Type.SUBTITLE._value_ = qoEnums.tr("Add Subtitle To Video")
    Task.Type.SYNTHESIS._value_ = qoEnums.tr("Combine Subtitle with Video")
    Task.Type.TRANSCRIBE._value_ = qoEnums.tr("Get Subtitle From Video/Audio")
    Task.Type.URL._value_ = qoEnums.tr("Download Video from URL then Add Subtitle")