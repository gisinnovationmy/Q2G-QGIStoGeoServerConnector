"""
GeoPackage Layer Exists in Datastore Module
Handles checking if a GeoPackage layer exists in its datastore and publishing if needed.
Extracted from main.py for better code organization and maintainability.
"""

import requests


class GeoPackageLayerExistenceChecker:
    """Handles checking GeoPackage layer existence and publishing in GeoServer."""
    
    def __init__(self, main_instance):
        """
        Initialize the GeoPackage layer existence checker.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def geopackage_layer_exists_in_datastore(self, layer_name, gpkg_datastore_name, workspace, url, username, password):
        """
        Check if a GeoPackage layer exists in its datastore (similar to PostGIS featuretype check).
        
        This method will:
        1. Check if the layer exists at workspace level (using shared LayerExistenceChecker)
        2. Check if the featuretype exists in the datastore
        3. If featuretype exists but layer doesn't, publish it as a layer
        4. Return True if layer exists or was successfully published
        
        Args:
            layer_name: Name of the layer to check
            gpkg_datastore_name: Name of the GeoPackage datastore
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if layer exists or was published, False otherwise
        """
        try:
            # Check if the layer exists in the workspace first (using shared checker)
            if self.main.layer_existence_checker.check_layer_exists_at_workspace_level(layer_name, workspace, url, username, password, "GeoPackage"):
                return True
            
            # Check if the featuretype exists in the datastore
            if self.main.layer_existence_checker.check_featuretype_exists_in_datastore(layer_name, gpkg_datastore_name, workspace, url, username, password, "GeoPackage"):
                # Try to publish it as a layer
                return self._publish_featuretype_as_layer(layer_name, gpkg_datastore_name, workspace, url, username, password)
            
            return False
        except Exception as e:
            self.main.log_message(f"Error checking GeoPackage layer availability: {e}")
            return False
    
    
    def _publish_featuretype_as_layer(self, layer_name, gpkg_datastore_name, workspace, url, username, password):
        """
        Publish a featuretype as a layer.
        
        Args:
            layer_name: Name of the layer to publish
            gpkg_datastore_name: Name of the GeoPackage datastore
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if publishing was successful, False otherwise
        """
        self.main.log_message(f"ℹ️ GeoPackage featuretype '{layer_name}' exists but layer doesn't. Publishing featuretype as layer...")
        
        layer_pub_url = f"{url}/rest/workspaces/{workspace}/layers/{layer_name}"
        layer_payload = self._create_layer_payload(layer_name, gpkg_datastore_name, workspace)
        
        layer_pub_resp = requests.put(
            layer_pub_url,
            json=layer_payload,
            auth=(username, password),
            headers={"Content-Type": "application/json"}
        )
        
        if layer_pub_resp.status_code in [200, 201]:
            self.main.log_message(f"✓ Published GeoPackage featuretype '{layer_name}' as layer")
            return True
        else:
            self.main.log_message(f"⚠️ Could not publish featuretype as layer: {layer_pub_resp.status_code}")
            return False
    
    def _create_layer_payload(self, layer_name, gpkg_datastore_name, workspace):
        """
        Create the JSON payload for layer publishing.
        
        Args:
            layer_name: Name of the layer
            gpkg_datastore_name: Name of the GeoPackage datastore
            workspace: Target workspace name
            
        Returns:
            dict: JSON payload for layer publishing
        """
        return {
            "layer": {
                "name": layer_name,
                "type": "VECTOR",
                "resource": {
                    "@class": "featureType",
                    "name": layer_name,
                    "store": {
                        "@class": "dataStore",
                        "name": f"{workspace}:{gpkg_datastore_name}"
                    }
                },
                "enabled": True
            }
        }
