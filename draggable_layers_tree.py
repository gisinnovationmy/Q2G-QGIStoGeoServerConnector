"""
Layers Tree Widget for Map Layers panel.

Drag-and-drop is DISABLED due to Qt crash when item widgets (checkboxes, sliders)
are destroyed during internal move operations. Use Move Up/Move Down buttons instead.
"""

from PyQt5.QtWidgets import QTreeWidget, QAbstractItemView
from PyQt5.QtCore import Qt, pyqtSignal


class DraggableLayersTree(QTreeWidget):
    """Custom QTreeWidget for layer management. 
    
    Note: Drag-drop is disabled to prevent QGIS crashes. Use Move Up/Move Down buttons.
    """
    
    layers_reordered = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        # DISABLED: Drag-drop causes access violation crash in Qt when item widgets exist
        self.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.setDragEnabled(False)
        self.setAcceptDrops(False)
        self.setStyleSheet("""
            QTreeWidget {
                border: 2px solid #cccccc;
                border-radius: 4px;
            }
        """)
