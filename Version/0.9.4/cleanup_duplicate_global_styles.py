"""
Cleanup Duplicate Global Styles Module
Handles cleanup of duplicate global styles that should be workspace-scoped.
Extracted from main.py for better code organization and maintainability.
"""

import requests


class DuplicateGlobalStylesCleaner:
    """Handles cleanup of duplicate global styles in GeoServer."""
    
    def __init__(self, main_instance):
        """
        Initialize the duplicate global styles cleaner.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def cleanup_duplicate_global_styles(self, workspace, url, username, password):
        """
        Delete duplicate global styles that should be workspace-scoped.
        
        This method will:
        1. Fetch all global styles from GeoServer
        2. Fetch all workspace-scoped styles
        3. Identify global styles that have workspace equivalents
        4. Delete the duplicate global styles
        
        Args:
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        try:
            # Get global and workspace styles
            global_styles = self._fetch_global_styles(url, username, password)
            if global_styles is None:
                return
            
            workspace_style_names = self._fetch_workspace_style_names(workspace, url, username, password)
            
            # Delete duplicate global styles
            deleted_count = self._delete_duplicate_global_styles(global_styles, workspace_style_names, url, username, password)
            
            if deleted_count > 0:
                self.main.log_message(f"✓ Cleaned up {deleted_count} duplicate global style(s)")
        
        except Exception as e:
            self.main.log_message(f"Error during duplicate global style cleanup: {e}")
    
    def _fetch_global_styles(self, url, username, password):
        """
        Fetch all global styles from GeoServer.
        
        Args:
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            list: List of global styles or None if fetch failed
        """
        global_styles_url = f"{url}/rest/styles.json"
        response = requests.get(global_styles_url, auth=(username, password))
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        styles = data.get('styles', {}).get('style', [])
        
        # Ensure styles is always a list
        if not isinstance(styles, list):
            styles = [styles] if styles else []
        
        return styles
    
    def _fetch_workspace_style_names(self, workspace, url, username, password):
        """
        Fetch all workspace-scoped style names.
        
        Args:
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            set: Set of workspace style names
        """
        workspace_styles_url = f"{url}/rest/workspaces/{workspace}/styles.json"
        ws_response = requests.get(workspace_styles_url, auth=(username, password))
        
        workspace_style_names = set()
        if ws_response.status_code == 200:
            ws_data = ws_response.json()
            ws_styles = ws_data.get('styles', {}).get('style', [])
            
            # Ensure ws_styles is always a list
            if not isinstance(ws_styles, list):
                ws_styles = [ws_styles] if ws_styles else []
            
            workspace_style_names = {s.get('name', '') for s in ws_styles}
        
        return workspace_style_names
    
    def _delete_duplicate_global_styles(self, global_styles, workspace_style_names, url, username, password):
        """
        Delete global styles that have workspace equivalents.
        
        Args:
            global_styles: List of global styles
            workspace_style_names: Set of workspace style names
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            int: Number of styles deleted
        """
        deleted_count = 0
        
        # Delete global styles that have workspace equivalents
        for style in global_styles:
            style_name = style.get('name', '')
            if not style_name:
                continue
            
            # If this style exists in workspace scope, delete the global duplicate
            if style_name in workspace_style_names:
                if self._delete_global_style(style_name, url, username, password):
                    deleted_count += 1
        
        return deleted_count
    
    def _delete_global_style(self, style_name, url, username, password):
        """
        Delete a specific global style.
        
        Args:
            style_name: Name of the style to delete
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        self.main.log_message(f"🗑️ Deleting duplicate global style '{style_name}' (workspace version exists)...")
        
        delete_url = f"{url}/rest/styles/{style_name}"
        delete_response = requests.delete(delete_url, auth=(username, password), params={'purge': 'true'})
        
        if delete_response.status_code in [200, 204]:
            self.main.log_message(f"✓ Deleted duplicate global style '{style_name}'")
            return True
        else:
            self.main.log_message(f"⚠ Failed to delete duplicate global style {style_name}: {delete_response.status_code}")
            return False
