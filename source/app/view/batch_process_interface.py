import datetime, time
import os
from pathlib import Path
import subprocess
import sys
from threading import Lock

from PyQt5.QtCore import *
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFileDialog, QMainWindow, QMessageBox
from qfluentwidgets import ComboBox, CardWidget, ToolTipFilter, FluentWindow, isDarkTheme, \
    ToolTipPosition, PrimaryPushButton, PushButton, InfoBar, BodyLabel, PillPushButton, setFont, \
    InfoBadgePosition, ProgressRing, InfoBarPosition, ScrollArea, Action, RoundMenu, IconInfoBadge, \
    InfoLevel, SwitchButton, IndicatorPosition
from qfluentwidgets import FluentIcon as FIF
from qframelesswindow import FramelessWindow, StandardTitleBar

from ..config import RESOURCE_PATH
from ..common.config import cfg
from ..common.signal_bus import signalBus

from ..core.entities import SupportedVideoFormats, SupportedAudioFormats, TodoWhenDoneEnum, SupportedSubtitleFormats, SupportedImageFormats
from ..core.entities import Task, VideoInfo, BatchTaskTypeEnum, TranslateMethodEnum, NOT_RUNNING_TASKS
from ..core.thread.create_task_thread import CreateTaskThread
from ..core.thread.subtitle_pipeline_thread import SubtitlePipelineThread
from ..core.thread.transcript_thread import TranscriptThread
from ..view.subtitle_optimization_interface import SubtitleOptimizationInterface


class TimedMessageBox(QMessageBox):
    def __init__(self, title, message, timeout=60):
        super(TimedMessageBox, self).__init__()
        self.timeout = timeout
        self.setWindowTitle(title)
        self.setText('\n'.join((message, f"Closing in {timeout} seconds")))
        self.setIcon(QMessageBox.Icon.Warning)
        self.setStandardButtons( QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel )
        self.setDefaultButton = QMessageBox.StandardButton.Ok

    def showEvent(self, event):
        QTimer().singleShot(self.timeout*1000, self.close)
        super(TimedMessageBox, self).showEvent(event)

class BatchProcessInterface(QWidget):
    add_tasks_finished = pyqtSignal()
    win_title_update = pyqtSignal(str)
    file_list = []
    org_title = ""
    update_timer = None
    
    """批量处理界面"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BatchProcessInterface")
        self.org_title = self.tr("批量处理")
        self.setWindowTitle(self.org_title)
        self.setAcceptDrops(True)

        self.tasks: list[Task] = []
        self.task_cards: list[TaskInfoCard] = []
        self.processing = False
        self.lock = Lock()
        self.create_threads: list[CreateTaskThread] = []
        self.update_timer = UpdateTimer()
        self.setup_ui()
        self._initStyle()
        self.setup_signals()

    def setup_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(20)

        # 顶部操作布局
        self.top_layout = QHBoxLayout()
        self.top_layout.setSpacing(10)

        # 添加文件按钮
        self.add_file_button = PushButton(self.tr("添加视频文件"), self, icon=FIF.ADD)
        self.top_layout.addWidget(self.add_file_button)

        # 清空任务按钮
        self.clear_all_button = PushButton(self.tr("清空任务"), self, icon=FIF.DELETE)
        self.clear_all_button.setToolTip(self.tr("删除所有的任务"))
        self.top_layout.addWidget(self.clear_all_button)

        # 任务类型选择
        self.task_type_combo = ComboBox(self)
        self.task_type_combo.addItems(job.value for job in BatchTaskTypeEnum)
        self.task_type_combo.setToolTip(self.tr("添加新任务时的类型，一般和首页的类型一致，但也可以选其它类型"))
        self.set_default_task_type(True)
            
        self.top_layout.addWidget(self.task_type_combo)

        self.top_layout.addStretch(1)

        # 添加启动和取消按钮
        self.start_all_button = PrimaryPushButton(self.tr("开始处理"), self, icon=FIF.PLAY)
        self.start_all_button.setToolTip(self.tr("开始批量音视频处理，将会处理所有处于'等待'或者'取消'状态的任务。"))
        self.cancel_button = PushButton(self.tr("取消"), self, icon=FIF.CLOSE)
        self.cancel_button.setToolTip(self.tr("停止所有正在运行中的任务"))
        self.cancel_button.setEnabled(False)
        self.todo_when_done_label = BodyLabel(self.tr("After All Done, "))
        self.todo_when_done_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignCenter )
        self.todo_when_done_combobox = ComboBox()
        self.todo_when_done_combobox.addItems(item.value for item in TodoWhenDoneEnum)
        self.todo_when_done_combobox.setToolTip(self.tr("设定所有任务完成后执行的行动"))
        todoEnum = cfg.todo_when_done.value
        self.todo_when_done_combobox.setCurrentText(todoEnum.value)  # Doing nothing
        
        self.top_layout.addWidget(self.start_all_button)
        self.top_layout.addWidget(self.cancel_button)
        self.top_layout.addWidget(self.todo_when_done_label)
        self.top_layout.addWidget(self.todo_when_done_combobox)

        self.main_layout.addLayout(self.top_layout)

        # 创建滚动区域
        self.scroll_area = ScrollArea(self)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.setAlignment(Qt.AlignTop)
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.main_layout.addWidget(self.scroll_area)

    def _initStyle(self):
        """初始化样式"""
        self.scroll_widget.setObjectName("scrollWidget")
        self.setObjectName("BatchProcessInterface")
        self.setStyleSheet("""        
            BatchProcessInterface, #scrollWidget {
                background-color: transparent;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

    def setup_signals(self):
        # Local
        self.add_file_button.clicked.connect(self.on_add_file)
        self.clear_all_button.clicked.connect(self.clear_all_tasks)
        self.start_all_button.clicked.connect(self.start_batch_process)
        self.cancel_button.clicked.connect(self.cancel_batch_process)
        self.todo_when_done_combobox.currentTextChanged.connect(self.todo_when_done_changed)
        self.add_tasks_finished.connect(self.update_win_title)
        
        # From signalBus to local
        signalBus.need_video_changed.connect(self.set_default_task_type)
        signalBus.translation_method_changed.connect(self.set_default_task_type)
        signalBus.soft_subtitle_changed.connect(self.set_default_task_type)

    def set_default_task_type(self, whatever):
        # Set it according to the configuration
        if cfg.need_video.value:
            # Has video.
            if cfg.soft_subtitle.value:
                # Create soft sub video
                self.task_type_combo.setCurrentText(BatchTaskTypeEnum.SOFT.value)
            else:
                # Create hard sub video
                self.task_type_combo.setCurrentText(BatchTaskTypeEnum.HARD.value)
        elif cfg.translate_method.value == TranslateMethodEnum.NONE:
            # No video. No translation.
            self.task_type_combo.setCurrentText(BatchTaskTypeEnum.TRANSCRIBE.value)
        else:
            # No video. Need translation.
            self.task_type_combo.setCurrentText(BatchTaskTypeEnum.TRANSLATE.value)

    def todo_when_done_changed(self, text: str):
        cfg.set(cfg.todo_when_done, text)

    def clear_all_tasks(self):
        """清空所有任务"""
        # 如果正在处理任务,不允许清空
        if self.processing:
            InfoBar.warning(
                self.tr("无法清空"),
                self.tr("正在处理的任务无法清空"),
                duration=2000,
                position=InfoBarPosition.BOTTOM,
                parent=self
            )
            return

        # 清空所有任务卡片
        for task_card in self.task_cards[:]:
            self.remove_task_card(task_card)

        InfoBar.success(
            self.tr("已清空"),
            self.tr("已清空所有任务"),
            duration=2000,
            position=InfoBarPosition.BOTTOM,
            parent=self
        )
        self.update_win_title()

    def start_batch_process(self):
        """开始批量处理"""
        self.processing = True
        # self.start_all_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        # self.add_file_button.setEnabled(False)
        self.clear_all_button.setEnabled(False)

        if not self.task_cards:
            InfoBar.warning(
                self.tr("警告"),
                self.tr("没有可处理的任务"),
                duration=2000,
                parent=self
            )
            return

        # 显示开始处理的通知
        InfoBar.info(
            self.tr("开始处理"),
            self.tr("开始批量处理任务"),
            duration=5000,
            position=InfoBarPosition.BOTTOM,
            parent=self
        )

        # Reset all canceled tasks to pending tasks.
        for task_card in self.task_cards:
            if task_card.task.status == Task.Status.CANCELED:
                task_card.task.status = Task.Status.PENDING
        
        # 查找头两个未完成的任务并开始处理
        c = 1
        for task_card in self.task_cards:
            if task_card.task.status == Task.Status.PENDING:
                if c == 2:  # Add a 2 second pause between 1 and 2
                    time.sleep(2)
                task_card.finished.connect(self.on_task_finished)
                task_card.error.connect(self.on_task_error)
                task_card.finished.connect(self.update_win_title)
                task_card.error.connect(self.update_win_title)
                task_card.start()
                c += 1
                if c > 2:
                    break

        self.update_win_title("Batch process started.")
        self.update_timer.updateSignal.connect(self.update_win_title)   # Runs every 5 seconds
        self.update_timer.start()


        # 判断是否所有任务都已完成
        # if all(task_card.task.status in [Task.Status.COMPLETED, Task.Status.FAILED, Task.Status.CANCELED] for task_card in self.task_cards):
        #     self.on_batch_finished()

    def cancel_batch_process(self):
        """取消批量处理"""
        self.processing = False
        # self.start_all_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        # self.add_file_button.setEnabled(True)
        self.clear_all_button.setEnabled(True)

        # 停止所有正在运行的任务
        for task_card in self.task_cards:
            if task_card.task.status not in NOT_RUNNING_TASKS:
                task_card.stop()

        # 显示取消处理的通知
        InfoBar.warning(
            self.tr("已取消"),
            self.tr("已取消批量处理"),
            duration=2000,
            position=InfoBarPosition.BOTTOM,
            parent=self
        )
        
        self.update_win_title(self.tr("Batch Process Canceled."))
        self.update_timer.stop()

    def on_task_finished(self, task):
        """单个任务完成的处理"""
        InfoBar.success(
            self.tr("任务完成"),
            self.tr("任务已完成"),
            duration=2000,
            position=InfoBarPosition.BOTTOM,
            parent=self
        )

        # 查找下一个未完成的任务
        next_task = None
        c = 0
        for task_card in self.task_cards:
            if task_card.task.status not in NOT_RUNNING_TASKS:
                # This task is running.
                c += 1
                continue
            if c >= 2:
                # Over 2 tasks are running.
                break
            if task_card.task.status == Task.Status.PENDING:
                # Not includes Failed or Completed.
                task_card.finished.connect(self.on_task_finished)
                if c == 1:  # Add a 2 second pause between 1 and 2
                    time.sleep(2)
                task_card.start()
                c += 1
            if c >= 2:  # 2 tasks are running
                break

        self.update_win_title()
        if c == 0:  # No next task at all
            # 所有任务都完成了
            self.on_batch_finished()

    def on_task_error(self, error):
        """单个任务出错"""
        InfoBar.error(
            self.tr("任务出错"),
            self.tr("任务出错:") + error,
            duration=5000,
            parent=self
        )
        # 查找下一个未完成的任务
        next_task = None
        for task_card in self.task_cards:
            if task_card.task.status == Task.Status.PENDING:
                next_task = task_card
                break

        if next_task:
            next_task.finished.connect(self.on_task_finished)
            next_task.start()
        else:
            # 所有任务都完成了
            self.on_batch_finished()
            
        self.update_win_title()
    
    def on_batch_finished(self):
        """批量处理完成的处理"""

        self.update_timer.stop()
        
        match self.todo_when_done_combobox.currentText():
            case TodoWhenDoneEnum.EXIT.value:
                qbox = TimedMessageBox(
                    self.tr("Program exiting in 1 minute"),
                    self.tr("All jobs are done. This program is going to be closed."),
                    60
                )
                ret = qbox.exec()
                if ret != QMessageBox.StandardButton.Cancel:
                    QCoreApplication.quit() # Exit
            case TodoWhenDoneEnum.SUSPEND.value:
                qbox = TimedMessageBox(
                    self.tr("Suspending in 1 minute"),
                    self.tr("All jobs are done. The computer is going to be suspended."),
                    60
                )
                ret = qbox.exec()
                if ret != QMessageBox.StandardButton.Cancel:
                    if sys.platform == 'win32':
                        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
                    else:
                        os.system('sudo systemctl suspend')
            case TodoWhenDoneEnum.SHUTDOWN.value:
                qbox = TimedMessageBox(
                    self.tr( "Shutting Down in 1 minute"),
                    self.tr("All jobs are done. The computer is shutting down. "),
                    60
                )
                ret = qbox.exec()
                if ret != QMessageBox.StandardButton.Cancel:
                    if sys.platform == 'win32':
                        os.system("shutdown /s /t 1")
                    else:
                        self.stop()
                        os.system('sudo shutdown now')

        # Doing nothing.
        self.processing = False
        # self.start_all_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        # self.add_file_button.setEnabled(True)
        self.clear_all_button.setEnabled(True)
        # 显示所有任务完成的通知
        InfoBar.success(
            self.tr("全部完成"),
            self.tr("所有任务已处理完成"),
            duration=3000,
            position=InfoBarPosition.BOTTOM,
            parent=self
        )

    def on_add_file(self):
        """添加文件按钮点击事件"""
        # 构建文件过滤器字符串
        video_formats = [f"*.{fmt.value}" for fmt in SupportedVideoFormats]
        audio_formats = [f"*.{fmt.value}" for fmt in SupportedAudioFormats]
        match self.task_type_combo.currentText():
            case BatchTaskTypeEnum.SOFT.value:  # Create soft sub video
                filter_str = f"{self.tr('视频文件')} ({' '.join(video_formats)})"
                task_type = Task.Type.SUBTITLE
                soft_sub = True
            case BatchTaskTypeEnum.HARD.value:  # Create hard sub video
                filter_str = f"{self.tr('视频文件')} ({' '.join(video_formats)})"
                task_type = Task.Type.SUBTITLE
                soft_sub = False
            case BatchTaskTypeEnum.TRANSCRIBE.value:  # Create transcription
                # 音频/视频生成字幕
                filter_str = f"{self.tr('音频文件或视频文件')} ({' '.join(audio_formats + video_formats)})"
                task_type = Task.Type.TRANSCRIBE
                soft_sub = True
            case BatchTaskTypeEnum.TRANSLATE.value:   # Transcribe + Translate
                filter_str = f"{self.tr('音频文件或视频文件')} ({' '.join(audio_formats + video_formats)})"
                task_type = Task.Type.TRANSLATE
                soft_sub = True
            case _:
                pass

        files, _ = QFileDialog.getOpenFileNames(self, self.tr("选择文件"), cfg.last_open_dir.value , filter_str)
        for file_path in files:
            self.create_task(file_path, task_type, soft_sub)
            
        # Save the files' directory for later use
        if files:
            file_dir = str( Path(files[0]).parent )
            if file_dir != cfg.last_open_dir.value:
                cfg.set( cfg.last_open_dir, file_dir, True)

    def create_task(self, file_path, task_type: Task.Type, soft_sub: bool):
        """创建新任务"""
        # 检查文件是否已存在
        for task in self.tasks:
            if Path(task.file_path).resolve() == Path(file_path).resolve():
                InfoBar.warning(
                    self.tr("添加失败"),
                    self.tr("该文件已存在于任务列表中"),
                    duration=3000,
                    position=InfoBarPosition.BOTTOM,
                    parent=self
                )
                return
        
        need_translate = False
        need_video = False
        match task_type:
            case Task.Type.SUBTITLE:
                need_video = True
                need_translate = not (cfg.translate_method.value == TranslateMethodEnum.NONE)
            case Task.Type.TRANSCRIBE:
                need_video = False
                need_translate = False
            case Task.Type.TRANSLATE:
                need_video = cfg.need_video.value
                need_translate = True
        
        create_thread = CreateTaskThread(
                            file_path,
                            task_type,
                            need_translate,
                            cfg.translate_method.value,
                            soft_sub,
                            need_video,
                        )
        create_thread.finished.connect(self.add_task_card)
        create_thread.finished.connect(lambda: self.cleanup_thread(create_thread))
        self.create_threads.append(create_thread)
        create_thread.start()

    def cleanup_thread(self, thread):
        """清理完成的线程"""
        if thread in self.create_threads:
            self.create_threads.remove(thread)
            thread.deleteLater()
        
    def add_task_card(self, task: Task):
        """添加新的任务卡片"""
        task_card = TaskInfoCard(self)
        task_card.set_task(task)
        task_card.remove.connect(self.remove_task_card)
        self.task_cards.append(task_card)
        self.tasks.append(task)
        self.scroll_layout.addWidget(task_card)

        # 当有任务时禁用任务类型选择
        # self.task_type_combo.setEnabled(False)

        # 显示成功提示
        InfoBar.success(
            self.tr("添加成功"),
            self.tr(f"已添加视频:") + task.video_info.file_name,
            duration=2000,
            position=InfoBarPosition.BOTTOM,
            parent=self
        )
        self.update_win_title()

        # 检查 任务是否为最后一个，如果是则发出信号
        if self.file_list:      # It's batch processing from command line.
            if task.file_path == self.file_list[len(self.file_list)-1]:
                self.file_list = None
                

    def remove_task_card(self, task_card):
        """移除任务卡片"""
        if task_card in self.task_cards:
            # 如果任务正在处理中,不允许删除
            if not task_card.task.status in NOT_RUNNING_TASKS:
                InfoBar.warning(
                    self.tr("无法删除"),
                    self.tr("正在处理的任务无法删除"),
                    duration=2000,
                    position=InfoBarPosition.BOTTOM,
                    parent=self
                )
                return

            self.task_cards.remove(task_card)
            self.tasks.remove(task_card.task)
            self.scroll_layout.removeWidget(task_card)
            task_card.deleteLater()

            # 显示删除成功的通知
            InfoBar.success(
                self.tr("删除成功"),
                self.tr(f"已删除任务:") + task_card.task.video_info.file_name,
                duration=2000,
                position=InfoBarPosition.BOTTOM,
                parent=self
            )

            # 当没有任务时启用任务类型选择
            # if len(self.task_cards) == 0:  # 因为当前任务还未被移除
            #   self.task_type_combo.setEnabled(True)

    def dragEnterEvent(self, event):
        """拖拽进入事件处理"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """拖拽放下事件处理"""
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if not os.path.isfile(file_path):
                continue

            file_ext = os.path.splitext(file_path)[1][1:].lower()

            # 根据任务类型检查文件格式
            match self.task_type_combo.currentText():
                case BatchTaskTypeEnum.HARD.value:
                    # Create hard sub video
                    supported_formats = {fmt.value for fmt in SupportedVideoFormats}
                    task_type = Task.Type.SUBTITLE
                    soft_sub = False
                case BatchTaskTypeEnum.SOFT.value:
                    # Create soft sub video
                    supported_formats = {fmt.value for fmt in SupportedVideoFormats}
                    task_type = Task.Type.SUBTITLE
                    soft_sub = True
                case BatchTaskTypeEnum.TRANSLATE.value:
                    # Create Optimize+Translate / Single Sentence Translate / Google Translate sub
                    supported_formats = {fmt.value for fmt in SupportedVideoFormats} | {fmt.value for fmt in SupportedAudioFormats}
                    task_type = Task.Type.TRANSLATE
                    soft_sub = True
                case BatchTaskTypeEnum.TRANSCRIBE.value:
                    # Create transcrptions only
                    supported_formats = {fmt.value for fmt in SupportedVideoFormats} | {fmt.value for fmt in SupportedAudioFormats}
                    task_type = Task.Type.TRANSCRIBE
                    soft_sub = True
            
            if file_ext in supported_formats:
                self.create_task(file_path, task_type, soft_sub)
            else:
                error_msg = self.tr("请拖入视频文件") if task_type in [ BatchTaskTypeEnum.SOFT or BatchTaskTypeEnum.HARD ] else self.tr("请拖入音频或视频文件")
                InfoBar.error(
                    self.tr("格式错误") + file_ext,
                    error_msg,
                    duration=3000,
                    parent=self
                )
                

    def closeEvent(self, event):
        """关闭事件处理"""
        self.cancel_batch_process()
        super().closeEvent(event)

    def addFiles(self, fileList: list):
        self.file_list = fileList
        for file_str in fileList:
            if not os.path.isfile(file_str):
                InfoBar.error(
                    self.tr("File not exist."),
                    self.tr(f"The file {file_str} is not a valid file."),
                    duration= 5000,
                    parent=self,
                )
                continue
            file_ext = os.path.splitext(file_str)[1][1:].lower()

            # 根据任务类型检查文件格式
            match self.task_type_combo.currentText():
                case BatchTaskTypeEnum.HARD.value:
                    # Create hard sub video
                    supported_formats = {fmt.value for fmt in SupportedVideoFormats}
                    task_type = Task.Type.SUBTITLE
                    soft_sub = False
                case BatchTaskTypeEnum.SOFT.value:
                    # Create soft sub video
                    supported_formats = {fmt.value for fmt in SupportedVideoFormats}
                    task_type = Task.Type.SUBTITLE
                    soft_sub = True
                case BatchTaskTypeEnum.TRANSLATE.value:
                    # Create Optimize+Translate / Single Sentence Translate / Google Translate sub
                    supported_formats = {fmt.value for fmt in SupportedVideoFormats} | {fmt.value for fmt in SupportedAudioFormats}
                    task_type = Task.Type.TRANSLATE
                    soft_sub = True
                case BatchTaskTypeEnum.TRANSCRIBE.value:
                    # Create transcrptions only
                    supported_formats = {fmt.value for fmt in SupportedVideoFormats} | {fmt.value for fmt in SupportedAudioFormats}
                    task_type = Task.Type.TRANSCRIBE
                    soft_sub = True
            
            if file_ext in supported_formats:
                self.create_task(file_str, task_type, soft_sub)
            else:
                InfoBar.error(
                    self.tr("File Format Error"),
                    self.tr(f"This file, {file_str}, has a wrong extension."),
                    duration=5000,
                    parent=self,
                )
        
    def update_win_title(self, whatever = None):
        # Update windows title when the task status is changed.
        status = {}
        status_text = ""
        for task in self.tasks:
            task_value = status.get(task.status.value)
            if task_value:
                # The key already exists
                status[task.status.value] = task_value + 1
            else:
                # No key yet. Set 1 up.
                status[task.status.value] = 1
        
        # Build the status string after all tasks processed.
        for key in status:
            t = self.tr("task") if status[key] == 1 else self.tr("tasks")
            status_text += self.tr(f"{status[key]} {t} {key}, ")
        
        if status_text:
            parts = status_text.rsplit(",", 1)
            status_text = self.tr("Currently ") + ".".join(parts)  # Replace last "," to be "."
        else:
            status_text = self.tr("Currently the task list is empty.")
        
        if whatever and type(whatever) == str:    # Additional info.
            status_text = whatever + " " + status_text
        
        final_text = self.org_title + " - " + status_text
        self.setWindowTitle(final_text)
        self.win_title_update.emit(final_text)
        

class TaskInfoCard(CardWidget):
    finished = pyqtSignal(Task)
    remove = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.task: Task = None
        self.setup_ui()
        self.setup_signals()
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.installEventFilter(ToolTipFilter(self, 100, ToolTipPosition.BOTTOM))

        self.transcript_thread = None
        self.subtitle_thread = None
        self.subtitle_window = None  # 添加成员变量

    def setup_ui(self):
        self.setFixedHeight(180)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(15, 5, 15, 5)
        self.layout.setSpacing(10)

        # 设置缩略图
        self.setup_thumbnail()
        # 设置视频信息
        self.setup_info_layout()
        # 设置按钮
        self.setup_button_layout()

        self.task_state = IconInfoBadge.info(FIF.REMOVE, self, target=self.video_title,
                                             position=InfoBadgePosition.TOP_RIGHT)

    def setup_thumbnail(self):
        self.video_thumbnail = QLabel(self)
        self.video_thumbnail.setFixedSize(208, 117)
        self.video_thumbnail.setStyleSheet("background-color: #1E1F22;")
        self.video_thumbnail.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.video_thumbnail, 0, Qt.AlignLeft)

    def setup_info_layout(self):
        self.info_layout = QVBoxLayout()
        self.info_layout.setContentsMargins(3, 8, 3, 8)
        self.info_layout.setSpacing(5)

        # 设置视频标题
        self.video_title = BodyLabel(self.tr("未选择视频"), self)
        self.video_title.setFont(QFont("Microsoft YaHei", 12))
        self.video_title.setWordWrap(True)
        self.info_layout.addWidget(self.video_title, alignment=Qt.AlignTop)

        # 设置视频详细信息
        self.details_layout1 = QHBoxLayout()
        self.details_layout1.setSpacing(10)
        self.details_layout2 = QHBoxLayout()
        self.details_layout2.setSpacing(10)

        self.resolution_info = self.create_pill_button(self.tr("画质"), 120)
        self.file_size_info = self.create_pill_button(self.tr("文件大小"), 120)
        self.duration_info = self.create_pill_button(self.tr("时长"), 120)
        self.video_codec = self.create_pill_button(self.tr("视频码"), 120)
        self.audio_codec = self.create_pill_button(self.tr("音频码"), 120)
        
        self.portrait_mode = SwitchButton(self, indicatorPos = IndicatorPosition.RIGHT)
        self.portrait_mode.setOnText(self.tr("竖屏"))
        self.portrait_mode.setOffText(self.tr("横屏"))
        self.portrait_background = PushButton(self.tr("背景：无"), parent=self)
        self.portrait_background.hide()
        
        
        self.progress_ring = ProgressRing(self)
        self.progress_ring.setFixedSize(20, 20)
        self.progress_ring.setStrokeWidth(4)
        self.progress_ring.hide()

        self.details_layout1.addWidget(self.resolution_info)
        self.details_layout1.addWidget(self.file_size_info)
        self.details_layout1.addWidget(self.duration_info)
        self.details_layout1.addWidget(self.progress_ring)
        self.details_layout1.addStretch(1)
        self.details_layout2.addWidget(self.video_codec)
        self.details_layout2.addWidget(self.audio_codec)
        self.details_layout2.addWidget(self.portrait_mode)
        self.details_layout2.addWidget(self.portrait_background)
        
        self.details_layout2.addStretch(1)
        self.info_layout.addLayout(self.details_layout1)
        self.info_layout.addLayout(self.details_layout2)
        self.layout.addLayout(self.info_layout)

    def create_pill_button(self, text, width):
        button = PillPushButton(text, self)
        button.setCheckable(False)
        setFont(button, 11)
        button.setFixedWidth(width)
        return button

    def setup_button_layout(self):
        self.button_layout = QVBoxLayout()
        self.preview_subtitle_button = PushButton(self.tr("预览字幕"), self)
        self.open_folder_button = PushButton(self.tr("打开文件夹"), self)
        self.start_button = PrimaryPushButton(self.tr("未开始转录"), self)
        self.button_layout.addWidget(self.preview_subtitle_button)
        self.button_layout.addWidget(self.open_folder_button)
        self.button_layout.addWidget(self.start_button)

        self.start_button.setDisabled(True)

        button_widget = QWidget()
        button_widget.setLayout(self.button_layout)
        button_widget.setFixedWidth(200)
        self.layout.addWidget(button_widget)

    def mouseDoubleClickEvent(self, event):
        """双击事件处理"""
        self.open_subtitle()

    def update_info(self, video_info: VideoInfo):
        """更新视频信息显示"""
        self.video_title.setText(video_info.file_name + '\n' + video_info.file_path)
        self.resolution_info.setText(self.tr("画质: ") + f"{video_info.width}x{video_info.height}")
        file_size_mb = os.path.getsize(self.task.file_path) / 1024 / 1024
        self.file_size_info.setText(self.tr("大小: ") + f"{file_size_mb:.1f} MB")
        duration = datetime.timedelta(seconds=int(video_info.duration_seconds))
        self.duration_info.setText(self.tr("时长: ") + str(duration))
        self.video_codec.setText(self.tr("视频码 ") + video_info.video_codec)
        self.audio_codec.setText(self.tr("音频码 ") + video_info.audio_codec)
        # self.start_button.setDisabled(False)
        self.update_thumbnail(video_info.thumbnail_path)
        if self.task and self.task.type == Task.Type.SUBTITLE and not cfg.soft_subtitle.value:
            # When need to hard code subtitles, enable it.
            self.portrait_mode.setDisabled(False)
        else:
            # Other cases, disable it.
            self.portrait_mode.setDisabled(True)
            
        self.update_tooltip()

    def update_tooltip(self):
        """更新tooltip"""
        # 设置整体tooltip
        
        strategy_text = ""
        if self.task.need_translate:
            match self.task.translate_method:
                case TranslateMethodEnum.OPTIMIZE:
                    strategy_text += self.tr("翻译方式：智能多线程优化+翻译，目标: "
                                            ) + str(self.task.target_language) + " "
                case TranslateMethodEnum.SINGLE_SENTENCE:
                    strategy_text += self.tr("翻译方式：智能单线程单句翻译，目标: "
                                             ) + self.task.target_language + " "
                case TranslateMethodEnum.GOOGLE:
                    strategy_text += self.tr("翻译方式：谷歌批量翻译，目标: "
                                             ) + self.task.target_language + " "

            strategy_text += self.tr(", 使用的LLM 模型: ") + self.task.llm_model + ""

        # if self.task.need_video:
        #     if self.task.soft_subtitle:
        #         strategy_text += self.tr(" 任务：视频加软字幕 ")
        #     else:
        #         strategy_text += self.tr(" 任务：视频加硬字幕 ")
        # else:   # No video
        #     if self.task.type == Task.Type.TRANSCRIBE:
        #         strategy_text += self.tr(" 任务：语言转录 ")
        #     elif self.task.type == Task.Type.TRANSLATE:
        #         strategy_text += self.tr(" 任务：生成字幕文件 ")

        if self.task.portrait:
            strategy_text += self.tr(" 竖屏模式：开启 ")
        if self.task.portrait_background:
            strategy_text += "\n" + self.tr(" 竖屏背景: ") + self.task.portrait_background

        tooltip = self.tr("任务类型: ") + self.task.type.value + "  " + self.tr("转录模型: ") + self.task.transcribe_model.value + "\n"
        if len(self.task.file_path) > 100:
            tooltip += self.tr("文件: ") + self.task.file_path[:50] + "..." + Path(self.task.file_path).name + "\n"
        else:
            tooltip += self.tr("文件: ") + self.task.file_path + '\n'
        tooltip += strategy_text + "\n"
        tooltip += self.tr("任务状态: ") + self.task.status.value
        self.setToolTip(tooltip)

    def update_thumbnail(self, thumbnail_path):
        """更新视频缩略图"""
        if not Path(thumbnail_path).exists() or cfg.no_thumbnail.value:
            thumbnail_path = RESOURCE_PATH / "assets" / "audio-thumbnail.png"

        pixmap = QPixmap(str(thumbnail_path)).scaled(
            self.video_thumbnail.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.video_thumbnail.setPixmap(pixmap)

    def setup_signals(self):
        self.start_button.clicked.connect(self.start)
        self.open_folder_button.clicked.connect(self.on_open_folder_clicked)
        self.preview_subtitle_button.clicked.connect(self.open_subtitle)
        self.portrait_mode.checkedChanged.connect(self.on_portrait_mode_changed)
        self.portrait_background.clicked.connect(self.on_portrait_background_clicked)

    def on_portrait_mode_changed(self, checked):
        """竖屏模式切换"""
        self.task.portrait = checked
        if checked:
            self.portrait_background.show()
        else:
            self.portrait_background.hide()
        self.update_tooltip()

    def on_portrait_background_clicked(self):
        picture_formats = [f"*.{fmt.value}" for fmt in SupportedImageFormats]
        file, _ = QFileDialog.getOpenFileName(self, self.tr("选择背景图片"),
                                               cfg.last_open_dir.value,
                                               self.tr("Image Files (") + " ".join(picture_formats) + ")")
        if not file:
            return
        file_path = Path(file)
        if not file_path.exists():
            InfoBar.warning(
                self.tr("文件不存在"),
                self.tr("请重新选择"),
                duration=3000,
            )
            return

        self.portrait_background.setText(self.tr("背景：") + file_path.name)
        self.task.portrait_background = file
        self.update_tooltip()

    def show_context_menu(self, pos):
        """显示右键菜单"""
        menu = RoundMenu(parent=self)
        
        # 添加打开字幕选项
        open_subtitle_action = Action(FIF.DOCUMENT, self.tr("打开字幕（双击）"), self)
        open_subtitle_action.triggered.connect(self.open_subtitle)
        menu.addAction(open_subtitle_action)

        # 添加菜单项
        open_folder_action = Action(FIF.FOLDER, self.tr("打开文件夹"), self)
        open_folder_action.triggered.connect(self.on_open_folder_clicked)
        menu.addAction(open_folder_action)
        
        reprocess_action = Action(FIF.SYNC, self.tr("重新处理"), self)
        reprocess_action.triggered.connect(self.reprocess)
        menu.addAction(reprocess_action)

        cancel_action = Action(FIF.CANCEL, self.tr("取消/停止任务"), self)
        cancel_action.triggered.connect(self.cancel)
        menu.addAction(cancel_action)

        delete_action = Action(FIF.DELETE, self.tr("删除任务"), self)
        delete_action.triggered.connect(lambda: self.remove.emit(self))
        menu.addAction(delete_action)
        
        # 显示菜单
        menu.exec_(self.mapToGlobal(pos))

    def reprocess(self):
        self.status = Task.Status.PENDING
        self.start()

    def open_subtitle(self):
        """打开字幕优化界面"""
        preview_subtitle_path = Path(self.task.original_subtitle_save_path)
        if self.task.result_subtitle_save_path and Path(self.task.result_subtitle_save_path).exists():
            preview_subtitle_path = Path(self.task.result_subtitle_save_path)
        # The original sub might be word-split and not full sentence sub.
        # elif self.task.original_subtitle_save_path and Path(self.task.original_subtitle_save_path).exists():
        #     preview_subtitle_path = Path(self.task.original_subtitle_save_path)
        else:
            # Open file dialog
            subtitle_formats = [f"*.{fmt.value}" for fmt in SupportedSubtitleFormats]
            filter_str = f"{self.tr('字幕文件')} ({' '.join(subtitle_formats)})"
            file, _ = QFileDialog.getOpenFileName( self, self.tr("选择字幕文件"), cfg.last_open_dir.value, filter_str)
            if file and Path(file).exists():
                preview_subtitle_path = Path(file)
            else:
                return

        if preview_subtitle_path.exists():
            self.subtitle_window = QWidget()
            self.subtitle_window.setWindowTitle(self.tr("字幕预览"))
            subtitle_interface = SubtitleOptimizationInterface(self.subtitle_window)
            subtitle_interface.load_subtitle_file(str(preview_subtitle_path))
            subtitle_interface.remove_widget()
            layout = QHBoxLayout(self.subtitle_window)
            layout.setContentsMargins(3, 0, 3, 3)
            layout.addWidget(subtitle_interface)
            
            self.subtitle_window.resize(1000, 800)

            theme = 'dark' if isDarkTheme() else 'light'
            with open(RESOURCE_PATH / "assets" / "qss" / theme / "demo.qss", encoding='utf-8') as f:
                self.subtitle_window.setStyleSheet(f.read())
            self.subtitle_window.show()
        else:
            InfoBar.warning(
                self.tr("警告"),
                self.tr("字幕文件不存在"), 
                duration=2000,
                parent=self
            )

    def delete(self):
        self.remove.emit(self)

    def cancel(self):
        """修改任务状态"""
        self.stop()
        self.task.status = Task.Status.CANCELED
        self.update_tooltip()
        if not self.task.status in NOT_RUNNING_TASKS:
            # If the task is running
            self.finished.emit(self.task)

    def stop(self):
        """停止转录"""
        if self.transcript_thread:
            self.transcript_thread.allow_running[0] = False
            # self.transcript_thread.quit()
            # self.transcript_thread.terminate()
        if self.subtitle_thread:
            self.subtitle_thread.allow_running[0] = False
            # self.subtitle_thread.quit()
            # self.subtitle_thread.terminate()

        self.reset_ui()

        InfoBar.success(
            self.tr("已取消"),
            self.tr("任务已取消"),
            duration=2000,
            parent=self
        )

    def start(self):
        """开始转录按钮点击事件"""
        # 获取任务类型
        if self.task.status == Task.Status.COMPLETED:
            InfoBar.warning(
                self.tr("警告"),
                self.tr("该任务已完成"),
                duration=2000,
                parent=self
            )
            return

        self.task.status = Task.Status.PENDING
        self.progress_ring.show()
        self.progress_ring.setValue(100)
        # self.start_button.setDisabled(True)
        self.preview_subtitle_button.setDisabled(True)
        self.task_state.setLevel(InfoLevel.WARNING)
        self.task_state.setIcon(FIF.SYNC)
        self.progress_ring.resume()

        # 开始转录过程
        match self.task.type:
            case Task.Type.TRANSCRIBE:
                self.transcript_thread = TranscriptThread(self.task)
                self.transcript_thread.finished.connect(self.on_finished)
                self.transcript_thread.progress.connect(self.on_progress)
                self.transcript_thread.error.connect(self.on_error)
                self.transcript_thread.start()
            case Task.Type.SUBTITLE | Task.Type.TRANSLATE:
                self.subtitle_thread = SubtitlePipelineThread(self.task)
                self.subtitle_thread.finished.connect(self.on_finished)
                self.subtitle_thread.progress.connect(self.on_progress)
                self.subtitle_thread.error.connect(self.on_error)
                self.subtitle_thread.start()
            case _:
                self.on_error(self.tr("任务类型错误"))
        

    def on_open_folder_clicked(self):
        """打开文件夹按钮点击事件"""
        if self.task and Path(self.task.file_path).exists():
            if sys.platform == "win32":
                os.startfile(str( Path(self.task.file_path).parent) )
            elif sys.platform == "darwin":  # macOS
                subprocess.run(["open", str( Path(self.task.file_path).parent) ])
            else:  # Linux
                subprocess.run(["xdg-open", str( Path(self.task.file_path).parent) ])
        else:
            if self.task:
                # Task exists, so the file is missing.
                InfoBar.warning(
                    self.tr("警告"),
                    self.tr(f"找不到文件 {self.task.file_path}"),
                    duration=2000,
                    parent=self
                )
            else:
                # Task not exists yet.
                InfoBar.warning(
                    self.tr("警告"),
                    self.tr(f"找不到文件{self.task.file_path}"),
                    duration=2000,
                    parent=self
                )

    def is_canceled(self):
        if self.transcript_thread:
            allow_running = self.transcript_thread.allow_running[0]
        elif self.subtitle_thread:
            allow_running = self.subtitle_thread.allow_running[0]
        else:
            allow_running = True
        return not allow_running

    def on_progress(self, value, message):
        """更新转录进度"""
        self.start_button.setText(message)
        self.progress_ring.setValue(value)
        self.update_tooltip()

    def on_error(self, error):
        """处理转录错误"""
        self.reset_ui()
        
        if self.is_canceled():
            # An error by cancelling.
            self.task_state.setLevel(InfoLevel.WARNING)
            self.progress_ring.setValue(0)
            self.task.status = Task.Status.CANCELED
            self.update_tooltip()
        else:
            # Other errors.
            self.task_state.setLevel(InfoLevel.ERROR)
            self.task_state.setIcon(FIF.CLOSE)
            self.progress_ring.error()
            self.task.status = Task.Status.FAILED

            self.update_tooltip()
            self.error.emit(error)
            InfoBar.error(
                self.tr("转录失败"),
                self.tr(error),
                duration=5000,
                parent=self
            )

    def on_finished(self, task):
        """转录完成处理"""
        self.reset_ui()
        self.task_state.setLevel(InfoLevel.SUCCESS)
        self.task_state.setIcon(FIF.ACCEPT)
        self.update_tooltip()

        self.task.status = Task.Status.COMPLETED
        self.finished.emit(task)

    def reset_ui(self):
        """重置UI状态"""
        # self.start_button.setEnabled(True)
        # self.start_button.setText(self.tr("开始转录"))
        self.preview_subtitle_button.setEnabled(True)
        self.progress_ring.setValue(100)
        self.task_state.setLevel(InfoLevel.INFOAMTION)
        self.task_state.setIcon(FIF.REMOVE)
        self.update_tooltip()

    def set_task(self, task):
        """设置任务并更新UI"""
        self.task = task
        self.update_info(self.task.video_info)
        self.reset_ui()


class UpdateTimer(QThread):
    """
    This emit signal every 5 seconds after batch processing starts.
    """
    updateSignal = pyqtSignal()
    run_timer = True
    
    def run(self):
        self.run_timer = True
        while self.run_timer:
            self.sleep(5)
            self.updateSignal.emit()

    def stop(self):
        self.run_timer = False

        