"""
Upload Batch Handler Module
Groups layers by source directory/file to avoid duplicate uploads.
Handles batch uploads for layers from the same source.
"""

import os
import sys
import importlib.util
from collections import defaultdict

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


class UploadBatchHandler:
    """Groups layers by source and handles batch uploads to avoid duplicates."""
    
    def __init__(self, main_instance):
        """
        Initialize the batch handler.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
        self.source_groups = defaultdict(list)
    
    def group_layers_by_source(self, layers):
        """
        Group layers by their source path to identify batch uploads.
        
        Args:
            layers: List of QGIS layer objects
            
        Returns:
            dict: Mapping of source_path -> list of (layer, layer_name, upload_method, native_format)
        """
        _lfd = _load_local_module("layer_format_detector")
        get_layer_provider_info = _lfd.get_layer_provider_info
        
        source_groups = defaultdict(list)
        
        for layer in layers:
            provider_info = get_layer_provider_info(layer)
            upload_method = provider_info.get('upload_method')
            native_format = provider_info.get('native_format')
            
            # Skip PostGIS layers - they don't have file sources
            if upload_method == 'postgis':
                source_groups[f"postgis_{layer.name()}"].append({
                    'layer': layer,
                    'layer_name': self.main._sanitize_layer_name(layer.name()),
                    'upload_method': upload_method,
                    'native_format': native_format,
                    'is_postgis': True
                })
                continue
            
            # Get source path
            source_path = layer.source().split('|')[0].split('?')[0]
            
            # For directories, use the directory path as key
            # For files, use the file path as key
            source_key = source_path
            
            source_groups[source_key].append({
                'layer': layer,
                'layer_name': self.main._sanitize_layer_name(layer.name()),
                'upload_method': upload_method,
                'native_format': native_format,
                'is_postgis': False
            })
        
        return source_groups
    
    def get_batch_info(self, source_groups):
        """
        Get information about batch uploads.
        
        Args:
            source_groups: Mapping of source_path -> list of layer info
            
        Returns:
            dict: Batch information with statistics
        """
        batch_info = {
            'total_sources': len(source_groups),
            'total_layers': sum(len(layers) for layers in source_groups.values()),
            'batch_uploads': {},
            'single_uploads': {}
        }
        
        for source, layers_info in source_groups.items():
            if len(layers_info) > 1:
                batch_info['batch_uploads'][source] = {
                    'count': len(layers_info),
                    'layers': [info['layer'].name() for info in layers_info]
                }
            else:
                batch_info['single_uploads'][source] = {
                    'layer': layers_info[0]['layer'].name()
                }
        
        return batch_info
    
    def log_batch_info(self, batch_info):
        """
        Log batch upload information.
        
        Args:
            batch_info: Batch information dictionary
        """
        self.main.log_message(f"\n📦 BATCH UPLOAD ANALYSIS:")
        self.main.log_message(f"Total sources: {batch_info['total_sources']}")
        self.main.log_message(f"Total layers: {batch_info['total_layers']}")
        
        if batch_info['batch_uploads']:
            self.main.log_message(f"\n⚠️ Batch uploads detected ({len(batch_info['batch_uploads'])} sources):")
            for source, info in batch_info['batch_uploads'].items():
                self.main.log_message(f"  📁 {source}")
                self.main.log_message(f"     Layers: {', '.join(info['layers'])}")
                self.main.log_message(f"     Will upload ONCE and publish {info['count']} layers")
        
        if batch_info['single_uploads']:
            self.main.log_message(f"\n✓ Single uploads ({len(batch_info['single_uploads'])} sources):")
            for source, info in batch_info['single_uploads'].items():
                self.main.log_message(f"  📄 {source} → {info['layer']}")
        
        self.main.log_message("")
