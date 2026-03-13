"""
Duplicate Layer Handler Module
Detects and filters duplicate layers based on format priority.
Extracted for better code organization and maintainability.
"""

import os
import sys
import importlib.util

# Ensure we load modules from the same folder as this file
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

def _load_local_module(module_name):
    """Load a module from the same directory as this file."""
    module_file = os.path.join(_CURRENT_DIR, f"{module_name}.py")
    if not os.path.exists(module_file):
        raise ImportError(f"Module not found: {module_file}")
    spec = importlib.util.spec_from_file_location(module_name, module_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for: {module_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

_lfd = _load_local_module("layer_format_detector")
get_layer_provider_info = _lfd.get_layer_provider_info


class DuplicateLayerHandler:
    """Handles detection and filtering of duplicate layers based on format priority."""
    
    # Priority order: native formats > importer formats > other formats
    FORMAT_PRIORITY = {
        # Native formats (highest priority)
        'PostGIS': 0,
        'GeoPackage': 1,
        'GeoTIFF': 2,
        
        # Importer formats (medium priority)
        'Shapefile': 10,
        'KML': 11,
        'CSV': 12,
        
        # Other formats (lowest priority)
        'GeoJSON': 20,
        'SQLite': 21,
    }
    
    def __init__(self, main_instance):
        """
        Initialize the duplicate layer handler.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
        self.duplicates_report = {}  # Track duplicates for final report
    
    def filter_duplicate_layers(self, layers):
        """
        Filter duplicate layers based on format priority.
        
        For layers with the same name, keep only the one with highest priority format.
        
        Args:
            layers: List of QGIS layer objects
            
        Returns:
            tuple: (filtered_layers, duplicates_dict)
                - filtered_layers: List of layers to upload (no duplicates)
                - duplicates_dict: Dict mapping layer_name -> list of duplicate layer names
        """
        # Group layers by name
        layers_by_name = {}
        for layer in layers:
            layer_name = self.main._sanitize_layer_name(layer.name())
            if layer_name not in layers_by_name:
                layers_by_name[layer_name] = []
            layers_by_name[layer_name].append(layer)
        
        # Filter duplicates and track them
        filtered_layers = []
        duplicates_dict = {}
        
        for layer_name, layer_list in layers_by_name.items():
            if len(layer_list) == 1:
                # No duplicates for this layer name
                filtered_layers.append(layer_list[0])
            else:
                # Multiple layers with same name - select by priority
                self.main.log_message(f"\n⚠️ DUPLICATE LAYERS DETECTED: '{layer_name}'")
                
                # Get format info for each layer
                layer_info = []
                for layer in layer_list:
                    provider_info = get_layer_provider_info(layer)
                    native_format = provider_info.get('native_format', 'Unknown')
                    upload_method = provider_info.get('upload_method', 'unknown')
                    priority = self.FORMAT_PRIORITY.get(native_format, 999)
                    
                    layer_info.append({
                        'layer': layer,
                        'format': native_format,
                        'upload_method': upload_method,
                        'priority': priority,
                        'source': layer.source().split('|')[0].split('?')[0]
                    })
                    
                    self.main.log_message(f"   - {layer.name()} ({native_format}, priority={priority})")
                
                # Sort by priority (lower number = higher priority)
                layer_info.sort(key=lambda x: x['priority'])
                
                # Keep the highest priority layer
                selected_layer = layer_info[0]['layer']
                selected_format = layer_info[0]['format']
                filtered_layers.append(selected_layer)
                
                self.main.log_message(f"   ✓ Selected: {selected_layer.name()} ({selected_format})")
                
                # Track the duplicates that were skipped
                duplicate_names = [info['layer'].name() for info in layer_info[1:]]
                duplicates_dict[layer_name] = {
                    'selected': selected_layer.name(),
                    'duplicates': duplicate_names,
                    'selected_format': selected_format,
                    'duplicate_formats': [info['format'] for info in layer_info[1:]]
                }
                
                for dup_info in layer_info[1:]:
                    self.main.log_message(f"   ✗ Skipped: {dup_info['layer'].name()} ({dup_info['format']})")
        
        self.duplicates_report = duplicates_dict
        return filtered_layers, duplicates_dict
    
    def show_duplicates_report(self):
        """
        Show a report of duplicate layers that were skipped.
        
        Returns:
            str: Formatted report message
        """
        if not self.duplicates_report:
            return None
        
        report_lines = ["\n⚠️ DUPLICATE LAYERS REPORT\n"]
        
        for layer_name, dup_info in self.duplicates_report.items():
            report_lines.append(f"Layer: {layer_name}")
            report_lines.append(f"✓ UPLOADED: {dup_info['selected']} ({dup_info['selected_format']})")
            for i, dup_name in enumerate(dup_info['duplicates']):
                dup_format = dup_info['duplicate_formats'][i]
                report_lines.append(f"✗ NOT ADDED: {dup_name} ({dup_format})")
        
        report_lines.append("")
        
        return "\n".join(report_lines)
