"""
Load QGIS Layer Module
Handles the main upload orchestration workflow for QGIS layers to GeoServer.
Extracted from main.py for better code organization and maintainability.
"""

import os
import sys
import importlib.util
from qgis.core import Qgis
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtCore import Qt

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
_lfd = _load_local_module("layer_format_detector")
get_layer_provider_info = _lfd.get_layer_provider_info
_uc = _load_local_module("upload_controller")
UploadController = _uc.UploadController
_up = _load_local_module("upload_processor")
UploadProcessor = _up.UploadProcessor
_ubh = _load_local_module("upload_batch_handler")
UploadBatchHandler = _ubh.UploadBatchHandler
_dlh = _load_local_module("duplicate_layer_handler")
DuplicateLayerHandler = _dlh.DuplicateLayerHandler
_ut = _load_local_module("upload_thread")
UploadThread = _ut.UploadThread


class QGISLayerLoader:
    """Handles the main upload orchestration workflow for QGIS layers."""
    
    def __init__(self, main_instance):
        """
        Initialize the QGIS layer loader.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def load_qgis_layer(self):
        """Exports a QGIS layer using its native format when possible, and uploads it to GeoServer."""
        self.main.log_message("=== load_qgis_layer method called ===")

        # Get connection details
        url = self.main.get_base_url()
        username = self.main.username_input.text()
        password = self.main.password_input.text()
        workspace_item = self.main.workspaces_list.currentItem()
        if not workspace_item:
            QMessageBox.warning(self.main, "Input Error", "Please select a workspace.")
            return
        workspace = workspace_item.text()

        # DEBUG: Log provider info for each selected QGIS layer
        selected_items = self.main.qgis_layers_tree.selectedItems() if hasattr(self.main, 'qgis_layers_tree') else []
        for item in selected_items:
            layer = item.data(0, Qt.ItemDataRole.UserRole) if hasattr(item, 'data') else None
            if layer:
                provider_info = get_layer_provider_info(layer)
                self.main.log_message(f"DEBUG: Provider info for layer '{layer.name()}': {provider_info}")

        if not all([url, username, password, workspace]):
            QMessageBox.warning(self.main, "Input Error", "Please fill in all GeoServer connection details and select a workspace.")
            return

        # Show progress bar
        self.main.load_progress_bar.setVisible(True)
        self.main.update_progress_bar(0)

        # Clear upload log for new session
        self.main.log_tracker.clear()
        
        # Reset overwrite decision for new session
        if hasattr(self.main, '_overwrite_decision'):
            delattr(self.main, '_overwrite_decision')
        
        # Check if log dialog should be shown
        show_log_dialog = self.main.show_log_dialog_checkbox.isChecked()
        
        # Show live log window only if checkbox is checked
        live_log = None
        if show_log_dialog:
            live_log = self.main.log_tracker.show_live_log_window(self.main, "Upload Progress")
        
        # Store the show_log_dialog flag in log_tracker for use during upload
        self.main.log_tracker.show_log_dialog = show_log_dialog
        
        # Start upload in background thread to prevent UI freezing
        self._start_upload_thread(url, username, password, workspace)
    
    def _start_upload_thread(self, url, username, password, workspace):
        """Start the upload process in a background thread."""
        # Initialize and show stop button FIRST, before starting thread
        self.main.stop_upload_btn.setVisible(True)
        self.main.stop_upload_btn.setEnabled(True)
        self.main.log_message("🛑 Stop button initialized and ready")
        
        # Create a lambda that captures all parameters
        upload_func = lambda: self._perform_upload(url, username, password, workspace)
        
        # Create and start the thread
        self.upload_thread = UploadThread(upload_func)
        self.upload_thread.upload_finished.connect(self._on_upload_finished)
        self.upload_thread.upload_error.connect(self._on_upload_error)
        self.upload_thread.show_completion_popup.connect(self._on_show_completion_popup)
        
        # Start the upload thread
        self.upload_thread.start()
    
    def _perform_upload(self, url, username, password, workspace):
        """Perform the actual upload (runs in background thread)."""
        try:
            # Reset stop flag at start of upload
            self.main.upload_stop_requested = False
            
            # Get selected layers from the QGIS project
            self.main.log_message("--- Step 1: Getting Selected Layers ---")
            selected_layers = self.main.get_selected_qgis_layers()
            if not selected_layers:
                self.main.log_message("No layers selected for upload", level=Qgis.Warning)
                self.main.load_progress_bar.setVisible(False)
                return False
            
            self.main.log_message(f"Found {len(selected_layers)} selected layers to upload")
            
            # Filter duplicate layers based on format priority
            duplicate_handler = DuplicateLayerHandler(self.main)
            selected_layers, duplicates_dict = duplicate_handler.filter_duplicate_layers(selected_layers)
            
            if duplicates_dict:
                self.main.log_message(f"\nFiltered {len(duplicates_dict)} duplicate layer(s)")
                for layer_name, dup_info in duplicates_dict.items():
                    self.main.log_message(f"  Layer '{layer_name}': Keeping {dup_info['selected_format']}, skipping {len(dup_info['duplicates'])} duplicate(s)")
            
            self.main.log_message(f"Processing {len(selected_layers)} unique layer(s) for upload")

            # Calculate total size of files to upload for progress tracking
            total_size = 0
            layer_sizes = {}
            for layer in selected_layers:
                source_path = layer.source().split('|')[0]
                if os.path.exists(source_path):
                    try:
                        size = os.path.getsize(source_path)
                        layer_sizes[layer.name()] = size
                        total_size += size
                        self.main.log_message(f"Layer '{layer.name()}' size: {size} bytes")
                    except Exception as e:
                        self.main.log_message(f"Could not get size for layer '{layer.name()}': {e}")
                        layer_sizes[layer.name()] = 0
                else:
                    self.main.log_message(f"File not found for layer '{layer.name()}': {source_path}")
                    layer_sizes[layer.name()] = 0
            
            self.main.log_message(f"Total upload size: {total_size} bytes ({total_size / (1024*1024):.2f} MB)")
            
            # Set progress bar to track layer count as percentage
            total_layers = len(selected_layers)
            self.main.load_progress_bar.setMaximum(100)  # Use percentage
            
            # Initialize upload controller, processor, and batch handler
            upload_controller = UploadController(self.main.log_tracker)
            upload_processor = UploadProcessor(self.main)
            batch_handler = UploadBatchHandler(self.main)
            
            # Analyze batch uploads to detect duplicates
            source_groups = batch_handler.group_layers_by_source(selected_layers)
            batch_info = batch_handler.get_batch_info(source_groups)
            batch_handler.log_batch_info(batch_info)
            
            # Create a mapping of layer to its index for progress tracking
            layer_to_index = {id(layer): i for i, layer in enumerate(selected_layers)}
            
            # Track which sources have already been uploaded
            uploaded_sources = set()
            processed_layers = set()  # Track which layers we've processed
            
            for i, layer in enumerate(selected_layers):
                # Check if stop was requested via stop button
                if self.main.upload_stop_requested:
                    processed_count = len(processed_layers)
                    self.main.log_message(f"🛑 Upload stopped by user at layer {processed_count+1}/{total_layers}")
                    
                    # Mark all remaining unprocessed layers as skipped
                    for remaining_layer in selected_layers:
                        if id(remaining_layer) not in processed_layers:
                            self.main.log_message(f"⏭️ Skipping layer '{remaining_layer.name()}' - upload stopped by user")
                            self.main.log_tracker.track_skip_user(remaining_layer.name())
                            processed_layers.add(id(remaining_layer))
                    
                    break
                
                # Skip if this layer was already processed as part of a batch
                if id(layer) in processed_layers:
                    continue
                
                # Count how many layers we've actually processed (not skipped)
                processed_count = len(processed_layers)
                
                # Add special layer title in blue color with larger font
                self.main.log_tracker.add_layer_title(layer.name())
                self.main.log_message(f"Processing layer {processed_count+1}/{total_layers}")
                
                # Check upload control signals (stop, pause, step-in)
                control_result = upload_controller.process_layer_controls(layer.name())
                if control_result == 'stop':
                    self.main.log_message(f"🛑 Upload stopped by user at layer {processed_count+1}/{total_layers}")
                    break
                
                # Update progress bar at start of each layer - use SELECTED layer count, not QGIS project indices
                progress_percent = int(((processed_count + 1) / total_layers) * 100)
                self.main.update_progress_bar(progress_percent)
                self.main.log_message(f"Progress: {progress_percent}% (Layer {processed_count+1}/{total_layers})")
                
                provider_info = get_layer_provider_info(layer)
                upload_method = provider_info.get('upload_method')
                native_format = provider_info.get('native_format')
                layer_name = self.main._sanitize_layer_name(layer.name())
                self.main.log_message(f"DEBUG: Layer '{layer.name()}' format: {native_format}, upload method: {upload_method}")
                
                # Get source path for duplicate detection
                source_path = layer.source().split('|')[0].split('?')[0]
                
                # For ALL batch sources (GeoPackage, shapefile directories, databases, etc.), find all layers from the same source
                # This applies to: importer, shapefile_conversion, AND database sources
                # Find all layers from this source
                layers_from_source = [l for l in selected_layers if l.source().split('|')[0].split('?')[0] == source_path]
                
                # Check if this source has already been uploaded
                if source_path in uploaded_sources:
                    self.main.log_message(f"⚠️ BATCH SOURCE DETECTED: '{source_path}' already loaded")
                    for batch_layer in layers_from_source:
                        self.main.log_message(f"⏭️ Skipping layer '{batch_layer.name()}' - datastore already loaded, no additional upload required")
                        self.main.log_tracker.track_skip_batch(batch_layer.name())
                        processed_layers.add(id(batch_layer))
                    continue
                
                # Mark ALL layers from this source as processed BEFORE upload
                # This prevents the loop from trying to upload the same source multiple times
                for batch_layer in layers_from_source:
                    processed_layers.add(id(batch_layer))
                
                # Mark this source as uploaded BEFORE upload attempt
                uploaded_sources.add(source_path)
                
                # Log how many layers will be published from this source (if more than 1)
                if len(layers_from_source) > 1:
                    self.main.log_message(f"📦 BATCH UPLOAD: Uploading {len(layers_from_source)} layers from source: {source_path}")
                    self.main.log_message(f"   Layers: {', '.join([l.name() for l in layers_from_source])}")
                
                # For batch uploads, check and delete ALL layers from the source
                # For single uploads, just check the one layer
                layers_to_check = layers_from_source if len(layers_from_source) > 1 else [layer]
                
                # DEBUG: Log which layers we're checking
                if len(layers_from_source) > 1:
                    self.main.log_message(f"DEBUG: Checking {len(layers_to_check)} layers from batch source")
                
                should_skip_all = False
                for check_layer in layers_to_check:
                    check_layer_name = self.main._sanitize_layer_name(check_layer.name())
                    layer_exists = self.main._layer_exists_in_workspace(check_layer_name, workspace, url, username, password)
                    
                    if layer_exists:
                        # Layer exists - check if we should overwrite
                        if self.main.auto_overwrite_checkbox.isChecked():
                            self.main.log_message(f"🔄 Auto-overwrite enabled: Deleting existing layer '{check_layer_name}' before re-upload...")
                            # Delete existing layer and its datastore/coveragestore
                            self.main._delete_existing_layer(check_layer_name, workspace, url, username, password)
                        else:
                            # Ask user what to do with existing layer (only if not already decided for all)
                            if not hasattr(self.main, '_overwrite_decision'):
                                overwrite_action = self.main._ask_overwrite_existing_layer(check_layer_name, i+1, total_layers)
                                if overwrite_action in ['skip_all', 'overwrite_all']:
                                    self.main._overwrite_decision = overwrite_action
                            else:
                                overwrite_action = self.main._overwrite_decision
                            
                            if overwrite_action in ['skip', 'skip_all']:
                                self.main.log_message(f"⚠ Layer '{check_layer_name}' already exists in workspace '{workspace}'. Skipping as requested.", level=Qgis.Warning)
                                self.main.log_tracker.track_skip_user(check_layer_name)
                                if overwrite_action == 'skip_all':
                                    should_skip_all = True
                            elif overwrite_action in ['overwrite', 'overwrite_all']:
                                self.main.log_message(f"🔄 Overwriting existing layer '{check_layer_name}'...")
                                # Delete existing layer and its datastore/coveragestore
                                self.main._delete_existing_layer(check_layer_name, workspace, url, username, password)
                    else:
                        self.main.log_message(f"✓ Layer '{check_layer_name}' does not exist in workspace. Proceeding with upload.")
                
                if should_skip_all:
                    continue

                # Clean up any duplicate datastores/coveragestores BEFORE upload for ALL layers in batch
                # This prevents the importer from creating more duplicates
                for cleanup_layer in layers_to_check:
                    cleanup_layer_name = self.main._sanitize_layer_name(cleanup_layer.name())
                    self.main.log_message(f"DEBUG: Cleaning up duplicate stores for '{cleanup_layer_name}'")
                    self.main._cleanup_all_duplicate_stores_for_layer(cleanup_layer_name, workspace, url, username, password)

                # For batch uploads (multiple layers from same source), upload ONCE
                if len(layers_from_source) > 1:
                    self.main.log_message(f"📦 BATCH UPLOAD: Processing {len(layers_from_source)} layers from single source")
                    
                    # Check if this is a GeoPackage batch upload
                    first_layer = layers_from_source[0]
                    source_path = first_layer.source().split('|')[0].split('?')[0]
                    is_geopackage = source_path.lower().endswith('.gpkg')
                    
                    if is_geopackage:
                        # Use native batch uploader for GeoPackage
                        self.main.log_message(f"📦 GeoPackage batch upload detected - uploading all {len(layers_from_source)} layers together")
                        success = self.main.geopackage_native_uploader.upload_geopackage_batch(layers_from_source, workspace, url, username, password)
                        
                        if success:
                            # Handle success for ALL layers in the batch
                            for batch_layer in layers_from_source:
                                batch_layer_name = self.main._sanitize_layer_name(batch_layer.name())
                                upload_processor.handle_upload_success(batch_layer, batch_layer_name, workspace, url, username, password)
                                self.main.log_message(f"✅ Batch layer '{batch_layer.name()}' processed successfully")
                        else:
                            # Handle failure for ALL layers in the batch
                            for batch_layer in layers_from_source:
                                upload_processor.handle_upload_failure(batch_layer)
                                self.main.log_message(f"❌ Batch layer '{batch_layer.name()}' failed")
                    else:
                        # For batch shapefile/other uploads, upload each layer individually
                        # (Importer API only publishes the first layer when uploading a directory)
                        self.main.log_message(f"📦 Batch upload: Uploading {len(layers_from_source)} layers individually")
                        all_success = True
                        
                        for batch_layer in layers_from_source:
                            batch_layer_name = self.main._sanitize_layer_name(batch_layer.name())
                            self.main.log_message(f"📤 Uploading batch layer: '{batch_layer.name()}' ({batch_layer_name})")
                            
                            success = upload_processor.process_upload(batch_layer, batch_layer_name, workspace, url, username, password, upload_method, native_format)
                            
                            if success:
                                upload_processor.handle_upload_success(batch_layer, batch_layer_name, workspace, url, username, password)
                                self.main.log_message(f"✅ Batch layer '{batch_layer.name()}' uploaded successfully")
                            else:
                                upload_processor.handle_upload_failure(batch_layer)
                                self.main.log_message(f"❌ Batch layer '{batch_layer.name()}' failed")
                                all_success = False
                else:
                    # Single layer upload
                    self.main.log_message(f"DEBUG: Single layer upload for '{layer.name()}'")
                    success = upload_processor.process_upload(layer, layer_name, workspace, url, username, password, upload_method, native_format)
                    
                    self.main.log_message(f"DEBUG: Upload result for layer '{layer.name()}': {success}")

                    if success:
                        upload_processor.handle_upload_success(layer, layer_name, workspace, url, username, password)
                    else:
                        upload_processor.handle_upload_failure(layer)

            # Set progress to 100% when all layers are complete
            self.main.update_progress_bar(100)

            self.main.load_progress_bar.setVisible(False)
            
            # Reset upload controls for next session
            upload_controller.reset_controls()
            
            # Mark upload as complete
            if hasattr(self.main, 'log_tracker'):
                self.main.log_tracker.update_window_title("Upload Complete")
                # Disable upload control buttons
                self.main.log_tracker.disable_controls()
            
            # Show duplicates report if any duplicates were filtered
            duplicates_report = duplicate_handler.show_duplicates_report()
            if duplicates_report:
                self.main.log_message(duplicates_report)
            
            # Emit signal to show completion popup on main thread
            self.upload_thread.show_completion_popup.emit()
            
            # Refresh only the current workspace layers WITHOUT changing workspace selection
            self.main.load_workspace_layers()
            self.main.load_stores()
            
            return True
            
        except Exception as e:
            import traceback
            self.main.log_message(f"Error during upload: {str(e)}", level=Qgis.Critical)
            self.main.log_message(traceback.format_exc(), level=Qgis.Critical)
            self.main.load_progress_bar.setVisible(False)
            return False
    
    def _on_upload_finished(self, success):
        """Handle upload completion."""
        # Hide stop button
        self.main.stop_upload_btn.setVisible(False)
        
        if success:
            self.main.log_message("✅ Upload process completed successfully")
        else:
            self.main.log_message("❌ Upload process failed", level=Qgis.Critical)
        
        # Save log to file
        if hasattr(self.main, 'log_tracker'):
            log_file_path = self.main.log_tracker.save_log_to_file()
            if log_file_path:
                self.main.log_message(f"📁 Log saved to: {log_file_path}")
    
    def _on_upload_error(self, error_message):
        """Handle upload error."""
        # Hide stop button
        self.main.stop_upload_btn.setVisible(False)
        
        self.main.log_message(f"❌ Upload error: {error_message}", level=Qgis.Critical)
        self.main.load_progress_bar.setVisible(False)
    
    def _on_show_completion_popup(self):
        """Show completion popup on main thread."""
        if hasattr(self.main, 'log_tracker'):
            self.main.log_tracker.show_completion_popup(self.main)
