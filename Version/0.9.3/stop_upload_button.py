"""
Stop Upload Button Module
Provides a floating stop button for uploads when log dialog is hidden.
"""

from qgis.PyQt.QtWidgets import QPushButton, QWidget
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QIcon


class StopUploadButton(QWidget):
    """Floating stop button for uploads."""
    
    stop_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        """Initialize the stop upload button."""
        super().__init__(parent)
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Create button
        self.button = QPushButton("🛑 Stop Upload")
        self.button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 12pt;
                font-weight: bold;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #e53935;
            }
            QPushButton:pressed {
                background-color: #c62828;
            }
        """)
        self.button.clicked.connect(self._on_stop_clicked)
        
        # Set window properties
        self.setWindowTitle("Stop Upload")
        self.setGeometry(100, 100, 180, 50)
        self.setCentralWidget(self.button)
    
    def setCentralWidget(self, widget):
        """Set the central widget (button)."""
        from qgis.PyQt.QtWidgets import QVBoxLayout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)
        self.setLayout(layout)
    
    def _on_stop_clicked(self):
        """Handle stop button click."""
        self.stop_clicked.emit()
    
    def show_button(self):
        """Show the stop button."""
        self.show()
        self.raise_()
        self.activateWindow()
    
    def hide_button(self):
        """Hide the stop button."""
        self.hide()
