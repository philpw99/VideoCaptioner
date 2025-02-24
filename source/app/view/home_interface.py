from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QStackedWidget, QVBoxLayout, QSizePolicy
from qfluentwidgets import SegmentedWidget

from ..core.entities import Task
from .subtitle_optimization_interface import SubtitleOptimizationInterface
from .task_creation_interface import TaskCreationInterface
from .transcription_interface import TranscriptionInterface
from .video_synthesis_interface import VideoSynthesisInterface


class HomeInterface(QWidget):
    # 定义一个信号，当任务完成时发出
    finished = pyqtSignal(Task)

    def __init__(self, parent=None):
        super().__init__(parent)

        # 设置对象名称和样式
        self.setObjectName('HomeInterface')
        self.setStyleSheet("""
            HomeInterface{background: #333}
        """)  # Dark grey

        # 创建分段控件和堆叠控件
        self.pivot = SegmentedWidget(self)
        self.pivot.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

        self.stackedWidget = QStackedWidget(self)
        self.vBoxLayout = QVBoxLayout(self)

        # 添加子界面
        self.task_creation_interface = TaskCreationInterface(self)
        self.transcription_interface = TranscriptionInterface(self)
        self.subtitle_optimization_interface = SubtitleOptimizationInterface(self)
        self.video_synthesis_interface = VideoSynthesisInterface(self)

        self.addSubInterface(self.task_creation_interface, 'TaskCreationInterface', self.tr('任务创建'))
        self.addSubInterface(self.transcription_interface, 'TranscriptionInterface', self.tr('语音转录/日志'))
        self.addSubInterface(self.subtitle_optimization_interface, 'SubtitleOptimizationInterface',
                             self.tr('字幕优化与翻译'))
        self.addSubInterface(self.video_synthesis_interface, 'VideoSynthesisInterface', self.tr('字幕视频合成'))

        self.vBoxLayout.addWidget(self.pivot)
        self.vBoxLayout.addWidget(self.stackedWidget)
        self.vBoxLayout.setContentsMargins(30, 10, 30, 30)

        self.stackedWidget.currentChanged.connect(self.onCurrentIndexChanged)
        self.stackedWidget.setCurrentWidget(self.task_creation_interface)
        self.pivot.setCurrentItem('TaskCreationInterface')

        self.task_creation_interface.finished.connect(self.switch_to_transcription)
        self.transcription_interface.finished.connect(self.switch_to_subtitle_optimization)
        self.subtitle_optimization_interface.finished.connect(self.switch_to_video_synthesis)

    def switch_to_transcription(self, task: Task | None):
        # 切换到转录界面
        self.transcription_interface.set_task(task)
        self.transcription_interface.process()
        self.stackedWidget.setCurrentWidget(self.transcription_interface)
        self.pivot.setCurrentItem('TranscriptionInterface')

    def switch_to_subtitle_optimization(self, task: Task | None):
        # 切换到字幕优化/翻译界面 但不执行
        self.subtitle_optimization_interface.set_task(task)
        if task.need_translate:
            self.subtitle_optimization_interface.process()
        self.stackedWidget.setCurrentWidget(self.subtitle_optimization_interface)
        self.pivot.setCurrentItem('SubtitleOptimizationInterface')

    def switch_to_video_synthesis(self, task: Task | None):
        # 切换到视频合成界面 但不执行
        self.video_synthesis_interface.set_task(task)
        if task.type == Task.Type.SUBTITLE:
            self.video_synthesis_interface.process()
        self.stackedWidget.setCurrentWidget(self.video_synthesis_interface)
        self.pivot.setCurrentItem('VideoSynthesisInterface')

    def addSubInterface(self, widget: QWidget, objectName: str, text: str):
        # 添加子界面到堆叠控件和分段控件
        widget.setObjectName(objectName)
        self.stackedWidget.addWidget(widget)
        self.pivot.addItem(
            routeKey=objectName,
            text=text,
            onClick=lambda: self.stackedWidget.setCurrentWidget(widget),
        )

    def onCurrentIndexChanged(self, index):
        # 当堆叠控件的当前索引改变时，更新分段控件的当前项
        widget = self.stackedWidget.widget(index)
        if widget:
            self.pivot.setCurrentItem(widget.objectName())

    def closeEvent(self, event):
        # 关闭事件，关闭所有子界面
        self.task_creation_interface.close()
        self.transcription_interface.close()
        self.subtitle_optimization_interface.close()
        self.video_synthesis_interface.close()
        super().closeEvent(event)
