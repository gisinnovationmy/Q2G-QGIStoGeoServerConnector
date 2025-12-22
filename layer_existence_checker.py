"""
Layer Existence Checker Module
Handles checking if layers exist in GeoServer workspaces and datastores.
Consolidated module to eliminate duplicate layer existence checking logic.
"""

import requests


class LayerExistenceChecker:
    """Handles checking layer existence in GeoServer workspaces and datastores."""
    
    def __init__(self, main_instance):
        """
        Initialize the layer existence checker.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def layer_exists_in_workspace(self, layer_name, workspace, url, username, password):
        """
        Check if a layer already exists in the specified workspace.
        
        Checks both:
        1. Layer at workspace level: /rest/workspaces/{workspace}/layers/{layer_name}
        2. Featuretype in PostGIS datastore: /rest/workspaces/{workspace}/datastores/postgis_postgres/featuretypes/{layer_name}
        
        Args:
            layer_name: Name of the layer to check
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if layer exists at workspace or PostGIS datastore level, False otherwise
        """
        try:
            # Check 1: Layer at workspace level
            if self.check_layer_exists_at_workspace_level(layer_name, workspace, url, username, password):
                return True
            
            # Check 2: Featuretype in PostGIS datastore (for PostGIS layers)
            if self.check_featuretype_exists_in_postgis_datastore(layer_name, workspace, url, username, password):
                return True
            
            return False
        except Exception as e:
            self.main.log_message(f"Error checking if layer exists: {e}")
            return False
    
    def check_layer_exists_at_workspace_level(self, layer_name, workspace, url, username, password, log_prefix=""):
        """
        Check if the layer exists at workspace level.
        
        Args:
            layer_name: Name of the layer to check
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            log_prefix: Optional prefix for log messages (e.g., "GeoPackage", "PostGIS")
            
        Returns:
            bool: True if layer exists at workspace level, False otherwise
        """
        layer_check_url = f"{url}/rest/workspaces/{workspace}/layers/{layer_name}.json"
        layer_resp = requests.get(layer_check_url, auth=(username, password), headers={'Accept': 'application/json'})
        
        if layer_resp.status_code == 200:
            prefix = f"{log_prefix} " if log_prefix else ""
            self.main.log_message(f"✓ {prefix}layer '{layer_name}' exists at workspace level")
            return True
        
        return False
    
    def check_featuretype_exists_in_postgis_datastore(self, layer_name, workspace, url, username, password):
        """
        Check if the featuretype exists in the PostGIS datastore.
        
        Args:
            layer_name: Name of the layer to check
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if featuretype exists in PostGIS datastore, False otherwise
        """
        # Try the shared PostGIS datastore
        postgis_ds_url = f"{url}/rest/workspaces/{workspace}/datastores/postgis_postgres/featuretypes/{layer_name}.json"
        postgis_response = requests.get(
            postgis_ds_url,
            auth=(username, password),
            headers={"Accept": "application/json"}
        )
        
        if postgis_response.status_code == 200:
            self.main.log_message(f"DEBUG: Found featuretype '{layer_name}' in PostGIS datastore (not yet published as layer)")
            return True
        
        return False
    
    def check_featuretype_exists_in_datastore(self, layer_name, datastore_name, workspace, url, username, password, log_prefix=""):
        """
        Check if the featuretype exists in a specific datastore.
        
        Args:
            layer_name: Name of the layer to check
            datastore_name: Name of the datastore
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            log_prefix: Optional prefix for log messages (e.g., "GeoPackage")
            
        Returns:
            bool: True if featuretype exists in datastore, False otherwise
        """
        ft_check_url = f"{url}/rest/workspaces/{workspace}/datastores/{datastore_name}/featuretypes/{layer_name}.json"
        self.main.log_message(f"DEBUG: Checking if {log_prefix.lower() if log_prefix else ''}featuretype exists at: {ft_check_url}")
        ft_resp = requests.get(ft_check_url, auth=(username, password), headers={'Accept': 'application/json'})
        
        if ft_resp.status_code == 200:
            prefix = f"{log_prefix} " if log_prefix else ""
            self.main.log_message(f"✓ {prefix}featuretype '{layer_name}' exists in datastore '{datastore_name}'")
            return True
        
        return False
