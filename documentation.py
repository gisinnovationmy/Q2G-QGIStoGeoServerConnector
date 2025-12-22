"""
Documentation viewer dialog for GeoVirtuallis QGIS Plugin.
Displays HTML documentation in a nice dialog with navigation.
"""

import os
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel
)
from qgis.PyQt.QtWebEngineWidgets import QWebEngineView
from qgis.PyQt.QtCore import Qt, QUrl
from qgis.PyQt.QtGui import QIcon


class DocumentationDialog(QDialog):
    """Dialog for displaying plugin documentation in HTML format."""
    
    def __init__(self, parent=None, plugin_dir=None):
        super().__init__(parent)
        self.setWindowTitle("GeoVirtuallis QGIS Plugin - Documentation")
        self.setMinimumSize(1000, 700)
        self.setWindowFlags(Qt.Window | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        
        self.plugin_dir = plugin_dir or os.path.dirname(os.path.abspath(__file__))
        self.manual_dir = os.path.join(self.plugin_dir, 'manual')
        
        # Documentation pages
        self.pages = {
            'Home': 'index.html',
            'Getting Started': '01-getting-started.html',
            'Installation': '02-installation.html',
            'Configuration': '03-configuration.html',
            'Layer Upload': '04-layer-upload.html',
            'Style Management': '05-style-management.html',
            'Workspace Management': '06-workspace-management.html',
            'Preview': '07-preview.html',
            'Troubleshooting': '08-troubleshooting.html',
            'Advanced Features': '09-advanced-features.html',
            'FAQ': '10-faq.html',
        }
        
        self.setup_ui()
        self.load_page('index.html')
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        # Navigation bar
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(8)
        
        # Page selector dropdown
        nav_label = QLabel("Documentation:")
        nav_layout.addWidget(nav_label)
        
        self.page_combo = QComboBox()
        self.page_combo.addItems(self.pages.keys())
        self.page_combo.currentTextChanged.connect(self.on_page_changed)
        nav_layout.addWidget(self.page_combo)
        
        nav_layout.addStretch()
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_button.setMaximumWidth(100)
        nav_layout.addWidget(close_button)
        
        layout.addLayout(nav_layout)
        
        # Web view for displaying HTML
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)
        
        self.setLayout(layout)
    
    def on_page_changed(self, page_name):
        """Handle page selection change."""
        if page_name in self.pages:
            self.load_page(self.pages[page_name])
    
    def load_page(self, filename):
        """Load an HTML page from the manual directory."""
        try:
            file_path = os.path.join(self.manual_dir, filename)
            
            if not os.path.exists(file_path):
                error_html = f"""
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; padding: 20px; }}
                        .error {{ color: #d32f2f; font-size: 16px; }}
                    </style>
                </head>
                <body>
                    <div class="error">
                        <h2>Documentation Not Found</h2>
                        <p>The documentation file could not be found at:</p>
                        <p><code>{file_path}</code></p>
                    </div>
                </body>
                </html>
                """
                self.web_view.setHtml(error_html)
                return
            
            # Load the HTML file
            file_url = QUrl.fromLocalFile(file_path)
            self.web_view.load(file_url)
            
        except Exception as e:
            error_html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 20px; }}
                    .error {{ color: #d32f2f; font-size: 16px; }}
                </style>
            </head>
            <body>
                <div class="error">
                    <h2>Error Loading Documentation</h2>
                    <p>{str(e)}</p>
                </div>
            </body>
            </html>
            """
            self.web_view.setHtml(error_html)
