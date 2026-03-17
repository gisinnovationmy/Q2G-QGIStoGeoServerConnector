"""
Copy/Move Layers Dialog Module
Dialog for copying or moving layers between workspaces.
"""

import os
import sys
import importlib.util
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QComboBox, QTextEdit, QProgressBar, QGroupBox
)
from qgis.PyQt.QtCore import Qt, pyqtSignal, QTimer
from qgis.PyQt.QtGui import QFont
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
_cmt = _load_local_module("copy_move_thread")
CopyMoveThread = _cmt.CopyMoveThread
_lcmh = _load_local_module("layer_copy_move_handler")
LayerCopyMoveHandler = _lcmh.LayerCopyMoveHandler
_lme = _load_local_module("layer_metadata_extractor")
LayerMetadataExtractor = _lme.LayerMetadataExtractor


class CopyMoveLayersDialog(QDialog):
    """Dialog for copying or moving layers between workspaces."""
    
    # Signal emitted when operation completes successfully
    operation_completed = pyqtSignal(str)  # target_workspace
    
    def __init__(self, parent=None, layers=None, source_workspace=None, operation_mode='copy',
                 url=None, auth=None, conflict_strategy=None):
        super().__init__(parent)
        
        self.layers = layers or []
        self.source_workspace = source_workspace
        self.operation_mode = operation_mode  # 'copy' or 'move'
        self.url = url
        self.auth = auth
        self.target_workspace = None
        self.conflict_strategy = conflict_strategy  # 'rename', 'skip', 'overwrite', or None
        
        self.extractor = LayerMetadataExtractor()
        self.handler = LayerCopyMoveHandler()
        self.thread = None
        
        self.setWindowTitle(f"{operation_mode.capitalize()} Layer(s) to Another Workspace")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        self._init_ui()
        self._populate_workspaces()
        
        # If conflict strategy is provided, set it and auto-start
        if self.conflict_strategy:
            # Set the conflict combo to the provided strategy
            strategy_map = {
                'rename': 0,
                'skip': 1,
                'overwrite': 2
            }
            if self.conflict_strategy in strategy_map:
                self.conflict_combo.setCurrentIndex(strategy_map[self.conflict_strategy])
                # Auto-start the operation after a short delay (wait for UI to be ready)
                from qgis.PyQt.QtCore import QTimer
                QTimer.singleShot(200, self._auto_start_operation)
    
    def _init_ui(self):
        """Initialize the dialog UI."""
        layout = QVBoxLayout()
        
        # Source info
        source_group = QGroupBox("Source")
        source_layout = QVBoxLayout()
        source_layout.addWidget(QLabel(f"Workspace: {self.source_workspace}"))
        source_layout.addWidget(QLabel(f"Layers ({len(self.layers)}):"))
        
        layers_list = QListWidget()
        layers_list.setMaximumHeight(80)
        for layer in self.layers:
            layers_list.addItem(layer)
        source_layout.addWidget(layers_list)
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)
        
        # Target workspace selector
        target_group = QGroupBox("Target Workspace")
        target_layout = QVBoxLayout()
        target_layout.addWidget(QLabel("Select target workspace:"))
        
        self.workspace_list = QListWidget()
        self.workspace_list.itemSelectionChanged.connect(self._on_workspace_selected)
        target_layout.addWidget(self.workspace_list)
        target_group.setLayout(target_layout)
        layout.addWidget(target_group)
        
        # Conflict handling
        conflict_group = QGroupBox("Conflict Handling")
        conflict_layout = QHBoxLayout()
        conflict_layout.addWidget(QLabel("If layer exists:"))
        
        self.conflict_combo = QComboBox()
        self.conflict_combo.addItems(["Rename (add _copy)", "Skip", "Overwrite"])
        conflict_layout.addWidget(self.conflict_combo)
        conflict_layout.addStretch()
        conflict_group.setLayout(conflict_layout)
        layout.addWidget(conflict_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Log area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setVisible(False)
        layout.addWidget(self.log_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.copy_move_btn = QPushButton(f"✓ {self.operation_mode.capitalize()}")
        self.copy_move_btn.setMinimumHeight(32)
        self.copy_move_btn.clicked.connect(self._on_copy_move_clicked)
        button_layout.addWidget(self.copy_move_btn)
        
        self.cancel_btn = QPushButton("✕ Cancel")
        self.cancel_btn.setMinimumHeight(32)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _populate_workspaces(self):
        """Populate the workspace list, excluding source workspace."""
        try:
            workspaces = self.extractor.get_all_workspaces(self.url, self.auth)
            
            for workspace in workspaces:
                if workspace != self.source_workspace:
                    self.workspace_list.addItem(workspace)
            
            if self.workspace_list.count() == 0:
                self._log_message("❌ No other workspaces available", Qgis.Warning)
                self.copy_move_btn.setEnabled(False)
        
        except Exception as e:
            self._log_message(f"❌ Error loading workspaces: {str(e)}", Qgis.Critical)
            self.copy_move_btn.setEnabled(False)
    
    def _on_workspace_selected(self):
        """Handle workspace selection."""
        selected = self.workspace_list.selectedItems()
        if selected:
            self.target_workspace = selected[0].text()
    
    def _auto_start_operation(self):
        """Auto-start the operation when conflict strategy is provided."""
        try:
            # Select first workspace if not already selected
            if self.workspace_list.count() > 0 and not self.target_workspace:
                self.workspace_list.setCurrentRow(0)
                self.target_workspace = self.workspace_list.item(0).text()
            
            # Start the operation
            self._on_copy_move_clicked()
        except Exception as e:
            self._log_message(f"Error auto-starting operation: {str(e)}", Qgis.Critical)
    
    def _on_copy_move_clicked(self):
        """Handle copy/move button click."""
        if not self.target_workspace:
            self._log_message("❌ Please select a target workspace", Qgis.Warning)
            return
        
        if not self.layers:
            self._log_message("❌ No layers selected", Qgis.Warning)
            return
        
        # Disable buttons and show progress
        self.copy_move_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.workspace_list.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log_text.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Get conflict strategy
        conflict_map = {
            "Rename (add _copy)": "rename",
            "Skip": "skip",
            "Overwrite": "overwrite"
        }
        conflict_strategy = conflict_map.get(self.conflict_combo.currentText(), "rename")
        
        # Create and start thread
        self.thread = CopyMoveThread()
        self.thread.set_operation(
            self.operation_mode,
            self.layers,
            self.source_workspace,
            self.target_workspace,
            conflict_strategy,
            self.url,
            self.auth[0],
            self.auth[1],
            self.handler
        )
        
        # Connect signals
        self.thread.progress_updated.connect(self._on_progress_updated)
        self.thread.layer_progress.connect(self._on_layer_progress)
        self.thread.operation_finished.connect(self._on_operation_finished)
        self.thread.error_occurred.connect(self._on_error_occurred)
        
        # Start thread
        self.thread.start()
    
    def _on_progress_updated(self, percentage, message):
        """Handle progress update."""
        self.progress_bar.setValue(percentage)
        self._log_message(message)
    
    def _on_layer_progress(self, layer_name, success, message):
        """Handle layer progress."""
        status = "✓" if success else "✗"
        self._log_message(f"{status} {layer_name}: {message}")
    
    def _on_operation_finished(self, success, message):
        """Handle operation completion."""
        self._log_message(f"\n{'='*50}")
        self._log_message(f"📊 {message}")
        self._log_message(f"{'='*50}\n")
        
        if success:
            self._log_message(f"✅ {self.operation_mode.capitalize()} completed successfully!")
            
            # Auto-close after 2 seconds
            QTimer.singleShot(2000, self._close_and_emit)
        else:
            self._log_message(f"⚠️ {self.operation_mode.capitalize()} completed with issues", Qgis.Warning)
            
            # Re-enable buttons for retry
            self.copy_move_btn.setEnabled(True)
            self.cancel_btn.setEnabled(True)
            self.workspace_list.setEnabled(True)
    
    def _on_error_occurred(self, error_message):
        """Handle error."""
        self._log_message(f"❌ Error: {error_message}", Qgis.Critical)
        
        # Re-enable buttons
        self.copy_move_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        self.workspace_list.setEnabled(True)
    
    def _close_and_emit(self):
        """Close dialog and emit completion signal."""
        self.operation_completed.emit(self.target_workspace)
        self.accept()
    
    def _log_message(self, message, level=Qgis.Info):
        """Log message to both dialog and QGIS log."""
        self.log_text.append(message)
        QgsMessageLog.logMessage(message, "Q2G", level=level)
