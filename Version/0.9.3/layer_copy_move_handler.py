"""
Layer Copy/Move Handler Module
Core logic for copying and moving layers between workspaces.
"""

import requests
import json
import os
import shutil
import tempfile
from qgis.core import Qgis, QgsMessageLog

# Import with fallback for direct execution
try:
    from .layer_metadata_extractor import LayerMetadataExtractor
    from .data_store_manager import DataStoreManager
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from layer_metadata_extractor import LayerMetadataExtractor
    from data_store_manager import DataStoreManager


class LayerCopyMoveHandler:
    """Handles layer copy and move operations between workspaces."""
    
    def __init__(self):
        self.extractor = LayerMetadataExtractor()
        self.datastore_manager = DataStoreManager()
        self.timeout = 30
        self.created_items = []  # Track created items for rollback
        self.temp_files = []  # Track temporary files for cleanup
        self.temp_dir = None  # Temporary directory for downloads
    
    def log_message(self, message, level=Qgis.Info):
        """Log a message to QGIS message log."""
        QgsMessageLog.logMessage(message, "Q2G", level=level)
    
    def _get_temp_dir(self):
        """
        Get or create a temporary directory for layer copy operations.
        
        Returns:
            str: Path to temporary directory
        """
        if not self.temp_dir or not os.path.exists(self.temp_dir):
            self.temp_dir = tempfile.mkdtemp(prefix='geoserver_layer_copy_')
            print(f"DEBUG: Created temporary directory: {self.temp_dir}")
        return self.temp_dir
    
    def _download_file(self, url, auth, output_path):
        """
        Download a file from URL and save to output path.
        
        Args:
            url: URL to download from
            auth: Tuple of (username, password)
            output_path: Path to save the file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"DEBUG: Downloading file from {url}")
            response = requests.get(url, auth=auth, timeout=self.timeout, stream=True)
            
            if response.status_code != 200:
                print(f"DEBUG: Download failed with status {response.status_code}")
                return False
            
            # Write file in chunks
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print(f"DEBUG: File downloaded successfully to {output_path}")
            self.temp_files.append(output_path)
            return True
            
        except Exception as e:
            print(f"DEBUG: Error downloading file: {e}")
            return False
    
    def _cleanup_temp_files(self):
        """
        Clean up all temporary files and directories.
        """
        try:
            # Delete individual temp files
            for temp_file in self.temp_files:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    print(f"DEBUG: Deleted temporary file: {temp_file}")
            
            self.temp_files = []
            
            # Delete temp directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                print(f"DEBUG: Deleted temporary directory: {self.temp_dir}")
                self.temp_dir = None
                
        except Exception as e:
            print(f"DEBUG: Error cleaning up temporary files: {e}")
            self.log_message(f"Warning: Could not clean up temporary files: {e}", level=Qgis.Warning)
    
    def _cleanup_temp_files_on_success(self):
        """
        Clean up temporary files after successful operation.
        """
        print(f"DEBUG: Cleaning up temporary files after successful operation")
        self._cleanup_temp_files()
    
    def _cleanup_temp_files_on_failure(self):
        """
        Clean up temporary files after failed operation.
        """
        print(f"DEBUG: Cleaning up temporary files after failed operation")
        self._cleanup_temp_files()
    
    def _ensure_style_exists(self, url, auth, source_workspace, target_workspace, style_name):
        """
        Ensure a style exists in the target workspace.
        If it doesn't exist, copy it from the source workspace.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            source_workspace: Source workspace name
            target_workspace: Target workspace name
            style_name: Style name to ensure
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        print(f"DEBUG: Ensuring style {style_name} exists in {target_workspace}")
        
        # Check if style exists in target workspace
        check_url = f"{url}/rest/workspaces/{target_workspace}/styles/{style_name}.json"
        response = requests.get(check_url, auth=auth, timeout=self.timeout)
        
        if response.status_code == 200:
            print(f"DEBUG: Style {style_name} already exists in target workspace")
            return True, "Style already exists"
        
        # Style doesn't exist, try to copy from source
        print(f"DEBUG: Style doesn't exist in target, copying from source")
        
        # Get SLD from source workspace
        source_sld_url = f"{url}/rest/workspaces/{source_workspace}/styles/{style_name}.sld"
        response = requests.get(source_sld_url, auth=auth, timeout=self.timeout)
        
        if response.status_code != 200:
            # Try global styles
            source_sld_url = f"{url}/rest/styles/{style_name}.sld"
            response = requests.get(source_sld_url, auth=auth, timeout=self.timeout)
        
        if response.status_code != 200:
            print(f"DEBUG: Could not find source style: {response.status_code}")
            return False, f"Source style not found: {response.status_code}"
        
        sld_content = response.text
        print(f"DEBUG: Got SLD content, length: {len(sld_content)}")
        
        # Create style in target workspace
        # Step 1: Create the style metadata
        create_style_url = f"{url}/rest/workspaces/{target_workspace}/styles"
        style_metadata = {
            'style': {
                'name': style_name,
                'filename': f"{style_name}.sld"
            }
        }
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            create_style_url,
            auth=auth,
            json=style_metadata,
            headers=headers,
            timeout=self.timeout
        )
        
        print(f"DEBUG: Style metadata creation response: {response.status_code}")
        
        if response.status_code not in [200, 201]:
            print(f"DEBUG: Style metadata creation failed: {response.text}")
            return False, f"Failed to create style metadata: {response.status_code}"
        
        # Step 2: Upload the SLD content
        upload_url = f"{url}/rest/workspaces/{target_workspace}/styles/{style_name}"
        headers_sld = {'Content-Type': 'application/vnd.ogc.sld+xml'}
        response = requests.put(
            upload_url,
            auth=auth,
            data=sld_content.encode('utf-8'),
            headers=headers_sld,
            timeout=self.timeout
        )
        
        print(f"DEBUG: SLD upload response: {response.status_code}")
        
        if response.status_code not in [200, 201]:
            print(f"DEBUG: SLD upload failed: {response.text}")
            return False, f"Failed to upload SLD: {response.status_code}"
        
        print(f"DEBUG: Style {style_name} successfully created in target workspace")
        return True, "Style created successfully"
    
    def copy_layer(self, url, auth, source_workspace, layer_name, target_workspace, 
                   new_layer_name, conflict_strategy='rename'):
        """
        Copy a layer from source workspace to target workspace.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            source_workspace: Source workspace name
            layer_name: Source layer name
            target_workspace: Target workspace name
            new_layer_name: New layer name in target workspace
            conflict_strategy: 'rename', 'skip', or 'overwrite'
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            print(f"DEBUG copy_layer: Starting copy of {layer_name} from {source_workspace} to {target_workspace}")
            print(f"DEBUG: URL={url}, Auth user={auth[0] if auth else 'None'}")
            self.created_items = []
            
            # Skip validation - just try to copy
            print(f"DEBUG: Proceeding with copy operation")
            
            # Handle naming conflict
            final_layer_name = self._handle_naming_conflict(
                url, auth, target_workspace, new_layer_name, conflict_strategy
            )
            
            if final_layer_name is None:
                return True, f"Layer '{layer_name}' skipped (already exists)"
            
            # Get source layer metadata
            print(f"DEBUG: Getting layer metadata")
            layer_metadata = self.extractor.get_layer_metadata(url, auth, source_workspace, layer_name)
            print(f"DEBUG: Layer metadata: {layer_metadata}")
            if not layer_metadata:
                print(f"DEBUG: Could not get layer metadata!")
                return False, f"Could not retrieve metadata for layer '{layer_name}'"
            
            # Check if this is a raster layer (coverage)
            layer_info = layer_metadata.get('layer', {})
            layer_type = layer_info.get('type', '')
            print(f"DEBUG: Layer type: {layer_type}")
            
            if layer_type == 'RASTER':
                print(f"DEBUG: Raster layer detected - skipping copy")
                return False, (
                    f"Raster layer drag-and-drop copy is not yet implemented. "
                    f"To use this layer in another workspace, please upload the GeoTIFF file directly to that workspace."
                )
            
            # Get source data store
            print(f"DEBUG: Getting data store config")
            datastore_config = self.extractor.get_layer_data_store(url, auth, source_workspace, layer_name)
            print(f"DEBUG: Data store config: {datastore_config}")
            
            # Copy data store if available
            if datastore_config:
                success, datastore_name, ds_msg = self.datastore_manager.create_data_store_reference(
                    url, auth, target_workspace, datastore_config
                )
                if not success:
                    return False, f"Failed to create data store: {ds_msg}"
                self.created_items.append(('datastore', target_workspace, datastore_name))
            
            # Copy SLD style
            sld_content = self.extractor.get_layer_style(url, auth, source_workspace, layer_name)
            if sld_content:
                success, style_msg = self._copy_sld_style(
                    url, auth, source_workspace, layer_name, target_workspace, final_layer_name, sld_content
                )
                if not success:
                    self._rollback_on_failure(url, auth)
                    return False, f"Failed to copy style: {style_msg}"
                self.created_items.append(('style', target_workspace, final_layer_name))
            
            # Copy layer configuration
            success, layer_msg = self._copy_layer_config(
                url, auth, source_workspace, layer_name, target_workspace, final_layer_name, layer_metadata
            )
            if not success:
                self._rollback_on_failure(url, auth)
                return False, f"Failed to copy layer: {layer_msg}"
            
            self.log_message(f"✓ Layer '{layer_name}' copied to '{target_workspace}' as '{final_layer_name}'")
            return True, f"Layer '{layer_name}' copied successfully"
        
        except Exception as e:
            self._rollback_on_failure(url, auth)
            error_msg = f"Error copying layer: {str(e)}"
            self.log_message(error_msg, level=Qgis.Warning)
            return False, error_msg
    
    def move_layer(self, url, auth, source_workspace, layer_name, target_workspace, 
                   new_layer_name, conflict_strategy='rename'):
        """
        Move a layer from source workspace to target workspace.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            source_workspace: Source workspace name
            layer_name: Source layer name
            target_workspace: Target workspace name
            new_layer_name: New layer name in target workspace
            conflict_strategy: 'rename', 'skip', or 'overwrite'
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Check if this is a raster layer before attempting to move
            layer_metadata = self.extractor.get_layer_metadata(url, auth, source_workspace, layer_name)
            if layer_metadata:
                layer_info = layer_metadata.get('layer', {})
                layer_type = layer_info.get('type', '')
                
                if layer_type == 'RASTER':
                    print(f"DEBUG: Raster layer detected in move - skipping")
                    return False, (
                        f"Raster layer drag-and-drop move is not yet implemented. "
                        f"To use this layer in another workspace, please upload the GeoTIFF file directly to that workspace."
                    )
            
            # First, copy the layer
            success, copy_msg = self.copy_layer(
                url, auth, source_workspace, layer_name, target_workspace, 
                new_layer_name, conflict_strategy
            )
            
            if not success:
                return False, f"Move failed: {copy_msg}"
            
            # Then, delete the source layer
            success, delete_msg = self._delete_layer(url, auth, source_workspace, layer_name)
            if not success:
                return False, f"Layer copied but deletion failed: {delete_msg}"
            
            self.log_message(f"✓ Layer '{layer_name}' moved from '{source_workspace}' to '{target_workspace}'")
            return True, f"Layer '{layer_name}' moved successfully"
        
        except Exception as e:
            error_msg = f"Error moving layer: {str(e)}"
            self.log_message(error_msg, level=Qgis.Warning)
            return False, error_msg
    
    def _copy_sld_style(self, url, auth, source_workspace, layer_name, target_workspace, 
                        new_layer_name, sld_content):
        """
        Copy SLD style from source to target workspace.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            style_name = new_layer_name
            
            # Create style in target workspace
            create_url = f"{url}/rest/workspaces/{target_workspace}/styles?raw=true"
            params = {'name': style_name}
            headers = {'Content-Type': 'application/vnd.ogc.sld+xml'}
            
            response = requests.post(
                create_url,
                params=params,
                auth=auth,
                headers=headers,
                data=sld_content.encode('utf-8'),
                timeout=self.timeout
            )
            
            if response.status_code not in [200, 201]:
                return False, f"Failed to create style: {response.status_code}"
            
            return True, f"Style '{style_name}' created"
        
        except Exception as e:
            return False, f"Error copying style: {str(e)}"
    
    def _copy_layer_config(self, url, auth, source_workspace, layer_name, target_workspace, 
                          new_layer_name, layer_metadata):
        """
        Copy layer configuration to target workspace.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if 'layer' not in layer_metadata:
                return False, "Invalid layer metadata"
            
            layer_info = layer_metadata['layer']
            print(f"DEBUG: Layer info: {layer_info}")
            
            # Get feature type info
            feature_type = self.extractor.get_feature_type_info(url, auth, source_workspace, layer_name)
            print(f"DEBUG: Feature type: {feature_type}")
            if not feature_type or 'featureType' not in feature_type:
                print(f"DEBUG: No feature type found, trying coverage...")
                # Try to get coverage info instead (for raster layers)
                coverage = self.extractor.get_coverage_info(url, auth, source_workspace, layer_name)
                print(f"DEBUG: Coverage: {coverage}")
                if not coverage or 'coverage' not in coverage:
                    return False, "Could not get feature type or coverage info"
                # Handle coverage copy instead
                return self._copy_coverage_config(url, auth, source_workspace, layer_name, target_workspace, new_layer_name, coverage, layer_info)
            
            # Vector layer - copy feature type and layer
            print(f"DEBUG: Copying vector layer (feature type)")
            ft_info = feature_type['featureType']
            datastore_name = ft_info.get('store', {}).get('name')
            
            if not datastore_name:
                return False, "Could not determine data store"
            
            # Extract just the store name (remove workspace prefix if present)
            if ':' in datastore_name:
                datastore_name = datastore_name.split(':')[1]
            
            print(f"DEBUG: Data store: {datastore_name}")
            
            # Step 0: Create the datastore in target workspace if it doesn't exist
            print(f"DEBUG: Checking if datastore exists in target workspace")
            check_store_url = f"{url}/rest/workspaces/{target_workspace}/datastores/{datastore_name}.json"
            response = requests.get(check_store_url, auth=auth, timeout=self.timeout)
            
            if response.status_code != 200:
                print(f"DEBUG: Datastore doesn't exist, creating it")
                # Get source datastore config
                source_store_url = f"{url}/rest/workspaces/{source_workspace}/datastores/{datastore_name}.json"
                response = requests.get(source_store_url, auth=auth, timeout=self.timeout)
                
                if response.status_code == 200:
                    source_store_data = response.json().get('dataStore', {})
                    print(f"DEBUG: Source store config retrieved")
                    
                    # Create datastore in target workspace
                    create_store_url = f"{url}/rest/workspaces/{target_workspace}/datastores"
                    
                    store_payload = {
                        'dataStore': {
                            'name': datastore_name,
                            'type': source_store_data.get('type', 'PostGIS'),
                            'connectionParameters': source_store_data.get('connectionParameters', {}),
                            'workspace': {'name': target_workspace},
                            'enabled': True
                        }
                    }
                    
                    headers = {'Content-Type': 'application/json'}
                    response = requests.post(
                        create_store_url,
                        auth=auth,
                        json=store_payload,
                        headers=headers,
                        timeout=self.timeout
                    )
                    
                    print(f"DEBUG: Datastore creation response: {response.status_code}")
                    if response.status_code not in [200, 201, 409]:  # 409 = already exists
                        print(f"DEBUG: Datastore creation failed: {response.text}")
                        return False, f"Failed to create datastore: {response.status_code} - {response.text}"
                else:
                    print(f"DEBUG: Could not get source datastore")
                    return False, f"Could not get source datastore: {response.status_code}"
            else:
                print(f"DEBUG: Datastore already exists in target workspace")
            
            # Step 1: Create new feature type by copying the source
            print(f"DEBUG: Creating new feature type: {new_layer_name}")
            import copy
            ft_copy = copy.deepcopy(ft_info)
            ft_copy['name'] = new_layer_name
            ft_copy['nativeName'] = ft_info.get('nativeName', new_layer_name)
            # Remove read-only and workspace-specific fields
            ft_copy.pop('id', None)
            ft_copy.pop('store', None)
            ft_copy.pop('namespace', None)  # Remove source workspace namespace
            ft_copy.pop('dateCreated', None)
            ft_copy.pop('dateModified', None)
            print(f"DEBUG: FT copy keys: {list(ft_copy.keys())}")
            
            create_ft_url = f"{url}/rest/workspaces/{target_workspace}/datastores/{datastore_name}/featuretypes"
            ft_payload = {'featureType': ft_copy}
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                create_ft_url,
                auth=auth,
                json=ft_payload,
                headers=headers,
                timeout=self.timeout
            )
            
            print(f"DEBUG: Feature type creation response: {response.status_code}")
            print(f"DEBUG: FT response: {response.text[:200] if response.text else 'empty'}")
            
            if response.status_code not in [200, 201]:
                return False, f"Failed to create feature type: {response.status_code} - {response.text}"
            
            # Step 2: Update the auto-created layer with style and settings
            # Note: The layer is automatically created when we create the feature type,
            # so we just need to update it with PUT to set the style
            print(f"DEBUG: Updating layer with style and settings")
            
            # Get style name from source layer
            style_name = new_layer_name
            if 'defaultStyle' in layer_info:
                source_style = layer_info['defaultStyle'].get('name', new_layer_name)
                if ':' in source_style:
                    style_name = source_style.split(':')[1]
                else:
                    style_name = source_style
            
            print(f"DEBUG: Using style: {style_name}")
            
            # Ensure the style exists in the target workspace
            success, msg = self._ensure_style_exists(url, auth, source_workspace, target_workspace, style_name)
            print(f"DEBUG: Style ensure result: {success}, {msg}")
            
            # Update the layer with PUT to set style and enable it
            update_layer_url = f"{url}/rest/layers/{target_workspace}:{new_layer_name}"
            
            layer_update_payload = {
                'layer': {
                    'enabled': True,
                    'queryable': layer_info.get('queryable', True),
                    'defaultStyle': {'name': style_name}
                }
            }
            
            response = requests.put(
                update_layer_url,
                auth=auth,
                json=layer_update_payload,
                headers=headers,
                timeout=self.timeout
            )
            
            print(f"DEBUG: Layer update response: {response.status_code}")
            print(f"DEBUG: Layer update response: {response.text[:200] if response.text else 'empty'}")
            
            if response.status_code not in [200, 201]:
                print(f"DEBUG: Layer update failed, but feature type was created successfully")
                # Don't fail here - the feature type was created successfully
                # The layer should be accessible even if style update failed
            
            return True, "Layer copied successfully"
        
        except Exception as e:
            print(f"DEBUG: Exception in _copy_layer_config: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, f"Error copying layer config: {str(e)}"
    
    def _handle_naming_conflict(self, url, auth, target_workspace, layer_name, strategy):
        """
        Handle layer name conflicts based on strategy.
        
        Returns:
            Final layer name to use, or None if should skip
        """
        if not self.extractor.layer_exists(url, auth, target_workspace, layer_name):
            return layer_name  # No conflict
        
        if strategy == 'skip':
            return None  # Skip this layer
        elif strategy == 'overwrite':
            return layer_name  # Use same name (will overwrite)
        else:  # rename
            # Find a unique name by appending _copy
            counter = 1
            new_name = f"{layer_name}_copy"
            while self.extractor.layer_exists(url, auth, target_workspace, new_name):
                counter += 1
                new_name = f"{layer_name}_copy{counter}"
            return new_name
    
    def _delete_layer(self, url, auth, workspace, layer_name):
        """
        Delete a layer from a workspace.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            delete_url = f"{url}/rest/layers/{workspace}:{layer_name}"
            response = requests.delete(delete_url, auth=auth, timeout=self.timeout)
            
            if response.status_code == 200:
                return True, f"Layer '{layer_name}' deleted"
            else:
                return False, f"Failed to delete layer: {response.status_code}"
        
        except Exception as e:
            return False, f"Error deleting layer: {str(e)}"
    
    def _copy_coverage_config(self, url, auth, source_workspace, layer_name, target_workspace, 
                             new_layer_name, coverage_metadata, layer_info):
        """
        Raster layers (GeoTIFF, coverages) cannot be copied via drag-and-drop.
        This feature is not yet implemented.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            print(f"DEBUG: Raster layer copy requested - feature not yet implemented")
            
            # Get the default style name and copy it
            default_style_name = layer_info.get('defaultStyle', {}).get('name', new_layer_name)
            print(f"DEBUG: Default style from layer metadata: {default_style_name}")
            
            # Clean up style name
            if default_style_name:
                if ':' in default_style_name:
                    default_style_name = default_style_name.split(':')[1]
            
            # Ensure the style exists in the target workspace (at least copy the style)
            if default_style_name:
                success, msg = self._ensure_style_exists(url, auth, source_workspace, target_workspace, default_style_name)
                print(f"DEBUG: Style ensure result: {success}, {msg}")
            
            # Return a message explaining that this feature is not yet implemented
            return False, (
                f"Raster layer drag-and-drop copy is not yet implemented. "
                f"To use this layer in another workspace, please upload the GeoTIFF file directly to that workspace."
            )
        
        except Exception as e:
            print(f"DEBUG: Error in _copy_coverage_config: {str(e)}")
            import traceback
            traceback.print_exc()
            self._cleanup_temp_files_on_failure()
            return False, f"Error: {str(e)}"

    def _rollback_on_failure(self, url, auth):
        """
        Rollback created items on failure.
        """
        for item_type, workspace, item_name in reversed(self.created_items):
            try:
                if item_type == 'style':
                    delete_url = f"{url}/rest/workspaces/{workspace}/styles/{item_name}"
                    requests.delete(delete_url, auth=auth, timeout=self.timeout)
                    self.log_message(f"Rolled back style: {item_name}")
                elif item_type == 'datastore':
                    delete_url = f"{url}/rest/workspaces/{workspace}/datastores/{item_name}"
                    requests.delete(delete_url, auth=auth, timeout=self.timeout)
                    self.log_message(f"Rolled back data store: {item_name}")
                elif item_type == 'coveragestore':
                    delete_url = f"{url}/rest/workspaces/{workspace}/coveragestores/{item_name}"
                    requests.delete(delete_url, auth=auth, timeout=self.timeout)
                    self.log_message(f"Rolled back coverage store: {item_name}")
                elif item_type == 'coverage':
                    # Coverage will be deleted when coverage store is deleted
                    self.log_message(f"Coverage {item_name} will be deleted with store")
                elif item_type == 'layer':
                    delete_url = f"{url}/rest/workspaces/{workspace}/layers/{item_name}"
                    requests.delete(delete_url, auth=auth, timeout=self.timeout)
                    self.log_message(f"Rolled back layer: {item_name}")
            except Exception as e:
                self.log_message(f"Error rolling back {item_type}: {str(e)}", level=Qgis.Warning)
