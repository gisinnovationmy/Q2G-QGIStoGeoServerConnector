"""
Verify and Publish Tasks Module
Handles verification and publishing of GeoServer import tasks.
Extracted from main.py for better code organization and maintainability.
"""

import requests
from qgis.core import Qgis


class TaskVerificationPublisher:
    """Handles verification and publishing of GeoServer import tasks."""
    
    def __init__(self, main_instance):
        """
        Initialize the task verification publisher.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def verify_and_publish_tasks(self, layer, import_id, workspace, url, username, password):
        """
        Verify import tasks and publish layers.
        
        Args:
            layer: QGIS layer object
            import_id: GeoServer import ID
            workspace: Target GeoServer workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        
        Returns:
            bool: True if at least one layer was published, False otherwise
        """
        try:
            self.main.log_message(f"Step 5: Verifying and publishing layers from import {import_id}")
            
            tasks_url = f"{url}/rest/imports/{import_id}/tasks"
            tasks_response = requests.get(tasks_url, auth=(username, password))
            
            if tasks_response.status_code != 200:
                self.main.log_message(f"Failed to get import tasks: {tasks_response.status_code}")
                return False
            
            tasks_data = tasks_response.json()
            layers_published = 0
            
            # Debug: Log all tasks
            all_tasks = tasks_data.get('tasks', [])
            self.main.log_message(f"DEBUG: Total tasks in import: {len(all_tasks)}")
            for idx, t in enumerate(all_tasks):
                published_name = t.get('layer', {}).get('name', 'N/A')
                self.main.log_message(f"DEBUG: Task {idx}: ID={t.get('id')}, State={t.get('state')}, Layer={published_name}")
            
            # Process each task
            for task in all_tasks:
                task_state = task.get('state', 'UNKNOWN')
                task_id = task.get('id')
                
                self.main.log_message(f"DEBUG: Task {task_id} - State: {task_state}")
                
                if task_state == 'READY':
                    layers_published += self._handle_ready_task(task_id, import_id, url, username, password)
                
                elif task_state == 'COMPLETE':
                    layers_published += 1
                    self.main.log_message(f"✓ Task {task_id} completed successfully")
                
                elif task_state == 'NO_CRS':
                    layers_published += self._handle_no_crs_task(task_id, layer, import_id, url, username, password)
                
                elif task_state == 'NO_FORMAT':
                    self.main.log_message(f"⚠️ Task {task_id} has no format - skipping (SQLite/unsupported format)")
                
                elif task_state == 'ERROR':
                    self._handle_error_task(task_id, task)
            
            # After all tasks are processed, fetch the actual published layer names
            published_layer_names = self._get_published_layer_names(import_id, url, username, password)
            
            # Final result - pass the actual published layer names
            return self._process_final_result(layers_published, layer, workspace, url, username, password, published_layer_names)
                
        except Exception as e:
            self.main.log_message(f"❌ Error in task verification: {e}", level=Qgis.Critical)
            return False
    
    def _get_published_layer_names(self, import_id, url, username, password):
        """
        Get the actual published layer names from completed import tasks.
        
        Args:
            import_id: GeoServer import ID
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        
        Returns:
            list: List of published layer names
        """
        try:
            tasks_url = f"{url}/rest/imports/{import_id}/tasks"
            tasks_response = requests.get(tasks_url, auth=(username, password))
            
            if tasks_response.status_code != 200:
                self.main.log_message(f"DEBUG: Could not fetch tasks for layer names: {tasks_response.status_code}")
                return []
            
            tasks_data = tasks_response.json()
            all_tasks = tasks_data.get('tasks', [])
            published_layer_names = []
            
            for task in all_tasks:
                task_state = task.get('state', 'UNKNOWN')
                layer_info = task.get('layer', {})
                layer_name = layer_info.get('name')
                
                # Only collect layer names from completed tasks
                if task_state in ['COMPLETE', 'READY'] and layer_name:
                    self.main.log_message(f"DEBUG: Found published layer from task: '{layer_name}'")
                    published_layer_names.append(layer_name)
            
            return published_layer_names
            
        except Exception as e:
            self.main.log_message(f"DEBUG: Error getting published layer names: {e}")
            return []
    
    def _handle_ready_task(self, task_id, import_id, url, username, password):
        """
        Handle a task in READY state.
        
        Returns:
            int: 1 if task was successfully executed, 0 otherwise
        """
        if task_id is not None:
            task_execute_url = f"{url}/rest/imports/{import_id}/tasks/{task_id}"
            task_response = requests.post(task_execute_url, auth=(username, password))
            if task_response.status_code in [200, 201, 202]:
                self.main.log_message(f"✓ Successfully executed task {task_id}")
                return 1
            else:
                self.main.log_message(f"❌ Failed to execute task {task_id}: {task_response.text}", level=Qgis.Critical)
        return 0
    
    def _handle_no_crs_task(self, task_id, layer, import_id, url, username, password):
        """
        Handle a task in NO_CRS state by setting the CRS and executing.
        Uses EPSG:4326 as default if layer has no CRS.
        
        Returns:
            int: 1 if task was successfully executed, 0 otherwise
        """
        if task_id is not None:
            layer_crs = layer.crs()
            crs_code = None
            
            if layer_crs.isValid():
                crs_code = layer_crs.authid()
                self.main.log_message(f"Layer has valid CRS: {crs_code}")
            else:
                # Layer has no CRS - use default EPSG:4326
                crs_code = "EPSG:4326"
                self.main.log_message(f"⚠️ Layer has no CRS defined. Using default: {crs_code}")
            
            # Check if CRS code is empty (layer marked valid but has no actual CRS)
            if not crs_code or crs_code.strip() == '':
                crs_code = "EPSG:4326"
                self.main.log_message(f"⚠️ Layer CRS is empty. Using default: {crs_code}")
            
            if crs_code:
                self.main.log_message(f"Setting CRS for task {task_id}: {crs_code}")
                
                task_update_url = f"{url}/rest/imports/{import_id}/tasks/{task_id}"
                crs_payload = {
                    "task": {
                        "layer": {
                            "srs": crs_code
                        }
                    }
                }
                self.main.log_message(f"DEBUG: CRS update URL: {task_update_url}")
                self.main.log_message(f"DEBUG: CRS payload: {crs_payload}")
                
                crs_response = requests.put(
                    task_update_url,
                    auth=(username, password),
                    json=crs_payload,
                    headers={"Content-Type": "application/json"}
                )
                
                self.main.log_message(f"DEBUG: CRS update response status: {crs_response.status_code}")
                self.main.log_message(f"DEBUG: CRS update response: {crs_response.text[:500]}")
                
                if crs_response.status_code in [200, 201]:
                    task_execute_url = f"{url}/rest/imports/{import_id}/tasks/{task_id}"
                    task_response = requests.post(task_execute_url, auth=(username, password))
                    if task_response.status_code in [200, 201, 202]:
                        self.main.log_message(f"✓ Successfully executed task {task_id} with CRS {crs_code}")
                        return 1
                    else:
                        self.main.log_message(f"❌ Failed to execute task {task_id} after CRS update: {task_response.text}", level=Qgis.Critical)
                else:
                    self.main.log_message(f"❌ Failed to update CRS for task {task_id}: Status {crs_response.status_code} - {crs_response.text}", level=Qgis.Critical)
        return 0
    
    def _handle_error_task(self, task_id, task):
        """
        Handle a task in ERROR state.
        """
        error_msg = task.get('errorMessage', 'Unknown error')
        self.main.log_message(f"❌ Task {task_id} error: {error_msg}", level=Qgis.Critical)
    
    def _process_final_result(self, layers_published, layer, workspace, url, username, password, published_layer_names=None):
        """
        Process the final result of task verification and publishing.
        
        Args:
            layers_published: Number of layers published
            layer: QGIS layer object
            workspace: GeoServer workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            published_layer_names: List of actual published layer names from tasks
        
        Returns:
            bool: True if at least one layer was published, False otherwise
        """
        if layers_published > 0:
            self.main.log_message(f"✓ Successfully published {layers_published} layer(s) from '{layer.name()}'")
            
            # For GeoTIFF/TIFF files, rename the published layer back to original name
            self._rename_geotiff_layer_if_needed(layer, workspace, url, username, password, published_layer_names)
            
            self.main._refresh_geoserver_layers_list(workspace, url, username, password)
            return True
        else:
            self.main.log_message(f"⚠️ No layers were published from '{layer.name()}' (may be unsupported format)", level=Qgis.Warning)
            return False
    
    def _rename_geotiff_layer_if_needed(self, layer, workspace, url, username, password, published_layer_names=None):
        """
        For GeoTIFF/TIFF files, ensure the published layer name matches the original QGIS layer name.
        The importer API sometimes adds prefixes during import, so we rename them back to match.
        
        Args:
            layer: QGIS layer object
            workspace: GeoServer workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            published_layer_names: List of actual published layer names from tasks
        """
        try:
            # Check if this is a GeoTIFF/TIFF file
            source_path = layer.source().split('|')[0].split('?')[0]
            is_geotiff = source_path.lower().endswith(('.tif', '.tiff'))
            
            if not is_geotiff:
                self.main.log_message(f"DEBUG: Not a GeoTIFF file, skipping rename")
                return
            
            original_name = self.main._sanitize_layer_name(layer.name())
            self.main.log_message(f"🔍 GeoTIFF layer target name: '{original_name}'")
            
            # Search for the actual published layer name
            actual_name = self._find_actual_published_layer(original_name, workspace, url, username, password)
            
            if not actual_name:
                self.main.log_message(f"⚠️ Could not find published layer for '{original_name}'", level=Qgis.Warning)
                return
            
            self.main.log_message(f"DEBUG: Found published layer: '{actual_name}'")
            
            # If names don't match, rename the published layer
            if actual_name != original_name:
                self.main.log_message(f"📝 Renaming '{actual_name}' → '{original_name}'")
                success = self._rename_coverage_in_datastore(actual_name, original_name, workspace, url, username, password)
                
                if success:
                    self.main.log_message(f"✓ Successfully renamed layer to '{original_name}'")
                    self._update_style_association_for_renamed_layer(original_name, workspace, url, username, password)
                else:
                    self.main.log_message(f"⚠️ Failed to rename layer", level=Qgis.Warning)
            else:
                self.main.log_message(f"✓ Layer name is correct: '{original_name}'")
                
        except Exception as e:
            self.main.log_message(f"⚠️ Error checking/renaming GeoTIFF layer: {e}", level=Qgis.Warning)
            import traceback
            self.main.log_message(f"DEBUG: Traceback: {traceback.format_exc()}")
    
    def _find_actual_published_layer(self, original_name, workspace, url, username, password):
        """
        Find the actual published layer name that corresponds to the original name.
        Searches for exact match first, then looks for layers with prefixes.
        
        Returns:
            str: The actual published layer name, or None if not found
        """
        try:
            # Get all layers in workspace
            layers_url = f"{url}/rest/workspaces/{workspace}/layers.json"
            layers_response = requests.get(layers_url, auth=(username, password))
            
            if layers_response.status_code != 200:
                self.main.log_message(f"DEBUG: Could not get workspace layers: {layers_response.status_code}")
                return None
            
            layers_data = layers_response.json()
            layers = layers_data.get('layers', {}).get('layer', [])
            
            if isinstance(layers, dict):
                layers = [layers]
            
            self.main.log_message(f"DEBUG: Searching through {len(layers)} layers in workspace")
            
            # First, look for exact match
            for layer in layers:
                if isinstance(layer, dict):
                    layer_name = layer.get('name', '')
                    if layer_name == original_name:
                        self.main.log_message(f"DEBUG: Found exact match: '{layer_name}'")
                        return layer_name
            
            # If no exact match, look for layers that end with the original name
            # (e.g., "a_3420C_2010_327_RGB_LATLNG" ends with "3420C_2010_327_RGB_LATLNG")
            for layer in layers:
                if isinstance(layer, dict):
                    layer_name = layer.get('name', '')
                    if layer_name.endswith(original_name) and layer_name != original_name:
                        self.main.log_message(f"DEBUG: Found layer with suffix: '{layer_name}'")
                        return layer_name
            
            self.main.log_message(f"DEBUG: No matching layer found for '{original_name}'")
            return None
            
        except Exception as e:
            self.main.log_message(f"DEBUG: Error finding published layer: {e}")
            return None
    
    def _find_published_coverage_name(self, expected_name, workspace, url, username, password):
        """
        Find the actual published coverage/layer name in GeoServer.
        Checks both workspace layers and coverages in stores.
        
        Returns:
            str: The actual coverage/layer name if different from expected, or None if already correct
        """
        try:
            # First, check if layer already exists at workspace level with expected name
            layer_url = f"{url}/rest/workspaces/{workspace}/layers/{expected_name}.json"
            layer_response = requests.get(layer_url, auth=(username, password))
            
            if layer_response.status_code == 200:
                self.main.log_message(f"DEBUG: Layer '{expected_name}' already exists at workspace level - no rename needed")
                return None  # Layer already has correct name
            
            self.main.log_message(f"DEBUG: Layer '{expected_name}' not found at workspace level, checking coverages...")
            
            # Check all coveragestores in the workspace for the coverage
            stores_url = f"{url}/rest/workspaces/{workspace}/coveragestores.json"
            stores_response = requests.get(stores_url, auth=(username, password))
            
            if stores_response.status_code != 200:
                self.main.log_message(f"DEBUG: Could not fetch coveragestores: {stores_response.status_code}")
                return None
            
            stores_data = stores_response.json()
            stores_obj = stores_data.get('coverageStores', {})
            
            # Handle different response formats
            if isinstance(stores_obj, dict):
                stores = stores_obj.get('coverageStore', [])
            else:
                stores = stores_obj
            
            # Ensure it's a list
            if isinstance(stores, dict):
                stores = [stores]
            elif not isinstance(stores, list):
                stores = []
            
            if not stores:
                self.main.log_message(f"DEBUG: No coveragestores found in workspace '{workspace}'")
                return None
            
            self.main.log_message(f"DEBUG: Found {len(stores)} coveragestore(s)")
            
            # For each coveragestore, check its coverages
            for store in stores:
                store_name = store.get('name')
                if not store_name:
                    continue
                
                self.main.log_message(f"DEBUG: Checking coveragestore '{store_name}'...")
                coverages_url = f"{url}/rest/workspaces/{workspace}/coveragestores/{store_name}/coverages.json"
                coverages_response = requests.get(coverages_url, auth=(username, password))
                
                if coverages_response.status_code == 200:
                    coverages_data = coverages_response.json()
                    coverages = coverages_data.get('coverages', {})
                    
                    # Handle different response formats
                    if isinstance(coverages, dict):
                        coverage_list = coverages.get('coverage', [])
                    else:
                        coverage_list = coverages
                    
                    # Ensure it's a list
                    if isinstance(coverage_list, dict):
                        coverage_list = [coverage_list]
                    elif not isinstance(coverage_list, list):
                        coverage_list = []
                    
                    self.main.log_message(f"DEBUG: Found {len(coverage_list)} coverage(s) in store '{store_name}'")
                    
                    for coverage in coverage_list:
                        if isinstance(coverage, dict):
                            coverage_name = coverage.get('name')
                            if coverage_name:
                                self.main.log_message(f"DEBUG: Coverage name: '{coverage_name}'")
                                # If coverage name is different from expected, return it for renaming
                                if coverage_name != expected_name:
                                    self.main.log_message(f"DEBUG: Coverage '{coverage_name}' differs from expected '{expected_name}' - will rename")
                                    return coverage_name
                                else:
                                    self.main.log_message(f"DEBUG: Coverage '{coverage_name}' matches expected name - no rename needed")
                                    return None
                        else:
                            self.main.log_message(f"DEBUG: Invalid coverage format: {type(coverage)} - {coverage}")
            
            self.main.log_message(f"DEBUG: No coverages found in any store")
            return None
            
        except Exception as e:
            self.main.log_message(f"DEBUG: Error finding published coverage: {e}")
            return None
    
    def _rename_coverage_in_datastore(self, old_name, new_name, workspace, url, username, password):
        """
        Rename a coverage in its datastore and update the layer name at workspace level.
        
        Returns:
            bool: True if rename was successful, False otherwise
        """
        try:
            # First, find which datastore contains this coverage
            stores_url = f"{url}/rest/workspaces/{workspace}/coveragestores.json"
            stores_response = requests.get(stores_url, auth=(username, password))
            
            if stores_response.status_code != 200:
                return False
            
            stores_data = stores_response.json()
            stores_obj = stores_data.get('coverageStores', {})
            
            # Handle different response formats
            if isinstance(stores_obj, dict):
                stores = stores_obj.get('coverageStore', [])
            else:
                stores = stores_obj
            
            # Ensure it's a list
            if isinstance(stores, dict):
                stores = [stores]
            elif not isinstance(stores, list):
                stores = []
            
            for store in stores:
                store_name = store.get('name')
                if not store_name:
                    continue
                
                coverages_url = f"{url}/rest/workspaces/{workspace}/coveragestores/{store_name}/coverages.json"
                coverages_response = requests.get(coverages_url, auth=(username, password))
                
                if coverages_response.status_code == 200:
                    coverages_data = coverages_response.json()
                    coverages = coverages_data.get('coverages', {})
                    
                    # Handle different response formats
                    if isinstance(coverages, dict):
                        coverage_list = coverages.get('coverage', [])
                    else:
                        coverage_list = coverages
                    
                    # Ensure it's a list
                    if isinstance(coverage_list, dict):
                        coverage_list = [coverage_list]
                    elif not isinstance(coverage_list, list):
                        coverage_list = []
                    
                    for coverage in coverage_list:
                        if isinstance(coverage, dict) and coverage.get('name') == old_name:
                            # Found the coverage, now rename it
                            rename_url = f"{url}/rest/workspaces/{workspace}/coveragestores/{store_name}/coverages/{old_name}"
                            rename_payload = {
                                "coverage": {
                                    "name": new_name
                                }
                            }
                            
                            self.main.log_message(f"DEBUG: Renaming coverage at {rename_url}")
                            rename_response = requests.put(
                                rename_url,
                                auth=(username, password),
                                json=rename_payload,
                                headers={"Content-Type": "application/json"}
                            )
                            
                            if rename_response.status_code in [200, 201]:
                                self.main.log_message(f"DEBUG: Coverage rename response: {rename_response.status_code}")
                                
                                # Now rename the layer at workspace level
                                layer_rename_url = f"{url}/rest/workspaces/{workspace}/layers/{old_name}"
                                layer_rename_payload = {
                                    "layer": {
                                        "name": new_name
                                    }
                                }
                                
                                self.main.log_message(f"DEBUG: Renaming layer at workspace level: {old_name} → {new_name}")
                                layer_rename_response = requests.put(
                                    layer_rename_url,
                                    auth=(username, password),
                                    json=layer_rename_payload,
                                    headers={"Content-Type": "application/json"}
                                )
                                
                                if layer_rename_response.status_code in [200, 201]:
                                    self.main.log_message(f"DEBUG: Layer rename response: {layer_rename_response.status_code}")
                                    return True
                                else:
                                    self.main.log_message(f"DEBUG: Layer rename failed: {layer_rename_response.status_code} - {layer_rename_response.text}")
                                    # Coverage was renamed but layer wasn't - still consider it partial success
                                    return True
                            else:
                                self.main.log_message(f"DEBUG: Coverage rename failed: {rename_response.status_code} - {rename_response.text}")
                                return False
            
            return False
            
        except Exception as e:
            self.main.log_message(f"DEBUG: Error renaming coverage: {e}")
            return False
    
    def _update_style_association_for_renamed_layer(self, layer_name, workspace, url, username, password):
        """
        Update style association for a renamed layer.
        This ensures the style is properly bound to the layer with its new name.
        
        Args:
            layer_name: The new (correct) layer name
            workspace: GeoServer workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        try:
            # Check if layer exists and has a style
            layer_url = f"{url}/rest/workspaces/{workspace}/layers/{layer_name}.json"
            layer_response = requests.get(layer_url, auth=(username, password))
            
            if layer_response.status_code == 200:
                layer_data = layer_response.json()
                layer_obj = layer_data.get('layer', {})
                default_style = layer_obj.get('defaultStyle', {})
                
                if default_style and default_style.get('name'):
                    style_name = default_style.get('name')
                    self.main.log_message(f"✓ Layer '{layer_name}' has style '{style_name}' associated")
                else:
                    self.main.log_message(f"⚠️ Layer '{layer_name}' has no style associated")
            else:
                self.main.log_message(f"DEBUG: Could not verify layer after rename: {layer_response.status_code}")
                
        except Exception as e:
            self.main.log_message(f"DEBUG: Error updating style association: {e}")
