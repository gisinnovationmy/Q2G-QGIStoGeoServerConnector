"""
Load Layer Styles Module
Handles loading and displaying SLD styles associated with the selected workspace.
Extracted from main.py for better code organization and maintainability.
"""

import requests


class LayerStylesLoader:
    """Handles loading and displaying layer styles from GeoServer workspace."""
    
    def __init__(self, main_instance):
        """
        Initialize the layer styles loader.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def load_layer_styles(self):
        """
        Load and display all SLD styles associated with the selected workspace.
        
        This method will:
        1. Clear the current styles list
        2. Get connection details and workspace selection
        3. Fetch styles from GeoServer REST API
        4. Parse and display the styles in the UI
        """
        # Clear the styles list
        self.main.layer_styles_list.clear()
        
        # Get connection details and workspace
        connection_details = self._get_connection_details()
        if not connection_details:
            return
        
        url, username, password, workspace_name = connection_details
        
        # Fetch and display styles
        self._fetch_and_display_styles(url, username, password, workspace_name)
    
    def _get_connection_details(self):
        """
        Get and validate connection details and workspace selection.
        
        Returns:
            tuple: (url, username, password, workspace_name) or None if validation fails
        """
        url = self.main.get_base_url()
        username = self.main.username_input.text().strip()
        password = self.main.password_input.text().strip()
        
        # Get selected workspace
        selected_workspace_items = self.main.workspaces_list.selectedItems()
        if not selected_workspace_items:
            return None
        
        workspace_name = selected_workspace_items[0].text()
        
        if not url or not username or not password:
            return None
        
        return url, username, password, workspace_name
    
    def _fetch_and_display_styles(self, url, username, password, workspace_name):
        """
        Fetch styles from GeoServer and display them in the UI.
        
        Args:
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            workspace_name: Name of the workspace
        """
        try:
            # Fetch styles from GeoServer REST API
            styles_data = self._fetch_styles_from_geoserver(url, username, password, workspace_name)
            if styles_data is not None:
                self._display_styles(styles_data, workspace_name)
            else:
                self._handle_fetch_failure(workspace_name)
                
        except Exception as e:
            self._handle_fetch_error(workspace_name, e)
    
    def _fetch_styles_from_geoserver(self, url, username, password, workspace_name):
        """
        Fetch styles from GeoServer REST API.
        
        Args:
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            workspace_name: Name of the workspace
            
        Returns:
            dict: Styles data from GeoServer or None if request failed
        """
        # Fetch styles for the selected workspace using the correct endpoint
        # According to GeoServer REST API: /rest/workspaces/<workspace>/styles.json
        response = requests.get(
            f"{url}/rest/workspaces/{workspace_name}/styles.json",
            auth=(username, password),
            headers={"Accept": "application/json"}
        )
        
        self.main.log_message(f"DEBUG: Requesting workspace styles from: {url}/rest/workspaces/{workspace_name}/styles.json")
        
        if response.status_code == 200:
            return response.json()
        else:
            self.main.log_message(f"Failed to fetch styles for workspace {workspace_name}: {response.status_code}")
            return None
    
    def _display_styles(self, styles_info, workspace_name):
        """
        Parse and display styles in the UI.
        
        Args:
            styles_info: JSON response from GeoServer
            workspace_name: Name of the workspace (for logging)
        """
        try:
            # Get styles from the response according to GeoServer documentation structure
            styles_data = styles_info.get("styles", {})
            if isinstance(styles_data, dict):
                styles = styles_data.get("style", [])
            else:
                styles = []
            
            # Handle both single style (dict) and multiple styles (list)
            if isinstance(styles, dict):
                styles = [styles]
            elif not isinstance(styles, list):
                styles = []
                
            if not styles:
                self.main.layer_styles_list.addItem("No styles found in workspace")
            else:
                # Extract style names and add to list
                for style in styles:
                    style_name = style.get("name", "Unknown Style")
                    self.main.layer_styles_list.addItem(style_name)
            
            # Styles loaded for workspace
        except Exception as e:
            self.main.layer_styles_list.addItem("Error parsing styles")
            self.main.log_message(f"Error parsing styles for workspace {workspace_name}: {str(e)}")
            # Error parsing styles
    
    def _handle_fetch_failure(self, workspace_name):
        """
        Handle failed style fetch (non-200 response).
        
        Args:
            workspace_name: Name of the workspace (for logging)
        """
        self.main.layer_styles_list.addItem("Failed to fetch styles")
        # Failed to fetch workspace styles
    
    def _handle_fetch_error(self, workspace_name, error):
        """
        Handle exception during style fetch.
        
        Args:
            workspace_name: Name of the workspace (for logging)
            error: Exception that occurred
        """
        self.main.layer_styles_list.addItem("Error fetching styles")
        self.main.log_message(f"Error fetching styles for workspace {workspace_name}: {str(error)}")
        # Error fetching workspace styles
