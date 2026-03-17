"""
Layer Copy/Move Handler Module
Core logic for copying and moving layers between workspaces.
"""

import requests
import json
import os
import sys
import shutil
import tempfile
import importlib.util
from qgis.core import Qgis, QgsMessageLog

# Ensure we load modules from the same folder as this file
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

def _load_local_module(module_name):
    """Load a module from the same directory as this file."""
    module_file = os.path.join(_CURRENT_DIR, f"{module_name}.py")
    if not os.path.exists(module_file):
        raise ImportError(f"Module not found: {module_file}")
    spec = importlib.util.spec_from_file_location(module_name, module_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for: {module_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load local modules
_lme = _load_local_module("layer_metadata_extractor")
LayerMetadataExtractor = _lme.LayerMetadataExtractor
_dsm = _load_local_module("data_store_manager")
DataStoreManager = _dsm.DataStoreManager


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
    
    def _ensure_namespace_exists(self, url, auth, workspace):
        """
        Ensure a namespace exists for the workspace.
        If it doesn't exist, create one.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            workspace: Workspace name
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Check if namespace exists
            namespace_url = f"{url}/rest/namespaces/{workspace}.json"
            response = requests.get(namespace_url, auth=auth, timeout=self.timeout)
            
            if response.status_code == 200:
                print(f"DEBUG: Namespace '{workspace}' already exists")
                return True, f"Namespace '{workspace}' exists"
            
            # Create namespace
            print(f"DEBUG: Creating namespace '{workspace}'")
            create_url = f"{url}/rest/namespaces"
            namespace_payload = {
                'namespace': {
                    'prefix': workspace,
                    'uri': f"http://geoserver.org/{workspace}"
                }
            }
            
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                create_url,
                auth=auth,
                json=namespace_payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code in [200, 201]:
                print(f"DEBUG: Namespace '{workspace}' created successfully")
                self.log_message(f"✓ Namespace '{workspace}' created")
                return True, f"Namespace '{workspace}' created"
            else:
                error_msg = f"Failed to create namespace: {response.status_code} - {response.text}"
                print(f"DEBUG: {error_msg}")
                return False, error_msg
        
        except Exception as e:
            error_msg = f"Error ensuring namespace exists: {str(e)}"
            print(f"DEBUG: {error_msg}")
            return False, error_msg
    
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
            
            # Step 1: Ensure namespace exists in target workspace
            print(f"DEBUG: Ensuring namespace exists for target workspace {target_workspace}")
            success, ns_msg = self._ensure_namespace_exists(url, auth, target_workspace)
            if not success:
                return False, f"Failed to ensure namespace: {ns_msg}"
            
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
            
            # Extract layer info and style name first (needed for both raster and vector)
            layer_info = layer_metadata.get('layer', {})
            layer_type = layer_info.get('type', '')
            print(f"DEBUG: Layer type: {layer_type}")
            
            # Extract actual style name from layer metadata
            actual_style_name = None
            if 'defaultStyle' in layer_info:
                style_ref = layer_info['defaultStyle'].get('name', '')
                # Remove workspace prefix if present (e.g., "a123:polygon_style" -> "polygon_style")
                if ':' in style_ref:
                    actual_style_name = style_ref.split(':')[1]
                else:
                    actual_style_name = style_ref
                print(f"DEBUG: Extracted actual style name: {actual_style_name}")
            else:
                # Fallback to layer name if no default style found
                actual_style_name = layer_name
                print(f"DEBUG: No defaultStyle found, using layer name as style: {actual_style_name}")
            
            # Check if this is a raster layer (coverage)
            if layer_type == 'RASTER':
                print(f"DEBUG: Raster layer detected - using raster copy method")
                # For raster layers, use WCS export/import approach
                success, msg = self._copy_raster_layer(
                    url, auth, source_workspace, layer_name, target_workspace, 
                    final_layer_name, layer_metadata, actual_style_name
                )
                return success, msg
            
            # Get source data store
            print(f"DEBUG: Getting data store config")
            datastore_config = self.extractor.get_layer_data_store(url, auth, source_workspace, layer_name)
            print(f"DEBUG: Data store config: {datastore_config}")
            
            # Check for file-based datastores and handle them differently
            is_file_based = False
            if datastore_config and 'dataStore' in datastore_config:
                ds_type = datastore_config['dataStore'].get('type', '')
                print(f"DEBUG: Datastore type: {ds_type}")
                if ds_type in ['Shapefile', 'GeoPackage', 'Directory of spatial files']:
                    is_file_based = True
                    print(f"DEBUG: File-based datastore detected: {ds_type}")
                    # For file-based datastores, we need to copy via file upload
                    success, msg = self._copy_file_based_layer(
                        url, auth, source_workspace, layer_name, target_workspace, 
                        final_layer_name, layer_metadata, actual_style_name, datastore_config
                    )
                    return success, msg
            
            # Copy data store if available (PostGIS and other connection-based stores)
            if datastore_config and not is_file_based:
                success, datastore_name, ds_msg = self.datastore_manager.create_data_store_reference(
                    url, auth, target_workspace, datastore_config
                )
                if not success:
                    return False, f"Failed to create data store: {ds_msg}"
                self.created_items.append(('datastore', target_workspace, datastore_name))
            
            # Copy SLD style using actual style name
            print(f"DEBUG: Getting layer style for style: {actual_style_name}")
            sld_content = self.extractor.get_layer_style(url, auth, source_workspace, layer_name)
            style_copied = False
            if sld_content:
                print(f"DEBUG: Got SLD content, copying style as '{actual_style_name}'...")
                success, style_msg = self._copy_sld_style(
                    url, auth, source_workspace, target_workspace, actual_style_name, sld_content
                )
                if success:
                    self.created_items.append(('style', target_workspace, actual_style_name))
                    style_copied = True
                    print(f"DEBUG: Style copied successfully")
                else:
                    print(f"DEBUG: Style copy failed: {style_msg} - continuing anyway")
                    self.log_message(f"Warning: Style copy failed: {style_msg}", level=Qgis.Warning)
            else:
                print(f"DEBUG: No SLD content found for layer")
            
            # Copy layer configuration with actual style name
            print(f"DEBUG: Copying layer configuration...")
            success, layer_msg = self._copy_layer_config(
                url, auth, source_workspace, layer_name, target_workspace, final_layer_name, 
                layer_metadata, actual_style_name
            )
            if not success:
                print(f"DEBUG: Layer config copy failed: {layer_msg}")
                self._rollback_on_failure(url, auth)
                return False, f"Failed to copy layer: {layer_msg}"
            
            print(f"DEBUG: Layer copied successfully")
            
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
            # First, copy the layer (works for both vector and raster now)
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
    
    def _copy_sld_style(self, url, auth, source_workspace, target_workspace, style_name, sld_content):
        """
        Copy SLD style from source to target workspace.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            source_workspace: Source workspace name (for reference)
            target_workspace: Target workspace name
            style_name: Actual style name to use (from layer's defaultStyle)
            sld_content: SLD XML content
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            print(f"DEBUG: _copy_sld_style - Creating style '{style_name}' in {target_workspace}")
            print(f"DEBUG: SLD content length: {len(sld_content) if sld_content else 0}")
            
            # Create style in target workspace
            create_url = f"{url}/rest/workspaces/{target_workspace}/styles?raw=true"
            params = {'name': style_name}
            headers = {'Content-Type': 'application/vnd.ogc.sld+xml'}
            
            print(f"DEBUG: POST to {create_url} with params {params}")
            response = requests.post(
                create_url,
                params=params,
                auth=auth,
                headers=headers,
                data=sld_content.encode('utf-8'),
                timeout=self.timeout
            )
            
            print(f"DEBUG: Style creation response: {response.status_code}")
            if response.status_code not in [200, 201]:
                print(f"DEBUG: Style creation failed: {response.text[:200] if response.text else 'empty'}")
                return False, f"Failed to create style: {response.status_code} - {response.text[:100] if response.text else ''}"
            
            print(f"DEBUG: Style '{style_name}' created successfully")
            return True, f"Style '{style_name}' created"
        
        except Exception as e:
            print(f"DEBUG: Exception in _copy_sld_style: {str(e)}")
            return False, f"Error copying style: {str(e)}"
    
    def _copy_file_based_layer(self, url, auth, source_workspace, layer_name, target_workspace,
                                new_layer_name, layer_metadata, actual_style_name, datastore_config):
        """
        Copy a file-based layer (Shapefile, GeoPackage) by re-uploading the file to target workspace.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            source_workspace: Source workspace name
            layer_name: Source layer name
            target_workspace: Target workspace name
            new_layer_name: New layer name in target workspace
            layer_metadata: Layer metadata dict
            actual_style_name: Actual style name from layer's defaultStyle
            datastore_config: Datastore configuration dict
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            print(f"DEBUG: _copy_file_based_layer - Copying file-based layer {layer_name}")
            
            ds_info = datastore_config.get('dataStore', {})
            ds_type = ds_info.get('type', '')
            ds_name = ds_info.get('name', '')
            
            print(f"DEBUG: Datastore type: {ds_type}, name: {ds_name}")
            
            # For Shapefile and GeoPackage, we need to get the feature type info
            # to understand the source data structure
            feature_type = self.extractor.get_feature_type_info(url, auth, source_workspace, layer_name)
            if not feature_type or 'featureType' not in feature_type:
                return False, "Could not get feature type info for file-based layer"
            
            ft_info = feature_type['featureType']
            
            # Get connection parameters to find file location
            conn_params = ds_info.get('connectionParameters', {})
            print(f"DEBUG: Connection parameters: {conn_params}")
            
            # Check if this is a GeoPackage datastore - if so, download the file directly
            is_geopackage = 'GeoPackage' in ds_type or ds_type == 'GeoPackage'
            
            if is_geopackage:
                print(f"DEBUG: Detected GeoPackage datastore - will download .gpkg file directly")
                return self._copy_geopackage_direct(url, auth, source_workspace, layer_name, 
                                                     target_workspace, new_layer_name, 
                                                     actual_style_name, ds_name, ds_info)
            
            # For other file-based datastores, we'll use the WFS service to export and re-import
            print(f"DEBUG: Using WFS export/import approach for file-based datastore")
            
            # Step 1: Copy the style first
            sld_content = self.extractor.get_layer_style(url, auth, source_workspace, layer_name)
            if sld_content:
                print(f"DEBUG: Copying style '{actual_style_name}' to target workspace")
                success, style_msg = self._copy_sld_style(
                    url, auth, source_workspace, target_workspace, actual_style_name, sld_content
                )
                if success:
                    self.created_items.append(('style', target_workspace, actual_style_name))
                    print(f"DEBUG: Style copied successfully")
                else:
                    print(f"DEBUG: Style copy failed: {style_msg} - continuing anyway")
            
            # Step 2: Export data from source using WFS GetFeature
            print(f"DEBUG: Exporting data from source layer via WFS")
            wfs_url = f"{url}/wfs"
            wfs_params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetFeature',
                'typeName': f"{source_workspace}:{layer_name}",
                'outputFormat': 'application/geopackage+sqlite3'  # Export as GeoPackage
            }
            
            response = requests.get(wfs_url, params=wfs_params, auth=auth, timeout=60)
            if response.status_code != 200:
                print(f"DEBUG: WFS export failed: {response.status_code}")
                return False, f"Failed to export layer data via WFS: {response.status_code}"
            
            # Save the GeoPackage file temporarily
            temp_dir = self._get_temp_dir()
            gpkg_path = os.path.join(temp_dir, f"{layer_name}.gpkg")
            
            with open(gpkg_path, 'wb') as f:
                f.write(response.content)
            
            self.temp_files.append(gpkg_path)
            print(f"DEBUG: Saved GeoPackage to {gpkg_path}, size: {len(response.content)} bytes")
            
            # Step 3: Upload the file to target workspace
            print(f"DEBUG: Uploading GeoPackage to target workspace {target_workspace}")
            
            # Use the REST API to upload the GeoPackage
            upload_url = f"{url}/rest/workspaces/{target_workspace}/datastores/{new_layer_name}/file.gpkg"
            
            headers = {'Content-Type': 'application/geopackage+sqlite3'}
            
            with open(gpkg_path, 'rb') as f:
                upload_response = requests.put(
                    upload_url,
                    auth=auth,
                    data=f,
                    headers=headers,
                    timeout=120
                )
            
            print(f"DEBUG: Upload response: {upload_response.status_code}")
            
            if upload_response.status_code not in [200, 201]:
                print(f"DEBUG: Upload failed: {upload_response.text}")
                return False, f"Failed to upload GeoPackage: {upload_response.status_code} - {upload_response.text}"
            
            print(f"DEBUG: GeoPackage uploaded successfully")
            self.created_items.append(('datastore', target_workspace, new_layer_name))
            
            # Step 4: Update the layer with the correct style
            print(f"DEBUG: Updating layer with style {actual_style_name}")
            
            # The layer should be auto-created with the upload, now update its style
            update_layer_url = f"{url}/rest/layers/{target_workspace}:{new_layer_name}"
            
            layer_update_payload = {
                'layer': {
                    'enabled': True,
                    'defaultStyle': {'name': actual_style_name}
                }
            }
            
            headers_json = {'Content-Type': 'application/json'}
            update_response = requests.put(
                update_layer_url,
                auth=auth,
                json=layer_update_payload,
                headers=headers_json,
                timeout=self.timeout
            )
            
            print(f"DEBUG: Layer update response: {update_response.status_code}")
            
            if update_response.status_code not in [200, 201]:
                print(f"DEBUG: Layer update failed: {update_response.text}")
                # Don't fail - the layer was created successfully
            
            # Clean up temp files on success
            self._cleanup_temp_files_on_success()
            
            self.log_message(f"✓ File-based layer '{layer_name}' copied to '{target_workspace}' as '{new_layer_name}'")
            return True, f"File-based layer '{layer_name}' copied successfully"
            
        except Exception as e:
            print(f"DEBUG: Exception in _copy_file_based_layer: {str(e)}")
            import traceback
            traceback.print_exc()
            self._cleanup_temp_files_on_failure()
            error_msg = f"Error copying file-based layer: {str(e)}"
            return False, error_msg
    
    def _copy_geopackage_direct(self, url, auth, source_workspace, layer_name, target_workspace,
                                 new_layer_name, actual_style_name, datastore_name, ds_info):
        """
        Copy a GeoPackage layer by downloading the .gpkg file directly and re-uploading it.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            source_workspace: Source workspace name
            layer_name: Source layer name
            target_workspace: Target workspace name
            new_layer_name: New layer name in target workspace
            actual_style_name: Actual style name from layer's defaultStyle
            datastore_name: Name of the source datastore
            ds_info: Datastore info dict
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            print(f"DEBUG: _copy_geopackage_direct - Downloading GeoPackage file for {layer_name}")
            
            # Step 1: Copy the style first
            sld_content = self.extractor.get_layer_style(url, auth, source_workspace, layer_name)
            if sld_content:
                print(f"DEBUG: Copying style '{actual_style_name}' to target workspace")
                success, style_msg = self._copy_sld_style(
                    url, auth, source_workspace, target_workspace, actual_style_name, sld_content
                )
                if success:
                    self.created_items.append(('style', target_workspace, actual_style_name))
                    print(f"DEBUG: Style copied successfully")
                else:
                    print(f"DEBUG: Style copy failed: {style_msg} - continuing anyway")
            
            # Step 2: Download the GeoPackage file from the source datastore
            print(f"DEBUG: Downloading GeoPackage file from datastore {datastore_name}")
            
            # Try multiple download methods
            response = None
            download_methods = [
                f"{url}/rest/workspaces/{source_workspace}/datastores/{datastore_name}/file.gpkg",
                f"{url}/rest/workspaces/{source_workspace}/datastores/{datastore_name}/file",
            ]
            
            for download_url in download_methods:
                print(f"DEBUG: Trying download from: {download_url}")
                try:
                    response = requests.get(download_url, auth=auth, timeout=60)
                    print(f"DEBUG: Response status: {response.status_code}")
                    if response.status_code == 200:
                        print(f"DEBUG: Successfully downloaded from {download_url}")
                        break
                    else:
                        print(f"DEBUG: Failed with status {response.status_code}: {response.text[:200]}")
                        response = None
                except Exception as e:
                    print(f"DEBUG: Exception during download: {str(e)}")
                    response = None
            
            if not response or response.status_code != 200:
                print(f"DEBUG: All direct download methods failed, trying WFS export")
                # Fallback: use WFS export as GeoPackage
                return self._copy_geopackage_via_wfs(url, auth, source_workspace, layer_name,
                                                     target_workspace, new_layer_name, actual_style_name)
            
            # Save the GeoPackage file temporarily
            temp_dir = self._get_temp_dir()
            gpkg_path = os.path.join(temp_dir, f"{new_layer_name}.gpkg")
            
            with open(gpkg_path, 'wb') as f:
                f.write(response.content)
            
            self.temp_files.append(gpkg_path)
            print(f"DEBUG: Downloaded GeoPackage to {gpkg_path}, size: {len(response.content)} bytes")
            
            # Step 3: Upload the GeoPackage file to target workspace
            print(f"DEBUG: Uploading GeoPackage to target workspace {target_workspace}")
            
            upload_url = f"{url}/rest/workspaces/{target_workspace}/datastores/{new_layer_name}/file.gpkg"
            headers = {'Content-Type': 'application/geopackage+sqlite3'}
            
            with open(gpkg_path, 'rb') as f:
                upload_response = requests.put(
                    upload_url,
                    auth=auth,
                    data=f,
                    headers=headers,
                    timeout=120
                )
            
            print(f"DEBUG: Upload response: {upload_response.status_code}")
            
            if upload_response.status_code not in [200, 201]:
                print(f"DEBUG: Upload failed: {upload_response.text}")
                return False, f"Failed to upload GeoPackage: {upload_response.status_code} - {upload_response.text}"
            
            print(f"DEBUG: GeoPackage uploaded successfully")
            self.created_items.append(('datastore', target_workspace, new_layer_name))
            
            # Step 4: Update the layer with the correct style
            print(f"DEBUG: Updating layer with style {actual_style_name}")
            
            update_layer_url = f"{url}/rest/layers/{target_workspace}:{new_layer_name}"
            layer_update_payload = {
                'layer': {
                    'enabled': True,
                    'defaultStyle': {'name': actual_style_name}
                }
            }
            
            headers_json = {'Content-Type': 'application/json'}
            update_response = requests.put(
                update_layer_url,
                auth=auth,
                json=layer_update_payload,
                headers=headers_json,
                timeout=self.timeout
            )
            
            print(f"DEBUG: Layer update response: {update_response.status_code}")
            
            if update_response.status_code not in [200, 201]:
                print(f"DEBUG: Layer update failed: {update_response.text}")
                # Don't fail - the layer was created successfully
            
            # Clean up temp files on success
            self._cleanup_temp_files_on_success()
            
            self.log_message(f"✓ GeoPackage layer '{layer_name}' copied to '{target_workspace}' as '{new_layer_name}'")
            return True, f"GeoPackage layer '{layer_name}' copied successfully"
            
        except Exception as e:
            print(f"DEBUG: Exception in _copy_geopackage_direct: {str(e)}")
            import traceback
            traceback.print_exc()
            self._cleanup_temp_files_on_failure()
            return False, f"Error copying GeoPackage layer: {str(e)}"
    
    def _copy_geopackage_via_wfs(self, url, auth, source_workspace, layer_name, target_workspace,
                                  new_layer_name, actual_style_name):
        """
        Fallback method: Copy GeoPackage layer using WFS export.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            source_workspace: Source workspace name
            layer_name: Source layer name
            target_workspace: Target workspace name
            new_layer_name: New layer name in target workspace
            actual_style_name: Actual style name from layer's defaultStyle
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            print(f"DEBUG: Using WFS export as fallback for GeoPackage layer {layer_name}")
            
            # Export data from source using WFS GetFeature
            wfs_url = f"{url}/wfs"
            wfs_params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetFeature',
                'typeName': f"{source_workspace}:{layer_name}",
                'outputFormat': 'application/geopackage+sqlite3'
            }
            
            response = requests.get(wfs_url, params=wfs_params, auth=auth, timeout=60)
            if response.status_code != 200:
                print(f"DEBUG: WFS export failed: {response.status_code}")
                print(f"DEBUG: Response text: {response.text}")
                return False, f"Failed to export GeoPackage via WFS: {response.status_code}"
            
            # Save the GeoPackage file temporarily
            temp_dir = self._get_temp_dir()
            gpkg_path = os.path.join(temp_dir, f"{new_layer_name}.gpkg")
            
            with open(gpkg_path, 'wb') as f:
                f.write(response.content)
            
            self.temp_files.append(gpkg_path)
            print(f"DEBUG: Saved GeoPackage to {gpkg_path}, size: {len(response.content)} bytes")
            
            # Upload the file to target workspace
            upload_url = f"{url}/rest/workspaces/{target_workspace}/datastores/{new_layer_name}/file.gpkg"
            headers = {'Content-Type': 'application/geopackage+sqlite3'}
            
            with open(gpkg_path, 'rb') as f:
                upload_response = requests.put(
                    upload_url,
                    auth=auth,
                    data=f,
                    headers=headers,
                    timeout=120
                )
            
            if upload_response.status_code not in [200, 201]:
                print(f"DEBUG: Upload failed: {upload_response.text}")
                return False, f"Failed to upload GeoPackage: {upload_response.status_code}"
            
            self.created_items.append(('datastore', target_workspace, new_layer_name))
            
            # Update the layer with the correct style
            update_layer_url = f"{url}/rest/layers/{target_workspace}:{new_layer_name}"
            layer_update_payload = {
                'layer': {
                    'enabled': True,
                    'defaultStyle': {'name': actual_style_name}
                }
            }
            
            update_response = requests.put(
                update_layer_url,
                auth=auth,
                json=layer_update_payload,
                headers={'Content-Type': 'application/json'},
                timeout=self.timeout
            )
            
            # Clean up temp files on success
            self._cleanup_temp_files_on_success()
            
            self.log_message(f"✓ GeoPackage layer '{layer_name}' copied via WFS to '{target_workspace}' as '{new_layer_name}'")
            return True, f"GeoPackage layer '{layer_name}' copied successfully via WFS"
            
        except Exception as e:
            print(f"DEBUG: Exception in _copy_geopackage_via_wfs: {str(e)}")
            import traceback
            traceback.print_exc()
            self._cleanup_temp_files_on_failure()
            return False, f"Error copying GeoPackage via WFS: {str(e)}"
    
    def _copy_raster_layer(self, url, auth, source_workspace, layer_name, target_workspace,
                           new_layer_name, layer_metadata, actual_style_name):
        """
        Copy a raster layer (GeoTIFF, coverage) by re-uploading the file to target workspace.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            source_workspace: Source workspace name
            layer_name: Source layer name
            target_workspace: Target workspace name
            new_layer_name: New layer name in target workspace
            layer_metadata: Layer metadata dict
            actual_style_name: Actual style name from layer's defaultStyle
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            print(f"DEBUG: _copy_raster_layer - Copying raster layer {layer_name}")
            
            layer_info = layer_metadata.get('layer', {})
            
            # Step 1: Copy the style first
            sld_content = self.extractor.get_layer_style(url, auth, source_workspace, layer_name)
            if sld_content:
                print(f"DEBUG: Copying style '{actual_style_name}' to target workspace")
                success, style_msg = self._copy_sld_style(
                    url, auth, source_workspace, target_workspace, actual_style_name, sld_content
                )
                if success:
                    self.created_items.append(('style', target_workspace, actual_style_name))
                    print(f"DEBUG: Style copied successfully")
                else:
                    print(f"DEBUG: Style copy failed: {style_msg} - continuing anyway")
            
            # Step 2: Export raster data from source using WCS GetCoverage
            print(f"DEBUG: Exporting raster data from source layer via WCS")
            wcs_url = f"{url}/wcs"
            wcs_params = {
                'service': 'WCS',
                'version': '2.0.1',
                'request': 'GetCoverage',
                'coverageId': f"{source_workspace}__{layer_name}",  # WCS 2.0 uses __ separator
                'format': 'image/tiff'  # Export as GeoTIFF
            }
            
            print(f"DEBUG: WCS request to {wcs_url} with params {wcs_params}")
            response = requests.get(wcs_url, params=wcs_params, auth=auth, timeout=120)
            
            if response.status_code != 200:
                # Try alternate coverageId format
                print(f"DEBUG: WCS export failed with __ separator, trying : separator")
                wcs_params['coverageId'] = f"{source_workspace}:{layer_name}"
                response = requests.get(wcs_url, params=wcs_params, auth=auth, timeout=120)
            
            if response.status_code != 200:
                print(f"DEBUG: WCS export failed: {response.status_code}")
                print(f"DEBUG: Response: {response.text[:500] if response.text else 'empty'}")
                return False, f"Failed to export raster data via WCS: {response.status_code}"
            
            # Save the GeoTIFF file temporarily
            temp_dir = self._get_temp_dir()
            tiff_path = os.path.join(temp_dir, f"{layer_name}.tif")
            
            with open(tiff_path, 'wb') as f:
                f.write(response.content)
            
            self.temp_files.append(tiff_path)
            print(f"DEBUG: Saved GeoTIFF to {tiff_path}, size: {len(response.content)} bytes")
            
            # Step 3: Upload the GeoTIFF to target workspace
            print(f"DEBUG: Uploading GeoTIFF to target workspace {target_workspace}")
            
            # Use the REST API to upload the GeoTIFF
            upload_url = f"{url}/rest/workspaces/{target_workspace}/coveragestores/{new_layer_name}/file.geotiff"
            
            headers = {'Content-Type': 'image/tiff'}
            
            with open(tiff_path, 'rb') as f:
                upload_response = requests.put(
                    upload_url,
                    auth=auth,
                    data=f,
                    headers=headers,
                    timeout=180
                )
            
            print(f"DEBUG: Upload response: {upload_response.status_code}")
            
            if upload_response.status_code not in [200, 201]:
                print(f"DEBUG: Upload failed: {upload_response.text}")
                return False, f"Failed to upload GeoTIFF: {upload_response.status_code} - {upload_response.text}"
            
            print(f"DEBUG: GeoTIFF uploaded successfully")
            self.created_items.append(('coveragestore', target_workspace, new_layer_name))
            
            # Step 4: Update the coverage layer with the correct style
            print(f"DEBUG: Updating coverage layer with style {actual_style_name}")
            
            # The coverage layer should be auto-created with the upload, now update its style
            update_layer_url = f"{url}/rest/layers/{target_workspace}:{new_layer_name}"
            
            layer_update_payload = {
                'layer': {
                    'enabled': True,
                    'defaultStyle': {'name': actual_style_name}
                }
            }
            
            headers_json = {'Content-Type': 'application/json'}
            update_response = requests.put(
                update_layer_url,
                auth=auth,
                json=layer_update_payload,
                headers=headers_json,
                timeout=self.timeout
            )
            
            print(f"DEBUG: Layer update response: {update_response.status_code}")
            
            if update_response.status_code not in [200, 201]:
                print(f"DEBUG: Layer update failed: {update_response.text}")
                # Don't fail - the coverage was created successfully
            
            # Clean up temp files on success
            self._cleanup_temp_files_on_success()
            
            self.log_message(f"✓ Raster layer '{layer_name}' copied to '{target_workspace}' as '{new_layer_name}'")
            return True, f"Raster layer '{layer_name}' copied successfully"
            
        except Exception as e:
            print(f"DEBUG: Exception in _copy_raster_layer: {str(e)}")
            import traceback
            traceback.print_exc()
            self._cleanup_temp_files_on_failure()
            error_msg = f"Error copying raster layer: {str(e)}"
            return False, error_msg
    
    def _copy_layer_config(self, url, auth, source_workspace, layer_name, target_workspace, 
                          new_layer_name, layer_metadata, actual_style_name):
        """
        Copy layer configuration to target workspace.
        
        Args:
            url: GeoServer base URL
            auth: Tuple of (username, password)
            source_workspace: Source workspace name
            layer_name: Source layer name
            target_workspace: Target workspace name
            new_layer_name: New layer name in target workspace
            layer_metadata: Layer metadata dict
            actual_style_name: Actual style name from layer's defaultStyle
        
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
                print(f"DEBUG: No feature type found - this should not happen for vector layers")
                return False, "Could not get feature type info for vector layer"
            
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
            
            # Step 0: Ensure the datastore exists in target workspace
            # Note: The datastore should already be created by copy_layer() via datastore_manager
            # But we check again just in case
            print(f"DEBUG: Checking if datastore exists in target workspace")
            check_store_url = f"{url}/rest/workspaces/{target_workspace}/datastores/{datastore_name}.json"
            response = requests.get(check_store_url, auth=auth, timeout=self.timeout)
            
            if response.status_code != 200:
                print(f"DEBUG: Datastore doesn't exist in target, creating it now")
                # Get source datastore config
                source_store_url = f"{url}/rest/workspaces/{source_workspace}/datastores/{datastore_name}.json"
                print(f"DEBUG: Getting source datastore from: {source_store_url}")
                response = requests.get(source_store_url, auth=auth, timeout=self.timeout)
                
                if response.status_code == 200:
                    source_store_data = response.json().get('dataStore', {})
                    print(f"DEBUG: Source store config: type={source_store_data.get('type')}")
                    
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
                    
                    print(f"DEBUG: Creating datastore with payload: {store_payload}")
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
                    print(f"DEBUG: Datastore created successfully")
                else:
                    print(f"DEBUG: Could not get source datastore: {response.status_code}")
                    return False, f"Could not get source datastore: {response.status_code}"
            else:
                print(f"DEBUG: Datastore already exists in target workspace")
            
            # Step 1: Create new feature type by copying the source
            print(f"DEBUG: Creating new feature type: {new_layer_name}")
            
            # For GeoPackage layers, nativeName must match the actual table name in the file
            # Keep the original nativeName from source, only change the published name
            original_native_name = ft_info.get('nativeName', layer_name)
            print(f"DEBUG: Original nativeName: {original_native_name}")
            
            # Create a minimal feature type payload - GeoServer will auto-detect most settings
            # IMPORTANT: Must include namespace with proper URI for the target workspace
            ft_copy = {
                'name': new_layer_name,
                'nativeName': original_native_name,
                'namespace': {
                    'name': target_workspace,
                    'href': f"{url}/rest/namespaces/{target_workspace}.json"
                },
                'title': ft_info.get('title', new_layer_name),
                'srs': ft_info.get('srs', 'EPSG:4326'),
                'enabled': True
            }
            
            # Copy bounding box if available
            if 'nativeBoundingBox' in ft_info:
                ft_copy['nativeBoundingBox'] = ft_info['nativeBoundingBox']
            if 'latLonBoundingBox' in ft_info:
                ft_copy['latLonBoundingBox'] = ft_info['latLonBoundingBox']
            
            print(f"DEBUG: FT copy - name: {ft_copy['name']}, nativeName: {ft_copy['nativeName']}")
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
            
            # Use the actual style name that was passed in (already copied in copy_layer())
            style_name = actual_style_name
            print(f"DEBUG: Using actual style name: {style_name}")
            
            # Check if the style exists in target workspace (it should have been created already)
            check_style_url = f"{url}/rest/workspaces/{target_workspace}/styles/{style_name}.json"
            style_response = requests.get(check_style_url, auth=auth, timeout=self.timeout)
            
            if style_response.status_code != 200:
                # Style doesn't exist, try to ensure it exists by copying from source
                print(f"DEBUG: Style {style_name} not found in target, trying to ensure it exists")
                success, msg = self._ensure_style_exists(url, auth, source_workspace, target_workspace, style_name)
                print(f"DEBUG: Style ensure result: {success}, {msg}")
                if not success:
                    print(f"DEBUG: Could not ensure style exists, layer may use default style")
            else:
                print(f"DEBUG: Style {style_name} already exists in target workspace")
            
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
