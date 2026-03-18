import os
import uuid
import requests
import json
import re
import math
import xml.etree.ElementTree as ET
from xml.dom import minidom
from requests.exceptions import Timeout, ConnectionError
import configparser
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socket
from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QListWidget, QPushButton, 
    QSplitter, QTreeWidget, QTreeWidgetItem, QLabel, QLineEdit, 
    QWidget, QCheckBox, QAbstractItemView, QMessageBox, QSlider,
    QTextEdit, QApplication, QListWidgetItem, QComboBox, QRadioButton, QButtonGroup,
    QGroupBox, QGridLayout
)
try:
    from .left_panel import LeftPanel
    from .right_panel import RightPanel
    from .pyqtwebengine_installer import PyQtWebEngineInstallerDialog
    from .master_layer_visibility_checkbox import MasterLayerVisibilityHandler
except ImportError:
    # Fallback for direct execution
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from left_panel import LeftPanel
    from right_panel import RightPanel
    from pyqtwebengine_installer import PyQtWebEngineInstallerDialog
    from master_layer_visibility_checkbox import MasterLayerVisibilityHandler
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QUrl
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    from PyQt5.QtWebChannel import QWebChannel
    WEBENGINE_AVAILABLE = True
except ImportError as e:
    print(f"DEBUG: QtWebEngineWidgets not available: {e}")
    WEBENGINE_AVAILABLE = False
    QWebEngineView = None
    QWebChannel = None
from qgis.core import QgsApplication, QgsMessageLog, Qgis, QgsSettings

# Import Qt resources for local libraries
try:
    from . import libs
except ImportError:
    pass

class LocalLibraryServer:
    """Simple HTTP server to serve local OpenLayers library files."""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.server = None
        self.thread = None
        self.port = None
    
    def start(self, libs_dir, port=None):
        """Start the HTTP server for local libraries."""
        if self.server is not None:
            print(f"✅ Local library server already running on port {self.port}")
            return self.port  # Already running
        
        try:
            # Use provided port or find an available one
            if port is None:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('127.0.0.1', 0))
                self.port = sock.getsockname()[1]
                sock.close()
            else:
                self.port = port
            
            # Create handler with the libs directory
            handler = self._create_handler(libs_dir)
            self.server = HTTPServer(('127.0.0.1', self.port), handler)
            
            # Start server in background thread
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.daemon = True
            self.thread.start()
            
            print(f"✅ Local library server started on http://127.0.0.1:{self.port}")
            print(f"📁 Serving files from: {libs_dir}")
            return self.port
        except Exception as e:
            print(f"❌ Error starting local library server: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_handler(self, libs_dir):
        """Create a request handler for the specified directory."""
        class LocalLibraryHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=libs_dir, **kwargs)
            
            def log_message(self, format, *args):
                pass  # Suppress logging
        
        return LocalLibraryHandler
    
    def stop(self):
        """Stop the HTTP server."""
        if self.server:
            self.server.shutdown()
            self.server = None
            self.thread = None
            self.port = None

class LayerLoadingThread(QThread):
    """Worker thread to load layers from GeoServer asynchronously."""
    layers_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, url, username, password, parent=None):
        super().__init__(parent)
        self.geoserver_url = url
        self.username = username
        self.password = password
        self.log_messages = []

    def log_message(self, message):
        self.log_messages.append(message)

    def run(self):
        """Execute the layer loading task."""
        all_layers = []
        try:
            self.log_message("Starting layer loading thread.")
            all_layers = self._load_all_layers_from_rest()
            self.log_message(f"Finished loading. Total layers found: {len(all_layers)}")
            self.layers_loaded.emit(all_layers)

        except Exception as e:
            self.log_message(f"An error occurred in the loading thread: {e}")
            self.error_occurred.emit(str(e))

    def _load_all_layers_from_rest(self):
        self.log_message("Fetching layers from all workspaces...")
        all_layers = []
        
        try:
            # First, get all workspaces
            workspaces_response = requests.get(f"{self.geoserver_url}/rest/workspaces.xml", auth=(self.username, self.password), headers={"Accept": "application/xml"}, timeout=10)
            if workspaces_response.status_code != 200:
                self.log_message(f"Failed to fetch workspaces. Status: {workspaces_response.status_code}")
                return all_layers
            
            workspaces_root = ET.fromstring(workspaces_response.content)
            workspaces = [ws.text for ws in workspaces_root.findall('.//workspace/name') if ws.text]
            self.log_message(f"Found {len(workspaces)} workspaces: {workspaces}")
            
            # Fetch layers from each workspace
            for workspace in workspaces:
                self.log_message(f"Fetching layers for workspace: {workspace}...")
                try:
                    ws_response = requests.get(f"{self.geoserver_url}/rest/workspaces/{workspace}/layers.xml", auth=(self.username, self.password), headers={"Accept": "application/xml"}, timeout=10)
                    if ws_response.status_code == 200:
                        ws_root = ET.fromstring(ws_response.content)
                        for layer in ws_root.findall('.//layer/name'):
                            if layer.text:
                                actual_layer_name = f"{workspace}:{layer.text}"
                                display_name = actual_layer_name
                                layer_info = {'display_name': display_name, 'actual_name': actual_layer_name, 'layer_type': 'Unknown'}
                                try:
                                    detail_response = requests.get(f"{self.geoserver_url}/rest/workspaces/{workspace}/layers/{layer.text}.xml", auth=(self.username, self.password), headers={"Accept": "application/xml"}, timeout=10)
                                    if detail_response.status_code == 200:
                                        detail_root = ET.fromstring(detail_response.content)
                                        type_elem = detail_root.find('.//type')
                                        if type_elem is not None:
                                            layer_info['layer_type'] = type_elem.text
                                except Exception as detail_error:
                                    self.log_message(f"Could not fetch details for {actual_layer_name}: {detail_error}")
                                all_layers.append(layer_info)
                    else:
                        self.log_message(f"Failed to fetch layers for workspace {workspace}. Status: {ws_response.status_code}")
                except Exception as e:
                    self.log_message(f"Error loading layers from workspace {workspace}: {e}")
                    
        except Exception as e:
            self.log_message(f"Error loading layers from REST API: {e}")
        
        return all_layers


class PreviewDialog(QDialog):
    """Dialog for OpenLayers map preview of GeoServer WMS layers."""
    
    def __init__(self, parent=None, geoserver_url=None, username=None, password=None, workspace=None, plugin_dir=None):
        super().__init__(parent)
        # Set window flags BEFORE anything else
        self.setWindowFlags(Qt.Window | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle("Q2G Layer Preview")
        self.resize(1200, 700)
        self.setMinimumSize(800, 600)
        
        # Keep reference to parent to prevent garbage collection
        self._parent_ref = parent
        
        self.geoserver_url = geoserver_url
        self.username = username
        self.password = password
        self.workspace = workspace
        self.plugin_dir = plugin_dir or os.path.dirname(os.path.abspath(__file__))
        self.added_layers = {}
        self.all_layers = []
        self.sort_order = 'asc'
        self.loading_thread = None
        self.error = None
        self.is_webview_loading = True
        self._js_call_queue = []
        self._reload_after_library_change = False  # Flag for library mode toggle
        self.pending_search_text = ""  # Store search text to apply after loading
        self.init_theme_state()
        
    def log_message(self, message, level=Qgis.Info):
        QgsMessageLog.logMessage(message, "Q2G", level=level)
        
    def init_theme_state(self):
        try:
            current_theme = QgsApplication.themeName()
            self.is_dark_theme = 'dark' in QgsSettings().value('qgis/theme', 'default', type=str).lower()
        except Exception:
            self.is_dark_theme = False
    
    def _run_diagnostics(self):
        """
        Run diagnostics to check if all components are available.
        
        Returns:
            bool: True if all checks pass, False otherwise
        """
        issues = []
        webengine_missing = False
        
        # Check 1: WebEngine availability
        try:
            from PyQt5.QtWebEngineWidgets import QWebEngineView
            from PyQt5.QtWebChannel import QWebChannel
            self.log_message("✓ WebEngine components available")
        except ImportError as e:
            webengine_missing = True
            issues.append(f"❌ WebEngine not available: No module named 'PyQt5.QtWebEngineWidgets'")
        
        # Check 2: Panel modules
        try:
            from .left_panel import LeftPanel
            from .right_panel import RightPanel
            self.log_message("✓ Panel modules available")
        except ImportError as e:
            issues.append(f"❌ Panel modules missing: {e}")
        
        # Check 3: Connection details
        if not self.geoserver_url:
            issues.append("❌ GeoServer URL missing")
        else:
            self.log_message(f"✓ GeoServer URL: {self.geoserver_url}")
        
        if not self.username or not self.password:
            issues.append("❌ GeoServer credentials missing")
        else:
            self.log_message("✓ GeoServer credentials provided")
        
        # Check 4: Workspace
        if not self.workspace:
            issues.append("❌ Workspace not specified")
        else:
            self.log_message(f"✓ Workspace: {self.workspace}")
        
        # Report results
        if issues:
            self.log_message("🚨 Preview Dialog Issues Found:")
            for issue in issues:
                self.log_message(issue)
            
            # If WebEngine is missing, show installer dialog
            if webengine_missing:
                dialog = PyQtWebEngineInstallerDialog(self.parent())
                dialog.exec_()
                # After dialog closes, return False (user needs to restart QGIS)
                return False
            else:
                # For other issues, show warning
                QMessageBox.warning(self.parent(), "Preview Issues", 
                                  "Preview dialog cannot be opened due to missing requirements:\n\n" + 
                                  "\n".join(issues))
                return False
        else:
            self.log_message("✅ All preview dialog checks passed")
            return True
        
    def open_openlayers_preview(self):
        self.log_message("🎬 Opening OpenLayers preview dialog...")
        
        # Run diagnostics first
        self.log_message("🔍 Running diagnostics...")
        if not self._run_diagnostics():
            self.log_message("❌ Diagnostics failed", level=Qgis.Critical)
            return False
        self.log_message("✅ Diagnostics passed")
        
        try:
            self.log_message("⚙️ Window already configured in __init__")

            if not all([self.geoserver_url, self.username, self.password]):
                self.error = "GeoServer connection details are missing."
                self.log_message(f"❌ {self.error}", level=Qgis.Critical)
                QMessageBox.warning(self.parent(), "Input Error", self.error)
                return False
            self.log_message("✅ Connection details verified")

            self.log_message("🧹 Clearing existing layout if present...")
            if self.layout() is not None:
                while self.layout().count():
                    item = self.layout().takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
                try:
                    import sip
                    sip.delete(self.layout())
                except (ImportError, RuntimeError):
                    self.setLayout(None)
            self.log_message("✅ Layout cleared")

            self.log_message("📐 Creating main layout and splitter...")
            layout = QHBoxLayout()
            splitter = QSplitter(Qt.Horizontal)
            self.log_message("✅ Layout and splitter created")
            
            self.log_message("🔨 Creating left panel...")
            try:
                left_widget = LeftPanel(self.plugin_dir, self.is_dark_theme, self)
                self.log_message("✅ Left panel created")
            except Exception as e:
                self.log_message(f"❌ Error creating left panel: {e}", level=Qgis.Critical)
                import traceback
                self.log_message(traceback.format_exc(), level=Qgis.Critical)
                return False
            
            self.log_message("🔗 Connecting left panel signals...")
            try:
                left_widget.connect_signals(self)
                self.log_message("✅ Left panel signals connected")
            except Exception as e:
                self.log_message(f"❌ Error connecting left panel signals: {e}", level=Qgis.Critical)
                import traceback
                self.log_message(traceback.format_exc(), level=Qgis.Critical)
                return False
            
            # Store references to left panel widgets for backward compatibility
            self.load_layers_button = left_widget.load_layers_button
            self.layers_list = left_widget.layers_list
            self.search_box = left_widget.search_box
            self.header_label = left_widget.header_label
            self.added_layers_tree = left_widget.added_layers_tree
            self.rb_wms = left_widget.rb_wms
            self.rb_wfs = left_widget.rb_wfs
            self.rb_wmts = left_widget.rb_wmts
            self.rb_base_none = left_widget.rb_base_none
            self.rb_base_light = left_widget.rb_base_light
            self.rb_base_dark = left_widget.rb_base_dark
            self.select_all_layers_checkbox = left_widget.select_all_layers_checkbox
            self.log_message("✅ Left panel references stored")
            
            # Initialize the master layer visibility handler
            self.master_visibility_handler = MasterLayerVisibilityHandler(self)
            
            self.log_message("🗺️ Creating map panel...")
            try:
                map_widget = self._create_map_panel()
                self.log_message("✅ Map panel created")
            except Exception as e:
                self.log_message(f"❌ Error creating map panel: {e}", level=Qgis.Critical)
                import traceback
                self.log_message(traceback.format_exc(), level=Qgis.Critical)
                return False
            
            self.log_message("🔨 Creating right panel...")
            try:
                right_widget = RightPanel(self.is_dark_theme, self, self.plugin_dir)
                self.log_message("✅ Right panel created")
            except Exception as e:
                self.log_message(f"❌ Error creating right panel: {e}", level=Qgis.Critical)
                import traceback
                self.log_message(traceback.format_exc(), level=Qgis.Critical)
                return False
            
            self.log_message("🔗 Connecting right panel signals...")
            try:
                right_widget.connect_signals(self)
                self.log_message("✅ Right panel signals connected")
            except Exception as e:
                self.log_message(f"❌ Error connecting right panel signals: {e}", level=Qgis.Critical)
                import traceback
                self.log_message(traceback.format_exc(), level=Qgis.Critical)
                return False
            
            # Store references to right panel widgets for backward compatibility
            self.control_checkboxes = right_widget.control_checkboxes
            self.log_message("✅ Right panel references stored")
            
            self.log_message("🧩 Adding widgets to splitter...")
            try:
                splitter.addWidget(left_widget)
                splitter.addWidget(map_widget)
                splitter.addWidget(right_widget)
                # Set initial sizes: left=450px (fully expanded), map=auto, right=300px
                splitter.setSizes([450, 550, 300])
                self.log_message("✅ Widgets added to splitter (L:450px, M:550px, R:300px)")
            except Exception as e:
                self.log_message(f"❌ Error adding widgets to splitter: {e}", level=Qgis.Critical)
                import traceback
                self.log_message(traceback.format_exc(), level=Qgis.Critical)
                return False
            
            # Store splitter reference and connect to size changes
            self.splitter = splitter
            self.right_panel = right_widget
            splitter.splitterMoved.connect(self._on_splitter_moved)
            
            self.log_message("📦 Adding splitter to layout...")
            try:
                layout.addWidget(splitter)
                self.setLayout(layout)
                self.log_message("✅ Layout set")
            except Exception as e:
                self.log_message(f"❌ Error setting layout: {e}", level=Qgis.Critical)
                import traceback
                self.log_message(traceback.format_exc(), level=Qgis.Critical)
                return False
            
            
            # Set up web channel BEFORE loading HTML to avoid race conditions in JS initialization
            self.log_message("📡 Setting up web channel...")
            try:
                self.setup_web_channel()
                self.log_message("✅ Web channel setup complete")
            except Exception as e:
                self.log_message(f"❌ Error setting up web channel: {e}", level=Qgis.Critical)
                import traceback
                self.log_message(traceback.format_exc(), level=Qgis.Critical)
                return False
            
            self.log_message("🗺️ Initializing OpenLayers map...")
            try:
                self.initialize_openlayers_map(self.web_view)
                self.log_message("✅ OpenLayers map initialized")
            except Exception as e:
                self.log_message(f"❌ Error initializing OpenLayers map: {e}", level=Qgis.Critical)
                import traceback
                self.log_message(traceback.format_exc(), level=Qgis.Critical)
                return False
            
            # Load saved base map mode from ini file
            self.log_message("📂 Loading saved base map mode...")
            try:
                self._load_saved_base_map_mode()
                self.log_message("✅ Base map mode loaded")
            except Exception as e:
                self.log_message(f"❌ Error loading base map mode: {e}", level=Qgis.Critical)
                import traceback
                self.log_message(traceback.format_exc(), level=Qgis.Critical)
                return False
            
            self.log_message("👁️ Showing dialog...")
            try:
                # Center dialog on screen
                from qgis.PyQt.QtWidgets import QApplication
                screen = QApplication.primaryScreen()
                screen_geometry = screen.availableGeometry()
                x = (screen_geometry.width() - self.width()) // 2
                y = (screen_geometry.height() - self.height()) // 2
                self.move(x, y)
                self.log_message("✅ Dialog centered on screen")
                
                # Show the dialog (non-blocking)
                self.show()
                self.log_message("✅ Dialog show() called successfully")
                
                # Ensure dialog is visible and on top
                from PyQt5.QtCore import QTimer
                
                # Initialize the select all checkbox state
                QTimer.singleShot(200, self.update_select_all_checkbox_state)
                QTimer.singleShot(100, lambda: self.raise_() if self.isVisible() else None)
                QTimer.singleShot(100, lambda: self.activateWindow() if self.isVisible() else None)
                
            except Exception as e:
                import traceback
                self.log_message(f"❌ Error calling show(): {e}", level=Qgis.Critical)
                self.log_message(traceback.format_exc(), level=Qgis.Critical)
                return False
            
            self.log_message("✅✅✅ Preview dialog opened successfully!")
            return self
        except Exception as e:
            import traceback
            self.error = str(e)
            error_details = traceback.format_exc()
            self.log_message(f"❌ Error opening preview dialog: {self.error}\n{error_details}", level=Qgis.Critical)
            return False

    # This method is no longer used - replaced by LeftPanel class
    # def _create_left_panel(self):

    # This method is no longer used - replaced by RightPanel class
    # def _create_right_panel(self):

    def _load_saved_base_map_mode(self):
        """Load and apply the saved base map mode from controls.ini file."""
        try:
            # Get saved base map mode from right panel
            if hasattr(self, 'right_panel') and hasattr(self.right_panel, 'saved_base_map_mode'):
                base_map_mode = self.right_panel.saved_base_map_mode
                self.log_message(f"📂 Loading saved base map mode: {base_map_mode}")
                
                # Apply the saved mode by setting the appropriate radio button
                if base_map_mode == "No base map":
                    self.rb_base_none.setChecked(True)
                elif base_map_mode == "Dark Mode":
                    self.rb_base_dark.setChecked(True)
                else:  # Default to "Light Mode"
                    self.rb_base_light.setChecked(True)
                
                self.log_message(f"✅ Base map mode applied: {base_map_mode}")
        except Exception as e:
            self.log_message(f"Error loading saved base map mode: {e}", level=Qgis.Warning)

    def _on_mode_changed(self, checked):
        # This signal fires for both radio buttons, so we only act on the one being selected.
        if not checked:
            return

        is_dark = self.rb_base_dark.isChecked()
        if is_dark != self.is_dark_theme:
            self.is_dark_theme = is_dark
            js_call = f"toggleDarkMode({str(self.is_dark_theme).lower()});"
            if self.is_webview_loading:
                self.log_message(f"Webview loading, queuing JS call: {js_call}")
                self._js_call_queue.append(js_call)
            else:
                self.web_view.page().runJavaScript(js_call)

    def _on_base_map_mode_changed(self, checked):
        """Handle Base Map Mode radios: None, Light, Dark.
        - None: hide base layer, keep current theme state.
        - Light: show base and switch to light theme.
        - Dark: show base and switch to dark theme.
        """
        if not checked:
            return

        try:
            self.log_message(f"Base map mode changed - rb_base_none: {self.rb_base_none.isChecked()}, rb_base_light: {self.rb_base_light.isChecked()}, rb_base_dark: {self.rb_base_dark.isChecked()}")
            
            # Determine the desired state from the base map radios
            if self.rb_base_none.isChecked():
                base_visible = False
                desired_dark = self.is_dark_theme  # keep current theme
                base_map_mode = "No base map"
                self.log_message("Base map mode: No base map")
            elif self.rb_base_light.isChecked():
                base_visible = True
                desired_dark = False
                base_map_mode = "Light Mode"
                self.log_message("Base map mode: Light mode")
            elif self.rb_base_dark.isChecked():
                base_visible = True
                desired_dark = True
                base_map_mode = "Dark Mode"
                self.log_message("Base map mode: Dark mode")
            else:
                self.log_message("Base map mode: No radio button selected, returning")
                return

            # Save base map mode to ini file
            try:
                self.right_panel._save_controls_state(base_map_mode=base_map_mode)
                self.log_message(f"💾 Base map mode saved: {base_map_mode}")
            except Exception as e:
                self.log_message(f"Error saving base map mode: {e}", level=Qgis.Warning)

            # Update internal theme state
            if desired_dark != self.is_dark_theme:
                self.log_message(f"Changing theme from {self.is_dark_theme} to {desired_dark}")
                self.is_dark_theme = desired_dark

            # Build and execute JS calls
            js_calls = []
            # Apply theme toggle first so base visibility uses the right layer
            js_calls.append(f"toggleDarkMode({str(self.is_dark_theme).lower()});")
            js_calls.append(f"toggleBaseLayer({str(base_visible).lower()});")

            self.log_message(f"Executing JS calls: {js_calls}")

            if self.is_webview_loading:
                for c in js_calls:
                    self._js_call_queue.append(c)
                self.log_message("Webview loading, queued JS calls")
            else:
                for c in js_calls:
                    self.web_view.page().runJavaScript(c)
                self.log_message("Executed JS calls immediately")
                
        except Exception as e:
            # Be resilient to any missing widgets during initialization
            try:
                self.log_message(f"_on_base_map_mode_changed error: {e}")
            except Exception:
                pass

    def _on_control_checkbox_changed(self, name, state):
        # Map checkbox text to OpenLayers control name
        control_map = {
            "Zoom Control": "Zoom",
            "Scale Control": "ScaleLine",
            "Layer Control": "LayerSwitcher", # Assuming a custom or extension control
            "Attribution Control": "Attribution",
            "FullScreen Control": "FullScreen",
            "Rotate Control": "Rotate",
            "ZoomSlider Control": "ZoomSlider",
            "ZoomToExtent Control": "ZoomToExtent",
            "Mouse Position Control": "MousePosition",
            "OverviewMap Control": "OverviewMap",
            "Print Control": "Print",
            "Export Control": "Export",
            "Mode Indicator": "ModeIndicator"
        }
        control_name = control_map.get(name)
        if not control_name:
            return
            
        # Special handling for Mode Indicator
        if control_name == "ModeIndicator":
            js_call = f"toggleModeIndicator({str(state == Qt.Checked).lower()});"
        else:
            if state == Qt.Checked:
                js_call = f"addControl('{control_name}');"
            else:
                js_call = f"removeControl('{control_name}');"
        

        if self.is_webview_loading:
            self.log_message(f"Webview loading, queuing JS call: {js_call}")
            self._js_call_queue.append(js_call)
        else:
            self.web_view.page().runJavaScript(js_call)

    def _create_map_panel(self):
        map_widget = QWidget()
        map_layout = QVBoxLayout()
        
        if not WEBENGINE_AVAILABLE or QWebEngineView is None:
            error_label = QLabel("❌ QtWebEngineWidgets is not available.\n\nTo fix:\n1. Open QGIS Python Console\n2. Run: import subprocess, sys; subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'PyQtWebEngine'])\n3. Restart QGIS")
            error_label.setWordWrap(True)
            map_layout.addWidget(error_label)
            map_widget.setLayout(map_layout)
            self.log_message("❌ QWebEngineView not available", level=Qgis.Critical)
            raise RuntimeError("QtWebEngineWidgets not available")
        
        self.web_view = QWebEngineView()
        self.web_view.loadFinished.connect(self.on_webview_load_finished)
        map_layout.addWidget(self.web_view)
        map_widget.setLayout(map_layout)
        return map_widget

    def start_layer_loading(self):
        """Start loading layers from GeoServer in a background thread."""
        self.log_message("🔄 Starting layer loading...")
        
        # Update UI to show loading state
        self.layers_list.clear()
        self.layers_list.addItem("🔄 Loading layers from GeoServer...")
        self.load_layers_button.setText("⏳ Loading...")
        self.load_layers_button.setEnabled(False)
        
        # Disconnect textChanged signal to prevent filter_layers from interfering
        self.search_box.textChanged.disconnect()
        
        # Start the loading thread
        self.loading_thread = LayerLoadingThread(self.geoserver_url, self.username, self.password, parent=self)
        self.loading_thread.layers_loaded.connect(self.on_layers_loaded)
        self.loading_thread.error_occurred.connect(self.on_loading_error)
        self.loading_thread.finished.connect(self.on_loading_finished)
        self.loading_thread.start()

    @pyqtSlot(list)
    def on_layers_loaded(self, layers):
        self.log_message(f"on_layers_loaded called with {len(layers)} layers")
        
        # Debug: Print layer types
        layer_types = {}
        for layer in layers:
            layer_types[layer.get('layer_type', 'Unknown')] = layer_types.get(layer.get('layer_type', 'Unknown'), 0) + 1
        self.log_message(f"Layer types received: {layer_types}")
        
        if not layers:
            self.layers_list.clear()
            self.layers_list.addItem("No layers found.")
            return

        self.all_layers = sorted(layers, key=lambda x: x['display_name'])
        self.log_message(f"Successfully loaded {len(self.all_layers)} layers.")
        
        # Get search text from search box
        search_text = self.search_box.text().strip()
        self.log_message(f"🔍 on_layers_loaded: search_box.text()='{search_text}' (len={len(search_text)})")
        
        # Clear the list
        self.layers_list.clear()
        
        # If search text exists, filter layers; otherwise show all
        if search_text:
            self.log_message(f"🔍 Search text found, filtering...")
            try:
                from wildcard_filter import WildcardFilter
            except ImportError:
                try:
                    from .wildcard_filter import WildcardFilter
                except ImportError:
                    import wildcard_filter as wf
                    WildcardFilter = wf.WildcardFilter
            
            filtered_layers = [layer for layer in self.all_layers 
                             if WildcardFilter.matches_pattern(layer['display_name'], search_text)]
            self.log_message(f"🔍 Filtered result: {len(filtered_layers)} layers match '{search_text}'")
            for layer in filtered_layers[:3]:
                self.log_message(f"  - {layer['display_name']}")
            layers_to_show = filtered_layers
        else:
            self.log_message(f"🔍 No search text, showing all {len(self.all_layers)} layers")
            layers_to_show = self.all_layers
        
        # Populate the list
        self.log_message(f"🔍 Populating list with {len(layers_to_show)} layers")
        for layer_data in layers_to_show:
            item = QListWidgetItem(layer_data['display_name'])
            item.setData(Qt.UserRole, layer_data)
            self.layers_list.addItem(item)
        
        self.log_message(f"🔍 List now contains {self.layers_list.count()} items")
        
        # Reconnect textChanged signal now that filtering is complete
        self.search_box.textChanged.connect(self.filter_layers)
        self.log_message(f"🔍 textChanged signal reconnected")

    @pyqtSlot(str)
    def on_loading_error(self, error_message):
        self.layers_list.clear()
        self.layers_list.addItem(f"Error loading layers: {error_message}")
        QMessageBox.warning(self, "Layer Loading Error", error_message)

    @pyqtSlot()
    def on_loading_finished(self):
        self.log_message("Layer loading thread has finished.")
        
        # Reset the load button state
        self.load_layers_button.setText("🔄 Load Layers from GeoServer")
        self.load_layers_button.setEnabled(True)
        
        if self.loading_thread:
            for msg in self.loading_thread.log_messages:
                self.log_message(f"ThreadLog: {msg}")
            self.loading_thread.deleteLater()
            self.loading_thread = None

    def initialize_openlayers_map(self, web_view):
        """Initialize the OpenLayers map in the web view."""
        # Correctly escape braces for f-string formatting.
        # Python's f-string uses {{ and }} to represent literal braces.
        # JavaScript template literals `${...}` need to be escaped if they are inside an f-string.
        # Since we are not using python variables inside the JS template literals, we can just use them as is.
        
        # Determine library mode (Local or CDN)
        library_mode = 'CDN'  # Default
        self.use_local_libs = False  # Track if we're using local libraries
        try:
            if hasattr(self, 'right_panel') and self.right_panel:
                library_mode = self.right_panel.get_library_mode()
                self.log_message(f"📚 Library mode detected: {library_mode}")
            else:
                self.log_message(f"⚠️ Right panel not available, using default CDN")
        except Exception as e:
            self.log_message(f"⚠️ Could not determine library mode, using CDN: {e}")
        
        # Generate appropriate library links based on mode
        if library_mode == 'Local':
            # Use local OpenLayers files with absolute file:// paths
            import os
            libs_dir = os.path.join(self.plugin_dir, 'libs', 'openlayers')
            ol_css_file = os.path.join(libs_dir, 'ol.css')
            ol_js_file = os.path.join(libs_dir, 'ol.js')
            
            # Validate files exist
            if not os.path.exists(ol_css_file):
                self.log_message(f"⚠️ Local CSS file not found: {ol_css_file}, falling back to CDN")
                library_mode = 'CDN'
            elif not os.path.exists(ol_js_file):
                self.log_message(f"⚠️ Local JS file not found: {ol_js_file}, falling back to CDN")
                library_mode = 'CDN'
            else:
                # Start HTTP server to serve local libraries
                self.log_message(f"📂 Local libraries folder: {libs_dir}")
                
                # List files in the local folder for verification
                try:
                    local_files = os.listdir(libs_dir)
                    self.log_message(f"📋 Files in local folder ({len(local_files)} items): {', '.join(local_files[:5])}{'...' if len(local_files) > 5 else ''}")
                except Exception as e:
                    self.log_message(f"⚠️ Could not list local folder: {e}")
                
                server = LocalLibraryServer()
                # Get port from right panel if available
                port = None
                try:
                    if hasattr(self, 'right_panel') and self.right_panel:
                        port = self.right_panel.get_local_server_port()
                except Exception as e:
                    self.log_message(f"⚠️ Could not get port from right panel: {e}")
                
                self.log_message(f"🚀 Starting HTTP server on port {port or 'auto'}...")
                port = server.start(libs_dir, port)
                if port:
                    # Verify server is actually responding
                    try:
                        import time
                        time.sleep(0.2)  # Give server time to start
                        test_url = f"http://127.0.0.1:{port}/openlayers/ol.js"
                        response = requests.head(test_url, timeout=2)
                        if response.status_code == 200:
                            # Server is responding, use it
                            ol_css_link = f'<link rel="stylesheet" href="http://127.0.0.1:{port}/openlayers/ol.css" type="text/css">'
                            ol_js_link = f'<script src="http://127.0.0.1:{port}/openlayers/ol.js"></script>'
                            self.use_local_libs = True
                            self.log_message(f"✅ HTTP server started successfully on port {port}")
                            self.log_message(f"✅ Server is responding to requests")
                            self.log_message(f"📁 Using LOCAL OpenLayers library (NOT CDN)")
                            self.log_message(f"📁 Server URL: http://127.0.0.1:{port}/openlayers/")
                            self.log_message(f"📁 Serving from: {libs_dir}")
                            self.log_message(f"📁 CSS URL: http://127.0.0.1:{port}/openlayers/ol.css")
                            self.log_message(f"📁 JS URL: http://127.0.0.1:{port}/openlayers/ol.js")
                        else:
                            # Server not responding properly
                            self.log_message(f"❌ Local server not responding (HTTP {response.status_code}), falling back to CDN")
                            library_mode = 'CDN'
                    except Exception as e:
                        # Server test failed
                        self.log_message(f"❌ Local server test failed: {e}, falling back to CDN")
                        library_mode = 'CDN'
                else:
                    # Fallback to CDN if server fails to start
                    self.log_message(f"❌ Failed to start local library server, falling back to CDN")
                    library_mode = 'CDN'
        
        if library_mode == 'CDN':
            # Use CDN OpenLayers files
            ol_css_link = '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/openlayers/openlayers.github.io@master/en/v6.5.0/css/ol.css" type="text/css">'
            ol_js_link = '<script src="https://cdn.jsdelivr.net/gh/openlayers/openlayers.github.io@master/en/v6.5.0/build/ol.js"></script>'
            self.log_message("☁️ Using CDN OpenLayers library (from internet)")
            self.log_message("☁️ CSS URL: https://cdn.jsdelivr.net/gh/openlayers/openlayers.github.io@master/en/v6.5.0/css/ol.css")
            self.log_message("☁️ JS URL: https://cdn.jsdelivr.net/gh/openlayers/openlayers.github.io@master/en/v6.5.0/build/ol.js")
        
        # Add library mode indicator to HTML content with a unique ID
        # Position it higher to avoid overlapping with contribution controls
        library_indicator = f'''
        <div id="library-mode-indicator" style="position: absolute; bottom: 70px; right: 10px; background: rgba(0,0,0,0.6); 
                                               color: white; padding: 5px 10px; border-radius: 4px; font-size: 12px; 
                                               font-family: Arial, sans-serif; z-index: 1000; pointer-events: none; display: block;">
            {'🌐 CDN Mode' if library_mode == 'CDN' else '📂 Local Mode'}
        </div>
        '''
        
        # Add JavaScript function to update the library mode indicator
        update_indicator_js = '''
        function updateLibraryModeIndicator(mode) {
            var indicator = document.getElementById('library-mode-indicator');
            if (indicator) {
                indicator.innerHTML = mode === 'CDN' ? '🌐 CDN Mode' : '📂 Local Mode';
            }
        }
        '''
        
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>GeoServer Layer Preview</title>
            <!-- OpenLayers (Local or CDN) -->
            {ol_css_link}
            {ol_js_link}
            
            <!-- Qt Web Channel -->
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <style>
                html, body, #map {{ margin: 0; padding: 0; width: 100%; height: 100%; }}
                /* Rulers & Guides */
                #overlay-container {{ position: absolute; top: 0; left: 0; right: 0; bottom: 0; pointer-events: none; }}
                #ruler-top {{ position: absolute; top: 0; left: 0; right: 0; height: 18px; background: #f0f0f0; border-bottom: 1px solid #ccc; display: none; pointer-events: auto; z-index: 1000; }}
                #ruler-left {{ position: absolute; top: 0; left: 0; bottom: 0; width: 18px; background: #f0f0f0; border-right: 1px solid #ccc; display: none; pointer-events: auto; z-index: 1000; }}
                #guide-container {{ position: absolute; top: 0; left: 0; right: 0; bottom: 0; z-index: 999; pointer-events: none; }}
                .guide-h {{ position: absolute; left: 0; right: 0; height: 1px; background: #ff0000; opacity: 0.8; pointer-events: auto; cursor: ns-resize; }}
                .guide-v {{ position: absolute; top: 0; bottom: 0; width: 1px; background: #ff0000; opacity: 0.8; pointer-events: auto; cursor: ew-resize; }}
                .ruler-tick {{ position: absolute; width: 1px; background: #bbb; height: 6px; bottom: 0; }}
                .ruler-tick-left {{ position: absolute; height: 1px; background: #bbb; width: 6px; right: 0; }}
            </style>
        </head>
        <body>
            <div id="map" class="map" style="position: relative;"></div>
            <div id="overlay-container">
                <div id="ruler-top"></div>
                <div id="ruler-left"></div>
                <div id="guide-container"></div>
            </div>
            {library_indicator}
            <script type="text/javascript">
            // Function to update library mode indicator
            function toggleModeIndicator(visible) {{
                var indicator = document.getElementById('library-mode-indicator');
                if (indicator) {{
                    indicator.style.display = visible ? 'block' : 'none';
                }}
            }}
            
            function updateLibraryModeIndicator(mode) {{
                var indicator = document.getElementById('library-mode-indicator');
                if (indicator) {{
                    indicator.innerHTML = mode === 'CDN' ? '🌐 CDN Mode' : '📂 Local Mode';
                }}
            }}
            
            // Report JS errors back to Python via QWebChannel backend
            window.onerror = function(message, source, lineno, colno, error) {{
                try {{
                    if (window.backend && window.backend.log_message) {{
                        window.backend.log_message('JS Error: ' + message + ' at ' + source + ':' + lineno + ':' + colno);
                    }}
                }} catch (e) {{}}
            }};
            window.addEventListener('unhandledrejection', function(event) {{
                try {{
                    if (window.backend && window.backend.log_message) {{
                        window.backend.log_message('Unhandled Promise Rejection: ' + (event.reason && (event.reason.stack || event.reason)));
                    }}
                }} catch (e) {{}}
            }});
                var base_layer_light = new ol.layer.Tile({{ 
                    source: new ol.source.OSM(),
                    attribution: '© OpenStreetMap contributors'
                }});
                var base_layer_dark = new ol.layer.Tile({{ 
                    source: new ol.source.XYZ({{ 
                        url: 'https://{{a-c}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}.png',
                        attributions: '© CartoDB contributors, © OpenStreetMap contributors'
                    }}) 
                }});
                base_layer_dark.setVisible(false);

                var map = new ol.Map({{ 
                    target: 'map',
                    layers: [base_layer_light, base_layer_dark],
                    // Disable default controls so none appear until explicitly added via checkboxes
                    controls: [],
                    view: new ol.View({{ 
                        center: [0, 0],
                        zoom: 2
                    }})
                }});

                window.ol_map = map;
                window.ol_layers = {{}};
                window.ol_controls = {{}};
                window.is_dark_theme = {str(self.is_dark_theme).lower()};

                new QWebChannel(qt.webChannelTransport, function (channel) {{
                    window.backend = channel.objects.backend;
                }});


                function addWmsLayer(url, layerName, layerId, title) {{
                    try {{
                        var wmsLayer = new ol.layer.Tile({{
                            source: new ol.source.TileWMS({{
                                url: url,
                                params: {{'LAYERS': layerName, 'TILED': true}},
                                serverType: 'geoserver',
                                transition: 0,
                                crossOrigin: 'anonymous'
                            }})
                        }});
                        wmsLayer.set('id', layerId);
                        if (title) wmsLayer.set('title', title);
                        map.addLayer(wmsLayer);
                        window.ol_layers[layerId] = wmsLayer;
                        if (window.backend && window.backend.log_message) {{
                            window.backend.log_message('✅ WMS layer added: ' + layerId);
                        }}
                        refreshLayerSwitcher();
                    }} catch (e) {{
                        if (window.backend && window.backend.log_message) {{
                            window.backend.log_message('❌ Error adding WMS layer ' + layerId + ': ' + e.message);
                        }}
                    }}
                }}

                function addWfsLayer(url, layerName, layerId, title) {{
                    try {{
                        var wfsLayer = new ol.layer.Vector({{
                            source: new ol.source.Vector({{
                                format: new ol.format.GeoJSON(),
                                url: function(extent) {{
                                    return `${{url}}?service=WFS&version=1.1.0&request=GetFeature&typename=${{layerName}}&outputFormat=application/json&srsname=EPSG:3857&bbox=${{extent.join(',')}},EPSG:3857`;
                                }},
                                strategy: ol.loadingstrategy.bbox
                            }})
                        }});
                        wfsLayer.set('id', layerId);
                        if (title) wfsLayer.set('title', title);
                        map.addLayer(wfsLayer);
                        window.ol_layers[layerId] = wfsLayer;
                        if (window.backend && window.backend.log_message) {{
                            window.backend.log_message('✅ WFS layer added: ' + layerId);
                        }}
                        refreshLayerSwitcher();
                    }} catch (e) {{
                        if (window.backend && window.backend.log_message) {{
                            window.backend.log_message('❌ Error adding WFS layer ' + layerId + ': ' + e.message);
                        }}
                    }}
                }}

                function addWmtsLayer(url, layerName, layerId, title) {{
                    try {{
                        fetch(url + '?request=GetCapabilities').then(function(response) {{
                            return response.text();
                        }}).then(function(text) {{
                            try {{
                                var parser = new ol.format.WMTSCapabilities();
                                var result = parser.read(text);
                                var options = ol.source.WMTS.optionsFromCapabilities(result, {{
                                    layer: layerName,
                                    matrixSet: 'EPSG:900913'
                                }});
                                var wmtsLayer = new ol.layer.Tile({{ source: new ol.source.WMTS(options) }});
                                wmtsLayer.set('id', layerId);
                                if (title) wmtsLayer.set('title', title);
                                map.addLayer(wmtsLayer);
                                window.ol_layers[layerId] = wmtsLayer;
                                if (window.backend && window.backend.log_message) {{
                                    window.backend.log_message('✅ WMTS layer added: ' + layerId);
                                }}
                                refreshLayerSwitcher();
                            }} catch (e) {{
                                if (window.backend && window.backend.log_message) {{
                                    window.backend.log_message('❌ Error parsing WMTS capabilities for ' + layerId + ': ' + e.message);
                                }}
                            }}
                        }}).catch(function(error) {{
                            if (window.backend && window.backend.log_message) {{
                                window.backend.log_message('❌ Error fetching WMTS capabilities for ' + layerId + ': ' + error.message);
                            }}
                        }});
                    }} catch (e) {{
                        if (window.backend && window.backend.log_message) {{
                            window.backend.log_message('❌ Error adding WMTS layer ' + layerId + ': ' + e.message);
                        }}
                    }}
                }}

                function setLayerOpacity(layerId, opacity) {{
                    if (window.ol_layers[layerId]) {{
                        window.ol_layers[layerId].setOpacity(opacity);
                    }}
                }}

                function toggleLayerVisibility(layerId, visible) {{
                    if (window.ol_layers[layerId]) {{
                        window.ol_layers[layerId].setVisible(visible);
                        refreshLayerSwitcher();
                    }}
                }}

                function clearMap() {{
                    Object.values(window.ol_layers).forEach(layer => map.removeLayer(layer));
                    window.ol_layers = {{}};
                    refreshLayerSwitcher();
                }}

                function zoomToLayer(extent, crs) {{
                    if (extent && extent.length === 4) {{
                        try {{
                            var sourceCrs = crs || 'EPSG:4326';
                            var viewProj = map.getView().getProjection();
                            var viewCode = viewProj ? viewProj.getCode() : 'EPSG:3857';
                            var fitExtent = extent;
                            if (sourceCrs && viewCode && sourceCrs !== viewCode) {{
                                fitExtent = ol.proj.transformExtent(extent, sourceCrs, viewCode);
                            }}
                            map.getView().fit(fitExtent, {{ duration: 1000, padding: [50, 50, 50, 50] }});
                        }} catch (e) {{
                            map.getView().fit(extent, {{ duration: 1000, padding: [50, 50, 50, 50] }});
                        }}
                    }}
                }}

                function toggleBaseLayer(visible) {{
                    base_layer_light.setVisible(visible && !window.is_dark_theme);
                    base_layer_dark.setVisible(visible && window.is_dark_theme);
                }}

                function toggleDarkMode(is_dark) {{
                    window.is_dark_theme = is_dark;
                    if (base_layer_light.getVisible() || base_layer_dark.getVisible()) {{
                        base_layer_light.setVisible(!is_dark);
                        base_layer_dark.setVisible(is_dark);
                    }}
                }}

                function refreshLayerOrder(layerIds) {{
                    layerIds.forEach((id, index) => {{
                        const layer = window.ol_layers[id];
                        if (layer) {{
                            layer.setZIndex(index + 2);
                        }}
                    }});
                    window._layerOrder = layerIds.slice();
                    refreshLayerSwitcher();
                }}

                function getMapView() {{
                    var view = map.getView();
                    return {{
                        center: view.getCenter(),
                        zoom: view.getZoom(),
                        extent: view.calculateExtent(map.getSize())
                    }};
                }}

                // Apply map view (center and zoom) from Python
                function setMapView(center, zoom) {{
                    try {{
                        var view = map.getView();
                        if (Array.isArray(center) && center.length === 2 && isFinite(center[0]) && isFinite(center[1])) {{
                            view.setCenter(center);
                        }}
                        if (typeof zoom === 'number' && isFinite(zoom)) {{
                            view.setZoom(zoom);
                        }}
                    }} catch (e) {{
                        if (window.backend && window.backend.log_message) {{
                            window.backend.log_message('JS Error in setMapView: ' + e.message);
                        }}
                    }}
                }}

                function addControl(controlName) {{
                    if (window.ol_controls[controlName]) return;
                    var control;
                    switch (controlName) {{
                        case 'Zoom': control = new ol.control.Zoom(); break;
                        case 'ScaleLine': control = new ol.control.ScaleLine(); break;
                        case 'Attribution': control = new ol.control.Attribution(); break;
                        case 'FullScreen': control = new ol.control.FullScreen(); break;
                        case 'Rotate': control = new ol.control.Rotate(); break;
                        case 'ZoomSlider': control = new ol.control.ZoomSlider(); break;
                        case 'ZoomToExtent': control = new ol.control.ZoomToExtent(); break;
                        case 'MousePosition': control = createMousePositionControl(); break;
                        case 'OverviewMap': 
                            control = new ol.control.OverviewMap({{
                                layers: [new ol.layer.Tile({{
                                    source: new ol.source.OSM()
                                }})]
                            }});
                            // Move OverviewMap up significantly to avoid overlapping with ScaleLine
                            if (control && control.element) {{
                                setTimeout(function() {{
                                    const el = control.element;
                                    if (el) {{
                                        el.style.bottom = '35px';
                                    }}
                                }}, 100);
                            }}
                            break;
                        case 'LayerSwitcher': control = createLayerSwitcherControl(); break;
                        case 'Print': control = createPrintControl(); break;
                        case 'Export': control = createExportControl(); break;
                    }}
                    if (control) {{
                        map.addControl(control);
                        window.ol_controls[controlName] = control;
                        if (controlName === 'LayerSwitcher') {{
                            refreshLayerSwitcher();
                        }}
                    }}
                }}

                function removeControl(controlName) {{
                    if (window.ol_controls[controlName]) {{
                        // Special cleanup for certain custom controls
                        if (controlName === 'MousePosition') {{
                            removeMousePositionControl();
                            delete window.ol_controls[controlName];
                            return;
                        }}
                        if (controlName === 'Print') {{
                            removePrintControl();
                            delete window.ol_controls[controlName];
                            return;
                        }}
                        if (controlName === 'Export') {{
                            removeExportControl();
                            delete window.ol_controls[controlName];
                            return;
                        }}
                        map.removeControl(window.ol_controls[controlName]);
                        delete window.ol_controls[controlName];
                        if (controlName === 'LayerSwitcher') {{
                            // Nothing else needed; DOM element is already removed by OL.
                        }}
                    }}
                }}

                // Custom Mouse Position Control (WGS84 lat/long with styling)
                let mousePosControl = null;
                let mousePosMoveFn = null;
                function createMousePositionControl() {{
                    if (mousePosControl) return mousePosControl;
                    try {{
                        const container = document.createElement('div');
                        container.className = 'ol-control ol-unselectable';
                        container.style.cssText = 'position:absolute; left:50%; bottom:8px; transform:translateX(-50%); z-index:9999;';
                        const panel = document.createElement('div');
                        panel.style.cssText = 'background:rgba(30,30,30,0.8); color:#fff; font: 12px \"Segoe UI\", Roboto, \"Helvetica Neue\", Arial, sans-serif; padding:4px 8px; border-radius:4px; box-shadow:0 2px 6px rgba(0,0,0,0.3);';
                        const label = document.createElement('span');
                        label.textContent = 'Lat: –, Lon: –';
                        panel.appendChild(label);
                        container.appendChild(panel);
                        mousePosMoveFn = function(evt) {{
                            try {{
                                if (!evt || !evt.coordinate) return;
                                const coord = ol.proj.transform(evt.coordinate, map.getView().getProjection(), 'EPSG:4326');
                                const lon = coord[0];
                                const lat = coord[1];
                                const fmt = function(v) {{ return isFinite(v) ? v.toFixed(5) : '–'; }};
                                label.textContent = 'Lat: ' + fmt(lat) + ', Lon: ' + fmt(lon);
                            }} catch (e) {{}}
                        }};
                        map.on('pointermove', mousePosMoveFn);
                        // Clear when pointer leaves map
                        map.getViewport().addEventListener('mouseout', function() {{
                            label.textContent = 'Lat: –, Lon: –';
                        }});
                        mousePosControl = new ol.control.Control({{ element: container }});
                        return mousePosControl;
                    }} catch (e) {{
                        mousePosControl = null;
                        return null;
                    }}
                }}

                function removeMousePositionControl() {{
                    try {{
                        if (mousePosMoveFn) {{
                            map.un('pointermove', mousePosMoveFn);
                            mousePosMoveFn = null;
                        }}
                        if (mousePosControl) {{
                            map.removeControl(mousePosControl);
                            mousePosControl = null;
                        }}
                    }} catch (e) {{}}
                }}

                function setControlSize(scale) {{
                    var controls = document.getElementsByClassName('ol-control');
                    for (var i = 0; i < controls.length; i++) {{
                        controls[i].style.transform = 'scale(' + scale + ')';
                        controls[i].style.transformOrigin = 'top left';
                    }}
                }}

                // EDIT MODE FOR CONTROLS (drag/resize frames)
                window.controlsEditEnabled = false;
                let controlFrames = [];
                let activeDrag = null; // {{ type: 'move'|'resize', frame, el, startX, startY, startLeft, startTop, startW, startH, dir }}

                function setControlsInteractive(interactive) {{
                    try {{
                        const ctrls = document.getElementsByClassName('ol-control');
                        for (let i = 0; i < ctrls.length; i++) {{
                            ctrls[i].style.pointerEvents = interactive ? 'auto' : 'none';
                        }}
                    }} catch(e) {{}}
                }}

                function removeAllControlFrames() {{
                    try {{
                        controlFrames.forEach(f => f.parentNode && f.parentNode.removeChild(f));
                        controlFrames = [];
                    }} catch(e) {{ controlFrames = []; }}
                }}

                function getMapDivRect() {{
                    try {{
                        const mapDiv = document.getElementById('map');
                        return mapDiv.getBoundingClientRect();
                    }} catch(e) {{ return {{left:0, top:0}}; }}
                }}

                function normalizeControlPosition(el) {{
                    // Ensure the control uses left/top for positioning so dragging works reliably
                    const rect = el.getBoundingClientRect();
                    const mapRect = getMapDivRect();
                    const left = rect.left - mapRect.left;
                    const top = rect.top - mapRect.top;
                    el.style.left = left + 'px';
                    el.style.top = top + 'px';
                    el.style.right = '';
                    el.style.bottom = '';
                    // Preserve width/height if any
                    if (!el.style.width) el.style.width = rect.width + 'px';
                    if (!el.style.height) el.style.height = rect.height + 'px';
                }}

                function createHandle(dir) {{
                    const h = document.createElement('div');
                    h.dataset.dir = dir; // e.g., 'nw','n','ne','e','se','s','sw','w'
                    h.style.position = 'absolute';
                    h.style.width = '8px';
                    h.style.height = '8px';
                    h.style.background = '#2d8cf0';
                    h.style.border = '1px solid #fff';
                    h.style.boxSizing = 'border-box';
                    h.style.borderRadius = '50%';
                    h.style.cursor = ({{
                        'n':'ns-resize','s':'ns-resize','e':'ew-resize','w':'ew-resize',
                        'ne':'nesw-resize','nw':'nwse-resize','se':'nwse-resize','sw':'nesw-resize'
                    }})[dir] || 'pointer';
                    return h;
                }}

                function positionHandles(frame) {{
                    const w = frame.offsetWidth, h = frame.offsetHeight;
                    const setPos = (el, x, y) => {{ el.style.left = (x-4) + 'px'; el.style.top = (y-4) + 'px'; }};
                    const handles = frame._handles;
                    setPos(handles.nw, 0, 0);
                    setPos(handles.n,  w/2, 0);
                    setPos(handles.ne, w, 0);
                    setPos(handles.e,  w, h/2);
                    setPos(handles.se, w, h);
                    setPos(handles.s,  w/2, h);
                    setPos(handles.sw, 0, h);
                    setPos(handles.w,  0, h/2);
                }}

                function buildFrameForControl(el) {{
                    try {{
                        normalizeControlPosition(el);
                        const mapRect = getMapDivRect();
                        const rect = el.getBoundingClientRect();
                        const left = rect.left - mapRect.left;
                        const top = rect.top - mapRect.top;
                        const frame = document.createElement('div');
                        frame.className = 'ol-control-edit-frame';
                        frame.style.position = 'absolute';
                        frame.style.left = left + 'px';
                        frame.style.top = top + 'px';
                        frame.style.width = rect.width + 'px';
                        frame.style.height = rect.height + 'px';
                        frame.style.border = '1px dashed #2d8cf0';
                        frame.style.boxSizing = 'border-box';
                        frame.style.zIndex = 20000;
                        frame.style.background = 'rgba(45,140,240,0.06)';
                        frame.style.cursor = 'move';

                        // Create 8 handles
                        const dirs = ['nw','n','ne','e','se','s','sw','w'];
                        frame._handles = {{}};
                        dirs.forEach(d => {{
                            const hd = createHandle(d);
                            frame.appendChild(hd);
                            frame._handles[d] = hd;
                            hd.addEventListener('mousedown', function(e) {{
                                e.stopPropagation();
                                e.preventDefault();
                                activeDrag = {{
                                    type: 'resize', frame: frame, el: el,
                                    startX: e.clientX, startY: e.clientY,
                                    startLeft: frame.offsetLeft, startTop: frame.offsetTop,
                                    startW: frame.offsetWidth, startH: frame.offsetHeight,
                                    dir: d
                                }};
                            }});
                        }});
                        positionHandles(frame);

                        frame.addEventListener('mousedown', function(e) {{
                            // Start moving the frame (and the control)
                            e.preventDefault();
                            activeDrag = {{
                                type: 'move', frame: frame, el: el,
                                startX: e.clientX, startY: e.clientY,
                                startLeft: frame.offsetLeft, startTop: frame.offsetTop
                            }};
                        }});

                        const overlayContainer = document.getElementById('overlay-container');
                        overlayContainer.appendChild(frame);
                        controlFrames.push(frame);
                    }} catch(e) {{}}
                }}

                function onEditMouseMove(e) {{
                    if (!activeDrag) return;
                    const dx = e.clientX - activeDrag.startX;
                    const dy = e.clientY - activeDrag.startY;
                    if (activeDrag.type === 'move') {{
                        const nl = Math.max(0, activeDrag.startLeft + dx);
                        const nt = Math.max(0, activeDrag.startTop + dy);
                        activeDrag.frame.style.left = nl + 'px';
                        activeDrag.frame.style.top = nt + 'px';
                        // Apply to control
                        activeDrag.el.style.left = nl + 'px';
                        activeDrag.el.style.top = nt + 'px';
                    }} else if (activeDrag.type === 'resize') {{
                        let nl = activeDrag.startLeft;
                        let nt = activeDrag.startTop;
                        let nw = activeDrag.startW;
                        let nh = activeDrag.startH;
                        const dir = activeDrag.dir;
                        if (dir.indexOf('e') !== -1) nw = Math.max(20, activeDrag.startW + dx);
                        if (dir.indexOf('s') !== -1) nh = Math.max(20, activeDrag.startH + dy);
                        if (dir.indexOf('w') !== -1) {{
                            nw = Math.max(20, activeDrag.startW - dx);
                            nl = activeDrag.startLeft + dx;
                        }}
                        if (dir.indexOf('n') !== -1) {{
                            nh = Math.max(20, activeDrag.startH - dy);
                            nt = activeDrag.startTop + dy;
                        }}
                        activeDrag.frame.style.left = nl + 'px';
                        activeDrag.frame.style.top = nt + 'px';
                        activeDrag.frame.style.width = nw + 'px';
                        activeDrag.frame.style.height = nh + 'px';
                        positionHandles(activeDrag.frame);
                        // Apply to control element
                        activeDrag.el.style.left = nl + 'px';
                        activeDrag.el.style.top = nt + 'px';

                        // Use CSS transform to scale the control, preserving its internal layout
                        const originalWidth = activeDrag.startW;
                        const originalHeight = activeDrag.startH;
                        const scaleX = nw / originalWidth;
                        const scaleY = nh / originalHeight;
                        
                        activeDrag.el.style.transformOrigin = 'top left';
                        activeDrag.el.style.transform = `scale(${{scaleX}}, ${{scaleY}})`;
                    }}
                }}

                function onEditMouseUp() {{
                    activeDrag = null;
                }}

                window.addEventListener('mousemove', onEditMouseMove);
                window.addEventListener('mouseup', onEditMouseUp);

                function rebuildControlFrames() {{
                    if (!window.controlsEditEnabled) return;
                    removeAllControlFrames();
                    try {{
                        const ctrls = document.getElementsByClassName('ol-control');
                        for (let i = 0; i < ctrls.length; i++) {{
                            const el = ctrls[i];
                            // Skip the edit frames themselves or any transient containers
                            if (el.classList.contains('ol-unselectable') || true) {{
                                buildFrameForControl(el);
                            }}
                        }}
                    }} catch(e) {{}}
                }}

                function setControlsEditMode(enabled) {{
                    window.controlsEditEnabled = !!enabled;
                    const overlayContainer = document.getElementById('overlay-container');
                    if (window.controlsEditEnabled) {{
                        // Allow frames to receive pointer events
                        overlayContainer.style.pointerEvents = 'auto';
                        setControlsInteractive(false);
                        rebuildControlFrames();
                    }} else {{
                        overlayContainer.style.pointerEvents = 'none';
                        removeAllControlFrames();
                        setControlsInteractive(true);
                    }}
                }}

                // Serialize current controls layout (position/size) relative to map div
                function getControlsLayout() {{
                    const layout = {{}};
                    try {{
                        const mapRect = getMapDivRect();
                        if (!window.ol_controls) return layout;
                        Object.keys(window.ol_controls).forEach(function(name) {{
                            const ctrl = window.ol_controls[name];
                            if (!ctrl || !ctrl.element) return;
                            const el = ctrl.element;
                            // Ensure left/top/width/height are in styles for reliability
                            normalizeControlPosition(el);
                            const rect = el.getBoundingClientRect();
                            layout[name] = {{
                                left: Math.round(rect.left - mapRect.left),
                                top: Math.round(rect.top - mapRect.top),
                                width: Math.round(rect.width),
                                height: Math.round(rect.height)
                            }};
                        }});
                    }} catch(e) {{}}
                    return layout;
                }}

                // Apply a saved controls layout
                function setControlsLayout(layout) {{
                    try {{
                        if (!layout || !window.ol_controls) return;
                        Object.keys(layout).forEach(function(name) {{
                            const ctrl = window.ol_controls[name];
                            if (!ctrl || !ctrl.element) return;
                            const el = ctrl.element;
                            const v = layout[name] || {{}};
                            try {{
                                el.style.position = 'absolute';
                                if (Number.isFinite(v.left)) el.style.left = v.left + 'px';
                                if (Number.isFinite(v.top)) el.style.top = v.top + 'px';
                                if (Number.isFinite(v.width)) el.style.width = v.width + 'px';
                                if (Number.isFinite(v.height)) el.style.height = v.height + 'px';
                            }} catch(e) {{}}
                        }});
                        // If edit mode is on, refresh frames to match new layout
                        if (window.controlsEditEnabled) {{
                            try {{ rebuildControlFrames(); }} catch(e) {{}}
                        }}
                    }} catch(e) {{}}
                }}

                // PRINT CONTROL
                let printControl = null;
                function createPrintControl() {{
                    if (printControl) return printControl;
                    try {{
                        const container = document.createElement('div');
                        container.className = 'ol-control ol-unselectable';
                        container.style.cssText = 'position:absolute; top: 8px; left: 8px; z-index: 9999;';
                        const btn = document.createElement('button');
                        btn.type = 'button';
                        btn.title = 'Print map';
                        btn.textContent = 'Print';
                        btn.style.cssText = 'padding:4px 8px;border:1px solid #999;border-radius:3px;background:rgba(255,255,255,0.85);cursor:pointer;font:12px \"Segoe UI\", Roboto, Arial;';
                        btn.addEventListener('click', function() {{
                            // Open a print-friendly window containing just the map element
                            try {{
                                const canvas = map.getViewport().querySelector('canvas');
                                if (canvas) {{
                                    const dataUrl = canvas.toDataURL('image/png');
                                    const w = window.open('', '_blank');
                                    w.document.write('<html><head><title>Print Map</title></head><body style="margin:0;">');
                                    w.document.write('<img src="' + dataUrl + '" style="width:100%;height:auto;" />');
                                    w.document.write('</body></html>');
                                    w.document.close();
                                    w.focus();
                                    setTimeout(function() {{ w.print(); }}, 200);
                                }} else {{
                                    window.print();
                                }}
                            }} catch (e) {{ window.print(); }}
                        }});
                        container.appendChild(btn);
                        printControl = new ol.control.Control({{ element: container }});
                        return printControl;
                    }} catch(e) {{ return null; }}
                }}

                function removePrintControl() {{
                    try {{
                        if (printControl) {{
                            map.removeControl(printControl);
                            printControl = null;
                        }}
                    }} catch(e) {{}}
                }}

                // EXPORT CONTROL (to PDF via browser print dialog)
                let exportControl = null;
                function createExportControl() {{
                    if (exportControl) return exportControl;
                    try {{
                        const container = document.createElement('div');
                        container.className = 'ol-control ol-unselectable';
                        container.style.cssText = 'position:absolute; top: 8px; left: 70px; z-index: 9999;';
                        const btn = document.createElement('button');
                        btn.type = 'button';
                        btn.title = 'Export map to PDF';
                        btn.textContent = 'Export PDF';
                        btn.style.cssText = 'padding:4px 8px;border:1px solid #999;border-radius:3px;background:rgba(255,255,255,0.85);cursor:pointer;font:12px \"Segoe UI\", Roboto, Arial;';
                        btn.addEventListener('click', function() {{
                            try {{
                                // Try to capture the primary canvas
                                const canvas = map.getViewport().querySelector('canvas');
                                if (canvas) {{
                                    const dataUrl = canvas.toDataURL('image/png');
                                    const w = window.open('', '_blank');
                                    w.document.write('<html><head><title>Export Map</title></head>');
                                    w.document.write('<body style="margin:0;">');
                                    w.document.write('<img src="' + dataUrl + '" style="width:100%;height:auto;" />');
                                    w.document.write('</body></html>');
                                    w.document.close();
                                    w.focus();
                                    // Let user Save as PDF via print dialog
                                    setTimeout(function() {{ w.print(); }}, 200);
                                }} else {{
                                    // Fallback: use print directly
                                    window.print();
                                }}
                            }} catch(e) {{ window.print(); }}
                        }});
                        container.appendChild(btn);
                        exportControl = new ol.control.Control({{ element: container }});
                        return exportControl;
                    }} catch(e) {{ return null; }}
                }}

                function removeExportControl() {{
                    try {{
                        if (exportControl) {{
                            map.removeControl(exportControl);
                            exportControl = null;
                        }}
                    }} catch(e) {{}}
                }}

                // MEASURE TOOL (distance)
                let measureSource = new ol.source.Vector();
                let measureLayer = new ol.layer.Vector({{ 
                    source: measureSource,
                    style: new ol.style.Style({{
                        stroke: new ol.style.Stroke({{ color: '#ff3b30', width: 2 }}),
                        image: new ol.style.Circle({{
                            radius: 4,
                            fill: new ol.style.Fill({{ color: '#ff3b30' }}),
                            stroke: new ol.style.Stroke({{ color: '#ffffff', width: 1 }})
                        }})
                    }})
                }});
                measureLayer.setZIndex(10000);
                map.addLayer(measureLayer);

                let measureDraw = null;
                let measureTooltipElement = null;
                let measureTooltip = null;
                let measureEnabled = false;
                let measureControl = null;

                function createMeasureTooltip() {{
                    if (measureTooltipElement) {{
                        measureTooltipElement.parentNode && measureTooltipElement.parentNode.removeChild(measureTooltipElement);
                    }}
                    measureTooltipElement = document.createElement('div');
                    measureTooltipElement.className = 'measure-tooltip';
                    measureTooltipElement.style.cssText = 'position:absolute;z-index:20000;background:rgba(0,0,0,0.7);color:#fff;padding:4px 6px;border-radius:3px;white-space:nowrap;transform:translate(-50%, -100%);pointer-events:none;font:12px sans-serif;';
                    measureTooltip = new ol.Overlay({{
                        element: measureTooltipElement,
                        offset: [0, -10],
                        positioning: 'bottom-center'
                    }});
                    map.addOverlay(measureTooltip);
                }}

                function formatLength(line) {{
                    try {{
                        const length = ol.sphere.getLength(line, {{ projection: map.getView().getProjection() }});
                        if (length > 1000) {{
                            return (length / 1000).toFixed(2) + ' km';
                        }}
                        return length.toFixed(2) + ' m';
                    }} catch (e) {{
                        return '';
                    }}
                }}

                function enableMeasure(mode) {{
                    // Currently only 'line' supported; extendable to 'area'
                    disableMeasure();
                    createMeasureTooltip();
                    measureDraw = new ol.interaction.Draw({{
                        source: measureSource,
                        type: 'LineString',
                        stopClick: true
                    }});
                    map.addInteraction(measureDraw);

                    let sketch = null;
                    measureDraw.on('drawstart', function(evt) {{
                        sketch = evt.feature;
                        measureTooltip.setPosition(evt.coordinate);
                        measureTooltipElement.innerHTML = '0.00 m';
                        try {{ map.getTargetElement().style.cursor = 'crosshair'; }} catch(e) {{}}
                        sketch.getGeometry().on('change', function(geomEvt) {{
                            const geom = geomEvt.target;
                            measureTooltip.setPosition(geom.getLastCoordinate());
                            measureTooltipElement.innerHTML = formatLength(geom);
                        }});
                    }});
                    measureDraw.on('drawend', function(evt) {{
                        // Keep final label at last coord
                        const geom = evt.feature.getGeometry();
                        measureTooltip.setPosition(geom.getLastCoordinate());
                        sketch = null;
                        try {{ map.getTargetElement().style.cursor = ''; }} catch(e) {{}}
                    }});
                }}

                function disableMeasure() {{
                    if (measureDraw) {{
                        map.removeInteraction(measureDraw);
                        measureDraw = null;
                    }}
                    try {{ map.getTargetElement().style.cursor = ''; }} catch(e) {{}}
                    if (measureTooltip) {{
                        map.removeOverlay(measureTooltip);
                        measureTooltip = null;
                    }}
                    if (measureTooltipElement && measureTooltipElement.parentNode) {{
                        measureTooltipElement.parentNode.removeChild(measureTooltipElement);
                        measureTooltipElement = null;
                    }}
                    // Clear drawings when disabling
                    try {{ measureSource.clear(); }} catch (e) {{}}
                    // Do not clear existing measurements automatically; keep user sketches
                }}

                function setControlActive(active) {{
                    try {{
                        const btn = document.getElementById('measure-btn');
                        if (!btn) return;
                        if (active) {{
                            btn.style.backgroundColor = 'rgba(255,59,48,0.9)';
                            btn.style.color = '#fff';
                        }} else {{
                            btn.style.backgroundColor = 'rgba(255,255,255,0.7)';
                            btn.style.color = '#000';
                        }}
                    }} catch(e) {{}}
                }}

                function createMeasureControl() {{
                    if (measureControl) return;
                    try {{
                        const container = document.createElement('div');
                        container.className = 'ol-control ol-unselectable';
                        container.style.cssText = 'top: 8px; left: 8px; position: absolute;';
                        const btn = document.createElement('button');
                        btn.id = 'measure-btn';
                        btn.type = 'button';
                        btn.title = 'Measure distance';
                        btn.innerText = 'Measure';
                        btn.style.cssText = 'padding:4px 8px;border:1px solid #999;border-radius:3px;background:rgba(255,255,255,0.7);cursor:pointer;';
                        btn.addEventListener('click', function() {{
                            if (!measureEnabled) {{
                                enableMeasure('line');
                                measureEnabled = true;
                                setControlActive(true);
                            }} else {{
                                disableMeasure();
                                measureEnabled = false;
                                setControlActive(false);
                            }}
                        }});
                        container.appendChild(btn);
                        measureControl = new ol.control.Control({{ element: container }});
                        map.addControl(measureControl);
                    }} catch(e) {{
                        measureControl = null;
                        if (window.backend && window.backend.log_message) {{
                            window.backend.log_message('Failed to create measure control: ' + e.message);
                        }}
                    }}
                }}

                function removeMeasureControl() {{
                    try {{
                        if (measureControl) {{
                            map.removeControl(measureControl);
                            measureControl = null;
                        }}
                    }} catch(e) {{}}
                }}

                function setMeasureEnabled(enabled) {{
                    enabled = !!enabled;
                    if (enabled) {{
                        createMeasureControl();
                        // Do not auto-start measuring; let the user click the control button.
                    }} else {{
                        // If currently measuring, stop it
                        if (measureEnabled) {{
                            disableMeasure();
                            measureEnabled = false;
                        }}
                        setControlActive(false);
                        removeMeasureControl();
                    }}
                }}

                // RULERS & GUIDES IMPLEMENTATION
                let rulersVisible = false;
                let guidesEnabled = false;
                let isDraggingGuide = false;
                let activeGuide = null;
                let dragType = null; // 'h' or 'v'

                const overlayContainer = document.getElementById('overlay-container');
                const mapDiv = document.getElementById('map');
                const rulerTop = document.getElementById('ruler-top');
                const rulerLeft = document.getElementById('ruler-left');
                const guideContainer = document.getElementById('guide-container');
                const topOffset = 18;  // ruler height
                const leftOffset = 18; // ruler width

                // Ruler unit handling
                let rulerUnit = 'px';
                // CSS pixels per millimeter (96 px/inch)
                let pxPerMM = 96 / 25.4;

                function clearGuides() {{
                    guideContainer.innerHTML = '';
                }}

                // Drag from rulers to create guides
                rulerTop.addEventListener('mousedown', function(e) {{
                    if (!guidesEnabled) return;
                    const rect = mapDiv.getBoundingClientRect();
                    const x = e.clientX - rect.left;
                    createGuide('v', x);
                    isDraggingGuide = true;
                    activeGuide = guideContainer.lastElementChild;
                    dragType = 'v';
                    e.preventDefault();
                }});

                rulerLeft.addEventListener('mousedown', function(e) {{
                    if (!guidesEnabled) return;
                    const rect = mapDiv.getBoundingClientRect();
                    const y = e.clientY - rect.top;
                    createGuide('h', y);
                    isDraggingGuide = true;
                    activeGuide = guideContainer.lastElementChild;
                    dragType = 'h';
                    e.preventDefault();
                }});

                function createGuide(type, pos) {{
                    const guide = document.createElement('div');
                    if (type === 'v') {{
                        guide.className = 'guide-v';
                        guide.style.left = (pos + leftOffset) + 'px';
                    }} else {{
                        guide.className = 'guide-h';
                        guide.style.top = (pos + topOffset) + 'px';
                    }}
                    guideContainer.appendChild(guide);
                }}

                function onMouseMove(e) {{
                    if (!isDraggingGuide || !activeGuide) return;
                    const rect = mapDiv.getBoundingClientRect();
                    if (dragType === 'v') {{
                        const x = e.clientX - rect.left;
                        activeGuide.style.left = (x + leftOffset) + 'px';
                    }} else if (dragType === 'h') {{
                        const y = e.clientY - rect.top;
                        activeGuide.style.top = (y + topOffset) + 'px';
                    }}
                }}

                function onMouseUp() {{
                    isDraggingGuide = false;
                    activeGuide = null;
                    dragType = null;
                }}

                window.addEventListener('mousemove', onMouseMove);
                window.addEventListener('mouseup', onMouseUp);

                function renderRulerTicks() {{
                    rulerTop.innerHTML = '';
                    rulerLeft.innerHTML = '';
                    const width = mapDiv.clientWidth;
                    const height = mapDiv.clientHeight;

                    let stepPxX, labelStepPxX, toLabelX;
                    let stepPxY, labelStepPxY, toLabelY;

                    if (rulerUnit === 'mm') {{
                        stepPxX = 5 * pxPerMM;      // tick every 5mm
                        labelStepPxX = 10 * pxPerMM; // label every 10mm
                        toLabelX = (px) => Math.round(px / pxPerMM);
                        stepPxY = 5 * pxPerMM;
                        labelStepPxY = 10 * pxPerMM;
                        toLabelY = (px) => Math.round(px / pxPerMM);
                    }} else {{
                        stepPxX = 50;               // tick every 50px
                        labelStepPxX = 100;          // label every 100px
                        toLabelX = (px) => Math.round(px);
                        stepPxY = 50;
                        labelStepPxY = 100;
                        toLabelY = (px) => Math.round(px);
                    }}

                    const tickCountX = Math.ceil(width / stepPxX);
                    const labelEveryX = Math.max(1, Math.round(labelStepPxX / stepPxX));
                    for (let i = 0; i <= tickCountX; i++) {{
                        const x = i * stepPxX;
                        const tick = document.createElement('div');
                        tick.className = 'ruler-tick';
                        tick.style.left = (x + leftOffset) + 'px';
                        rulerTop.appendChild(tick);
                        if (i % labelEveryX === 0) {{
                            const label = document.createElement('div');
                            label.style.position = 'absolute';
                            label.style.left = (x + leftOffset + 2) + 'px';
                            label.style.bottom = '2px';
                            label.style.fontSize = '10px';
                            label.style.color = '#666';
                            label.textContent = toLabelX(x);
                            rulerTop.appendChild(label);
                        }}
                    }}

                    const tickCountY = Math.ceil(height / stepPxY);
                    const labelEveryY = Math.max(1, Math.round(labelStepPxY / stepPxY));
                    for (let j = 0; j <= tickCountY; j++) {{
                        const y = j * stepPxY;
                        const tick = document.createElement('div');
                        tick.className = 'ruler-tick-left';
                        tick.style.top = (y + topOffset) + 'px';
                        rulerLeft.appendChild(tick);
                        if (j % labelEveryY === 0) {{
                            const label = document.createElement('div');
                            label.style.position = 'absolute';
                            label.style.top = (y + topOffset + 2) + 'px';
                            label.style.right = '2px';
                            label.style.fontSize = '10px';
                            label.style.color = '#666';
                            label.textContent = toLabelY(y);
                            rulerLeft.appendChild(label);
                        }}
                    }}
                }}

                function showRulers(show) {{
                    rulersVisible = !!show;
                    rulerTop.style.display = rulersVisible ? 'block' : 'none';
                    rulerLeft.style.display = rulersVisible ? 'block' : 'none';
                    // Keep overlay container non-interactive so map remains clickable
                    overlayContainer.style.pointerEvents = 'none';
                    // Enable pointer events only on the rulers themselves for guide creation
                    rulerTop.style.pointerEvents = rulersVisible ? 'auto' : 'none';
                    rulerLeft.style.pointerEvents = rulersVisible ? 'auto' : 'none';
                    if (rulersVisible) {{
                        mapDiv.style.marginTop = topOffset + 'px';
                        mapDiv.style.marginLeft = leftOffset + 'px';
                        renderRulerTicks();
                    }} else {{
                        mapDiv.style.marginTop = '0px';
                        mapDiv.style.marginLeft = '0px';
                    }}
                }}

                function setGuidesEnabled(enabled) {{
                    guidesEnabled = !!enabled;
                    // Guides themselves have pointer-events auto; container remains non-interactive to preserve map interactions
                    const guides = guideContainer.children;
                    for (let i = 0; i < guides.length; i++) {{
                        guides[i].style.pointerEvents = guidesEnabled ? 'auto' : 'none';
                    }}
                }}

                function setRulerUnit(unit) {{
                    rulerUnit = (unit === 'mm') ? 'mm' : 'px';
                    if (rulersVisible) {{
                        renderRulerTicks();
                    }}
                }}

                window.addEventListener('resize', function() {{
                    if (rulersVisible) {{
                        renderRulerTicks();
                    }}
                }});

                // LAYER SWITCHER IMPLEMENTATION
                let layerSwitcherElement = null;
                function createLayerSwitcherControl() {{
                    try {{
                        const container = document.createElement('div');
                        container.className = 'ol-control ol-unselectable';
                        container.style.cssText = 'top: 8px; right: 8px; position: absolute; max-height: 50%; overflow:auto;';
                        const panel = document.createElement('div');
                        panel.id = 'layer-switcher-panel';
                        panel.style.cssText = 'background:rgba(255,255,255,0.85);border:1px solid #999;border-radius:4px;padding:6px;min-width:200px;';
                        const title = document.createElement('div');
                        title.textContent = 'Layers';
                        title.style.cssText = 'font:bold 12px sans-serif;margin-bottom:4px;';
                        panel.appendChild(title);
                        const list = document.createElement('div');
                        list.id = 'layer-switcher-list';
                        panel.appendChild(list);
                        container.appendChild(panel);
                        layerSwitcherElement = container;
                        return new ol.control.Control({{ element: container }});
                    }} catch (e) {{
                        layerSwitcherElement = null;
                        if (window.backend && window.backend.log_message) {{
                            window.backend.log_message('Failed to create LayerSwitcher: ' + e.message);
                        }}
                        return null;
                    }}
                }}

                function getOrderedLayerIds() {{
                    // Prefer stored order from Python; otherwise, current map order by zIndex
                    if (Array.isArray(window._layerOrder) && window._layerOrder.length) {{
                        return window._layerOrder.filter(id => !!window.ol_layers[id]);
                    }}
                    // Fallback: keys of ol_layers
                    return Object.keys(window.ol_layers);
                }}

                function refreshLayerSwitcher() {{
                    try {{
                        const ctrl = window.ol_controls && window.ol_controls['LayerSwitcher'];
                        if (!ctrl || !layerSwitcherElement) return;
                        const list = layerSwitcherElement.querySelector('#layer-switcher-list');
                        if (!list) return;
                        list.innerHTML = '';
                        const orderedIds = getOrderedLayerIds();
                        orderedIds.forEach(function(layerId) {{
                            const layer = window.ol_layers[layerId];
                            if (!layer) return;
                            const row = document.createElement('div');
                            row.style.cssText = 'display:flex;align-items:center;gap:6px;margin:2px 0;';
                            const cb = document.createElement('input');
                            cb.type = 'checkbox';
                            cb.checked = !!layer.getVisible();
                            cb.addEventListener('change', function() {{
                                try {{
                                    layer.setVisible(cb.checked);
                                    if (window.backend && window.backend.layerVisibilityChanged) {{
                                        window.backend.layerVisibilityChanged(layerId, cb.checked);
                                    }}
                                }} catch(e) {{}}
                            }});
                            const label = document.createElement('span');
                            const title = layer.get('title') || layer.get('id') || layerId;
                            label.textContent = title;
                            label.style.cssText = 'font:12px sans-serif;';
                            row.appendChild(cb);
                            row.appendChild(label);
                            list.appendChild(row);
                        }});
                    }} catch (e) {{}}
                }}

                function setLayerTitle(layerId, title) {{
                    try {{
                        if (window.ol_layers[layerId]) {{
                            window.ol_layers[layerId].set('title', title);
                            refreshLayerSwitcher();
                        }}
                    }} catch(e) {{}}
                }}

            </script>
        </body>
        </html>
        '''
        # Delay setting HTML to allow UI to render first
        from PyQt5.QtCore import QTimer
        self.log_message("⏳ Scheduling HTML load...")
        QTimer.singleShot(100, lambda: self._load_html_content(web_view, html_content))

    def _load_html_content(self, web_view, html_content):
        """Helper to load HTML content into web view."""
        try:
            self.log_message("🚀 Loading HTML content into WebEngine...")
            # Use GeoServer URL as base for resolving relative URLs
            base_url = QUrl(self.geoserver_url) if self.geoserver_url else QUrl()
            web_view.setHtml(html_content, base_url)
            self.log_message("✅ setHtml called")
            
            # Add JavaScript to verify OpenLayers source after map loads
            verify_js = """
            (function() {
                // Wait for OpenLayers to be fully loaded
                setTimeout(function() {
                    try {
                        // Check if OpenLayers is loaded
                        if (typeof ol !== 'undefined') {
                            // Try to determine source by checking script tags
                            var scripts = document.getElementsByTagName('script');
                            var olSource = 'Unknown';
                            
                            for (var i = 0; i < scripts.length; i++) {
                                var src = scripts[i].src;
                                if (src && src.indexOf('ol.js') !== -1) {
                                    olSource = src;
                                    break;
                                }
                            }
                            
                            // Report back to Python
                            if (window.backend && window.backend.log_message) {
                                window.backend.log_message('🔍 OpenLayers source verified: ' + olSource);
                            }
                            
                            // Add version info if available
                            if (ol.VERSION) {
                                if (window.backend && window.backend.log_message) {
                                    window.backend.log_message('📊 OpenLayers version: ' + ol.VERSION);
                                }
                            }
                        } else {
                            if (window.backend && window.backend.log_message) {
                                window.backend.log_message('⚠️ OpenLayers not loaded properly');
                            }
                        }
                    } catch(e) {
                        if (window.backend && window.backend.log_message) {
                            window.backend.log_message('❌ Error verifying OpenLayers: ' + e.message);
                        }
                    }
                }, 1000); // Wait 1 second for everything to load
            })();
            """
            
            # Execute verification after a delay to ensure map is loaded
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1500, lambda: web_view.page().runJavaScript(verify_js))
        except Exception as e:
            self.log_message(f"❌ Error setting HTML: {e}", level=Qgis.Critical)

    def setup_web_channel(self):
        self.log_message("Setting up web channel...")
        self.channel = QWebChannel(self.web_view.page())
        self.web_view.page().setWebChannel(self.channel)
        self.channel.registerObject('backend', self)
        self.log_message("Web channel setup complete.")

    def _save_current_map_view(self):
        """Save the current map view (center and zoom) to restore later."""
        try:
            # Use JavaScript to get the current map view
            self.web_view.page().runJavaScript(
                "JSON.stringify({center: map.getView().getCenter(), zoom: map.getView().getZoom()})",
                lambda result: self._on_map_view_saved(result)
            )
        except Exception as e:
            self.log_message(f"Error saving map view: {e}", level=Qgis.Warning)
    
    def _on_map_view_saved(self, view_json):
        """Callback to store the saved map view."""
        try:
            if view_json:
                self.saved_map_view = json.loads(view_json)
                self.log_message(f"Map view saved: {self.saved_map_view}")
        except Exception as e:
            self.log_message(f"Error parsing saved map view: {e}", level=Qgis.Warning)
    
    def _restore_map_view(self):
        """Restore the previously saved map view."""
        try:
            if hasattr(self, 'saved_map_view') and self.saved_map_view:
                center = self.saved_map_view.get('center', [0, 0])
                zoom = self.saved_map_view.get('zoom', 2)
                
                # Use a more robust JavaScript approach with direct view manipulation
                js_code = f"""
                (function() {{
                    try {{
                        console.log('Setting map view to:', [{center[0]}, {center[1]}], {zoom});
                        var view = map.getView();
                        view.setCenter([{center[0]}, {center[1]}]);
                        view.setZoom({zoom});
                        console.log('Map view set successfully');
                        if (window.backend) window.backend.log_message('Map view set via direct JavaScript');
                    }} catch(e) {{
                        console.error('Error setting map view:', e);
                        if (window.backend) window.backend.log_message('Error setting map view: ' + e.message);
                    }}
                }})();
                """
                
                # Execute immediately
                self.web_view.page().runJavaScript(js_code)
                
                # Also try again after a short delay to ensure it's applied
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(500, lambda: self.web_view.page().runJavaScript(js_code))
                
                self.log_message(f"Map view restore requested: center={center}, zoom={zoom}")
        except Exception as e:
            self.log_message(f"Error restoring map view: {e}", level=Qgis.Warning)

    @pyqtSlot()
    def clear_cache_and_reload(self):
        """Reload the map, clear cache, and refresh all layers from GeoServer."""
        try:
            self.log_message("🔄 Reloading map and clearing cache...")
            
            # Save current control states to ini BEFORE clearing
            self.log_message("💾 Saving control states...")
            if hasattr(self, 'right_panel') and self.right_panel:
                self.right_panel._save_controls_state()
            
            # Save current map state before clearing
            import tempfile
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, 'geovirtuallis_reload_state.geos')
            
            self.log_message("💾 Saving current map state...")
            self._save_map_state_to_file(temp_file)
            
            # Clear the map completely - this removes all cached layers
            self.log_message("🧹 Clearing map cache...")
            self.clear_openlayers_map()
            
            # Reload the HTML with fresh map
            self.log_message("🔄 Reinitializing map...")
            self.initialize_openlayers_map(self.web_view)
            
            # Restore the saved state (zoom, pan, theme, layers) after a short delay
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(500, lambda: self._load_map_state_from_file(temp_file))
            
            self.log_message("✅ Map reloaded with cache cleared")
            
        except Exception as e:
            self.log_message(f"❌ Error reloading map: {str(e)}", level=Qgis.Warning)
            import traceback
            traceback.print_exc()
    
    def _save_map_state_to_file(self, file_path):
        """Save the current map state to a file."""
        try:
            # First, capture the current map view using JavaScript
            js_code = """
            (function() {
                try {
                    var view = map.getView();
                    var center = view.getCenter();
                    var zoom = view.getZoom();
                    var extent = view.calculateExtent(map.getSize());
                    return JSON.stringify({
                        center: center,
                        zoom: zoom,
                        extent: extent
                    });
                } catch(e) {
                    console.error('Error getting map view:', e);
                    return JSON.stringify({});
                }
            })();
            """
            
            # Execute JavaScript and wait for the result
            from PyQt5.QtCore import QEventLoop
            loop = QEventLoop()
            
            def handle_map_view(view_json):
                try:
                    # Parse the map view state
                    view_state = json.loads(view_json) if view_json else {}
                    self.saved_map_view = view_state
                    self.log_message(f"📍 Current map view captured: center={view_state.get('center')}, zoom={view_state.get('zoom')}")
                except Exception as e:
                    self.log_message(f"Error parsing map view: {e}", level=Qgis.Warning)
                finally:
                    # Continue execution
                    loop.quit()
            
            # Execute JavaScript and wait for the result
            self.web_view.page().runJavaScript(js_code, handle_map_view)
            loop.exec_()  # Wait for JavaScript to complete
            
            # Now continue with saving the state
            map_state = self._get_map_state()
            config = configparser.ConfigParser()
            
            # Theme
            config['Theme'] = {
                'is_dark_theme': str(self.is_dark_theme),
                'base_layer_visible': str(self.rb_base_none.isChecked() == False)
            }
            
            # Layers - use data from _get_map_state() which has correct visibility and transparency
            for idx, layer_data in enumerate(map_state.get('layers', [])):
                section = f'Layer_{idx}'
                config[section] = {
                    'layer_id': layer_data['layer_id'],
                    'display_name': layer_data.get('display_name', ''),
                    'actual_name': layer_data.get('actual_name', ''),
                    'layer_type': layer_data.get('layer_type', 'WMS'),
                    'visible': str(layer_data.get('visible', True)),
                    'transparency': str(layer_data.get('transparency', 100))
                }
            
            # Layer Order
            if map_state.get('layer_order'):
                config['LayerOrder'] = {
                    'order': json.dumps(map_state['layer_order'])
                }
            
            # View - use the freshly captured view state
            if hasattr(self, 'saved_map_view') and self.saved_map_view:
                config['View'] = {
                    'center': json.dumps(self.saved_map_view.get('center', [0, 0])),
                    'zoom': str(self.saved_map_view.get('zoom', 2)),
                    'extent': json.dumps(self.saved_map_view.get('extent', []))
                }
                self.log_message(f"Map view saved with zoom={self.saved_map_view.get('zoom', 2)}")
            
            # Write to file
            with open(file_path, 'w') as f:
                config.write(f)
            
            self.log_message(f"✅ Map state saved to {file_path}")
        except Exception as e:
            self.log_message(f"Error saving map state: {e}", level=Qgis.Warning)
    
    def _load_map_state_from_file(self, file_path):
        """Load map state from a file."""
        try:
            if not os.path.exists(file_path):
                self.log_message(f"Temp file not found: {file_path}", level=Qgis.Warning)
                return
            
            self.log_message(f"📂 Loading map state from {file_path}...")
            self._on_load_state_from_path(file_path)
            
            # Clean up temp file
            try:
                os.remove(file_path)
            except:
                pass
        except Exception as e:
            self.log_message(f"Error loading map state: {e}", level=Qgis.Warning)
    
    def _on_load_state_from_path(self, file_path):
        """Load a map state from a specific file path."""
        try:
            # Clear current map
            self.clear_openlayers_map()
            
            # Load config file
            config = configparser.ConfigParser()
            config.read(file_path)
            
            # Load theme settings
            if 'Theme' in config:
                self.is_dark_theme = config.getboolean('Theme', 'is_dark_theme', fallback=False)
                base_visible = config.getboolean('Theme', 'base_layer_visible', fallback=True)
                # Update base map radio buttons based on loaded state
                if base_visible:
                    if self.is_dark_theme:
                        self.rb_base_dark.setChecked(True)
                    else:
                        self.rb_base_light.setChecked(True)
                else:
                    self.rb_base_none.setChecked(True)
                
                # Apply theme to map
                js_call = f"toggleDarkMode({str(self.is_dark_theme).lower()});"
                self.web_view.page().runJavaScript(js_call)
                js_call = f"toggleBaseLayer({str(base_visible).lower()});"
                self.web_view.page().runJavaScript(js_call)
            
            # Load layers
            layers_to_add = []
            for section_name in config.sections():
                if section_name.startswith('Layer_'):
                    layer_info = {
                        'layer_id': config.get(section_name, 'layer_id', fallback=''),
                        'display_name': config.get(section_name, 'display_name', fallback=''),
                        'actual_name': config.get(section_name, 'actual_name', fallback=''),
                        'layer_type': config.get(section_name, 'layer_type', fallback='WMS'),
                        'visible': config.getboolean(section_name, 'visible', fallback=True),
                        'transparency': config.getint(section_name, 'transparency', fallback=100)
                    }
                    layers_to_add.append(layer_info)
            
            # Add layers to map
            for layer_info in layers_to_add:
                # Add to UI tree
                label_text = f"{layer_info['display_name']} ({layer_info['layer_type']})"
                tree_item = QTreeWidgetItem(self.added_layers_tree)
                tree_item.setText(1, label_text)
                tree_item.setData(0, Qt.UserRole, layer_info['layer_id'])
                
                # Add visibility checkbox
                visibility_checkbox = QCheckBox()
                visibility_checkbox.setChecked(layer_info['visible'])
                visibility_checkbox.stateChanged.connect(
                    lambda state, l_id=layer_info['layer_id']: 
                    self.toggle_layer_visibility(l_id, state == Qt.Checked)
                )
                self.added_layers_tree.setItemWidget(tree_item, 0, visibility_checkbox)
                
                # Add transparency slider
                slider = QSlider(Qt.Horizontal)
                slider.setRange(0, 100)
                slider.setValue(layer_info['transparency'])
                slider.setToolTip("Adjust layer transparency")
                slider.valueChanged.connect(
                    lambda value, l_id=layer_info['layer_id']: 
                    self.on_transparency_changed(l_id, value)
                )
                self.added_layers_tree.setItemWidget(tree_item, 2, slider)
                
                # Store layer info
                self.added_layers[layer_info['layer_id']] = {
                    'display_name': layer_info['display_name'],
                    'actual_name': layer_info['actual_name'],
                    'item': tree_item,
                    'layer_type': layer_info['layer_type'],
                    'visibility_widget': visibility_checkbox,
                    'slider_widget': slider
                }
                
                # Add to map via JavaScript
                js_call = ""
                if layer_info['layer_type'] == 'WMS':
                    wms_url = f"{self.geoserver_url}/wms"
                    js_call = f"addWmsLayer('{wms_url}', '{layer_info['actual_name']}', '{layer_info['layer_id']}');"
                elif layer_info['layer_type'] == 'WFS':
                    wfs_url = f"{self.geoserver_url}/ows"
                    js_call = f"addWfsLayer('{wfs_url}', '{layer_info['actual_name']}', '{layer_info['layer_id']}');"
                elif layer_info['layer_type'] == 'WMTS':
                    wmts_url = f"{self.geoserver_url}/gwc/service/wmts"
                    js_call = f"addWmtsLayer('{wmts_url}', '{layer_info['actual_name']}', '{layer_info['layer_id']}');"
                
                if js_call:
                    self.web_view.page().runJavaScript(js_call)
                    
                    # Set layer title for Layer Control display
                    try:
                        self.web_view.page().runJavaScript(
                            f"setLayerTitle('{layer_info['layer_id']}', {json.dumps(label_text)});"
                        )
                    except Exception:
                        pass
                    
                    # Set visibility (but NOT transparency yet - do that after layer order is restored)
                    if not layer_info['visible']:
                        js_call = f"toggleLayerVisibility('{layer_info['layer_id']}', false);"
                        self.web_view.page().runJavaScript(js_call)
            
            # Restore layer order FIRST
            if 'LayerOrder' in config:
                try:
                    layer_order = json.loads(config.get('LayerOrder', 'order', fallback='[]'))
                    if layer_order:
                        js_call = f"refreshLayerOrder({json.dumps(layer_order)});"
                        self.web_view.page().runJavaScript(js_call)
                except Exception as e:
                    self.log_message(f"Error restoring layer order: {e}", level=Qgis.Warning)
            
            # NOW apply transparency AFTER layer order is restored
            for layer_info in layers_to_add:
                if layer_info['transparency'] != 100:
                    opacity = layer_info['transparency'] / 100.0
                    js_call = f"setLayerOpacity('{layer_info['layer_id']}', {opacity});"
                    self.web_view.page().runJavaScript(js_call)
            
            # NOTE: Do NOT adjust tree widget height when toggling between CDN and Local modes
            # This preserves the minimum height set in left_panel.py
            # self._adjust_tree_widget_height()  # Commented out to fix height issue
            
            # NOTE: Do NOT reload the layers list from GeoServer here
            # The layers list should stay exactly as it was before the reload
            # Only the map state (layers, zoom, pan, theme) is restored
            
            # LAST STEP: Restore map view after everything else is done
            # This ensures the map view is set after all layers are added and ordered
            if 'View' in config:
                try:
                    center = json.loads(config.get('View', 'center', fallback='[]'))
                    zoom = config.getfloat('View', 'zoom', fallback=2.0)
                    extent = json.loads(config.get('View', 'extent', fallback='[]'))
                    
                    # Add a longer delay to ensure all other operations are complete
                    from PyQt5.QtCore import QTimer
                    
                    # Use a simple fixed delay
                    delay_ms = 500
                    
                    # Use a direct JavaScript call to set the view
                    if center and len(center) == 2:
                        self.log_message(f"Restoring map to center={center}, zoom={zoom}")
                        
                        # Save to instance variable for reference and debugging
                        self.saved_map_view = {'center': center, 'zoom': zoom, 'extent': extent}
                        
                        # Use a more robust JavaScript approach with multiple attempts
                        js_code = f"""
                        (function() {{
                            try {{
                                console.log('Setting map view to:', [{center[0]}, {center[1]}], {zoom});
                                var view = map.getView();
                                view.setCenter([{center[0]}, {center[1]}]);
                                view.setZoom({zoom});
                                console.log('Map view set successfully');
                                if (window.backend) window.backend.log_message('Map view set via direct JavaScript: zoom=' + view.getZoom());
                            }} catch(e) {{
                                console.error('Error setting map view:', e);
                                if (window.backend) window.backend.log_message('Error setting map view: ' + e.message);
                            }}
                        }})();
                        """
                        
                        # Use multiple attempts with increasing delays to ensure it works
                        # This is especially important when toggling library modes
                        from PyQt5.QtCore import QTimer
                        
                        # Log that we're making multiple attempts
                        self.log_message("Making multiple attempts to set map view with increasing delays")
                        
                        # First attempt immediately
                        self.web_view.page().runJavaScript(js_code)
                        
                        # Additional attempts with increasing delays
                        QTimer.singleShot(500, lambda: self.web_view.page().runJavaScript(js_code))
                        QTimer.singleShot(1000, lambda: self.web_view.page().runJavaScript(js_code))
                        QTimer.singleShot(2000, lambda: self.web_view.page().runJavaScript(js_code))
                        QTimer.singleShot(3000, lambda: self.web_view.page().runJavaScript(js_code))
                    # End of map view restoration
                except Exception as e:
                    self.log_message(f"Error restoring map view: {e}", level=Qgis.Warning)
            
            # NOTE: Do NOT apply controls here - they are applied in on_webview_load_finished()
            # Applying them here causes duplicate/conflicting calls
            
            # Connect visibility checkboxes and update master checkbox state
            self.connect_visibility_checkboxes()
            self.update_select_all_checkbox_state()
            
            self.log_message("✅ Map state restored successfully")
        except Exception as e:
            self.log_message(f"Error loading map state: {str(e)}", level=Qgis.Warning)

    @pyqtSlot(bool)
    def on_webview_load_finished(self, ok):
        """Handle loadFinished from the QWebEngineView and log status."""
        self.is_webview_loading = False
        if ok:
            self.log_message("Web view finished loading successfully.")
            
            # Update the library mode indicator
            try:
                current_mode = self.get_library_mode()
                js_call = f"updateLibraryModeIndicator('{current_mode}');"
                self.web_view.page().runJavaScript(js_call)
                self.log_message(f"Updated library mode indicator to: {current_mode} mode")
            except Exception as e:
                self.log_message(f"Error updating library mode indicator: {e}", level=Qgis.Warning)
            
            # Check if we need to reload after library change
            if hasattr(self, '_reload_after_library_change') and self._reload_after_library_change:
                self._reload_after_library_change = False  # Clear the flag
                self.log_message("Library mode changed, reloading map state...")
                
                # First apply controls to ensure they're active in the new library mode
                self.log_message("Applying controls to new library mode...")
                self._apply_saved_controls()
                
                # Check if we have a temporary file path for the map state
                if hasattr(self, '_library_toggle_temp_file') and self._library_toggle_temp_file:
                    temp_file = self._library_toggle_temp_file
                    self._library_toggle_temp_file = None  # Clear the reference
                    
                    # Check if the temp file exists
                    if os.path.exists(temp_file):
                        self.log_message(f"📂 Loading map state from temporary file: {temp_file}")
                        
                        # Load the map state from the temp file with a short delay
                        # to ensure the map is fully initialized
                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(500, lambda: self._load_map_state_from_file(temp_file))
                    else:
                        self.log_message(f"⚠️ Temporary map state file not found: {temp_file}", level=Qgis.Warning)
                        # Fallback to regular reload
                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(200, lambda: self.clear_cache_and_reload())
                else:
                    self.log_message("No temporary map state file specified, using regular reload")
                    # Fallback to regular reload
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(200, lambda: self.clear_cache_and_reload())
                return
            
            # Normal load - apply saved controls and restore map view
            # Apply saved controls from ini file
            # NOTE: Checkbox state DICTATES what appears on map, not the other way around
            self._apply_saved_controls()
            # Restore saved map view if available
            self._restore_map_view()
            # Execute any queued JS calls
            if self._js_call_queue:
                self.log_message(f"Executing {len(self._js_call_queue)} queued JS calls.")
                for js_call in self._js_call_queue:
                    self.web_view.page().runJavaScript(js_call)
                self._js_call_queue.clear()
        else:
            self.log_message("Web view failed to load HTML content.", level=Qgis.Warning)
            # Provide basic feedback in the web view if load failed
            try:
                self.web_view.setHtml("<h1>Error: Could not load map content.</h1>")
            except Exception as e:
                self.log_message(f"Failed to set error HTML: {e}", level=Qgis.Critical)
    
    def _apply_saved_controls(self):
        """Apply controls to the map based on checkbox state.
        
        IMPORTANT: The checkbox state DICTATES what appears on the map.
        If checkbox is OFF, the control does NOT appear on the map.
        If checkbox is ON, the control appears on the map.
        """
        try:
            if hasattr(self, 'control_checkboxes') and self.control_checkboxes:
                control_map = {
                    "Zoom Control": "Zoom",
                    "Scale Control": "ScaleLine",
                    "Layer Control": "LayerSwitcher",
                    "Attribution Control": "Attribution",
                    "FullScreen Control": "FullScreen",
                    "Rotate Control": "Rotate",
                    "ZoomSlider Control": "ZoomSlider",
                    "ZoomToExtent Control": "ZoomToExtent",
                    "Mouse Position Control": "MousePosition",
                    "OverviewMap Control": "OverviewMap",
                    "Print Control": "Print",
                    "Export Control": "Export",
                    "Mode Indicator": "ModeIndicator"
                }
                
                for control_name, checkbox in self.control_checkboxes.items():
                    ol_control_name = control_map.get(control_name)
                    if not ol_control_name:
                        continue
                    
                    if checkbox.isChecked():
                        # Checkbox is ON - add control to map
                        if ol_control_name == "ModeIndicator":
                            js_call = f"toggleModeIndicator(true);"
                        else:
                            js_call = f"addControl('{ol_control_name}');"
                        self.web_view.page().runJavaScript(js_call)
                        self.log_message(f"✓ Control ON: {control_name}")
                    else:
                        # Checkbox is OFF - remove control from map
                        if ol_control_name == "ModeIndicator":
                            js_call = f"toggleModeIndicator(false);"
                        else:
                            js_call = f"removeControl('{ol_control_name}');"
                        self.web_view.page().runJavaScript(js_call)
                        self.log_message(f"✗ Control OFF: {control_name}")
        except Exception as e:
            self.log_message(f"Error applying saved controls: {e}", level=Qgis.Warning)
    
    def _synchronize_mode_indicator_checkbox(self):
        """Synchronize the Mode Indicator checkbox state with the actual visibility on the map.
        
        This ensures that on startup, if the mode indicator is visible on the map,
        the checkbox is checked, and vice versa.
        """
        try:
            if not hasattr(self, 'control_checkboxes') or 'Mode Indicator' not in self.control_checkboxes:
                return
            
            # Get the current visibility state of the mode indicator from the map
            js_code = """
            (function() {
                var indicator = document.getElementById('library-mode-indicator');
                if (indicator) {
                    var isVisible = indicator.style.display !== 'none';
                    return isVisible;
                }
                return false;
            })();
            """
            
            def update_checkbox(is_visible):
                try:
                    # Convert JavaScript boolean to Python boolean
                    is_visible_bool = is_visible if isinstance(is_visible, bool) else (is_visible == 'true' or is_visible == True)
                    
                    # Update the checkbox state without triggering the signal
                    checkbox = self.control_checkboxes['Mode Indicator']
                    checkbox.blockSignals(True)
                    checkbox.setChecked(is_visible_bool)
                    checkbox.blockSignals(False)
                    
                    self.log_message(f"Synchronized Mode Indicator checkbox with map state: {is_visible_bool}")
                except Exception as e:
                    self.log_message(f"Error updating Mode Indicator checkbox: {e}", level=Qgis.Warning)
            
            # Run the JavaScript to get the visibility state but don't block other operations
            # Use a QTimer to delay this operation slightly to ensure it doesn't interfere with map rendering
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, lambda: self.web_view.page().runJavaScript(js_code, update_checkbox))
        except Exception as e:
            self.log_message(f"Error synchronizing Mode Indicator checkbox: {e}", level=Qgis.Warning)

    def add_layers_to_map(self):
        """Add selected layers to the map using stored GeoServer connection details."""
        selected_items = self.layers_list.selectedItems()
        if not selected_items:
            return

        # Use stored connection details
        url = self.geoserver_url
        if not url:
            self.log_message("❌ GeoServer URL not available", level=Qgis.Critical)
            return

        for item in selected_items:
            display_name = item.text()
            layer_data = item.data(Qt.UserRole)
            actual_name = layer_data['actual_name']
            layer_type = layer_data.get('layer_type', 'VECTOR')  # Default to VECTOR if not specified
            # Selected add type from UI (via radio buttons)
            add_as_type = self.get_selected_add_type()

            # Avoid duplicates for same (layer, type)
            if any(l['actual_name'] == actual_name and l.get('layer_type') == add_as_type for l in self.added_layers.values()):
                continue

            layer_id = str(uuid.uuid4())
            # Show service type in the label, e.g. "workspace:layer (WMS)"
            label_text = f"{display_name} ({add_as_type})"
            tree_item = QTreeWidgetItem(self.added_layers_tree)
            # Column 1 is now the Layer Name; Column 0 is Visibility
            tree_item.setText(1, label_text)
            tree_item.setData(0, Qt.UserRole, layer_id)

            visibility_checkbox = QCheckBox()
            visibility_checkbox.setChecked(True)
            visibility_checkbox.stateChanged.connect(lambda state, l_id=layer_id: self.toggle_layer_visibility(l_id, state == Qt.Checked))
            self.added_layers_tree.setItemWidget(tree_item, 0, visibility_checkbox)

            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 100)
            slider.setValue(100)
            slider.setToolTip("Adjust layer transparency")
            slider.valueChanged.connect(lambda value, l_id=layer_id: self.on_transparency_changed(l_id, value))
            self.added_layers_tree.setItemWidget(tree_item, 2, slider)
            # Track with the chosen type and keep widget refs for reattachment on reorder
            self.added_layers[layer_id] = {
                'display_name': display_name,
                'actual_name': actual_name,
                'item': tree_item,
                'layer_type': add_as_type, # Store the type it was added as
                'visibility_widget': visibility_checkbox,
                'slider_widget': slider
            }

            js_call = ""
            safe_label = json.dumps(label_text)
            if add_as_type == 'WMS':
                wms_url = f"{url}/wms"
                js_call = f"addWmsLayer('{wms_url}', '{actual_name}', '{layer_id}', {safe_label});"
                self.log_message(f"📍 Adding WMS layer: {actual_name}")
            elif add_as_type == 'WFS':
                wfs_url = f"{url}/ows"
                js_call = f"addWfsLayer('{wfs_url}', '{actual_name}', '{layer_id}', {safe_label});"
                self.log_message(f"📍 Adding WFS layer: {actual_name}")
            elif add_as_type == 'WMTS':
                wmts_url = f"{url}/gwc/service/wmts"
                js_call = f"addWmtsLayer('{wmts_url}', '{actual_name}', '{layer_id}', {safe_label});"
                self.log_message(f"📍 Adding WMTS layer: {actual_name}")

            if js_call:
                if self.is_webview_loading:
                    self.log_message(f"Webview loading, queuing JS call for layer: {actual_name}")
                    self._js_call_queue.append(js_call)
                else:
                    self.log_message(f"Executing JS call immediately for layer: {actual_name}")
                    self.web_view.page().runJavaScript(js_call)
        
        # Connect visibility checkboxes and update master checkbox state
        self.connect_visibility_checkboxes()
        self.update_select_all_checkbox_state()
        self.refresh_layer_order()

    def _on_layer_selection_changed(self):
        """Enable/disable service type radio buttons based on selected layer type."""
        # Check if radio buttons are initialized
        if not hasattr(self, 'rb_wfs') or not hasattr(self, 'rb_wms'):
            return
        
        selected_items = self.layers_list.selectedItems()
        # Default to enabled if no selection or multiple selections of different types
        is_raster = False
        if len(selected_items) == 1:
            item = selected_items[0]
            layer_data = item.data(Qt.UserRole)
            if isinstance(layer_data, dict):
                layer_type = layer_data.get('layer_type')
                # Check for various raster/image layer types that GeoServer might return
                raster_types = ['RASTER', 'ImageMosaic', 'ImagePyramid', 'WorldImage', 'GeoTIFF']
                if layer_type in raster_types or (layer_type and 'image' in layer_type.lower()):
                    is_raster = True
        
        self.rb_wfs.setEnabled(not is_raster)
        # If a raster is selected and WFS was checked, switch to WMS
        if is_raster and self.rb_wfs.isChecked():
            self.rb_wms.setChecked(True)

    def get_selected_add_type(self):
        """Return the selected 'Add as' type from radio buttons: WMS, WFS, or WMTS."""
        try:
            # Check if radio buttons exist and are initialized
            if hasattr(self, 'rb_wfs') and self.rb_wfs is not None and self.rb_wfs.isChecked():
                return 'WFS'
            if hasattr(self, 'rb_wmts') and self.rb_wmts is not None and self.rb_wmts.isChecked():
                return 'WMTS'
            return 'WMS'
        except Exception:
            # Default to WMS if there's any issue
            return 'WMS'

    def on_available_layer_double_clicked(self, item):
        self.add_layers_to_map()

    def remove_layer_from_added_list(self):
        selected_items = self.added_layers_tree.selectedItems()
        if not selected_items:
            return

        for item in selected_items:
            layer_id = item.data(0, Qt.UserRole)
            if layer_id in self.added_layers:
                js_call = f"map.removeLayer(window.ol_layers['{layer_id}']); delete window.ol_layers['{layer_id}'];"
                self.web_view.page().runJavaScript(js_call)
                # Update LayerSwitcher if present
                try:
                    self.web_view.page().runJavaScript("if (window.refreshLayerSwitcher) refreshLayerSwitcher();")
                except Exception:
                    pass
                root = self.added_layers_tree.invisibleRootItem()
                (item.parent() or root).removeChild(item)
                # Clean up stored widget refs
                info = self.added_layers.get(layer_id, {})
                vw = info.get('visibility_widget')
                sw = info.get('slider_widget')
                try:
                    if vw is not None:
                        vw.deleteLater()
                except Exception:
                    pass
                try:
                    if sw is not None:
                        sw.deleteLater()
                except Exception:
                    pass
                del self.added_layers[layer_id]
        
        # Update master checkbox state after removing layers
        self.update_select_all_checkbox_state()
        self.refresh_layer_order()

    def _reattach_added_tree_widgets(self):
        """Ensure each item has its cell widgets reattached after operations like reorder."""
        try:
            for i in range(self.added_layers_tree.topLevelItemCount()):
                item = self.added_layers_tree.topLevelItem(i)
                layer_id = item.data(0, Qt.UserRole)
                info = self.added_layers.get(layer_id)
                if not info:
                    continue
                vw = info.get('visibility_widget')
                sw = info.get('slider_widget')
                if vw is not None:
                    self.added_layers_tree.setItemWidget(item, 0, vw)
                if sw is not None:
                    self.added_layers_tree.setItemWidget(item, 2, sw)
            
            # Reconnect visibility checkboxes and update master checkbox
            self.connect_visibility_checkboxes()
            self.update_select_all_checkbox_state()
        except Exception:
            pass

    def move_layer_up(self):
        selected_item = self.added_layers_tree.currentItem()
        if not selected_item:
            return
        index = self.added_layers_tree.indexOfTopLevelItem(selected_item)
        if index > 0:
            # Preserve state
            layer_id = selected_item.data(0, Qt.UserRole)
            prev_cb = self.added_layers_tree.itemWidget(selected_item, 0)
            prev_sl = self.added_layers_tree.itemWidget(selected_item, 2)
            prev_checked = prev_cb.isChecked() if prev_cb is not None else True
            prev_value = prev_sl.value() if prev_sl is not None else 100

            # Move item
            self.added_layers_tree.takeTopLevelItem(index)
            self.added_layers_tree.insertTopLevelItem(index - 1, selected_item)

            # Recreate and attach widgets with preserved state
            new_cb = QCheckBox()
            new_cb.setChecked(prev_checked)
            new_cb.stateChanged.connect(lambda state, l_id=layer_id: self.toggle_layer_visibility(l_id, state == Qt.Checked))
            self.added_layers_tree.setItemWidget(selected_item, 0, new_cb)

            new_sl = QSlider(Qt.Horizontal)
            new_sl.setRange(0, 100)
            new_sl.setValue(prev_value)
            new_sl.setToolTip("Adjust layer transparency")
            new_sl.valueChanged.connect(lambda value, l_id=layer_id: self.on_transparency_changed(l_id, value))
            self.added_layers_tree.setItemWidget(selected_item, 2, new_sl)

            # Update stored refs
            if layer_id in self.added_layers:
                self.added_layers[layer_id]['visibility_widget'] = new_cb
                self.added_layers[layer_id]['slider_widget'] = new_sl

            self.added_layers_tree.setCurrentItem(selected_item)
            self.refresh_layer_order()

    def move_layer_down(self):
        selected_item = self.added_layers_tree.currentItem()
        if not selected_item:
            return
        index = self.added_layers_tree.indexOfTopLevelItem(selected_item)
        if index < self.added_layers_tree.topLevelItemCount() - 1:
            # Preserve state
            layer_id = selected_item.data(0, Qt.UserRole)
            prev_cb = self.added_layers_tree.itemWidget(selected_item, 0)
            prev_sl = self.added_layers_tree.itemWidget(selected_item, 2)
            prev_checked = prev_cb.isChecked() if prev_cb is not None else True
            prev_value = prev_sl.value() if prev_sl is not None else 100

            # Move item
            self.added_layers_tree.takeTopLevelItem(index)
            self.added_layers_tree.insertTopLevelItem(index + 1, selected_item)

            # Recreate and attach widgets with preserved state
            new_cb = QCheckBox()
            new_cb.setChecked(prev_checked)
            new_cb.stateChanged.connect(lambda state, l_id=layer_id: self.toggle_layer_visibility(l_id, state == Qt.Checked))
            self.added_layers_tree.setItemWidget(selected_item, 0, new_cb)

            new_sl = QSlider(Qt.Horizontal)
            new_sl.setRange(0, 100)
            new_sl.setValue(prev_value)
            new_sl.setToolTip("Adjust layer transparency")
            new_sl.valueChanged.connect(lambda value, l_id=layer_id: self.on_transparency_changed(l_id, value))
            self.added_layers_tree.setItemWidget(selected_item, 2, new_sl)

            # Update stored refs
            if layer_id in self.added_layers:
                self.added_layers[layer_id]['visibility_widget'] = new_cb
                self.added_layers[layer_id]['slider_widget'] = new_sl

            self.added_layers_tree.setCurrentItem(selected_item)
            self.refresh_layer_order()

    def move_layer_to_top(self):
        selected_item = self.added_layers_tree.currentItem()
        if not selected_item:
            return
        index = self.added_layers_tree.indexOfTopLevelItem(selected_item)
        if index > 0:
            # Preserve state
            layer_id = selected_item.data(0, Qt.UserRole)
            prev_cb = self.added_layers_tree.itemWidget(selected_item, 0)
            prev_sl = self.added_layers_tree.itemWidget(selected_item, 2)
            prev_checked = prev_cb.isChecked() if prev_cb is not None else True
            prev_value = prev_sl.value() if prev_sl is not None else 100

            # Move item to top
            self.added_layers_tree.takeTopLevelItem(index)
            self.added_layers_tree.insertTopLevelItem(0, selected_item)

            # Recreate and attach widgets with preserved state
            new_cb = QCheckBox()
            new_cb.setChecked(prev_checked)
            new_cb.stateChanged.connect(lambda state, l_id=layer_id: self.toggle_layer_visibility(l_id, state == Qt.Checked))
            self.added_layers_tree.setItemWidget(selected_item, 0, new_cb)

            new_sl = QSlider(Qt.Horizontal)
            new_sl.setRange(0, 100)
            new_sl.setValue(prev_value)
            new_sl.setToolTip("Adjust layer transparency")
            new_sl.valueChanged.connect(lambda value, l_id=layer_id: self.on_transparency_changed(l_id, value))
            self.added_layers_tree.setItemWidget(selected_item, 2, new_sl)

            # Update stored refs
            if layer_id in self.added_layers:
                self.added_layers[layer_id]['visibility_widget'] = new_cb
                self.added_layers[layer_id]['slider_widget'] = new_sl

            self.added_layers_tree.setCurrentItem(selected_item)
            self.refresh_layer_order()

    def move_layer_to_bottom(self):
        selected_item = self.added_layers_tree.currentItem()
        if not selected_item:
            return
        index = self.added_layers_tree.indexOfTopLevelItem(selected_item)
        if index < self.added_layers_tree.topLevelItemCount() - 1:
            # Preserve state
            layer_id = selected_item.data(0, Qt.UserRole)
            prev_cb = self.added_layers_tree.itemWidget(selected_item, 0)
            prev_sl = self.added_layers_tree.itemWidget(selected_item, 2)
            prev_checked = prev_cb.isChecked() if prev_cb is not None else True
            prev_value = prev_sl.value() if prev_sl is not None else 100

            # Move item to bottom
            self.added_layers_tree.takeTopLevelItem(index)
            self.added_layers_tree.insertTopLevelItem(self.added_layers_tree.topLevelItemCount(), selected_item)

            # Recreate and attach widgets with preserved state
            new_cb = QCheckBox()
            new_cb.setChecked(prev_checked)
            new_cb.stateChanged.connect(lambda state, l_id=layer_id: self.toggle_layer_visibility(l_id, state == Qt.Checked))
            self.added_layers_tree.setItemWidget(selected_item, 0, new_cb)

            new_sl = QSlider(Qt.Horizontal)
            new_sl.setRange(0, 100)
            new_sl.setValue(prev_value)
            new_sl.setToolTip("Adjust layer transparency")
            new_sl.valueChanged.connect(lambda value, l_id=layer_id: self.on_transparency_changed(l_id, value))
            self.added_layers_tree.setItemWidget(selected_item, 2, new_sl)

            # Update stored refs
            if layer_id in self.added_layers:
                self.added_layers[layer_id]['visibility_widget'] = new_cb
                self.added_layers[layer_id]['slider_widget'] = new_sl

            self.added_layers_tree.setCurrentItem(selected_item)
            self.refresh_layer_order()

    def refresh_layer_order(self):
        layer_ids = []
        for i in range(self.added_layers_tree.topLevelItemCount()):
            item = self.added_layers_tree.topLevelItem(i)
            layer_id = item.data(0, Qt.UserRole)
            layer_ids.append(layer_id)
        
        layer_ids.reverse() # OpenLayers draws layers from bottom up
        js_call = f"refreshLayerOrder({json.dumps(layer_ids)});"
        self.web_view.page().runJavaScript(js_call)

    @pyqtSlot(list)
    def on_layers_reordered_by_drag(self, layer_ids):
        """Handle layer reordering when items are dragged and dropped in the tree."""
        try:
            self._reattach_added_tree_widgets()
            self.refresh_layer_order()
        except Exception as e:
            self.log_message(f"Error handling layer reordering: {e}", level=Qgis.Warning)

    def toggle_sort_order(self, event):
        self.sort_order = 'desc' if self.sort_order == 'asc' else 'asc'
        self.header_label.setText(f"Available Layers (Click to sort: {'Z-A' if self.sort_order == 'desc' else 'A-Z'})")
        self.filter_layers(self.search_box.text())

    def filter_layers(self, text):
        """
        Filter layers based on wildcard pattern (* and ? wildcards).
        If text is typed and no layers are loaded yet, automatically load them.
        
        Args:
            text: Search pattern with optional wildcards (* for any chars, ? for single char)
        """
        self.log_message(f"DEBUG filter_layers: text='{text}', all_layers count={len(self.all_layers) if self.all_layers else 0}")
        
        # Store the search text for use after loading
        self.pending_search_text = text
        
        # If text is provided but no layers loaded yet, start loading
        if text.strip() and not self.all_layers:
            self.log_message(f"DEBUG: Text provided but no layers loaded, starting layer loading")
            self.start_layer_loading()
            return
        
        # If no layers at all, just clear and return
        if not self.all_layers:
            self.log_message(f"DEBUG: No layers at all, clearing list")
            self.layers_list.clear()
            return
        
        try:
            from wildcard_filter import WildcardFilter
        except ImportError:
            try:
                from .wildcard_filter import WildcardFilter
            except ImportError:
                # Fallback: import directly if already in path
                import wildcard_filter as wf
                WildcardFilter = wf.WildcardFilter
        
        self.layers_list.clear()
        
        # If no text, show all layers
        if not text.strip():
            filtered_layers = self.all_layers[:]
            self.log_message(f"DEBUG: No search text, showing all {len(filtered_layers)} layers")
        else:
            # Use wildcard filter for pattern matching
            filtered_layers = [layer for layer in self.all_layers 
                             if WildcardFilter.matches_pattern(layer['display_name'], text)]
            self.log_message(f"DEBUG: Filtering with text '{text}', found {len(filtered_layers)} matching layers")
        
        # Sort based on current sort order
        if self.sort_order == 'asc':
            filtered_layers.sort(key=lambda x: x['display_name'])
        else:
            filtered_layers.sort(key=lambda x: x['display_name'], reverse=True)

        for layer_data in filtered_layers:
            item = QListWidgetItem(layer_data['display_name'])
            # Store the full dict to keep access to layer_type and other attributes
            item.setData(Qt.UserRole, layer_data)
            self.layers_list.addItem(item)
        
        self.log_message(f"Filtered layers: {len(filtered_layers)} results for search '{text}'")

    def toggle_base_layer(self, state):
        visible = state == Qt.Checked
        js_call = f"toggleBaseLayer({str(visible).lower()});"
        self.web_view.page().runJavaScript(js_call)


    @pyqtSlot(str, int)
    def on_transparency_changed(self, layer_id, value):
        opacity = value / 100.0
        js_call = f"setLayerOpacity('{layer_id}', {opacity});"
        self.web_view.page().runJavaScript(js_call)

    @pyqtSlot(str, bool)
    def toggle_layer_visibility(self, layer_id, visible):
        js_call = f"toggleLayerVisibility('{layer_id}', {str(visible).lower()});"
        self.web_view.page().runJavaScript(js_call)

    @pyqtSlot(str, bool)
    def layerVisibilityChanged(self, layer_id, visible):
        """Called from JS LayerSwitcher when a layer's visibility is toggled on-map.
        Sync the corresponding checkbox in the left 'Added Layers' tree.
        """
        try:
            for i in range(self.added_layers_tree.topLevelItemCount()):
                item = self.added_layers_tree.topLevelItem(i)
                if item.data(0, Qt.UserRole) == layer_id:
                    cb = self.added_layers_tree.itemWidget(item, 0)
                    if cb is not None:
                        cb.blockSignals(True)
                        cb.setChecked(visible)
                        cb.blockSignals(False)
                    break
        except Exception:
            pass

    def clear_openlayers_map(self):
        self.web_view.page().runJavaScript("clearMap();")
        self.added_layers_tree.clear()
        self.added_layers.clear()
        
        # Update the master checkbox state - disable it when no layers
        self.update_select_all_checkbox_state()

    def _on_splitter_moved(self):
        """Trigger map resize when splitter is moved to reposition controls."""
        try:
            self.web_view.page().runJavaScript("window.dispatchEvent(new Event('resize'));")
        except Exception:
            pass
    
    def _trigger_map_resize_on_load(self):
        """Trigger map resize when loading a .geos file to reposition controls."""
        try:
            self.web_view.page().runJavaScript("window.dispatchEvent(new Event('resize'));")
        except Exception:
            pass

    def toggle_full_map(self):
        """Toggle full map view by collapsing/expanding left and right panels while maintaining control positions."""
        try:
            if hasattr(self, 'splitter'):
                # Get current sizes
                current_sizes = self.splitter.sizes()
                
                # Check if we're in full map mode (left and right panels are 0)
                if current_sizes[0] == 0 and current_sizes[2] == 0:
                    # Restore to default sizes: 450, 550, 300
                    self.splitter.setSizes([450, 550, 300])
                    self.log_message("📐 Panels restored (L:450px, M:550px, R:300px)")
                    # Restore control positions after restoring panels
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(100, self._restore_control_positions)
                else:
                    # Save current control positions before collapsing
                    self._save_control_positions()
                    # Collapse to full map: set left and right panels to 0
                    self.splitter.setSizes([0, 1000, 0])
                    self.log_message("🗺️ Full map mode enabled")
                    # Reposition controls to maintain relative positions
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(100, self._reposition_controls_full_map)
        except Exception as e:
            self.log_message(f"❌ Error toggling full map: {str(e)}", level=Qgis.Warning)
    
    def _save_control_positions(self):
        """Save the relative positions of map controls."""
        try:
            js_code = """
            (function() {
                const controls = document.querySelectorAll('.ol-control');
                const positions = {};
                controls.forEach(control => {
                    const rect = control.getBoundingClientRect();
                    const mapContainer = document.querySelector('.ol-viewport');
                    if (mapContainer) {
                        const mapRect = mapContainer.getBoundingClientRect();
                        positions[control.className] = {
                            top: (rect.top - mapRect.top) / mapRect.height,
                            left: (rect.left - mapRect.left) / mapRect.width,
                            right: (mapRect.right - rect.right) / mapRect.width,
                            bottom: (mapRect.bottom - rect.bottom) / mapRect.height
                        };
                    }
                });
                window.savedControlPositions = positions;
            })();
            """
            self.web_view.page().runJavaScript(js_code)
            self.log_message("💾 Control positions saved")
        except Exception as e:
            self.log_message(f"Error saving control positions: {e}", level=Qgis.Warning)
    
    def _reposition_controls_full_map(self):
        """Reposition controls to maintain their relative positions in full map mode."""
        try:
            self.web_view.page().runJavaScript("window.dispatchEvent(new Event('resize'));")
            self.log_message("📏 Map resized, controls repositioned")
        except Exception as e:
            self.log_message(f"Error repositioning controls: {e}", level=Qgis.Warning)
    
    def _restore_control_positions(self):
        """Restore controls to their original relative positions."""
        try:
            self.web_view.page().runJavaScript("window.dispatchEvent(new Event('resize'));")
            self.log_message("📍 Map resized, controls restored")
        except Exception as e:
            self.log_message(f"Error restoring control positions: {e}", level=Qgis.Warning)
            
    def zoom_to_selected_layer(self):
        # Basic safety: ensure UI elements exist
        if not hasattr(self, 'added_layers_tree') or self.added_layers_tree is None:
            return
        selected_items = self.added_layers_tree.selectedItems()
        if not selected_items:
            return

        layer_id = selected_items[0].data(0, Qt.UserRole)
        layer_info = self.added_layers.get(layer_id)
        if not layer_info:
            return

        actual_name = layer_info['actual_name']
        if ':' in actual_name:
            workspace, layer_name = actual_name.split(':', 1)
        else:
            workspace = None
            layer_name = actual_name
        
        try:
            # 1) Query the layer endpoint to obtain the resource href
            if workspace:
                layer_url = f"{self.geoserver_url}/rest/workspaces/{workspace}/layers/{layer_name}.json"
            else:
                layer_url = f"{self.geoserver_url}/rest/layers/{layer_name}.json"
            layer_resp = requests.get(layer_url, auth=(self.username, self.password), timeout=10)
            if layer_resp.status_code != 200:
                self.log_message(f"Failed to get layer info for zoom: {layer_resp.text}", level=Qgis.Warning)
                return

            layer_data = layer_resp.json()
            resource_info = layer_data.get('layer', {}).get('resource', {})

            # 2) Follow resource href if present (FeatureType/Coverage holds actual bbox)
            extent = None
            crs = None

            resource_href = resource_info.get('href') if isinstance(resource_info, dict) else None
            if resource_href:
                # Normalize relative hrefs
                if resource_href.startswith('/'):
                    resource_href = f"{self.geoserver_url}{resource_href}"
                elif not resource_href.lower().startswith('http'):
                    # e.g., 'rest/layers/ws:layer.json'
                    sep = '' if self.geoserver_url.endswith('/') else '/'
                    resource_href = f"{self.geoserver_url}{sep}{resource_href}"
                res_resp = requests.get(resource_href, auth=(self.username, self.password), timeout=10)
                if res_resp.status_code == 200:
                    res_data = res_resp.json()
                    # FeatureType JSON typically under key 'featureType'; coverage under 'coverage'
                    res_obj = res_data.get('featureType') or res_data.get('coverage') or {}

                    # Prefer nativeBoundingBox
                    native_bbox = res_obj.get('nativeBoundingBox') if isinstance(res_obj, dict) else None
                    if native_bbox and all(k in native_bbox for k in ('minx', 'miny', 'maxx', 'maxy')):
                        extent = [float(native_bbox['minx']), float(native_bbox['miny']), float(native_bbox['maxx']), float(native_bbox['maxy'])]
                        # CRS may be in 'crs' dict or as 'srs'
                        crs_obj = native_bbox.get('crs')
                        if isinstance(crs_obj, dict):
                            crs = crs_obj.get('$') or crs_obj.get('name')
                        else:
                            crs = crs_obj
                        if not crs:
                            crs = res_obj.get('srs') or res_obj.get('nativeCRS')

                    # Fallback to latLonBoundingBox
                    if extent is None:
                        ll_bbox = res_obj.get('latLonBoundingBox') if isinstance(res_obj, dict) else None
                        if ll_bbox and all(k in ll_bbox for k in ('minx', 'miny', 'maxx', 'maxy')):
                            extent = [float(ll_bbox['minx']), float(ll_bbox['miny']), float(ll_bbox['maxx']), float(ll_bbox['maxy'])]
                            crs = 'EPSG:4326'
                else:
                    self.log_message(f"Failed to get resource info for zoom: {res_resp.text}", level=Qgis.Warning)
            else:
                # Some servers inline bbox in the layer resource minimal object (rare)
                native_bbox = resource_info.get('nativeBoundingBox') if isinstance(resource_info, dict) else None
                if native_bbox and all(k in native_bbox for k in ('minx', 'miny', 'maxx', 'maxy')):
                    extent = [float(native_bbox['minx']), float(native_bbox['miny']), float(native_bbox['maxx']), float(native_bbox['maxy'])]
                    crs = 'EPSG:4326'

            if extent:
                # Normalize CRS to a standard EPSG:xxxx form for OL transform
                norm_crs = crs or 'EPSG:4326'
                if isinstance(norm_crs, str):
                    norm_upper = norm_crs.upper()
                    # Extract EPSG code if present in URN or text
                    if 'EPSG' in norm_upper:
                        import re
                        m = re.search(r"EPSG[:/\\s]*([0-9]{3,5})", norm_upper)
                        if m:
                            norm_crs = f"EPSG:{m.group(1)}"
                        else:
                            norm_crs = 'EPSG:4326'
                    else:
                        norm_crs = 'EPSG:4326'
                else:
                    norm_crs = 'EPSG:4326'

                # If native bbox CRS is uncommon (not EPSG:4326 or EPSG:3857) and latLonBoundingBox exists, prefer that
                try:
                    preferred_crs = norm_crs
                    if norm_crs not in ('EPSG:4326', 'EPSG:3857') and 'res_obj' in locals():
                        ll_bbox = res_obj.get('latLonBoundingBox') if isinstance(res_obj, dict) else None
                        if ll_bbox and all(k in ll_bbox for k in ('minx', 'miny', 'maxx', 'maxy')):
                            extent = [float(ll_bbox['minx']), float(ll_bbox['miny']), float(ll_bbox['maxx']), float(ll_bbox['maxy'])]
                            preferred_crs = 'EPSG:4326'
                            self.log_message(f"Using latLonBoundingBox for zoom due to uncommon CRS {norm_crs}.")
                    js_extent = json.dumps(extent)
                    js_crs = json.dumps(preferred_crs)
                    js_call = f"zoomToLayer({js_extent}, {js_crs});"
                    self.log_message(f"Calling zoomToLayer with extent={extent}, crs={preferred_crs}")
                    self.web_view.page().runJavaScript(js_call)
                except Exception as _e:
                    # Fallback to prior behavior
                    js_extent = json.dumps(extent)
                    js_crs = json.dumps(norm_crs)
                    js_call = f"zoomToLayer({js_extent}, {js_crs});"
                    self.log_message(f"Calling zoomToLayer (fallback) with extent={extent}, crs={norm_crs}")
                    self.web_view.page().runJavaScript(js_call)
            else:
                self.log_message(f"No valid extent found for {actual_name}.", level=Qgis.Warning)
        except Exception as e:
            self.log_message(f"Error zooming to layer {actual_name}: {e}", level=Qgis.Critical)

    def toggle_select_all_layers(self, state):
        """Toggle visibility for all layers in the map layers tree."""
        # Delegate to the master visibility handler
        self.master_visibility_handler.toggle_select_all_layers(state)

    def connect_visibility_checkboxes(self):
        """Connect all visibility checkboxes to update the master checkbox state."""
        # Delegate to the master visibility handler
        self.master_visibility_handler.connect_visibility_checkboxes()
    
    def update_select_all_checkbox_state(self):
        """Update the Select All checkbox state based on layer visibility."""
        # Delegate to the master visibility handler
        self.master_visibility_handler.update_select_all_checkbox_state()

    def toggle_base_layer(self, state):
        visible = state == Qt.Checked
        js_call = f"toggleBaseLayer({str(visible).lower()});"
        self.web_view.page().runJavaScript(js_call)

    def on_added_layer_double_clicked(self, item, column):
        """Handle double-click on an added layer to zoom to its extent."""
        self.log_message(f"🔍 Double-clicked on layer in tree: {item.text(1) if item else 'None'}, column: {column}")
        
        # Make sure the item is selected
        if item:
            self.added_layers_tree.setCurrentItem(item)
            
            # Get the layer ID directly from the clicked item
            layer_id = item.data(0, Qt.UserRole)
            self.log_message(f"🔍 Double-clicked layer ID: {layer_id}")
            
            # Call zoom_to_selected_layer which will use the selected item
            self.zoom_to_selected_layer()

    def _get_map_state(self):
        """Get the current map state including layers, order, visibility, transparency, and view."""
        # Get layer information
        layers_data = []
        layer_ids = []
        
        for i in range(self.added_layers_tree.topLevelItemCount()):
            item = self.added_layers_tree.topLevelItem(i)
            layer_id = item.data(0, Qt.UserRole)
            layer_info = self.added_layers.get(layer_id, {})
            
            # Get visibility state
            visibility_widget = self.added_layers_tree.itemWidget(item, 0)
            is_visible = visibility_widget.isChecked() if visibility_widget else True
            
            # Get transparency state
            slider_widget = self.added_layers_tree.itemWidget(item, 2)
            transparency = slider_widget.value() if slider_widget else 100
            
            layers_data.append({
                'layer_id': layer_id,
                'display_name': layer_info.get('display_name', ''),
                'actual_name': layer_info.get('actual_name', ''),
                'layer_type': layer_info.get('layer_type', 'WMS'),
                'visible': is_visible,
                'transparency': transparency
            })
            layer_ids.append(layer_id)
        
        # Reverse layer order for OpenLayers (draws from bottom up)
        layer_ids.reverse()
        
        # Get map view state from JavaScript
        js_code = "JSON.stringify(getMapView());"
        # We'll need to handle this asynchronously
        
        # Get theme state
        theme_state = {
            'is_dark_theme': self.is_dark_theme,
            'base_layer_visible': not self.rb_base_none.isChecked()
        }
        
        return {
            'layers': layers_data,
            'layer_order': layer_ids,
            'theme': theme_state
            # view_state will be added when we get it from JavaScript
        }
    
    def _on_save_state(self):
        """Save the current map state to a .geos file."""
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Map State", 
            "", 
            "GeoServer Map Files (*.geos)"
        )
        
        if not file_path:
            return
        
        # Ensure .geos extension
        if not file_path.endswith('.geos'):
            file_path += '.geos'
        
        try:
            # Get map view state from JavaScript
            js_code = "JSON.stringify(getMapView());"
            
            def save_with_view(view_state_json):
                try:
                    view_state = json.loads(view_state_json) if view_state_json else {}
                    
                    # Get complete state
                    map_state = self._get_map_state()
                    map_state['view'] = view_state
                    
                    # Now get controls layout and then write file
                    def save_with_layout(layout_json):
                        try:
                            controls_layout = json.loads(layout_json) if layout_json else {}
                            
                            # Save to config file
                            config = configparser.ConfigParser()
                            
                            # Add general section
                            config['General'] = {
                                'layer_count': str(len(map_state['layers']))
                            }
                            
                            # Add theme section
                            config['Theme'] = {
                                'is_dark_theme': str(map_state['theme']['is_dark_theme']),
                                'base_layer_visible': str(map_state['theme']['base_layer_visible'])
                            }
                            
                            # Add view section
                            config['View'] = {
                                'center': json.dumps(view_state.get('center', [])),
                                'zoom': str(view_state.get('zoom', 2)),
                                'extent': json.dumps(view_state.get('extent', []))
                            }
                            
                            # Add controls layout section
                            config['Controls'] = {
                                'layout': json.dumps(controls_layout)
                            }
                            
                            # Add layers
                            for i, layer in enumerate(map_state['layers']):
                                section_name = f'Layer_{i}'
                                config[section_name] = {
                                    'layer_id': layer['layer_id'],
                                    'display_name': layer['display_name'],
                                    'actual_name': layer['actual_name'],
                                    'layer_type': layer['layer_type'],
                                    'visible': str(layer['visible']),
                                    'transparency': str(layer['transparency'])
                                }
                            
                            # Add layer order
                            config['LayerOrder'] = {
                                'order': json.dumps(map_state['layer_order'])
                            }
                            
                            with open(file_path, 'w') as configfile:
                                config.write(configfile)
                            
                            QMessageBox.information(self, "Save Successful", f"Map state saved to {file_path}")
                            self.setWindowTitle(f"Q2G Layer Preview - {os.path.basename(file_path)}")
                        except Exception as e:
                            QMessageBox.critical(self, "Save Error", f"Failed to save map state: {str(e)}")
                    
                    # Call JavaScript to get controls layout
                    self.web_view.page().runJavaScript("JSON.stringify(getControlsLayout());", save_with_layout)
                except Exception as e:
                    QMessageBox.critical(self, "Save Error", f"Failed to save map state: {str(e)}")
            
            # Call JavaScript function to get view state
            self.web_view.page().runJavaScript(js_code, save_with_view)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save map state: {str(e)}")
    
    def _on_load_state(self):
        """Load a map state from a .geos file."""
        from PyQt5.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Load Map State", 
            "", 
            "GeoServer Map Files (*.geos)"
        )
        
        if not file_path or not os.path.exists(file_path):
            return
        
        try:
            # Clear current map
            self.clear_openlayers_map()
            
            # Load config file
            config = configparser.ConfigParser()
            config.read(file_path)
            
            # Load theme settings
            if 'Theme' in config:
                self.is_dark_theme = config.getboolean('Theme', 'is_dark_theme', fallback=False)
                base_visible = config.getboolean('Theme', 'base_layer_visible', fallback=True)
                # Update base map radio buttons based on loaded state
                if base_visible:
                    if self.is_dark_theme:
                        self.rb_base_dark.setChecked(True)
                    else:
                        self.rb_base_light.setChecked(True)
                else:
                    self.rb_base_none.setChecked(True)
                
                # Apply theme to map
                js_call = f"toggleDarkMode({str(self.is_dark_theme).lower()});"
                self.web_view.page().runJavaScript(js_call)
                js_call = f"toggleBaseLayer({str(base_visible).lower()});"
                self.web_view.page().runJavaScript(js_call)
            
            # Load layers
            layers_to_add = []
            for section_name in config.sections():
                if section_name.startswith('Layer_'):
                    layer_info = {
                        'layer_id': config.get(section_name, 'layer_id', fallback=''),
                        'display_name': config.get(section_name, 'display_name', fallback=''),
                        'actual_name': config.get(section_name, 'actual_name', fallback=''),
                        'layer_type': config.get(section_name, 'layer_type', fallback='WMS'),
                        'visible': config.getboolean(section_name, 'visible', fallback=True),
                        'transparency': config.getint(section_name, 'transparency', fallback=100)
                    }
                    layers_to_add.append(layer_info)
            
            # Add layers to map
            for layer_info in layers_to_add:
                # Add to UI tree
                label_text = f"{layer_info['display_name']} ({layer_info['layer_type']})"
                tree_item = QTreeWidgetItem(self.added_layers_tree)
                tree_item.setText(1, label_text)
                tree_item.setData(0, Qt.UserRole, layer_info['layer_id'])
                
                # Add visibility checkbox
                visibility_checkbox = QCheckBox()
                visibility_checkbox.setChecked(layer_info['visible'])
                visibility_checkbox.stateChanged.connect(
                    lambda state, l_id=layer_info['layer_id']: 
                    self.toggle_layer_visibility(l_id, state == Qt.Checked)
                )
                self.added_layers_tree.setItemWidget(tree_item, 0, visibility_checkbox)
                
                # Add transparency slider
                slider = QSlider(Qt.Horizontal)
                slider.setRange(0, 100)
                slider.setValue(layer_info['transparency'])
                slider.setToolTip("Adjust layer transparency")
                slider.valueChanged.connect(
                    lambda value, l_id=layer_info['layer_id']: 
                    self.on_transparency_changed(l_id, value)
                )
                self.added_layers_tree.setItemWidget(tree_item, 2, slider)
                
                # Store layer info
                self.added_layers[layer_info['layer_id']] = {
                    'display_name': layer_info['display_name'],
                    'actual_name': layer_info['actual_name'],
                    'item': tree_item,
                    'layer_type': layer_info['layer_type'],
                    'visibility_widget': visibility_checkbox,
                    'slider_widget': slider
                }
                
                # Add to map via JavaScript
                js_call = ""
                if layer_info['layer_type'] == 'WMS':
                    wms_url = f"{self.geoserver_url}/wms"
                    js_call = f"addWmsLayer('{wms_url}', '{layer_info['actual_name']}', '{layer_info['layer_id']}');"
                elif layer_info['layer_type'] == 'WFS':
                    wfs_url = f"{self.geoserver_url}/ows"
                    js_call = f"addWfsLayer('{wfs_url}', '{layer_info['actual_name']}', '{layer_info['layer_id']}');"
                elif layer_info['layer_type'] == 'WMTS':
                    wmts_url = f"{self.geoserver_url}/gwc/service/wmts"
                    js_call = f"addWmtsLayer('{wmts_url}', '{layer_info['actual_name']}', '{layer_info['layer_id']}');"
                
                if js_call:
                    self.web_view.page().runJavaScript(js_call)
                    # Ensure the LayerSwitcher shows a friendly title, consistent with left tree
                    try:
                        self.web_view.page().runJavaScript(
                            f"setLayerTitle('{layer_info['layer_id']}', {json.dumps(label_text)});"
                        )
                    except Exception:
                        pass
                    
                    # Set visibility and transparency
                    if not layer_info['visible']:
                        js_call = f"toggleLayerVisibility('{layer_info['layer_id']}', false);"
                        self.web_view.page().runJavaScript(js_call)
                    
                    if layer_info['transparency'] != 100:
                        opacity = layer_info['transparency'] / 100.0
                        js_call = f"setLayerOpacity('{layer_info['layer_id']}', {opacity});"
                        self.web_view.page().runJavaScript(js_call)
            
            # Restore layer order
            if 'LayerOrder' in config:
                try:
                    layer_order = json.loads(config.get('LayerOrder', 'order'))
                    # Reverse the order for OpenLayers (bottom to top)
                    layer_order.reverse()
                    js_call = f"refreshLayerOrder({json.dumps(layer_order)});"
                    self.web_view.page().runJavaScript(js_call)
                except Exception as e:
                    self.log_message(f"Error restoring layer order: {e}", level=Qgis.Warning)
            
            # Restore map view
            if 'View' in config:
                try:
                    center = json.loads(config.get('View', 'center', fallback='[]'))
                    zoom = config.getfloat('View', 'zoom', fallback=2.0)
                    
                    if center and len(center) == 2:
                        js_call = f"setMapView([{center[0]}, {center[1]}], {zoom});"
                        self.web_view.page().runJavaScript(js_call)
                except Exception as e:
                    self.log_message(f"Error restoring map view: {e}", level=Qgis.Warning)
            
            # NOTE: Do NOT adjust tree widget height when loading state
            # This preserves the minimum height set in left_panel.py
            # self._adjust_tree_widget_height()  # Commented out to fix height issue
            
            # Save current control positions before removing them
            self._save_control_positions()
            
            # Turn off all controls first
            for control_name in self.control_checkboxes.keys():
                js_call = f"removeControl('{control_name}');"
                self.web_view.page().runJavaScript(js_call)
            
            # Reload controls from ini file automatically
            self.right_panel._load_controls_state()
            for control_name, checkbox in self.control_checkboxes.items():
                if checkbox.isChecked():
                    self._on_control_checkbox_changed(control_name, Qt.Checked)
            
            # Trigger map resize to reposition controls with saved relative positions
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self._trigger_map_resize_on_load)
            
            # Connect visibility checkboxes and update master checkbox state
            self.connect_visibility_checkboxes()
            self.update_select_all_checkbox_state()
            
            # Show success dialog
            QMessageBox.information(self, "Load Successful", f"Map state loaded from {file_path}")
            self.setWindowTitle(f"Q2G Layer Preview - {os.path.basename(file_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load map state: {str(e)}")
            self.log_message(f"Error loading map state: {str(e)}", level=Qgis.Critical)
    
    def get_library_mode(self):
        """Get the current library mode (Local or CDN)."""
        try:
            if hasattr(self, 'right_panel') and self.right_panel:
                return self.right_panel.get_library_mode()
            return 'CDN'  # Default
        except Exception:
            return 'CDN'  # Default
    
    def _adjust_tree_widget_height(self):
        """Adjust the height of the added_layers_tree to fit its content."""
        try:
            if hasattr(self, 'added_layers_tree') and self.added_layers_tree:
                # Get the current minimum height (set in left_panel.py)
                current_min_height = self.added_layers_tree.minimumHeight()
                
                # Calculate total height needed
                total_height = self.added_layers_tree.header().height()
                
                # Add height for each item
                for i in range(self.added_layers_tree.topLevelItemCount()):
                    item = self.added_layers_tree.topLevelItem(i)
                    if item:
                        total_height += self.added_layers_tree.itemDelegate().sizeHint(None, item).height()
                
                # Add some padding
                total_height += 10
                
                # Only adjust the maximum height, preserve the minimum height
                # This ensures the tree widget doesn't shrink below the minimum height set in left_panel.py
                max_height = max(current_min_height, min(total_height, 600))
                
                # Only set the maximum height, don't modify the minimum height
                self.added_layers_tree.setMaximumHeight(max_height)
                
                self.log_message(f"Adjusted tree widget height: current_min={current_min_height}px, max={max_height}px")
        except Exception as e:
            self.log_message(f"Error adjusting tree widget height: {e}", level=Qgis.Warning)

    def closeEvent(self, event):
        """Handle dialog close event."""
        try:
            self.log_message("🔒 Preview dialog closing...")
            
            # Save control states to ini file on exit
            try:
                if hasattr(self, 'right_panel') and self.right_panel:
                    self.log_message("💾 Saving control states on exit...")
                    self.right_panel._save_controls_state()
            except Exception as e:
                self.log_message(f"⚠️ Could not save control states: {e}", level=Qgis.Warning)
            
            # Clean up resources
            if hasattr(self, 'loading_thread') and self.loading_thread:
                self.loading_thread.quit()
                self.loading_thread.wait()
            event.accept()
        except Exception as e:
            self.log_message(f"Error in closeEvent: {str(e)}", level=Qgis.Warning)
            event.accept()
    
    def _on_save_as_state(self):
        """Save the current map state to a new .geos file."""
        # This is the same as save for now
        self._on_save_state()
