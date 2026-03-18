"""
Dynamic Import Manager
Manages imports regardless of package folder name.
Allows the plugin to work with any folder name (geoserverconnector, GeoVirtuallis, etc.)
"""

import os
import sys
from importlib import import_module
from pathlib import Path

# Debug flag - set to False for production (faster startup)
DEBUG_IMPORTS = False


class ImportManager:
    """
    Manages dynamic imports regardless of package name.
    
    This class detects the actual package name at runtime and provides
    a unified interface for importing modules and items from the package.
    
    Usage:
        manager = ImportManager()
        PreviewDialog = manager.import_from("preview", "PreviewDialog")
        get_layer_provider_info = manager.import_from("layer_format_detector", "get_layer_provider_info")
    """
    
    def __init__(self):
        """Initialize the import manager and detect package name."""
        try:
            # Get the directory of this file
            current_file = os.path.abspath(__file__)
            current_dir = os.path.dirname(current_file)
            
            # Get the package name from the folder name
            self.package_name = os.path.basename(current_dir)
            
            # Get parent directory (where the package folder is)
            parent_dir = os.path.dirname(current_dir)
            
            # Ensure parent directory is in sys.path (for absolute imports)
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            # Also ensure current directory is in sys.path (for direct module imports)
            if current_dir not in sys.path:
                sys.path.insert(0, current_dir)
            
            if DEBUG_IMPORTS:
                print(f"✓ ImportManager initialized: package_name = '{self.package_name}'")
                print(f"  Parent dir: {parent_dir}")
                print(f"  Current dir: {current_dir}")
            
        except Exception as e:
            print(f"✗ ImportManager initialization error: {e}")
            raise
    
    def import_from(self, module_name, *items):
        """
        Dynamically import items from a module within the package.
        
        Args:
            module_name (str): Name of the module (e.g., "preview", "layer_format_detector")
            *items (str): Names of items to import from the module
            
        Returns:
            object or dict: Single item if one requested, dict if multiple requested
            
        Raises:
            ImportError: If module or items cannot be imported
            
        Examples:
            # Import single item
            PreviewDialog = manager.import_from("preview", "PreviewDialog")
            
            # Import multiple items
            items = manager.import_from("layer_format_detector", "get_layer_provider_info", "detect_format")
            get_layer_provider_info = items["get_layer_provider_info"]
            detect_format = items["detect_format"]
        """
        try:
            # Build full module path
            full_module_path = f"{self.package_name}.{module_name}"
            
            # Import the module
            module = import_module(full_module_path)
            
            # Get requested items from module
            result = {}
            for item in items:
                if not hasattr(module, item):
                    raise AttributeError(f"Module '{full_module_path}' has no attribute '{item}'")
                result[item] = getattr(module, item)
            
            # Return single item or dict based on number of items
            if len(items) == 1:
                return result[items[0]]
            else:
                return result
                
        except ImportError as e:
            print(f"✗ ImportManager: Failed to import from '{self.package_name}.{module_name}': {e}")
            raise
        except AttributeError as e:
            print(f"✗ ImportManager: {e}")
            raise
        except Exception as e:
            print(f"✗ ImportManager: Unexpected error importing from '{self.package_name}.{module_name}': {e}")
            raise
    
    def import_module_direct(self, module_name):
        """
        Import an entire module directly.
        
        Args:
            module_name (str): Name of the module to import
            
        Returns:
            module: The imported module object
            
        Examples:
            preview_module = manager.import_module_direct("preview")
            dialog = preview_module.PreviewDialog()
        """
        try:
            full_module_path = f"{self.package_name}.{module_name}"
            module = import_module(full_module_path)
            return module
        except ImportError as e:
            print(f"✗ ImportManager: Failed to import module '{full_module_path}': {e}")
            raise


# Initialize global import manager instance
_import_manager = ImportManager()


def dynamic_import(module_name, *items):
    """
    Convenience function for dynamic imports.
    
    Args:
        module_name (str): Name of the module to import from
        *items (str): Names of items to import
        
    Returns:
        object or dict: Imported item(s)
        
    Examples:
        PreviewDialog = dynamic_import("preview", "PreviewDialog")
        items = dynamic_import("layer_format_detector", "get_layer_provider_info", "detect_format")
    """
    return _import_manager.import_from(module_name, *items)


def get_import_manager():
    """
    Get the global import manager instance.
    
    Returns:
        ImportManager: The global import manager
    """
    return _import_manager
