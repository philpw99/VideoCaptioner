import os
import logging
from pathlib import Path

VERSION = "v1.2.0"
SUBVERSION = "3.6.0"
YEAR = 2025
APP_NAME = "VideoCaptioner"
AUTHOR = "Weifeng"
COAUTHOR = "Philpw99"

HELP_URL = "https://github.com/WEIFENG2333/VideoCaptioner"
GITHUB_REPO_URL = "https://github.com/WEIFENG2333/VideoCaptioner"
RELEASE_URL = "https://github.com/WEIFENG2333/VideoCaptioner/releases/latest"
FEEDBACK_URL = "https://github.com/WEIFENG2333/VideoCaptioner/issues"

FFMPEG_DOWNLOAD_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-git-essentials.7z"

# 路径
ROOT_PATH = Path(__file__).parent

RESOURCE_PATH = ROOT_PATH.parent / "resource"
APPDATA_PATH = ROOT_PATH.parent / "AppData"
WORK_PATH = ROOT_PATH.parent / "work-dir"


BIN_PATH = RESOURCE_PATH / "bin"
ASSETS_PATH = RESOURCE_PATH / "assets"
SUBTITLE_STYLE_PATH = RESOURCE_PATH / "subtitle_style"

CACHE_PATH = APPDATA_PATH / "cache"
LOG_PATH = APPDATA_PATH / "logs"
SETTINGS_PATH = APPDATA_PATH / "settings.json"
MODEL_PATH = APPDATA_PATH / "models"

FASER_WHISPER_PATH = BIN_PATH / "Faster-Whisper-XXL"

# 日志配置
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 环境变量添加 bin 路径，添加到PATH开头以优先使用
os.environ["PATH"] = str(BIN_PATH) + os.pathsep + os.environ["PATH"]
os.environ["PATH"] = str(FASER_WHISPER_PATH) + os.pathsep + os.environ["PATH"]

# 添加 VLC 路径
# os.environ['PYTHON_VLC_MODULE_PATH'] = str( BIN_PATH / "vlc" / "plugins" )
# os.environ['PYTHON_VLC_LIB_PATH'] = str( BIN_PATH / "vlc" / "libvlc.dll" )
if os.name == "nt":
    VLC_PATH = Path(os.environ["ProgramFiles"] + "\\VideoLAN\\VLC")

# 创建路径
for p in [CACHE_PATH, LOG_PATH, WORK_PATH, MODEL_PATH]:
    p.mkdir(parents=True, exist_ok=True)
