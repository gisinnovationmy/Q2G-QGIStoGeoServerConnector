"""
Copy/Move Thread Module
Handles layer copy/move operations in a background thread to prevent UI freezing.
"""

from qgis.PyQt.QtCore import QThread, pyqtSignal
from qgis.core import Qgis, QgsMessageLog


class CopyMoveThread(QThread):
    """Background thread for handling layer copy/move operations."""
    
    # Signals
    progress_updated = pyqtSignal(int, str)           # percentage, message
    layer_progress = pyqtSignal(str, bool, str)       # layer_name, success, message
    operation_finished = pyqtSignal(bool, str)        # success, result_message
    error_occurred = pyqtSignal(str)                  # error_message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.operation_mode = None  # 'copy' or 'move'
        self.layers = []
        self.source_workspace = None
        self.target_workspace = None
        self.conflict_strategy = 'rename'  # 'rename', 'skip', 'overwrite'
        self.url = None
        self.username = None
        self.password = None
        self.handler = None
        self.results = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
    
    def set_operation(self, operation_mode, layers, source_workspace, target_workspace, 
                     conflict_strategy, url, username, password, handler):
        """
        Set up the copy/move operation parameters.
        
        Args:
            operation_mode: 'copy' or 'move'
            layers: List of layer names to copy/move
            source_workspace: Source workspace name
            target_workspace: Target workspace name
            conflict_strategy: 'rename', 'skip', or 'overwrite'
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            handler: LayerCopyMoveHandler instance
        """
        self.operation_mode = operation_mode
        self.layers = layers
        self.source_workspace = source_workspace
        self.target_workspace = target_workspace
        self.conflict_strategy = conflict_strategy
        self.url = url
        self.username = username
        self.password = password
        self.handler = handler
        self.results = {
            'total': len(layers),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
    
    def run(self):
        """Execute the copy/move operation in background thread."""
        try:
            self.log_message(f"🔄 Starting {self.operation_mode.upper()} operation for {len(self.layers)} layer(s)")
            self.log_message(f"Source: {self.source_workspace} → Target: {self.target_workspace}")
            
            # Process each layer
            for index, layer_name in enumerate(self.layers):
                try:
                    # Calculate progress
                    progress = int((index / len(self.layers)) * 100)
                    self.progress_updated.emit(progress, f"Processing layer {index + 1}/{len(self.layers)}: {layer_name}")
                    
                    # Perform copy or move
                    if self.operation_mode == 'copy':
                        success, message = self.handler.copy_layer(
                            self.url,
                            (self.username, self.password),
                            self.source_workspace,
                            layer_name,
                            self.target_workspace,
                            layer_name,  # new_name same as original
                            self.conflict_strategy
                        )
                    else:  # move
                        success, message = self.handler.move_layer(
                            self.url,
                            (self.username, self.password),
                            self.source_workspace,
                            layer_name,
                            self.target_workspace,
                            layer_name,  # new_name same as original
                            self.conflict_strategy
                        )
                    
                    # Track result
                    if success:
                        self.results['successful'] += 1
                        self.layer_progress.emit(layer_name, True, message)
                    else:
                        if 'skipped' in message.lower():
                            self.results['skipped'] += 1
                        else:
                            self.results['failed'] += 1
                        self.layer_progress.emit(layer_name, False, message)
                    
                    self.results['details'].append({
                        'layer': layer_name,
                        'success': success,
                        'message': message
                    })
                    
                except Exception as e:
                    self.results['failed'] += 1
                    error_msg = f"Error processing layer '{layer_name}': {str(e)}"
                    self.layer_progress.emit(layer_name, False, error_msg)
                    self.results['details'].append({
                        'layer': layer_name,
                        'success': False,
                        'message': error_msg
                    })
                    self.log_message(f"❌ {error_msg}", level=Qgis.Warning)
            
            # Emit final result
            progress = 100
            self.progress_updated.emit(progress, "Operation complete")
            
            # Generate summary message
            summary = self._generate_summary()
            success = self.results['failed'] == 0
            
            self.operation_finished.emit(success, summary)
            self.log_message(f"✅ {self.operation_mode.upper()} operation completed: {summary}")
            
        except Exception as e:
            import traceback
            error_msg = f"Critical error in {self.operation_mode} operation: {str(e)}\n{traceback.format_exc()}"
            self.error_occurred.emit(error_msg)
            self.log_message(f"❌ {error_msg}", level=Qgis.Critical)
            self.operation_finished.emit(False, error_msg)
    
    def _generate_summary(self):
        """Generate a summary message of the operation results."""
        total = self.results['total']
        successful = self.results['successful']
        failed = self.results['failed']
        skipped = self.results['skipped']
        
        summary = f"{self.operation_mode.upper()} Summary: {successful}/{total} successful"
        
        if failed > 0:
            summary += f", {failed} failed"
        if skipped > 0:
            summary += f", {skipped} skipped"
        
        return summary
    
    def log_message(self, message, level=Qgis.Info):
        """Log a message to QGIS message log."""
        QgsMessageLog.logMessage(message, "Q2G", level=level)
