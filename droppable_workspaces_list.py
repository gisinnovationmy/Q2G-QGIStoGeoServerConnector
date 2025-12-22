"""
Droppable Workspaces List Widget
Enables drop of layers onto workspaces.
"""

from qgis.PyQt.QtWidgets import QListWidget
from qgis.PyQt.QtCore import Qt, pyqtSignal, QTimer
from qgis.PyQt.QtGui import QDropEvent, QColor


class DroppableWorkspacesList(QListWidget):
    """Custom QListWidget that does not accept dropped layers."""
    
    # Signal emitted when layers are dropped on a workspace
    layers_dropped = pyqtSignal(list, str)  # layer_names, target_workspace
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(False)
        self.drop_target_item = None
        self.previous_target_item = None
        self.auto_scroll_timer = QTimer()
        self.auto_scroll_timer.timeout.connect(self._auto_scroll)
        self.scroll_direction = 0  # -1 for up, 1 for down, 0 for none
        self.setStyleSheet("""
            QListWidget {
                border: 2px solid #cccccc;
                border-radius: 4px;
            }
        """)
    
    def dragEnterEvent(self, event):
        """Reject all drag enter events."""
        event.ignore()
    
    def dragLeaveEvent(self, event):
        """Reset visual feedback when drag leaves."""
        try:
            # Stop auto-scroll
            self.auto_scroll_timer.stop()
            self.scroll_direction = 0
            
            # Reset previous target item
            if self.previous_target_item:
                self.previous_target_item.setBackground(QColor(255, 255, 255))
                self.previous_target_item = None
            
            self.drop_target_item = None
        except Exception as e:
            print(f"Error in dragLeaveEvent: {str(e)}")
    
    def dragMoveEvent(self, event):
        """Reject all drag move events."""
        event.ignore()
    
    def _handle_auto_scroll(self, pos):
        """Handle auto-scroll when dragging near edges."""
        try:
            # Get scroll area dimensions
            viewport_height = self.viewport().height()
            scroll_margin = 30  # pixels from top/bottom to trigger scroll
            
            if pos.y() < scroll_margin:
                # Near top - scroll up
                self.scroll_direction = -1
                if not self.auto_scroll_timer.isActive():
                    self.auto_scroll_timer.start(100)
            elif pos.y() > viewport_height - scroll_margin:
                # Near bottom - scroll down
                self.scroll_direction = 1
                if not self.auto_scroll_timer.isActive():
                    self.auto_scroll_timer.start(100)
            else:
                # In middle - stop scrolling
                self.auto_scroll_timer.stop()
                self.scroll_direction = 0
        except Exception as e:
            print(f"Error in _handle_auto_scroll: {str(e)}")
    
    def _auto_scroll(self):
        """Auto-scroll the list."""
        try:
            scrollbar = self.verticalScrollBar()
            if self.scroll_direction == -1:
                scrollbar.setValue(scrollbar.value() - 2)
            elif self.scroll_direction == 1:
                scrollbar.setValue(scrollbar.value() + 2)
        except Exception as e:
            print(f"Error in _auto_scroll: {str(e)}")
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event."""
        try:
            print(f"DEBUG: dropEvent called at position {event.pos()}")
            
            # Stop auto-scroll
            self.auto_scroll_timer.stop()
            self.scroll_direction = 0
            
            # Reset styling
            self.setStyleSheet("""
                QListWidget {
                    border: 2px solid #cccccc;
                    border-radius: 4px;
                }
            """)
            
            # Get item at drop position
            item = self.itemAt(event.pos())
            print(f"DEBUG: Item at position: {item}")
            if not item:
                print("DEBUG: No item at drop position")
                event.ignore()
                return
            
            target_workspace = item.text()
            print(f"DEBUG: Target workspace: {target_workspace}")
            
            # Get layer names from MIME data
            mime_data = event.mimeData()
            layer_names = []
            
            print(f"DEBUG: MIME formats available: {mime_data.formats()}")
            
            if mime_data.hasFormat('application/x-geoserver-layers'):
                data = mime_data.data('application/x-geoserver-layers').data()
                layer_names = [name.strip() for name in data.decode('utf-8').split(',') if name.strip()]
                print(f"DEBUG: Got layer names from custom format: {layer_names}")
            elif mime_data.hasText():
                layer_names = [name.strip() for name in mime_data.text().split(',') if name.strip()]
                print(f"DEBUG: Got layer names from text: {layer_names}")
            
            print(f"DEBUG: Final layer names: {layer_names}")
            
            if layer_names:
                # Emit signal with layer names and target workspace
                print(f"DEBUG: Emitting layers_dropped signal with {len(layer_names)} layers")
                self.layers_dropped.emit(layer_names, target_workspace)
                event.acceptProposedAction()
                print("DEBUG: Drop accepted")
            else:
                print("DEBUG: No layer names found")
                event.ignore()
        
        except Exception as e:
            print(f"Error in dropEvent: {str(e)}")
            import traceback
            traceback.print_exc()
            event.ignore()
        
        finally:
            # Reset drop target item
            if self.drop_target_item:
                self.drop_target_item.setBackground(QColor(255, 255, 255))
                self.drop_target_item = None
            if self.previous_target_item:
                self.previous_target_item.setBackground(QColor(255, 255, 255))
                self.previous_target_item = None
