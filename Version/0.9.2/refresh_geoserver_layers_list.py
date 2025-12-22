"""
Refresh GeoServer Layers List Module
Handles refreshing the GeoServer layers list to show newly uploaded layers.
Extracted from main.py for better code organization and maintainability.
"""

import requests


class GeoServerLayersListRefresher:
    """Handles refreshing GeoServer layers list after uploads."""
    
    def __init__(self, main_instance):
        """
        Initialize the GeoServer layers list refresher.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def refresh_geoserver_layers_list(self, workspace, url, username, password):
        """
        Refresh the GeoServer layers list to show newly uploaded layers.
        
        This method will:
        1. Clean up temporary datastores
        2. Clean up duplicate global styles
        3. Fetch all layers in the workspace
        4. Return the list of layers
        
        Args:
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            list: List of layers in the workspace, empty list if error
        """
        try:
            # Clean up temporary stores first
            self._cleanup_temporary_datastores(workspace, url, username, password)
            
            # Clean up duplicate global styles
            self._cleanup_duplicate_global_styles(workspace, url, username, password)
            
            # Get all layers in the workspace
            layers = self._fetch_workspace_layers(workspace, url, username, password)
            
            self.main.log_message(f"✓ Found {len(layers)} layers in workspace '{workspace}'")
            return layers
            
        except Exception as e:
            self.main.log_message(f"Error refreshing layers list: {e}")
            return []
    
    def _cleanup_temporary_datastores(self, workspace, url, username, password):
        """
        Clean up temporary datastores.
        
        Args:
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        self.main._cleanup_temporary_datastores(workspace, url, username, password)
    
    def _cleanup_duplicate_global_styles(self, workspace, url, username, password):
        """
        Clean up duplicate global styles.
        
        Args:
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        self.main._cleanup_duplicate_global_styles(workspace, url, username, password)
    
    def _fetch_workspace_layers(self, workspace, url, username, password):
        """
        Fetch all layers in the workspace via GeoServer REST API.
        
        Args:
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            list: List of layers in the workspace
        """
        layers_url = f"{url}/rest/workspaces/{workspace}/layers.json"
        response = requests.get(layers_url, auth=(username, password))
        
        if response.status_code == 200:
            data = response.json()
            layers_data = data.get('layers', {})
            
            # Handle different response formats
            if isinstance(layers_data, dict):
                layers = layers_data.get('layer', [])
            else:
                layers = layers_data if isinstance(layers_data, list) else []
            
            # Ensure layers is always a list
            if not isinstance(layers, list):
                layers = [layers] if layers else []
            
            return layers
        else:
            self.main.log_message(f"Failed to fetch layers from workspace: {response.status_code}")
            return []
