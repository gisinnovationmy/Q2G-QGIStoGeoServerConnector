import os
import sys

# Global debug flag - set to False for production (faster startup)
DEBUG_VERBOSE = False

# Dynamic imports using ImportManager (works with any folder name)
# Handle both package context (relative import) and script context (absolute import)
try:
    # Try relative import first (works when run as QGIS plugin)
    from .import_manager import dynamic_import, get_import_manager
except (ImportError, ValueError) as e:
    # Fallback to absolute import (works when run from console/script)
    # Add current directory to path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    from import_manager import dynamic_import, get_import_manager

# Initialize import manager (silently)
_manager = get_import_manager()

# Import all required modules and classes dynamically
get_layer_provider_info = dynamic_import("layer_format_detector", "get_layer_provider_info")
# PreviewDialog imported lazily to avoid QtWebEngineWidgets dependency on all machines
LayerExtentsDialog = dynamic_import("layer_extents_dialog", "LayerExtentsDialog")
SLDViewerDialog = dynamic_import("sld_viewer_dialog", "SLDViewerDialog")
UploadController = dynamic_import("upload_controller", "UploadController")
UploadProcessor = dynamic_import("upload_processor", "UploadProcessor")
UploadBatchHandler = dynamic_import("upload_batch_handler", "UploadBatchHandler")
UploadLogTracker = dynamic_import("logs", "UploadLogTracker")
PostGISCredentialsManager = dynamic_import("postgis_credentials", "PostGISCredentialsManager")
PostGISRegistrationPublisher = dynamic_import("postgis_registration_publishing", "PostGISRegistrationPublisher")
QGISLayerLoader = dynamic_import("load_qgis_layer", "QGISLayerLoader")
SLDStyleUploader = dynamic_import("upload_sld_style", "SLDStyleUploader")
TaskVerificationPublisher = dynamic_import("verify_publish_tasks", "TaskVerificationPublisher")
SLDConverter = dynamic_import("convert_se_to_sld_1_0", "SLDConverter")
QGISLayersPopulator = dynamic_import("populate_qgis_layers", "QGISLayersPopulator")
StyleSLDWindowManager = dynamic_import("show_style_sld_window", "StyleSLDWindowManager")
WorkspaceContentRefresher = dynamic_import("refresh_current_workspace_content", "WorkspaceContentRefresher")
WMSLayerBBoxRetriever = dynamic_import("get_wms_layer_bbox", "WMSLayerBBoxRetriever")
CacheResetManager = dynamic_import("reset_all_caches", "CacheResetManager")
ProgressBarUpdater = dynamic_import("update_progress_bar", "ProgressBarUpdater")
StyleDeletionManager = dynamic_import("delete_selected_style", "StyleDeletionManager")
LayerStylesLoader = dynamic_import("load_layer_styles", "LayerStylesLoader")
DatastoreDeletionManager = dynamic_import("delete_selected_datastores", "DatastoreDeletionManager")
LayerDeletionManager = dynamic_import("delete_layer", "LayerDeletionManager")
WorkspaceDeletionManager = dynamic_import("delete_workspace", "WorkspaceDeletionManager")
WorkspaceCreationManager = dynamic_import("create_workspace", "WorkspaceCreationManager")
SLDWindowManager = dynamic_import("show_sld_window", "SLDWindowManager")
GeoPackageDatastorePublisher = dynamic_import("register_geopackage_datastore_publish", "GeoPackageDatastorePublisher")
GeoServerLayersListRefresher = dynamic_import("refresh_geoserver_layers_list", "GeoServerLayersListRefresher")
DuplicateGlobalStylesCleaner = dynamic_import("cleanup_duplicate_global_styles", "DuplicateGlobalStylesCleaner")
TemporaryDatastoresCleaner = dynamic_import("cleanup_temporary_datastores", "TemporaryDatastoresCleaner")
DuplicateDatastoresCleaner = dynamic_import("cleanup_duplicate_datastores", "DuplicateDatastoresCleaner")
AllDuplicateStoresForLayerCleaner = dynamic_import("cleanup_all_duplicate_stores_for_layer", "AllDuplicateStoresForLayerCleaner")
ExistingLayerDeleter = dynamic_import("delete_existing_layer", "ExistingLayerDeleter")
OverwriteExistingLayerDialog = dynamic_import("ask_overwrite_existing_layer", "OverwriteExistingLayerDialog")
LayersAndStylesSetupManager = dynamic_import("setup_layers_and_styles", "LayersAndStylesSetupManager")
GeoPackageLayerExistenceChecker = dynamic_import("geopackage_layer_exists_in_datastore", "GeoPackageLayerExistenceChecker")
GeoPackageNativeUploader = dynamic_import("geopackage_native", "GeoPackageNativeUploader")
LayerExistenceChecker = dynamic_import("layer_existence_checker", "LayerExistenceChecker")
GeoPackageDatastoreNameExtractor = dynamic_import("get_geopackage_datastore_name", "GeoPackageDatastoreNameExtractor")
PostGISCredentialsDialog = dynamic_import("postgis_dialog", "PostGISCredentialsDialog")
CORSManager = dynamic_import("cors_manager", "CORSManager")
FirstLoadDialog = dynamic_import("first_load_dialog", "FirstLoadDialog")
should_show_first_load_dialog = dynamic_import("first_load_dialog", "should_show_first_load_dialog")
__version__ = dynamic_import("__init__", "__version__")

import configparser
import re
import requests
import tempfile
import zipfile
import shutil
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

# Additional Qt/QGIS imports required by this module
from PyQt5.QtCore import Qt, QSize, QTimer, QCoreApplication
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QHBoxLayout, 
    QSplitter, QListWidget, QCheckBox, QTreeWidget, QTreeWidgetItem, QHeaderView, 
    QProgressBar, QMessageBox, QFileDialog, QAbstractItemView, QSizePolicy, QGroupBox,
    QTextEdit, QLabel, QApplication, QMenu, QInputDialog, QWidget, QToolBar
)
from qgis.PyQt.QtGui import QAction
from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer, QgsMessageLog, Qgis, QgsPathResolver
from qgis.core import Qgis


class QGISGeoServerLayerLoader(QDialog):
    """Dialog to manage GeoServer data import using the Importer REST API."""
    
    def tr(self, message):
        """
        Get the translation for a string using Qt translation API.
        
        :param message: String for translation.
        :type message: str, QString
        
        :returns: Translated version of message.
        :rtype: QString
        """
        return QCoreApplication.translate('QGISGeoServerLayerLoader', message)
    
    def add_action(self, icon_path, text, callback, enabled_flag=True, add_to_menu=True, add_to_toolbar=True, status_tip=None, whats_this=None, parent=None):
        """
        Add a toolbar icon to the toolbar.
        
        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str
        
        :param text: Text that should be shown in menu items for this action.
        :type text: str
        
        :param callback: Function to be called when the action is triggered.
        :type callback: function
        
        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool
        
        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool
        
        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool
        
        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str
        
        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget
        
        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.
        
        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        
        if status_tip is not None:
            action.setStatusTip(status_tip)
        
        if whats_this is not None:
            action.setWhatsThis(whats_this)
        
        if add_to_menu:
            self.iface.addPluginToWebMenu(
                self.menu,
                action)
        
        self.actions.append(action)
        
        return action
    
    def _show_custom_notification(self, message):
        """Show a popup notification dialog with light blue background and dark blue text."""
        print(f"DEBUG: _show_custom_notification called with message: {message}")
        try:
            from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel
            from PyQt5.QtCore import QTimer, Qt
            from PyQt5.QtGui import QFont
            
            # Create dialog
            main_window = self.iface.mainWindow()
            print(f"DEBUG: main_window: {main_window}")
            
            dialog = QDialog(main_window)
            dialog.setWindowTitle("")
            dialog.setModal(False)
            dialog.setAttribute(Qt.WA_TranslucentBackground)
            dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
            dialog.raise_()
            dialog.activateWindow()
            
            # Create layout
            layout = QVBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            
            # Create label
            label = QLabel(message)
            label.setFont(QFont("Arial", 11, QFont.Normal))
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    background-color: #d4e8f7;
                    color: #003d7a;
                    padding: 15px 25px;
                    border-radius: 4px;
                    font-size: 11px;
                    border: 1px solid #a8d0e8;
                }
            """)
            
            layout.addWidget(label)
            dialog.setLayout(layout)
            
            # Position dialog in center-top of screen
            screen_geometry = main_window.geometry()
            dialog_width = 380
            dialog_height = 70
            x = screen_geometry.center().x() - dialog_width // 2
            y = screen_geometry.top() + 100
            dialog.setGeometry(x, y, dialog_width, dialog_height)
            
            print(f"DEBUG: Showing notification dialog at ({x}, {y})")
            # Show dialog
            dialog.show()
            
            # Auto-close after 3 seconds
            QTimer.singleShot(3000, dialog.close)
            print(f"DEBUG: Notification dialog shown successfully")
            
        except Exception as e:
            print(f"DEBUG: Error showing custom notification: {e}")
            import traceback
            traceback.print_exc()
    
    def _setup_window_and_styling(self):
        """Setup window properties and apply modern stylesheet."""
        self.setWindowTitle("Q2G - QGIS to GeoServer")
        self.setMinimumSize(900, 650)
        self.setWindowFlags(Qt.Window | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        
        # Set window icon from logo
        try:
            plugin_dir = os.path.dirname(os.path.abspath(__file__))
            logo_path = os.path.join(plugin_dir, 'logos', '11_spiral_blue2.svg')
            if os.path.exists(logo_path):
                icon = QIcon(logo_path)
                self.setWindowIcon(icon)
        except Exception as e:
            self.log_message(f"Note: Could not load window icon: {e}", level=Qgis.Info)
        
        # Try to set QGIS icon in top right (if iface is available)
        try:
            if self.iface:
                qgis_icon = self.iface.mainWindow().windowIcon()
                if not qgis_icon.isNull():
                    # Create a composite icon or use QGIS icon as fallback
                    self.setWindowIcon(qgis_icon)
        except Exception as e:
            pass  # Silently fail if QGIS icon not available
        
        # Set a modern stylesheet
        self.setStyleSheet('''
            QDialog { background: #f6f6f6; }
            QGroupBox { font-weight: bold; border: 1px solid #bbb; border-radius: 6px; margin-top: 8px; background: #fcfcfc; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; }
            QLabel { font-size: 10pt; }
            QLineEdit, QComboBox, QListWidget, QTreeWidget { font-size: 10pt; background: #fff; border: 1px solid #ccc; border-radius: 3px; }
            QPushButton { font-size: 10pt; padding: 6px 16px; background: #e6e6e6; border: 1px solid #aaa; border-radius: 4px; }
            QPushButton:hover { background: #d0eaff; border: 1px solid #3399ff; }
            QPushButton:pressed { background: #b5d9ff; }
            QPushButton#import { background: #4CAF50; color: white; border: 1px solid #388E3C; }
            QPushButton#delete, QPushButton#delete_style_btn, QPushButton#delete_workspace_btn { background: #f44336; color: white; border: 1px solid #b71c1c; }
            QCheckBox { font-size: 10pt; }
            QProgressBar { border: 1px solid #0078d4; border-radius: 4px; background: #f0f0f0; height: 28px; }
            QProgressBar::chunk { background: #0078d4; border-radius: 3px; }
        ''')
    
    def _setup_connection_section(self, main_layout):
        """Setup GeoServer connection section with collapsible group box and buttons."""
        # Horizontal layout for Connection Settings and Others groups
        conn_others_layout = QHBoxLayout()
        conn_others_layout.setSpacing(12)
        
        # ===== CONNECTION SETTINGS GROUP =====
        conn_group = QGroupBox("Connection Settings")
        conn_group.setCheckable(True)
        conn_group.setChecked(True)
        conn_layout = QVBoxLayout()
        
        # Form layout for connection fields
        form_layout = QFormLayout()
        
        self.url_input = QLineEdit()
        self.url_input.textChanged.connect(self.update_rest_url)
        self.rest_url_input = QLineEdit()
        self.rest_url_input.setReadOnly(True)
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        
        form_layout.addRow("GeoServer URL:", self.url_input)
        form_layout.addRow("Generated REST URL:", self.rest_url_input)
        form_layout.addRow("Username:", self.username_input)
        form_layout.addRow("Password:", self.password_input)
        
        conn_layout.addLayout(form_layout)
        
        # Connection buttons (horizontal)
        conn_btn_row = QHBoxLayout()
        self.load_settings_btn = QPushButton("Load Settings from INI File")
        self.load_settings_btn.clicked.connect(self.load_settings)
        conn_btn_row.addWidget(self.load_settings_btn)
        
        self.save_settings_btn = QPushButton("Save Settings to INI File")
        self.save_settings_btn.clicked.connect(self.save_settings_to_file)
        conn_btn_row.addWidget(self.save_settings_btn)
        
        self.fetch_info_btn = QPushButton("Retrieve GeoServer Information")
        self.fetch_info_btn.clicked.connect(self.retrieve_geoserver_info)
        conn_btn_row.addWidget(self.fetch_info_btn)
        
        conn_layout.addLayout(conn_btn_row)
        conn_group.setLayout(conn_layout)
        
        # Hide/show connection controls when collapsed
        def toggle_conn_group(checked):
            form_layout_visible = checked
            for i in range(form_layout.rowCount()):
                label_item = form_layout.itemAt(i, QFormLayout.LabelRole)
                field_item = form_layout.itemAt(i, QFormLayout.FieldRole)
                if label_item and label_item.widget():
                    label_item.widget().setVisible(form_layout_visible)
                if field_item and field_item.widget():
                    field_item.widget().setVisible(form_layout_visible)
            # Also hide buttons
            for i in range(conn_btn_row.count()):
                widget = conn_btn_row.itemAt(i).widget()
                if widget:
                    widget.setVisible(form_layout_visible)
        
        conn_group.toggled.connect(toggle_conn_group)
        toggle_conn_group(True)  # Ensure visible at start
        
        # Set maximum height to reduce vertical space (cut by a third)
        conn_group.setMaximumHeight(180)
        
        conn_others_layout.addWidget(conn_group, 1)
        
        # ===== OTHERS GROUP =====
        others_group = QGroupBox("Others")
        others_layout = QVBoxLayout()
        
        self.reset_cache_btn = QPushButton("Reset All Caches")
        self.reset_cache_btn.clicked.connect(self.reset_all_caches)
        others_layout.addWidget(self.reset_cache_btn)
        
        self.postgis_credentials_btn = QPushButton("PostGIS Credentials")
        self.postgis_credentials_btn.clicked.connect(self.open_postgis_credentials_dialog)
        others_layout.addWidget(self.postgis_credentials_btn)
        
        self.documentation_btn = QPushButton("Documentation")
        self.documentation_btn.clicked.connect(self.show_documentation)
        others_layout.addWidget(self.documentation_btn)
        
        others_layout.addStretch()
        others_group.setLayout(others_layout)
        
        # Set maximum height to match Connection Settings group (cut by a third)
        others_group.setMaximumHeight(180)
        
        conn_others_layout.addWidget(others_group, 1)
        
        main_layout.addLayout(conn_others_layout)
    
    def _setup_workspaces_section(self, top_splitter):
        """Setup workspaces section with list and buttons."""
        global os
        ws_group = QGroupBox("Workspaces")
        ws_layout = QVBoxLayout()
        
        # Import droppable workspaces list
        try:
            from .droppable_workspaces_list import DroppableWorkspacesList
        except ImportError:
            # Fallback for direct execution
            import sys
            import os
            sys.path.insert(0, os.path.dirname(__file__))
            from droppable_workspaces_list import DroppableWorkspacesList
        
        self.workspaces_list = DroppableWorkspacesList()
        # Resize the workspace list box to 1.3x its default width
        self.workspaces_list.setMinimumWidth(int(self.workspaces_list.sizeHintForColumn(0) * 1.3) if self.workspaces_list.sizeHintForColumn(0) > 0 else 200)
        self.workspaces_list.itemSelectionChanged.connect(self.load_workspace_layers)
        self.workspaces_list.itemSelectionChanged.connect(self.load_stores)
        # Enable context menu on workspaces list
        self.workspaces_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.workspaces_list.customContextMenuRequested.connect(self._show_workspace_context_menu)
        # Connect drop signal for drag and drop copy/move
        self.workspaces_list.layers_dropped.connect(self._on_layers_dropped)
        ws_layout.addWidget(self.workspaces_list)
        
        # Create and delete workspace buttons
        ws_btn_row = QHBoxLayout()
        self.create_workspace_btn = QPushButton("Create New Workspace")
        self.create_workspace_btn.clicked.connect(self.create_workspace)
        ws_btn_row.addWidget(self.create_workspace_btn)
        
        self.delete_workspace_btn = QPushButton()
        self.delete_workspace_btn.setObjectName("delete_workspace_btn")
        self.delete_workspace_btn.setIcon(QIcon(os.path.join(self.plugin_dir, 'icons/bin.svg')))
        self.delete_workspace_btn.setIconSize(QSize(16, 16))
        self.delete_workspace_btn.setFixedSize(16, 16)
        self.delete_workspace_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.delete_workspace_btn.setToolTip("Delete Workspace")
        self.delete_workspace_btn.setStyleSheet("""
            QPushButton {
                background-color: #e6e6e6;
                border: 1px solid #aaa;
                border-radius: 4px;
                padding: 3px;
            }
            QPushButton:hover {
                background-color: #d0eaff;
                border: 1px solid #3399ff;
            }
        """)
        self.delete_workspace_btn.clicked.connect(self.delete_workspace)
        ws_btn_row.addWidget(self.delete_workspace_btn)
        ws_btn_row.addStretch(1)
        
        ws_layout.addLayout(ws_btn_row)
        ws_group.setLayout(ws_layout)
        top_splitter.addWidget(ws_group)
    
    def _setup_layers_and_styles_sections(self, top_splitter):
        """
        Setup workspace layers, styles, and datastores sections.
        
        This method has been refactored into the LayersAndStylesSetupManager class
        for better code organization and maintainability.
        
        Args:
            top_splitter: QSplitter widget to add the sections to
        """
        return self.layers_styles_setup.setup_layers_and_styles_sections(top_splitter)
    
    def _setup_qgis_layers_section_in_panel(self, qgis_layout):
        """
        Setup QGIS layers section in a panel layout at the bottom.
        
        Args:
            qgis_layout: QVBoxLayout to add widgets to
        """
        # Create main group box for QGIS layers
        qgis_group = QGroupBox("Select All Layers")
        qgis_inner_layout = QVBoxLayout()
        qgis_inner_layout.setContentsMargins(8, 8, 8, 8)
        qgis_inner_layout.setSpacing(6)
        
        # Top row: Select All and settings checkboxes on same line
        top_row = QHBoxLayout()
        
        # Select all checkbox for QGIS layers
        self.select_all_qgis_layers_checkbox = QCheckBox("Select All Layers")
        self.select_all_qgis_layers_checkbox.stateChanged.connect(self.toggle_qgis_layer_selection)
        top_row.addWidget(self.select_all_qgis_layers_checkbox)
        
        # Overwrite existing layers checkbox
        self.auto_overwrite_checkbox = QCheckBox("Overwrite existing layers")
        self.auto_overwrite_checkbox.setToolTip("When checked, existing layers will be automatically overwritten without asking")
        self.auto_overwrite_checkbox.setChecked(True)
        top_row.addWidget(self.auto_overwrite_checkbox)
        
        # Overwrite SLD checkbox
        self.overwrite_sld_checkbox = QCheckBox("Overwrite SLD")
        self.overwrite_sld_checkbox.setToolTip("When checked, existing SLD styles will be overwritten")
        self.overwrite_sld_checkbox.setChecked(True)
        top_row.addWidget(self.overwrite_sld_checkbox)
        
        # Expand All checkbox
        self.expand_groups_checkbox = QCheckBox("Expand All")
        self.expand_groups_checkbox.setToolTip("Expand all layer groups")
        self.expand_groups_checkbox.stateChanged.connect(self._on_expand_groups_toggled)
        top_row.addWidget(self.expand_groups_checkbox)
        
        # Collapse All checkbox
        self.collapse_groups_checkbox = QCheckBox("Collapse All")
        self.collapse_groups_checkbox.setToolTip("Collapse all layer groups")
        self.collapse_groups_checkbox.stateChanged.connect(self._on_collapse_groups_toggled)
        top_row.addWidget(self.collapse_groups_checkbox)
        
        top_row.addStretch()
        qgis_inner_layout.addLayout(top_row)
        
        # QGIS layers tree widget
        self.qgis_layers_tree = QTreeWidget()
        self.qgis_layers_tree.setHeaderHidden(False)
        self.qgis_layers_tree.setColumnCount(5)
        self.qgis_layers_tree.setHeaderLabels(["Name", "Format", "Extents", "Show SLD", "Upload SLD"])
        self.qgis_layers_tree.setAlternatingRowColors(True)
        self.qgis_layers_tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.qgis_layers_tree.setItemsExpandable(True)
        self.qgis_layers_tree.setRootIsDecorated(True)
        
        # Override mouse press event to prevent unwanted selection clearing
        original_mousePressEvent = self.qgis_layers_tree.mousePressEvent
        def custom_mousePressEvent(event):
            item = self.qgis_layers_tree.itemAt(event.pos())
            if item is None:
                # Clicked on empty area - completely ignore the event
                event.ignore()
                return
            # Store current selection before processing
            selected_items = self.qgis_layers_tree.selectedItems()
            # Process the event normally
            original_mousePressEvent(event)
            # If selection was cleared unexpectedly, restore it
            if not self.qgis_layers_tree.selectedItems() and selected_items:
                for item in selected_items:
                    item.setSelected(True)
        self.qgis_layers_tree.mousePressEvent = custom_mousePressEvent
        
        # Also override clearSelection to prevent unwanted clearing
        original_clearSelection = self.qgis_layers_tree.clearSelection
        def custom_clearSelection():
            # Only allow clearing if it's from our own code or user action
            import traceback
            stack = traceback.extract_stack()
            # Allow clearing from toggle_qgis_layer_selection or our own methods
            allowed_methods = ['toggle_qgis_layer_selection', '_update_select_all_qgis_layers_checkbox', 
                             '_on_button_clicked_preserve_selection']
            for frame in stack:
                if any(method in frame.name for method in allowed_methods):
                    original_clearSelection()
                    return
            # Otherwise, ignore the clear selection call
            pass
        self.qgis_layers_tree.clearSelection = custom_clearSelection
        
        self.qgis_layers_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.qgis_layers_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.qgis_layers_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.qgis_layers_tree.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.qgis_layers_tree.header().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.qgis_layers_tree.header().setStretchLastSection(False)
        qgis_inner_layout.addWidget(self.qgis_layers_tree)
        
        # SLD status label
        self.sld_status_label = QLabel("")
        self.sld_status_label.setStyleSheet("color: blue; font-size: 10pt;")
        self.sld_status_label.setVisible(False)
        qgis_inner_layout.addWidget(self.sld_status_label)
        
        # Load button and preview button in horizontal layout
        load_preview_layout = QHBoxLayout()
        
        self.load_layer_btn = QPushButton("Load Selected QGIS Layers to GeoServer")
        self.load_layer_btn.clicked.connect(self.load_qgis_layer)
        load_preview_layout.addWidget(self.load_layer_btn)
        
        self.preview_btn = QPushButton("Preview Layers in OpenLayers")
        self.preview_btn.clicked.connect(self._show_preview_dialog)
        load_preview_layout.addWidget(self.preview_btn)
        
        load_preview_layout.addStretch()
        
        # Stop Upload button (hidden by default, shown during uploads)
        self.stop_upload_btn = QPushButton("🛑 Stop Upload")
        self.stop_upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10pt;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #e53935;
            }
            QPushButton:pressed {
                background-color: #c62828;
            }
        """)
        self.stop_upload_btn.setVisible(False)
        self.stop_upload_btn.clicked.connect(self._on_stop_upload_clicked)
        load_preview_layout.addWidget(self.stop_upload_btn)
        
        # Show Log Dialog checkbox
        self.show_log_dialog_checkbox = QCheckBox("Show Log Dialog")
        self.show_log_dialog_checkbox.setToolTip("When checked, upload log dialog will appear during upload. When unchecked, logging is disabled for faster uploads.")
        self.show_log_dialog_checkbox.setChecked(False)
        load_preview_layout.addWidget(self.show_log_dialog_checkbox)
        
        qgis_inner_layout.addLayout(load_preview_layout)
        
        self.load_progress_bar = QProgressBar()
        self.load_progress_bar.setVisible(False)
        self.load_progress_bar.setAlignment(Qt.AlignCenter)
        self.load_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #0078d4;
                border-radius: 4px;
                background: #f0f0f0;
                height: 28px;
                color: #333333;
                font-weight: bold;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background: #0078d4;
                border-radius: 3px;
            }
        """)
        self._progress_bar = self.load_progress_bar
        qgis_inner_layout.addWidget(self.load_progress_bar)
        
        qgis_group.setLayout(qgis_inner_layout)
        qgis_layout.addWidget(qgis_group)
        
        # Populate the layers
        self.populate_qgis_layers()

    
    def _setup_layout_and_signals(self):
        """Setup main layout, splitters, and connect QGIS project signals."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create main vertical splitter for draggable divider between top and bottom
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.setChildrenCollapsible(False)
        main_splitter.setHandleWidth(8)
        
        # Top section: Connection and workspaces/styles
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(12, 12, 12, 12)
        top_layout.setSpacing(12)
        
        # Setup connection section at top
        self._setup_connection_section(top_layout)
        
        # Horizontal splitter with workspaces and styles
        h_splitter = QSplitter(Qt.Horizontal)
        h_splitter.setChildrenCollapsible(False)
        h_splitter.setHandleWidth(8)
        
        # Setup workspaces and styles sections
        self._setup_workspaces_section(h_splitter)
        self.layers_styles_setup.setup_layers_and_styles_sections(h_splitter)
        
        # Set initial sizes for the horizontal splitter
        h_splitter.setSizes([300, 400])
        
        top_layout.addWidget(h_splitter)
        main_splitter.addWidget(top_widget)
        
        # Bottom section: QGIS layers (left panel at bottom)
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(12, 12, 12, 12)
        bottom_layout.setSpacing(0)
        self._setup_qgis_layers_section_in_panel(bottom_layout)
        main_splitter.addWidget(bottom_widget)
        
        # Set initial sizes for the main vertical splitter (55:45 ratio - lower panel 45%)
        main_splitter.setSizes([550, 450])
        
        main_layout.addWidget(main_splitter)
        self.setLayout(main_layout)
        
        # Connect QGIS project signals
        QgsProject.instance().layersAdded.connect(self.populate_qgis_layers)
        QgsProject.instance().layersWillBeRemoved.connect(self.populate_qgis_layers)
        QgsProject.instance().layersRemoved.connect(self.populate_qgis_layers)
        QgsProject.instance().layerTreeRoot().customLayerOrderChanged.connect(self.sync_layer_order)
        QgsProject.instance().layerTreeRoot().visibilityChanged.connect(self._on_layer_visibility_changed)
        
        # Note: We don't connect to addedChildren/removedChildren/nameChanged on root
        # because layer name changes are handled by individual layer signals
        # and group name changes are handled by group node signals
        # Full refresh is only triggered by layersAdded/layersRemoved for major changes
        
        # Connect layer tree selection signals for QGIS sync (but disable unwanted selection clearing)
        self.qgis_layers_tree.itemSelectionChanged.connect(self._on_plugin_layer_selection_changed)
        
        # Connect tree item changed signal for group checkbox handling
        self.qgis_layers_tree.itemChanged.connect(self._on_qgis_tree_item_changed)
    
    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        # Initialize resources first
        try:
            from . import resources
        except ImportError:
            # If resources.py doesn't exist, try to import it directly
            try:
                import resources
            except ImportError:
                pass  # Resources might not be needed
        
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        
        # Create the action and add it to the default locations (Plugins menu and toolbar)
        # Use toggle_panel as callback for checkable action
        action = self.add_action(
            icon_path,
            text=self.tr(u'Q2G - QGIS to GeoServer Connector'),
            callback=self.toggle_panel,
            parent=self.iface.mainWindow())
        
        # Make the action checkable
        action.setCheckable(True)
        self.action = action
            
        # Add to 'Q2GTools' toolbar as requested
        try:
            # Check if "Q2GTools" toolbar already exists
            self.q2gtools_toolbar = self.iface.mainWindow().findChild(QToolBar, "Q2GTools")
            if self.q2gtools_toolbar is None:
                self.q2gtools_toolbar = self.iface.addToolBar("Q2GTools")
                self.q2gtools_toolbar.setObjectName("Q2GTools")
            
            # Add the action to the Q2GTools toolbar
            self.q2gtools_toolbar.addAction(action)
        except Exception as e:
            print(f"Error adding to Q2GTools toolbar: {e}")
        
        # will be set False in run()
        self.first_start = True
        
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        # Make sure self.actions exists to prevent errors
        if hasattr(self, 'actions'):
            for action in self.actions:
                # Remove from web menu
                try:
                    self.iface.removePluginWebMenu(
                        self.tr(u'&Q2G - QGIS to GeoServer Connector'),
                        action)
                except Exception:
                    pass
                
                # Remove from Q2GTools toolbar if it exists
                if hasattr(self, 'q2gtools_toolbar') and self.q2gtools_toolbar:
                    try:
                        self.q2gtools_toolbar.removeAction(action)
                    except Exception:
                        pass
        
        # Clean up module references to prevent KeyError during unloading
        try:
            import sys
            # Remove any references to this plugin's modules from sys.modules
            for module_name in list(sys.modules.keys()):
                if module_name.startswith('geoserverconnector'):
                    try:
                        del sys.modules[module_name]
                    except KeyError:
                        pass
        except Exception:
            pass
            
    def toggle_panel(self, checked):
        """Toggle the visibility of the dialog based on the checked state."""
        if checked:
            self.run()
        else:
            self.hide()
            
    def run(self):
        """Run method that performs all the real work"""
        # Show first load dialog if needed
        self._show_first_load_dialog_if_needed()
        
        # Show the dialog non-modally to allow toggling
        self.show()
        self.raise_()
        self.activateWindow()
        # Removed exec_() to allow main window interaction and toggling
    
    def __init__(self, iface):
        """
        Initialize the GeoServer Layer Loader dialog.
        
        :param iface: A QGIS interface instance.
        :type iface: QgsInterface
        
        This method has been refactored into smaller, focused helper methods:
        - _setup_window_and_styling(): Window properties and stylesheet
        - _setup_connection_section(): GeoServer connection UI
        - _setup_workspaces_section(): Workspaces list and buttons
        - _setup_layers_and_styles_sections(): Layers, styles, and datastores UI
        - _setup_qgis_layers_section(): QGIS project layers UI
        - _setup_layout_and_signals(): Layout setup and signal connections
        """
        super().__init__(iface.mainWindow())
        print(f"--- Q2G QGIS Plugin Version: {__version__} ---")
        
        # Initialize core properties
        self.iface = iface
        self.plugin_dir = Path(__file__).resolve().parent
        self.connected_layers = set()
        self.is_updating_style = False
        self.layer_to_item_map = {}
        self.layer_name_mapping = {}
        self.group_to_item_map = {}  # Map group names to tree items
        self.group_node_to_item_map = {}  # Map group node IDs to (item, path) for rename tracking
        self.user_initiated_checkbox_change = False
        
        # Initialize actions list for toolbar functionality
        self.actions = []
        self.menu = self.tr(u'&Q2G - QGIS to GeoServer Connector')
        
        # Initialize managers
        self.log_tracker = UploadLogTracker()
        self.postgis_credentials = PostGISCredentialsManager()
        self.postgis_publisher = PostGISRegistrationPublisher(self)
        self.qgis_layer_loader = QGISLayerLoader(self)
        self.sld_style_uploader = SLDStyleUploader(self)
        self.task_verifier = TaskVerificationPublisher(self)
        self.sld_converter = SLDConverter(self)
        self.layers_populator = QGISLayersPopulator(self)
        self.style_sld_manager = StyleSLDWindowManager(self)
        self.workspace_refresher = WorkspaceContentRefresher(self)
        self.wms_bbox_retriever = WMSLayerBBoxRetriever(self)
        self.cache_reset_manager = CacheResetManager(self)
        self.progress_bar_updater = ProgressBarUpdater(self)
        self.style_deletion_manager = StyleDeletionManager(self)
        self.layer_styles_loader = LayerStylesLoader(self)
        self.datastore_deletion_manager = DatastoreDeletionManager(self)
        self.layer_deletion_manager = LayerDeletionManager(self)
        self.workspace_deletion_manager = WorkspaceDeletionManager(self)
        self.workspace_creation_manager = WorkspaceCreationManager(self)
        self.sld_window_manager = SLDWindowManager(self)
        self.geopackage_publisher = GeoPackageDatastorePublisher(self)
        self.geoserver_layers_refresher = GeoServerLayersListRefresher(self)
        self.duplicate_styles_cleaner = DuplicateGlobalStylesCleaner(self)
        self.temp_datastores_cleaner = TemporaryDatastoresCleaner(self)
        self.duplicate_datastores_cleaner = DuplicateDatastoresCleaner(self)
        self.all_stores_cleaner = AllDuplicateStoresForLayerCleaner(self)
        self.existing_layer_deleter = ExistingLayerDeleter(self)
        self.overwrite_dialog = OverwriteExistingLayerDialog(self)
        self.layers_styles_setup = LayersAndStylesSetupManager(self)
        self.geopackage_layer_checker = GeoPackageLayerExistenceChecker(self)
        self.layer_existence_checker = LayerExistenceChecker(self)
        self.geopackage_name_extractor = GeoPackageDatastoreNameExtractor(self)
        self.geopackage_native_uploader = GeoPackageNativeUploader(self)
        self.cors_manager = CORSManager(self)
        
        # Setup UI components
        self._setup_window_and_styling()
        self._setup_layout_and_signals()
        
        # Initialize data and settings
        self.populate_qgis_layers()
        self.load_settings_on_startup()
        self._initialize_postgis_credentials()
        
        # First load dialog is disabled to prevent automatic opening
        # self._show_first_load_dialog_if_needed()
    
    def _initialize_postgis_credentials(self):
        """Initialize PostGIS credentials setup."""
        try:
            self.check_postgis_credentials_setup()
        except Exception as e:
            import traceback
            self.log_message(f"Error in PostGIS credentials setup: {str(e)}", level=Qgis.Warning)
            self.log_message(traceback.format_exc(), level=Qgis.Warning)

    def _show_first_load_dialog_if_needed(self):
        """Show first load dialog on plugin startup if not disabled by user."""
        try:
            plugin_dir = str(self.plugin_dir)
            if should_show_first_load_dialog(plugin_dir):
                dialog = FirstLoadDialog(self, plugin_dir)
                dialog.exec_()
        except Exception as e:
            # Silently fail - don't interrupt plugin startup
            print(f"DEBUG: Error showing first load dialog: {str(e)}")

    def load_settings_on_startup(self):
        """Load GeoServer credentials and URL from an INI file on startup if it exists."""
        try:
            # Get the plugin directory safely
            if '__file__' in globals():
                plugin_dir = os.path.dirname(os.path.abspath(__file__))
            else:
                # Fallback: use the current working directory or home directory
                plugin_dir = os.getcwd() if os.getcwd() else os.path.expanduser("~")
            
            settings_file = os.path.join(plugin_dir, "geoserver_settings.ini")
            
            print(f"DEBUG: Looking for settings file at: {settings_file}")
            
            if os.path.exists(settings_file):
                print(f"DEBUG: Settings file found, loading...")
                config = configparser.ConfigParser()
                config.read(settings_file)
                
                # Load settings
                url = config.get("GeoServer", "url", fallback="")
                username = config.get("GeoServer", "username", fallback="")
                password = config.get("GeoServer", "password", fallback="")
                
                print(f"DEBUG: Loaded URL: {url}")
                print(f"DEBUG: Loaded Username: {username}")
                print(f"DEBUG: Loaded Password: {'*' * len(password) if password else '(empty)'}")
                
                self.url_input.setText(url)
                self.username_input.setText(username)
                self.password_input.setText(password)
                
                # Load UI preferences
                show_log = config.get("UI", "show_log_dialog", fallback="false").lower() == "true"
                self.show_log_dialog_checkbox.setChecked(show_log)
                
                # Automatically retrieve GeoServer info if we have credentials
                if url and username:
                    print(f"DEBUG: Auto-retrieving GeoServer info...")
                    self.retrieve_geoserver_info()
            else:
                print(f"DEBUG: Settings file not found at {settings_file}")
        except Exception as e:
            # Log the error but don't interrupt startup
            print(f"DEBUG: Failed to load settings on startup: {str(e)}")
            import traceback
            traceback.print_exc()

    def get_base_url(self):
        """Get the base GeoServer URL, stripping off /rest/imports and any trailing slash."""
        url = self.url_input.text().strip()
        if '/rest/imports' in url:
            url = url.split('/rest/imports')[0]
        
        # Ensure no trailing slash for clean URL joining
        if url.endswith('/'):
            url = url[:-1]
            
        return url

    def update_rest_url(self):
        """Automatically generate the REST URL based on the GeoServer URL."""
        base_url = self.get_base_url()
        if base_url:
            if not base_url.endswith('/'):
                base_url += '/'
            rest_url = base_url + "rest/imports"
            self.rest_url_input.setText(rest_url)
        else:
            self.rest_url_input.clear()

    def load_settings(self):
        """Load GeoServer credentials and URL from an INI file."""
        # Use the script directory for the default open location
        script_dir = os.path.dirname(os.path.realpath(sys.argv[0])) if hasattr(sys, 'argv') and sys.argv else os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.path.expanduser("~")
        default_path = os.path.join(script_dir, "geoserver_settings.ini")
        
        settings_path, _ = QFileDialog.getOpenFileName(self, "Open INI File", default_path, "INI Files (*.ini)")
        if not settings_path:
            return

        config = configparser.ConfigParser()
        config.read(settings_path)

        # Load settings
        self.url_input.setText(config.get("GeoServer", "url", fallback=""))
        self.username_input.setText(config.get("GeoServer", "username", fallback=""))
        self.password_input.setText(config.get("GeoServer", "password", fallback=""))
        
        # Initialize styles view mode
        
    def save_settings_to_file(self):
        """Save GeoServer credentials and URL to an INI file."""
        # Use the plugin directory (where main.py is located) for the default save location
        try:
            script_dir = str(Path(__file__).resolve().parent)
        except (NameError, KeyError):
            # Fallback: use the directory of the import_manager module
            import import_manager
            script_dir = str(Path(import_manager.__file__).resolve().parent)
        default_path = os.path.join(script_dir, "geoserver_settings.ini")
        
        # Open file dialog to choose where to save the file
        settings_path, _ = QFileDialog.getSaveFileName(self, "Save INI File", default_path, "INI Files (*.ini)")
        
        if not settings_path:
            return

        # Create config object
        config = configparser.ConfigParser()
        
        # Add settings to config
        config["GeoServer"] = {
            "url": self.url_input.text().strip(),
            "username": self.username_input.text().strip(),
            "password": self.password_input.text().strip()
        }
        
        # Write config to file
        try:
            with open(settings_path, "w") as configfile:
                config.write(configfile)
            QMessageBox.information(self, "Success", "Settings saved successfully to:\n{}".format(settings_path))
        except Exception as e:
            QMessageBox.critical(self, "Error", "Failed to save settings: {}".format(str(e)))

    def check_postgis_credentials_setup(self):
        """Check if postgis.ini exists and has credentials, create if needed."""
        # Check if directory exists
        config_dir = os.path.dirname(self.postgis_credentials.config_path)
        
        # Ensure postgis.ini file exists
        if not os.path.exists(self.postgis_credentials.config_path):
            # Create empty postgis.ini file
            try:
                # Create directory if it doesn't exist
                os.makedirs(config_dir, exist_ok=True)
                
                with open(self.postgis_credentials.config_path, "w") as configfile:
                    configfile.write("# PostGIS Database Credentials\n")
                    configfile.write("# This file stores database connection credentials for the Q2G QGIS Plugin\n")
                    configfile.write("# Each section represents a unique database connection\n\n")
                    
                self.log_message(f"✓ Created new postgis.ini file")
            except Exception as e:
                import traceback
                self.log_message(f"✗ Failed to create postgis.ini file: {str(e)}", level=Qgis.Warning)
                return
        
        # Check if postgis.ini is empty (no saved connections)
        try:
            connections = self.postgis_credentials.list_saved_connections()
            if not connections:
                self.log_message("ℹ No PostGIS credentials found. You may need to set up PostGIS credentials for database connections.")
            else:
                self.log_message(f"✓ Found {len(connections)} saved PostGIS connection(s).")
        except Exception as e:
            self.log_message(f"✗ Error checking saved connections: {str(e)}", level=Qgis.Warning)

    def save_postgis_credentials(self, pg_params):
        """Save PostGIS credentials to a postgis.ini file using the credentials manager."""
        self.postgis_credentials.save_credentials(pg_params, log_callback=self.log_message)

    def toggle_select_all_styles(self, state):
        """Toggle selection of all styles in the list."""
        if state == Qt.Checked:
            # Select all items
            for i in range(self.layer_styles_list.count()):
                item = self.layer_styles_list.item(i)
                item.setSelected(True)
            self.log_message(f"Selected all {self.layer_styles_list.count()} styles")
        else:
            # Deselect all items
            self.layer_styles_list.clearSelection()
            self.log_message("Deselected all styles")

    def retrieve_geoserver_info(self):
        """Fetch and display GeoServer workspaces, datastores, layers, and styles."""
        url = self.get_base_url()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not all([url, username, password]):
            QMessageBox.warning(self, "Input Error", "Please provide the URL, username, and password.")
            return

        # 1. Disconnect signals to prevent premature UI updates
        try:
            self.workspaces_list.itemSelectionChanged.disconnect(self.load_workspace_layers)
            self.workspaces_list.itemSelectionChanged.disconnect(self.load_stores)
        except TypeError:
            pass  # It's okay if signals were not connected

        try:
            # 2. Clear UI elements before populating
            self.workspaces_list.clear()
            self.workspace_layers_list.clear()
            self.datastores_list.clear()
            self.layer_styles_list.clear()

            # 3. Fetch and populate workspaces
            response = requests.get(f"{url}/rest/workspaces.xml", auth=(username, password), headers={"Accept": "application/xml"})
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

            root = ET.fromstring(response.content)
            workspaces = [name.text for name in root.findall('.//name')]
            sorted_workspaces = sorted(workspaces, key=str.lower)
            
            # Remember the currently selected workspace before clearing
            current_workspace = None
            if self.workspaces_list.count() > 0:
                current_item = self.workspaces_list.currentItem()
                if current_item:
                    current_workspace = current_item.text()
            
            self.workspaces_list.addItems(sorted_workspaces)
            self.log_message(f"Successfully retrieved {len(sorted_workspaces)} workspaces.")

            # 4. Fetch and populate all styles
            self.load_layer_styles()

            # 5. Select workspace - keep current selection if it still exists, otherwise select first
            if self.workspaces_list.count() > 0:
                if current_workspace and current_workspace in sorted_workspaces:
                    # Restore the previously selected workspace
                    for i in range(self.workspaces_list.count()):
                        if self.workspaces_list.item(i).text() == current_workspace:
                            self.workspaces_list.setCurrentRow(i)
                            self.log_message(f"Restored workspace selection: {current_workspace}")
                            break
                else:
                    # No previous selection or it doesn't exist anymore, select first
                    self.workspaces_list.setCurrentRow(0)
                    self.log_message("Automatically selected the first workspace.")
                
                # Explicitly call these to ensure UI updates reliably
                self.load_stores()
                self.load_workspace_layers()

        except requests.exceptions.RequestException as e:
            # Provide user-friendly error message
            error_msg = self._get_user_friendly_error_message(str(e))
            QMessageBox.critical(self, "Connection Error", error_msg)
            self.log_message(f"GeoServer connection error: {e}")
        except Exception as e:
            # General catch-all for other errors (e.g., XML parsing, UI updates)
            QMessageBox.critical(self, "Processing Error", f"An unexpected error occurred: {e}")
            self.log_message(f"An unexpected error in retrieve_geoserver_info: {e}")
        finally:
            # 6. ALWAYS reconnect signals
            try:
                self.workspaces_list.itemSelectionChanged.connect(self.load_workspace_layers)
                self.workspaces_list.itemSelectionChanged.connect(self.load_stores)
            except TypeError:
                pass  # It's okay if they are already connected

    def load_stores(self):
        """Load and display all datastores and coveragestores for the selected workspace."""
        self.datastores_list.clear()
        url = self.get_base_url()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        workspace_item = self.workspaces_list.currentItem()
        if not workspace_item:
            self.datastores_list.addItem("No workspace selected")
            return
        workspace = workspace_item.text()

        stores_found = False
        # Fetch datastores
        try:
            response = requests.get(f"{url}/rest/workspaces/{workspace}/datastores.json", auth=(username, password))
            if response.status_code == 200:
                datastores = response.json().get('dataStores', {}).get('dataStore', [])
                # Handle case where single datastore is returned as dict instead of list
                if isinstance(datastores, dict):
                    datastores = [datastores]
                for store in datastores:
                    self.datastores_list.addItem(f"(DS) {store['name']}")
                    stores_found = True
        except Exception as e:
            self.log_message(f"Could not fetch datastores: {e}", level=Qgis.Warning)

        # Fetch coveragestores
        try:
            response = requests.get(f"{url}/rest/workspaces/{workspace}/coveragestores.json", auth=(username, password))
            if response.status_code == 200:
                cs_data = response.json().get('coverageStores', {})
                # Handle case where cs_data is a string or invalid type
                if isinstance(cs_data, dict):
                    coveragestores = cs_data.get('coverageStore', [])
                    # Handle case where single coverage store is returned as dict instead of list
                    if isinstance(coveragestores, dict):
                        coveragestores = [coveragestores]
                    elif not isinstance(coveragestores, list):
                        coveragestores = []
                    
                    for store in coveragestores:
                        if isinstance(store, dict) and 'name' in store:
                            self.datastores_list.addItem(f"(CS) {store['name']}")
                            stores_found = True
        except Exception as e:
            self.log_message(f"Could not fetch coveragestores: {e}", level=Qgis.Warning)

        if not stores_found:
            self.datastores_list.addItem("No stores available")

    def _get_user_friendly_error_message(self, error_str):
        """Convert technical error messages into user-friendly messages."""
        error_lower = error_str.lower()
        
        # Connection refused or refused to connect
        if "connection refused" in error_lower or "refused" in error_lower:
            url = self.get_base_url()
            return (
                f"❌ Cannot connect to GeoServer\n\n"
                f"It seems that your GeoServer instance is not running.\n\n"
                f"Please check:\n"
                f"• Is GeoServer running at {url}?\n"
                f"• Is the URL correct?\n"
                f"• Check your network connection\n"
                f"• Start GeoServer and try again"
            )
        
        # Connection timeout
        elif "timeout" in error_lower or "timed out" in error_lower:
            return (
                f"⏱️ Connection Timeout\n\n"
                f"GeoServer is taking too long to respond.\n\n"
                f"Please check:\n"
                f"• Is GeoServer running and responsive?\n"
                f"• Is your network connection stable?\n"
                f"• Try again in a moment"
            )
        
        # No connection could be made
        elif "no connection could be made" in error_lower or "actively refused" in error_lower:
            url = self.get_base_url()
            return (
                f"❌ GeoServer Connection Failed\n\n"
                f"It seems that your GeoServer instance is not running.\n\n"
                f"Please check:\n"
                f"• Is GeoServer running at {url}?\n"
                f"• Is the URL correct?\n"
                f"• Check your firewall settings\n"
                f"• Start GeoServer and try again"
            )
        
        # Invalid URL or hostname
        elif "name or service not known" in error_lower or "nodename nor servname provided" in error_lower:
            url = self.get_base_url()
            return (
                f"🔗 Invalid GeoServer URL\n\n"
                f"Cannot resolve the hostname: {url}\n\n"
                f"Please check:\n"
                f"• Is the URL correct?\n"
                f"• Check your internet connection\n"
                f"• Verify the hostname is reachable"
            )
        
        # Authentication error
        elif "401" in error_lower or "unauthorized" in error_lower:
            return (
                f"🔐 Authentication Failed\n\n"
                f"Invalid username or password.\n\n"
                f"Please check:\n"
                f"• Is your username correct?\n"
                f"• Is your password correct?\n"
                f"• Try again with correct credentials"
            )
        
        # Default message with technical details
        else:
            return (
                f"❌ GeoServer Connection Error\n\n"
                f"It seems that your GeoServer instance is not running or is unreachable.\n\n"
                f"Technical details:\n{error_str}\n\n"
                f"Please check:\n"
                f"• Is GeoServer running?\n"
                f"• Is the URL correct?\n"
                f"• Check your network connection"
            )

    def load_workspace_layers(self):
        """Load and display layers for the selected workspace."""
        url = self.get_base_url()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        workspace_item = self.workspaces_list.currentItem()
        
        self.workspace_layers_list.clear()
        self.workspace_layers_filter.clear()  # Clear filter when loading new workspace

        if not workspace_item:
            return

        workspace = workspace_item.text()

        try:
            response = requests.get(
                f"{url}/rest/workspaces/{workspace}/layers.xml",
                auth=(username, password),
                headers={"Accept": "application/xml"}
            )
            if response.status_code == 200:
                try:
                    root = ET.fromstring(response.content)
                    layers = root.findall('.//layer/name')
                    
                    if not layers:
                        self.workspace_layers_list.addItem("No layers available in this workspace")
                        self.all_workspace_layers = []
                    else:
                        # Store all layers for filtering
                        self.all_workspace_layers = [layer.text for layer in layers]
                        for layer_name in self.all_workspace_layers:
                            self.workspace_layers_list.addItem(layer_name)
                except ET.ParseError:
                    self.workspace_layers_list.addItem("Failed to parse layer list")
                    self.all_workspace_layers = []
            else:
                QMessageBox.warning(self, "Error", f"Failed to fetch workspace layers. Status: {response.status_code}\n{response.text}")
        except requests.exceptions.RequestException as e:
            error_msg = self._get_user_friendly_error_message(str(e))
            QMessageBox.critical(self, "Connection Error", error_msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred while fetching layers: {e}")
    
    def filter_workspace_layers(self):
        """
        Filter workspace layers based on wildcard pattern.
        Updates workspace layers, datastores, and styles lists.
        """
        try:
            from wildcard_filter import WildcardFilter
        except ImportError:
            try:
                from .wildcard_filter import WildcardFilter
            except ImportError:
                # Fallback: import directly if already in path
                import wildcard_filter as wf
                WildcardFilter = wf.WildcardFilter
        
        pattern = self.workspace_layers_filter.text().strip()
        
        # Filter layers based on pattern
        filtered_layers = WildcardFilter.filter_items(self.all_workspace_layers, pattern)
        
        # Update workspace layers list
        self.workspace_layers_list.clear()
        if filtered_layers:
            for layer_name in filtered_layers:
                self.workspace_layers_list.addItem(layer_name)
        else:
            self.workspace_layers_list.addItem("No layers match the filter")
        
        # Update datastores and styles based on filtered layers
        self._update_datastores_for_filtered_layers(filtered_layers)
        self._update_styles_for_filtered_layers(filtered_layers)
    
    def _update_datastores_for_filtered_layers(self, filtered_layers):
        """
        Update datastores list to show only datastores that contain the filtered layers.
        
        Args:
            filtered_layers: List of filtered layer names
        """
        if not filtered_layers:
            self.datastores_list.clear()
            self.datastores_list.addItem("No datastores for filtered layers")
            return
        
        url = self.get_base_url()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        workspace_item = self.workspaces_list.currentItem()
        
        if not workspace_item:
            return
        
        workspace = workspace_item.text()
        
        # Collect all datastores that actually contain the filtered layers
        relevant_datastores = set()
        
        try:
            # For each filtered layer, find which datastore it belongs to
            for layer_name in filtered_layers:
                # Check layer details to find its datastore
                layer_url = f"{url}/rest/workspaces/{workspace}/layers/{layer_name}.json"
                layer_response = requests.get(layer_url, auth=(username, password))
                
                if layer_response.status_code == 200:
                    layer_data = layer_response.json()
                    layer_obj = layer_data.get('layer', {})
                    resource = layer_obj.get('resource', {})
                    
                    if isinstance(resource, dict):
                        # Extract datastore name from resource href
                        resource_href = resource.get('href', '')
                        if 'datastores/' in resource_href:
                            # Extract datastore name: .../datastores/storename/...
                            store_name = resource_href.split('datastores/')[1].split('/')[0]
                            relevant_datastores.add(f"(DS) {store_name}")
                        elif 'coveragestores/' in resource_href:
                            # Extract coverage store name: .../coveragestores/storename/...
                            store_name = resource_href.split('coveragestores/')[1].split('/')[0]
                            relevant_datastores.add(f"(CS) {store_name}")
                            
        except Exception as e:
            self.log_message(f"Could not determine datastores for filtered layers: {e}", level=Qgis.Warning)
        
        # Update datastores list
        self.datastores_list.clear()
        if relevant_datastores:
            for store in sorted(relevant_datastores):
                self.datastores_list.addItem(store)
        else:
            self.datastores_list.addItem("No datastores for filtered layers")
    
    def _update_styles_for_filtered_layers(self, filtered_layers):
        """
        Update styles list to show only styles actually used by the filtered layers.
        
        Args:
            filtered_layers: List of filtered layer names
        """
        if not filtered_layers:
            self.layer_styles_list.clear()
            self.layer_styles_list.addItem("No styles for filtered layers")
            return
        
        url = self.get_base_url()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        workspace_item = self.workspaces_list.currentItem()
        
        if not workspace_item:
            return
        
        workspace = workspace_item.text()
        
        # Collect styles actually used by filtered layers
        relevant_styles = set()
        
        try:
            # For each filtered layer, get its associated styles
            for layer_name in filtered_layers:
                layer_url = f"{url}/rest/workspaces/{workspace}/layers/{layer_name}.json"
                layer_response = requests.get(layer_url, auth=(username, password))
                
                if layer_response.status_code == 200:
                    layer_data = layer_response.json()
                    layer_obj = layer_data.get('layer', {})
                    
                    # Get default style
                    default_style = layer_obj.get('defaultStyle', {})
                    if isinstance(default_style, dict):
                        style_name = default_style.get('name')
                        if style_name:
                            relevant_styles.add(style_name)
                    
                    # Get additional styles
                    styles = layer_obj.get('styles', {})
                    if isinstance(styles, dict):
                        style_list = styles.get('style', [])
                        if isinstance(style_list, dict):
                            style_list = [style_list]
                        elif not isinstance(style_list, list):
                            style_list = []
                        
                        for style in style_list:
                            if isinstance(style, dict):
                                style_name = style.get('name')
                                if style_name:
                                    relevant_styles.add(style_name)
                                    
        except Exception as e:
            self.log_message(f"Could not determine styles for filtered layers: {e}", level=Qgis.Warning)
        
        # Update styles list
        self.layer_styles_list.clear()
        if relevant_styles:
            for style in sorted(relevant_styles):
                self.layer_styles_list.addItem(style)
        else:
            self.layer_styles_list.addItem("No styles for filtered layers")

    def populate_qgis_layers(self):
        """
        Populate the QGIS layers tree widget with layers from the current project.
        
        This method has been refactored into the QGISLayersPopulator class
        for better code organization and maintainability.
        """
        return self.layers_populator.populate_qgis_layers()

    def _on_upload_sld_clicked(self, layer):
        """Handle custom SLD upload for a specific layer."""
        if self.is_updating_style:
            return  # Do not trigger on simple style change
        # Get GeoServer connection details
        url = self.get_base_url()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        # Get current workspace
        workspace_item = self.workspaces_list.currentItem()
        if not workspace_item:
            QMessageBox.warning(self, "Warning", "Please select a workspace first.")
            return
        workspace = workspace_item.text()
        
        layer_name = self._sanitize_layer_name(layer.name())

        # Clear log
        self.log_tracker.clear()
        
        # Check if log dialog should be shown (respect the "show log dialog" checkbox setting)
        show_log_dialog = self.show_log_dialog_checkbox.isChecked()
        self.log_tracker.show_log_dialog = show_log_dialog
        
        # Show live log window only if checkbox is checked
        if show_log_dialog:
            live_log = self.log_tracker.show_live_log_window(self, "Upload SLD Progress")
        
        # Use the original method with notification system
        self.log_message(f"Uploading SLD for layer '{layer_name}' via button click...")
        self._upload_layer_sld_to_geoserver(layer, layer_name, workspace, url, username, password)

    def _upload_layer_sld_to_geoserver(self, layer, layer_name, workspace, url, username, password):
        """Export current layer's SLD and upload to GeoServer, always overwriting existing styles."""
        try:
            self.log_message(f"Exporting and uploading SLD for layer '{layer_name}' to GeoServer...")

            # Export the current layer's SLD using centralized method
            sld_content = self.sld_window_manager._extract_sld_content(layer)
            if not sld_content:
                self.log_message(f"No SLD content available for layer '{layer_name}'. Cannot upload.", level=Qgis.Warning)
                QMessageBox.warning(self, "Warning", f"Could not export SLD for layer '{layer_name}'.")
                return

            # Use SLD 1.1 directly without conversion
            if 'xmlns:se=' in sld_content or 'se:' in sld_content:
                self.log_message(f"Using SLD 1.1.0 (SE format) directly for layer '{layer_name}'")
            else:
                self.log_message(f"Using SLD format directly for layer '{layer_name}'")

            style_name = layer_name
            
            # SLD 1.1 upload requires proper content type - GeoServer supports both SLD 1.0 and 1.1
            headers = {
                'Content-Type': 'application/vnd.ogc.sld+xml',
            }

            # Check if style exists first to respect overwrite setting
            check_style_url = f"{url}/rest/workspaces/{workspace}/styles/{style_name}.json"
            check_response = requests.get(check_style_url, auth=(username, password))
            
            if check_response.status_code == 200:
                # Style exists - for manual uploads, always overwrite (show message)
                self.log_message(f"🔄 Overwriting existing style '{style_name}' in workspace '{workspace}' (manual upload)...")
                style_url = f"{url}/rest/workspaces/{workspace}/styles/{style_name}.sld?raw=true"
                response = requests.put(
                    style_url,
                    auth=(username, password),
                    headers=headers,
                    data=sld_content.encode('utf-8')
                )
            else:
                # Style doesn't exist - use POST to create
                self.log_message(f"📝 Creating new style '{style_name}' in workspace '{workspace}'...")
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
                    self.log_message(f"Failed to create style '{style_name}' with POST. Status: {post_response.status_code}\n{post_response.text}", level=Qgis.Critical)
                    self._show_sld_status(f"SLD for {layer_name} upload failed")
                    return
                
                self.log_message(f"✓ Style '{style_name}' created successfully with POST")
                response = post_response
            
            if response.status_code not in [200, 201]:
                self.log_message(f"Failed to upload style '{style_name}'. Status: {response.status_code}\\n{response.text}", level=Qgis.Critical)
                self._show_sld_status(f"SLD for {layer_name} upload failed")
                return

            self.log_message(f"✓ Style '{style_name}' uploaded successfully to GeoServer.")
            self._show_sld_status(f"SLD for {layer_name} uploaded successfully")

        except Exception as e:
            self.log_message(f"An error occurred during SLD upload for '{layer_name}': {e}", level=Qgis.Critical)
            self._show_sld_status(f"SLD for {layer_name} upload failed")
        finally:
            # Disable upload controls when SLD upload is complete
            if hasattr(self, 'log_tracker') and self.log_tracker.live_window:
                self.log_tracker.live_window.disable_upload_controls()

    def _show_sld_status(self, message):
        """Show a fading status message next to the Overwrite SLD checkbox."""
        self.sld_status_label.setText(message)
        self.sld_status_label.setVisible(True)
        
        # Set color based on message type
        if "failed" in message.lower():
            base_color = "255, 0, 0"  # Red for errors
            self.sld_status_label.setStyleSheet("color: red; font-size: 10pt;")
        else:
            base_color = "0, 0, 255"  # Blue for success
            self.sld_status_label.setStyleSheet("color: blue; font-size: 10pt;")
        
        # Create gradual fade out effect using opacity over 3 seconds
        fade_steps = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0]
        for i, opacity in enumerate(fade_steps):
            QTimer.singleShot(5000 + (i * 300), 
                lambda op=opacity, color=base_color: self.sld_status_label.setStyleSheet(f"color: rgba({color}, {op}); font-size: 10pt;"))

    def _on_show_extents_clicked(self, layer):
        """Handle click on the extents button for a layer."""
        dialog = LayerExtentsDialog(layer, self)
        dialog.show()
        
        # Keep a reference to prevent garbage collection
        if not hasattr(self, '_extents_dialogs'):
            self._extents_dialogs = []
        self._extents_dialogs.append(dialog)
        
        # Clean up references when dialog is closed
        dialog.finished.connect(lambda: self._cleanup_extents_dialog(dialog))

    def _cleanup_extents_dialog(self, dialog):
        """Remove closed dialog from the references list."""
        if hasattr(self, '_extents_dialogs'):
            if dialog in self._extents_dialogs:
                self._extents_dialogs.remove(dialog)

    def _on_show_sld_clicked(self, layer):
        """Handle click on the SLD button for a layer."""
        sld_content = self.sld_window_manager._extract_sld_content(layer)
        if sld_content:
            dialog = SLDViewerDialog(sld_content, f"SLD - {layer.name()}", self)
            dialog.show()
            
            # Keep a reference to prevent garbage collection
            if not hasattr(self, '_sld_dialogs'):
                self._sld_dialogs = []
            self._sld_dialogs.append(dialog)
            
            # Clean up references when dialog is closed
            dialog.finished.connect(lambda: self._cleanup_sld_dialog(dialog))
        else:
            QMessageBox.warning(self, "SLD Export Failed", 
                              f"Failed to export SLD for layer '{layer.name()}'. Check the log for details.")

    def _cleanup_sld_dialog(self, dialog):
        """Remove closed dialog from the references list."""
        if hasattr(self, '_sld_dialogs'):
            if dialog in self._sld_dialogs:
                self._sld_dialogs.remove(dialog)

    def get_selected_qgis_layers(self):
        """Returns a list of checked QGIS layers from the tree, including those in groups."""
        selected_layers = []
        root = self.qgis_layers_tree.invisibleRootItem()
        child_count = root.childCount()
        
        self.log_message(f"DEBUG: Checking {child_count} items in QGIS layers tree")
        
        for i in range(child_count):
            item = root.child(i)
            self._collect_checked_layers_recursive(item, selected_layers)
        
        self.log_message(f"get_selected_qgis_layers found {len(selected_layers)} checked layers.")
        return selected_layers

    def _collect_checked_layers_recursive(self, item, selected_layers):
        """
        Recursively collect checked layers from tree items, including those in groups.
        
        Args:
            item: Current tree widget item
            selected_layers: List to accumulate selected layers
        """
        if not item:
            return
        
        check_state = item.checkState(0)
        layer_name = item.text(0)
        
        # Check if this is a layer (has layer data)
        layer = item.data(0, Qt.UserRole)
        is_group = item.data(0, Qt.UserRole + 3)  # True if marked as group
        
        if layer and isinstance(layer, (QgsVectorLayer, QgsRasterLayer)):
            # This is a layer item
            if check_state == Qt.Checked:
                selected_layers.append(layer)
                self.log_message(f"DEBUG: Added layer '{layer_name}' to selection")
        elif is_group:
            # This is a group - recursively check its children
            self.log_message(f"DEBUG: Checking group '{layer_name}' with {item.childCount()} children")
            for i in range(item.childCount()):
                child = item.child(i)
                self._collect_checked_layers_recursive(child, selected_layers)

    def _convert_se_to_sld_1_0(self, se_sld_content, layer_name=''):
        """
        Convert SLD 1.1.0 with SE namespace to SLD 1.0.0 format for GeoServer compatibility.
        
        This method has been refactored into the SLDConverter class
        for better code organization and maintainability.
        
        Args:
            se_sld_content: SLD content string with SE namespace
            layer_name: Optional layer name for logging
            
        Returns:
            str: Converted SLD 1.0.0 content string
        """
        return self.sld_converter.convert_se_to_sld_1_0(se_sld_content, layer_name)

    def _sanitize_layer_name(self, name):
        """Sanitize a layer name to be safe as a GeoServer resource/store name."""
        try:
            safe = re.sub(r"[^A-Za-z0-9_]+", "_", name or "")
            # GeoServer can handle names starting with digits, so no need to add underscore prefix
            # Avoid empty names
            if not safe:
                safe = f"layer_{uuid.uuid4().hex[:8]}"
            return safe
        except Exception:
            return f"layer_{uuid.uuid4().hex[:8]}"

    def _get_shapefile_info(self, layer):
        """
        Extract shapefile info from a layer's source URI.
        Handles formats like: "folder/path|layername=shapefile_name"
        Returns: (folder_path, shapefile_name, shapefile_base_name)
        """
        try:
            source_uri = layer.dataProvider().dataSourceUri() if layer.dataProvider() else layer.source()
            
            # Parse the source URI to extract folder and layer name
            if '|' in source_uri:
                parts = source_uri.split('|')
                containing_folder = parts[0]
                
                # Parse the layername parameter
                if len(parts) > 1:
                    layer_name_part = parts[1]
                    if '=' in layer_name_part:
                        key, value = layer_name_part.split('=', 1)
                        shapefile_name = value  # e.g., "polbnda_mys"
                        
                        if containing_folder and shapefile_name:
                            return (containing_folder, shapefile_name, shapefile_name)
            
            # Fallback: return the first part (folder or file path)
            return (source_uri.split('|')[0].split('?')[0], None, None)
        except Exception as e:
            self.log_message(f"Error extracting shapefile info: {e}")
            return (layer.source().split('|')[0].split('?')[0], None, None)

    def _detect_file_type_and_validate(self, layer):
        """
        Detect file type and validate source file exists.
        
        Returns:
            tuple: (source_path, file_type) where file_type is one of:
                   'shapefile', 'geojson', 'kml', 'csv', 'geotiff', 'geopackage'
                   or (None, None) if invalid
        """
        try:
            # Extract the file path from layer source
            source_path = layer.source().split('|')[0].split('?')[0]
            
            # Validate file exists
            if not os.path.exists(source_path):
                self.log_message(f"❌ File not found: {source_path}", level=Qgis.Critical)
                return None, None
            
            # Determine file type
            is_shapefile = source_path.lower().endswith('.shp') or (os.path.isdir(source_path) and '|layername=' in layer.source())
            is_geopackage = source_path.lower().endswith('.gpkg')
            is_sqlite = source_path.lower().endswith('.sqlite')
            is_geotiff = source_path.lower().endswith(('.tif', '.tiff'))
            is_geojson = source_path.lower().endswith(('.geojson', '.json'))
            is_kml = source_path.lower().endswith('.kml')
            is_csv = source_path.lower().endswith('.csv')
            
            # Log file type detection for debugging
            self.log_message(f"DEBUG: File type detection - Shapefile: {is_shapefile}, GeoPackage: {is_geopackage}, GeoTIFF: {is_geotiff}, GeoJSON: {is_geojson}, KML: {is_kml}, CSV: {is_csv}")
            self.log_message(f"DEBUG: Source path: {source_path}")
            
            # Note: SQLite, GeoJSON, and other unsupported formats are now handled
            # by the fallback upload method (_upload_unsupported_as_geopackage)
            # which converts them to GeoPackage format before uploading
            if is_shapefile:
                file_type = 'shapefile'
            elif is_kml:
                file_type = 'kml'
            elif is_csv:
                file_type = 'csv'
            elif is_geotiff:
                file_type = 'geotiff'
            elif is_geopackage:
                file_type = 'geopackage'
            else:
                # SQLite, GeoJSON and other formats are NOT supported by importer
                # They should be handled by the fallback GeoPackage conversion method
                self.log_message(f"❌ Unsupported format for importer: {source_path}", level=Qgis.Critical)
                return None, None
            
            return source_path, file_type
            
        except Exception as e:
            self.log_message(f"❌ Error in file type detection: {e}", level=Qgis.Critical)
            return None, None
    
    def _create_import_job(self, workspace, url, username, password):
        """
        Create a new import job in GeoServer.
        
        Returns:
            str: Import ID if successful, None if failed
        """
        try:
            import_payload = {
                "import": {
                    "targetWorkspace": {
                        "workspace": {
                            "name": workspace
                        }
                    }
                }
            }
            
            import_resp = requests.post(
                f"{url}/rest/imports",
                auth=(username, password),
                json=import_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if import_resp.status_code not in [200, 201]:
                self.log_message(f"❌ Failed to create import job: {import_resp.status_code}", level=Qgis.Critical)
                return None
            
            import_id = import_resp.json().get('import', {}).get('id')
            if import_id is None:
                self.log_message(f"❌ No import ID returned", level=Qgis.Critical)
                return None
            
            self.log_message(f"✓ Created import job: {import_id}")
            return import_id
            
        except Exception as e:
            self.log_message(f"❌ Error creating import job: {e}", level=Qgis.Critical)
            return None
    
    def _upload_geopackage_file(self, source_path, tasks_url, username, password, layer=None):
        """
        Upload GeoPackage file using multipart/form-data with layer specification.
        
        Args:
            source_path: Path to the GeoPackage file
            tasks_url: GeoServer import tasks URL
            username: GeoServer username
            password: GeoServer password
            layer: QGIS layer object (optional, for extracting layer name)
        
        Returns:
            requests.Response: Upload response
        """
        self.log_message("DEBUG: GeoPackage detected - using Importer API with layer specification")
        self.log_message(f"DEBUG: Source path: {source_path}")
        self.log_message(f"DEBUG: File size: {os.path.getsize(source_path)} bytes")
        self.log_message(f"DEBUG: Upload URL: {tasks_url}")
        
        try:
            with open(source_path, 'rb') as file_data:
                files = {'file': (os.path.basename(source_path), file_data, 'application/octet-stream')}
                self.log_message(f"DEBUG: Uploading file: {os.path.basename(source_path)}")
                
                # Extract layer name from source if layer object is provided
                data = None
                if layer:
                    layer_source = layer.source()
                    if '|layername=' in layer_source:
                        layer_name_param = layer_source.split('|layername=')[1].split('|')[0]
                        self.log_message(f"DEBUG: GeoPackage layer name: {layer_name_param}")
                        data = {'configure': 'first', 'layer': layer_name_param}
                        self.log_message(f"DEBUG: Upload data parameters: {data}")
                    else:
                        self.log_message("DEBUG: No layername parameter found in source, uploading without layer specification")
                
                # Upload with or without layer specification
                if data:
                    response = requests.post(tasks_url, auth=(username, password), files=files, data=data, timeout=300)
                else:
                    response = requests.post(tasks_url, auth=(username, password), files=files, timeout=300)
                
                self.log_message(f"DEBUG: Upload response status: {response.status_code}")
                self.log_message(f"DEBUG: Upload response headers: {dict(response.headers)}")
                
                return response
        except Exception as e:
            self.log_message(f"DEBUG: Upload exception: {e}")
            raise
    
    def _upload_shapefile(self, layer, source_path, layer_name, tasks_url, username, password):
        """
        Upload Shapefile by zipping companion files.
        
        Returns:
            requests.Response: Upload response
        """
        # Get shapefile info
        folder_path, shapefile_name, _ = self._get_shapefile_info(layer) if os.path.isdir(source_path) else (os.path.dirname(source_path), os.path.splitext(os.path.basename(source_path))[0], None)
        
        # Create temporary zip file
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_zip_path = temp_zip.name
        temp_zip.close()
        
        try:
            # Zip all companion files
            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg', '.qpj']:
                    file_path = os.path.join(folder_path, f"{shapefile_name}{ext}")
                    if os.path.exists(file_path):
                        zipf.write(file_path, arcname=f"{layer_name}{ext}")
            
            # Upload the zip file
            with open(temp_zip_path, 'rb') as f:
                return requests.post(tasks_url, auth=(username, password), files={'file': (f"{layer_name}.zip", f)})
        finally:
            # Clean up temporary zip file
            if os.path.exists(temp_zip_path):
                os.unlink(temp_zip_path)
    
    def _upload_geojson_file(self, source_path, tasks_url, username, password):
        """
        Upload GeoJSON file with proper MIME type.
        
        Returns:
            requests.Response: Upload response
        """
        self.log_message(f"DEBUG: Uploading GeoJSON {os.path.basename(source_path)} to {tasks_url}")
        
        with open(source_path, 'rb') as f:
            # GeoJSON needs application/json MIME type
            return requests.post(
                tasks_url, 
                files={'file': (os.path.basename(source_path), f, 'application/json')}, 
                auth=(username, password)
            )
    
    def _upload_geotiff_file(self, source_path, tasks_url, username, password):
        """
        Upload GeoTIFF file directly.
        
        Returns:
            requests.Response: Upload response
        """
        self.log_message(f"DEBUG: Uploading {os.path.basename(source_path)} to {tasks_url}")
        
        with open(source_path, 'rb') as f:
            return requests.post(tasks_url, files={'file': (os.path.basename(source_path), f)}, auth=(username, password))
    
    def _execute_import_job(self, import_id, url, username, password):
        """
        Execute the import job in GeoServer.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            execute_url = f"{url}/rest/imports/{import_id}"
            execute_resp = requests.post(execute_url, auth=(username, password))
            
            if execute_resp.status_code not in [200, 201, 204]:
                self.log_message(f"❌ Failed to execute import: {execute_resp.status_code}", level=Qgis.Critical)
                return False
            
            self.log_message(f"✓ Import executed")
            return True
            
        except Exception as e:
            self.log_message(f"❌ Error executing import job: {e}", level=Qgis.Critical)
            return False
    
    def _verify_and_publish_tasks(self, layer, import_id, workspace, url, username, password):
        """
        Verify import tasks and publish layers.
        
        This method has been refactored into the TaskVerificationPublisher class
        for better code organization and maintainability.
        
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
        return self.task_verifier.verify_and_publish_tasks(layer, import_id, workspace, url, username, password)
    
    def _upload_layer_importer(self, layer, layer_name, workspace, url, username, password):
        """
        Upload files using GeoServer Importer API.
        
        Supports: Shapefiles, GeoJSON, KML, CSV, GeoTIFF, GeoPackage
        """
        try:
            # Check if this is a GeoPackage - if so, use native REST API method
            source_path = layer.source().split('|')[0].split('?')[0]
            if source_path.lower().endswith('.gpkg'):
                self.log_message("🔄 GeoPackage detected - using native REST API method")
                return self.geopackage_native_uploader.upload_geopackage(layer, workspace, url, username, password)
            
            # For non-GeoPackage files, use the current modular approach
            # Step 1: Detect file type and validate
            source_path, file_type = self._detect_file_type_and_validate(layer)
            if source_path is None:
                return False
            
            # Step 2: Create import job
            import_id = self._create_import_job(workspace, url, username, password)
            if import_id is None:
                return False
            
            # Step 3: Upload file based on type
            tasks_url = f"{url}/rest/imports/{import_id}/tasks"
            
            if file_type == 'shapefile':
                upload_resp = self._upload_shapefile(layer, source_path, layer_name, tasks_url, username, password)
            elif file_type in ['kml', 'csv', 'geotiff']:
                # These formats upload as single files directly
                upload_resp = self._upload_geotiff_file(source_path, tasks_url, username, password)
            else:
                self.log_message(f"❌ Unsupported file type: {file_type}", level=Qgis.Critical)
                return False
            
            # Validate file upload
            if upload_resp.status_code not in [200, 201]:
                self.log_message(f"❌ File upload failed: {upload_resp.status_code}", level=Qgis.Critical)
                self.log_message(f"DEBUG: Upload response headers: {dict(upload_resp.headers)}")
                self.log_message(f"DEBUG: Upload response body: {upload_resp.text}")
                self.log_message(f"DEBUG: Request URL was: {upload_resp.url}")
                return False
            
            self.log_message(f"✓ File uploaded")
            
            # Step 4: Execute import job
            if not self._execute_import_job(import_id, url, username, password):
                return False
            
            # Step 5: Verify and publish tasks
            return self._verify_and_publish_tasks(layer, import_id, workspace, url, username, password)
            
        except Exception as e:
            self.log_message(f"❌ Error in importer upload: {e}", level=Qgis.Critical)
            self.log_message(traceback.format_exc())
            return False

    
    def _upload_unsupported_as_geopackage(self, layer, layer_name, workspace, url, username, password):
        """
        Fallback method: Convert unsupported formats to GeoPackage and upload.
        
        This handles formats like SQLite, GeoJSON, KML, CSV that are not directly supported by GeoServer.
        The layer is exported to GeoPackage format and then uploaded via the native GeoPackage datastore method.
        
        GeoPackage advantages over Shapefile:
        - Single file (no companion files needed)
        - Built-in compression (smaller file size)
        - Better metadata support
        - No zipping required
        
        Args:
            layer: QGIS layer object
            layer_name: Sanitized layer name
            workspace: GeoServer workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if upload succeeded, False otherwise
        """
        try:
            from qgis.core import QgsVectorFileWriter, QgsVectorLayer
            import tempfile
            
            self.log_message(f"🔄 Converting unsupported format to GeoPackage: '{layer.name()}'")
            
            # Only handle vector layers
            if not isinstance(layer, QgsVectorLayer):
                self.log_message(f"❌ Unsupported format for layer '{layer.name()}' - only vector layers can be converted", level=Qgis.Critical)
                return False
            
            # Create temporary directory for geopackage
            temp_dir = tempfile.mkdtemp(prefix='geoserver_')
            geopackage_path = os.path.join(temp_dir, f"{layer_name}.gpkg")
            
            self.log_message(f"📝 Exporting to temporary GeoPackage: {geopackage_path}")
            
            # Export layer to GeoPackage
            error = QgsVectorFileWriter.writeAsVectorFormat(
                layer,
                geopackage_path,
                'utf-8',
                layer.crs(),
                'GPKG'
            )
            
            if error[0] != QgsVectorFileWriter.NoError:
                self.log_message(f"❌ Failed to convert to GeoPackage: {error[1]}", level=Qgis.Critical)
                return False
            
            self.log_message(f"✓ GeoPackage created successfully")
            
            # Now upload the geopackage using the native GeoPackage datastore method
            # Create a temporary layer object pointing to the geopackage
            temp_layer = QgsVectorLayer(f"{geopackage_path}|layername={layer_name}", layer_name, 'ogr')
            if not temp_layer.isValid():
                self.log_message(f"❌ Failed to load converted GeoPackage", level=Qgis.Critical)
                return False
            
            # Copy CRS from original layer
            temp_layer.setCrs(layer.crs())
            
            # Upload the geopackage using native datastore method
            self.log_message(f"📤 Uploading converted GeoPackage to GeoServer")
            success = self._register_geopackage_datastore_and_publish(temp_layer, layer_name, workspace, url, username, password)
            
            # Clean up temporary files
            try:
                import shutil
                shutil.rmtree(temp_dir)
                self.log_message(f"🗑️ Cleaned up temporary files")
            except Exception as e:
                self.log_message(f"⚠️ Could not clean up temporary files: {e}")
            
            return success
            
        except Exception as e:
            self.log_message(f"❌ Error converting to GeoPackage: {e}", level=Qgis.Critical)
            self.log_message(traceback.format_exc())
            return False


    def _upload_layer_importer_main18(self, layer, workspace, url, username, password):
        """
        Working GeoPackage upload method from main18.py.
        This method handles GeoPackage uploads that actually work.
        """
        try:
            source_path = layer.source().split('|')[0].split('?')[0]
            layer_name = self._sanitize_layer_name(layer.name())
            self.log_message(f"DEBUG IMPORTER: Starting upload for layer '{layer.name()}' using Importer API to workspace '{workspace}'")
            self.log_message(f"DEBUG IMPORTER: Source path: {source_path}")
            self.log_message(f"DEBUG IMPORTER: File exists: {os.path.exists(source_path)}")

            if not os.path.exists(source_path):
                self.log_message(f"ERROR IMPORTER: File not found at source path: {source_path}", level=Qgis.Critical)
                return False

            # Step 1: Create an import job without specifying target store (let importer handle it)
            import_payload = {
                "import": {
                    "targetWorkspace": {
                        "workspace": {
                            "name": workspace
                        }
                    }
                }
            }
            create_import_url = f"{url}/rest/imports"
            self.log_message(f"Step 1: Creating import job at {create_import_url}")
            import_response = requests.post(
                create_import_url,
                auth=(username, password),
                json=import_payload,
                headers={"Content-Type": "application/json"}
            )

            self.log_message(f"Import creation response: {import_response.status_code}")
            if import_response.status_code not in [200, 201]:
                self.log_message(f"Failed to create import job: {import_response.text}", level=Qgis.Critical)
                return False

            try:
                import_data = import_response.json()
                import_id = import_data.get('import', {}).get('id')
                if not import_id:
                    self.log_message("Failed to get import ID from response", level=Qgis.Critical)
                    self.log_message(f"Response content: {import_response.text}")
                    return False
            except Exception as e:
                self.log_message(f"Failed to parse import response JSON: {e}", level=Qgis.Critical)
                self.log_message(f"Response content: {import_response.text}")
                return False

            self.log_message(f"Created import job with ID: {import_id}")

            # Step 2: Upload the file to the import job's task list
            tasks_url = f"{url}/rest/imports/{import_id}/tasks"
            self.log_message(f"Step 2: Uploading file to {tasks_url}")
            
            # For GeoPackage files, we need to specify the layer name
            layer_source = layer.source()
            self.log_message(f"DEBUG IMPORTER: Full layer source: {layer_source}")
            if source_path.lower().endswith('.gpkg') and '|layername=' in layer_source:
                # Extract the RAW layer name from the source (DO NOT SANITIZE!)
                # This must match exactly what's in the GeoPackage file
                layer_name_param = layer_source.split('|layername=')[1].split('|')[0]
                self.log_message(f"DEBUG IMPORTER: RAW GeoPackage layer name: '{layer_name_param}'")
                
                # Upload with layer specification using RAW layer name
                with open(source_path, 'rb') as file_data:
                    files = {'file': (os.path.basename(source_path), file_data)}
                    data = {'configure': 'first', 'layer': layer_name_param}
                    self.log_message(f"DEBUG IMPORTER: Upload data: {data}")
                    upload_response = requests.post(tasks_url, auth=(username, password), files=files, data=data)
            else:
                # Standard file upload for other formats
                with open(source_path, 'rb') as file_data:
                    files = {'file': (os.path.basename(source_path), file_data)}
                    upload_response = requests.post(tasks_url, auth=(username, password), files=files)

            self.log_message(f"File upload response: {upload_response.status_code}")
            if upload_response.status_code not in [200, 201]:
                self.log_message(f"Failed to upload file: {upload_response.text}", level=Qgis.Critical)
                self.log_message(f"DEBUG: Upload request URL: {upload_response.url}")
                self.log_message(f"DEBUG: Upload request headers: {dict(upload_response.request.headers)}")
                return False

            self.log_message("File uploaded successfully to the import task.")

            # Step 3: Execute the import
            execute_url = f"{url}/rest/imports/{import_id}"
            self.log_message(f"Step 3: Executing import at {execute_url}")
            execute_response = requests.post(execute_url, auth=(username, password))

            self.log_message(f"Import execution response: {execute_response.status_code}")
            if execute_response.status_code not in [200, 201, 202, 204]:
                self.log_message(f"Failed to execute import: {execute_response.text}", level=Qgis.Critical)
                return False

            # Step 4: Verify and publish layers from the import
            self.log_message(f"Step 4: Verifying and publishing layers from import {import_id}")
            try:
                # Get the import status and tasks
                import_status_response = requests.get(f"{url}/rest/imports/{import_id}", auth=(username, password))
                if import_status_response.status_code == 200:
                    import_status = import_status_response.json()
                    self.log_message(f"Import status: {import_status.get('import', {}).get('state', 'UNKNOWN')}")
                
                # Get tasks to find what was imported
                tasks_response = requests.get(tasks_url, auth=(username, password))
                if tasks_response.status_code == 200:
                    tasks_data = tasks_response.json()
                    layers_published = 0
                    
                    for task in tasks_data.get('tasks', []):
                        task_state = task.get('state', 'UNKNOWN')
                        self.log_message(f"Task state: {task_state}")
                        
                        if task_state == 'READY':
                            # Task is ready but not executed - execute it
                            task_id = task.get('id')
                            if task_id:
                                task_execute_url = f"{url}/rest/imports/{import_id}/tasks/{task_id}"
                                task_response = requests.post(task_execute_url, auth=(username, password))
                                if task_response.status_code in [200, 201, 202]:
                                    self.log_message(f"Successfully executed task {task_id}")
                                    layers_published += 1
                                else:
                                    self.log_message(f"Failed to execute task {task_id}: {task_response.text}")
                        elif task_state == 'COMPLETE':
                            layers_published += 1
                            self.log_message(f"Task completed successfully")
                        elif task_state == 'NO_CRS':
                            # Handle missing CRS by setting a default one
                            task_id = task.get('id')
                            if task_id:
                                # Get the layer's CRS from QGIS
                                layer_crs = layer.crs()
                                if layer_crs.isValid():
                                    crs_code = layer_crs.authid()  # e.g., "EPSG:4326"
                                    self.log_message(f"Setting CRS for task {task_id}: {crs_code}")
                                    
                                    # Update the task with CRS information
                                    task_update_url = f"{url}/rest/imports/{import_id}/tasks/{task_id}"
                                    crs_payload = {
                                        "task": {
                                            "layer": {
                                                "srs": crs_code
                                            }
                                        }
                                    }
                                    crs_response = requests.put(task_update_url, auth=(username, password), 
                                                              json=crs_payload, headers={"Content-Type": "application/json"})
                                    
                                    if crs_response.status_code in [200, 201]:
                                        # Now execute the task
                                        task_execute_url = f"{url}/rest/imports/{import_id}/tasks/{task_id}"
                                        task_response = requests.post(task_execute_url, auth=(username, password))
                                        if task_response.status_code in [200, 201, 202]:
                                            self.log_message(f"Successfully executed task {task_id} with CRS {crs_code}")
                                            layers_published += 1
                                        else:
                                            self.log_message(f"Failed to execute task {task_id} after CRS update: {task_response.text}")
                                    else:
                                        self.log_message(f"Failed to update CRS for task {task_id}: {crs_response.text}")
                                else:
                                    self.log_message(f"Layer has invalid CRS, cannot set CRS for task {task_id}")
                        elif task_state == 'ERROR':
                            error_msg = task.get('errorMessage', 'Unknown error')
                            self.log_message(f"Task error: {error_msg}", level=Qgis.Critical)
                    
                    if layers_published > 0:
                        self.log_message(f"Successfully published {layers_published} layer(s) from '{layer.name()}'")
                        return True
                    else:
                        self.log_message(f"No layers were published from '{layer.name()}'", level=Qgis.Warning)
                        return False
                else:
                    self.log_message(f"Failed to get import tasks: {tasks_response.status_code}")
                    return False
                    
            except Exception as e:
                self.log_message(f"Error during layer verification: {str(e)}")
                # Still return True if the import executed successfully, even if verification failed
                return True

            self.log_message(f"Successfully imported layer '{layer.name()}' using Importer API")
            return True
            
        except Exception as e:
            self.log_message(f"Exception during Importer upload: {str(e)}")
            import traceback
            self.log_message(f"Traceback: {traceback.format_exc()}")
            return False


    def load_qgis_layer(self):
        """
        Exports a QGIS layer using its native format when possible, and uploads it to GeoServer.
        
        This method has been refactored into the QGISLayerLoader class
        for better code organization and maintainability.
        """
        return self.qgis_layer_loader.load_qgis_layer()
    
    def _ask_overwrite_existing_layer(self, layer_name, current_layer, total_layers):
        """
        Ask user what to do with existing layer and provide batch options.
        
        This method has been refactored into the OverwriteExistingLayerDialog class
        for better code organization and maintainability.
        
        Args:
            layer_name: Name of the existing layer
            current_layer: Current layer number being processed
            total_layers: Total number of layers to process
            
        Returns:
            str: User decision ('overwrite', 'overwrite_all', 'skip', 'skip_all')
        """
        return self.overwrite_dialog.ask_overwrite_existing_layer(layer_name, current_layer, total_layers)
    
    def _delete_existing_layer(self, layer_name, workspace, url, username, password):
        """
        Delete an existing layer and its associated datastore/coveragestore from GeoServer.
        
        This method has been refactored into the ExistingLayerDeleter class
        for better code organization and maintainability.
        
        Args:
            layer_name: Name of the layer to delete
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if at least one layer was deleted, False otherwise
        """
        return self.existing_layer_deleter.delete_existing_layer(layer_name, workspace, url, username, password)


    def _cleanup_all_duplicate_stores_for_layer(self, layer_name, workspace, url, username, password):
        """
        Delete ALL duplicate datastores and coveragestores for a layer BEFORE upload.
        
        This method has been refactored into the AllDuplicateStoresForLayerCleaner class
        for better code organization and maintainability.
        
        Args:
            layer_name: Name of the layer to clean up stores for
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        return self.all_stores_cleaner.cleanup_all_duplicate_stores_for_layer(layer_name, workspace, url, username, password)
    
    def _cleanup_duplicate_datastores(self, layer_name, workspace, url, username, password):
        """
        Delete duplicate datastores (vector stores) created by importer.
        
        This method has been refactored into the DuplicateDatastoresCleaner class
        for better code organization and maintainability.
        
        Args:
            layer_name: Name of the layer to check for duplicates
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        return self.duplicate_datastores_cleaner.cleanup_duplicate_datastores(layer_name, workspace, url, username, password)

    def _layer_exists_in_workspace(self, layer_name, workspace, url, username, password):
        """
        Check if a layer already exists in the specified workspace.
        
        This method has been refactored to use the shared LayerExistenceChecker class
        to eliminate duplicate layer checking logic.
        
        Args:
            layer_name: Name of the layer to check
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if layer exists at workspace or PostGIS datastore level, False otherwise
        """
        return self.layer_existence_checker.layer_exists_in_workspace(layer_name, workspace, url, username, password)
    
    def _get_geopackage_datastore_name(self, layer_source):
        """
        Extract GeoPackage datastore name from layer source.
        
        This method has been refactored into the GeoPackageDatastoreNameExtractor class
        for better code organization and maintainability.
        
        Args:
            layer_source: Source URI of the GeoPackage layer
            
        Returns:
            str: Sanitized datastore name or None if extraction fails
        """
        return self.geopackage_name_extractor.get_geopackage_datastore_name(layer_source)
    
    def _geopackage_layer_exists_in_datastore(self, layer_name, gpkg_datastore_name, workspace, url, username, password):
        """
        Check if a GeoPackage layer exists in its datastore (similar to PostGIS featuretype check).
        
        This method has been refactored into the GeoPackageLayerExistenceChecker class
        for better code organization and maintainability.
        
        Args:
            layer_name: Name of the layer to check
            gpkg_datastore_name: Name of the GeoPackage datastore
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if layer exists or was published, False otherwise
        """
        return self.geopackage_layer_checker.geopackage_layer_exists_in_datastore(layer_name, gpkg_datastore_name, workspace, url, username, password)
    
    def _cleanup_temporary_datastores(self, workspace, url, username, password):
        """
        Delete temporary datastores created during import process.
        
        This method has been refactored into the TemporaryDatastoresCleaner class
        for better code organization and maintainability.
        
        Args:
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        return self.temp_datastores_cleaner.cleanup_temporary_datastores(workspace, url, username, password)
    
    def _cleanup_duplicate_global_styles(self, workspace, url, username, password):
        """
        Delete duplicate global styles that should be workspace-scoped.
        
        This method has been refactored into the DuplicateGlobalStylesCleaner class
        for better code organization and maintainability.
        
        Args:
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        return self.duplicate_styles_cleaner.cleanup_duplicate_global_styles(workspace, url, username, password)
    
    def _refresh_geoserver_layers_list(self, workspace, url, username, password):
        """
        Refresh the GeoServer layers list to show newly uploaded layers.
        
        This method has been refactored into the GeoServerLayersListRefresher class
        for better code organization and maintainability.
        
        Args:
            workspace: Target workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            list: List of layers in the workspace
        """
        return self.geoserver_layers_refresher.refresh_geoserver_layers_list(workspace, url, username, password)


    def _upload_layer_native(self, layer, layer_name, workspace, url, username, password, provider_info):
        """
        Upload a layer using its native format when supported.
        
        This method routes to the appropriate upload method based on the provider info.
        All specific upload methods have been refactored into dedicated modules.
        """
        self.log_message(f"DEBUG: _upload_layer_native called for '{layer_name}', provider_info: {provider_info}")
        upload_method = provider_info.get('upload_method', 'shapefile')
        self.log_message(f"DEBUG: Upload method for '{layer_name}' is '{upload_method}'")
        
        if upload_method == 'gpkg_native':
            self.log_message(f"DEBUG: Using GeoPackage datastore registration for '{layer_name}'")
            return self._register_geopackage_datastore_and_publish(layer, layer_name, workspace, url, username, password)
        elif upload_method == 'postgis':
            self.log_message(f"DEBUG: Using PostGIS datastore registration for '{layer_name}'")
            return self._register_postgis_datastore_and_publish(layer, layer_name, workspace, url, username, password)
        elif upload_method == 'importer':
            self.log_message(f"DEBUG: Using importer upload for '{layer_name}'")
            return self._upload_layer_importer(layer, layer_name, workspace, url, username, password)
        else:
            self.log_message(f"Unsupported native upload method '{upload_method}', falling back to GeoPackage conversion")
            return self._upload_unsupported_as_geopackage(layer, layer_name, workspace, url, username, password)

    def _register_postgis_datastore_and_publish(self, layer, layer_name, workspace, url, username, password):
        """
        Register a PostGIS data store in GeoServer and publish the table as a layer.
        
        This method has been refactored into the PostGISRegistrationPublisher class
        for better code organization and maintainability.
        
        Args:
            layer: QGIS layer object
            layer_name: Sanitized layer name for GeoServer
            workspace: Target GeoServer workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if registration and publishing succeeded, False otherwise
        """
        return self.postgis_publisher.register_and_publish(layer, layer_name, workspace, url, username, password)

    def _register_geopackage_datastore_and_publish(self, layer, layer_name, workspace, url, username, password):
        """
        Upload GeoPackage file using the GeoServer Importer API.
        
        This method has been refactored into the GeoPackageDatastorePublisher class
        for better code organization and maintainability.
        
        Args:
            layer: QGIS layer object
            layer_name: Name of the layer
            workspace: Target workspace
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.geopackage_publisher.register_geopackage_datastore_and_publish(layer, layer_name, workspace, url, username, password)

    def sync_layer_order(self):
        """Synchronize the layer order in the QGIS layers tree with the project's layer tree."""
        self.populate_qgis_layers()

    def _on_layer_visibility_changed(self, node):
        """
        Handle layer visibility changes in QGIS.
        Updates the checkbox state in the layer list when a layer's or group's visibility changes.
        
        Args:
            node: The layer tree node that changed visibility
        """
        try:
            # Check if this is a layer node
            if hasattr(node, 'layer') and node.layer():
                layer = node.layer()
                
                # Find the corresponding item in the tree widget
                item = self.layer_to_item_map.get(layer.id())
                if item:
                    # Update the checkbox state based on visibility
                    is_visible = node.itemVisibilityChecked()
                    check_state = Qt.Checked if is_visible else Qt.Unchecked
                    item.setCheckState(0, check_state)
                    
                    # Log the change
                    status = "visible" if is_visible else "hidden"
                    self.log_message(f"Layer '{layer.name()}' is now {status}")
            else:
                # This is a group node
                if hasattr(node, 'name'):
                    # Find the corresponding group item using the node ID mapping
                    node_id = id(node)
                    if hasattr(self, 'group_node_to_item_map') and node_id in self.group_node_to_item_map:
                        group_item, group_path = self.group_node_to_item_map[node_id]
                        
                        # Update the checkbox state based on visibility
                        is_visible = node.itemVisibilityChecked()
                        check_state = Qt.Checked if is_visible else Qt.Unchecked
                        group_item.setCheckState(0, check_state)
                        
                        # Log the change
                        status = "visible" if is_visible else "hidden"
                        self.log_message(f"Group '{node.name()}' is now {status}")
        except Exception as e:
            # Silently ignore errors to avoid disrupting the UI
            pass

    def _on_expand_groups_toggled(self, state):
        """Handle expand all groups checkbox toggle."""
        if state == Qt.Checked:
            try:
                for i in range(self.qgis_layers_tree.topLevelItemCount()):
                    item = self.qgis_layers_tree.topLevelItem(i)
                    self._expand_item_recursive(item)
                # Uncheck collapse when expand is checked
                self.collapse_groups_checkbox.blockSignals(True)
                self.collapse_groups_checkbox.setChecked(False)
                self.collapse_groups_checkbox.blockSignals(False)
            except Exception as e:
                self.log_message(f"Error expanding groups: {e}", level=Qgis.Warning)

    def _on_collapse_groups_toggled(self, state):
        """Handle collapse all groups checkbox toggle."""
        if state == Qt.Checked:
            try:
                for i in range(self.qgis_layers_tree.topLevelItemCount()):
                    item = self.qgis_layers_tree.topLevelItem(i)
                    self._collapse_item_recursive(item)
                # Uncheck expand when collapse is checked
                self.expand_groups_checkbox.blockSignals(True)
                self.expand_groups_checkbox.setChecked(False)
                self.expand_groups_checkbox.blockSignals(False)
            except Exception as e:
                self.log_message(f"Error collapsing groups: {e}", level=Qgis.Warning)

    def _expand_item_recursive(self, item):
        """Recursively expand an item and all its children."""
        if item:
            item.setExpanded(True)
            for i in range(item.childCount()):
                child = item.child(i)
                self._expand_item_recursive(child)

    def _collapse_item_recursive(self, item):
        """Recursively collapse an item and all its children."""
        if item:
            item.setExpanded(False)
            for i in range(item.childCount()):
                child = item.child(i)
                self._collapse_item_recursive(child)

    def _on_plugin_layer_selection_changed(self):
        """
        Handle layer selection changes in the plugin's layer tree.
        Syncs group visibility to QGIS and updates the "Select All Layers" checkbox.
        """
        try:
            # Sync group visibility when a group is selected
            selected_items = self.qgis_layers_tree.selectedItems()
            for item in selected_items:
                # Check if this is a group item (no layer ID in UserRole)
                layer_id = item.data(0, Qt.UserRole)
                if not layer_id:
                    # This is a group - sync its visibility to QGIS
                    is_checked = item.checkState(0) == Qt.Checked
                    self._sync_group_visibility_to_qgis(item, is_checked)
            
            # Update "Select All Layers" checkbox based on checkbox states (not selection)
            self._update_select_all_qgis_layers_checkbox()
            
        except Exception as e:
            # Silently ignore errors to avoid disrupting the UI
            pass

    def _update_select_all_qgis_layers_checkbox(self):
        """
        Update the "Select All Layers" checkbox based on current checkbox states.
        If all selectable layers are checked, check the box. Otherwise, uncheck it.
        """
        try:
            # Count total selectable items (exclude groups) and checked items
            total_selectable = 0
            checked_count = 0
            
            root = self.qgis_layers_tree.invisibleRootItem()
            for i in range(root.childCount()):
                item = root.child(i)
                if item.data(0, Qt.UserRole):  # Has layer ID, so it's a layer not a group
                    total_selectable += 1
                    if item.checkState(0) == Qt.Checked:
                        checked_count += 1
                else:
                    # It's a group, check its children
                    for j in range(item.childCount()):
                        child = item.child(j)
                        if child.data(0, Qt.UserRole):  # Has layer ID
                            total_selectable += 1
                            if child.checkState(0) == Qt.Checked:
                                checked_count += 1
            
            # Block signals to prevent recursive calls
            self.select_all_qgis_layers_checkbox.blockSignals(True)
            
            # Update checkbox state
            if total_selectable > 0 and checked_count == total_selectable:
                self.select_all_qgis_layers_checkbox.setChecked(True)
            else:
                self.select_all_qgis_layers_checkbox.setChecked(False)
            
            # Unblock signals
            self.select_all_qgis_layers_checkbox.blockSignals(False)
            
        except Exception as e:
            # Silently ignore errors to avoid disrupting the UI
            pass

    def _on_qgis_tree_item_changed(self, item, column):
        """
        Handle checkbox state changes in the QGIS layers tree.
        When a group checkbox is changed, toggle all children.
        Also syncs changes back to QGIS layer visibility.
        
        Args:
            item: The tree widget item that changed
            column: The column that changed
        """
        try:
            # Check if this is a group item (has no layer data but is marked as group)
            is_group = item.data(0, Qt.UserRole) is None and item.data(0, Qt.UserRole + 3)
            
            if is_group:
                # This is a group - toggle all children
                new_state = item.checkState(0)
                self._set_children_check_state(item, new_state)
                self.log_message(f"Group '{item.text(0)}' checkbox changed to {new_state}")
                
                # Sync group visibility to QGIS
                self._sync_group_visibility_to_qgis(item, new_state)
            else:
                # This is a layer item - sync visibility to QGIS
                layer = item.data(0, Qt.UserRole)
                if layer and isinstance(layer, (QgsVectorLayer, QgsRasterLayer)):
                    new_state = item.checkState(0)
                    is_visible = new_state == Qt.Checked
                    
                    # Find the layer node in QGIS and update its visibility
                    root = QgsProject.instance().layerTreeRoot()
                    layer_node = root.findLayer(layer.id())
                    if layer_node:
                        layer_node.setItemVisibilityChecked(is_visible)
                        status = "visible" if is_visible else "hidden"
                        self.log_message(f"Layer '{layer.name()}' set to {status} in QGIS")
            
            # Update "Select All Layers" checkbox when any checkbox changes
            self._update_select_all_qgis_layers_checkbox()
            
        except Exception as e:
            self.log_message(f"Error handling tree item change: {e}", level=Qgis.Warning)

    def _set_children_check_state(self, parent_item, state):
        """
        Recursively set the check state of all children.
        
        Args:
            parent_item: The parent tree widget item
            state: The check state to set (Qt.Checked or Qt.Unchecked)
        """
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            if child:
                # Check if this child is also a group
                is_group = child.data(0, Qt.UserRole) is None and child.data(0, Qt.UserRole + 3)
                
                # Set the child's check state
                child.setCheckState(0, state)
                
                # If it's a group, recursively set its children
                if is_group:
                    self._set_children_check_state(child, state)

    def _sync_group_visibility_to_qgis(self, group_item, state):
        """
        Sync group visibility changes to QGIS layer tree.
        Recursively updates visibility of all layers in the group.
        
        Args:
            group_item: The group tree widget item
            state: The check state (Qt.Checked or Qt.Unchecked)
        """
        is_visible = state == Qt.Checked
        
        # Recursively sync all children
        for i in range(group_item.childCount()):
            child = group_item.child(i)
            if child:
                # Check if this child is a layer or group
                layer = child.data(0, Qt.UserRole)
                is_group = child.data(0, Qt.UserRole + 3)
                
                if layer and isinstance(layer, (QgsVectorLayer, QgsRasterLayer)):
                    # This is a layer - update its visibility in QGIS
                    root = QgsProject.instance().layerTreeRoot()
                    layer_node = root.findLayer(layer.id())
                    if layer_node:
                        layer_node.setItemVisibilityChecked(is_visible)
                elif is_group:
                    # This is a nested group - recursively sync it
                    self._sync_group_visibility_to_qgis(child, state)

    def _on_individual_layer_style_changed(self):
        """Handle style changes for a layer and update its icon in the tree."""
        if self.is_updating_style:
            return

        self.is_updating_style = True
        try:
            layer = self.sender()
            if not isinstance(layer, (QgsVectorLayer, QgsRasterLayer)):
                return

            # Fast lookup using the mapping
            item = self.layer_to_item_map.get(layer.id())
            if item:
                # Update the icon for the specific item
                try:
                    renderer = layer.renderer() if hasattr(layer, 'renderer') else None
                    if renderer:
                        legend_symbol_items = renderer.legendSymbolItems()
                        if legend_symbol_items:
                            symbol = legend_symbol_items[0].symbol()
                            if symbol:
                                img = symbol.asImage(QSize(16, 16))
                                if not img.isNull():
                                    pixmap = QPixmap.fromImage(img)
                                    if not pixmap.isNull():
                                        icon = QIcon(pixmap)
                                        item.setIcon(0, icon)
                                        self.log_message(f"Style icon updated for layer '{layer.name()}'.")
                except Exception as e:
                    self.log_message(f"Could not update style icon for layer '{layer.name()}': {e}")
        finally:
            self.is_updating_style = False

    def upload_sld_style(self, layer, layer_name, base_url, username, password, workspace):
        """
        Export and upload the SLD style for a given layer based on GeoServer REST API best practices.
        
        This method has been refactored into the SLDStyleUploader class
        for better code organization and maintainability.
        
        Args:
            layer: QGIS layer object
            layer_name: Name of the layer
            base_url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            workspace: Target workspace name
        """
        return self.sld_style_uploader.upload_sld_style(layer, layer_name, workspace, base_url, username, password)

    def create_workspace(self):
        """
        Create a new GeoServer workspace.
        
        This method has been refactored into the WorkspaceCreationManager class
        for better code organization and maintainability.
        """
        return self.workspace_creation_manager.create_workspace()

    def toggle_layer_selection(self, state):
        """Toggle selection of all layers based on the checkbox state."""
        # Mark this as a user-initiated change
        self.user_initiated_checkbox_change = True
        self.workspace_layers_list.blockSignals(True)
        if state == Qt.Checked:
            self.workspace_layers_list.selectAll()
        else:
            self.workspace_layers_list.clearSelection()
        self.workspace_layers_list.blockSignals(False)
        # Reset the flag after a short delay to allow for processing
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, lambda: setattr(self, 'user_initiated_checkbox_change', False))


    def toggle_qgis_layer_selection(self, state):
        """Toggle selection of all layers in the QGIS project layers tree."""
        for i in range(self.qgis_layers_tree.topLevelItemCount()):
            item = self.qgis_layers_tree.topLevelItem(i)
            if state == Qt.Checked:
                item.setCheckState(0, Qt.Checked)
            else:
                item.setCheckState(0, Qt.Unchecked)

    def delete_workspace(self):
        """
        Delete the selected GeoServer workspace and all its contents.
        
        This method has been refactored into the WorkspaceDeletionManager class
        for better code organization and maintainability.
        """
        return self.workspace_deletion_manager.delete_workspace()

    def _show_workspace_context_menu(self, position):
        """
        Show context menu for workspace list right-click operations.
        
        Args:
            position: Position where the context menu was requested
        """
        # Get the item at the clicked position
        item = self.workspaces_list.itemAt(position)
        if not item:
            return
        
        # Create context menu
        context_menu = QMenu(self)
        
        # Add Rename action
        rename_action = QAction("Rename Workspace", self)
        rename_action.triggered.connect(self._on_rename_workspace_context)
        context_menu.addAction(rename_action)
        
        # Add Delete Content action
        delete_content_action = QAction("Delete Workspace Content", self)
        delete_content_action.triggered.connect(self._on_delete_workspace_content_context)
        context_menu.addAction(delete_content_action)
        
        # Show the menu at the cursor position
        context_menu.exec_(self.workspaces_list.mapToGlobal(position))
    
    def _on_rename_workspace_context(self):
        """
        Handle rename workspace action from context menu.
        """
        # Get selected workspace
        current_item = self.workspaces_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Workspace Error", "Please select a workspace to rename.")
            return
        
        old_name = current_item.text()
        
        # Prompt for new name
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Workspace",
            f"Enter new name for workspace '{old_name}':",
            text=old_name
        )
        
        if not ok or not new_name.strip():
            return
        
        new_name = new_name.strip()
        
        # Check if name changed
        if new_name == old_name:
            QMessageBox.information(self, "No Change", "The new workspace name is the same as the current name.")
            return
        
        # Get connection details
        url = self.get_base_url()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not url or not username or not password:
            QMessageBox.warning(self, "Input Error", "Please provide the URL, username, and password.")
            return
        
        try:
            # Get workspace details
            get_response = requests.get(
                f"{url}/rest/workspaces/{old_name}.json",
                auth=(username, password),
                headers={"Accept": "application/json"}
            )
            
            if get_response.status_code != 200:
                raise Exception(f"Failed to get workspace details: {get_response.status_code}")
            
            # Update workspace with new name
            workspace_data = get_response.json()
            workspace_data['workspace']['name'] = new_name
            
            # Send PUT request to update workspace
            response = requests.put(
                f"{url}/rest/workspaces/{old_name}.json",
                auth=(username, password),
                headers={"Content-Type": "application/json"},
                json=workspace_data
            )
            
            # Handle response
            if response.status_code == 200:
                QMessageBox.information(self, "Success", f"Workspace '{old_name}' renamed to '{new_name}' successfully.")
                self.log_message(f"✓ Workspace renamed from '{old_name}' to '{new_name}'")
                # Refresh the workspaces list
                self.retrieve_geoserver_info()
            elif response.status_code == 409:
                QMessageBox.warning(
                    self, 
                    "Error", 
                    f"Failed to rename workspace. A workspace with the name '{new_name}' may already exist."
                )
                self.log_message(f"Failed to rename workspace {old_name}: 409 Conflict - name may already exist")
            else:
                QMessageBox.warning(
                    self, 
                    "Error", 
                    f"Failed to rename workspace. Status code: {response.status_code}\nResponse: {response.text}"
                )
                self.log_message(f"Failed to rename workspace {old_name}: Status {response.status_code} - {response.text}")
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while renaming workspace: {str(e)}")
            self.log_message(f"Error renaming workspace {old_name} to {new_name}: {str(e)}")
    
    def _on_delete_workspace_content_context(self):
        """
        Handle delete workspace content action from context menu.
        Deletes all layers, styles, and datastores in the workspace, leaving it empty.
        """
        # Get selected workspace
        current_item = self.workspaces_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Workspace Error", "Please select a workspace.")
            return
        
        workspace_name = current_item.text()
        
        # Confirm deletion with strong warning
        reply = QMessageBox.question(
            self,
            "Confirm Delete Workspace Content",
            f"Are you sure you want to delete all content in workspace '{workspace_name}'?\n"
            "This will delete all layers, styles, and datastores in this workspace.\n"
            "The workspace itself will remain empty.\n\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Get connection details
        url = self.get_base_url()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not url or not username or not password:
            QMessageBox.warning(self, "Input Error", "Please provide the URL, username, and password.")
            return
        
        try:
            self.log_message(f"Starting to delete content from workspace '{workspace_name}'...")
            
            # Delete all layers in the workspace
            self._delete_all_workspace_layers(workspace_name, url, username, password)
            
            # Delete all datastores in the workspace
            self._delete_all_workspace_datastores(workspace_name, url, username, password)
            
            # Delete all coverage stores (raster data) in the workspace
            self._delete_all_workspace_coveragestores(workspace_name, url, username, password)
            
            # Delete all styles in the workspace
            self._delete_all_workspace_styles(workspace_name, url, username, password)
            
            QMessageBox.information(self, "Success", f"All content in workspace '{workspace_name}' has been deleted successfully.")
            self.log_message(f"✓ Workspace '{workspace_name}' content deleted successfully")
            
            # Refresh the workspace content
            self.load_workspace_layers()
            self.load_stores()
            self.load_layer_styles()
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while deleting workspace content: {str(e)}")
            self.log_message(f"Error deleting workspace content: {str(e)}")
    
    def _delete_all_workspace_layers(self, workspace_name, url, username, password):
        """
        Delete all layers in the workspace.
        
        Args:
            workspace_name: Name of the workspace
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        try:
            # Get all layers in the workspace
            response = requests.get(
                f"{url}/rest/workspaces/{workspace_name}/layers.json",
                auth=(username, password),
                headers={"Accept": "application/json"}
            )
            
            if response.status_code != 200:
                self.log_message(f"No layers found in workspace '{workspace_name}'")
                return
            
            layers_data = response.json()
            layers = layers_data.get('layers', {}).get('layer', [])
            
            # Handle single layer returned as dict
            if isinstance(layers, dict):
                layers = [layers]
            
            for layer in layers:
                layer_name = layer.get('name')
                if layer_name:
                    delete_response = requests.delete(
                        f"{url}/rest/workspaces/{workspace_name}/layers/{layer_name}",
                        auth=(username, password)
                    )
                    if delete_response.status_code in [200, 204]:
                        self.log_message(f"✓ Deleted layer '{layer_name}'")
                    else:
                        self.log_message(f"⚠ Failed to delete layer '{layer_name}': {delete_response.status_code}")
        
        except Exception as e:
            self.log_message(f"Error deleting workspace layers: {str(e)}")
    
    def _delete_all_workspace_datastores(self, workspace_name, url, username, password):
        """
        Delete all datastores in the workspace.
        
        Args:
            workspace_name: Name of the workspace
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        try:
            # Get all datastores in the workspace
            response = requests.get(
                f"{url}/rest/workspaces/{workspace_name}/datastores.json",
                auth=(username, password),
                headers={"Accept": "application/json"}
            )
            
            if response.status_code != 200:
                self.log_message(f"No datastores found in workspace '{workspace_name}'")
                return
            
            datastores_data = response.json()
            datastores = datastores_data.get('dataStores', {}).get('dataStore', [])
            
            # Handle single datastore returned as dict
            if isinstance(datastores, dict):
                datastores = [datastores]
            
            for datastore in datastores:
                datastore_name = datastore.get('name')
                if datastore_name:
                    delete_response = requests.delete(
                        f"{url}/rest/workspaces/{workspace_name}/datastores/{datastore_name}?recurse=true",
                        auth=(username, password)
                    )
                    if delete_response.status_code in [200, 204]:
                        self.log_message(f"✓ Deleted datastore '{datastore_name}'")
                    else:
                        self.log_message(f"⚠ Failed to delete datastore '{datastore_name}': {delete_response.status_code}")
        
        except Exception as e:
            self.log_message(f"Error deleting workspace datastores: {str(e)}")
    
    def _delete_all_workspace_coveragestores(self, workspace_name, url, username, password):
        """
        Delete all coverage stores (raster data) in the workspace.
        
        Args:
            workspace_name: Name of the workspace
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        try:
            # Get all coverage stores in the workspace
            response = requests.get(
                f"{url}/rest/workspaces/{workspace_name}/coveragestores.json",
                auth=(username, password),
                headers={"Accept": "application/json"}
            )
            
            if response.status_code != 200:
                self.log_message(f"No coverage stores found in workspace '{workspace_name}'")
                return
            
            coveragestores_data = response.json()
            coveragestores = coveragestores_data.get('coverageStores', {}).get('coverageStore', [])
            
            # Handle single coverage store returned as dict
            if isinstance(coveragestores, dict):
                coveragestores = [coveragestores]
            
            for coveragestore in coveragestores:
                coveragestore_name = coveragestore.get('name')
                if coveragestore_name:
                    delete_response = requests.delete(
                        f"{url}/rest/workspaces/{workspace_name}/coveragestores/{coveragestore_name}?recurse=true",
                        auth=(username, password)
                    )
                    if delete_response.status_code in [200, 204]:
                        self.log_message(f"✓ Deleted coverage store '{coveragestore_name}'")
                    else:
                        self.log_message(f"⚠ Failed to delete coverage store '{coveragestore_name}': {delete_response.status_code}")
        
        except Exception as e:
            self.log_message(f"Error deleting workspace coverage stores: {str(e)}")
    
    def _delete_all_workspace_styles(self, workspace_name, url, username, password):
        """
        Delete all styles in the workspace.
        
        Args:
            workspace_name: Name of the workspace
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        try:
            # Get all styles in the workspace
            response = requests.get(
                f"{url}/rest/workspaces/{workspace_name}/styles.json",
                auth=(username, password),
                headers={"Accept": "application/json"}
            )
            
            if response.status_code != 200:
                self.log_message(f"No styles found in workspace '{workspace_name}'")
                return
            
            styles_data = response.json()
            styles = styles_data.get('styles', {}).get('style', [])
            
            # Handle single style returned as dict
            if isinstance(styles, dict):
                styles = [styles]
            
            for style in styles:
                style_name = style.get('name')
                if style_name:
                    delete_response = requests.delete(
                        f"{url}/rest/workspaces/{workspace_name}/styles/{style_name}",
                        auth=(username, password)
                    )
                    if delete_response.status_code in [200, 204]:
                        self.log_message(f"✓ Deleted style '{style_name}'")
                    else:
                        self.log_message(f"⚠ Failed to delete style '{style_name}': {delete_response.status_code}")
        
        except Exception as e:
            self.log_message(f"Error deleting workspace styles: {str(e)}")

    def show_sld_window(self, layer):
        """
        Display the SLD content of a layer in a new window using a temporary file for robustness.
        
        This method has been refactored into the SLDWindowManager class
        for better code organization and maintainability.
        
        Args:
            layer: QGIS layer object to display SLD for
        """
        return self.sld_window_manager.show_sld_window(layer)

    def _on_show_sld_clicked(self, layer):
        """Helper method to handle SLD button clicks."""
        self.show_sld_window(layer)

    def show_sld(self, layer, sld_content, dialog):
        """Display the SLD content in the dialog window."""
        dialog.close()
        self.show_sld_window(layer)

    def delete_layer(self):
        """
        Delete the selected layers and their associated stores from GeoServer.
        
        This method has been refactored into the LayerDeletionManager class
        for better code organization and maintainability.
        """
        return self.layer_deletion_manager.delete_layer()

    def select_all_datastores(self, state):
        """Select or deselect all items in the datastores list."""
        # Set selection mode to allow multiple selections
        self.datastores_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        if state == Qt.Checked:
            # Select all valid items
            for i in range(self.datastores_list.count()):
                item = self.datastores_list.item(i)
                # Avoid trying to select placeholder messages
                if "No stores available" not in item.text() and "No workspace selected" not in item.text():
                    item.setSelected(True)
        else:
            # Deselect all items
            self.datastores_list.clearSelection()

    def uncheck_select_all_if_checked(self):
        """
        Uncheck "Select All Layers" checkbox if not all layers are selected.
        
        This method is called when:
        - User changes selection in workspace_layers_list
        - Items are added/removed from the list
        
        Logic:
        - If selected count < total count → uncheck "Select All Layers"
        - If selected count == total count → check "Select All Layers"
        """
        if not hasattr(self, 'workspace_layers_list') or not hasattr(self, 'select_all_layers_checkbox'):
            return
        
        total_items = self.workspace_layers_list.count()
        selected_items = len(self.workspace_layers_list.selectedItems())
        
        # Block signals to prevent recursive calls
        self.select_all_layers_checkbox.blockSignals(True)
        
        if selected_items == total_items and total_items > 0:
            # All items selected
            self.select_all_layers_checkbox.setChecked(True)
        else:
            # Not all items selected or no items
            self.select_all_layers_checkbox.setChecked(False)
        
        self.select_all_layers_checkbox.blockSignals(False)

    def uncheck_select_all_datastores_if_needed(self):
        """
        Uncheck "Select All Datastores" checkbox if not all datastores are selected.
        
        This method is called when:
        - User changes selection in datastores_list
        - Items are added/removed from the list
        
        Logic:
        - If selected count < total count → uncheck "Select All Datastores"
        - If selected count == total count → check "Select All Datastores"
        """
        if not hasattr(self, 'datastores_list') or not hasattr(self, 'select_all_datastores_checkbox'):
            return
        
        total_items = self.datastores_list.count()
        selected_items = len(self.datastores_list.selectedItems())
        
        # Block signals to prevent recursive calls
        self.select_all_datastores_checkbox.blockSignals(True)
        
        if selected_items == total_items and total_items > 0:
            # All items selected
            self.select_all_datastores_checkbox.setChecked(True)
        else:
            # Not all items selected or no items
            self.select_all_datastores_checkbox.setChecked(False)
        
        self.select_all_datastores_checkbox.blockSignals(False)

    def uncheck_select_all_styles_if_needed(self):
        """
        Uncheck "Select All Styles" checkbox if not all styles are selected.
        
        This method is called when:
        - User changes selection in layer_styles_list
        - Items are added/removed from the list
        
        Logic:
        - If selected count < total count → uncheck "Select All Styles"
        - If selected count == total count → check "Select All Styles"
        """
        if not hasattr(self, 'layer_styles_list') or not hasattr(self, 'select_all_styles_checkbox'):
            return
        
        total_items = self.layer_styles_list.count()
        selected_items = len(self.layer_styles_list.selectedItems())
        
        # Block signals to prevent recursive calls
        self.select_all_styles_checkbox.blockSignals(True)
        
        if selected_items == total_items and total_items > 0:
            # All items selected
            self.select_all_styles_checkbox.setChecked(True)
        else:
            # Not all items selected or no items
            self.select_all_styles_checkbox.setChecked(False)
        
        self.select_all_styles_checkbox.blockSignals(False)

    def delete_selected_datastores(self):
        """
        Delete selected datastores and coveragestores from GeoServer.
        
        This method has been refactored into the DatastoreDeletionManager class
        for better code organization and maintainability.
        """
        return self.datastore_deletion_manager.delete_selected_datastores()

    def save_ui_preferences(self):
        """Save UI preferences and GeoServer settings to the INI file."""
        try:
            # Get the plugin directory safely
            if '__file__' in globals():
                plugin_dir = os.path.dirname(os.path.abspath(__file__))
            else:
                # Fallback: use the current working directory or home directory
                plugin_dir = os.getcwd() if os.getcwd() else os.path.expanduser("~")
            
            settings_file = os.path.join(plugin_dir, "geoserver_settings.ini")
            
            config = configparser.ConfigParser()
            
            # Read existing config if it exists
            if os.path.exists(settings_file):
                config.read(settings_file)
            
            # Ensure sections exist
            if not config.has_section("UI"):
                config.add_section("UI")
            if not config.has_section("GeoServer"):
                config.add_section("GeoServer")
            
            # Save UI preferences
            config.set("UI", "show_log_dialog", "true" if self.show_log_dialog_checkbox.isChecked() else "false")
            
            # Save GeoServer settings
            config.set("GeoServer", "url", self.url_input.text().strip())
            config.set("GeoServer", "username", self.username_input.text().strip())
            config.set("GeoServer", "password", self.password_input.text().strip())
            
            # Write config to file
            with open(settings_file, "w") as configfile:
                config.write(configfile)
        except Exception as e:
            # Silently fail - don't interrupt dialog closing
            print(f"DEBUG: Failed to save UI preferences: {str(e)}")

    def _on_stop_upload_clicked(self):
        """Handle stop upload button click."""
        # Set stop flag
        self.upload_stop_requested = True
        
        # Set stop flag in log tracker
        if hasattr(self, 'log_tracker') and hasattr(self.log_tracker, 'live_window'):
            if self.log_tracker.live_window:
                self.log_tracker.live_window.stop_upload = True
        
        # Hide the stop button
        self.stop_upload_btn.setVisible(False)
        self.log_message("🛑 Stop upload requested by user")
    
    def closeEvent(self, event):
        """Disconnect signals when the dialog is closed to prevent memory leaks."""
        # Save UI preferences before closing
        self.save_ui_preferences()
        
        # Uncheck the action when dialog is closed
        if hasattr(self, 'action'):
            self.action.setChecked(False)
            
    def reject(self):
        """Handle dialog reject event (e.g. Esc key or X button) to uncheck the action."""
        if hasattr(self, 'action'):
            self.action.setChecked(False)
        super().reject()
        
        # Set flag to suppress logging during shutdown
        global DEBUG_VERBOSE
        original_debug = DEBUG_VERBOSE
        DEBUG_VERBOSE = False
        
        try:
            QgsProject.instance().layersAdded.disconnect(self.populate_qgis_layers)
            QgsProject.instance().layersWillBeRemoved.disconnect(self.populate_qgis_layers)
            QgsProject.instance().layersRemoved.disconnect(self.populate_qgis_layers)
            QgsProject.instance().layerTreeRoot().layerOrderChanged.disconnect(self.sync_layer_order)
        except TypeError:
            # This can happen if the signals were already disconnected or never connected
            pass
        
        # Disconnect the layer order signal
        try:
            QgsProject.instance().layerTreeRoot().customLayerOrderChanged.disconnect(self.sync_layer_order)
        except TypeError:
            # This can happen if the signal was already disconnected or never connected
            pass
        
        # Disconnect the layer visibility signal
        try:
            QgsProject.instance().layerTreeRoot().visibilityChanged.disconnect(self._on_layer_visibility_changed)
        except TypeError:
            # This can happen if the signal was already disconnected or never connected
            pass
        
        # Restore debug flag
        DEBUG_VERBOSE = original_debug
        
        super().closeEvent(event)


    def load_layer_styles(self):
        """
        Load and display all SLD styles associated with the selected workspace.
        
        This method has been refactored into the LayerStylesLoader class
        for better code organization and maintainability.
        """
        return self.layer_styles_loader.load_layer_styles()

    def delete_selected_style(self):
        """
        Delete all selected styles from the styles list.
        
        This method has been refactored into the StyleDeletionManager class
        for better code organization and maintainability.
        """
        return self.style_deletion_manager.delete_selected_style()

    def show_sld_for_selected_style(self):
        """Show SLD content for the currently selected style in the layer styles list."""
        selected_items = self.layer_styles_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Selection Error", "Please select a style to view its SLD.")
            return
            
        style_name = selected_items[0].text()
        self.show_style_sld_window(style_name)

    def show_style_sld_window(self, style_name):
        """
        Display the SLD content of a selected style from the workspace layer styles list.
        
        This method has been refactored into the StyleSLDWindowManager class
        for better code organization and maintainability.
        
        Args:
            style_name: Name of the style to display SLD content for
        """
        return self.style_sld_manager.show_style_sld_window(style_name)

    def uncheck_select_all_if_checked(self):
        """Uncheck the 'Select All Layers' checkbox if it is currently checked and change is not user-initiated."""
        # Only uncheck if this is not a user-initiated change
        if not getattr(self, 'user_initiated_checkbox_change', False) and self.select_all_layers_checkbox.isChecked():
            self.select_all_layers_checkbox.setChecked(False)

    def reset_all_caches(self):
        """
        Reset all GeoServer tile caches using the GeoWebCache REST API.
        
        This method has been refactored into the CacheResetManager class
        for better code organization and maintainability.
        """
        return self.cache_reset_manager.reset_all_caches()

    def get_wms_layer_bbox(self, url, username, password, layer_name):
        """
        Fetch and parse WMS Capabilities XML to get the bounding box for a given layer.
        
        This method has been refactored into the WMSLayerBBoxRetriever class
        for better code organization and maintainability.
        
        Args:
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            layer_name: Name of the layer to get bbox for
            
        Returns:
            tuple: (extent, crs) where extent is [minx, miny, maxx, maxy] and crs is the coordinate reference system,
                   or (None, None) if not found or error occurred
        """
        return self.wms_bbox_retriever.get_wms_layer_bbox(url, username, password, layer_name)

    

    def refresh_current_workspace_content(self):
        """
        Refresh layers, datastores, and styles for the current workspace while preserving selection.
        
        This method has been refactored into the WorkspaceContentRefresher class
        for better code organization and maintainability.
        """
        return self.workspace_refresher.refresh_current_workspace_content()

    def open_postgis_credentials_dialog(self):
        """Open the PostGIS credentials management dialog."""
        dialog = PostGISCredentialsDialog(self)
        dialog.exec_()

    def prompt_for_postgis_credentials(self, host, port, database):
        """
        Prompt user for PostGIS credentials when they are needed for upload.
        Pre-populate the dialog with connection details and focus on credentials.
        Returns True if credentials were saved, False if cancelled.
        """
        dialog = PostGISCredentialsDialog(self)
        
        # Pre-populate the connection details
        dialog.host_input.setText(host)
        dialog.port_input.setValue(int(port))
        dialog.database_input.setText(database)
        
        # Focus on username field since connection details are pre-filled
        dialog.username_input.setFocus()
        
        # Show a message about why the dialog opened
        QMessageBox.information(self, "PostGIS Credentials Required", 
                              f"PostGIS credentials are required for database connection:\n"
                              f"Host: {host}\n"
                              f"Port: {port}\n"
                              f"Database: {database}\n\n"
                              f"Please enter your username and password.")
        
        result = dialog.exec_()
        return result == QDialog.Accepted

    def show_documentation(self):
        """Show the documentation dialog."""
        try:
            import sys
            import os
            import importlib.util
            
            # Use self.plugin_dir which is already set during initialization
            plugin_path = self.plugin_dir
            
            # Ensure plugin path is in sys.path
            if plugin_path not in sys.path:
                sys.path.insert(0, plugin_path)
            
            # Try relative import first (plugin context)
            try:
                from .documentation import DocumentationDialog
            except (ImportError, ValueError, SystemError):
                # Fall back to absolute import (script context)
                try:
                    from documentation import DocumentationDialog
                except ImportError:
                    # Last resort: load the module directly from file
                    doc_file = os.path.join(plugin_path, "documentation.py")
                    spec = importlib.util.spec_from_file_location("documentation", doc_file)
                    if spec and spec.loader:
                        doc_module = importlib.util.module_from_spec(spec)
                        sys.modules["documentation"] = doc_module
                        spec.loader.exec_module(doc_module)
                        DocumentationDialog = doc_module.DocumentationDialog
                    else:
                        raise ImportError(f"Could not load documentation.py from {doc_file}")
            
            dialog = DocumentationDialog(parent=self, plugin_dir=self.plugin_dir)
            dialog.exec_()
        except Exception as e:
            import traceback
            error_msg = f"Could not open documentation: {e}\n\n{traceback.format_exc()}"
            self.log_message(f"❌ ERROR: {error_msg}", level=Qgis.Critical)
            QMessageBox.critical(self, "Error", error_msg)

    def _on_layers_dropped(self, layer_names, target_workspace):
        """Handle layers dropped on a workspace."""
        try:
            print(f"DEBUG: _on_layers_dropped called with {len(layer_names)} layers, target: {target_workspace}")
            self.log_message(f"Layers dropped: {layer_names} -> {target_workspace}")
            
            # Get current workspace
            current_workspace_item = self.workspaces_list.currentItem()
            if not current_workspace_item:
                self.log_message("No source workspace selected", level=Qgis.Warning)
                print("DEBUG: No source workspace selected")
                return
            
            source_workspace = current_workspace_item.text()
            print(f"DEBUG: Source workspace: {source_workspace}")
            
            # Check if dropping on same workspace
            if source_workspace == target_workspace:
                self.log_message("Cannot copy/move to the same workspace", level=Qgis.Warning)
                print("DEBUG: Same workspace, ignoring")
                return
            
            # Filter layers: separate vectors and rasters
            print(f"DEBUG: Filtering layers by type")
            vector_layers = []
            raster_layers = []
            
            url = self.get_base_url()
            username = self.username_input.text().strip()
            password = self.password_input.text().strip()
            auth = (username, password) if username and password else None
            
            try:
                from .layer_metadata_extractor import LayerMetadataExtractor
            except ImportError:
                import sys
                import os
                sys.path.insert(0, self.plugin_dir)
                from layer_metadata_extractor import LayerMetadataExtractor
            
            extractor = LayerMetadataExtractor()
            
            for layer_name in layer_names:
                try:
                    layer_metadata = extractor.get_layer_metadata(url, auth, source_workspace, layer_name)
                    if layer_metadata:
                        layer_info = layer_metadata.get('layer', {})
                        layer_type = layer_info.get('type', '')
                        
                        if layer_type == 'RASTER':
                            raster_layers.append(layer_name)
                            print(f"DEBUG: {layer_name} is RASTER")
                        else:
                            vector_layers.append(layer_name)
                            print(f"DEBUG: {layer_name} is VECTOR")
                    else:
                        vector_layers.append(layer_name)
                        print(f"DEBUG: {layer_name} type unknown, treating as vector")
                except Exception as e:
                    print(f"DEBUG: Error checking layer type for {layer_name}: {e}")
                    vector_layers.append(layer_name)
            
            print(f"DEBUG: Vector layers: {vector_layers}, Raster layers: {raster_layers}")
            
            # Case 1: Only rasters - show custom notification and exit
            if not vector_layers and raster_layers:
                print(f"DEBUG: Only raster layers detected")
                # Show custom light blue notification
                self._show_custom_notification("Drag n Drop Rasters is not implemented yet")
                return
            
            # Case 2: Only vectors or mixed - show dialog with only vectors
            if not vector_layers:
                print(f"DEBUG: No vector layers to process")
                return
            
            # Show copy/move choice dialog with only vector layers
            try:
                from .copy_move_choice_dialog import CopyMoveChoiceDialog
            except ImportError:
                import sys
                import os
                # Use plugin_dir instead of __file__
                sys.path.insert(0, self.plugin_dir)
                from copy_move_choice_dialog import CopyMoveChoiceDialog
            
            print(f"DEBUG: Creating CopyMoveChoiceDialog with {len(vector_layers)} vector layers")
            dialog = CopyMoveChoiceDialog(
                parent=self,
                layer_names=vector_layers,
                target_workspace=target_workspace
            )
            
            print("DEBUG: Showing CopyMoveChoiceDialog")
            result = dialog.exec_()
            print(f"DEBUG: Dialog result: {result}, QDialog.Accepted: {QDialog.Accepted}")
            print(f"DEBUG: Dialog choice: {dialog.get_choice()}")
            
            if result == QDialog.Accepted:
                operation_mode = dialog.get_choice()
                print(f"DEBUG: Operation mode: {operation_mode}")
                if operation_mode:
                    # Execute operation directly with overwrite strategy (no dialog)
                    print(f"DEBUG: Executing copy/move operation with {len(vector_layers)} vector layers")
                    self._execute_copy_move_operation(
                        vector_layers, source_workspace, target_workspace, operation_mode, "overwrite"
                    )
                    
                    # Show notification about skipped rasters if mixed
                    if raster_layers:
                        print(f"DEBUG: Skipped {len(raster_layers)} raster layer(s)")
                        self._show_custom_notification("Drag n Drop Rasters is not implemented yet")
                else:
                    print("DEBUG: Operation mode is None or empty")
            else:
                print(f"DEBUG: Dialog was not accepted (result={result})")
        
        except Exception as e:
            print(f"DEBUG: Exception in _on_layers_dropped: {str(e)}")
            import traceback
            traceback.print_exc()
            self.log_message(f"Error handling dropped layers: {str(e)}", level=Qgis.Warning)
    
    def _show_layer_details_dialog(self, layer_names, source_workspace):
        """Show a dialog with layer details (name, datastore, style)."""
        try:
            url = self.get_base_url()
            username = self.username_input.text().strip()
            password = self.password_input.text().strip()
            auth = (username, password) if username and password else None
            
            # Build details text
            details_text = "Layer Details:\n\n"
            
            for layer_name in layer_names:
                details_text += f"Layer: {layer_name}\n"
                
                # Get layer metadata
                try:
                    layer_url = f"{url}/rest/layers/{source_workspace}:{layer_name}.json"
                    response = requests.get(layer_url, auth=auth, timeout=30)
                    
                    if response.status_code == 200:
                        layer_info = response.json().get('layer', {})
                        
                        # Get style name directly from the layer endpoint response
                        # The defaultStyle.name field contains the actual style name
                        style_name = layer_info.get('defaultStyle', {}).get('name', 'N/A')
                        print(f"DEBUG: Style name from layer endpoint: {style_name}")
                        
                        details_text += f"  Style: {style_name}\n"
                        
                        # Get datastore/coverage name
                        resource = layer_info.get('resource', {})
                        resource_class = resource.get('@class', 'unknown')
                        
                        if resource_class == 'featureType':
                            # Vector layer
                            ft_url = resource.get('href', '')
                            if ft_url:
                                ft_response = requests.get(ft_url, auth=auth, timeout=30)
                                if ft_response.status_code == 200:
                                    ft_info = ft_response.json().get('featureType', {})
                                    store_name = ft_info.get('store', {}).get('name', 'N/A')
                                    details_text += f"  DataStore: {store_name}\n"
                                    details_text += f"  Type: Vector (FeatureType)\n"
                        elif resource_class == 'coverage':
                            # Raster layer
                            cov_url = resource.get('href', '')
                            if cov_url:
                                cov_response = requests.get(cov_url, auth=auth, timeout=30)
                                if cov_response.status_code == 200:
                                    cov_info = cov_response.json().get('coverage', {})
                                    store_name = cov_info.get('store', {}).get('name', 'N/A')
                                    details_text += f"  CoverageStore: {store_name}\n"
                                    details_text += f"  Type: Raster (Coverage)\n"
                    
                except Exception as e:
                    details_text += f"  Error fetching details: {str(e)}\n"
                
                details_text += "\n"
            
            # Show dialog
            QMessageBox.information(self, "Layer Details", details_text)
            
        except Exception as e:
            print(f"DEBUG: Error in _show_layer_details_dialog: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _execute_copy_move_operation(self, layer_names, source_workspace, target_workspace, operation_mode, conflict_strategy):
        """Execute copy/move operation directly without any dialog."""
        try:
            print(f"DEBUG: _execute_copy_move_operation called")
            print(f"DEBUG: Layers: {layer_names}, Source: {source_workspace}, Target: {target_workspace}, Mode: {operation_mode}, Strategy: {conflict_strategy}")
            
            # Import handler directly
            try:
                from .layer_copy_move_handler import LayerCopyMoveHandler
            except ImportError:
                import sys
                import os
                sys.path.insert(0, self.plugin_dir)
                from layer_copy_move_handler import LayerCopyMoveHandler
            
            print("DEBUG: Creating LayerCopyMoveHandler")
            handler = LayerCopyMoveHandler()
            
            # Get connection details
            url = self.get_base_url()
            username = self.username_input.text().strip()
            password = self.password_input.text().strip()
            
            print(f"DEBUG: Starting {operation_mode} operation for {len(layer_names)} layers")
            
            # Execute operation for each layer
            success_count = 0
            auth = (username, password)
            
            for layer_name in layer_names:
                try:
                    print(f"DEBUG: Processing layer: {layer_name}")
                    if operation_mode == 'copy':
                        result, message = handler.copy_layer(
                            url, auth, source_workspace, layer_name, 
                            target_workspace, layer_name, conflict_strategy
                        )
                    else:  # move
                        result, message = handler.move_layer(
                            url, auth, source_workspace, layer_name,
                            target_workspace, layer_name, conflict_strategy
                        )
                    
                    print(f"DEBUG: Result: {result}, Message: {message}")
                    
                    if result:
                        success_count += 1
                        self.log_message(f"✓ {layer_name}: {operation_mode.capitalize()} successful - {message}")
                        print(f"DEBUG: {layer_name} {operation_mode} successful")
                    else:
                        self.log_message(f"✗ {layer_name}: {operation_mode.capitalize()} failed - {message}")
                        print(f"DEBUG: {layer_name} {operation_mode} failed - {message}")
                
                except Exception as e:
                    self.log_message(f"✗ {layer_name}: Error - {str(e)}", level=Qgis.Warning)
                    print(f"DEBUG: Error processing {layer_name}: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            # Log summary
            self.log_message(f"✓ {operation_mode.capitalize()} completed: {success_count}/{len(layer_names)} layers")
            print(f"DEBUG: Operation completed: {success_count}/{len(layer_names)} successful")
            
            # Focus on target workspace
            self._on_copy_move_completed(target_workspace)
        
        except Exception as e:
            print(f"DEBUG: Exception in _execute_copy_move_operation: {str(e)}")
            import traceback
            traceback.print_exc()
            self.log_message(f"Error executing copy/move operation: {str(e)}", level=Qgis.Warning)
    
    def _open_copy_move_dialog_with_layers(self, layer_names, source_workspace, target_workspace, operation_mode):
        """Open copy/move dialog with pre-filled information."""
        try:
            print(f"DEBUG: _open_copy_move_dialog_with_layers called")
            print(f"DEBUG: Layers: {layer_names}, Source: {source_workspace}, Target: {target_workspace}, Mode: {operation_mode}")
            
            try:
                from .copy_move_layers_dialog import CopyMoveLayersDialog
            except ImportError:
                import sys
                import os
                # Use plugin_dir instead of __file__
                sys.path.insert(0, self.plugin_dir)
                from copy_move_layers_dialog import CopyMoveLayersDialog
            
            print("DEBUG: Creating CopyMoveLayersDialog")
            dialog = CopyMoveLayersDialog(
                parent=self,
                layers=layer_names,
                source_workspace=source_workspace,
                operation_mode=operation_mode,
                url=self.get_base_url(),
                auth=(self.username_input.text().strip(), self.password_input.text().strip())
            )
            
            print("DEBUG: Connecting completion signal")
            # Connect completion signal
            dialog.operation_completed.connect(self._on_copy_move_completed)
            
            # Show dialog
            print("DEBUG: Showing CopyMoveLayersDialog")
            dialog.exec_()
            print("DEBUG: CopyMoveLayersDialog closed")
        
        except Exception as e:
            print(f"DEBUG: Exception in _open_copy_move_dialog_with_layers: {str(e)}")
            import traceback
            traceback.print_exc()
            self.log_message(f"Error opening copy/move dialog: {str(e)}", level=Qgis.Warning)
    
    def _show_layers_context_menu(self, position):
        """Show context menu for layers list copy/move operations."""
        try:
            # Get item at position
            item = self.workspace_layers_list.itemAt(position)
            if not item:
                return
            
            # Get selected layers
            selected_items = self.workspace_layers_list.selectedItems()
            if not selected_items:
                return
            
            # Create context menu (no icons)
            from qgis.PyQt.QtWidgets import QMenu
            menu = QMenu()
            
            copy_action = menu.addAction("Copy Layer(s) to Another Workspace")
            move_action = menu.addAction("Move Layer(s) to Another Workspace")
            
            action = menu.exec_(self.workspace_layers_list.mapToGlobal(position))
            
            if action == copy_action:
                self._open_copy_move_dialog(selected_items, "copy")
            elif action == move_action:
                self._open_copy_move_dialog(selected_items, "move")
        except Exception as e:
            self.log_message(f"Error showing layers context menu: {str(e)}", level=Qgis.Warning)
    
    def _open_copy_move_dialog(self, selected_items, operation_mode):
        """Open copy/move dialog for selected layers."""
        # Extract layer names from selected items
        layer_names = [item.text() for item in selected_items]
        
        # Get current workspace
        current_workspace_item = self.workspaces_list.currentItem()
        if not current_workspace_item:
            self.log_message("No workspace selected", level=Qgis.Warning)
            return
        
        current_workspace = current_workspace_item.text()
        
        # Import dialog
        try:
            from .copy_move_layers_dialog import CopyMoveLayersDialog
        except ImportError:
            import sys
            import os
            # Use plugin_dir instead of __file__
            sys.path.insert(0, self.plugin_dir)
            from copy_move_layers_dialog import CopyMoveLayersDialog
        
        # Create and show dialog
        dialog = CopyMoveLayersDialog(
            parent=self,
            layers=layer_names,
            source_workspace=current_workspace,
            operation_mode=operation_mode,
            url=self.get_base_url(),
            auth=(self.username_input.text().strip(), self.password_input.text().strip())
        )
        
        # Connect completion signal
        dialog.operation_completed.connect(self._on_copy_move_completed)
        
        # Show dialog
        dialog.exec_()
    
    def _on_copy_move_completed(self, target_workspace):
        """Called when copy/move operation completes successfully."""
        try:
            # Find and select target workspace in list
            for i in range(self.workspaces_list.count()):
                item = self.workspaces_list.item(i)
                if item.text() == target_workspace:
                    self.workspaces_list.setCurrentItem(item)
                    self.log_message(f"Focused on target workspace: {target_workspace}")
                    break
        except Exception as e:
            self.log_message(f"Error focusing on target workspace: {str(e)}", level=Qgis.Warning)
    
    def _show_preview_dialog(self):
        """Create and show the OpenLayers preview dialog."""
        self.log_message("🎬 Preview button clicked - starting preview dialog creation")
        
        # Get current connection details
        url = self.get_base_url()
        self.log_message(f"📍 GeoServer URL: {url}")
        
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        self.log_message(f"👤 Username: {username}")

        if not url:
            self.log_message("❌ GeoServer URL is empty", level=Qgis.Warning)
            QMessageBox.warning(self, "Missing Information", "GeoServer URL is required to open the preview.")
            return

        # Get current workspace
        workspace_item = self.workspaces_list.currentItem()
        if not workspace_item:
            self.log_message("❌ No workspace selected", level=Qgis.Warning)
            QMessageBox.warning(self, "No Workspace Selected", "Please select a workspace before opening the preview.")
            return
        
        workspace = workspace_item.text()
        self.log_message(f"🏢 Workspace: {workspace}")
        
        if not workspace or workspace.strip() == "":
            self.log_message("❌ Workspace is empty", level=Qgis.Warning)
            QMessageBox.warning(self, "Invalid Workspace", "Selected workspace is empty or invalid.")
            return

        # Create and show the PreviewDialog - let preview.py handle the complexity
        try:
            self.log_message("🔧 Creating PreviewDialog instance...")
            # Import PreviewDialog lazily to avoid QtWebEngineWidgets dependency
            PreviewDialog = dynamic_import("preview", "PreviewDialog")
            preview_dialog = PreviewDialog(
                parent=self,
                geoserver_url=url,
                username=username,
                password=password,
                workspace=workspace,
                plugin_dir=self.plugin_dir
            )
            self.log_message("✅ PreviewDialog instance created successfully")
            
            self.log_message("🚀 Calling open_openlayers_preview()...")
            result = preview_dialog.open_openlayers_preview()
            self.log_message(f"✅ open_openlayers_preview() returned: {result}")
            
            if result:
                self.log_message("📺 Dialog is now displayed (non-blocking)")
                # Store reference to prevent garbage collection
                self.preview_dialog = preview_dialog
            else:
                self.log_message("❌ open_openlayers_preview() returned False/None", level=Qgis.Warning)
            
        except Exception as e:
            print(f"DEBUG: Exception in _show_preview_dialog: {str(e)}")
            import traceback
            traceback.print_exc()
            
            if 'QtWebEngineWidgets' in str(e) or 'ModuleNotFoundError' in str(type(e).__name__):
                # Create a custom dialog with copy button
                dialog = QMessageBox(self)
                dialog.setWindowTitle("Preview Not Available - Easy Fix")
                dialog.setIcon(QMessageBox.Warning)
                
                error_msg = (
                    "Preview dialog is not available on this system.\n\n"
                    "Reason: PyQt5.QtWebEngineWidgets is not installed.\n\n"
                    "═══════════════════════════════════════════════════════════\n"
                    "HOW TO INSTALL (Easy Steps):\n"
                    "═══════════════════════════════════════════════════════════\n\n"
                    "1. Open QGIS Python Console (Plugins → Python Console)\n\n"
                    "2. Copy the command below and paste it into the console:\n"
                    "   import subprocess, sys\n"
                    "   subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'PyQtWebEngine'])\n\n"
                    "3. Press Enter and wait for installation to complete\n\n"
                    "4. Restart QGIS\n\n"
                    "5. Try Preview again - it should work now!\n\n"
                    "═══════════════════════════════════════════════════════════\n\n"
                    "Note: The plugin will still work for uploading layers to GeoServer.\n"
                    "You can continue using other features."
                )
                
                dialog.setText(error_msg)
                
                # Add copy button
                copy_btn = dialog.addButton("Copy Installation Command", QMessageBox.ActionRole)
                ok_btn = dialog.addButton("OK", QMessageBox.AcceptRole)
                
                # Handle copy button click
                def copy_command():
                    from PyQt5.QtWidgets import QApplication
                    clipboard = QApplication.clipboard()
                    command = "import subprocess, sys\nsubprocess.check_call([sys.executable, '-m', 'pip', 'install', 'PyQtWebEngine'])"
                    clipboard.setText(command)
                    QMessageBox.information(self, "Copied", "Installation command copied to clipboard!\n\nNow paste it in the QGIS Python Console.")
                
                copy_btn.clicked.connect(copy_command)
                
                self.log_message(f"⚠️ Preview not available: QtWebEngineWidgets missing", level=Qgis.Warning)
                dialog.exec_()
            else:
                error_msg = f"Could not open the preview dialog: {e}"
                self.log_message(f"❌ ERROR: {error_msg}", level=Qgis.Critical)
                QMessageBox.critical(self, "Error", error_msg)
        except Exception as e:
            import traceback
            error_msg = f"Could not open the preview dialog: {e}\n\n{traceback.format_exc()}"
            self.log_message(f"❌ ERROR: {error_msg}", level=Qgis.Critical)
            QMessageBox.critical(self, "Error", error_msg)

    def update_progress_bar(self, value):
        """
        Update progress bar with dynamic text color based on fill percentage.
        
        This method has been refactored into the ProgressBarUpdater class
        for better code organization and maintainability.
        
        Args:
            value: Progress value (0-100)
        """
        return self.progress_bar_updater.update_progress_bar(value)

    def log_message(self, message, level=Qgis.Info):
        """Log a message to the QGIS Message Log, console, and upload log."""
        # Only print to console if debug mode is enabled
        if DEBUG_VERBOSE or level in [Qgis.Warning, Qgis.Critical]:
            print(message)
        QgsMessageLog.logMessage(str(message), "Q2G", level=level)
        
        # Add to upload log tracker with level for color coding
        if hasattr(self, 'log_tracker'):
            self.log_tracker.add_message(str(message), level)


# Create a plugin instance that can be used by QGIS
def classFactory(iface):
    return QGISGeoServerLayerLoader(iface)
