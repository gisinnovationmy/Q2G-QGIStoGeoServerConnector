"""
Upload Processor Module
Handles the core upload logic for different layer types.
Separates upload routing and processing from the main UI class.
"""

from qgis.core import Qgis


class UploadProcessor:
    """Processes layer uploads based on format and upload method."""
    
    def __init__(self, main_instance):
        """
        Initialize the upload processor.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def process_upload(self, layer, layer_name, workspace, url, username, password, upload_method, native_format):
        """
        Route and process layer upload based on method.
        
        Args:
            layer: QGIS layer object
            layer_name: Sanitized layer name
            workspace: GeoServer workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            upload_method: Upload method ('importer', 'shapefile_conversion', 'postgis', 'gpkg_native', etc.)
            native_format: Native format of the layer
            
        Returns:
            bool: True if upload succeeded, False otherwise
        """
        # Force GeoPackage to use importer instead of gpkg_native
        if native_format == 'GeoPackage' and upload_method == 'gpkg_native':
            self.main.log_message(f"Routing GeoPackage through importer instead of gpkg_native for better compatibility")
            upload_method = 'importer'

        if upload_method == 'importer':
            return self._process_importer_upload(layer, layer_name, workspace, url, username, password, native_format)
        
        elif upload_method == 'postgis':
            return self._process_postgis_upload(layer, layer_name, workspace, url, username, password)
        
        elif upload_method == 'gpkg_native':
            return self._process_geopackage_upload(layer, layer_name, workspace, url, username, password)
        
        elif upload_method == 'unsupported':
            return self._process_fallback_upload(layer, layer_name, workspace, url, username, password)
        
        else:
            self.main.log_message(f"❌ Unknown upload method: {upload_method}")
            return False
    
    def _process_importer_upload(self, layer, layer_name, workspace, url, username, password, native_format):
        """
        Process upload using GeoServer Importer API.
        
        Args:
            layer: QGIS layer object
            layer_name: Sanitized layer name
            workspace: GeoServer workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            native_format: Native format of the layer
            
        Returns:
            bool: True if upload succeeded
        """
        self.main.log_message(f"📤 Using Importers to upload: '{layer.name()}' ({native_format})")
        success = self.main._upload_layer_importer(layer, layer_name, workspace, url, username, password)
        return success
    
    def _process_postgis_upload(self, layer, layer_name, workspace, url, username, password):
        """
        Process upload using PostGIS method.
        
        Args:
            layer: QGIS layer object
            layer_name: Sanitized layer name
            workspace: GeoServer workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if upload succeeded
        """
        self.main.log_message(f"🐘 Using PostGIS method to upload: '{layer.name()}'")
        success = self.main._register_postgis_datastore_and_publish(layer, layer_name, workspace, url, username, password)
        return success
    
    def _process_geopackage_upload(self, layer, layer_name, workspace, url, username, password):
        """
        Process upload using GeoPackage native datastore method.
        
        Args:
            layer: QGIS layer object
            layer_name: Sanitized layer name
            workspace: GeoServer workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if upload succeeded
        """
        self.main.log_message(f"📦 Using GeoPackage method to upload: '{layer.name()}'")
        success = self.main._register_geopackage_datastore_and_publish(layer, layer_name, workspace, url, username, password)
        return success
    
    def _process_fallback_upload(self, layer, layer_name, workspace, url, username, password):
        """
        Process upload using fallback GeoPackage conversion method for unsupported formats.
        
        Converts unsupported formats (SQLite, GeoJSON, KML, CSV, etc.) to GeoPackage
        and uploads via the native GeoPackage datastore method.
        
        Args:
            layer: QGIS layer object
            layer_name: Sanitized layer name
            workspace: GeoServer workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if upload succeeded
        """
        self.main.log_message(f"🔄 Fallback: Converting to GeoPackage: '{layer.name()}'")
        success = self.main._upload_unsupported_as_geopackage(layer, layer_name, workspace, url, username, password)
        return success
    
    def handle_upload_success(self, layer, layer_name, workspace, url, username, password):
        """
        Handle successful layer upload - upload SLD style.
        
        Args:
            layer: QGIS layer object
            layer_name: Sanitized layer name
            workspace: GeoServer workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        self.main.log_message(f"✓ Layer '{layer.name()}' uploaded successfully.")
        # Count the layer upload ONCE (not twice)
        self.main.log_tracker.track_success(layer_name)
        try:
            sld_was_counted = self.main.sld_style_uploader.upload_sld_style(layer, layer_name, workspace, url, username, password)
            # Log SLD status but don't count it again (layer already counted above)
            if sld_was_counted:
                self.main.log_message(f"📊 SLD: Existing style overwritten")
            else:
                self.main.log_message(f"📊 SLD: New style created")
        except Exception as e:
            self.main.log_message(f"Warning: Failed to upload SLD for '{layer.name()}': {e}", level=Qgis.Warning)
    
    def handle_upload_failure(self, layer, reason=None):
        """
        Handle failed layer upload.
        
        Args:
            layer: QGIS layer object
            reason: Optional reason for failure
        """
        self.main.log_message(f"✗ Layer '{layer.name()}' was not loaded.", level=Qgis.Critical)
        self.main.log_tracker.track_failure(layer.name(), reason)
