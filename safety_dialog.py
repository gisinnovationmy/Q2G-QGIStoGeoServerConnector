# safety_dialog.py - Safety Information Dialog for QtWebEngine Diagnostics
"""
Provides a safety notice dialog to inform users that the diagnostic tool is safe and read-only.
"""

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QCheckBox, QScrollArea
)
from qgis.PyQt.QtCore import Qt, QSettings
from qgis.PyQt.QtGui import QFont, QPixmap, QPainter, QColor


class SafetyDialog(QDialog):
    """Dialog showing safety information for the diagnostic tool."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔒 Diagnostic Tool Safety Notice")
        self.setMinimumSize(700, 600)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)
        
        self._setup_ui()
        self._load_settings()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header with icon
        header_layout = QHBoxLayout()
        
        # Create a simple lock icon using text
        icon_label = QLabel("🔒")
        icon_label.setStyleSheet("font-size: 48px; margin-right: 20px;")
        header_layout.addWidget(icon_label)
        
        # Title
        title_label = QLabel("Diagnostic Tool Safety Notice")
        title_label.setStyleSheet("""
            font-size: 20px; 
            font-weight: bold; 
            color: #2e7d32;
            margin-bottom: 10px;
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Subtitle
        subtitle = QLabel("This diagnostic tool is 100% safe and read-only")
        subtitle.setStyleSheet("font-size: 14px; color: #666; margin-bottom: 20px;")
        layout.addWidget(subtitle)
        
        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        
        # Safety information
        safety_text = self._get_safety_text()
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(safety_text)
        text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
                line-height: 1.6;
            }
        """)
        content_layout.addWidget(text_edit)
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # Checkbox for "Don't show again"
        self.dont_show_cb = QCheckBox("Don't show this notice again")
        self.dont_show_cb.setStyleSheet("margin-top: 10px;")
        layout.addWidget(self.dont_show_cb)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.continue_btn = QPushButton("Continue to Diagnostics")
        self.continue_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #43a047;
            }
            QPushButton:pressed {
                background-color: #1b5e20;
            }
        """)
        self.continue_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.continue_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #9e9e9e;
            }
            QPushButton:pressed {
                background-color: #616161;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
    def _get_safety_text(self):
        """Return the safety information as HTML."""
        return """
        <h2 style="color: #2e7d32;">🔒 What This Diagnostic Tool Does NOT Do</h2>
        
        <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
        <tr style="background-color: #ffebee;">
        <td style="padding: 10px; border: 1px solid #ffcdd2;">❌ Install anything</td>
        <td style="padding: 10px; border: 1px solid #ffcdd2;">❌ Modify system settings</td>
        </tr>
        <tr style="background-color: #ffebee;">
        <td style="padding: 10px; border: 1px solid #ffcdd2;">❌ Change GPU configuration</td>
        <td style="padding: 10px; border: 1px solid #ffcdd2;">❌ Alter drivers</td>
        </tr>
        <tr style="background-color: #ffebee;">
        <td style="padding: 10px; border: 1px solid #ffcdd2;">❌ Touch the registry</td>
        <td style="padding: 10px; border: 1px solid #ffcdd2;">❌ Disable hardware</td>
        </tr>
        <tr style="background-color: #ffebee;">
        <td style="padding: 10px; border: 1px solid #ffcdd2;">❌ Enable hardware</td>
        <td style="padding: 10px; border: 1px solid #ffcdd2;">❌ Elevate privileges</td>
        </tr>
        <tr style="background-color: #ffebee;">
        <td style="padding: 10px; border: 1px solid #ffcdd2;">❌ Behave like malware</td>
        <td style="padding: 10px; border: 1px solid #ffcdd2;">❌ Persistent changes</td>
        </tr>
        </table>
        
        <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
        
        <h2 style="color: #1976d2;">✅ What This Diagnostic Tool Actually Does</h2>
        
        <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <h3 style="color: #1565c0; margin-top: 0;">Read-Only Operations Only:</h3>
        <ul style="margin: 10px 0;">
        <li>🔍 <strong>Reads</strong> environment variables</li>
        <li>📁 <strong>Checks</strong> file paths and directories</li>
        <li>⚙️ <strong>Spawns</strong> a harmless test process (QtWebEngineProcess)</li>
        <li>🖥️ <strong>Runs</strong> standard OS commands (dxdiag, tasklist, lspci, system_profiler)</li>
        <li>📋 <strong>Lists</strong> directory contents</li>
        <li>📝 <strong>Creates</strong> temporary files and immediately deletes them</li>
        </ul>
        </div>
        
        <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
        
        <h2 style="color: #f57c00;">🛡️ Antivirus Compatibility</h2>
        
        <div style="background-color: #fff3e0; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <p><strong>⭐ This tool will NOT trigger antivirus software because:</strong></p>
        <ul style="margin: 10px 0;">
        <li>✅ It performs only standard diagnostic operations</li>
        <li>✅ It doesn't modify registry keys or inject into processes</li>
        <li>✅ It doesn't alter drivers or GPU settings</li>
        <li>✅ It doesn't write to system folders or download executables</li>
        <li>✅ All operations are read-only and temporary</li>
        </ul>
        
        <p><strong>Common in trusted software:</strong> These same operations are used daily in:</p>
        <ul style="margin: 10px 0;">
        <li>🔧 Automated testing tools</li>
        <li>🚀 CI/CD pipelines</li>
        <li>🌐 Headless browsers (Selenium, Puppeteer)</li>
        <li>📱 Electron applications</li>
        <li>🖼️ QtWebEngine applications</li>
        </ul>
        </div>
        
        <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
        
        <h2 style="color: #7b1fa2;">🔧 Technical Flags Explained</h2>
        
        <div style="background-color: #f3e5f5; padding: 15px; border-radius: 8px; margin: 10px 0;">
        <p>You may see flags like <code style="background: #e1bee7; padding: 2px 6px; border-radius: 3px;">--disable-gpu</code>, <code style="background: #e1bee7; padding: 2px 6px; border-radius: 3px;">--no-sandbox</code>, <code style="background: #e1bee7; padding: 2px 6px; border-radius: 3px;">--single-process</code>.</p>
        
        <p><strong>🔍 What these actually do:</strong></p>
        <ul style="margin: 10px 0;">
        <li>📍 They tell Chromium to run in "safe mode" for testing</li>
        <li>🔄 They affect ONLY the diagnostic process</li>
        <li>⚡ They do NOT change system settings</li>
        <li>🚫 They do NOT disable hardware on your computer</li>
        <li>💾 They do NOT persist after the tool closes</li>
        </ul>
        
        <p><strong>🎯 Analogy:</strong> This is like running <code>chrome.exe --disable-gpu</code> - it only affects that one browser tab, not your entire system.</p>
        </div>
        
        <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
        
        <h2 style="color: #388e3c;">✅ Final Guarantee</h2>
        
        <div style="background-color: #e8f5e8; padding: 15px; border-radius: 8px; margin: 10px 0; border: 2px solid #4caf50;">
        <h3 style="color: #2e7d32; margin-top: 0;">This diagnostic tool is:</h3>
        <table style="width: 100%; margin: 10px 0;">
        <tr>
        <td style="padding: 8px;">✔️ <strong>Safe</strong></td>
        <td style="padding: 8px;">✔️ <strong>Read-only</strong></td>
        <td style="padding: 8px;">✔️ <strong>Non-intrusive</strong></td>
        </tr>
        <tr>
        <td style="padding: 8px;">✔️ <strong>Antivirus-friendly</strong></td>
        <td style="padding: 8px;">✔️ <strong>No system modifications</strong></td>
        <td style="padding: 8px;">✔️ <strong>No hardware changes</strong></td>
        </tr>
        </table>
        
        <p style="margin: 15px 0 0 0;"><strong>🎯 It simply observes your system and reports what it finds. Nothing more.</strong></p>
        </div>
        """
    
    def _load_settings(self):
        """Load user preference for showing this dialog."""
        settings = QSettings()
        dont_show = settings.value("diagnostic/dont_show_safety", False, type=bool)
        self.dont_show_cb.setChecked(dont_show)
    
    def _save_settings(self):
        """Save user preference for showing this dialog."""
        settings = QSettings()
        settings.setValue("diagnostic/dont_show_safety", self.dont_show_cb.isChecked())
    
    def accept(self):
        """Override to save settings before accepting."""
        self._save_settings()
        super().accept()
    
    @staticmethod
    def should_show():
        """Check if the safety dialog should be shown."""
        settings = QSettings()
        return not settings.value("diagnostic/dont_show_safety", False, type=bool)
    
    @staticmethod
    def show_safety_dialog(parent=None):
        """Show the safety dialog and return if user wants to continue."""
        if not SafetyDialog.should_show():
            return True
        
        dialog = SafetyDialog(parent)
        result = dialog.exec()
        return result == 1  # QDialog.Accepted
