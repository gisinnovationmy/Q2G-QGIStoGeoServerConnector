"""
Draggable Layers List Widget
Enables drag and drop of layers from the list.
"""

from qgis.PyQt.QtWidgets import QListWidget, QAbstractItemView
from qgis.PyQt.QtCore import Qt, QMimeData, QByteArray
from qgis.PyQt.QtGui import QDrag


class DraggableLayersList(QListWidget):
    """Custom QListWidget that does not support dragging layers."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.setDefaultDropAction(Qt.IgnoreAction)
        self.setStyleSheet("""
            QListWidget {
                border: 2px solid #cccccc;
                border-radius: 4px;
            }
        """)
    
    def startDrag(self, supportedActions):
        """Drag operation is disabled for this list."""
        pass
    
