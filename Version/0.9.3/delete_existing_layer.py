"""
Delete Existing Layer Module
Handles deletion of existing layers and their associated datastores/coveragestores from GeoServer.
Extracted from main.py for better code organization and maintainability.
"""

import requests
from qgis.core import Qgis


class ExistingLayerDeleter:
    """Handles deletion of existing layers and their associated stores in GeoServer."""
    
    def __init__(self, main_instance):
        """
        Initialize the existing layer deleter.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def delete_existing_layer(self, layer_name, workspace, url, username, password):
        """
        Delete an existing layer and its associated datastore/coveragestore from GeoServer.
        
        This method will:
        1. Find all layers matching the layer name (exact match or containing the name)
        2. Delete each matching layer
        3. Delete featuretypes from all datastores to prevent "Resource already exists" errors
        4. Determine store type (datastore vs coveragestore) and delete appropriately
        5. Handle both vector (datastore) and raster (coveragestore) data
        6. Report deletion results
        
        Args:
            layer_name: Name of the layer to delete
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if at least one layer was deleted, False otherwise
        """
        try:
            # First, get all layers in the workspace to find exact matches
            layers_to_delete = self._find_matching_layers(layer_name, workspace, url, username, password)
            
            # If no matches found, try the original name anyway
            if not layers_to_delete:
                layers_to_delete = [layer_name]
            
            deleted_count = 0
            for actual_layer_name in layers_to_delete:
                if self._delete_single_layer(actual_layer_name, workspace, url, username, password):
                    deleted_count += 1
            
            if deleted_count > 0:
                self.main.log_message(f"Successfully deleted {deleted_count} layer(s) matching '{layer_name}'")
                
            return deleted_count > 0
        except Exception as e:
            self.main.log_message(f"Error deleting layer '{layer_name}': {e}", level=Qgis.Critical)
            return False
    
    def _find_matching_layers(self, layer_name, workspace, url, username, password):
        """
        Find all layers in the workspace that match the given layer name.
        
        Args:
            layer_name: Name of the layer to match
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            list: List of matching layer names
        """
        layers_url = f"{url}/rest/workspaces/{workspace}/layers.json"
        layers_response = requests.get(layers_url, auth=(username, password))
        
        layers_to_delete = []
        if layers_response.status_code == 200:
            layers_data = layers_response.json()
            if 'layers' in layers_data and 'layer' in layers_data['layers']:
                for layer_info in layers_data['layers']['layer']:
                    layer_actual_name = layer_info['name']
                    # Check for exact match or if the layer name contains our target name
                    if (layer_actual_name == layer_name or 
                        layer_actual_name.startswith(layer_name) or
                        layer_name in layer_actual_name):
                        layers_to_delete.append(layer_actual_name)
        
        return layers_to_delete
    
    def _delete_single_layer(self, actual_layer_name, workspace, url, username, password):
        """
        Delete a single layer and its associated stores.
        
        Args:
            actual_layer_name: Actual name of the layer to delete
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if layer was deleted successfully, False otherwise
        """
        # Step 1: Delete the layer
        layer_deleted = self._delete_layer(actual_layer_name, workspace, url, username, password)
        
        # Step 1.5: For PostGIS layers, also delete the featuretype from ALL datastores
        self._delete_featuretypes_from_datastores(actual_layer_name, workspace, url, username, password)
        
        # Step 2: Determine store type and delete appropriately
        store_deleted = self._delete_associated_store(actual_layer_name, workspace, url, username, password)
        
        return layer_deleted
    
    def _delete_layer(self, actual_layer_name, workspace, url, username, password):
        """
        Delete the layer itself.
        
        Args:
            actual_layer_name: Actual name of the layer to delete
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if layer was deleted successfully, False otherwise
        """
        layer_url = f"{url}/rest/workspaces/{workspace}/layers/{actual_layer_name}"
        response = requests.delete(layer_url, auth=(username, password))
        
        if response.status_code in [200, 204]:
            self.main.log_message(f"🗑️ Deleted existing layer '{actual_layer_name}'")
            return True
        else:
            self.main.log_message(f"Warning: Could not delete layer '{actual_layer_name}': {response.status_code}", level=Qgis.Warning)
            return False
    
    def _delete_featuretypes_from_datastores(self, actual_layer_name, workspace, url, username, password):
        """
        Delete featuretypes from all datastores to prevent "Resource already exists" errors.
        
        Args:
            actual_layer_name: Actual name of the layer
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        try:
            # Get all datastores to find which one has this featuretype
            datastores_url = f"{url}/rest/workspaces/{workspace}/datastores.json"
            ds_list_resp = requests.get(datastores_url, auth=(username, password))
            if ds_list_resp.status_code == 200:
                ds_data = ds_list_resp.json()
                datastores = ds_data.get('dataStores', {}).get('dataStore', [])
                if not isinstance(datastores, list):
                    datastores = [datastores] if datastores else []
                
                for ds in datastores:
                    ds_name = ds.get('name', '')
                    if not ds_name:
                        continue
                    
                    # Try to delete featuretype from this datastore
                    ft_url = f"{url}/rest/workspaces/{workspace}/datastores/{ds_name}/featuretypes/{actual_layer_name}"
                    ft_check = requests.get(ft_url, auth=(username, password))
                    if ft_check.status_code == 200:
                        # Featuretype exists in this datastore, delete it
                        ft_delete = requests.delete(ft_url, auth=(username, password), params={'recurse': 'true'})
                        if ft_delete.status_code in [200, 204]:
                            self.main.log_message(f"🗑️ Deleted featuretype '{actual_layer_name}' from datastore '{ds_name}'")
        except Exception as e:
            pass  # Error occurred, continue
    
    def _delete_associated_store(self, actual_layer_name, workspace, url, username, password):
        """
        Delete the associated datastore or coveragestore.
        
        Args:
            actual_layer_name: Actual name of the layer
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if store was deleted successfully, False otherwise
        """
        # First try to get layer info to determine store type and extract actual store name
        store_deleted = self._delete_store_by_layer_info(actual_layer_name, workspace, url, username, password)
        
        # If we couldn't determine the type or deletion failed, try both
        if not store_deleted:
            store_deleted = self._delete_store_by_fallback(actual_layer_name, workspace, url, username, password)
        
        return store_deleted
    
    def _delete_store_by_layer_info(self, actual_layer_name, workspace, url, username, password):
        """
        Delete store by extracting store information from layer info.
        
        Args:
            actual_layer_name: Actual name of the layer
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if store was deleted successfully, False otherwise
        """
        try:
            layer_info_url = f"{url}/rest/workspaces/{workspace}/layers/{actual_layer_name}.json"
            layer_info_response = requests.get(layer_info_url, auth=(username, password))
            
            if layer_info_response.status_code == 200:
                layer_data = layer_info_response.json()
                layer_info = layer_data.get('layer', {})
                
                # Check if it's a featuretype (vector) or coverage (raster)
                if 'resource' in layer_info:
                    resource_info = layer_info['resource']
                    
                    # Extract the actual store name from the resource href
                    if 'href' in resource_info:
                        href = resource_info['href']
                        
                        # For vector layers: .../datastores/ACTUAL_STORE_NAME/featuretypes/...
                        if '/datastores/' in href:
                            return self._delete_datastore_from_href(href, actual_layer_name, workspace, url, username, password)
                        
                        # For raster layers: .../coveragestores/ACTUAL_STORE_NAME/coverages/...
                        elif '/coveragestores/' in href:
                            return self._delete_coveragestore_from_href(href, actual_layer_name, workspace, url, username, password)
        except Exception as e:
            self.main.log_message(f"Warning: Could not extract store info for '{actual_layer_name}': {e}")
        
        return False
    
    def _delete_datastore_from_href(self, href, actual_layer_name, workspace, url, username, password):
        """
        Delete datastore extracted from href.
        
        Args:
            href: Resource href containing store information
            actual_layer_name: Actual name of the layer
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if datastore was deleted successfully, False otherwise
        """
        store_name = href.split('/datastores/')[1].split('/')[0]
        datastore_url = f"{url}/rest/workspaces/{workspace}/datastores/{store_name}"
        ds_response = requests.delete(datastore_url, auth=(username, password), params={'recurse': 'true'})
        
        if ds_response.status_code in [200, 204]:
            self.main.log_message(f"🗑️ Deleted datastore '{store_name}' for layer '{actual_layer_name}'")
            return True
        else:
            self.main.log_message(f"Warning: Failed to delete datastore '{store_name}': {ds_response.status_code}")
            return False
    
    def _delete_coveragestore_from_href(self, href, actual_layer_name, workspace, url, username, password):
        """
        Delete coveragestore extracted from href.
        
        Args:
            href: Resource href containing store information
            actual_layer_name: Actual name of the layer
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if coveragestore was deleted successfully, False otherwise
        """
        store_name = href.split('/coveragestores/')[1].split('/')[0]
        coveragestore_url = f"{url}/rest/workspaces/{workspace}/coveragestores/{store_name}"
        cs_response = requests.delete(coveragestore_url, auth=(username, password), params={'recurse': 'true'})
        
        if cs_response.status_code in [200, 204]:
            self.main.log_message(f"🗑️ Deleted coveragestore '{store_name}' for layer '{actual_layer_name}'")
            return True
        else:
            self.main.log_message(f"Warning: Failed to delete coveragestore '{store_name}': {cs_response.status_code}")
            return False
    
    def _delete_store_by_fallback(self, actual_layer_name, workspace, url, username, password):
        """
        Delete store using fallback method (try both datastore and coveragestore).
        
        Args:
            actual_layer_name: Actual name of the layer
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if store was deleted successfully, False otherwise
        """
        # Try datastore first (for vector data)
        if self._try_delete_datastore(actual_layer_name, workspace, url, username, password):
            return True
        
        # If datastore deletion failed, try coveragestore (for raster data)
        if self._try_delete_coveragestore(actual_layer_name, workspace, url, username, password):
            return True
        
        return False
    
    def _try_delete_datastore(self, actual_layer_name, workspace, url, username, password):
        """
        Try to delete datastore with the layer name.
        
        Args:
            actual_layer_name: Actual name of the layer
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if datastore was deleted successfully, False otherwise
        """
        try:
            datastore_url = f"{url}/rest/workspaces/{workspace}/datastores/{actual_layer_name}"
            ds_response = requests.delete(datastore_url, auth=(username, password), params={'recurse': 'true'})
            if ds_response.status_code in [200, 204]:
                self.main.log_message(f"🗑️ Deleted datastore for '{actual_layer_name}'")
                return True
        except:
            pass
        return False
    
    def _try_delete_coveragestore(self, actual_layer_name, workspace, url, username, password):
        """
        Try to delete coveragestore with the layer name.
        
        Args:
            actual_layer_name: Actual name of the layer
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if coveragestore was deleted successfully, False otherwise
        """
        try:
            coveragestore_url = f"{url}/rest/workspaces/{workspace}/coveragestores/{actual_layer_name}"
            cs_response = requests.delete(coveragestore_url, auth=(username, password), params={'recurse': 'true'})
            if cs_response.status_code in [200, 204]:
                self.main.log_message(f"🗑️ Deleted coveragestore for '{actual_layer_name}'")
                return True
        except:
            pass
        return False
