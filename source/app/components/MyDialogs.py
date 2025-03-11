from qfluentwidgets import MessageBoxBase, BodyLabel, LineEdit, TextEdit, ComboBox, FluentIcon as FIF, PushButton, InfoBar
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout
from ..core.entities import MovieDatabaseEnum, TranscribeModelEnum
from ..common.config import cfg
from ..core.utils.imdb import get_imdb_movie_info
from ..core.utils.douban import get_douban_movie_info

class LineInputDialog(MessageBoxBase):
    def __init__(self, title:str = None, content:str = None, parent = None):
        super().__init__(parent)
        if title:
            self.setWindowTitle(title)
        if content:
            self.contentLabel = BodyLabel(content, self)
            self.viewLayout.addWidget(self.contentLabel)
        self.inputLine = LineEdit(self)
        self.inputLine.setClearButtonEnabled(True)
        self.viewLayout.addWidget(self.inputLine)
        self.widget.setMinimumWidth(300)

class PromptSettingDialog(MessageBoxBase):
    old_prompt = ""
    summary = ""
    post_url = ""
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setup_ui()
        self.setup_value()
        self.setup_signal()
        self.old_prompt = self.prompt_input.toPlainText()
    
    def setup_ui(self):
        self.v_layout = QVBoxLayout()
        self.viewLayout.addLayout(self.v_layout)
        
        self.prompt_label = BodyLabel(self.tr("Prompt for Whisper:"), self)
        self.prompt_input = TextEdit(self)
        self.v_layout.addWidget(self.prompt_label)
        self.v_layout.addWidget(self.prompt_input)

        self.movie_info_layout = QHBoxLayout()
        self.movie_info_layout.setContentsMargins(0, 0, 10, 0)
        self.movie_info_layout.setSpacing(20)
        
        self.movie_info_label1 = BodyLabel(self.tr("(Optional) From "),self)
        self.movie_info_source = ComboBox()
        self.movie_info_source.setToolTip(self.tr("Choose the info source for a movie or a TV show."))
        self.movie_info_source.addItems(list(item.value for item in MovieDatabaseEnum))
        
        self.movie_info_label2 = BodyLabel(self.tr("get info about a Movie or TV Episode by ID:"), self)
        self.movie_info_label2.setToolTip(self.tr("This will improve transcription accuracy by fetching video summary info from webside."))
        self.movie_info_input = LineEdit(self)
        self.movie_info_input.setFixedWidth(100)
        self.movie_info_input.setPlaceholderText("tt1234567")
        self.movie_info_input.setToolTip(self.tr("Fill in the id for the movie/tv show only."))
        self.movie_info_button = PushButton(
            FIF.INFO,
            self.tr("Get Info"),
            self,
        )
        self.movie_info_button.setToolTip(self.tr("Fetch information from IMDB.com or Douban.com"))
        self.movie_info_layout.addStretch()
        self.movie_info_layout.addWidget(self.movie_info_label1)
        self.movie_info_layout.addWidget(self.movie_info_source)
        self.movie_info_layout.addWidget(self.movie_info_label2)
        self.movie_info_layout.addWidget(self.movie_info_input)
        self.movie_info_layout.addWidget(self.movie_info_button)
        self.v_layout.addLayout(self.movie_info_layout)
        self.v_layout.addSpacing(20)
        self.status = BodyLabel(self.tr("Ready."))
        self.v_layout.addWidget(self.status)
        
    def setup_value(self):
        match cfg.transcribe_model.value:
            case TranscribeModelEnum.FASTER_WHISPER | TranscribeModelEnum.WHISPER:
                self.prompt_input.setText(cfg.faster_whisper_prompt.value)

            case TranscribeModelEnum.WHISPER_API:
                self.prompt_input.setText(cfg.whisper_api_prompt.value)

    def setup_signal(self):
        self.movie_info_button.clicked.connect(self.on_movie_info_button_clicked)
        self.movie_info_source.currentTextChanged.connect(self.on_movie_source_changed)
        self.accepted.connect(self.on_accepted)
        self.rejected.connect(self.on_rejected)
        
    def on_rejected(self):
        # Revert to old value.
        match cfg.transcribe_model.value:
            case TranscribeModelEnum.FASTER_WHISPER | TranscribeModelEnum.WHISPER:
                self.prompt_input.setText(self.old_prompt)
                cfg.faster_whisper_prompt.value = self.old_prompt

            case TranscribeModelEnum.WHISPER_API:
                self.prompt_input.setText(self.old_prompt)
                cfg.whisper_api_prompt.value = self.old_prompt
        self.reject()

    def on_accepted(self):
        # Keep the prompt value and close itself
        match cfg.transcribe_model.value:
            case TranscribeModelEnum.FASTER_WHISPER | TranscribeModelEnum.WHISPER:
                cfg.faster_whisper_prompt.value = self.summary
            case TranscribeModelEnum.WHISPER_API:
                cfg.whisper_api_prompt.value = self.summary
        self.accept()
        
    def on_movie_source_changed(self, source: str):
        match source:
            case MovieDatabaseEnum.IMDB.value:
                self.movie_info_input.setPlaceholderText("tt1234567")
            case MovieDatabaseEnum.DOUBAN.value:
                self.movie_info_input.setPlaceholderText("1234567")

    def on_movie_info_button_clicked(self):
        movie_id = self.movie_info_input.text()
        source = self.movie_info_source.currentText()
        if not movie_id or not source:
            self.post_url = None
            return
        
        match source:
            case MovieDatabaseEnum.IMDB.value:
                movie_summary, post_url, kind = get_imdb_movie_info(movie_id)
            case MovieDatabaseEnum.DOUBAN.value:
                movie_summary, post_url, kind = get_douban_movie_info(movie_id)
            case _:
                self.status.setText(self.tr("Error! Invalid movie/tv info source."))
                return
                
        if not movie_summary:
            self.status.setText(self.tr("Failed! Error getting movie/tv info."))
            self.post_url = None
            return
        
        self.prompt_input.setText(movie_summary)
        self.summary = movie_summary
        
        print(f"kind: {kind} source: {source}")
        if ( kind == "tv series" or kind == "tv mini series") and source == MovieDatabaseEnum.IMDB.value:
            # Special message for TV series in imdb
            self.status.setText(self.tr("Tip: This is an id for whole TV series. It's better to use episode's id instead."))

        self.post_url = post_url
