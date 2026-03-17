"""
Cleanup Temporary Datastores Module
Handles cleanup of temporary datastores created during import process.
Extracted from main.py for better code organization and maintainability.
"""

import requests


class TemporaryDatastoresCleaner:
    """Handles cleanup of temporary datastores in GeoServer."""
    
    def __init__(self, main_instance):
        """
        Initialize the temporary datastores cleaner.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
        
        # Define prefixes that identify temporary datastores
        self.temp_prefixes = ['tmp', 'temp', 'import_', 'upload_']
    
    def cleanup_temporary_datastores(self, workspace, url, username, password):
        """
        Delete temporary datastores created during import process.
        
        This method will:
        1. Fetch all datastores in the workspace
        2. Identify temporary datastores by name prefixes
        3. Delete temporary datastores with recurse=true
        4. Report cleanup results
        
        Args:
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
            
            # Delete temporary datastores
            deleted_count = self._delete_temporary_datastores(datastores, workspace, url, username, password)
            
            if deleted_count > 0:
                self.main.log_message(f"✓ Cleaned up {deleted_count} temporary datastore(s)")
        
        except Exception as e:
            self.main.log_message(f"Error during temporary datastore cleanup: {e}")
    
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
    
    def _delete_temporary_datastores(self, datastores, workspace, url, username, password):
        """
        Delete temporary datastores based on name prefixes.
        
        Args:
            datastores: List of datastores
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            int: Number of datastores deleted
        """
        deleted_count = 0
        
        for store in datastores:
            store_name = store.get('name', '')
            if not store_name:
                continue
            
            # Check if this is a temporary datastore
            if self._is_temporary_datastore(store_name):
                if self._delete_datastore(store_name, workspace, url, username, password):
                    deleted_count += 1
        
        return deleted_count
    
    def _is_temporary_datastore(self, store_name):
        """
        Check if a datastore is temporary based on its name.
        
        Args:
            store_name: Name of the datastore
            
        Returns:
            bool: True if the datastore is temporary, False otherwise
        """
        return any(store_name.lower().startswith(prefix) for prefix in self.temp_prefixes)
    
    def _delete_datastore(self, store_name, workspace, url, username, password):
        """
        Delete a specific datastore.
        
        Args:
            store_name: Name of the datastore to delete
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        self.main.log_message(f"🗑️ Deleting temporary datastore: {store_name}")
        
        delete_url = f"{url}/rest/workspaces/{workspace}/datastores/{store_name}"
        delete_response = requests.delete(delete_url, auth=(username, password), params={'recurse': 'true'})
        
        if delete_response.status_code in [200, 204]:
            self.main.log_message(f"✓ Deleted temporary datastore: {store_name}")
            return True
        else:
            self.main.log_message(f"⚠ Failed to delete temporary datastore {store_name}: {delete_response.status_code}")
            return False
