"""
CRS Validator Module
Validates and converts layer CRS to ensure GeoServer compatibility.
"""

from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject, Qgis
import tempfile
import os


class CRSValidator:
    """Validates and converts layer CRS for GeoServer compatibility."""
    
    # Common CRS codes that GeoServer supports
    GEOSERVER_SUPPORTED_CRS = {
        'EPSG:4326',  # WGS84
        'EPSG:3857',  # Web Mercator
        'EPSG:4269',  # NAD83
        'EPSG:3395',  # World Mercator
        'EPSG:900913', # Google Mercator (deprecated but still used)
    }
    
    def __init__(self, main_instance):
        """
        Initialize the CRS validator.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def validate_and_convert_crs(self, layer):
        """
        Validate layer CRS and convert to EPSG:4326 if not supported by GeoServer.
        
        Args:
            layer: QGIS layer object
            
        Returns:
            tuple: (converted_layer, was_converted, original_crs)
                - converted_layer: The layer (original or converted)
                - was_converted: Boolean indicating if conversion occurred
                - original_crs: Original CRS code
        """
        layer_crs = layer.crs()
        
        # Check if layer has a valid CRS
        if not layer_crs.isValid():
            self.main.log_message(f"⚠️ Layer '{layer.name()}' has no valid CRS. Will use EPSG:4326 as default.", level=Qgis.Warning)
            return layer, False, None
        
        crs_code = layer_crs.authid()
        
        # Check if CRS is empty
        if not crs_code or crs_code.strip() == '':
            self.main.log_message(f"⚠️ Layer '{layer.name()}' has empty CRS. Will use EPSG:4326 as default.", level=Qgis.Warning)
            return layer, False, None
        
        # Check if CRS is supported by GeoServer
        if self._is_crs_supported(crs_code):
            self.main.log_message(f"✓ Layer CRS {crs_code} is supported by GeoServer")
            return layer, False, crs_code
        
        # CRS is not supported - need to convert
        self.main.log_message(f"⚠️ Layer CRS {crs_code} may not be fully supported by GeoServer", level=Qgis.Warning)
        self.main.log_message(f"🔄 Converting layer '{layer.name()}' from {crs_code} to EPSG:4326 (WGS84)")
        
        converted_layer = self._convert_layer_to_epsg4326(layer, crs_code)
        
        if converted_layer:
            self.main.log_message(f"✓ Successfully converted layer to EPSG:4326")
            return converted_layer, True, crs_code
        else:
            self.main.log_message(f"⚠️ Failed to convert layer CRS. Will attempt upload with original CRS {crs_code}", level=Qgis.Warning)
            return layer, False, crs_code
    
    def _is_crs_supported(self, crs_code):
        """
        Check if a CRS is in the list of commonly supported CRS by GeoServer.
        
        Args:
            crs_code: CRS code (e.g., 'EPSG:4326')
            
        Returns:
            bool: True if CRS is in the supported list
        """
        # Check exact match first
        if crs_code in self.GEOSERVER_SUPPORTED_CRS:
            return True
        
        # Check if it's an EPSG code (most EPSG codes are supported by GeoServer)
        if crs_code.startswith('EPSG:'):
            # For now, we'll be conservative and only trust the common ones
            # GeoServer supports many EPSG codes, but some may have issues
            return False
        
        # Non-EPSG codes are less likely to be supported
        return False
    
    def _convert_layer_to_epsg4326(self, layer, original_crs):
        """
        Convert a layer to EPSG:4326 coordinate system.
        
        Args:
            layer: QGIS layer object
            original_crs: Original CRS code
            
        Returns:
            QgsVectorLayer or QgsRasterLayer: Converted layer, or None if conversion failed
        """
        try:
            from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsVectorFileWriter, QgsCoordinateTransformContext
            
            target_crs = QgsCoordinateReferenceSystem('EPSG:4326')
            
            if isinstance(layer, QgsVectorLayer):
                return self._convert_vector_layer(layer, target_crs, original_crs)
            elif isinstance(layer, QgsRasterLayer):
                return self._convert_raster_layer(layer, target_crs, original_crs)
            else:
                self.main.log_message(f"⚠️ Unknown layer type, cannot convert CRS", level=Qgis.Warning)
                return None
                
        except Exception as e:
            self.main.log_message(f"❌ Error converting layer CRS: {e}", level=Qgis.Critical)
            import traceback
            self.main.log_message(traceback.format_exc())
            return None
    
    def _convert_vector_layer(self, layer, target_crs, original_crs):
        """
        Convert a vector layer to target CRS.
        
        Args:
            layer: QgsVectorLayer object
            target_crs: Target CRS
            original_crs: Original CRS code
            
        Returns:
            QgsVectorLayer: Converted layer or None
        """
        try:
            from qgis.core import QgsVectorFileWriter, QgsCoordinateTransformContext
            
            # Create temporary file for converted layer
            temp_dir = tempfile.gettempdir()
            temp_filename = f"converted_{layer.name()}_{os.getpid()}.gpkg"
            temp_path = os.path.join(temp_dir, temp_filename)
            
            # Remove temp file if it exists
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # Write layer with CRS transformation
            transform_context = QgsProject.instance().transformContext()
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = "GPKG"
            options.fileEncoding = "UTF-8"
            options.destCRS = target_crs
            
            error = QgsVectorFileWriter.writeAsVectorFormatV3(
                layer,
                temp_path,
                transform_context,
                options
            )
            
            if error[0] == QgsVectorFileWriter.NoError:
                # Load the converted layer
                from qgis.core import QgsVectorLayer
                converted_layer = QgsVectorLayer(temp_path, layer.name(), "ogr")
                
                if converted_layer.isValid():
                    self.main.log_message(f"✓ Vector layer converted successfully to {temp_path}")
                    return converted_layer
                else:
                    self.main.log_message(f"❌ Converted layer is invalid", level=Qgis.Critical)
                    return None
            else:
                self.main.log_message(f"❌ Error writing converted layer: {error[1]}", level=Qgis.Critical)
                return None
                
        except Exception as e:
            self.main.log_message(f"❌ Error in vector layer conversion: {e}", level=Qgis.Critical)
            import traceback
            self.main.log_message(traceback.format_exc())
            return None
    
    def _convert_raster_layer(self, layer, target_crs, original_crs):
        """
        Convert a raster layer to target CRS using GDAL.
        
        Args:
            layer: QgsRasterLayer object
            target_crs: Target CRS
            original_crs: Original CRS code
            
        Returns:
            QgsRasterLayer: Converted layer or None
        """
        try:
            from qgis.core import QgsRasterLayer
            from osgeo import gdal
            
            # Create temporary file for converted raster
            temp_dir = tempfile.gettempdir()
            temp_filename = f"converted_{layer.name()}_{os.getpid()}.tif"
            temp_path = os.path.join(temp_dir, temp_filename)
            
            # Remove temp file if it exists
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # Get source file path
            source_path = layer.source()
            
            # Use GDAL to warp (reproject) the raster
            warp_options = gdal.WarpOptions(
                dstSRS='EPSG:4326',
                format='GTiff',
                resampleAlg='bilinear'
            )
            
            gdal.Warp(temp_path, source_path, options=warp_options)
            
            # Load the converted raster
            converted_layer = QgsRasterLayer(temp_path, layer.name())
            
            if converted_layer.isValid():
                self.main.log_message(f"✓ Raster layer converted successfully to {temp_path}")
                return converted_layer
            else:
                self.main.log_message(f"❌ Converted raster layer is invalid", level=Qgis.Critical)
                return None
                
        except Exception as e:
            self.main.log_message(f"❌ Error in raster layer conversion: {e}", level=Qgis.Critical)
            self.main.log_message(f"⚠️ Note: Raster CRS conversion requires GDAL", level=Qgis.Warning)
            import traceback
            self.main.log_message(traceback.format_exc())
            return None
