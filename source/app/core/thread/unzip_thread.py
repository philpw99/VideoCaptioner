import sys, subprocess, os
from PyQt5.QtCore import QThread, pyqtSignal

# 添加新的解压线程类
class UnzipThread(QThread):
    """7z解压线程"""
    finished = pyqtSignal()  # 解压完成信号
    error = pyqtSignal(str)  # 解压错误信号
    
    def __init__(self, zip_file, extract_path, extract_file = None, create_path = True):
        super().__init__()
        self.zip_file = zip_file
        self.extract_path = extract_path
        self.extract_command = "x" if create_path else "e"
        self.extract_file = extract_file
        
    def run(self):
        try:
            cmd = ["7z", self.extract_command, self.zip_file, f"-o{self.extract_path}", "-y"]
            if self.extract_file:
                # Only extract certain file.
                cmd.extend([self.extract_file, "-r"])

            subprocess.run(
                cmd,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
                
            # 删除压缩包
            os.remove(self.zip_file)
            self.finished.emit()
        except subprocess.CalledProcessError as e:
            self.error.emit(f"解压失败: {str(e)}")
        except Exception as e:
            self.error.emit(str(e))
