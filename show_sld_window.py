"""
Show SLD Window Module
Handles displaying SLD content of layers in a dialog window.
Extracted from main.py for better code organization and maintainability.
"""

import os
import tempfile
from qgis.PyQt.QtWidgets import QMessageBox
from .sld_viewer_dialog import SLDViewerDialog


class SLDWindowManager:
    """Handles displaying SLD content of layers in dialog windows."""
    
    def __init__(self, main_instance):
        """
        Initialize the SLD window manager.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def show_sld_window(self, layer):
        """
        Display the SLD content of a layer in a new window using a temporary file for robustness.
        
        This method will:
        1. Create a temporary file to store the SLD
        2. Export the layer's SLD style to the temporary file
        3. Read the SLD content from the file
        4. Display the content in an SLDViewerDialog
        5. Clean up the temporary file
        
        Args:
            layer: QGIS layer object to extract SLD from
        """
        sld_content = self._extract_sld_content(layer)
        if not sld_content:
            return
        
        # Create and show the SLD viewer dialog
        self._show_sld_dialog(sld_content, layer.name())
    
    def _extract_sld_content(self, layer):
        """
        Extract SLD content from a layer using a temporary file approach.
        
        Args:
            layer: QGIS layer object
            
        Returns:
            str: SLD content or None if extraction failed
        """
        sld_content = ""
        temp_filepath = ""
        
        try:
            # Create a temporary file to store the SLD
            temp_filepath = self._create_temp_sld_file()
            
            # Save the SLD style to the temporary file
            if not self._save_layer_sld_to_file(layer, temp_filepath):
                return None
            
            # Read the SLD content from the temporary file
            sld_content = self._read_sld_from_file(temp_filepath)
            
        except Exception as e:
            QMessageBox.critical(
                self.main, 
                "Error", 
                f"Failed to retrieve SLD for layer '{layer.name()}': {str(e)}"
            )
            return None
        finally:
            # Clean up the temporary file
            self._cleanup_temp_file(temp_filepath)
        
        if not sld_content:
            QMessageBox.warning(self.main, "Warning", "SLD content is empty.")
            return None
        
        return sld_content
    
    def _create_temp_sld_file(self):
        """
        Create a temporary file for SLD storage.
        
        Returns:
            str: Path to the temporary file
        """
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sld') as temp_file:
            return temp_file.name
    
    def _save_layer_sld_to_file(self, layer, temp_filepath):
        """
        Save layer's SLD style to a temporary file.
        
        Args:
            layer: QGIS layer object
            temp_filepath: Path to temporary file
            
        Returns:
            bool: True if successful, False otherwise
        """
        # This method is more reliable across QGIS versions
        result, message = layer.saveSldStyle(temp_filepath)
        
        if not result:
            raise IOError(f"Failed to export SLD: {message}")
        
        return True
    
    def _read_sld_from_file(self, temp_filepath):
        """
        Read SLD content from the temporary file.
        
        Args:
            temp_filepath: Path to temporary file
            
        Returns:
            str: SLD content
        """
        with open(temp_filepath, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _cleanup_temp_file(self, temp_filepath):
        """
        Clean up the temporary file.
        
        Args:
            temp_filepath: Path to temporary file to remove
        """
        if temp_filepath and os.path.exists(temp_filepath):
            os.remove(temp_filepath)
    
    def _show_sld_dialog(self, sld_content, layer_name):
        """
        Create and show the SLD viewer dialog.
        
        Args:
            sld_content: SLD content to display
            layer_name: Name of the layer for dialog title
        """
        sld_dialog = SLDViewerDialog(sld_content, f"SLD for Layer: {layer_name}", parent=self.main)
        sld_dialog.exec_()
