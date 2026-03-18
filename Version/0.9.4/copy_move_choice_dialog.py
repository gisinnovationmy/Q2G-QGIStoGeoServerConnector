"""
Copy/Move Choice Dialog
Simple dialog to let user choose between Copy and Move operations.
"""

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem
)
from qgis.PyQt.QtCore import Qt


class CopyMoveChoiceDialog(QDialog):
    """Dialog to choose between Copy and Move operations."""
    
    def __init__(self, parent=None, layer_names=None, target_workspace=None):
        super().__init__(parent)
        
        self.layer_names = layer_names or []
        self.target_workspace = target_workspace
        self.choice = None  # 'copy' or 'move'
        
        self.setWindowTitle("Copy or Move Layers")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        self.setModal(True)
        
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the dialog UI."""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Choose Operation")
        title_font = title.font()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Source and target info
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"Layers: {len(self.layer_names)}"))
        info_layout.addStretch()
        info_layout.addWidget(QLabel(f"Target: {self.target_workspace}"))
        layout.addLayout(info_layout)
        
        # Layers list
        layout.addWidget(QLabel("Layers to process:"))
        layers_list = QListWidget()
        layers_list.setMaximumHeight(120)
        for layer_name in self.layer_names:
            layers_list.addItem(layer_name)
        layout.addWidget(layers_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        copy_btn = QPushButton("Copy")
        copy_btn.setMinimumHeight(32)
        copy_btn.clicked.connect(self._on_copy_clicked)
        button_layout.addWidget(copy_btn)
        
        move_btn = QPushButton("Move")
        move_btn.setMinimumHeight(32)
        move_btn.clicked.connect(self._on_move_clicked)
        button_layout.addWidget(move_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumHeight(32)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _on_copy_clicked(self):
        """Handle copy button click."""
        print("DEBUG: Copy button clicked")
        self.choice = 'copy'
        print(f"DEBUG: Choice set to: {self.choice}")
        self.accept()
        print("DEBUG: Dialog accepted")
    
    def _on_move_clicked(self):
        """Handle move button click."""
        print("DEBUG: Move button clicked")
        self.choice = 'move'
        print(f"DEBUG: Choice set to: {self.choice}")
        self.accept()
        print("DEBUG: Dialog accepted")
    
    def get_choice(self):
        """Get the user's choice."""
        return self.choice
