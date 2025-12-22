from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QFileDialog
from PyQt5.QtCore import Qt

class SLDViewerDialog(QDialog):
    def __init__(self, sld_content, title, parent=None, save_callback=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(600, 400)
        self.setWindowModality(Qt.NonModal)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowFlags(Qt.Window | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)

        layout = QVBoxLayout()
        self.sld_text = QTextEdit()
        self.sld_text.setPlainText(sld_content)
        self.sld_text.setReadOnly(True)
        layout.addWidget(self.sld_text)

        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save SLD")
        self.save_btn.clicked.connect(self.save_sld)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.close_btn)
        button_layout.addStretch(1)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.save_callback = save_callback

    def save_sld(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save SLD File", "", "SLD Files (*.sld)")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(self.sld_text.toPlainText())
            if self.save_callback:
                self.save_callback(file_path)
