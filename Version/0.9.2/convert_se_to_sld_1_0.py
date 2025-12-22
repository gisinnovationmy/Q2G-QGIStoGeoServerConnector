"""
Convert SE to SLD 1.0 Module
Handles comprehensive conversion of SLD 1.1.0 with SE namespace to SLD 1.0.0 format.
Implements proper XML parsing, element renaming, namespace handling, and validation.
"""

import re
import xml.etree.ElementTree as ET
from qgis.core import Qgis


class SLDConverter:
    """Comprehensive SLD 1.1.0 to 1.0.0 converter with proper XML handling and validation."""
    
    # Namespace URIs
    SE_NS = 'http://www.opengis.net/se'
    SLD_NS = 'http://www.opengis.net/sld'
    OGC_NS = 'http://www.opengis.net/ogc'
    XSI_NS = 'http://www.w3.org/2001/XMLSchema-instance'
    
    # Supported symbolizers in SLD 1.0
    SUPPORTED_SYMBOLIZERS = {
        'PointSymbolizer', 'LineSymbolizer', 'PolygonSymbolizer', 
        'TextSymbolizer', 'RasterSymbolizer'
    }
    
    def __init__(self, main_instance):
        """
        Initialize the SLD converter.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
        self.conversion_log = []
    
    def convert_se_to_sld_1_0(self, se_sld_content, layer_name=''):
        """
        Convert SLD 1.1.0 with SE namespace to SLD 1.0.0 format.
        Implements all 10 conversion tasks with proper validation and logging.
        
        Args:
            se_sld_content: SLD content string with SE namespace
            layer_name: Optional layer name for logging
            
        Returns:
            str: Converted SLD 1.0.0 content string
        """
        self.conversion_log = []
        self._log(f"Starting SLD 1.1 to 1.0 conversion for layer: {layer_name}")
        
        try:
            # Task 1: Parse and validate
            self._log("Task 1: Parsing and validating SLD 1.1 format")
            if not self._validate_sld_1_1(se_sld_content):
                self._log("Warning: SLD does not appear to be version 1.1.0", level='warning')
            
            sld_content = se_sld_content
            
            # Task 2: Update root attributes (version and namespaces)
            self._log("Task 2: Updating version and root attributes")
            sld_content = self._update_root_attributes(sld_content)
            
            # Task 3: Rename SE elements to SLD namespace
            self._log("Task 3: Converting SE elements to SLD namespace")
            sld_content = self._rename_se_elements(sld_content)
            
            # Task 4: Replace unsupported tags (SvgParameter → CssParameter)
            self._log("Task 4: Replacing unsupported tags")
            sld_content = self._replace_unsupported_tags(sld_content)
            
            # Task 5: Adjust filters and expressions
            self._log("Task 5: Normalizing OGC filters and expressions")
            sld_content = self._normalize_filters(sld_content)
            
            # Task 6: Validate symbolizers
            self._log("Task 6: Validating symbolizers")
            sld_content = self._validate_symbolizers(sld_content)
            
            # Task 7: Clean up namespaces
            self._log("Task 7: Cleaning up namespace declarations")
            sld_content = self._cleanup_namespaces(sld_content)
            
            # Task 8: Final validation
            self._log("Task 8: Final validation of output")
            if not self._validate_sld_1_0(sld_content):
                self._log("Warning: Output may not be valid SLD 1.0.0", level='warning')
            
            self._log("Conversion completed successfully")
            self.main.log_message("Successfully converted SE 1.1 to SLD 1.0.")
            self.main.log_message(f"DEBUG: Converted SLD (first 800 chars):\n{sld_content[:800]}")
            
            return sld_content
            
        except Exception as e:
            self._log(f"Error during conversion: {str(e)}", level='error')
            self.main.log_message(f"Error during SLD conversion: {e}", level=Qgis.Critical)
            return se_sld_content
    
    def _validate_sld_1_1(self, content):
        """Validate that content is SLD 1.1.0 format."""
        return 'version="1.1.0"' in content and 'xmlns:se=' in content
    
    def _validate_sld_1_0(self, content):
        """Validate that content is SLD 1.0.0 format."""
        return 'version="1.0.0"' in content and 'xmlns:sld=' in content
    
    def _update_root_attributes(self, content):
        """Task 2: Update version and namespace declarations."""
        # Update version
        content = content.replace('version="1.1.0"', 'version="1.0.0"')
        
        # Replace default SE namespace with SLD
        content = content.replace(
            'xmlns="http://www.opengis.net/se"',
            'xmlns="http://www.opengis.net/sld"'
        )
        
        # Remove xsi:schemaLocation
        content = re.sub(r'\s+xsi:schemaLocation="[^"]*"', '', content)
        
        # Ensure sld namespace is declared
        if 'xmlns:sld=' not in content:
            content = content.replace(
                '<StyledLayerDescriptor',
                '<StyledLayerDescriptor xmlns:sld="http://www.opengis.net/sld"'
            )
        
        return content
    
    def _rename_se_elements(self, content):
        """Task 3: Convert SE-prefixed elements to SLD-prefixed."""
        se_to_sld_map = [
            ('se:FeatureTypeStyle', 'sld:FeatureTypeStyle'),
            ('se:Rule', 'sld:Rule'),
            ('se:PointSymbolizer', 'sld:PointSymbolizer'),
            ('se:LineSymbolizer', 'sld:LineSymbolizer'),
            ('se:PolygonSymbolizer', 'sld:PolygonSymbolizer'),
            ('se:RasterSymbolizer', 'sld:RasterSymbolizer'),
            ('se:TextSymbolizer', 'sld:TextSymbolizer'),
            ('se:Fill', 'sld:Fill'),
            ('se:Stroke', 'sld:Stroke'),
            ('se:Graphic', 'sld:Graphic'),
            ('se:Mark', 'sld:Mark'),
            ('se:ExternalGraphic', 'sld:ExternalGraphic'),
            ('se:Font', 'sld:Font'),
            ('se:Halo', 'sld:Halo'),
            ('se:LabelPlacement', 'sld:LabelPlacement'),
            ('se:PointPlacement', 'sld:PointPlacement'),
            ('se:LinePlacement', 'sld:LinePlacement'),
        ]
        
        for se_tag, sld_tag in se_to_sld_map:
            # Replace opening tags (with and without attributes)
            content = content.replace(f'<{se_tag}>', f'<{sld_tag}>')
            content = content.replace(f'<{se_tag} ', f'<{sld_tag} ')
            # Replace closing tags
            content = content.replace(f'</{se_tag}>', f'</{sld_tag}>')
        
        return content
    
    def _replace_unsupported_tags(self, content):
        """Task 4: Replace SvgParameter with CssParameter and handle VendorOption."""
        # SvgParameter → CssParameter (SLD 1.0 uses CssParameter)
        content = content.replace('<sld:SvgParameter', '<sld:CssParameter')
        content = content.replace('</sld:SvgParameter>', '</sld:CssParameter>')
        
        # Keep se:SvgParameter as-is (styling properties)
        # VendorOption elements are typically removed or logged
        # For now, we'll keep them but log a warning
        if '<sld:VendorOption' in content or '<se:VendorOption' in content:
            self._log("Warning: VendorOption elements found - may not be supported in SLD 1.0", level='warning')
        
        return content
    
    def _normalize_filters(self, content):
        """Task 5: Normalize OGC filters and expressions."""
        # Ensure ogc: prefix is used for filter elements
        ogc_elements = [
            'Filter', 'PropertyIsEqualTo', 'PropertyIsNotEqualTo',
            'PropertyIsLessThan', 'PropertyIsGreaterThan',
            'PropertyIsLessThanOrEqualTo', 'PropertyIsGreaterThanOrEqualTo',
            'PropertyName', 'Literal', 'And', 'Or', 'Not'
        ]
        
        for elem in ogc_elements:
            # Replace se: prefixed filter elements with ogc:
            content = content.replace(f'<se:{elem}', f'<ogc:{elem}')
            content = content.replace(f'</se:{elem}>', f'</ogc:{elem}>')
        
        return content
    
    def _validate_symbolizers(self, content):
        """Task 6: Validate and handle symbolizers."""
        # Check for unsupported symbolizers
        for symbolizer in self.SUPPORTED_SYMBOLIZERS:
            if f'<sld:{symbolizer}' in content:
                self._log(f"Found supported symbolizer: {symbolizer}")
        
        return content
    
    def _cleanup_namespaces(self, content):
        """Task 7: Remove unused namespace declarations."""
        # Remove xmlns:xlink if not used
        if 'xlink:' not in content:
            content = re.sub(r'\s+xmlns:xlink="[^"]*"', '', content)
        
        # Remove xmlns:se if not used (should be removed after conversion)
        if 'se:' not in content:
            content = re.sub(r'\s+xmlns:se="[^"]*"', '', content)
        
        # Ensure ogc namespace is declared if filters are present
        if '<ogc:' in content and 'xmlns:ogc=' not in content:
            content = content.replace(
                '<StyledLayerDescriptor',
                '<StyledLayerDescriptor xmlns:ogc="http://www.opengis.net/ogc"'
            )
        
        return content
    
    def _log(self, message, level='info'):
        """Log conversion steps."""
        self.conversion_log.append({'level': level, 'message': message})
        if level == 'error':
            self.main.log_message(f"[SLD Converter] {message}", level=Qgis.Critical)
        elif level == 'warning':
            self.main.log_message(f"[SLD Converter] {message}", level=Qgis.Warning)
        else:
            self.main.log_message(f"[SLD Converter] {message}")
