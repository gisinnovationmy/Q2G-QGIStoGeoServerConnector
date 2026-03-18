import os
import configparser
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox, QPushButton, 
    QLabel, QRadioButton, QButtonGroup, QSpinBox
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap

# Try to import Qgis for logging levels
try:
    from qgis.core import Qgis
except ImportError:
    # Fallback for non-QGIS contexts
    class Qgis:
        Info = 0
        Warning = 1
        Critical = 2

class RightPanel(QWidget):
    def __init__(self, is_dark_theme, parent=None, plugin_dir=None):
        super().__init__(parent)
        self.is_dark_theme = is_dark_theme
        self.plugin_dir = plugin_dir or os.path.dirname(os.path.abspath(__file__))
        self.controls_ini_path = os.path.join(self.plugin_dir, 'controls.ini')
        self._init_ui()
        self._load_controls_state()

    def _init_ui(self):
        # Create main layout with minimal margins
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)  # Padding inside
        main_layout.setSpacing(6)  # Space between widgets
        
        # Add border and styling to the panel (no margin/padding to avoid cutting)
        self.setStyleSheet("""
            RightPanel {
                border: 1px solid #cccccc;
                border-radius: 0px;
                background-color: white;
                margin: 0px;
                padding: 0px;
            }
        """)

        controls_group = QGroupBox("Map Controls")
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(4)

        # Keep only Zoom Control and Scale Control
        control_names = [
            "Zoom Control", "Scale Control", "Layer Control", "Attribution Control",
            "ZoomSlider Control", "OverviewMap Control", "Mouse Position Control",
            "Mode Indicator"
        ]
        self.control_checkboxes = {}
        for name in control_names:
            cb = QCheckBox(name)
            self.control_checkboxes[name] = cb
            controls_layout.addWidget(cb)

        controls_group.setLayout(controls_layout)
        main_layout.addWidget(controls_group)

        # Add spacing between controls and buttons
        main_layout.addSpacing(10)
        
        # Add Library Mode group (Local vs CDN)
        library_group = QGroupBox("JavaScript Library Mode")
        library_layout = QHBoxLayout()
        self.rb_lib_local = QRadioButton("📁 Local")
        self.rb_lib_cdn = QRadioButton("☁️ CDN")
        self.rb_lib_cdn.setChecked(True)  # Default to CDN (safer - no server needed)
        library_layout.addWidget(self.rb_lib_local)
        library_layout.addWidget(self.rb_lib_cdn)
        library_group.setLayout(library_layout)
        # Group for exclusive selection
        self.library_mode_group = QButtonGroup(self)
        self.library_mode_group.addButton(self.rb_lib_local)
        self.library_mode_group.addButton(self.rb_lib_cdn)
        main_layout.addWidget(library_group)
        
        # Add Local Server Port configuration (hidden by default)
        self.port_group = QGroupBox("Local Server Configuration")
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("Port:"))
        self.port_spinbox = QSpinBox()
        self.port_spinbox.setMinimum(1024)
        self.port_spinbox.setMaximum(65535)
        self.port_spinbox.setValue(8765)
        self.port_spinbox.setToolTip("Port for local OpenLayers library server (1024-65535)")
        port_layout.addWidget(self.port_spinbox)
        port_layout.addStretch()
        self.restart_server_btn = QPushButton("🔄 Restart Server")
        self.restart_server_btn.setToolTip("Restart the HTTP server on the configured port")
        self.restart_server_btn.setMinimumHeight(32)
        port_layout.addWidget(self.restart_server_btn)
        self.port_group.setLayout(port_layout)
        self.port_group.setVisible(False)  # Hidden by default
        main_layout.addWidget(self.port_group)
        
        # Add spacing after port config
        main_layout.addSpacing(10)
        
        # Add Full Map button
        self.full_map_btn = QPushButton("🗺️ Full Map")
        self.full_map_btn.setToolTip("Collapse panels to view full map")
        self.full_map_btn.setMinimumHeight(32)
        main_layout.addWidget(self.full_map_btn)
        
        # Add reload layers button
        self.cache_reset_btn = QPushButton("🔄 Reload Map and Layers")
        self.cache_reset_btn.setToolTip("Reload the map and refresh all layers")
        self.cache_reset_btn.setMinimumHeight(32)
        main_layout.addWidget(self.cache_reset_btn)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _load_controls_state(self):
        """Load control checkbox states, base map mode, and library mode from controls.ini file."""
        # Initialize defaults
        self.saved_base_map_mode = 'Light Mode'
        self.saved_library_mode = 'CDN'
        
        if not os.path.exists(self.controls_ini_path):
            # Create default ini file with all controls off
            self._create_default_controls_ini()
            return
        
        try:
            config = configparser.ConfigParser()
            config.read(self.controls_ini_path)
            
            if 'controls' in config:
                for control_name, checkbox in self.control_checkboxes.items():
                    # Get state from ini, default to False (unchecked)
                    state = config.getboolean('controls', control_name, fallback=False)
                    checkbox.setChecked(state)
            
            # Load base map mode if available
            if 'settings' in config:
                base_map_mode = config.get('settings', 'base_map_mode', fallback='Light Mode')
                self.saved_base_map_mode = base_map_mode
                
                # Load library mode if available
                library_mode = config.get('settings', 'library_mode', fallback='CDN')
                self.saved_library_mode = library_mode
                if library_mode == 'Local':
                    self.rb_lib_local.setChecked(True)
                    # Show port configuration if Local was saved
                    self.port_group.setVisible(True)
                else:
                    self.rb_lib_cdn.setChecked(True)
                    # Hide port configuration if CDN was saved
                    self.port_group.setVisible(False)
        except Exception as e:
            print(f"Error loading controls state: {e}")
    
    def _create_default_controls_ini(self):
        """Create default controls.ini file with all controls off, default base map mode, and library mode."""
        try:
            config = configparser.ConfigParser()
            config['controls'] = {}
            
            for control_name in self.control_checkboxes.keys():
                config['controls'][control_name] = 'False'
            
            # Add default settings section with base map mode and library mode
            config['settings'] = {
                'base_map_mode': 'Light Mode',
                'library_mode': 'CDN'
            }
            
            with open(self.controls_ini_path, 'w') as f:
                config.write(f)
        except Exception as e:
            print(f"Error creating default controls.ini: {e}")
    
    def _save_controls_state(self, base_map_mode=None, library_mode=None):
        """Save control checkbox states, base map mode, and library mode to controls.ini file."""
        try:
            config = configparser.ConfigParser()
            config['controls'] = {}
            
            for control_name, checkbox in self.control_checkboxes.items():
                config['controls'][control_name] = str(checkbox.isChecked())
            
            # Determine library mode
            if library_mode is None:
                if self.rb_lib_local.isChecked():
                    library_mode = 'Local'
                else:
                    library_mode = 'CDN'
            
            # Save base map mode and library mode
            config['settings'] = {
                'base_map_mode': base_map_mode or getattr(self, 'saved_base_map_mode', 'Light Mode'),
                'library_mode': library_mode
            }
            
            with open(self.controls_ini_path, 'w') as f:
                config.write(f)
        except Exception as e:
            print(f"Error saving controls state: {e}")

    def connect_signals(self, main_dialog):
        """Connect all widget signals to the main dialog's slots."""
        # Store reference to main dialog for library mode changes
        self.main_dialog = main_dialog
        
        # Connect all control checkboxes
        for name, cb in self.control_checkboxes.items():
            cb.stateChanged.connect(lambda state, n=name: self._on_checkbox_changed(n, state, main_dialog))
        
        # Connect library mode radio buttons
        self.rb_lib_local.toggled.connect(lambda checked: self._on_library_mode_toggled(checked))
        self.rb_lib_cdn.toggled.connect(lambda: self._on_library_mode_changed())
        
        # Connect restart server button
        self.restart_server_btn.clicked.connect(lambda: self._on_restart_server_clicked())
        
        # Connect Full Map button
        try:
            if hasattr(main_dialog, 'toggle_full_map'):
                self.full_map_btn.clicked.connect(main_dialog.toggle_full_map)
            else:
                print("DEBUG: toggle_full_map method not found on main_dialog")
        except Exception as e:
            print(f"DEBUG: Error connecting full_map_btn: {e}")
        
        # Connect reload layers button
        try:
            if hasattr(main_dialog, 'clear_cache_and_reload'):
                self.cache_reset_btn.clicked.connect(main_dialog.clear_cache_and_reload)
            else:
                print("DEBUG: clear_cache_and_reload method not found on main_dialog")
                # Fallback to a wrapper that logs the error
                self.cache_reset_btn.clicked.connect(lambda: self._on_cache_reset_clicked())
        except Exception as e:
            print(f"DEBUG: Error connecting cache_reset_btn: {e}")
            self.cache_reset_btn.clicked.connect(lambda: self._on_cache_reset_clicked())
    
    def _on_cache_reset_clicked(self):
        """Fallback handler for cache reset button if clear_cache_and_reload is not available."""
        try:
            if hasattr(self, 'main_dialog') and self.main_dialog:
                if hasattr(self.main_dialog, 'clear_cache_and_reload'):
                    self.main_dialog.clear_cache_and_reload()
                else:
                    print("DEBUG: clear_cache_and_reload method not available")
                    if hasattr(self.main_dialog, 'log_message'):
                        self.main_dialog.log_message("❌ Reload function not available", level=Qgis.Warning)
        except Exception as e:
            print(f"DEBUG: Error in _on_cache_reset_clicked: {e}")
            import traceback
            traceback.print_exc()
    
    def _on_checkbox_changed(self, control_name, state, main_dialog):
        """Handle checkbox state change and save to ini file."""
        # Call the main dialog's handler
        main_dialog._on_control_checkbox_changed(control_name, state)
        # Save the new state to ini file
        self._save_controls_state()
    
    def _on_library_mode_toggled(self, checked):
        """Handle Local radio button toggle to show/hide port configuration."""
        if checked:
            # Local mode selected - show port configuration
            self.port_group.setVisible(True)
        else:
            # CDN mode selected - hide port configuration
            self.port_group.setVisible(False)
        self._on_library_mode_changed()
    
    def _on_library_mode_changed(self):
        """Handle library mode change and save to ini file."""
        self._save_controls_state()
        # Reload map for both CDN and Local modes
        if hasattr(self, 'main_dialog') and self.main_dialog:
            try:
                if self.rb_lib_local.isChecked():
                    # Local mode: reload map and start server automatically
                    self.main_dialog.log_message("🔄 Switching to Local library mode...")
                    self.main_dialog.log_message("🚀 HTTP server will start automatically on the configured port")
                else:
                    # CDN mode: reload immediately
                    self.main_dialog.log_message("🔄 Switching to CDN library mode...")
                
                # Update the library mode indicator immediately (will be properly updated after reload too)
                current_mode = self.get_library_mode()
                try:
                    # Try to update the indicator immediately for better user feedback
                    if hasattr(self.main_dialog, 'web_view') and self.main_dialog.web_view:
                        js_call = f"updateLibraryModeIndicator('{current_mode}');"
                        self.main_dialog.web_view.page().runJavaScript(js_call)
                        self.main_dialog.log_message(f"Updating library mode indicator to: {current_mode} mode")
                except Exception as e:
                    print(f"DEBUG: Could not update indicator immediately: {e}")
                    self.main_dialog.log_message(f"Could not update indicator immediately: {e}", level=Qgis.Warning)
                
                # Ensure we capture the current map state before reloading
                try:
                    # First ensure we save the current map state
                    self.main_dialog.log_message("📸 Capturing current map state before library mode change...")
                    
                    # Use a short delay to ensure UI updates before reloading
                    QTimer.singleShot(100, lambda: self._reload_map_html_only())                
                except Exception as e:
                    print(f"DEBUG: Error during library mode change: {e}")
                    self.main_dialog.log_message(f"❌ Error during library mode change: {e}", level=Qgis.Warning)
                    # Still try to reload even if there was an error
                    QTimer.singleShot(100, lambda: self._reload_map_html_only())
            except Exception as e:
                print(f"DEBUG: Outer exception in _on_library_mode_changed: {e}")
                import traceback
                traceback.print_exc()
    
    def _on_restart_server_clicked(self):
        """Handle Restart Server button click - restarts HTTP server on configured port."""
        try:
            if hasattr(self, 'main_dialog') and self.main_dialog:
                port = self.port_spinbox.value()
                self.main_dialog.log_message(f"🔄 Restarting HTTP server on port {port}...")
                # Reload map which will restart the server on the new port
                self._reload_map_html_only()
                self.main_dialog.log_message(f"✅ Server restarted on port {port}")
        except Exception as e:
            self.main_dialog.log_message(f"❌ Error restarting server: {e}")
            print(f"Error restarting server: {e}")
    
    def _reload_map_html_only(self):
        """Reload map HTML with new library mode while preserving current state.
        
        This method reloads the map HTML with the new library mode (CDN or Local),
        then uses clear_cache_and_reload to restore the map state after loading.
        It does NOT reload the layers list from GeoServer - the layers list stays as is.
        """
        try:
            if not hasattr(self, 'main_dialog') or not self.main_dialog:
                print("DEBUG: main_dialog not available in _reload_map_html_only")
                return
            
            self.main_dialog.log_message("🔄 Switching library mode and reloading map...")
            
            # Create temporary file path for map state
            import tempfile
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, 'geovirtuallis_library_toggle_tmp.geos')
            
            # Save current map state to temp file
            self.main_dialog.log_message("💾 Saving map state to temporary file...")
            try:
                if hasattr(self.main_dialog, '_save_map_state_to_file'):
                    self.main_dialog._save_map_state_to_file(temp_file)
                else:
                    print("DEBUG: _save_map_state_to_file method not found on main_dialog")
            except Exception as e:
                print(f"DEBUG: Error saving map state: {e}")
                self.main_dialog.log_message(f"⚠️ Could not save map state: {e}", level=Qgis.Warning)
            
            # Save controls state before reloading
            self.main_dialog.log_message("Saving controls state before toggling...")
            self._save_controls_state()
            
            # Set a flag to indicate we need to reload after map loads
            if hasattr(self.main_dialog, '_reload_after_library_change'):
                self.main_dialog._reload_after_library_change = True
                self.main_dialog._library_toggle_temp_file = temp_file
            else:
                print("DEBUG: _reload_after_library_change attribute not found on main_dialog")
            
            # Regenerate the HTML with the new library mode
            # This will pick up the current library_mode from get_library_mode()
            if hasattr(self.main_dialog, 'initialize_openlayers_map'):
                self.main_dialog.log_message("🔄 Regenerating map HTML with new library mode...")
                self.main_dialog.initialize_openlayers_map(self.main_dialog.web_view)
            else:
                print("DEBUG: initialize_openlayers_map method not found on main_dialog")
                self.main_dialog.log_message("❌ Could not regenerate map HTML", level=Qgis.Warning)
            
            # The map state will be restored from the temp file
            # in on_webview_load_finished() after the HTML has fully loaded
        except Exception as e:
            print(f"DEBUG: Error reloading map with new library mode: {e}")
            import traceback
            traceback.print_exc()
            if hasattr(self, 'main_dialog') and self.main_dialog:
                self.main_dialog.log_message(f"❌ Error reloading map with new library mode: {e}", level=Qgis.Warning)
    
    def get_library_mode(self):
        """Get current library mode (Local or CDN)."""
        if self.rb_lib_local.isChecked():
            return 'Local'
        else:
            return 'CDN'
    
    def get_local_server_port(self):
        """Get the configured port for local library server."""
        return self.port_spinbox.value()
