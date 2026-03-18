"""
Data Store Manager Module
Handles data store operations for layer copy/move between workspaces.
"""

import requests
import json
from qgis.core import Qgis, QgsMessageLog


class DataStoreManager:
    """Manages data store operations for layer copy/move."""
    
    def __init__(self):
        self.timeout = 30
    
    def log_message(self, message, level=Qgis.Info):
        """Log a message to QGIS message log."""
        QgsMessageLog.logMessage(message, "Q2G", level=level)
    
    def get_data_store_config(self, url, auth, workspace, datastore_name):
        """
        Get complete data store configuration.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            workspace: Workspace name
            datastore_name: Data store name
        
        Returns:
            Dict with data store config or None on error
        """
        try:
            datastore_url = f"{url}/rest/workspaces/{workspace}/datastores/{datastore_name}.json"
            response = requests.get(datastore_url, auth=auth, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                self.log_message(f"Failed to get data store config: {response.status_code}", 
                               level=Qgis.Warning)
                return None
        except Exception as e:
            self.log_message(f"Error getting data store config: {str(e)}", level=Qgis.Warning)
            return None
    
    def data_store_exists(self, url, auth, workspace, datastore_name):
        """
        Check if a data store exists in a workspace.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            workspace: Workspace name
            datastore_name: Data store name
        
        Returns:
            True if data store exists, False otherwise
        """
        try:
            datastore_url = f"{url}/rest/workspaces/{workspace}/datastores/{datastore_name}.json"
            response = requests.get(datastore_url, auth=auth, timeout=self.timeout)
            return response.status_code == 200
        except Exception as e:
            self.log_message(f"Error checking data store existence: {str(e)}", level=Qgis.Warning)
            return False
    
    def create_data_store_reference(self, url, auth, target_workspace, datastore_config):
        """
        Create a reference to a data store in target workspace.
        If data store already exists, use it. Otherwise create new one.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            target_workspace: Target workspace name
            datastore_config: Data store configuration dict
        
        Returns:
            Tuple of (success: bool, datastore_name: str, message: str)
        """
        try:
            if not datastore_config or 'dataStore' not in datastore_config:
                return False, None, "Invalid data store config"
            
            ds_info = datastore_config['dataStore']
            datastore_name = ds_info.get('name')
            
            if not datastore_name:
                return False, None, "Data store name not found"
            
            # Check if data store already exists in target workspace
            if self.data_store_exists(url, auth, target_workspace, datastore_name):
                self.log_message(f"Data store '{datastore_name}' already exists in workspace '{target_workspace}'")
                return True, datastore_name, f"Using existing data store '{datastore_name}'"
            
            # Create new data store in target workspace
            create_url = f"{url}/rest/workspaces/{target_workspace}/datastores"
            
            # Prepare payload (remove id and workspace references)
            payload = {
                'dataStore': {
                    'name': datastore_name,
                    'type': ds_info.get('type', 'PostGIS'),
                    'enabled': ds_info.get('enabled', True),
                    'connectionParameters': ds_info.get('connectionParameters', {})
                }
            }
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                create_url,
                auth=auth,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code in [200, 201]:
                self.log_message(f"✓ Data store '{datastore_name}' created in workspace '{target_workspace}'")
                return True, datastore_name, f"Created data store '{datastore_name}'"
            else:
                error_msg = f"Failed to create data store: {response.status_code} - {response.text}"
                self.log_message(error_msg, level=Qgis.Warning)
                return False, None, error_msg
        
        except Exception as e:
            error_msg = f"Error creating data store reference: {str(e)}"
            self.log_message(error_msg, level=Qgis.Warning)
            return False, None, error_msg
    
    def validate_data_store_access(self, url, auth, workspace, datastore_name):
        """
        Validate that a data store is accessible.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            workspace: Workspace name
            datastore_name: Data store name
        
        Returns:
            Tuple of (accessible: bool, message: str)
        """
        try:
            if not self.data_store_exists(url, auth, workspace, datastore_name):
                return False, f"Data store '{datastore_name}' not found in workspace '{workspace}'"
            
            # Try to get data store config to verify accessibility
            config = self.get_data_store_config(url, auth, workspace, datastore_name)
            if config:
                return True, f"Data store '{datastore_name}' is accessible"
            else:
                return False, f"Data store '{datastore_name}' is not accessible"
        
        except Exception as e:
            return False, f"Error validating data store access: {str(e)}"
