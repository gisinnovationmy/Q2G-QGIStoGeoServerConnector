"""
Register GeoPackage Datastore and Publish Module
Handles GeoPackage file upload and publishing using GeoServer Importer API.
Extracted from main.py for better code organization and maintainability.
"""

import os
import traceback
from qgis.core import Qgis


class GeoPackageDatastorePublisher:
    """Handles GeoPackage datastore registration and layer publishing."""
    
    def __init__(self, main_instance):
        """
        Initialize the GeoPackage datastore publisher.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def register_geopackage_datastore_and_publish(self, layer, layer_name, workspace, url, username, password):
        """
        Upload GeoPackage file using the GeoServer Importer API.
        
        This is more reliable than trying to create a native datastore.
        GeoPackage files are uploaded just like Shapefiles via the Importer API.
        
        Args:
            layer: QGIS layer object
            layer_name: Name of the layer
            workspace: Target workspace
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Sanitize and validate layer name
            sanitized_layer_name = self._sanitize_and_validate_layer_name(layer_name)
            if not sanitized_layer_name:
                return False
            
            # Extract and validate GeoPackage file path
            gpkg_path = self._extract_geopackage_path(layer)
            if not gpkg_path:
                return False
            
            self.main.log_message(f"📦 Using GeoPackage Importer method to upload: '{sanitized_layer_name}' from {gpkg_path}")
            
            # Use the Importer API to upload the GeoPackage file
            # This is the same approach as Shapefiles
            return self.main._upload_layer_importer(layer, sanitized_layer_name, workspace, url, username, password)
            
        except Exception as e:
            self.main.log_message(f"❌ Exception while registering GeoPackage datastore: {str(e)}", level=Qgis.Critical)
            self.main.log_message(traceback.format_exc())
            return False
    
    def _sanitize_and_validate_layer_name(self, layer_name):
        """
        Sanitize layer name to only allow alphanumeric and underscore characters.
        
        Args:
            layer_name: Original layer name
            
        Returns:
            str: Sanitized layer name or None if validation fails
        """
        original_layer_name = layer_name
        sanitized_name = self.main._sanitize_layer_name(layer_name)
        
        self.main.log_message(f"DEBUG: Sanitized layer name from '{original_layer_name}' to '{sanitized_name}'")
        
        return sanitized_name
    
    def _extract_geopackage_path(self, layer):
        """
        Extract GeoPackage file path from layer source and validate its existence.
        
        Args:
            layer: QGIS layer object
            
        Returns:
            str: Path to GeoPackage file or None if not found/invalid
        """
        # Extract GeoPackage file path from layer source
        full_source = layer.source()
        gpkg_path = full_source.split('|')[0].split('?')[0]
        
        if not os.path.exists(gpkg_path):
            self.main.log_message(f"❌ GeoPackage file not found: {gpkg_path}", level=Qgis.Critical)
            return None
        
        return gpkg_path
