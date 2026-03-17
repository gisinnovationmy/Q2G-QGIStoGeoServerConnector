"""
First Load Dialog - Welcome screen for new users
Shows important setup information on first plugin load
"""

import os
import sys
import configparser
import importlib.util
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QCheckBox, QScrollArea, QWidget, QMessageBox
)
from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QFont, QIcon
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices

# Ensure we load modules from the same folder as this file
# Handle case when running via exec() where __file__ may point to non-existent path
_CURRENT_DIR = None
try:
    _candidate = os.path.dirname(os.path.abspath(__file__))
    if os.path.isdir(_candidate) and os.path.exists(os.path.join(_candidate, 'first_load_dialog.py')):
        _CURRENT_DIR = _candidate
except NameError:
    pass

if _CURRENT_DIR is None:
    # Try QGIS plugin path if available
    try:
        from qgis.core import QgsApplication
        plugin_root = QgsApplication.pluginPath()
        _candidate = os.path.join(plugin_root, "geoserverconnector")
        if os.path.isdir(_candidate) and os.path.exists(os.path.join(_candidate, 'first_load_dialog.py')):
            _CURRENT_DIR = _candidate
    except Exception:
        pass

if _CURRENT_DIR is None:
    # Final fallback: current working directory or home
    _CURRENT_DIR = os.getcwd() if os.getcwd() else os.path.expanduser("~")

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


class FirstLoadDialog(QDialog):
    """Welcome dialog shown on first plugin load"""
    
    def __init__(self, parent=None, plugin_dir=None):
        super().__init__(parent)
        self.plugin_dir = plugin_dir
        self.controls_ini = os.path.join(plugin_dir, 'controls.ini') if plugin_dir else None
        
        self.setWindowTitle("🌐 Welcome to GeoServerConnector")
        self.setGeometry(100, 100, 700, 550)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333333;
            }
            QCheckBox {
                color: #333333;
            }
        """)
        
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("🌐 Welcome to GeoServerConnector")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)
        layout.addLayout(header_layout)
        
        # Separator
        separator = QLabel("─" * 80)
        layout.addWidget(separator)
        
        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: white; }")
        
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(15)
        
        # Content sections
        content_layout.addWidget(self._create_section(
            "⚠️ Before You Start",
            "Please review these important requirements before using GeoServerConnector."
        ))
        
        content_layout.addWidget(self._create_section(
            "🌐 Web Components",
            "• PyQtWebEngine: Required for the Preview feature\n"
            "  - Auto-installed on first Preview use\n"
            "  - Requires internet connection (~50-100 MB)\n"
            "  - QGIS restart needed after installation\n\n"
            "• OpenLayers: Included locally"
        ))
        
        content_layout.addWidget(self._create_section(
            "🔒 GeoServer CORS Configuration",
            "CORS (Cross-Origin Resource Sharing) is recommended for the Preview feature.\n\n"
            "• Required for local/development testing\n"
            "• Good practice to enable for production use\n"
            "• Must be configured manually in GeoServer\n\n"
            "See the Documentation for setup instructions."
        ))
        
        content_layout.addWidget(self._create_section(
            "📦 GeoServer Importer Extension",
            "The Importer extension is REQUIRED for layer uploads:\n\n"
            "✓ Handles multiple file formats\n"
            "✓ Supports: Shapefile, GeoPackage, GeoTIFF, PostGIS, etc.\n"
            "✓ Enables batch uploads\n\n"
            "⚠️ Without Importer, you cannot upload layers\n\n"
            "To check if installed:\n"
            "1. Open GeoServer admin console\n"
            "2. Go to REST API → /rest/imports\n"
            "3. If you see a response, it's installed"
        ))
        
        content_layout.addWidget(self._create_section(
            "✅ Quick Checklist",
            "Before you start, make sure you have:\n\n"
            "☐ QGIS 3.x or later\n"
            "☐ GeoServer 2.20 or later\n"
            "☐ GeoServer Importer extension installed\n"
            "☐ GeoServer admin credentials\n"
            "☐ Network access to GeoServer\n"
            "☐ Internet connection (for PyQtWebEngine)\n"
            "☐ CORS enabled on GeoServer (recommended for Preview)"
        ))
        
        content_layout.addWidget(self._create_section(
            "📚 Learn More",
            "For detailed information, visit the documentation:\n\n"
            "• Web Manual: Check the 'Before You Start' section\n"
            "• Troubleshooting: Common issues and solutions\n"
            "• FAQ: Frequently asked questions"
        ))
        
        content_widget.setLayout(content_layout)
        scroll.setWidget(content_widget)
        layout.addWidget(scroll, 1)  # Give scroll area stretch priority
        
        # Separator
        separator2 = QLabel("─" * 80)
        layout.addWidget(separator2)
        
        # Checkbox
        self.dont_show_checkbox = QCheckBox("Do not show this dialog again")
        self.dont_show_checkbox.setStyleSheet("QCheckBox { color: #666666; font-size: 10px; }")
        layout.addWidget(self.dont_show_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        learn_more_btn = QPushButton("📚 Learn More")
        learn_more_btn.clicked.connect(self.open_documentation)
        button_layout.addWidget(learn_more_btn)
        
        ok_btn = QPushButton("✓ Got It!")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setMinimumWidth(100)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def _create_section(self, title, content):
        """Create a content section"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        title_label = QLabel(title)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setStyleSheet("color: #555555; line-height: 1.5;")
        layout.addWidget(content_label)
        
        widget.setLayout(layout)
        return widget
    
    def open_documentation(self):
        """Open documentation dialog on the 'Before You Start' page"""
        try:
            _doc = _load_local_module("documentation")
            DocumentationDialog = _doc.DocumentationDialog
            doc_dialog = DocumentationDialog(self, self.plugin_dir)
            # Set to "Getting Started" page (Before You Start)
            doc_dialog.page_combo.setCurrentText("Getting Started")
            doc_dialog.exec()
        except Exception as e:
            QMessageBox.warning(
                self,
                "📚 Documentation",
                f"Could not open documentation:\n{str(e)}\n\n"
                "Or contact us at: mygis@gis.my"
            )
    
    def accept(self):
        """Handle OK button click"""
        if self.dont_show_checkbox.isChecked():
            self.save_preference()
        super().accept()
    
    def save_preference(self):
        """Save 'do not show again' preference using QgsSettings (persistent across sessions)"""
        try:
            from qgis.core import QgsSettings
            settings = QgsSettings()
            settings.setValue('geoserverconnector/show_first_load_dialog', False)
            print(f"DEBUG: Saved show_first_load_dialog=False to QgsSettings")
        except Exception as e:
            print(f"Error saving preference: {e}")


def should_show_first_load_dialog(plugin_dir):
    """Check if first load dialog should be shown using QgsSettings"""
    try:
        from qgis.core import QgsSettings
        settings = QgsSettings()
        # Returns True (show dialog) if setting doesn't exist or is True
        value = settings.value('geoserverconnector/show_first_load_dialog', True, type=bool)
        print(f"DEBUG: should_show_first_load_dialog from QgsSettings: {value}")
        return value
    except Exception as e:
        print(f"Error reading preference: {e}")
        return True
