"""
Master Layer Visibility Checkbox Handler

This module provides functionality for managing a master checkbox that controls
the visibility of all layers in the map layers tree.
"""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QCheckBox

class MasterLayerVisibilityHandler:
    """
    Handler for the "Make All Map Layers Visible" checkbox functionality.
    
    This class provides methods to:
    1. Toggle all layer visibility checkboxes
    2. Update the master checkbox state based on layer visibility
    3. Connect visibility checkboxes to update the master checkbox
    """
    
    def __init__(self, parent_dialog):
        """
        Initialize the handler with a reference to the parent dialog.
        
        Args:
            parent_dialog: The parent PreviewDialog instance
        """
        self.parent = parent_dialog
        
    def connect_visibility_checkboxes(self):
        """Connect all visibility checkboxes to update the master checkbox state."""
        # Connect all existing visibility checkboxes
        for i in range(self.parent.added_layers_tree.topLevelItemCount()):
            item = self.parent.added_layers_tree.topLevelItem(i)
            checkbox = self.parent.added_layers_tree.itemWidget(item, 0)
            if checkbox and isinstance(checkbox, QCheckBox):
                # Disconnect first to avoid multiple connections
                try:
                    checkbox.stateChanged.disconnect(self.parent.update_select_all_checkbox_state)
                except:
                    pass  # Not connected yet
                # Connect to update master checkbox
                checkbox.stateChanged.connect(self.parent.update_select_all_checkbox_state)
    
    def toggle_select_all_layers(self, state):
        """Toggle visibility for all layers in the map layers tree."""
        # Disable checkbox if no layers
        if self.parent.added_layers_tree.topLevelItemCount() == 0:
            self.parent.select_all_layers_checkbox.setEnabled(False)
            return
        else:
            self.parent.select_all_layers_checkbox.setEnabled(True)
            
        # Temporarily block signals to avoid recursive updates
        self.parent.select_all_layers_checkbox.blockSignals(True)
        self.parent.added_layers_tree.blockSignals(True)
        
        try:
            is_checked = state == Qt.CheckState.Checked.value
            for i in range(self.parent.added_layers_tree.topLevelItemCount()):
                item = self.parent.added_layers_tree.topLevelItem(i)
                # Get the visibility checkbox widget in column 0
                checkbox = self.parent.added_layers_tree.itemWidget(item, 0)
                if checkbox and isinstance(checkbox, QCheckBox):
                    # Set checkbox state without triggering signals
                    checkbox.blockSignals(True)
                    checkbox.setChecked(is_checked)
                    checkbox.blockSignals(False)
                    
                    # Update layer visibility directly
                    layer_id = item.data(0, Qt.ItemDataRole.UserRole)
                    self.parent.toggle_layer_visibility(layer_id, is_checked)
        finally:
            # Re-enable signals
            self.parent.added_layers_tree.blockSignals(False)
            self.parent.select_all_layers_checkbox.blockSignals(False)
    
    def update_select_all_checkbox_state(self):
        """Update the Select All checkbox state based on layer visibility."""
        total_count = self.parent.added_layers_tree.topLevelItemCount()
        
        # Disable checkbox if no layers
        if total_count == 0:
            self.parent.select_all_layers_checkbox.setEnabled(False)
            self.parent.select_all_layers_checkbox.setChecked(False)
            return
        else:
            self.parent.select_all_layers_checkbox.setEnabled(True)
        
        # Count visible layers (checked QCheckBox widgets in column 0)
        visible_count = 0
        for i in range(total_count):
            item = self.parent.added_layers_tree.topLevelItem(i)
            checkbox = self.parent.added_layers_tree.itemWidget(item, 0)
            if checkbox and isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                visible_count += 1
        
        # Temporarily block signals to avoid recursive updates
        self.parent.select_all_layers_checkbox.blockSignals(True)
        
        try:
            if visible_count == total_count and total_count > 0:
                # All layers visible
                self.parent.select_all_layers_checkbox.setChecked(True)
            else:
                # Some or no layers visible
                self.parent.select_all_layers_checkbox.setChecked(False)
        finally:
            self.parent.select_all_layers_checkbox.blockSignals(False)
