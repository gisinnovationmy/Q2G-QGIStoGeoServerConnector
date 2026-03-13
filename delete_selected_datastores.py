"""
Delete Selected Datastores Module
Handles deletion of selected datastores and coveragestores from GeoServer.
Extracted from main.py for better code organization and maintainability.
"""

import requests
from qgis.core import Qgis
from qgis.PyQt.QtWidgets import QMessageBox


class DatastoreDeletionManager:
    """Handles deletion of selected datastores and coveragestores from GeoServer."""
    
    def __init__(self, main_instance):
        """
        Initialize the datastore deletion manager.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def delete_selected_datastores(self):
        """
        Delete selected datastores and coveragestores from GeoServer.
        
        This method will:
        1. Validate selection and workspace
        2. Confirm deletion with user
        3. Delete each store via GeoServer REST API
        4. Provide feedback and refresh the UI
        """
        # Validate selection
        selected_items = self._get_selected_datastores()
        if not selected_items:
            return
        
        # Validate workspace
        workspace = self._get_selected_workspace()
        if not workspace:
            return
        
        # Get connection details
        connection_details = self._get_connection_details()
        if not connection_details:
            return
        
        url, username, password = connection_details
        
        # Confirm deletion
        store_names = [item.text() for item in selected_items]
        if not self._confirm_deletion(store_names):
            return
        
        # Execute deletion
        self._execute_datastore_deletion(selected_items, workspace, url, username, password)
    
    def _get_selected_datastores(self):
        """
        Get selected datastores from the UI.
        
        Returns:
            list: Selected datastore items or None if no selection
        """
        selected_items = self.main.datastores_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self.main, "No Selection", "Please select one or more datastores or coveragestores to delete.")
            return None
        return selected_items
    
    def _get_selected_workspace(self):
        """
        Get the selected workspace.
        
        Returns:
            str: Workspace name or None if no workspace selected
        """
        workspace_item = self.main.workspaces_list.currentItem()
        if not workspace_item:
            QMessageBox.warning(self.main, "Warning", "Please select a workspace first.")
            return None
        return workspace_item.text()
    
    def _get_connection_details(self):
        """
        Get GeoServer connection details.
        
        Returns:
            tuple: (url, username, password) or None if invalid
        """
        url = self.main.get_base_url()
        username = self.main.username_input.text().strip()
        password = self.main.password_input.text().strip()
        
        if not all([url, username, password]):
            QMessageBox.warning(self.main, "Connection Error", "Please fill in all GeoServer connection details.")
            return None
        
        return url, username, password
    
    def _confirm_deletion(self, store_names):
        """
        Confirm deletion with the user.
        
        Args:
            store_names: List of store names to delete
            
        Returns:
            bool: True if user confirmed, False if cancelled
        """
        reply = QMessageBox.question(
            self.main, 
            'Confirm Deletion',
            f"Are you sure you want to delete the following {len(store_names)} store(s)?\n\n"
            f"{', '.join(store_names)}\n\n"
            "This will also delete all associated layers. This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        
        return reply == QMessageBox.StandardButton.Yes
    
    def _execute_datastore_deletion(self, selected_items, workspace, url, username, password):
        """
        Execute the deletion of datastores.
        
        Args:
            selected_items: List of selected UI items
            workspace: Workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        success_count = 0
        fail_count = 0
        failed_stores = []

        for item in selected_items:
            result = self._delete_single_datastore(item, workspace, url, username, password)
            if result['success']:
                success_count += 1
            else:
                fail_count += 1
                failed_stores.append(result['error_info'])

        # Show results and refresh UI
        self._show_deletion_results(success_count, fail_count, failed_stores)
        self._refresh_ui()
    
    def _delete_single_datastore(self, item, workspace, url, username, password):
        """
        Delete a single datastore or coveragestore.
        
        Args:
            item: UI item representing the store
            workspace: Workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            dict: Result with 'success' boolean and 'error_info' if failed
        """
        item_text = item.text()
        store_info = self._parse_store_info(item_text)
        
        if not store_info:
            return {'success': False, 'error_info': f"{item_text} (Invalid format)"}
        
        store_type, store_name = store_info
        delete_url = f"{url}/rest/workspaces/{workspace}/{store_type}/{store_name}?recurse=true"
        self.main.log_message(f"Attempting to delete store: {store_name} ({store_type}) from URL: {delete_url}")

        try:
            response = requests.delete(delete_url, auth=(username, password))
            if response.status_code == 200:
                self.main.log_message(f"Successfully deleted store: {store_name}")
                return {'success': True}
            else:
                error_message = response.text
                self.main.log_message(f"Failed to delete store '{store_name}'. Status: {response.status_code}, Response: {error_message}", level=Qgis.Critical)
                return {'success': False, 'error_info': f"{store_name} (Status: {response.status_code})"}

        except requests.exceptions.RequestException as e:
            self.main.log_message(f"Error deleting store '{store_name}': {e}", level=Qgis.Critical)
            return {'success': False, 'error_info': f"{store_name} (Error: {e})"}
    
    def _parse_store_info(self, item_text):
        """
        Parse store information from UI item text.
        
        Args:
            item_text: Text from UI item (e.g., "(DS) storename" or "(CS) storename")
            
        Returns:
            tuple: (store_type, store_name) or None if invalid format
        """
        if item_text.startswith('(DS) '):
            return 'datastores', item_text.replace('(DS) ', '')
        elif item_text.startswith('(CS) '):
            return 'coveragestores', item_text.replace('(CS) ', '')
        else:
            self.main.log_message(f"Skipping invalid store item: {item_text}", level=Qgis.Warning)
            return None
    
    def _show_deletion_results(self, success_count, fail_count, failed_stores):
        """
        Show deletion results to the user.
        
        Args:
            success_count: Number of successfully deleted stores
            fail_count: Number of failed deletions
            failed_stores: List of failed store information
        """
        if fail_count == 0:
            QMessageBox.information(self.main, "Success", f"Successfully deleted {success_count} store(s).")
        else:
            QMessageBox.warning(
                self.main, 
                "Deletion Partially Failed",
                f"Successfully deleted {success_count} store(s).\n"
                f"Failed to delete {fail_count} store(s):\n\n" + "\n".join(failed_stores)
            )
    
    def _refresh_ui(self):
        """Refresh the UI after deletion operations."""
        self.main.load_stores()
        self.main.load_workspace_layers()
