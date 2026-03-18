"""
Dynamic Import Manager
Manages imports regardless of package folder name.
Allows the plugin to work with any folder name (geoserverconnector, GeoVirtuallis, etc.)
Ensures all imports come from the same folder as this file.
"""

import os
import sys
import importlib.util
from pathlib import Path

# Debug flag - set to False for production (faster startup)
DEBUG_IMPORTS = False


class ImportManager:
    """
    Manages dynamic imports regardless of package name.
    
    This class detects the actual package name at runtime and provides
    a unified interface for importing modules and items from the package.
    All imports are guaranteed to come from the same folder as this file.
    
    Usage:
        manager = ImportManager()
        PreviewDialog = manager.import_from("preview", "PreviewDialog")
        get_layer_provider_info = manager.import_from("layer_format_detector", "get_layer_provider_info")
    """
    
    def __init__(self):
        """Initialize the import manager and detect package name."""
        try:
            # Get the directory of this file - this is the ONLY source for imports
            current_file = os.path.abspath(__file__)
            self.current_dir = os.path.dirname(current_file)
            
            # Get the package name from the folder name
            self.package_name = os.path.basename(self.current_dir)
            
            # Get parent directory (where the package folder is)
            self.parent_dir = os.path.dirname(self.current_dir)
            
            # Remove any conflicting paths from sys.path that might have the same package name
            self._clean_conflicting_paths()
            
            # Ensure our directories are at the FRONT of sys.path
            if self.current_dir in sys.path:
                sys.path.remove(self.current_dir)
            sys.path.insert(0, self.current_dir)
            
            if self.parent_dir in sys.path:
                sys.path.remove(self.parent_dir)
            sys.path.insert(0, self.parent_dir)
            
            # Store loaded modules to avoid reloading
            self._loaded_modules = {}
            
            if DEBUG_IMPORTS:
                print(f"✓ ImportManager initialized: package_name = '{self.package_name}'")
                print(f"  Parent dir: {self.parent_dir}")
                print(f"  Current dir: {self.current_dir}")
            
        except Exception as e:
            print(f"✗ ImportManager initialization error: {e}")
            raise
    
    def _clean_conflicting_paths(self):
        """Remove paths from sys.path that contain a conflicting package with the same name."""
        paths_to_remove = []
        for path in sys.path:
            if path == self.current_dir or path == self.parent_dir:
                continue
            # Check if this path contains a package with our name
            potential_conflict = os.path.join(path, self.package_name)
            if os.path.isdir(potential_conflict) and potential_conflict != self.current_dir:
                paths_to_remove.append(path)
                if DEBUG_IMPORTS:
                    print(f"  Removing conflicting path: {path}")
        
        for path in paths_to_remove:
            sys.path.remove(path)
    
    def _load_module_from_file(self, module_name):
        """
        Load a module directly from a file in the current directory.
        This bypasses Python's normal import system to ensure we load from the correct location.
        """
        module_file = os.path.join(self.current_dir, f"{module_name}.py")
        
        if not os.path.exists(module_file):
            raise ImportError(f"Module file not found: {module_file}")
        
        # Create a unique module name to avoid conflicts
        unique_module_name = f"{self.package_name}.{module_name}"
        
        # Check if already loaded
        if unique_module_name in self._loaded_modules:
            return self._loaded_modules[unique_module_name]
        
        # Load the module from the specific file
        spec = importlib.util.spec_from_file_location(unique_module_name, module_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec for module: {module_file}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[unique_module_name] = module
        
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            # Clean up on failure
            if unique_module_name in sys.modules:
                del sys.modules[unique_module_name]
            raise ImportError(f"Error loading module {module_name}: {e}")
        
        self._loaded_modules[unique_module_name] = module
        return module
    
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
            # Load module directly from file to ensure correct location
            module = self._load_module_from_file(module_name)
            
            # Get requested items from module
            result = {}
            for item in items:
                if not hasattr(module, item):
                    raise AttributeError(f"Module '{self.package_name}.{module_name}' has no attribute '{item}'")
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
            return self._load_module_from_file(module_name)
        except ImportError as e:
            print(f"✗ ImportManager: Failed to import module '{self.package_name}.{module_name}': {e}")
            raise
    
    def get_plugin_dir(self):
        """Return the plugin directory path."""
        return self.current_dir


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
