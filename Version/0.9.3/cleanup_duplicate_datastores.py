"""
Cleanup Duplicate Datastores Module
Handles cleanup of duplicate datastores (vector stores) created by importer.
Extracted from main.py for better code organization and maintainability.
"""

import requests


class DuplicateDatastoresCleaner:
    """Handles cleanup of duplicate datastores in GeoServer."""
    
    def __init__(self, main_instance):
        """
        Initialize the duplicate datastores cleaner.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
        
        # Define prefixes that identify temporary datastores
        self.temp_prefixes = ['tmp', 'temp', 'import_', 'upload_']
    
    def cleanup_duplicate_datastores(self, layer_name, workspace, url, username, password):
        """
        Delete duplicate datastores (vector stores) created by importer.
        
        This method will:
        1. Fetch all datastores in the workspace
        2. Identify duplicate datastores with numeric suffixes
        3. Identify temporary datastores by name prefixes
        4. Delete duplicate and temporary datastores
        5. Report cleanup results
        
        Args:
            layer_name: Name of the layer to check for duplicates
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        try:
            # Get all datastores in the workspace
            datastores = self._fetch_workspace_datastores(workspace, url, username, password)
            if datastores is None:
                return
            
            # Delete duplicate and temporary datastores
            deleted_count = self._delete_duplicate_and_temporary_datastores(datastores, layer_name, workspace, url, username, password)
            
            if deleted_count > 0:
                self.main.log_message(f"✓ Cleaned up {deleted_count} duplicate/temporary datastore(s)")
        
        except Exception as e:
            self.main.log_message(f"Error during duplicate datastore cleanup: {e}")
    
    def _fetch_workspace_datastores(self, workspace, url, username, password):
        """
        Fetch all datastores in the workspace.
        
        Args:
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            list: List of datastores or None if fetch failed
        """
        datastores_url = f"{url}/rest/workspaces/{workspace}/datastores.json"
        response = requests.get(datastores_url, auth=(username, password))
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        datastores = data.get('dataStores', {}).get('dataStore', [])
        
        # Ensure datastores is always a list
        if not isinstance(datastores, list):
            datastores = [datastores] if datastores else []
        
        return datastores
    
    def _delete_duplicate_and_temporary_datastores(self, datastores, layer_name, workspace, url, username, password):
        """
        Delete duplicate and temporary datastores.
        
        Args:
            datastores: List of datastores
            layer_name: Name of the layer to check for duplicates
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            int: Number of datastores deleted
        """
        deleted_count = 0
        sanitized_layer = self._sanitize_layer_name(layer_name)
        
        for store in datastores:
            store_name = store.get('name', '')
            if not store_name:
                continue
            
            # Check for duplicate datastores with numeric suffixes
            if self._is_duplicate_datastore_with_suffix(store_name, sanitized_layer):
                if self._delete_datastore(store_name, workspace, url, username, password, "duplicate datastore with suffix"):
                    deleted_count += 1
            
            # Check for temporary datastores
            elif self._is_temporary_datastore(store_name):
                if self._delete_datastore(store_name, workspace, url, username, password, "temporary datastore"):
                    deleted_count += 1
        
        return deleted_count
    
    def _sanitize_layer_name(self, layer_name):
        """
        Sanitize the layer name for comparison.
        
        Args:
            layer_name: Original layer name
            
        Returns:
            str: Sanitized layer name
        """
        return layer_name.replace(' ', '_').replace('—', '_').replace('-', '_')
    
    def _is_duplicate_datastore_with_suffix(self, store_name, sanitized_layer):
        """
        Check if a datastore is a duplicate with numeric suffix.
        
        Pattern: Duplicate with numeric suffix (e.g., layer_name1, layer_name2)
        
        Args:
            store_name: Name of the datastore
            sanitized_layer: Sanitized layer name for comparison
            
        Returns:
            bool: True if the datastore is a duplicate with suffix, False otherwise
        """
        if store_name[-1].isdigit() and not store_name.startswith('postgis'):
            base_name = store_name.rstrip('0123456789')
            return base_name == sanitized_layer or base_name.endswith(sanitized_layer)
        return False
    
    def _is_temporary_datastore(self, store_name):
        """
        Check if a datastore is temporary based on its name.
        
        Args:
            store_name: Name of the datastore
            
        Returns:
            bool: True if the datastore is temporary, False otherwise
        """
        return any(store_name.lower().startswith(prefix) for prefix in self.temp_prefixes)
    
    def _delete_datastore(self, store_name, workspace, url, username, password, store_type):
        """
        Delete a specific datastore.
        
        Args:
            store_name: Name of the datastore to delete
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            store_type: Type description for logging (e.g., "duplicate", "temporary")
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        self.main.log_message(f"🗑️ Deleting {store_type}: {store_name}")
        
        delete_url = f"{url}/rest/workspaces/{workspace}/datastores/{store_name}"
        delete_response = requests.delete(delete_url, auth=(username, password), params={'recurse': 'true'})
        
        if delete_response.status_code in [200, 204]:
            self.main.log_message(f"✓ Deleted {store_type}: {store_name}")
            return True
        else:
            self.main.log_message(f"⚠ Failed to delete {store_type} {store_name}: {delete_response.status_code}")
            return False
