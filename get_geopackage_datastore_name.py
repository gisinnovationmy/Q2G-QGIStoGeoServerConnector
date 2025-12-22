"""
Get GeoPackage Datastore Name Module
Handles extraction of GeoPackage datastore name from layer source.
Extracted from main.py for better code organization and maintainability.
"""

import os


class GeoPackageDatastoreNameExtractor:
    """Handles extraction of GeoPackage datastore names from layer sources."""
    
    def __init__(self, main_instance):
        """
        Initialize the GeoPackage datastore name extractor.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def get_geopackage_datastore_name(self, layer_source):
        """
        Extract GeoPackage datastore name from layer source.
        
        GeoPackage layer source format: /path/to/file.gpkg|layername=layer_name
        Datastore name should be the basename of the gpkg file without extension.
        
        This method will:
        1. Parse the layer source to extract the GeoPackage file path
        2. Extract the filename without extension
        3. Sanitize the name for use as a datastore name
        4. Return the sanitized datastore name
        
        Args:
            layer_source: Source URI of the GeoPackage layer
            
        Returns:
            str: Sanitized datastore name or None if extraction fails
        """
        try:
            # Extract the file path (before the pipe character)
            gpkg_path = self._extract_geopackage_path(layer_source)
            
            # Get the filename without extension
            gpkg_filename = self._extract_filename_without_extension(gpkg_path)
            
            # Sanitize the name
            datastore_name = self._sanitize_datastore_name(gpkg_filename)
            
            return datastore_name
        except Exception as e:
            self.main.log_message(f"Error extracting GeoPackage datastore name: {e}")
            return None
    
    def _extract_geopackage_path(self, layer_source):
        """
        Extract the GeoPackage file path from the layer source.
        
        Args:
            layer_source: Source URI of the GeoPackage layer
            
        Returns:
            str: Path to the GeoPackage file
        """
        # Extract the file path (before the pipe character and query parameters)
        return layer_source.split('|')[0].split('?')[0]
    
    def _extract_filename_without_extension(self, gpkg_path):
        """
        Extract the filename without extension from the GeoPackage path.
        
        Args:
            gpkg_path: Path to the GeoPackage file
            
        Returns:
            str: Filename without extension
        """
        return os.path.splitext(os.path.basename(gpkg_path))[0]
    
    def _sanitize_datastore_name(self, gpkg_filename):
        """
        Sanitize the GeoPackage filename for use as a datastore name.
        
        Args:
            gpkg_filename: Original GeoPackage filename
            
        Returns:
            str: Sanitized datastore name
        """
        return self.main._sanitize_layer_name(gpkg_filename)
