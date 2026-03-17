"""
Reset All Caches Module
Handles resetting all GeoServer tile caches using the GeoWebCache REST API.
Extracted from main.py for better code organization and maintainability.
"""

import requests
import traceback
from qgis.PyQt.QtWidgets import QMessageBox


class CacheResetManager:
    """Handles GeoServer cache reset operations using GeoWebCache REST API."""
    
    def __init__(self, main_instance):
        """
        Initialize the cache reset manager.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def reset_all_caches(self):
        """
        Reset all GeoServer tile caches using the GeoWebCache REST API.
        
        This method will:
        1. Validate connection details
        2. Confirm with user before proceeding
        3. Send mass truncation request to GeoWebCache
        4. Handle response and provide feedback
        """
        # Get and validate connection details
        connection_details = self._get_connection_details()
        if not connection_details:
            return
        
        url, username, password = connection_details
        
        # Confirm with user before proceeding
        if not self._confirm_cache_reset():
            return
        
        # Execute cache reset
        self._execute_cache_reset(url, username, password)
    
    def _get_connection_details(self):
        """
        Get and validate connection details.
        
        Returns:
            tuple: (url, username, password) or None if validation fails
        """
        url = self.main.get_base_url()
        username = self.main.username_input.text().strip()
        password = self.main.password_input.text().strip()
        
        if not all([url, username, password]):
            QMessageBox.warning(self.main, "Input Error", "Please fill in all GeoServer connection details.")
            return None
        
        return url, username, password
    
    def _confirm_cache_reset(self):
        """
        Confirm with user before proceeding with cache reset.
        
        Returns:
            bool: True if user confirmed, False if cancelled
        """
        reply = QMessageBox.question(
            self.main, 
            "Confirm Cache Reset", 
            "This will delete ALL cached tiles for every layer. This action cannot be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
            QMessageBox.StandardButton.No
        )
        
        return reply == QMessageBox.StandardButton.Yes
    
    def _execute_cache_reset(self, url, username, password):
        """
        Execute the cache reset operation.
        
        Args:
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        try:
            # Construct the GWC REST API URL for mass cache truncation
            gwc_url = f"{url}/gwc/rest/masstruncate"
            self.main.log_message(f"🔄 Sending mass cache truncation request to: {gwc_url}")

            # XML payload to truncate all layers
            xml_payload = "<truncateAll></truncateAll>"
            self.main.log_message(f"Cache reset payload: {xml_payload}")

            # Make the POST request to truncate all caches
            response = self._send_truncation_request(gwc_url, xml_payload, username, password)
            
            # Handle response
            self._handle_response(response)
                
        except Exception as e:
            self._handle_exception(e)
    
    def _send_truncation_request(self, gwc_url, xml_payload, username, password):
        """
        Send the cache truncation request to GeoWebCache.
        
        Args:
            gwc_url: GeoWebCache REST API URL
            xml_payload: XML payload for truncation
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            requests.Response: Response from the server
        """
        response = requests.post(
            gwc_url, 
            data=xml_payload.encode('utf-8'), 
            auth=(username, password), 
            headers={"Content-type": "text/xml"}
        )
        
        self.main.log_message(f"Mass cache truncation response status: {response.status_code}")
        self.main.log_message(f"Mass cache truncation response text: {response.text[:500] if response.text else 'Empty response'}")
        
        return response
    
    def _handle_response(self, response):
        """
        Handle the response from the cache truncation request.
        
        Args:
            response: requests.Response object
        """
        if response.status_code in [200, 201, 202, 204]:
            QMessageBox.information(
                self.main, 
                "Success", 
                "✓ All GeoServer caches have been successfully reset.\n\nTiles will be re-rendered on next WMS request.\n\nRefresh your browser to see updated colors."
            )
            self.main.log_message("✓ Successfully reset all GeoServer caches.")
        else:
            error_msg = f"Failed to reset caches. Status code: {response.status_code}. Response: {response.text}"
            QMessageBox.critical(self.main, "Error", error_msg)
            self.main.log_message(f"✗ {error_msg}")
    
    def _handle_exception(self, exception):
        """
        Handle exceptions during cache reset operation.
        
        Args:
            exception: Exception that occurred
        """
        error_msg = f"Error resetting caches: {str(exception)}"
        QMessageBox.critical(self.main, "Error", error_msg)
        self.main.log_message(f"✗ {error_msg}")
        self.main.log_message(f"Traceback: {traceback.format_exc()}")
