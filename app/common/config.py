# coding:utf-8
from enum import Enum

from PyQt5.QtCore import QLocale, QObject
from PyQt5.QtGui import QColor
from qfluentwidgets import (qconfig, QConfig, ConfigItem, OptionsConfigItem, BoolValidator,
                            OptionsValidator, RangeConfigItem, RangeValidator,
                            Theme, FolderValidator, ConfigSerializer, EnumSerializer)

from app.config import WORK_PATH, SETTINGS_PATH
from ..core.entities import (
    TargetLanguageEnum,
    TranscribeModelEnum,
    TranscribeLanguageEnum,
    WhisperModelEnum,
    FasterWhisperModelEnum,
    VadMethodEnum,
    OutputSubtitleFormatEnum,
    TodoWhenDoneEnum,
    SubtitleLayoutEnum,
    InternetTranslateEnum,
)
from ..components.EnumComboBoxSettingCard import EnumExSerializer, EnumOptionsValidator

qoConfig = QObject()    # qo means QObject

class Language(Enum):
    """ 软件语言 """
    CHINESE_SIMPLIFIED = QLocale(QLocale.Chinese, QLocale.China)
    CHINESE_TRADITIONAL = QLocale(QLocale.Chinese, QLocale.HongKong)
    ENGLISH = QLocale(QLocale.English)
    AUTO = QLocale()

class LanguageSerializer(ConfigSerializer):
    """ Language serializer """

    def serialize(self, language):
        return language.value.name() if language != Language.AUTO else "Auto"

    def deserialize(self, value: str):
        return Language(QLocale(value)) if value != "Auto" else Language.AUTO


class Config(QConfig):
    # Global variables here. g as global, b as bool
    gbDoingAudioRecoding = False
    gbDoingTranscribing = False
    gbDoingOptimizing = False
    gbDoingSynthesis = False
    
    """ 应用配置 """
    # ------------------- LLM 配置 -------------------
    api_key = ConfigItem("LLM", "API_Key", "")
    api_base = ConfigItem("LLM", "API_Base", "")
    model = ConfigItem("LLM", "Model", "gpt-4o-mini")
    batch_size = RangeConfigItem(
        "LLM", "BatchSize", 10, RangeValidator(10, 30)
    )
    thread_num = RangeConfigItem(
        "LLM", "ThreadNum", 10, RangeValidator(1, 30)
    )

    # ------------------- 转录配置 -------------------
    transcribe_model = OptionsConfigItem(
        "Transcribe", "TranscribeModel",
        TranscribeModelEnum.JIANYING.value,
        OptionsValidator(TranscribeModelEnum),
        EnumSerializer(TranscribeModelEnum)
    )
    use_asr_cache = ConfigItem(
        "Transcribe", "UseASRCache", True, BoolValidator()
    )
    transcribe_language = OptionsConfigItem(
        "Transcribe", "TranscribeLanguage",
        TranscribeLanguageEnum.ENGLISH.value,
        OptionsValidator(TranscribeLanguageEnum),
        EnumSerializer(TranscribeLanguageEnum)
    )

    # ------------------- Whisper Cpp 配置 -------------------
    whisper_model = OptionsConfigItem(
        "Whisper", "WhisperModel",
        WhisperModelEnum.TINY.value,
        OptionsValidator(WhisperModelEnum),
        EnumSerializer(WhisperModelEnum)
    )

    # ------------------- Faster Whisper 配置 -------------------
    faster_whisper_program = ConfigItem(
        "FasterWhisper", "Program",
        "faster-whisper-xxl.exe",
    )
    faster_whisper_model = OptionsConfigItem(
        "FasterWhisper", "Model",
        FasterWhisperModelEnum.TINY.value,
        OptionsValidator(FasterWhisperModelEnum),
        EnumSerializer(FasterWhisperModelEnum)
    )
    faster_whisper_model_dir = ConfigItem("FasterWhisper", "ModelDir", "")
    faster_whisper_device = OptionsConfigItem(
        "FasterWhisper", "Device",
        "cuda",
        OptionsValidator(["cuda", "cpu"])
    )
    # VAD 参数
    faster_whisper_vad_filter = ConfigItem(
        "FasterWhisper", "VadFilter", True, BoolValidator()
    )
    faster_whisper_vad_threshold = RangeConfigItem(
        "FasterWhisper", "VadThreshold", 0.4, RangeValidator(0, 1)
    )
    faster_whisper_vad_method = OptionsConfigItem(
        "FasterWhisper", "VadMethod",
        VadMethodEnum.SILERO_V3.value,
        OptionsValidator(VadMethodEnum),
        EnumSerializer(VadMethodEnum)
    )
    # 人声提取
    faster_whisper_ff_mdx_kim2 = ConfigItem(
        "FasterWhisper", "FfMdxKim2", False, BoolValidator()
    )
    # 文本处理参数
    faster_whisper_one_word = ConfigItem(
        "FasterWhisper", "OneWord", True, BoolValidator()
    )
    # 翻译成英语
    faster_whisper_translate_to_english = ConfigItem(
        "FasterWhisper", "TranslateToEnglish", False, BoolValidator()
    )
    # 重复惩罚
    faster_whisper_repetition_penalty = ConfigItem(
        "FasterWhisper", "RepetitionPenalty", 1, RangeValidator(1,2)
    )
    # 提示词
    faster_whisper_prompt = ConfigItem("FasterWhisper", "Prompt", "")

    # ------------------- Whisper API 配置 -------------------
    whisper_api_base = ConfigItem("WhisperAPI", "WhisperApiBase", "")
    whisper_api_key = ConfigItem("WhisperAPI", "WhisperApiKey", "")
    whisper_api_model = OptionsConfigItem("WhisperAPI", "WhisperApiModel", "")
    whisper_api_prompt = ConfigItem("WhisperAPI", "WhisperApiPrompt", "")

    # ------------------- 字幕配置 -------------------
    need_optimize = ConfigItem("Subtitle", "NeedOptimize", True, BoolValidator())
    need_translate = ConfigItem("Subtitle", "NeedTranslate", False, BoolValidator())
    use_internet_translate = ConfigItem("Subtitle","UseInternetTranslate", False, BoolValidator())
    use_internet_translate_method = OptionsConfigItem(
        "Subtitle","UseInternetTranslateMethod",
        InternetTranslateEnum.GOOGLE.value,
        OptionsValidator(InternetTranslateEnum),
        EnumSerializer(InternetTranslateEnum)
    )
    target_language = OptionsConfigItem(
        "Subtitle", "TargetLanguage",
        TargetLanguageEnum.CHINESE_SIMPLIFIED.value,
        OptionsValidator(TargetLanguageEnum),
        EnumSerializer(TargetLanguageEnum)
    )
    need_split = ConfigItem("Subtitle", "NeedSplit", True, BoolValidator())
    max_word_count_cjk = ConfigItem("Subtitle", "MaxWordCountCJK", 18, RangeValidator(8, 50))
    max_word_count_english = ConfigItem("Subtitle", "MaxWordCountEnglish", 12, RangeValidator(8, 50))
    needs_remove_punctuation = ConfigItem("Subtitle", "NeedsRemovePunctuation", False, BoolValidator())
    custom_prompt_text = ConfigItem("Subtitle", "CustomPromptText", "")

    # ------------------- 字幕合成配置 -------------------
    soft_subtitle = ConfigItem("Video", "SoftSubtitle", True, BoolValidator())
    need_video = ConfigItem("Video", "NeedVideo", True, BoolValidator())

    # ------------------- 字幕样式配置 -------------------
    subtitle_style_name = ConfigItem("SubtitleStyle", "StyleName", "default")
    subtitle_layout = OptionsConfigItem(
        "SubtitleStyle", "Layout",
        SubtitleLayoutEnum.ONLY_TRANSLATE.name,
        EnumOptionsValidator(SubtitleLayoutEnum),
        EnumExSerializer(SubtitleLayoutEnum)
    )
    subtitle_preview_image = ConfigItem("SubtitleStyle", "PreviewImage", "")

    # ------------------- 保存配置 -------------------
    work_dir = ConfigItem("Save", "Work_Dir", WORK_PATH, FolderValidator())

    # ------------------- 字幕生成配置 -------------------
    subtitle_output_format = OptionsConfigItem(
        "Subtitle", "SaveFormat",
        OutputSubtitleFormatEnum.ASS.value,
        OptionsValidator(OutputSubtitleFormatEnum),
        EnumSerializer(OutputSubtitleFormatEnum)
    )
    subtitle_file_prefix = ConfigItem("Subtitle", "FilePrefix", "")
    subtitle_file_suffix = ConfigItem("Subtitle", "FileSuffix", "")

    # ------------------- 字幕最低时长配置 -------------------
    subtitle_enable_sentence_minimum_time = ConfigItem(
        "Subtitle", "Enable Sentence Minimum Time",
        False, BoolValidator()
    )
    
    subtitle_sentence_minimum_time = RangeConfigItem(
        "Subtitle", "Sentence Minimum Time",
        1500, RangeValidator(500, 3000)
    )

    time_offset = RangeConfigItem(
        "Subtitle", "TimeOffset",
        0,
        RangeValidator(-5000, 5000)
    )
    
    vertical_offset = RangeConfigItem(
        "Subtitle", "VerticalOffset",
        0, RangeValidator(-500, 500)
    )

    # ------------------- 软件页面配置 -------------------
    micaEnabled = ConfigItem("MainWindow", "MicaEnabled", False, BoolValidator())
    dpiScale = OptionsConfigItem(
        "MainWindow", "DpiScale",
        "Auto",
        OptionsValidator([1, 1.25, 1.5, 1.75, 2, "Auto"]),
        restart=True
    )
    
    language = OptionsConfigItem(
        "MainWindow", "Language",
        Language.ENGLISH,
        OptionsValidator(Language),
        LanguageSerializer(),
        restart=True
    )

    # ------------------- 更新配置 -------------------
    checkUpdateAtStartUp = ConfigItem(
        "Update", "CheckUpdateAtStartUp", True, BoolValidator()
    )
    
    # ------------------- 最后打开文件夹 -------------------
    last_open_dir = ConfigItem("All", "Last_Open_Dir", "")

    # ------------------- 批量完成后的事情 -------------------
    todo_when_done = OptionsConfigItem(
        "All",
        "ToDo_When_Done",
        "NOTHING",
        EnumOptionsValidator(TodoWhenDoneEnum),
        EnumExSerializer(TodoWhenDoneEnum)
    )

cfg = Config()
cfg.themeMode.value = Theme.DARK
cfg.themeColor.value = QColor("#ff28f08b")
qconfig.load(SETTINGS_PATH, cfg)
