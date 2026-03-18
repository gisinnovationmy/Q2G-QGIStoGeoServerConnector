"""
First Load Dialog - Welcome screen for new users
Shows important setup information on first plugin load
"""

import os
import configparser
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QCheckBox, QScrollArea, QWidget, QMessageBox
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices


class FirstLoadDialog(QDialog):
    """Welcome dialog shown on first plugin load"""
    
    def __init__(self, parent=None, plugin_dir=None):
        super().__init__(parent)
        self.plugin_dir = plugin_dir
        self.controls_ini = os.path.join(plugin_dir, 'controls.ini') if plugin_dir else None
        
        self.setWindowTitle("🌐 Welcome to GeoServerConnector")
        self.setGeometry(100, 100, 700, 550)
        self.setWindowModality(Qt.WindowModal)
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
            "• OpenLayers & Cesium.js: Included locally"
        ))
        
        content_layout.addWidget(self._create_section(
            "🔒 GeoServer CORS Configuration",
            "CORS must be enabled for the Preview feature to work:\n\n"
            "1. Enter GeoServer credentials in the plugin\n"
            "2. Click 'Others' section\n"
            "3. Click 'Enable CORS in GeoServer' button\n"
            "4. Plugin will configure CORS automatically\n\n"
            "⚠️ CORS is only needed for Preview feature"
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
            "☐ CORS enabled on GeoServer (for Preview)"
        ))
        
        content_layout.addWidget(self._create_section(
            "📚 Learn More",
            "For detailed information, visit the documentation:\n\n"
            "• Web Manual: Check the 'Before You Start' section\n"
            "• Troubleshooting: Common issues and solutions\n"
            "• FAQ: Frequently asked questions"
        ))
        
        content_layout.addStretch()
        content_widget.setLayout(content_layout)
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
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
        """Open documentation link"""
        QMessageBox.information(
            self,
            "📚 Documentation",
            "For complete documentation, visit:\n\n"
            "Web Manual: Check the 'Before You Start' section\n\n"
            "Or contact us at: mygis@gis.my"
        )
    
    def accept(self):
        """Handle OK button click"""
        if self.dont_show_checkbox.isChecked():
            self.save_preference()
        super().accept()
    
    def save_preference(self):
        """Save 'do not show again' preference to INI file"""
        if not self.controls_ini or not os.path.exists(self.controls_ini):
            return
        
        try:
            config = configparser.ConfigParser()
            config.read(self.controls_ini)
            
            if not config.has_section('settings'):
                config.add_section('settings')
            
            config.set('settings', 'show_first_load_dialog', 'False')
            
            with open(self.controls_ini, 'w') as f:
                config.write(f)
        except Exception as e:
            print(f"Error saving preference: {e}")


def should_show_first_load_dialog(plugin_dir):
    """Check if first load dialog should be shown"""
    controls_ini = os.path.join(plugin_dir, 'controls.ini')
    
    if not os.path.exists(controls_ini):
        return True
    
    try:
        config = configparser.ConfigParser()
        config.read(controls_ini)
        
        if config.has_option('settings', 'show_first_load_dialog'):
            value = config.get('settings', 'show_first_load_dialog')
            return value.lower() == 'true'
        else:
            # First time - set to True and show dialog
            if not config.has_section('settings'):
                config.add_section('settings')
            config.set('settings', 'show_first_load_dialog', 'True')
            with open(controls_ini, 'w') as f:
                config.write(f)
            return True
    except Exception as e:
        print(f"Error reading preference: {e}")
        return True
