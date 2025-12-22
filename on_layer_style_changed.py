"""
On Layer Style Changed Module
Handles QGIS layer style changes by refreshing the SLD on GeoServer.
Extracted from main.py for better code organization and maintainability.
"""


class LayerStyleChangeHandler:
    """Handles QGIS layer style changes and SLD refresh operations."""
    
    def __init__(self, main_instance):
        """
        Initialize the layer style change handler.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def on_layer_style_changed(self, layer):
        """
        Handle QGIS layer style changes by refreshing the SLD.
        
        This method is triggered when a QGIS layer's style changes and will:
        1. Get current GeoServer connection details
        2. Validate workspace selection
        3. Upload updated SLD style to GeoServer
        4. Refresh the styles list UI
        
        Args:
            layer: QGIS layer object that had its style changed
        """
        self.main.log_message(f"Layer style changed for: {layer.name()}")
        
        # Get connection details and workspace
        connection_details = self._get_connection_details()
        if not connection_details:
            return
        
        url, username, password, workspace_name = connection_details
        
        # Get layer name mapping
        layer_name = self._get_layer_name(layer)
        
        # Refresh the SLD for this layer
        self._refresh_layer_sld(layer, layer_name, url, username, password, workspace_name)
        
        # Refresh the styles list UI
        self.main.load_layer_styles()
    
    def _get_connection_details(self):
        """
        Get and validate GeoServer connection details and workspace selection.
        
        Returns:
            tuple: (url, username, password, workspace_name) or None if validation fails
        """
        # Get current GeoServer connection details
        url = self.main.get_base_url()
        username = self.main.username_input.text().strip()
        password = self.main.password_input.text().strip()
        
        # Get selected workspace
        selected_workspace_items = self.main.workspaces_list.selectedItems()
        if not selected_workspace_items:
            self.main.log_message("No workspace selected, skipping SLD refresh.")
            return None
        
        workspace_name = selected_workspace_items[0].text()
        return url, username, password, workspace_name
    
    def _get_layer_name(self, layer):
        """
        Get the layer name from the layer name mapping or use the layer's name.
        
        Args:
            layer: QGIS layer object
            
        Returns:
            str: Layer name to use for GeoServer operations
        """
        return self.main.layer_name_mapping.get(layer.id(), layer.name())
    
    def _refresh_layer_sld(self, layer, layer_name, url, username, password, workspace_name):
        """
        Refresh the SLD for the specified layer on GeoServer.
        
        Args:
            layer: QGIS layer object
            layer_name: Layer name for GeoServer
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            workspace_name: Target workspace name
        """
        # Refresh the SLD for this layer
        self.main.upload_sld_style(layer, layer_name, url, username, password, workspace_name)
