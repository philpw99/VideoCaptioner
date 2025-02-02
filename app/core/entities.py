from dataclasses import dataclass, field
import datetime
from dataclasses import dataclass, field
from enum import Enum
from random import randint
from typing import Optional
from PyQt5.QtCore import QThread

class MuEnum(Enum):
    """ Mutable Enum. Unlike regular Enum, its values can be set again. """
    def setValue(self, newValue):
        # So far it works fine. Maybe it won't work in the furture.
        # Use on members like myEnum.member.setValue(newValue)
        oldValue = self.value
        self._value_ = newValue
        v2m_dict = self.__class__.__dict__['_value2member_map_']
        v2m_dict.pop( oldValue, None )
        v2m_dict[newValue] = self

class BatchTaskTypeEnum(MuEnum):
    """ 批量任务类型 """
    TRANSCRIBE = "Create Transcription from Audio/Video"
    TRANSLATE = "Transcribe + Translate Audio/Video"
    SOFT = "Create Soft Subtitle Video"
    HARD = "Create Hard Subtitle Video"


class SubtitleLayoutEnum(MuEnum):
    """ 字幕布局 """
    ONLY_ORIGINAL = "Original Only"
    ONLY_TRANSLATE = "Translated Only"
    ORIGINAL_ON_TOP = "Original On Top"
    TRANSLATE_ON_TOP = "Translated On Top"


class TranslateMethodEnum(MuEnum):
    """翻译方式"""
    OPTIMIZE = "大模型优化+翻译"
    SINGLE_SENTENCE = "大模型单句翻译"
    GOOGLE = "谷歌翻译"
    NONE = "不翻译"


class SupportedImageFormats(Enum):
    """ 支持的图片格式 """
    JPG = "jpg"
    PNG = "png"
    BMP = "bmp"
    GIF = "gif"
    WEBP = "webp"


class SupportedAudioFormats(Enum):
    """ 支持的音频格式 """
    AAC = "aac"
    AC3 = "ac3"
    AIFF = "aiff"
    AMR = "amr"
    APE = "ape"
    AU = "au"
    FLAC = "flac"
    M4A = "m4a"
    MP2 = "mp2"
    MP3 = "mp3"
    MKA = "mka"
    OGA = "oga"
    OGG = "ogg"
    OPUS = "opus"
    RA = "ra"
    WAV = "wav"
    WMA = "wma"


class SupportedVideoFormats(Enum):
    """ 支持的视频格式 """
    MP4 = "mp4"
    WEBM = "webm"
    OGM = "ogm"
    MOV = "mov"
    MKV = "mkv"
    AVI = "avi"
    WMV = "wmv"
    FLV = "flv"
    M4V = "m4v"
    TS = "ts"
    MPG = "mpg"
    MPEG = "mpeg"
    VOB = "vob"
    ASF = "asf"
    RM = "rm"
    RMVB = "rmvb"
    M2TS = "m2ts"
    MTS = "mts"
    DV = "dv"
    GXF = "gxf"
    TOD = "tod"
    MXF = "mxf"
    F4V = "f4v"


class SupportedSubtitleFormats(Enum):
    """ 支持的字幕格式 """
    SRT = "srt"
    ASS = "ass"
    VTT = "vtt"


class OutputSubtitleFormatEnum(Enum):
    """ 字幕输出格式 """
    SRT = "srt"
    ASS = "ass"
    # VTT = "vtt"
    JSON = "json"
    TXT = "txt"


class TranscribeModelEnum(Enum):
    """ 转录模型 """
    BIJIAN = "B 接口"
    JIANYING = "J 接口"
    FASTER_WHISPER = "FasterWhisper"
    WHISPER = "WhisperCpp"
    WHISPER_API = "Whisper [API]"

class VadMethodEnum(Enum):
    """ VAD方法 """
    SILERO_V3 = "silero_v3"
    SILERO_V4 = "silero_v4"
    SILERO_V4_FW = "silero_v4_fw"
    SILERO_V5 = "silero_v5"
    SILERO_V5_FW = "silero_v5_fw"
    PYANNOTE_V3 = "pyannote_v3"
    PYANNOTE_ONNX_V3 = "pyannote_onnx_v3"
    AUDITOK = "auditok"
    WEBRTC = "webrtc"
    NONE = ""

class TargetLanguageEnum(Enum):
    """ 翻译目标语言 """
    CHINESE_SIMPLIFIED = "简体中文"
    CHINESE_TRADITIONAL = "繁体中文"
    ENGLISH = "English"
    JAPANESE = "Japanese"
    KOREAN = "Korean"
    YUE = "粤语"
    FRENCH = "French"
    GERMAN = "German"
    SPANISH = "Spanish"
    RUSSIAN = "Russian" 
    PORTUGUESE = "Portuguese"
    TURKISH = "Turkish"
    POLISH = "Polish"
    CATALAN = "Catalan"
    DUTCH = "Dutch"
    ARABIC = "Arabic"
    SWEDISH = "Swedish"
    ITALIAN = "Italian"
    INDONESIAN = "Indonesian"
    HINDI = "Hindi"
    FINNISH = "Finnish"
    VIETNAMESE = "Vietnamese"
    HEBREW = "Hebrew"
    UKRAINIAN = "Ukrainian"
    GREEK = "Greek"
    MALAY = "Malay"
    CZECH = "Czech"
    ROMANIAN = "Romanian"
    DANISH = "Danish"
    HUNGARIAN = "Hungarian"
    TAMIL = "Tamil"
    NORWEGIAN = "Norwegian"
    THAI = "Thai"
    URDU = "Urdu"
    CROATIAN = "Croatian"
    BULGARIAN = "Bulgarian"
    LITHUANIAN = "Lithuanian"
    LATIN = "Latin"
    MAORI = "Maori"
    MALAYALAM = "Malayalam"
    WELSH = "Welsh"
    SLOVAK = "Slovak"
    TELUGU = "Telugu"
    PERSIAN = "Persian"
    LATVIAN = "Latvian"
    BENGALI = "Bengali"
    SERBIAN = "Serbian"
    AZERBAIJANI = "Azerbaijani"
    SLOVENIAN = "Slovenian"
    KANNADA = "Kannada"
    ESTONIAN = "Estonian"
    MACEDONIAN = "Macedonian"
    BRETON = "Breton"
    BASQUE = "Basque"
    ICELANDIC = "Icelandic"
    ARMENIAN = "Armenian"
    NEPALI = "Nepali"
    MONGOLIAN = "Mongolian"
    BOSNIAN = "Bosnian"
    KAZAKH = "Kazakh"
    ALBANIAN = "Albanian"
    SWAHILI = "Swahili"
    GALICIAN = "Galician"
    MARATHI = "Marathi"
    PUNJABI = "Punjabi"
    SINHALA = "Sinhala"
    KHMER = "Khmer"
    SHONA = "Shona"
    YORUBA = "Yoruba"
    SOMALI = "Somali"
    AFRIKAANS = "Afrikaans"
    OCCITAN = "Occitan"
    GEORGIAN = "Georgian"
    BELARUSIAN = "Belarusian"
    TAJIK = "Tajik"
    SINDHI = "Sindhi"
    GUJARATI = "Gujarati"
    AMHARIC = "Amharic"
    YIDDISH = "Yiddish"
    LAO = "Lao"
    UZBEK = "Uzbek"
    FAROESE = "Faroese"
    HAITIAN_CREOLE = "Haitian Creole"
    PASHTO = "Pashto"
    TURKMEN = "Turkmen"
    NYNORSK = "Nynorsk"
    MALTESE = "Maltese"
    SANSKRIT = "Sanskrit"
    LUXEMBOURGISH = "Luxembourgish"
    MYANMAR = "Myanmar"
    TIBETAN = "Tibetan"
    TAGALOG = "Tagalog"
    MALAGASY = "Malagasy"
    ASSAMESE = "Assamese"
    TATAR = "Tatar"
    HAWAIIAN = "Hawaiian"
    LINGALA = "Lingala"
    HAUSA = "Hausa"
    BASHKIR = "Bashkir"
    JAVANESE = "Javanese"
    SUNDANESE = "Sundanese"
    CANTONESE = "Cantonese"


class TodoWhenDoneEnum(MuEnum):
    """ 批量处理完成后需做事情 """
    NOTHING = "Nothing"
    SUSPEND = "Suspend the computer"
    SHUTDOWN = "Shutdown the computer"
    EXIT = "Exit the program"

class TranscribeLanguageEnum(Enum):
    """ 转录语言 """
    ENGLISH = "English"
    CHINESE_SIMPLIFIED = "简体中文"
    CHINESE_TRADITIONAL = "繁体中文"
    JAPANESE = "Japanese"
    KOREAN = "Korean"
    YUE = "粤语"
    FRENCH = "French"
    GERMAN = "German"
    SPANISH = "Spanish"
    RUSSIAN = "Russian" 
    PORTUGUESE = "Portuguese"
    TURKISH = "Turkish"
    POLISH = "Polish"
    CATALAN = "Catalan"
    DUTCH = "Dutch"
    ARABIC = "Arabic"
    SWEDISH = "Swedish"
    ITALIAN = "Italian"
    INDONESIAN = "Indonesian"
    HINDI = "Hindi"
    FINNISH = "Finnish"
    VIETNAMESE = "Vietnamese"
    HEBREW = "Hebrew"
    UKRAINIAN = "Ukrainian"
    GREEK = "Greek"
    MALAY = "Malay"
    CZECH = "Czech"
    ROMANIAN = "Romanian"
    DANISH = "Danish"
    HUNGARIAN = "Hungarian"
    TAMIL = "Tamil"
    NORWEGIAN = "Norwegian"
    THAI = "Thai"
    URDU = "Urdu"
    CROATIAN = "Croatian"
    BULGARIAN = "Bulgarian"
    LITHUANIAN = "Lithuanian"
    LATIN = "Latin"
    MAORI = "Maori"
    MALAYALAM = "Malayalam"
    WELSH = "Welsh"
    SLOVAK = "Slovak"
    TELUGU = "Telugu"
    PERSIAN = "Persian"
    LATVIAN = "Latvian"
    BENGALI = "Bengali"
    SERBIAN = "Serbian"
    AZERBAIJANI = "Azerbaijani"
    SLOVENIAN = "Slovenian"
    KANNADA = "Kannada"
    ESTONIAN = "Estonian"
    MACEDONIAN = "Macedonian"
    BRETON = "Breton"
    BASQUE = "Basque"
    ICELANDIC = "Icelandic"
    ARMENIAN = "Armenian"
    NEPALI = "Nepali"
    MONGOLIAN = "Mongolian"
    BOSNIAN = "Bosnian"
    KAZAKH = "Kazakh"
    ALBANIAN = "Albanian"
    SWAHILI = "Swahili"
    GALICIAN = "Galician"
    MARATHI = "Marathi"
    PUNJABI = "Punjabi"
    SINHALA = "Sinhala"
    KHMER = "Khmer"
    SHONA = "Shona"
    YORUBA = "Yoruba"
    SOMALI = "Somali"
    AFRIKAANS = "Afrikaans"
    OCCITAN = "Occitan"
    GEORGIAN = "Georgian"
    BELARUSIAN = "Belarusian"
    TAJIK = "Tajik"
    SINDHI = "Sindhi"
    GUJARATI = "Gujarati"
    AMHARIC = "Amharic"
    YIDDISH = "Yiddish"
    LAO = "Lao"
    UZBEK = "Uzbek"
    FAROESE = "Faroese"
    HAITIAN_CREOLE = "Haitian Creole"
    PASHTO = "Pashto"
    TURKMEN = "Turkmen"
    NYNORSK = "Nynorsk"
    MALTESE = "Maltese"
    SANSKRIT = "Sanskrit"
    LUXEMBOURGISH = "Luxembourgish"
    MYANMAR = "Myanmar"
    TIBETAN = "Tibetan"
    TAGALOG = "Tagalog"
    MALAGASY = "Malagasy"
    ASSAMESE = "Assamese"
    TATAR = "Tatar"
    HAWAIIAN = "Hawaiian"
    LINGALA = "Lingala"
    HAUSA = "Hausa"
    BASHKIR = "Bashkir"
    JAVANESE = "Javanese"
    SUNDANESE = "Sundanese"
    CANTONESE = "粤语"

WHISPER_LANGUAGES ={
    "英语": "en",
    "中文": "zh",
    "简体中文": "zh",
    "繁体中文": "zh",
    "日本語": "ja",
    "德语": "de",
    "粤语": "yue",
    "西班牙语": "es", 
    "俄语": "ru",
    "韩语": "ko",
    "法语": "fr",
    "葡萄牙语": "pt",
    "土耳其语": "tr",
    "English": "en",
    "Chinese": "zh",
    "German": "de", 
    "Spanish": "es",
    "Russian": "ru",
    "Korean": "ko",
    "French": "fr",
    "Japanese": "ja",
    "Portuguese": "pt",
    "Turkish": "tr",
    "Polish": "pl",
    "Catalan": "ca", 
    "Dutch": "nl",
    "Arabic": "ar",
    "Swedish": "sv",
    "Italian": "it",
    "Indonesian": "id",
    "Hindi": "hi",
    "Finnish": "fi",
    "Vietnamese": "vi",
    "Hebrew": "he",
    "Ukrainian": "uk",
    "Greek": "el",
    "Malay": "ms",
    "Czech": "cs",
    "Romanian": "ro",
    "Danish": "da",
    "Hungarian": "hu",
    "Tamil": "ta",
    "Norwegian": "no",
    "Thai": "th",
    "Urdu": "ur",
    "Croatian": "hr",
    "Bulgarian": "bg",
    "Lithuanian": "lt",
    "Latin": "la",
    "Maori": "mi",
    "Malayalam": "ml",
    "Welsh": "cy",
    "Slovak": "sk",
    "Telugu": "te",
    "Persian": "fa",
    "Latvian": "lv",
    "Bengali": "bn",
    "Serbian": "sr",
    "Azerbaijani": "az",
    "Slovenian": "sl",
    "Kannada": "kn",
    "Estonian": "et",
    "Macedonian": "mk",
    "Breton": "br",
    "Basque": "eu",
    "Icelandic": "is",
    "Armenian": "hy",
    "Nepali": "ne",
    "Mongolian": "mn",
    "Bosnian": "bs",
    "Kazakh": "kk",
    "Albanian": "sq",
    "Swahili": "sw",
    "Galician": "gl",
    "Marathi": "mr",
    "Punjabi": "pa",
    "Sinhala": "si",
    "Khmer": "km",
    "Shona": "sn",
    "Yoruba": "yo",
    "Somali": "so",
    "Afrikaans": "af",
    "Occitan": "oc",
    "Georgian": "ka",
    "Belarusian": "be",
    "Tajik": "tg",
    "Sindhi": "sd",
    "Gujarati": "gu",
    "Amharic": "am",
    "Yiddish": "yi",
    "Lao": "lo",
    "Uzbek": "uz",
    "Faroese": "fo",
    "Haitian Creole": "ht",
    "Pashto": "ps",
    "Turkmen": "tk",
    "Nynorsk": "nn",
    "Maltese": "mt",
    "Sanskrit": "sa",
    "Luxembourgish": "lb",
    "Myanmar": "my",
    "Tibetan": "bo",
    "Tagalog": "tl",
    "Malagasy": "mg",
    "Assamese": "as",
    "Tatar": "tt",
    "Hawaiian": "haw",
    "Lingala": "ln",
    "Hausa": "ha",
    "Bashkir": "ba",
    "Javanese": "jw",
    "Sundanese": "su",
    "Cantonese": "yue"
}


LANGUAGES = {
    "英语": "en",
    "中文": "zh",
    "简体中文": "zh-cn",
    "繁体中文": "zh-tw",
    "粤语": "yue",
    "日本語": "ja",
    "德语": "de",
    "粤语": "yue",
    "西班牙语": "es", 
    "俄语": "ru",
    "韩语": "ko",
    "法语": "fr",
    "葡萄牙语": "pt",
    "土耳其语": "tr",
    "English": "en",
    "Chinese": "zh",
    "German": "de", 
    "Spanish": "es",
    "Russian": "ru",
    "Korean": "ko",
    "French": "fr",
    "Japanese": "ja",
    "Portuguese": "pt",
    "Turkish": "tr",
    "Polish": "pl",
    "Catalan": "ca", 
    "Dutch": "nl",
    "Arabic": "ar",
    "Swedish": "sv",
    "Italian": "it",
    "Indonesian": "id",
    "Hindi": "hi",
    "Finnish": "fi",
    "Vietnamese": "vi",
    "Hebrew": "he",
    "Ukrainian": "uk",
    "Greek": "el",
    "Malay": "ms",
    "Czech": "cs",
    "Romanian": "ro",
    "Danish": "da",
    "Hungarian": "hu",
    "Tamil": "ta",
    "Norwegian": "no",
    "Thai": "th",
    "Urdu": "ur",
    "Croatian": "hr",
    "Bulgarian": "bg",
    "Lithuanian": "lt",
    "Latin": "la",
    "Maori": "mi",
    "Malayalam": "ml",
    "Welsh": "cy",
    "Slovak": "sk",
    "Telugu": "te",
    "Persian": "fa",
    "Latvian": "lv",
    "Bengali": "bn",
    "Serbian": "sr",
    "Azerbaijani": "az",
    "Slovenian": "sl",
    "Kannada": "kn",
    "Estonian": "et",
    "Macedonian": "mk",
    "Breton": "br",
    "Basque": "eu",
    "Icelandic": "is",
    "Armenian": "hy",
    "Nepali": "ne",
    "Mongolian": "mn",
    "Bosnian": "bs",
    "Kazakh": "kk",
    "Albanian": "sq",
    "Swahili": "sw",
    "Galician": "gl",
    "Marathi": "mr",
    "Punjabi": "pa",
    "Sinhala": "si",
    "Khmer": "km",
    "Shona": "sn",
    "Yoruba": "yo",
    "Somali": "so",
    "Afrikaans": "af",
    "Occitan": "oc",
    "Georgian": "ka",
    "Belarusian": "be",
    "Tajik": "tg",
    "Sindhi": "sd",
    "Gujarati": "gu",
    "Amharic": "am",
    "Yiddish": "yi",
    "Lao": "lo",
    "Uzbek": "uz",
    "Faroese": "fo",
    "Haitian Creole": "ht",
    "Pashto": "ps",
    "Turkmen": "tk",
    "Nynorsk": "nn",
    "Maltese": "mt",
    "Sanskrit": "sa",
    "Luxembourgish": "lb",
    "Myanmar": "my",
    "Tibetan": "bo",
    "Tagalog": "tl",
    "Malagasy": "mg",
    "Assamese": "as",
    "Tatar": "tt",
    "Hawaiian": "haw",
    "Lingala": "ln",
    "Hausa": "ha",
    "Bashkir": "ba",
    "Javanese": "jw",
    "Sundanese": "su",
    "Cantonese": "yue"
}


@dataclass
class VideoInfo:
    """视频信息类"""
    file_name: str
    file_path: str
    width: int
    height: int
    fps: float
    duration_seconds: float
    bitrate_kbps: int
    video_codec: str
    audio_codec: str
    audio_sampling_rate: int
    thumbnail_path: str

class WhisperModelEnum(Enum):
    TINY = "tiny"
    # BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE_V1 = "large-v1"
    LARGE_V2 = "large-v2"


class FasterWhisperModelEnum(Enum):
    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE_V1 = "large-v1"
    LARGE_V2 = "large-v2"
    LARGE_V3 = "large-v3"
    LARGE_V3_T = "large-v3-turbo"

@dataclass
class Task:
    class Status(MuEnum):
        """ 任务状态 (下载、转录、优化、翻译、生成) """
        PENDING = "Pending"
        DOWNLOADING = "Downloading"
        WAITINGAUDIO = "Waiting for audio transcoding"
        WAITINGTRANSCRIBE = "Waiting for transcribing"
        WAITINGTRANSLATE = "Waiting for translating"
        WAITINGSYNTHESIS = "Waiting for synthesizing"
        TRANSCODING = "Transcoding"
        TRANSCRIBING = "Transcribing"
        OPTIMIZING = "Optimizing"
        SYNTHESIZING = "Synthesizing"
        TRANSLATING = "Translating"
        GENERATING = "Generating"
        COMPLETED = "Completed"
        FAILED = "Failed"
        CANCELED = "Canceled"

    class Source(MuEnum):
        FILE_IMPORT = "File Import"
        URL_IMPORT = "URL Import"

    class Type(MuEnum):
        # 任务类型：transcribe or generate subtitle
        TRANSCRIBE = "Get Subtitle From Video/Audio"        # Get sub by whisper, save directly as srt or ass
        TRANSLATE = "Transcribe Video/Audio then Translate" # Get sub then translate it, save sub as file
        SUBTITLE = "Add Subtitle To Video"                  # Get sub then save it into the video file. Soft or hard.
        SYNTHESIS = "Combine Subtitle with Video"           # Combine sub with video only.
        URL = "Download Video from URL then Add Subtitle"   # Download video, get sub then translat then add it to video
        
        
    # 任务信息
    id: int = field(default_factory=lambda: randint(0, 100_000_000))
    queued_at: Optional[datetime.datetime] = None
    started_at: Optional[datetime.datetime] = None
    completed_at: Optional[datetime.datetime] = None
    status: Status = Status.PENDING
    type: Type = Type.SUBTITLE
    task_thread: Optional[QThread] = None
    fraction_downloaded: float = 0.0
    work_dir: Optional[str] = None

    # 初始输入
    file_path: Optional[str] = None
    url: Optional[str] = None
    source: Source = Source.FILE_IMPORT
    original_language: Optional[str] = None
    target_language: Optional[str] = None
    video_info: Optional[VideoInfo] = None

    # 音频转换
    audio_format: Optional[str] = "wav"
    audio_save_path: Optional[str] = None

    # 转录（转录模型）
    transcribe_model: Optional[TranscribeModelEnum] = TranscribeModelEnum.JIANYING
    transcribe_language: Optional[str] = None
    use_asr_cache: bool = True
    need_word_time_stamp: bool = False
    original_subtitle_save_path: Optional[str] = None
    # Whisper Cpp 配置
    whisper_model: Optional[WhisperModelEnum] = None
    # Whisper API 配置
    whisper_api_key: Optional[str] = None
    whisper_api_base: Optional[str] = None
    whisper_api_model: Optional[str] = None
    whisper_api_prompt: Optional[str] = None
    # Faster Whisper 配置
    faster_whisper_model: Optional[FasterWhisperModelEnum] = None
    faster_whisper_model_dir: Optional[str] = None
    faster_whisper_device: str = "cuda"
    faster_whisper_vad_filter: bool = True
    faster_whisper_vad_threshold: float = 0.5
    faster_whisper_vad_method: Optional[VadMethodEnum] = VadMethodEnum.SILERO_V3
    faster_whisper_ff_mdx_kim2: bool = False
    faster_whisper_one_word: bool = True
    faster_whisper_translate_to_english: bool = False
    faster_whisper_repetion_penalty: float = 1
    faster_whisper_prompt: Optional[str] = None

    # LLM（优化翻译模型）
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    llm_model: Optional[str] = None
    need_translate: bool = False
    translate_method: Optional[TranslateMethodEnum] = None   # Optimize, single translate or google
    result_subtitle_save_path: Optional[str] = None
    thread_num: int = 10
    batch_size: int = 10
    subtitle_layout: Optional[str] = None
    max_word_count_cjk: int = 12
    max_word_count_english: int = 18
    need_split: bool = False

    # 视频生成
    need_video: bool = True
    video_save_path: Optional[str] = None
    soft_subtitle: bool = True
    subtitle_style_srt: Optional[str] = None
    portrait: bool = False
    portrait_background: Optional[str] = None
    zoom_video: int = 100
    zoom_subtitle: int = 100
    subtitle_vertical_offset: int = 0
    
