"""
Dialog for displaying layer extents information.
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QFileDialog, QApplication
from PyQt5.QtCore import Qt


class LayerExtentsDialog(QDialog):
    """Dialog to display layer extents information in a table format."""
    
    def __init__(self, layer, parent=None):
        """Initialize the extents dialog with layer information."""
        super().__init__(parent)
        self.layer = layer
        self.setWindowTitle(f"Basic Layer Properties - {layer.name()}")
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
        
        # Add stretch to push buttons to the right
        button_layout.addStretch(1)
        
        # Add copy button (left of Close button)
        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setToolTip("Copy table data to clipboard (TSV format for Excel)")
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        button_layout.addWidget(self.copy_btn)
        
        # Add Close button (rightmost)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
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
    
    def _copy_to_clipboard(self):
        """Copy table data to clipboard in TSV (Tab-Separated Values) format for Excel."""
        rows = []
        
        # Add header row
        headers = []
        for col in range(self.extents_table.columnCount()):
            header_item = self.extents_table.horizontalHeaderItem(col)
            headers.append(header_item.text() if header_item else "")
        rows.append("\t".join(headers))
        
        # Add data rows - prepend '=' to force text format and left-alignment in Excel
        for row in range(self.extents_table.rowCount()):
            row_data = []
            for col in range(self.extents_table.columnCount()):
                item = self.extents_table.item(row, col)
                value = item.text() if item else ""
                # For the Value column (col 1), prepend with = and quotes to force text format
                if col == 1 and value:
                    value = f'="{value}"'
                row_data.append(value)
            rows.append("\t".join(row_data))
        
        # Join all rows with newlines and copy to clipboard
        tsv_data = "\n".join(rows)
        clipboard = QApplication.clipboard()
        clipboard.setText(tsv_data)
        
        # Provide visual feedback
        original_text = self.copy_btn.text()
        self.copy_btn.setText("Copied")
        self.copy_btn.setEnabled(False)
        
        # Reset button after 1 second
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1000, lambda: self._reset_copy_button(original_text))
    
    def _reset_copy_button(self, original_text):
        """Reset the copy button to its original state."""
        self.copy_btn.setText(original_text)
        self.copy_btn.setEnabled(True)
