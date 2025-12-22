"""
Create Workspace Module
Handles creation of new GeoServer workspaces.
Extracted from main.py for better code organization and maintainability.
"""

import requests
from qgis.PyQt.QtWidgets import QMessageBox, QInputDialog


class WorkspaceCreationManager:
    """Handles creation of new GeoServer workspaces."""
    
    def __init__(self, main_instance):
        """
        Initialize the workspace creation manager.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def create_workspace(self):
        """
        Create a new GeoServer workspace.
        
        This method will:
        1. Validate connection details
        2. Get workspace name from user input
        3. Validate workspace name (cannot start with number)
        4. Create workspace via GeoServer REST API
        5. Provide feedback and refresh the workspace list
        """
        # Get and validate connection details
        connection_details = self._get_connection_details()
        if not connection_details:
            return
        
        url, username, password = connection_details
        
        # Get workspace name from user
        workspace_name = self._get_workspace_name_from_user()
        if not workspace_name:
            return
        
        # Validate workspace name
        if not self._validate_workspace_name(workspace_name):
            return
        
        # Create the workspace
        self._create_workspace_via_api(workspace_name, url, username, password)
    
    def _get_connection_details(self):
        """
        Get and validate GeoServer connection details.
        
        Returns:
            tuple: (url, username, password) or None if validation fails
        """
        url = self.main.get_base_url()
        username = self.main.username_input.text().strip()
        password = self.main.password_input.text().strip()

        if not url or not username or not password:
            QMessageBox.warning(self.main, "Input Error", "Please provide the URL, username, and password.")
            return None
        
        return url, username, password
    
    def _get_workspace_name_from_user(self):
        """
        Get workspace name from user input dialog.
        
        Returns:
            str: Workspace name or None if cancelled/empty
        """
        workspace_name, ok = QInputDialog.getText(self.main, "Create Workspace", "Enter workspace name:")
        if not ok or not workspace_name.strip():
            return None
        
        return workspace_name.strip()
    
    def _validate_workspace_name(self, workspace_name):
        """
        Validate the workspace name according to GeoServer rules.
        
        Args:
            workspace_name: Name to validate
            
        Returns:
            bool: True if valid, False if invalid
        """
        # Check if workspace name starts with a number
        if workspace_name and workspace_name[0].isdigit():
            QMessageBox.warning(self.main, "Invalid Name", "Workspace name cannot start with a number.")
            return False
        
        return True
    
    def _create_workspace_via_api(self, workspace_name, url, username, password):
        """
        Create workspace via GeoServer REST API.
        
        Args:
            workspace_name: Name of the workspace to create
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        # Prepare the workspace payload
        workspace_payload = {
            "workspace": {
                "name": workspace_name
            }
        }

        try:
            # Create new workspace
            response = requests.post(
                f"{url}/rest/workspaces",
                auth=(username, password),
                headers={"Content-Type": "application/json"},
                json=workspace_payload
            )
            
            # Handle response
            self._handle_creation_response(response, workspace_name)
            
        except Exception as e:
            QMessageBox.critical(self.main, "Error", f"An error occurred while creating workspace: {str(e)}")
    
    def _handle_creation_response(self, response, workspace_name):
        """
        Handle the response from workspace creation.
        
        Args:
            response: requests.Response object from creation request
            workspace_name: Name of the workspace that was created
        """
        if response.status_code in [200, 201]:
            QMessageBox.information(self.main, "Success", f"Workspace '{workspace_name}' created successfully.")
            # Refresh workspaces list
            self.main.retrieve_geoserver_info()
        else:
            QMessageBox.warning(
                self.main, 
                "Error", 
                f"Failed to create workspace. Status code: {response.status_code}\nResponse: {response.text}"
            )
