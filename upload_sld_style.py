"""
Upload SLD Style Module
Handles SLD style upload and layer association in GeoServer.
Extracted from main.py for better code organization and maintainability.
"""

import requests
from qgis.core import Qgis, QgsRasterLayer
from qgis.PyQt.QtWidgets import QMessageBox


class SLDStyleUploader:
    """Handles SLD style upload and layer association in GeoServer."""
    
    def __init__(self, main_instance):
        """
        Initialize the SLD style uploader.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def upload_sld_style(self, layer, layer_name, workspace, url, username, password, sld_content=None):
        """
        Exports and uploads the SLD style for a given layer and assigns it.
        
        Returns:
            bool: True if SLD was counted (style already existed), False if not counted (new style created)
        """
        try:
            self.main.log_message(f"Uploading style for layer '{layer_name}'...")

            # If no custom SLD content is provided, export it from the layer
            if sld_content is None:
                self.main.log_message("No custom SLD provided, exporting from layer style using SLD Window Manager.")
                sld_content = self.main.sld_window_manager._extract_sld_content(layer)

            if not sld_content:
                self.main.log_message(f"No SLD content available for layer '{layer_name}'. Skipping style upload.", level=Qgis.Warning)
                return False

            # Use SLD 1.1 directly without conversion
            if 'xmlns:se=' in sld_content or 'se:' in sld_content:
                self.main.log_message(f"Using SLD 1.1.0 (SE format) directly for layer '{layer_name}'")
            else:
                self.main.log_message(f"Using SLD format directly for layer '{layer_name}'")

            style_name = layer_name
            
            # SLD 1.1 upload requires proper content type - GeoServer supports both SLD 1.0 and 1.1
            headers = {
                'Content-Type': 'application/vnd.ogc.sld+xml',
            }

            # Check if style exists in workspace
            check_style_url = f"{url}/rest/workspaces/{workspace}/styles/{style_name}.json"
            check_response = requests.get(check_style_url, auth=(username, password))

            sld_was_counted = False  # Track if we should count this SLD in batch report

            if check_response.status_code == 200:
                # Style EXISTS - use PUT to overwrite and COUNT it
                self.main.log_message(f"✓ Style '{style_name}' exists - using PUT to overwrite")
                style_url = f"{url}/rest/workspaces/{workspace}/styles/{style_name}.sld?raw=true"
                response = requests.put(
                    style_url,
                    auth=(username, password),
                    headers=headers,
                    data=sld_content.encode('utf-8')
                )
                sld_was_counted = True  # Mark as counted
                self.main.log_message(f"Overwriting existing style '{style_name}' in workspace '{workspace}'")
            else:
                # Style DOESN'T EXIST - use POST to create, then PUT to overwrite, COUNT the second PUT
                self.main.log_message(f"✗ Style '{style_name}' does not exist - using POST to create")
                
                # Step 1: POST to create the style (NOT counted)
                post_url = f"{url}/rest/workspaces/{workspace}/styles?raw=true"
                params = {'name': style_name}
                post_response = requests.post(
                    post_url,
                    params=params,
                    auth=(username, password),
                    headers=headers,
                    data=sld_content.encode('utf-8')
                )
                
                if post_response.status_code not in [200, 201]:
                    self.main.log_message(f"Failed to create style '{style_name}' with POST. Status: {post_response.status_code}\n{post_response.text}", level=Qgis.Critical)
                    return False
                
                self.main.log_message(f"📝 Style '{style_name}' created successfully with POST")
                
                # Step 2: PUT to overwrite (COUNTED in batch report)
                self.main.log_message(f"→ Now overwriting with PUT (counted in batch report)")
                style_url = f"{url}/rest/workspaces/{workspace}/styles/{style_name}.sld?raw=true"
                response = requests.put(
                    style_url,
                    auth=(username, password),
                    headers=headers,
                    data=sld_content.encode('utf-8')
                )
                sld_was_counted = True  # Count the second PUT overwrite
                self.main.log_message(f"Overwriting new style '{style_name}' in workspace '{workspace}'")

            if response.status_code not in [200, 201]:
                self.main.log_message(f"Failed to upload style '{style_name}'. Status: {response.status_code}\n{response.text}", level=Qgis.Critical)
                return False

            self.main.log_message(f"Style '{style_name}' uploaded successfully.")

            # Assign the style to the layer
            layer_update_url = f"{url}/rest/layers/{workspace}:{layer_name}"
            layer_payload = {
                "layer": {
                    "defaultStyle": {
                        "name": style_name
                    },
                    "enabled": True
                }
            }
            headers_json = {'Content-Type': 'application/json'}
            
            update_response = requests.put(
                layer_update_url,
                auth=(username, password),
                json=layer_payload,
                headers=headers_json
            )

            if update_response.status_code == 200:
                self.main.log_message(f"Successfully assigned style '{style_name}' to layer '{layer_name}'.")
            else:
                self.main.log_message(f"Failed to assign style '{style_name}' to layer '{layer_name}'. Status: {update_response.status_code}\n{update_response.text}", level=Qgis.Critical)

            return sld_was_counted  # Return whether this SLD should be counted

        except Exception as e:
            self.main.log_message(f"An error occurred during SLD style upload for '{layer_name}': {e}", level=Qgis.Critical)
            return False
