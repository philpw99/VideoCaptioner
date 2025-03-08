import os
from ...config import FFMPEG_DOWNLOAD_URL, BIN_PATH
from .download_thread import DownloadThread
from .unzip_thread import UnzipThread
from qfluentwidgets import InfoBar
from PyQt5.QtCore import QThread, pyqtSignal
from ..utils.logger import setup_logger

logger = setup_logger("download_ffmpeg")

class DownloadFFMpegThread(QThread):
    progress = pyqtSignal(int)
    error = pyqtSignal(str)
    finished = pyqtSignal()
    save_path = BIN_PATH / "ffmpeg.7z"
   
    def __init__(self):
        super().__init__()

    def run(self):
        logger.info("Start downloading ffmpeg")
        thread = DownloadThread(FFMPEG_DOWNLOAD_URL, self.save_path)
        thread.progress.connect(self._on_progress)
        thread.error.connect(self._on_error)
        if os.name != "nt":
            logger.error("Not windows system. Cannot download automatically.")
            self.error.emit(self.tr("Auto download and install only works under Windows."))
            return
        thread.start()
        thread.wait()
        logger.info("Finish ffmpeg.7z downloading, now extracting.")
        unzip = UnzipThread(self.save_path, BIN_PATH, create_path=False, extract_file="ffmpeg.exe")
        unzip.error.connect(self._on_error)
        unzip.start()
        unzip.wait()
        self.finished.emit()
        logger.info("Unzipping Done. Ffmpeg should be ready.")
        
    def _on_progress(self, progress):
        self.progress.emit(progress)

    def _on_error(self, error):
        logger.info(f"Error downloading or extracting ffmpeg: {error}")

