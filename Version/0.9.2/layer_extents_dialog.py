"""
Dialog for displaying layer extents information.
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QFileDialog
from PyQt5.QtCore import Qt


class LayerExtentsDialog(QDialog):
    """Dialog to display layer extents information in a table format."""
    
    def __init__(self, layer, parent=None):
        """Initialize the extents dialog with layer information."""
        super().__init__(parent)
        self.layer = layer
        self.setWindowTitle(f"Layer Extents - {layer.name()}")
        self.setMinimumSize(500, 300)
        self.setWindowModality(Qt.NonModal)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowFlags(Qt.Window | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        
        self._setup_ui()
        self._populate_extents()
    
    def _setup_ui(self):
        """Set up the user interface for the dialog."""
        layout = QVBoxLayout()
        
        # Create table to display extents information
        self.extents_table = QTableWidget()
        self.extents_table.setColumnCount(2)
        self.extents_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.extents_table.setAlternatingRowColors(True)
        self.extents_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.extents_table.setSelectionMode(QTableWidget.SingleSelection)
        self.extents_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.extents_table)
        
        # Button layout
        button_layout = QHBoxLayout()
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        button_layout.addStretch(1)
        button_layout.addWidget(self.close_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _populate_extents(self):
        """Populate the extents table with layer information."""
        # Get layer extents
        extent = self.layer.extent()
        
        # Prepare data rows
        rows = [
            ("Layer Name", self.layer.name()),
            ("Source", self.layer.source()),
            ("CRS", self.layer.crs().authid() if self.layer.crs() else "Unknown"),
            ("Min X", str(extent.xMinimum())),
            ("Min Y", str(extent.yMinimum())),
            ("Max X", str(extent.xMaximum())),
            ("Max Y", str(extent.yMaximum())),
            ("Width", str(extent.width())),
            ("Height", str(extent.height())),
        ]
        
        # Set table dimensions
        self.extents_table.setRowCount(len(rows))
        
        # Populate table
        for i, (prop, value) in enumerate(rows):
            self.extents_table.setItem(i, 0, QTableWidgetItem(prop))
            self.extents_table.setItem(i, 1, QTableWidgetItem(value))
        
        # Resize columns to fit content
        self.extents_table.resizeColumnsToContents()
