"""
Ask Overwrite Existing Layer Module
Handles user dialog for asking what to do with existing layers during upload.
Extracted from main.py for better code organization and maintainability.
"""

from qgis.PyQt.QtWidgets import QMessageBox, QCheckBox


class OverwriteExistingLayerDialog:
    """Handles user dialog for existing layer overwrite decisions."""
    
    def __init__(self, main_instance):
        """
        Initialize the overwrite existing layer dialog.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def ask_overwrite_existing_layer(self, layer_name, current_layer, total_layers):
        """
        Ask user what to do with existing layer and provide batch options.
        
        This method will:
        1. Display a dialog asking what to do with the existing layer
        2. Provide "Overwrite" and "Skip" options
        3. Include a checkbox for batch operations ("Apply to all remaining layers")
        4. Return the user's decision with batch information
        
        Args:
            layer_name: Name of the existing layer
            current_layer: Current layer number being processed
            total_layers: Total number of layers to process
            
        Returns:
            str: User decision - one of:
                - 'overwrite': Overwrite this layer only
                - 'overwrite_all': Overwrite this and all remaining layers
                - 'skip': Skip this layer only
                - 'skip_all': Skip this and all remaining layers
        """
        msg_box = self._create_message_box(layer_name, current_layer, total_layers)
        
        # Add custom buttons
        overwrite_btn, skip_btn = self._add_dialog_buttons(msg_box)
        
        # Add checkbox for batch operations
        checkbox = self._add_batch_checkbox(msg_box)
        
        # Show dialog and get user response
        msg_box.exec_()
        clicked_button = msg_box.clickedButton()
        apply_to_all = checkbox.isChecked()
        
        # Return appropriate response based on user selection
        return self._get_user_decision(clicked_button, overwrite_btn, apply_to_all)
    
    def _create_message_box(self, layer_name, current_layer, total_layers):
        """
        Create the main message box dialog.
        
        Args:
            layer_name: Name of the existing layer
            current_layer: Current layer number being processed
            total_layers: Total number of layers to process
            
        Returns:
            QMessageBox: Configured message box dialog
        """
        msg_box = QMessageBox(self.main)
        msg_box.setWindowTitle("Layer Already Exists")
        msg_box.setText(f"Layer '{layer_name}' already exists in the workspace.")
        msg_box.setInformativeText(f"Processing layer {current_layer} of {total_layers}")
        return msg_box
    
    def _add_dialog_buttons(self, msg_box):
        """
        Add custom buttons to the dialog.
        
        Args:
            msg_box: Message box to add buttons to
            
        Returns:
            tuple: (overwrite_button, skip_button)
        """
        overwrite_btn = msg_box.addButton("Overwrite", QMessageBox.AcceptRole)
        skip_btn = msg_box.addButton("Skip", QMessageBox.RejectRole)
        return overwrite_btn, skip_btn
    
    def _add_batch_checkbox(self, msg_box):
        """
        Add checkbox for batch operations.
        
        Args:
            msg_box: Message box to add checkbox to
            
        Returns:
            QCheckBox: The batch operations checkbox
        """
        checkbox = QCheckBox("Apply to all remaining layers")
        msg_box.setCheckBox(checkbox)
        return checkbox
    
    def _get_user_decision(self, clicked_button, overwrite_btn, apply_to_all):
        """
        Determine the user's decision based on button clicked and checkbox state.
        
        Args:
            clicked_button: The button that was clicked
            overwrite_btn: Reference to the overwrite button
            apply_to_all: Whether the "apply to all" checkbox was checked
            
        Returns:
            str: User decision string
        """
        if clicked_button == overwrite_btn:
            return 'overwrite_all' if apply_to_all else 'overwrite'
        else:
            return 'skip_all' if apply_to_all else 'skip'
