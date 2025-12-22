"""
Draggable Layers List Widget
Enables drag and drop of layers from the list.
"""

from qgis.PyQt.QtWidgets import QListWidget, QAbstractItemView
from qgis.PyQt.QtCore import Qt, QMimeData, QByteArray, QSize
from qgis.PyQt.QtGui import QDrag, QPixmap, QPainter, QColor, QFont


class DraggableLayersList(QListWidget):
    """Custom QListWidget that supports dragging layers."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setDefaultDropAction(Qt.IgnoreAction)
        self.setStyleSheet("""
            QListWidget {
                border: 2px solid #cccccc;
                border-radius: 4px;
            }
        """)
    
    def startDrag(self, supportedActions):
        """Start drag operation with selected layers."""
        try:
            selected_items = self.selectedItems()
            if not selected_items:
                return
            
            # Create MIME data with layer names
            mime_data = QMimeData()
            layer_names = [item.text() for item in selected_items]
            
            # Store layer names as comma-separated string
            mime_data.setText(','.join(layer_names))
            
            # Also store as custom MIME type for validation
            mime_data.setData('application/x-geoserver-layers', 
                            QByteArray(','.join(layer_names).encode('utf-8')))
            
            # Create drag object
            drag = QDrag(self)
            drag.setMimeData(mime_data)
            
            # Create visual feedback pixmap
            pixmap = self._create_drag_pixmap(selected_items)
            drag.setPixmap(pixmap)
            drag.setHotSpot(pixmap.rect().center())
            
            # Execute drag
            drag.exec_(supportedActions)
        
        except Exception as e:
            print(f"Error in startDrag: {str(e)}")
    
    def _create_drag_pixmap(self, items):
        """Create a pixmap showing dragged items."""
        # Create pixmap with semi-transparent background
        pixmap = QPixmap(250, max(30, len(items) * 20))
        pixmap.fill(QColor(200, 220, 255, 200))  # Light blue with transparency
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw border
        painter.drawRect(0, 0, pixmap.width() - 1, pixmap.height() - 1)
        
        # Draw layer names only (no "Moving" text)
        painter.setFont(QFont())
        y = 15
        for item in items[:4]:  # Show first 4 items
            text = item.text()
            if len(text) > 28:
                text = text[:25] + "..."
            painter.drawText(10, y, text)
            y += 20
        
        if len(items) > 4:
            painter.drawText(10, y, f"... and {len(items) - 4} more")
        
        painter.end()
        return pixmap
