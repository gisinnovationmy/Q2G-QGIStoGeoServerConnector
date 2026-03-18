"""
PyQtWebEngine installer dialog for handling missing PyQt5.QtWebEngineWidgets.
Provides one-click installation with real-time feedback.
"""

import subprocess
import sys
import os
import socket
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon


def check_internet_connection():
    """Check if internet connection is available"""
    sock = None
    try:
        # Try to connect to Google DNS
        sock = socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except (socket.timeout, socket.error):
        return False
    finally:
        if sock is not None:
            sock.close()


def check_pip_installed(python_exe):
    """Check if pip is installed for the given Python executable"""
    try:
        result = subprocess.run(
            [python_exe, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, Exception):
        return False


def install_pip(python_exe, progress_callback=None):
    """Attempt to install pip using ensurepip"""
    try:
        if progress_callback:
            progress_callback("🔧 Attempting to install pip using ensurepip...\n")
        
        result = subprocess.run(
            [python_exe, "-m", "ensurepip", "--upgrade"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            if progress_callback:
                progress_callback("✅ pip installed successfully!\n")
            return True
        else:
            if progress_callback:
                progress_callback(f"❌ Failed to install pip: {result.stderr}\n")
            return False
    except subprocess.TimeoutExpired:
        if progress_callback:
            progress_callback("❌ pip installation timed out\n")
        return False
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ Error installing pip: {str(e)}\n")
        return False


class InstallThread(QThread):
    """Background thread for installing PyQtWebEngine"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    pip_not_found = pyqtSignal(str)  # Signal to ask user about pip installation
    
    def __init__(self, install_pip_if_missing=False):
        super().__init__()
        self.install_pip_if_missing = install_pip_if_missing
        self.python_exe = None
    
    def run(self):
        try:
            # Check internet connection first
            self.progress.emit("🌐 Checking internet connection...\n")
            if not check_internet_connection():
                self.progress.emit("❌ No internet connection detected!\n\n")
                self.progress.emit("⚠️  Installation requires internet access to download PyQtWebEngine.\n\n")
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
            
            # Store python_exe for potential pip installation
            self.python_exe = python_exe
            
            # Check if pip is installed
            self.progress.emit("\n🔍 Checking if pip is installed...\n")
            if not check_pip_installed(python_exe):
                self.progress.emit("❌ pip is NOT installed!\n\n")
                self.progress.emit("pip is required to install PyQtWebEngine.\n")
                
                if self.install_pip_if_missing:
                    # User agreed to install pip
                    self.progress.emit("\n🔧 Installing pip...\n")
                    if install_pip(python_exe, self.progress.emit):
                        self.progress.emit("\n✅ pip is now installed. Continuing with PyQtWebEngine installation...\n")
                    else:
                        self.progress.emit("\n❌ Could not install pip automatically.\n\n")
                        self.progress.emit("═" * 50 + "\n")
                        self.progress.emit("📋 MANUAL INSTALLATION INSTRUCTIONS:\n")
                        self.progress.emit("═" * 50 + "\n\n")
                        self.progress.emit("Option 1: Using ensurepip (Recommended)\n")
                        self.progress.emit("   Open OSGeo4W Shell and run:\n")
                        self.progress.emit(f"   {python_exe} -m ensurepip --upgrade\n\n")
                        self.progress.emit("Option 2: Download get-pip.py\n")
                        self.progress.emit("   1. Download from: https://bootstrap.pypa.io/get-pip.py\n")
                        self.progress.emit("   2. Open OSGeo4W Shell and run:\n")
                        self.progress.emit(f"   {python_exe} get-pip.py\n\n")
                        self.progress.emit("After installing pip, restart QGIS and try again.\n")
                        self.finished.emit(False, "pip_not_installed")
                        return
                else:
                    # Emit signal to ask user about pip installation
                    self.pip_not_found.emit(python_exe)
                    self.finished.emit(False, "pip_not_installed_ask_user")
                    return
            else:
                self.progress.emit("✓ pip is installed\n")
            
            self.progress.emit("\n📦 Installing PyQtWebEngine...\n")
            self.progress.emit("⏳ This may take 1-2 minutes...\n")
            self.progress.emit("⚠️  Keep this window open and do NOT close QGIS\n\n")
            
            # Run pip install
            result = subprocess.run(
                [python_exe, "-m", "pip", "install", "PyQtWebEngine"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                self.progress.emit("✅ Installation successful!\n")
                self.progress.emit("\n🔄 Please restart QGIS to use the Preview feature.\n")
                self.finished.emit(True, "Installation successful")
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                self.progress.emit(f"❌ Installation failed:\n{error_msg}\n")
                self.finished.emit(False, error_msg)
                
        except subprocess.TimeoutExpired:
            self.progress.emit("❌ Installation timed out (exceeded 5 minutes)\n")
            self.finished.emit(False, "Installation timeout")
        except Exception as e:
            self.progress.emit(f"❌ Error: {str(e)}\n")
            self.finished.emit(False, str(e))


class PyQtWebEngineInstallerDialog(QDialog):
    """Dialog for installing PyQtWebEngine"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Install PyQtWebEngine")
        self.setGeometry(100, 100, 600, 400)
        self.install_thread = None
        self.pending_python_exe = None  # Store python exe path when pip is not found
        self.init_ui()
        
    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("PyQtWebEngine Installation")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "The Preview feature requires PyQtWebEngine.\n\n"
            "Click 'Install' to automatically install it for your QGIS Python environment."
        )
        layout.addWidget(desc)
        
        # Internet connection requirement
        internet_notice = QLabel(
            "⚠️  IMPORTANT: Internet connection is REQUIRED for installation\n"
            "The installer will download PyQtWebEngine (~50-100 MB)"
        )
        internet_notice_font = QFont()
        internet_notice_font.setPointSize(9)
        internet_notice_font.setItalic(True)
        internet_notice.setFont(internet_notice_font)
        internet_notice.setStyleSheet("color: #ff6b6b; padding: 10px; background-color: #ffe0e0; border-radius: 5px;")
        layout.addWidget(internet_notice)
        
        # Output text area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Courier", 9))
        layout.addWidget(self.output_text)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.install_btn = QPushButton("🔧 Install PyQtWebEngine")
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
        
    def start_installation(self, install_pip_if_missing=False):
        """Start the installation process"""
        if not install_pip_if_missing:
            self.output_text.clear()
        self.install_btn.setEnabled(False)
        self.docs_btn.setEnabled(False)
        self.close_btn.setEnabled(False)
        
        self.install_thread = InstallThread(install_pip_if_missing=install_pip_if_missing)
        self.install_thread.progress.connect(self.append_output)
        self.install_thread.finished.connect(self.installation_finished)
        self.install_thread.pip_not_found.connect(self.on_pip_not_found)
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
            QMessageBox.information(
                self,
                "Installation Complete",
                "✅ PyQtWebEngine installed successfully!\n\n"
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
            elif message == "pip_not_installed_ask_user":
                # User will be prompted via on_pip_not_found signal
                pass
            elif message == "pip_not_installed":
                # pip installation failed, instructions already shown in output
                QMessageBox.warning(
                    self,
                    "pip Not Installed",
                    "❌ pip is not installed and automatic installation failed.\n\n"
                    "Please see the manual installation instructions in the output area above.\n\n"
                    "After installing pip manually, restart QGIS and try again."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Installation Failed",
                    f"❌ Installation failed:\n\n{message}\n\n"
                    "Please check the documentation or contact us at mygis@gis.my"
                )
    
    def on_pip_not_found(self, python_exe):
        """Handle pip not found - ask user if they want to install it"""
        self.pending_python_exe = python_exe
        
        reply = QMessageBox.question(
            self,
            "pip Not Installed",
            "❌ pip is NOT installed on your system.\n\n"
            "pip is required to install PyQtWebEngine.\n\n"
            "Would you like to install pip now?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            # User wants to install pip - restart installation with pip install flag
            self.append_output("\n" + "=" * 50 + "\n")
            self.append_output("User chose to install pip...\n")
            self.append_output("=" * 50 + "\n\n")
            self.start_installation(install_pip_if_missing=True)
        else:
            # User declined - show manual installation instructions
            self.show_manual_pip_instructions(python_exe)
    
    def show_manual_pip_instructions(self, python_exe):
        """Show manual pip installation instructions when user declines automatic installation"""
        self.append_output("\n" + "=" * 50 + "\n")
        self.append_output("📋 MANUAL PIP INSTALLATION INSTRUCTIONS:\n")
        self.append_output("=" * 50 + "\n\n")
        self.append_output("Since you chose not to install pip automatically, here's how to do it manually:\n\n")
        self.append_output("Option 1: Using ensurepip (Recommended)\n")
        self.append_output("   1. Open OSGeo4W Shell (search for it in Start Menu)\n")
        self.append_output("   2. Run the following command:\n")
        self.append_output(f"      {python_exe} -m ensurepip --upgrade\n\n")
        self.append_output("Option 2: Download get-pip.py\n")
        self.append_output("   1. Download get-pip.py from:\n")
        self.append_output("      https://bootstrap.pypa.io/get-pip.py\n")
        self.append_output("   2. Open OSGeo4W Shell\n")
        self.append_output("   3. Navigate to where you downloaded get-pip.py\n")
        self.append_output("   4. Run:\n")
        self.append_output(f"      {python_exe} get-pip.py\n\n")
        self.append_output("After installing pip:\n")
        self.append_output("   1. Restart QGIS\n")
        self.append_output("   2. Open GeoServerConnector\n")
        self.append_output("   3. Try the Preview feature again\n")
        self.append_output("\n" + "=" * 50 + "\n")
        
        QMessageBox.information(
            self,
            "Manual Installation Required",
            "📋 Manual pip installation instructions have been displayed in the output area.\n\n"
            "Please follow the instructions to install pip, then restart QGIS and try again."
        )
    
    def open_documentation(self):
        """Open documentation"""
        import webbrowser
        import platform
        
        # Determine OS and provide platform-specific documentation
        system = platform.system()
        
        doc_urls = {
            "Windows": "https://github.com/yourusername/geoserverconnector/wiki/Setup-Windows",
            "Darwin": "https://github.com/yourusername/geoserverconnector/wiki/Setup-Mac",
            "Linux": "https://github.com/yourusername/geoserverconnector/wiki/Setup-Linux"
        }
        
        doc_url = doc_urls.get(system, "https://github.com/yourusername/geoserverconnector/wiki")
        
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
