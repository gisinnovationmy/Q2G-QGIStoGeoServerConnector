"""
CORS Configuration Manager Module
Handles enabling/disabling CORS (Cross-Origin Resource Sharing) in GeoServer.
"""

import requests
from qgis.core import Qgis


class CORSManager:
    """Manages CORS configuration for GeoServer."""
    
    def __init__(self, main_instance):
        """
        Initialize the CORS manager.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def enable_cors(self, url, username, password):
        """
        Enable CORS in GeoServer by configuring the web.xml settings.
        
        GeoServer CORS is typically enabled via the REST API by setting
        the CORS filter configuration in the web.xml.
        
        Args:
            url: Base GeoServer URL (e.g., http://localhost:8080/geoserver)
            username: GeoServer admin username
            password: GeoServer admin password
            
        Returns:
            bool: True if CORS was enabled successfully, False otherwise
        """
        try:
            self.main.log_message("🔧 Attempting to enable CORS in GeoServer...")
            
            # Normalize URL
            base_url = url.rstrip('/')
            
            # Method 1: Try to enable CORS via REST API settings
            # This attempts to configure CORS through GeoServer's REST API
            cors_config = {
                "cors": {
                    "enabled": True,
                    "allowedOrigins": ["*"],
                    "allowedMethods": ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"],
                    "allowedHeaders": ["*"],
                    "exposedHeaders": ["Content-Length", "Content-Type"],
                    "supportCredentials": True,
                    "maxAge": 3600
                }
            }
            
            # Try REST API endpoint for CORS settings
            cors_url = f"{base_url}/rest/about/cors.json"
            
            self.main.log_message(f"📡 Checking CORS endpoint: {cors_url}")
            
            # First, try to GET current CORS settings
            get_response = requests.get(cors_url, auth=(username, password), timeout=10)
            
            if get_response.status_code == 200:
                self.main.log_message("✓ CORS endpoint found, attempting to enable...")
                
                # Try to PUT the CORS configuration
                put_response = requests.put(
                    cors_url,
                    auth=(username, password),
                    json=cors_config,
                    timeout=10
                )
                
                if put_response.status_code in [200, 201]:
                    self.main.log_message("✓ CORS enabled successfully via REST API", level=Qgis.Success)
                    return True
                else:
                    self.main.log_message(
                        f"⚠ CORS REST API returned status {put_response.status_code}. "
                        f"Trying alternative method...",
                        level=Qgis.Warning
                    )
            else:
                self.main.log_message(
                    f"ℹ CORS endpoint not available (status {get_response.status_code}). "
                    f"Trying alternative method...",
                    level=Qgis.Info
                )
            
            # Method 2: Enable CORS via web.xml configuration
            # This is the more reliable method for most GeoServer installations
            return self._enable_cors_via_web_xml(base_url, username, password)
            
        except requests.exceptions.Timeout:
            self.main.log_message(
                "✗ Request timeout while enabling CORS. Check GeoServer connection.",
                level=Qgis.Critical
            )
            return False
        except Exception as e:
            self.main.log_message(
                f"✗ Error enabling CORS: {str(e)}",
                level=Qgis.Critical
            )
            return False
    
    def _enable_cors_via_web_xml(self, base_url, username, password):
        """
        Enable CORS by modifying GeoServer's web.xml configuration.
        
        This method attempts to enable CORS through GeoServer's REST API
        by configuring the necessary CORS filter settings.
        
        Args:
            base_url: Base GeoServer URL
            username: GeoServer admin username
            password: GeoServer admin password
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.main.log_message("🔧 Configuring CORS via web.xml settings...")
            
            # GeoServer CORS configuration via REST API
            # This endpoint manages the CORS filter in the web.xml
            cors_filter_url = f"{base_url}/rest/manage/cors"
            
            cors_payload = {
                "enabled": True,
                "allowedOrigins": ["*"],
                "allowedMethods": ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"],
                "allowedHeaders": ["*"],
                "exposedHeaders": ["Content-Length", "Content-Type", "Access-Control-Allow-Origin"],
                "supportCredentials": True,
                "maxAge": 3600
            }
            
            # Try to POST the CORS configuration
            response = requests.post(
                cors_filter_url,
                auth=(username, password),
                json=cors_payload,
                timeout=10
            )
            
            if response.status_code in [200, 201, 204]:
                self.main.log_message(
                    "✓ CORS enabled successfully via web.xml configuration",
                    level=Qgis.Success
                )
                return True
            else:
                self.main.log_message(
                    f"⚠ web.xml configuration returned status {response.status_code}",
                    level=Qgis.Warning
                )
                return self._enable_cors_via_global_settings(base_url, username, password)
                
        except Exception as e:
            self.main.log_message(
                f"ℹ web.xml method failed: {str(e)}. Trying global settings...",
                level=Qgis.Info
            )
            return self._enable_cors_via_global_settings(base_url, username, password)
    
    def _enable_cors_via_global_settings(self, base_url, username, password):
        """
        Enable CORS via GeoServer global settings.
        
        This is the fallback method that attempts to enable CORS through
        GeoServer's global settings endpoint.
        
        Args:
            base_url: Base GeoServer URL
            username: GeoServer admin username
            password: GeoServer admin password
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.main.log_message("🔧 Configuring CORS via global settings...")
            
            # Try global settings endpoint
            settings_url = f"{base_url}/rest/settings"
            
            # First, get current settings
            get_response = requests.get(settings_url, auth=(username, password), timeout=10)
            
            if get_response.status_code == 200:
                current_settings = get_response.json()
                
                # Add CORS configuration to settings
                current_settings["cors"] = {
                    "enabled": True,
                    "allowedOrigins": ["*"],
                    "allowedMethods": ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"],
                    "allowedHeaders": ["*"],
                    "exposedHeaders": ["Content-Length", "Content-Type"],
                    "supportCredentials": True,
                    "maxAge": 3600
                }
                
                # Update settings
                put_response = requests.put(
                    settings_url,
                    auth=(username, password),
                    json=current_settings,
                    timeout=10
                )
                
                if put_response.status_code in [200, 201]:
                    self.main.log_message(
                        "✓ CORS enabled successfully via global settings",
                        level=Qgis.Success
                    )
                    return True
                else:
                    self.main.log_message(
                        f"✗ Failed to update global settings (status {put_response.status_code})",
                        level=Qgis.Critical
                    )
                    return False
            else:
                self.main.log_message(
                    f"✗ Could not retrieve global settings (status {get_response.status_code})",
                    level=Qgis.Critical
                )
                return False
                
        except Exception as e:
            self.main.log_message(
                f"✗ Error configuring CORS via global settings: {str(e)}",
                level=Qgis.Critical
            )
            return False
    
    def disable_cors(self, url, username, password):
        """
        Disable CORS in GeoServer.
        
        Args:
            url: Base GeoServer URL
            username: GeoServer admin username
            password: GeoServer admin password
            
        Returns:
            bool: True if CORS was disabled successfully, False otherwise
        """
        try:
            self.main.log_message("🔧 Attempting to disable CORS in GeoServer...")
            
            base_url = url.rstrip('/')
            
            cors_config = {
                "cors": {
                    "enabled": False
                }
            }
            
            # Try REST API endpoint
            cors_url = f"{base_url}/rest/about/cors.json"
            
            response = requests.put(
                cors_url,
                auth=(username, password),
                json=cors_config,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                self.main.log_message("✓ CORS disabled successfully", level=Qgis.Success)
                return True
            else:
                self.main.log_message(
                    f"✗ Failed to disable CORS (status {response.status_code})",
                    level=Qgis.Critical
                )
                return False
                
        except Exception as e:
            self.main.log_message(
                f"✗ Error disabling CORS: {str(e)}",
                level=Qgis.Critical
            )
            return False
    
    def get_cors_status(self, url, username, password):
        """
        Get the current CORS status in GeoServer.
        
        Args:
            url: Base GeoServer URL
            username: GeoServer admin username
            password: GeoServer admin password
            
        Returns:
            dict: CORS configuration status, or None if unable to retrieve
        """
        try:
            base_url = url.rstrip('/')
            cors_url = f"{base_url}/rest/about/cors.json"
            
            response = requests.get(cors_url, auth=(username, password), timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            self.main.log_message(f"Error retrieving CORS status: {str(e)}", level=Qgis.Warning)
            return None
