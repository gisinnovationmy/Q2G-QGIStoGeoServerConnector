"""
Delete Workspace Module
Handles deletion of selected GeoServer workspace and all its contents.
Extracted from main.py for better code organization and maintainability.
"""

import requests
from qgis.PyQt.QtWidgets import QMessageBox


class WorkspaceDeletionManager:
    """Handles deletion of GeoServer workspaces and all their contents."""
    
    def __init__(self, main_instance):
        """
        Initialize the workspace deletion manager.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def delete_workspace(self):
        """
        Delete the selected GeoServer workspace and all its contents.
        
        This method will:
        1. Validate connection details and workspace selection
        2. Confirm deletion with user (with strong warning)
        3. Temporarily disconnect UI signals during deletion
        4. Delete workspace via GeoServer REST API with recurse=true
        5. Handle various response codes and provide appropriate feedback
        6. Reconnect UI signals and refresh the interface
        """
        # Get connection details and workspace
        connection_details = self._get_connection_details()
        if not connection_details:
            return
        
        url, username, password, workspace_name = connection_details
        
        # Confirm deletion with strong warning
        if not self._confirm_deletion(workspace_name):
            return
        
        # Execute deletion with proper signal management
        self._execute_workspace_deletion(workspace_name, url, username, password)
    
    def _get_connection_details(self):
        """
        Get and validate connection details and workspace selection.
        
        Returns:
            tuple: (url, username, password, workspace_name) or None if validation fails
        """
        url = self.main.get_base_url()
        username = self.main.username_input.text().strip()
        password = self.main.password_input.text().strip()
        
        if not url or not username or not password:
            QMessageBox.warning(self.main, "Input Error", "Please provide the URL, username, and password.")
            return None
        
        # Get selected workspace
        workspace_name = self.main.workspaces_list.currentItem().text() if self.main.workspaces_list.currentItem() else None
        
        if not workspace_name:
            QMessageBox.warning(self.main, "Workspace Error", "Please select a workspace to delete.")
            return None
        
        return url, username, password, workspace_name
    
    def _confirm_deletion(self, workspace_name):
        """
        Confirm deletion with the user with strong warning.
        
        Args:
            workspace_name: Name of the workspace to delete
            
        Returns:
            bool: True if user confirmed, False if cancelled
        """
        reply = QMessageBox.question(
            self.main, 
            "Confirm Deletion", 
            f"Are you sure you want to delete workspace '{workspace_name}' and all its contents?\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )
        
        return reply == QMessageBox.Yes
    
    def _execute_workspace_deletion(self, workspace_name, url, username, password):
        """
        Execute the workspace deletion with proper signal management.
        
        Args:
            workspace_name: Name of the workspace to delete
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        try:
            # Temporarily disconnect signals to prevent UI updates during deletion
            self._disconnect_ui_signals()
            
            # Delete the workspace
            response = self._delete_workspace_via_api(workspace_name, url, username, password)
            
            # Handle response and provide feedback
            self._handle_deletion_response(response, workspace_name)
            
            # Reconnect signals after deletion
            self._reconnect_ui_signals()
            
        except Exception as e:
            # Reconnect signals in case of error
            self._reconnect_ui_signals_safe()
            QMessageBox.critical(self.main, "Error", f"An error occurred while deleting workspace: {str(e)}")
            self.main.log_message(f"Error deleting workspace {workspace_name}: {str(e)}")
    
    def _disconnect_ui_signals(self):
        """Temporarily disconnect UI signals to prevent updates during deletion."""
        try:
            self.main.workspaces_list.itemSelectionChanged.disconnect(self.main.load_workspace_layers)
            self.main.workspaces_list.itemSelectionChanged.disconnect(self.main.load_stores)
        except TypeError:
            # Signals might not be connected
            pass
    
    def _reconnect_ui_signals(self):
        """Reconnect UI signals after deletion."""
        self.main.workspaces_list.itemSelectionChanged.connect(self.main.load_workspace_layers)
        self.main.workspaces_list.itemSelectionChanged.connect(self.main.load_stores)
    
    def _reconnect_ui_signals_safe(self):
        """Safely reconnect UI signals in case of error."""
        try:
            self.main.workspaces_list.itemSelectionChanged.connect(self.main.load_workspace_layers)
            self.main.workspaces_list.itemSelectionChanged.connect(self.main.load_stores)
        except TypeError:
            # Signals might already be connected
            pass
    
    def _delete_workspace_via_api(self, workspace_name, url, username, password):
        """
        Delete workspace via GeoServer REST API.
        
        Args:
            workspace_name: Name of the workspace to delete
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            requests.Response: Response from the deletion request
        """
        # Delete the workspace and all its resources recursively
        response = requests.delete(
            f"{url}/rest/workspaces/{workspace_name}?recurse=true",
            auth=(username, password),
            headers={"Accept": "application/xml"}
        )
        
        return response
    
    def _handle_deletion_response(self, response, workspace_name):
        """
        Handle the response from workspace deletion and provide appropriate feedback.
        
        Args:
            response: requests.Response object from deletion request
            workspace_name: Name of the workspace that was deleted
        """
        if response.status_code == 200:
            QMessageBox.information(self.main, "Success", f"Workspace '{workspace_name}' deleted successfully.")
            # Clear dependent lists first to avoid fetching datastores for deleted workspace
            self.main.workspace_layers_list.clear()
            self.main.datastores_list.clear()
            # Refresh the workspaces list
            self.main.retrieve_geoserver_info()
        elif response.status_code == 403:
            QMessageBox.warning(
                self.main, 
                "Error", 
                f"Failed to delete workspace '{workspace_name}'. Status code: {response.status_code}\n"
                "The workspace may contain resources that cannot be deleted automatically. "
                "Please check GeoServer logs for more details."
            )
            self.main.log_message(f"Failed to delete workspace {workspace_name}: 403 Forbidden. May contain protected resources.")
        else:
            QMessageBox.warning(
                self.main, 
                "Error", 
                f"Failed to delete workspace '{workspace_name}'. Status code: {response.status_code}\nResponse: {response.text}"
            )
            self.main.log_message(f"Failed to delete workspace {workspace_name}: Status {response.status_code} - {response.text}")
