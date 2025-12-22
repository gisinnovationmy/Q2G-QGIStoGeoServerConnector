"""
Delete Layer Module
Handles deletion of selected layers and their associated stores from GeoServer.
Extracted from main.py for better code organization and maintainability.
"""

import requests
from qgis.core import Qgis
from qgis.PyQt.QtWidgets import QMessageBox


class LayerDeletionManager:
    """Handles deletion of selected layers and their associated stores from GeoServer."""
    
    def __init__(self, main_instance):
        """
        Initialize the layer deletion manager.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def delete_layer(self):
        """
        Delete the selected layers and their associated stores from GeoServer.
        
        This method will:
        1. Validate workspace and layer selection
        2. Confirm deletion with user
        3. For each layer, find its associated store
        4. Delete the store (which also deletes the layer)
        5. Provide feedback and refresh the UI
        """
        # Validate workspace selection
        workspace_name = self._get_selected_workspace()
        if not workspace_name:
            return
        
        # Validate layer selection
        layer_names = self._get_selected_layers()
        if not layer_names:
            return
        
        # Confirm deletion
        if not self._confirm_deletion(workspace_name, layer_names):
            return
        
        # Get connection details
        connection_details = self._get_connection_details()
        if not connection_details:
            return
        
        url, username, password = connection_details
        
        # Execute deletion
        self._execute_layer_deletion(layer_names, workspace_name, url, username, password)
    
    def _get_selected_workspace(self):
        """
        Get the selected workspace.
        
        Returns:
            str: Workspace name or None if no workspace selected
        """
        selected_workspace_items = self.main.workspaces_list.selectedItems()
        if not selected_workspace_items:
            QMessageBox.warning(self.main, "Selection Error", "Please select a workspace first.")
            return None
        return selected_workspace_items[0].text()
    
    def _get_selected_layers(self):
        """
        Get selected layers from the UI.
        
        Returns:
            list: Layer names or None if no selection
        """
        selected_layer_items = self.main.workspace_layers_list.selectedItems()
        if not selected_layer_items:
            QMessageBox.warning(self.main, "Selection Error", "Please select one or more layers to delete.")
            return None
        return [item.text() for item in selected_layer_items]
    
    def _confirm_deletion(self, workspace_name, layer_names):
        """
        Confirm deletion with the user.
        
        Args:
            workspace_name: Name of the workspace
            layer_names: List of layer names to delete
            
        Returns:
            bool: True if user confirmed, False if cancelled
        """
        reply = QMessageBox.question(
            self.main, 
            'Confirm Deletion',
            f"Are you sure you want to delete {len(layer_names)} layers and their stores from '{workspace_name}'?\n\n" + "\n".join(layer_names),
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        return reply == QMessageBox.Yes
    
    def _get_connection_details(self):
        """
        Get GeoServer connection details.
        
        Returns:
            tuple: (url, username, password) or None if invalid
        """
        url = self.main.get_base_url()
        username = self.main.username_input.text()
        password = self.main.password_input.text()
        
        if not all([url, username, password]):
            QMessageBox.warning(self.main, "Connection Error", "Please fill in all GeoServer connection details.")
            return None
        
        return url, username, password
    
    def _execute_layer_deletion(self, layer_names, workspace_name, url, username, password):
        """
        Execute the deletion of layers and their stores.
        
        Args:
            layer_names: List of layer names to delete
            workspace_name: Name of the workspace
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        success_count = 0
        fail_count = 0
        failed_layers = []

        for layer_name in layer_names:
            result = self._delete_single_layer(layer_name, workspace_name, url, username, password)
            if result['success']:
                success_count += 1
            else:
                fail_count += 1
                failed_layers.append(result['error_info'])

        # Show results and refresh UI
        self._show_deletion_results(success_count, fail_count, failed_layers)
        self._refresh_ui()
    
    def _delete_single_layer(self, layer_name, workspace_name, url, username, password):
        """
        Delete a single layer and its associated store.
        
        Args:
            layer_name: Name of the layer to delete
            workspace_name: Name of the workspace
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            dict: Result with 'success' boolean and 'error_info' if failed
        """
        self.main.log_message(f"--- Deleting layer: {layer_name} ---")
        
        try:
            # Find the associated store for this layer
            store_info = self._find_layer_store(layer_name, workspace_name, url, username, password)
            if not store_info:
                return {'success': False, 'error_info': f"{layer_name} (Could not find store)"}
            
            store_name, store_type = store_info
            self.main.log_message(f"Determined store for '{layer_name}' is '{store_name}' (type: {store_type or 'unknown'})")
            
            # Delete the store (which also deletes the layer)
            return self._delete_store(layer_name, store_name, store_type, workspace_name, url, username, password)
            
        except requests.exceptions.RequestException as e:
            self.main.log_message(f"Error deleting layer '{layer_name}': {e}", level=Qgis.Critical)
            return {'success': False, 'error_info': f"{layer_name} (Error: {e})"}
    
    def _find_layer_store(self, layer_name, workspace_name, url, username, password):
        """
        Find the store associated with a layer.
        
        Args:
            layer_name: Name of the layer
            workspace_name: Name of the workspace
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            tuple: (store_name, store_type) or None if not found
        """
        # Get layer details to find the resource (datastore/coveragestore)
        layer_details_url = f"{url}/rest/workspaces/{workspace_name}/layers/{layer_name}.json"
        self.main.log_message(f"Fetching layer details from: {layer_details_url}")
        response = requests.get(layer_details_url, auth=(username, password))
        
        if response.status_code == 200:
            layer_info = response.json().get('layer', {})
            resource_href = layer_info.get('resource', {}).get('href', '')
            self.main.log_message(f"Found resource link: {resource_href}")
            
            if 'datastores' in resource_href:
                store_type = 'datastores'
                store_name = resource_href.split('/datastores/')[-1].split('.json')[0]
                return store_name, store_type
            elif 'coveragestores' in resource_href:
                store_type = 'coveragestores'
                store_name = resource_href.split('/coveragestores/')[-1].split('.json')[0]
                return store_name, store_type
        else:
            self.main.log_message(f"Could not get layer details for '{layer_name}'. Status: {response.status_code}", level=Qgis.Warning)
            # Fallback to old behavior: assume store name is layer name
            return layer_name, None
        
        return None
    
    def _delete_store(self, layer_name, store_name, store_type, workspace_name, url, username, password):
        """
        Delete a store and its associated layer.
        
        Args:
            layer_name: Name of the layer
            store_name: Name of the store
            store_type: Type of store ('datastores', 'coveragestores', or None)
            workspace_name: Name of the workspace
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            dict: Result with 'success' boolean and 'error_info' if failed
        """
        # If store type is unknown, try datastore first
        if store_type is None:
            self.main.log_message(f"Store type is unknown, trying datastore first.")
            delete_url = f"{url}/rest/workspaces/{workspace_name}/datastores/{store_name}?recurse=true"
            response = requests.delete(delete_url, auth=(username, password))
            if response.status_code == 404:
                self.main.log_message(f"Datastore '{store_name}' not found, trying coveragestore.")
                store_type = 'coveragestores'
            else:
                store_type = 'datastores'  # Assume it was a datastore
        
        # Delete with the determined store type
        if store_type is not None:
            delete_url = f"{url}/rest/workspaces/{workspace_name}/{store_type}/{store_name}?recurse=true"
            self.main.log_message(f"Sending DELETE request to: {delete_url}")
            response = requests.delete(delete_url, auth=(username, password))

        if response.status_code == 200:
            self.main.log_message(f"Successfully deleted store '{store_name}' and associated layer '{layer_name}'.")
            return {'success': True}
        else:
            self.main.log_message(f"Failed to delete store for layer '{layer_name}': {response.status_code} - {response.text}", level=Qgis.Critical)
            return {'success': False, 'error_info': f"{layer_name} (Status: {response.status_code})"}
    
    def _show_deletion_results(self, success_count, fail_count, failed_layers):
        """
        Show deletion results to the user.
        
        Args:
            success_count: Number of successfully deleted layers
            fail_count: Number of failed deletions
            failed_layers: List of failed layer information
        """
        if fail_count == 0:
            QMessageBox.information(self.main, "Success", f"Successfully deleted {success_count} layers.")
        else:
            QMessageBox.warning(
                self.main, 
                "Deletion Partially Failed", 
                f"Successfully deleted {success_count} layers.\n"
                f"Failed to delete {fail_count} layers:\n\n" + "\n".join(failed_layers)
            )
    
    def _refresh_ui(self):
        """Refresh the UI after deletion operations."""
        self.main.load_workspace_layers()
        self.main.load_stores()
