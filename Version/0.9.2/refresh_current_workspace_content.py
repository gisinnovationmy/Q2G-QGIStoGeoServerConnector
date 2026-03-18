"""
Refresh Current Workspace Content Module
Handles refreshing layers, datastores, and styles for the current workspace.
Extracted from main.py for better code organization and maintainability.
"""


class WorkspaceContentRefresher:
    """Handles refreshing workspace content including layers, datastores, and styles."""
    
    def __init__(self, main_instance):
        """
        Initialize the workspace content refresher.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def refresh_current_workspace_content(self):
        """
        Refresh layers, datastores, and styles for the current workspace while preserving selection.
        
        This method refreshes all workspace content components:
        - Workspace layers
        - Datastores and coveragestores
        - Layer styles
        """
        try:
            # Get current workspace selection
            current_workspace = self._get_current_workspace()
            
            if current_workspace:
                self._refresh_workspace_components(current_workspace)
            else:
                self.main.log_message("No workspace selected for refresh")
                
        except Exception as e:
            self.main.log_message(f"Error refreshing workspace content: {str(e)}")
    
    def _get_current_workspace(self):
        """
        Get the currently selected workspace.
        
        Returns:
            str: Current workspace name or None if no workspace is selected
        """
        current_workspace = None
        if self.main.workspaces_list.currentItem():
            current_workspace = self.main.workspaces_list.currentItem().text()
        return current_workspace
    
    def _refresh_workspace_components(self, current_workspace):
        """
        Refresh all components for the specified workspace.
        
        Args:
            current_workspace: Name of the workspace to refresh
        """
        self.main.log_message(f"Refreshing content for workspace: {current_workspace}")
        
        # Refresh layers, datastores, and styles for current workspace
        self.main.load_workspace_layers()
        self.main.load_stores() 
        
        # Refresh styles for current workspace
        self.main.load_layer_styles()
            
        self.main.log_message(f"✓ Refreshed workspace content for: {current_workspace}")
