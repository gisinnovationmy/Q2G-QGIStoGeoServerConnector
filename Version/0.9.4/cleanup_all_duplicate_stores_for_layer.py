"""
Cleanup All Duplicate Stores for Layer Module
Handles comprehensive cleanup of ALL stores (layers, datastores, coverage stores) before upload.
Extracted from main.py for better code organization and maintainability.
"""

import requests
import time


class AllDuplicateStoresForLayerCleaner:
    """Handles comprehensive cleanup of all duplicate stores for a layer before upload."""
    
    def __init__(self, main_instance):
        """
        Initialize the all duplicate stores cleaner.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def cleanup_all_duplicate_stores_for_layer(self, layer_name, workspace, url, username, password):
        """
        Delete ALL duplicate datastores and coveragestores for a layer BEFORE upload.
        
        This prevents the importer from creating new duplicates.
        We delete ALL stores with this layer name (with or without suffixes) because:
        - The importer will create a fresh one when uploading
        - We want a clean slate to avoid accumulation
        
        This method will:
        1. Delete the layer at workspace level to release file locks
        2. Clean up datastores (vector stores) with retry logic
        3. Clean up coverage stores (raster stores) with retry logic
        4. Handle file lock issues with delays and retries
        5. Report cleanup results
        
        Args:
            layer_name: Name of the layer to clean up stores for
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        try:
            sanitized_layer = self._sanitize_layer_name(layer_name)
            self.main.log_message(f"DEBUG: Cleaning up all duplicate stores for '{layer_name}' (sanitized: {sanitized_layer})")
            
            deleted_count = 0
            
            # FIRST: Delete the layer at workspace level to release file locks
            deleted_count += self._delete_workspace_layer(sanitized_layer, workspace, url, username, password)
            
            # Clean up datastores (vector stores)
            deleted_count += self._cleanup_datastores(sanitized_layer, workspace, url, username, password)
            
            # Clean up coverage stores (raster stores)
            deleted_count += self._cleanup_coverage_stores(sanitized_layer, workspace, url, username, password)
            
            if deleted_count > 0:
                self.main.log_message(f"✓ Cleaned up {deleted_count} store(s) before upload")
        
        except Exception as e:
            self.main.log_message(f"Error during pre-upload store cleanup: {e}")
    
    def _sanitize_layer_name(self, layer_name):
        """
        Sanitize the layer name for comparison.
        
        Args:
            layer_name: Original layer name
            
        Returns:
            str: Sanitized layer name
        """
        return layer_name.replace(' ', '_').replace('—', '_').replace('-', '_')
    
    def _delete_workspace_layer(self, sanitized_layer, workspace, url, username, password):
        """
        Delete the layer at workspace level to release file locks.
        
        Args:
            sanitized_layer: Sanitized layer name
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            int: Number of layers deleted (0 or 1)
        """
        layer_url = f"{url}/rest/workspaces/{workspace}/layers/{sanitized_layer}.json"
        layer_check = requests.get(layer_url, auth=(username, password))
        
        if layer_check.status_code == 200:
            self.main.log_message(f"🗑️ Deleting layer at workspace level: {sanitized_layer}")
            delete_layer_url = f"{url}/rest/workspaces/{workspace}/layers/{sanitized_layer}"
            delete_layer_resp = requests.delete(delete_layer_url, auth=(username, password), params={'recurse': 'true'})
            
            if delete_layer_resp.status_code in [200, 204]:
                self.main.log_message(f"✓ Deleted layer: {sanitized_layer}")
                # Wait a moment for GeoServer to release file locks
                time.sleep(0.5)
                return 1
            else:
                self.main.log_message(f"⚠ Failed to delete layer {sanitized_layer}: {delete_layer_resp.status_code}")
        
        return 0
    
    def _cleanup_datastores(self, sanitized_layer, workspace, url, username, password):
        """
        Clean up datastores (vector stores) with retry logic.
        
        Args:
            sanitized_layer: Sanitized layer name
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            int: Number of datastores deleted
        """
        deleted_count = 0
        datastores_url = f"{url}/rest/workspaces/{workspace}/datastores.json"
        ds_response = requests.get(datastores_url, auth=(username, password))
        
        if ds_response.status_code == 200:
            datastores = self._extract_datastores(ds_response.json())
            
            for store in datastores:
                store_name = store.get('name', '')
                if not store_name or store_name.startswith('postgis'):
                    continue
                
                # Match stores with this layer name (exact match or with numeric suffix)
                if self._is_matching_datastore(store_name, sanitized_layer):
                    if self._delete_datastore_with_retry(store_name, workspace, url, username, password):
                        deleted_count += 1
        
        return deleted_count
    
    def _cleanup_coverage_stores(self, sanitized_layer, workspace, url, username, password):
        """
        Clean up coverage stores (raster stores) with retry logic.
        
        Args:
            sanitized_layer: Sanitized layer name
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            int: Number of coverage stores deleted
        """
        deleted_count = 0
        coveragestores_url = f"{url}/rest/workspaces/{workspace}/coveragestores.json"
        cs_response = requests.get(coveragestores_url, auth=(username, password))
        
        if cs_response.status_code == 200:
            coveragestores = self._extract_coverage_stores(cs_response.json())
            
            for store in coveragestores:
                store_name = store.get('name', '')
                if not store_name:
                    continue
                
                # Match coverage stores with this layer name (exact match or with numeric suffix)
                if self._is_matching_coverage_store(store_name, sanitized_layer):
                    if self._delete_coverage_store_with_retry(store_name, workspace, url, username, password):
                        deleted_count += 1
        
        return deleted_count
    
    def _extract_datastores(self, ds_data):
        """
        Extract datastores list from API response.
        
        Args:
            ds_data: JSON response data
            
        Returns:
            list: List of datastores
        """
        ds_stores = ds_data.get('dataStores', {})
        if isinstance(ds_stores, dict):
            datastores = ds_stores.get('dataStore', [])
            if not isinstance(datastores, list):
                datastores = [datastores] if datastores else []
        else:
            datastores = []
        return datastores
    
    def _extract_coverage_stores(self, cs_data):
        """
        Extract coverage stores list from API response.
        
        Args:
            cs_data: JSON response data
            
        Returns:
            list: List of coverage stores
        """
        cs_stores = cs_data.get('coverageStores', {})
        if isinstance(cs_stores, dict):
            coveragestores = cs_stores.get('coverageStore', [])
            if not isinstance(coveragestores, list):
                coveragestores = [coveragestores] if coveragestores else []
        else:
            coveragestores = []
        return coveragestores
    
    def _is_matching_datastore(self, store_name, sanitized_layer):
        """
        Check if a datastore matches the layer name.
        
        Args:
            store_name: Name of the datastore
            sanitized_layer: Sanitized layer name
            
        Returns:
            bool: True if the datastore matches, False otherwise
        """
        base_name = store_name.rstrip('0123456789')
        return store_name == sanitized_layer or base_name == sanitized_layer
    
    def _is_matching_coverage_store(self, store_name, sanitized_layer):
        """
        Check if a coverage store matches the layer name.
        
        Args:
            store_name: Name of the coverage store
            sanitized_layer: Sanitized layer name
            
        Returns:
            bool: True if the coverage store matches, False otherwise
        """
        compare_name = store_name.lstrip('_')
        base_name = compare_name.rstrip('0123456789')
        return compare_name == sanitized_layer or base_name == sanitized_layer
    
    def _delete_datastore_with_retry(self, store_name, workspace, url, username, password):
        """
        Delete a datastore with retry logic for file lock issues.
        
        Args:
            store_name: Name of the datastore to delete
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        self.main.log_message(f"🗑️ Deleting datastore: {store_name}")
        delete_url = f"{url}/rest/workspaces/{workspace}/datastores/{store_name}"
        
        # Try deletion with retry logic for file lock issues
        delete_response = requests.delete(delete_url, auth=(username, password), params={'recurse': 'true'})
        
        if delete_response.status_code in [200, 204]:
            self.main.log_message(f"✓ Deleted: {store_name}")
            # Wait a moment for GeoServer to release file locks
            time.sleep(0.5)
            return True
        elif delete_response.status_code == 409:
            # 409 Conflict - likely file lock issue, try again after waiting
            self.main.log_message(f"⚠ File lock detected on datastore {store_name}, retrying...")
            time.sleep(1)
            delete_response = requests.delete(delete_url, auth=(username, password), params={'recurse': 'true'})
            if delete_response.status_code in [200, 204]:
                self.main.log_message(f"✓ Deleted (retry): {store_name}")
                return True
            else:
                self.main.log_message(f"⚠ Failed to delete datastore {store_name} (retry): {delete_response.status_code}")
        else:
            self.main.log_message(f"⚠ Failed to delete datastore {store_name}: {delete_response.status_code}")
        
        return False
    
    def _delete_coverage_store_with_retry(self, store_name, workspace, url, username, password):
        """
        Delete a coverage store with retry logic for file lock issues.
        
        Args:
            store_name: Name of the coverage store to delete
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        self.main.log_message(f"🗑️ Deleting coverage store: {store_name}")
        delete_url = f"{url}/rest/workspaces/{workspace}/coveragestores/{store_name}"
        
        # Try deletion with retry logic for file lock issues
        delete_response = requests.delete(delete_url, auth=(username, password), params={'recurse': 'true'})
        
        if delete_response.status_code in [200, 204]:
            self.main.log_message(f"✓ Deleted: {store_name}")
            # Wait a moment for GeoServer to release file locks
            time.sleep(0.5)
            return True
        elif delete_response.status_code == 409:
            # 409 Conflict - likely file lock issue, try again after waiting
            self.main.log_message(f"⚠ File lock detected on coverage store {store_name}, retrying...")
            time.sleep(1)
            delete_response = requests.delete(delete_url, auth=(username, password), params={'recurse': 'true'})
            if delete_response.status_code in [200, 204]:
                self.main.log_message(f"✓ Deleted (retry): {store_name}")
                return True
            else:
                self.main.log_message(f"⚠ Failed to delete coverage store {store_name} (retry): {delete_response.status_code}")
        else:
            self.main.log_message(f"⚠ Failed to delete coverage store {store_name}: {delete_response.status_code}")
        
        return False
