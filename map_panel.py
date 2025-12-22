from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView

class MapPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        map_layout = QVBoxLayout()
        map_layout.setContentsMargins(0, 0, 0, 0)
        self.web_view = QWebEngineView()
        map_layout.addWidget(self.web_view)
        self.setLayout(map_layout)
