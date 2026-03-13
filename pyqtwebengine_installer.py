"""
PyQtWebEngine installer dialog for handling missing QtWebEngineWidgets.
Provides one-click installation with real-time feedback.
Supports both PyQt5 (QGIS 3.16-3.26) and PyQt6 (QGIS 3.28+).
"""

import subprocess
import sys
import os
import socket
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QMessageBox, QCheckBox
)
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal
from qgis.core import QgsSettings
from qgis.PyQt.QtGui import QFont, QIcon


def detect_qt_version():
    """Detect which Qt version QGIS is using (Qt5 or Qt6)."""
    try:
        from qgis.PyQt.QtCore import QT_VERSION_STR
        qt_major = int(QT_VERSION_STR.split('.')[0])
        return qt_major
    except:
        # Default to Qt6 for newer QGIS
        return 6


def get_webengine_package_name():
    """Get the correct WebEngine package name based on Qt version."""
    qt_version = detect_qt_version()
    if qt_version >= 6:
        return "PyQt6-WebEngine"
    else:
        return "PyQt5-WebEngine"


def check_internet_connection():
    """Check if internet connection is available"""
    try:
        # Try to connect to Google DNS
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except (socket.timeout, socket.error):
        return False


class InstallThread(QThread):
    """Background thread for installing PyQt WebEngine (Qt5 or Qt6)"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, target_dir=None):
        super().__init__()
        self.target_dir = target_dir
        self.qt_version = detect_qt_version()
        self.package_name = get_webengine_package_name()
    
    def run(self):
        try:
            # First, check if PyQtWebEngine is already installed
            self.progress.emit(f"🔍 Detected Qt{self.qt_version} - checking for {self.package_name}...\n")
            
            # Check for existing installation based on Qt version
            webengine_found = False
            if self.qt_version >= 6:
                try:
                    from PyQt6 import QtWebEngineWidgets
                    webengine_found = True
                except ImportError:
                    pass
            else:
                try:
                    from PyQt5 import QtWebEngineWidgets
                    webengine_found = True
                except ImportError:
                    pass
            
            if webengine_found:
                self.progress.emit(f"✅ {self.package_name} is already installed.\n")
                self.progress.emit("\n🔄 Please restart QGIS to use the Preview feature if it's not working.\n")
                self.finished.emit(True, "Already installed")
                return
            else:
                self.progress.emit(f"⚠️  {self.package_name} not found. Proceeding with installation...\n\n")

            # Check internet connection if local installation is not found
            self.progress.emit("🌐 Checking internet connection...\n")
            if not check_internet_connection():
                self.progress.emit("❌ No internet connection detected!\n\n")
                self.progress.emit(f"⚠️  Installation requires internet access to download {self.package_name}.\n\n")
                self.progress.emit("Please:\n")
                self.progress.emit("1. Connect to the internet\n")
                self.progress.emit("2. Try the installation again\n")
                self.finished.emit(False, "No internet connection")
                return
            
            self.progress.emit("✓ Internet connection available\n\n")
            
            self.progress.emit("🔍 Detecting Python environment...\n")
            
            # Get the Python executable path
            # sys.executable might point to qgis-ltr-bin.exe or qgis-bin, so we need to find the actual Python executable
            import platform
            import glob
            
            python_exe = sys.executable
            system = platform.system()
            
            # Determine the Python executable name based on OS
            python_name = 'python.exe' if system == 'Windows' else 'python'
            
            # If sys.executable is a QGIS binary, find the actual Python executable
            if 'qgis' in python_exe.lower():
                qgis_dir = os.path.dirname(os.path.dirname(python_exe))  # Go up from bin to QGIS root
                
                # Look for Python in common QGIS locations (cross-platform)
                python_patterns = [
                    os.path.join(qgis_dir, 'apps', 'Python3*', python_name),
                    os.path.join(qgis_dir, 'apps', 'Python*', python_name),
                ]
                
                found_python = None
                for pattern in python_patterns:
                    matches = glob.glob(pattern)
                    if matches:
                        # Use the first match (usually the latest Python version)
                        found_python = matches[0]
                        break
                
                if found_python and os.path.exists(found_python):
                    python_exe = found_python
                    self.progress.emit(f"✓ Found QGIS Python: {python_exe}\n")
                else:
                    self.progress.emit(f"⚠️  Using default Python: {python_exe}\n")
            else:
                self.progress.emit(f"✓ Python: {python_exe}\n")
            
            # Auto-detect PyQt version to ensure compatible WebEngine
            try:
                from qgis.PyQt.QtCore import PYQT_VERSION_STR
                pyqt_version = PYQT_VERSION_STR
                self.progress.emit(f"🔍 Detected PyQt version: {pyqt_version}\n")
            except ImportError:
                pyqt_version = None
                self.progress.emit("⚠️  Could not detect PyQt version, installing latest\n")
            
            self.progress.emit(f"\n📦 Installing {self.package_name}...\n")
            self.progress.emit("⏳ This may take 1-2 minutes...\n")
            self.progress.emit("⚠️  Keep this window open and do NOT close QGIS\n\n")
            
            # Build pip install command with version pinning
            if pyqt_version:
                package_spec = f"{self.package_name}=={pyqt_version}"
                self.progress.emit(f"📌 Installing version {pyqt_version} to match PyQt{self.qt_version}\n")
            else:
                package_spec = self.package_name
            
            pip_cmd = [python_exe, "-m", "pip", "install", "--upgrade", "--user", package_spec, "--timeout", "120"]
            
            import site
            user_site = site.getusersitepackages()
            self.progress.emit(f"📁 Installing to user site-packages: {user_site}\n\n")
            
            # Run pip install with retry logic
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                self.progress.emit(f"🔄 Attempt {attempt} of {max_retries}...\n")
                
                result = subprocess.run(
                    pip_cmd,
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minutes timeout
                )
                
                if result.returncode == 0:
                    self.progress.emit("✅ Installation successful!\n")
                    self.progress.emit("\n🔄 Please restart QGIS to use the Preview feature.\n")
                    self.finished.emit(True, "Installation successful")
                    return
                else:
                    error_msg = result.stderr if result.stderr else result.stdout
                    # Check if it's a timeout error
                    if "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
                        if attempt < max_retries:
                            self.progress.emit(f"⚠️ Network timeout. Retrying in 5 seconds...\n\n")
                            import time
                            time.sleep(5)
                            continue
                    self.progress.emit(f"❌ Installation failed:\n{error_msg}\n")
                    self.finished.emit(False, error_msg)
                    return
            
            # All retries exhausted
            self.progress.emit("❌ Installation failed after all retries.\n")
            self.progress.emit("Please check your internet connection and try again.\n")
            self.finished.emit(False, "Installation failed after multiple retries")
                
        except subprocess.TimeoutExpired:
            self.progress.emit("❌ Installation timed out (exceeded 5 minutes)\n")
            self.finished.emit(False, "Installation timeout")
        except Exception as e:
            self.progress.emit(f"❌ Error: {str(e)}\n")
            self.finished.emit(False, str(e))


class PyQtWebEngineInstallerDialog(QDialog):
    """Dialog for installing PyQt WebEngine (Qt5 or Qt6)"""
    
    def __init__(self, parent=None, plugin_dir=None):
        super().__init__(parent)
        self.qt_version = detect_qt_version()
        self.package_name = get_webengine_package_name()
        self.setWindowTitle(f"Install {self.package_name}")
        self.setGeometry(100, 100, 600, 400)
        self.install_thread = None
        # Use plugin_dir if provided, otherwise derive from this file's location
        self.plugin_dir = plugin_dir or os.path.dirname(os.path.abspath(__file__))
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel(f"{self.package_name} Installation")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            f"The Preview feature requires {self.package_name}.\n\n"
            f"Detected: Qt{self.qt_version} - Click 'Install' to automatically install it for your QGIS Python environment."
        )
        layout.addWidget(desc)
        
        # Internet connection requirement
        self.internet_notice = QLabel(
            f"⚠️  IMPORTANT: Internet connection is REQUIRED for installation\n"
            f"The installer will download {self.package_name} (~50-100 MB)"
        )
        internet_notice_font = QFont()
        internet_notice_font.setPointSize(9)
        internet_notice_font.setItalic(True)
        self.internet_notice.setFont(internet_notice_font)
        self.internet_notice.setStyleSheet("color: #ff6b6b; padding: 10px; background-color: #ffe0e0; border-radius: 5px;")
        layout.addWidget(self.internet_notice)
        
        # Output text area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Courier", 9))
        layout.addWidget(self.output_text)

        # Do not show again checkbox
        self.skip_checkbox = QCheckBox("Don't show this installer automatically again")
        settings = QgsSettings()
        skip_installer = settings.value("q2g/pyqtwebengine/skip_installer", False, type=bool)
        self.skip_checkbox.setChecked(skip_installer)
        self.skip_checkbox.stateChanged.connect(self._on_skip_checkbox_changed)
        layout.addWidget(self.skip_checkbox)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.install_btn = QPushButton("🔧 Install PyQt6-WebEngine")
        self.install_btn.clicked.connect(self.start_installation)
        button_layout.addWidget(self.install_btn)
        
        self.docs_btn = QPushButton("📚 View Documentation")
        self.docs_btn.clicked.connect(self.open_documentation)
        button_layout.addWidget(self.docs_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def start_installation(self):
        """Start the installation process"""
        self.output_text.clear()
        self.install_btn.setEnabled(False)
        self.docs_btn.setEnabled(False)
        self.close_btn.setEnabled(False)
        
        # Install to user site-packages (AppData) using --user flag
        self.install_thread = InstallThread()
        self.install_thread.progress.connect(self.append_output)
        self.install_thread.finished.connect(self.installation_finished)
        self.install_thread.start()
        
    def append_output(self, text):
        """Append text to output area"""
        self.output_text.append(text)
        # Auto-scroll to bottom
        self.output_text.verticalScrollBar().setValue(
            self.output_text.verticalScrollBar().maximum()
        )
        
    def installation_finished(self, success, message):
        """Handle installation completion"""
        self.install_btn.setEnabled(True)
        self.docs_btn.setEnabled(True)
        self.close_btn.setEnabled(True)
        
        if success:
            if message == "Already installed":
                QMessageBox.information(
                    self,
                    "Installation Not Needed",
                    "✅ PyQt6-WebEngine is already installed!\n\n"
                    "If the Preview feature is not working, please restart QGIS."
                )
            else:
                QMessageBox.information(
                    self,
                    "Installation Complete",
                    "✅ PyQt6-WebEngine installed successfully!\n\n"
                    "Please restart QGIS to use the Preview feature."
                )
        else:
            # Check if it's an internet connection issue
            if "No internet connection" in message:
                QMessageBox.warning(
                    self,
                    "No Internet Connection",
                    "❌ Installation requires internet connection\n\n"
                    "Please:\n"
                    "1. Connect to the internet\n"
                    "2. Make sure you have at least 50-100 MB available\n"
                    "3. Try the installation again\n\n"
                    "If you continue to have issues, contact us at mygis@gis.my"
                )
            else:
                QMessageBox.critical(
                    self,
                    "Installation Failed",
                    f"❌ Installation failed:\n\n{message}\n\n"
                    "Please check the documentation or contact us at mygis@gis.my"
                )
    
    def open_documentation(self):
        """Open documentation"""
        import webbrowser
        import platform
        
        # Determine OS and provide platform-specific documentation
        system = platform.system()
        
        doc_urls = {
            "Windows": "https://github.com/gisinnovationmy/Q2G-QGIStoGeoServerConnector",
            "Darwin": "https://github.com/gisinnovationmy/Q2G-QGIStoGeoServerConnector",
            "Linux": "https://github.com/gisinnovationmy/Q2G-QGIStoGeoServerConnector"
        }
        
        doc_url = doc_urls.get(system, "https://github.com/gisinnovationmy/Q2G-QGIStoGeoServerConnector")
        
        try:
            webbrowser.open(doc_url)
        except Exception as e:
            QMessageBox.information(
                self,
                "Setup Documentation",
                f"📚 Setup Documentation for {system}\n\n"
                f"Visit: {doc_url}\n\n"
                "If you need help:\n"
                "📧 Email: mygis@gis.my\n\n"
                "Please include:\n"
                "• Your operating system\n"
                "• QGIS version\n"
                "• Error message from the installation log"
            )

    def _on_skip_checkbox_changed(self, state):
        settings = QgsSettings()
        settings.setValue("q2g/pyqtwebengine/skip_installer", state == Qt.CheckState.Checked)
