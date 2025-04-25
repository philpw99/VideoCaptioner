import os
import psutil
from PyQt5.QtCore import QUrl, QSize, QThread
from PyQt5.QtGui import QIcon, QDesktopServices
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import (NavigationAvatarWidget, NavigationItemPosition, MessageBox, FluentWindow, InfoBar,
                            SplashScreen)

from ..config import GITHUB_REPO_URL, ASSETS_PATH
from ..common.config import cfg
from ..core.thread.version_manager_thread import VersionManager
from .subtitle_style_interface import SubtitleStyleInterface
from .batch_process_interface import BatchProcessInterface
from .home_interface import HomeInterface
from .setting_interface import SettingInterface
from ..components.DonateDialog import DonateDialog
from ..core.entities import SubtitleLayoutEnum, TodoWhenDoneEnum, Task, BatchTaskTypeEnum, TranslateMethodEnum

LOGO_PATH = ASSETS_PATH / "logo.png"

class MainWindow(FluentWindow):

    def __init__(self, argv = []):
        super().__init__()
        # change the enum values first
        self.enums_translate()
        self.announcement = ""
        self.newVersion = ""
        self.initWindow()

        # 创建子界面
        self.homeInterface = HomeInterface(self)
        self.settingInterface = SettingInterface(self)
        self.subtitleStyleInterface = SubtitleStyleInterface(self)
        self.batchProcessInterface = BatchProcessInterface(self)

        # 初始化版本管理器
        self.versionManager = VersionManager()
        self.versionManager.newVersionAvailable.connect(self.onNewVersion)
        self.versionManager.announcementAvailable.connect(self.onAnnouncement)

        # 创建版本检查线程
        if cfg.checkUpdateAtStartUp.value:
            self.versionThread = QThread()
            self.versionManager.moveToThread(self.versionThread)
            self.versionThread.started.connect(self.versionManager.performCheck)
            self.versionThread.start()

        # 初始化导航界面
        self.initNavigation()
        self.splashScreen.finish()

        # 注册退出处理， 清理进程
        import atexit
        atexit.register(self.stop)
        
        # 处理 命令行 文件参数
        if argv:
            self.switchTo(self.batchProcessInterface)
            # Set the program to exit after the batch is done.
            self.batchProcessInterface.todo_when_done_combobox.setCurrentText(TodoWhenDoneEnum.EXIT.value)
            # Add files to the batch
            self.batchProcessInterface.addFiles(argv)
            # Once all the files are added, start the process
            self.batchProcessInterface.add_tasks_finished.connect(self.on_add_file_finished)

        # Update windows title
        self.batchProcessInterface.win_title_update.connect(self.setWindowTitle)

    def initNavigation(self):
        """初始化导航栏"""
        # 添加导航项
        self.addSubInterface(self.homeInterface, FIF.HOME, self.tr('主页'))
        self.addSubInterface(self.batchProcessInterface, FIF.VIDEO, self.tr('批量处理'))
        self.addSubInterface(self.subtitleStyleInterface, FIF.FONT, self.tr('字幕样式'))

        self.navigationInterface.addSeparator()

        # 在底部添加自定义小部件
        self.navigationInterface.addItem(routeKey='avatar', text='GitHub', icon=FIF.GITHUB, onClick=self.onGithubDialog, position=NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.settingInterface, FIF.SETTING, self.tr('Settings'), NavigationItemPosition.BOTTOM)

        # 设置默认界面
        self.switchTo(self.homeInterface)

    def switchTo(self, interface):
        if interface.windowTitle():
            self.setWindowTitle(interface.windowTitle())
        else:
            self.setWindowTitle(self.tr('卡卡字幕助手 -- VideoCaptioner'))
        self.stackedWidget.setCurrentWidget(interface, popOut=False)

    def initWindow(self):
        """初始化窗口"""
        self.resize(1280, 800)
        self.setMinimumWidth(800)
        self.setWindowIcon(QIcon(str(LOGO_PATH)))
        self.setWindowTitle(self.tr('卡卡字幕助手 -- VideoCaptioner'))

        self.setMicaEffectEnabled(cfg.get(cfg.micaEnabled))

        # 创建启动画面
        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(106, 106))
        self.splashScreen.raise_()

        # 设置窗口位置, 居中
        desktop = QApplication.desktop().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        self.show()
        QApplication.processEvents()

    def onGithubDialog(self):
        """打开GitHub"""
        w = MessageBox(
            self.tr('GitHub信息'),
            self.tr("VideoCaptioner 由本人在课余时间独立开发完成， 目前托管在GitHub上， 欢迎Star和Fork。" \
                + "项目诚然还有很多地方需要完善， 遇到软件的问题或者BUG欢迎提交Issue。\n\n" \
                + "主项目： https://github.com/WEIFENG2333/VideoCaptioner\n\n" \
                + "分支： https://github.com/philpw99/VideoCaptioner"
                ),
            self
        )
        w.yesButton.setText(self.tr('打开 GitHub'))
        w.cancelButton.setText(self.tr('支持作者'))
        if w.exec():
            QDesktopServices.openUrl(QUrl(GITHUB_REPO_URL))
        else:
            # 点击"支持作者"按钮时打开捐赠对话框
            donate_dialog = DonateDialog(self)
            donate_dialog.exec_()

    def onNewVersion(self, version, force_update, update_info, download_url):
        """新版本提示"""
        self.newVersion = self.tr(f"New version is out {version}\nDownload it here: {download_url}\nOr go to GitHub for the new release.")
        InfoBar.info(self.tr("New Version Available!"),
                     self.newVersion,
                     duration=10000,
                     parent=self
                    )
        # title = '发现新版本' if not force_update else '当前版本已停用'
        # content = f'发现新版本 {version}\n\n{update_info}'
        # w = MessageBox(title, content, self)
        # w.yesButton.setText('立即更新')
        # w.cancelButton.setText('稍后再说' if not force_update else '退出程序')
        # if w.exec():
        #     QDesktopServices.openUrl(QUrl(download_url))
        # if force_update:
        #     QApplication.quit()

    def onAnnouncement(self, content):
        """显示公告"""
        self.announcement = content
        InfoBar.info(self.tr("New Announcement!"),
                     content,
                     duration=10000,
                     parent=self
                    )
        # w = MessageBox('公告', content, self)
        # w.yesButton.setText('我知道了')
        # w.cancelButton.hide()
        # w.exec()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, 'splashScreen'):
            self.splashScreen.resize(self.size())

    def closeEvent(self, event):
        # 关闭所有子界面
        self.homeInterface.close()
        self.batchProcessInterface.close()
        self.subtitleStyleInterface.close()
        self.settingInterface.close()
        super().closeEvent(event)
        
        # # 强制退出应用程序
        # QApplication.quit()

        # # 确保所有线程和进程都被终止
        # import os
        # os._exit(0)
        
    def stop(self):
        # 找到 FFmpeg 进程并关闭
        process = psutil.Process(os.getpid())
        for child in process.children(recursive=True):
            child.kill()

    def on_add_file_finished(self):
        # Files are all added. Time to run them.
        self.batchProcessInterface.start_batch_process()
    
    def enums_translate(self):
        BatchTaskTypeEnum.TRANSCRIBE.setValue( self.tr("Transcribe Audio/Video") )
        BatchTaskTypeEnum.TRANSLATE.setValue( self.tr("Transcribe + Translate Audio/Video") )
        BatchTaskTypeEnum.SOFT.setValue( self.tr("Create Soft Subtitle Video") )
        BatchTaskTypeEnum.HARD.setValue( self.tr("Create Hard Subtitle Video") )
        BatchTaskTypeEnum.LOGO.setValue( self.tr("Add Logo or Video Processing"))
        
        SubtitleLayoutEnum.ONLY_ORIGINAL.setValue( self.tr("Original Only") )
        SubtitleLayoutEnum.ONLY_TRANSLATE.setValue( self.tr("Translated Only") )
        SubtitleLayoutEnum.ORIGINAL_ON_TOP.setValue( self.tr("Original on Top") )
        SubtitleLayoutEnum.TRANSLATE_ON_TOP.setValue( self.tr("Translated on Top"))
        
        TranslateMethodEnum.OPTIMIZE.setValue( self.tr("Optimize Translate") )
        TranslateMethodEnum.GOOGLE.setValue( self.tr("Google Translate") )
        TranslateMethodEnum.SINGLE_SENTENCE.setValue( self.tr("Single Sentence Translate") )
        TranslateMethodEnum.NONE.setValue( self.tr("No Translation") )

        TodoWhenDoneEnum.NOTHING.setValue( self.tr("Nothing"))
        TodoWhenDoneEnum.EXIT.setValue( self.tr("Exit The Program"))
        TodoWhenDoneEnum.SHUTDOWN.setValue( self.tr("Shutdown The Computer"))
        TodoWhenDoneEnum.SUSPEND.setValue( self.tr("Suspend The Computer"))
        
        Task.Status.CANCELED.setValue( self.tr("Canceled"))
        Task.Status.COMPLETED.setValue( self.tr("Completed"))
        Task.Status.DOWNLOADING.setValue( self.tr("Downloading"))
        Task.Status.FAILED.setValue( self.tr("Failed"))
        Task.Status.GENERATING.setValue( self.tr("Generating"))
        Task.Status.OPTIMIZING.setValue( self.tr("Optimizing/Translating"))
        Task.Status.PENDING.setValue( self.tr("Pending"))
        Task.Status.SYNTHESIZING.setValue( self.tr("Synthesizing"))
        Task.Status.TRANSCRIBING.setValue( self.tr("Transcribing"))
        Task.Status.TRANSCODING.setValue( self.tr("Transcoding"))
        Task.Status.TRANSLATING.setValue( self.tr("Translating"))
        Task.Status.WAITINGAUDIO.setValue( self.tr("Waiting for audio transcoding"))
        Task.Status.WAITINGTRANSLATE.setValue( self.tr("Waiting for translating."))
        Task.Status.WAITINGSYNTHESIS.setValue( self.tr("Waiting for video synthesis"))
        Task.Status.WAITINGTRANSCRIBE.setValue( self.tr("Waiting for transcripting"))

        Task.Source.FILE_IMPORT.setValue( self.tr("File Import"))
        Task.Source.URL_IMPORT.setValue( self.tr("URL Import"))
        
        Task.Type.SUBTITLE.setValue( self.tr("Add Subtitle To Video"))
        Task.Type.SYNTHESIS.setValue( self.tr("Combine Subtitle with Video"))
        Task.Type.TRANSCRIBE.setValue( self.tr("Get Subtitle From Video/Audio"))
        Task.Type.TRANSLATE.setValue(self.tr("Add Translated Sub To Video"))
        Task.Type.URL.setValue( self.tr("Download Video from URL then Add Subtitle"))