"""
Layer Metadata Extractor Module
Handles retrieval of layer metadata, styles, and data store information from GeoServer.
"""

import requests
import json
from qgis.core import Qgis, QgsMessageLog


class LayerMetadataExtractor:
    """Extracts layer metadata, styles, and data store information from GeoServer."""
    
    def __init__(self):
        self.timeout = 30
    
    def log_message(self, message, level=Qgis.Info):
        """Log a message to QGIS message log."""
        QgsMessageLog.logMessage(message, "Q2G", level=level)
    
    def get_all_workspaces(self, url, auth):
        """
        Get list of all workspaces.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
        
        Returns:
            List of workspace names or empty list on error
        """
        try:
            workspaces_url = f"{url}/rest/workspaces.json"
            response = requests.get(workspaces_url, auth=auth, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                workspaces = [ws['name'] for ws in data.get('workspaces', [])]
                return workspaces
            else:
                self.log_message(f"Failed to get workspaces: {response.status_code}", level=Qgis.Warning)
                return []
        except Exception as e:
            self.log_message(f"Error getting workspaces: {str(e)}", level=Qgis.Warning)
            return []
    
    def get_layer_metadata(self, url, auth, workspace, layer_name):
        """
        Get complete layer metadata.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            workspace: Workspace name
            layer_name: Layer name
        
        Returns:
            Dict with layer metadata or None on error
        """
        try:
            layer_url = f"{url}/rest/layers/{workspace}:{layer_name}.json"
            response = requests.get(layer_url, auth=auth, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.log_message(f"Failed to get layer metadata for {layer_name}: {response.status_code}", 
                               level=Qgis.Warning)
                return None
        except Exception as e:
            self.log_message(f"Error getting layer metadata: {str(e)}", level=Qgis.Warning)
            return None
    
    def get_layer_style(self, url, auth, workspace, layer_name):
        """
        Get SLD style for a layer.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            workspace: Workspace name
            layer_name: Layer name
        
        Returns:
            SLD content as string or None on error
        """
        try:
            print(f"DEBUG: get_layer_style called for {workspace}:{layer_name}")
            # Get layer metadata to find default style
            layer_metadata = self.get_layer_metadata(url, auth, workspace, layer_name)
            if not layer_metadata or 'layer' not in layer_metadata:
                print(f"DEBUG: No layer metadata found")
                return None
            
            default_style = layer_metadata['layer'].get('defaultStyle', {})
            if not default_style or 'name' not in default_style:
                print(f"DEBUG: No default style found in layer metadata")
                return None
            
            style_name = default_style['name']
            print(f"DEBUG: Default style name: {style_name}")
            
            # Remove workspace prefix if present
            if ':' in style_name:
                style_name = style_name.split(':')[1]
            
            # Try workspace-specific style first
            style_url = f"{url}/rest/workspaces/{workspace}/styles/{style_name}.sld"
            print(f"DEBUG: Trying workspace style URL: {style_url}")
            response = requests.get(style_url, auth=auth, timeout=self.timeout)
            
            if response.status_code == 200:
                print(f"DEBUG: Got style from workspace")
                return response.text
            
            # Try global styles
            style_url = f"{url}/rest/styles/{style_name}.sld"
            print(f"DEBUG: Trying global style URL: {style_url}")
            response = requests.get(style_url, auth=auth, timeout=self.timeout)
            
            if response.status_code == 200:
                print(f"DEBUG: Got style from global styles")
                return response.text
            
            self.log_message(f"Failed to get style {style_name}: {response.status_code}", 
                           level=Qgis.Warning)
            print(f"DEBUG: Failed to get style: {response.status_code}")
            return None
        except Exception as e:
            self.log_message(f"Error getting layer style: {str(e)}", level=Qgis.Warning)
            print(f"DEBUG: Exception in get_layer_style: {str(e)}")
            return None
    
    def get_layer_data_store(self, url, auth, workspace, layer_name):
        """
        Get data store information for a layer.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            workspace: Workspace name
            layer_name: Layer name
        
        Returns:
            Dict with data store info or None on error
        """
        try:
            print(f"DEBUG: get_layer_data_store called for {workspace}:{layer_name}")
            # Get feature type info to find data store
            feature_type = self.get_feature_type_info(url, auth, workspace, layer_name)
            if not feature_type or 'featureType' not in feature_type:
                print(f"DEBUG: No feature type found for {layer_name}")
                return None
            
            store_info = feature_type['featureType'].get('store', {})
            store_name = store_info.get('name')
            print(f"DEBUG: Store name from feature type: {store_name}")
            
            if not store_name:
                return None
            
            # Remove workspace prefix if present
            if ':' in store_name:
                store_name = store_name.split(':')[1]
            
            # Fetch data store config
            datastore_url = f"{url}/rest/workspaces/{workspace}/datastores/{store_name}.json"
            print(f"DEBUG: Fetching datastore from: {datastore_url}")
            response = requests.get(datastore_url, auth=auth, timeout=self.timeout)
            
            if response.status_code == 200:
                print(f"DEBUG: Got datastore config successfully")
                return response.json()
            else:
                self.log_message(f"Failed to get data store {store_name}: {response.status_code}", 
                               level=Qgis.Warning)
                print(f"DEBUG: Failed to get datastore: {response.status_code}")
                return None
        except Exception as e:
            self.log_message(f"Error getting layer data store: {str(e)}", level=Qgis.Warning)
            print(f"DEBUG: Exception in get_layer_data_store: {str(e)}")
            return None
    
    def get_feature_type_info(self, url, auth, workspace, layer_name):
        """
        Get feature type information for a layer.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            workspace: Workspace name
            layer_name: Layer name
        
        Returns:
            Dict with feature type info or None on error
        """
        try:
            # First try direct workspace/featuretypes path
            feature_type_url = f"{url}/rest/workspaces/{workspace}/featuretypes/{layer_name}.json"
            print(f"DEBUG: Trying feature type URL: {feature_type_url}")
            response = requests.get(feature_type_url, auth=auth, timeout=self.timeout)
            
            if response.status_code == 200:
                print(f"DEBUG: Got feature type from direct URL")
                return response.json()
            
            # If that fails, get the layer info first to find the datastore
            print(f"DEBUG: Direct URL failed ({response.status_code}), trying via layer resource")
            layer_url = f"{url}/rest/layers/{workspace}:{layer_name}.json"
            layer_response = requests.get(layer_url, auth=auth, timeout=self.timeout)
            
            if layer_response.status_code == 200:
                layer_data = layer_response.json()
                resource = layer_data.get('layer', {}).get('resource', {})
                resource_href = resource.get('href', '')
                
                if resource_href:
                    print(f"DEBUG: Found resource href: {resource_href}")
                    # Fetch the feature type from the resource href
                    ft_response = requests.get(resource_href, auth=auth, timeout=self.timeout)
                    if ft_response.status_code == 200:
                        print(f"DEBUG: Got feature type from resource href")
                        return ft_response.json()
            
            self.log_message(f"Failed to get feature type for {layer_name}: {response.status_code}", 
                           level=Qgis.Warning)
            return None
        except Exception as e:
            self.log_message(f"Error getting feature type info: {str(e)}", level=Qgis.Warning)
            print(f"DEBUG: Exception in get_feature_type_info: {str(e)}")
            return None
    
    def get_coverage_info(self, url, auth, workspace, layer_name):
        """
        Get coverage information for a raster layer.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            workspace: Workspace name
            layer_name: Layer name
        
        Returns:
            Dict with coverage info or None on error
        """
        try:
            coverage_url = f"{url}/rest/workspaces/{workspace}/coverages/{layer_name}.json"
            response = requests.get(coverage_url, auth=auth, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.log_message(f"Failed to get coverage for {layer_name}: {response.status_code}", 
                               level=Qgis.Warning)
                return None
        except Exception as e:
            self.log_message(f"Error getting coverage info: {str(e)}", level=Qgis.Warning)
            return None
    
    def layer_exists(self, url, auth, workspace, layer_name):
        """
        Check if a layer exists in a workspace.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            workspace: Workspace name
            layer_name: Layer name
        
        Returns:
            True if layer exists, False otherwise
        """
        try:
            layer_url = f"{url}/rest/layers/{workspace}:{layer_name}.json"
            response = requests.get(layer_url, auth=auth, timeout=self.timeout)
            return response.status_code == 200
        except Exception as e:
            self.log_message(f"Error checking if layer exists: {str(e)}", level=Qgis.Warning)
            return False
    
    def workspace_exists(self, url, auth, workspace):
        """
        Check if a workspace exists.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            workspace: Workspace name
        
        Returns:
            True if workspace exists, False otherwise
        """
        try:
            workspace_url = f"{url}/rest/workspaces/{workspace}.json"
            response = requests.get(workspace_url, auth=auth, timeout=self.timeout)
            return response.status_code == 200
        except Exception as e:
            self.log_message(f"Error checking if workspace exists: {str(e)}", level=Qgis.Warning)
            return False
