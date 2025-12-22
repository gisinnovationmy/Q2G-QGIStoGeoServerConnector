from PyQt5.QtWidgets import QTreeWidget, QCheckBox, QSlider
from PyQt5.QtCore import Qt, pyqtSignal


class DraggableTreeWidget(QTreeWidget):
    """Custom QTreeWidget that preserves item widgets during drag-and-drop operations."""
    
    items_reordered = pyqtSignal()  # Signal emitted after drag-drop reordering
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        # Only allow dropping between items, not on items (prevents group creation)
        self.setDropIndicatorShown(True)
        # Disable auto-scroll and selection during drag to prevent unwanted item selection
        self.setAutoScroll(True)  # Keep auto-scroll enabled for usability
        self._widget_states = {}  # Store widget states during drag-drop
        self._dialog = None  # Reference to the main dialog for signal connections
        self._is_dragging = False  # Track if we're currently dragging
    
    def set_dialog(self, dialog):
        """Set reference to the main dialog for signal connections."""
        self._dialog = dialog
    
    def startDrag(self, supportedActions):
        """Override to track when dragging starts."""
        self._is_dragging = True
        super().startDrag(supportedActions)
    
    def dragMoveEvent(self, event):
        """Override to prevent selection changes during drag."""
        # Store current selection
        current_selection = self.selectedItems()
        
        # Call parent implementation
        super().dragMoveEvent(event)
        
        # Restore original selection to prevent hover-selection
        if self._is_dragging and current_selection:
            self.clearSelection()
            for item in current_selection:
                item.setSelected(True)
    
    def dropEvent(self, event):
        """Override dropEvent to preserve widgets after drag-drop."""
        self._is_dragging = False
        
        # Get the drop indicator position
        drop_indicator = self.dropIndicatorPosition()
        
        # Only allow drops between items (AboveItem or BelowItem), not on items
        if drop_indicator == QTreeWidget.OnItem:
            event.ignore()
            return
        
        # Get the item being dragged
        dragged_items = self.selectedItems()
        if not dragged_items:
            super().dropEvent(event)
            return
        
        # Store widget states before drop
        for item in dragged_items:
            layer_id = item.data(0, Qt.UserRole)
            if layer_id:
                # Get current widgets
                checkbox = self.itemWidget(item, 0)
                slider = self.itemWidget(item, 2)
                
                # Store their states
                self._widget_states[layer_id] = {
                    'checked': checkbox.isChecked() if checkbox else True,
                    'transparency': slider.value() if slider else 100,
                    'item': item
                }
        
        # Perform the default drop operation
        super().dropEvent(event)
        
        # Restore widgets after drop
        self._restore_widgets_after_drop()
        
        # Emit signal that items were reordered
        self.items_reordered.emit()
    
    def _restore_widgets_after_drop(self):
        """Restore widgets to items after drag-drop operation."""
        if not self._widget_states:
            return
        
        # Find items and restore their widgets
        for layer_id, state in self._widget_states.items():
            # Find the item with this layer_id
            for i in range(self.topLevelItemCount()):
                item = self.topLevelItem(i)
                if item and item.data(0, Qt.UserRole) == layer_id:
                    # Recreate checkbox
                    checkbox = QCheckBox()
                    checkbox.setChecked(state['checked'])
                    # Connect to dialog's handler if available
                    if self._dialog and hasattr(self._dialog, 'toggle_layer_visibility'):
                        checkbox.stateChanged.connect(
                            lambda st, l_id=layer_id: self._dialog.toggle_layer_visibility(l_id, st == Qt.Checked)
                        )
                    self.setItemWidget(item, 0, checkbox)
                    
                    # Recreate slider
                    slider = QSlider(Qt.Horizontal)
                    slider.setRange(0, 100)
                    slider.setValue(state['transparency'])
                    slider.setToolTip("Adjust layer transparency")
                    # Connect to dialog's handler if available
                    if self._dialog and hasattr(self._dialog, 'on_transparency_changed'):
                        slider.valueChanged.connect(
                            lambda val, l_id=layer_id: self._dialog.on_transparency_changed(l_id, val)
                        )
                    self.setItemWidget(item, 2, slider)
                    
                    # Update dialog's stored references if available
                    if self._dialog and hasattr(self._dialog, 'added_layers') and layer_id in self._dialog.added_layers:
                        self._dialog.added_layers[layer_id]['visibility_widget'] = checkbox
                        self._dialog.added_layers[layer_id]['slider_widget'] = slider
                    
                    break
        
        # Clear stored states
        self._widget_states.clear()
