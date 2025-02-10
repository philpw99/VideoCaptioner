from qfluentwidgets import MessageBoxBase, BodyLabel, LineEdit

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