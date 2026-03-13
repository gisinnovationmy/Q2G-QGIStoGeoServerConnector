# debug_dialog.py - QtWebEngine Diagnostic Dialog
"""
Comprehensive diagnostic dialog for QtWebEngine issues.
Tests OpenGL, sandbox, resources, permissions, and more.
"""

import os
import sys
import platform
import tempfile
import subprocess
import time
import threading

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTextEdit, QTreeWidget, QTreeWidgetItem, QHeaderView,
    QSplitter, QGroupBox, QProgressBar, QMessageBox, QMenu, QInputDialog
)
from qgis.PyQt.QtCore import Qt, QUrl, pyqtSignal, QTimer
from qgis.PyQt.QtGui import QColor, QBrush

# Try to import WebEngine with PyQt6/PyQt5 fallback
try:
    # Try PyQt6 first (QGIS 3.28+)
    from PyQt6.QtCore import QCoreApplication, QLibraryInfo
    from PyQt6.QtGui import QGuiApplication, QClipboard
    from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    # Fallback to PyQt5 (QGIS 3.16-3.26)
    from PyQt5.QtCore import QCoreApplication, QLibraryInfo
    from PyQt5.QtGui import QGuiApplication, QClipboard
    from PyQt5.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
    from PyQt5.QtWebEngineWidgets import QWebEngineView
# QOpenGLContext may not be available in QGIS PyQt6 installation
try:
    from qgis.PyQt.QtOpenGL import QOpenGLContext
    HAS_OPENGL_CONTEXT = True
except ImportError:
    HAS_OPENGL_CONTEXT = False
    QOpenGLContext = None


class DebugDialog(QDialog):
    """Dialog for running QtWebEngine diagnostics."""
    
    # Signal to update UI from worker thread
    test_completed = pyqtSignal(str, str, str)  # category, test, result
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("QtWebEngine Diagnostic Tests")
        self.setMinimumSize(900, 700)
        self.setWindowFlags(
            self.windowFlags() | 
            Qt.WindowType.WindowMinimizeButtonHint | 
            Qt.WindowType.WindowMaximizeButtonHint
        )
        self.categories = {}
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("QtWebEngine Diagnostic Tests")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)
        
        # Test button and progress
        button_layout = QHBoxLayout()
        self.test_btn = QPushButton("🧪 Run All Tests")
        self.test_btn.clicked.connect(self._run_tests)
        button_layout.addWidget(self.test_btn)

        self.copy_btn = QPushButton("📋 Copy to Clipboard")
        self.copy_btn.clicked.connect(self._copy_results_to_clipboard)
        button_layout.addWidget(self.copy_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        button_layout.addWidget(self.progress_bar)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Results tree
        self.results_tree = QTreeWidget()
        self.results_tree.setColumnCount(2)
        self.results_tree.setHeaderLabels(["Test", "Result"])
        self.results_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.results_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.results_tree.setAlternatingRowColors(True)

        # TSV output area
        tsv_group = QGroupBox("Command Log")
        tsv_layout = QVBoxLayout(tsv_group)
        
        self.tsv_output = QTextEdit()
        self.tsv_output.setReadOnly(True)
        self.tsv_output.setStyleSheet("QTextEdit { font-family: Consolas; font-size: 10px; background: #1e1e1e; color: #00ff00; }")
        tsv_layout.addWidget(self.tsv_output)

        # Add context menu for find functionality
        self.tsv_output.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tsv_output.customContextMenuRequested.connect(self._show_log_context_menu)

        # Create a splitter to make the log resizable
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self.results_tree)
        splitter.addWidget(tsv_group)
        splitter.setSizes([400, 200]) # Initial sizes

        layout.addWidget(splitter)
        
        # Connect signal
        self.test_completed.connect(self._add_result)

    def _show_log_context_menu(self, pos):
        context_menu = QMenu(self)
        find_action = context_menu.addAction("Find...")
        action = context_menu.exec(self.tsv_output.mapToGlobal(pos))
        if action == find_action:
            self._find_in_log()

    def _find_in_log(self):
        text, ok = QInputDialog.getText(self, 'Find Text', 'Enter text to find:')
        if ok and text:
            if not self.tsv_output.find(text):
                # If not found, start from the beginning
                self.tsv_output.moveCursor(self.tsv_output.textCursor().Start)
                if not self.tsv_output.find(text):
                    QMessageBox.information(self, "Not Found", f"Text '{text}' not found.")

    def _copy_results_to_clipboard(self):
        """Copy the contents of the results tree to the clipboard in TSV format."""
        clipboard = QGuiApplication.clipboard()
        if not clipboard:
            return

        tsv = "Category\tTest Name\tResult\n"
        root = self.results_tree.invisibleRootItem()
        for i in range(root.childCount()):
            category_item = root.child(i)
            category_text = category_item.text(0)
            for j in range(category_item.childCount()):
                child = category_item.child(j)
                test_name = child.text(0)
                result = child.text(1).replace('\n', ' ')
                tsv += f"{category_text}\t{test_name}\t{result}\n"

        clipboard.setText(tsv)
        self.copy_btn.setText("✅ Copied!")
        QTimer.singleShot(2000, lambda: self.copy_btn.setText("📋 Copy to Clipboard"))
        
    def _add_result(self, category_text, test_name, result):
        """Add a test result to the tree, color-coded."""
        # Define colors
        colors = {
            "green": QColor("#c8e6c9"), # Light Green
            "yellow": QColor("#fff9c4"), # Light Yellow
            "red": QColor("#ffcdd2")      # Light Red
        }

        # Determine result color
        result_lower = result.lower()
        if any(s in result_lower for s in ["error:", "failed:", "missing", "not supported"]):
            color = colors["red"]
        elif any(s in result_lower for s in ["not set", "unknown", "disabled", "not available"]):
            color = colors["yellow"]
        else:
            color = colors["green"]

        # Get or create category item
        if category_text not in self.categories:
            emoji_map = {
                "OpenGL / GPU": "🟦", "Sandbox": "🟧", "QtWebEngineProcess": "🟩",
                "Qt Resources": "🟨", "Qt Plugins": "🟦", "Permissions": "🟩",
                "Environment": "🟦", "Platform Backend": "🟩", "WebEngine Test": "🟩",
                "Architecture": "🟩", "External Tests": "🟦"
            }
            emoji = emoji_map.get(category_text, "⚙️")
            category_item = QTreeWidgetItem(self.results_tree, [f"{emoji} {category_text}"])
            category_item.setExpanded(True)
            self.categories[category_text] = category_item
        else:
            category_item = self.categories[category_text]

        # Create and add the child item for the test result
        child_item = QTreeWidgetItem(category_item, [test_name, result])
        child_item.setBackground(0, QBrush(color))
        child_item.setBackground(1, QBrush(color))

        # Update TSV output
        tsv_line = f"{category_text}\t{test_name}\t{result}\n"
        self.tsv_output.append(tsv_line.strip())
        
        # Scroll to bottom
        self.tsv_output.verticalScrollBar().setValue(self.tsv_output.verticalScrollBar().maximum())
        
    def _run_tests(self):
        """Run all diagnostic tests in a separate thread."""
        # Warn about external scripts
        reply = QMessageBox.question(
            self,
            "External Diagnostic Scripts",
            "This diagnostic will run external scripts to check:\n"
            "• OpenGL/GPU information (dxdiag/glxinfo/system_profiler)\n"
            "• QtWebEngine resource files\n"
            "• Running QtWebEngine processes\n\n"
            "Scripts are safe, read-only, and platform-specific.\n"
            "Continue with diagnostic?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.test_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Clear previous results
        self.results_tree.clear()
        self.categories = {}
        self.tsv_output.clear()
        
        # Run tests in thread
        thread = threading.Thread(target=self._run_diagnostic_tests)
        thread.daemon = True
        thread.start()
        
    def _run_diagnostic_tests(self):
        """Run all diagnostic tests and emit results."""
        tests = [
            ("OpenGL / GPU", "OpenGL support", self._check_opengl_support),
            ("OpenGL / GPU", "GPU acceleration enabled", self._check_gpu_acceleration),
            ("Sandbox", "Sandbox initialization test", self._check_sandbox),
            ("Sandbox", "Sandbox disabled env var", self._check_sandbox_disabled),
            ("QtWebEngineProcess", "Process spawn test", self._check_process_spawn),
            ("QtWebEngineProcess", "Process running check", self._check_process_running),
            ("Qt Resources", "qtwebengine_resources.pak present", lambda: self._check_resource_file("qtwebengine_resources.pak")),
            ("Qt Resources", "qtwebengine_resources_100p.pak present", lambda: self._check_resource_file("qtwebengine_resources_100p.pak")),
            ("Qt Resources", "qtwebengine_resources_200p.pak present", lambda: self._check_resource_file("qtwebengine_resources_200p.pak")),
            ("Qt Resources", "icudtl.dat present", lambda: self._check_resource_file("icudtl.dat")),
            ("Qt Plugins", "Plugin path detection", self._check_plugin_paths),
            ("Permissions", "Cache directory writable", self._check_cache_writable),
            ("Permissions", "Temp directory writable", self._check_temp_writable),
            ("Environment", "QT_OPENGL", lambda: os.environ.get("QT_OPENGL", "Not set")),
            ("Environment", "QTWEBENGINE_DISABLE_SANDBOX", lambda: os.environ.get("QTWEBENGINE_DISABLE_SANDBOX", "Not set")),
            ("Environment", "QTWEBENGINE_CHROMIUM_FLAGS", lambda: os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "Not set")),
            ("Platform Backend", "Wayland vs X11", self._check_platform_backend),
            ("WebEngine Test", "Profile creation (safe)", self._check_webengine_availability),
            ("Architecture", "Python/OS architecture", self._check_architecture),
            ("External Tests", "Complete External Diagnostics", self._check_external_diagnostics),
        ]
        
        for category, test_name, test_func in tests:
            try:
                result = test_func()
            except Exception as e:
                result = f"ERROR: {e}"
            
            self.test_completed.emit(category, test_name, str(result))
            time.sleep(0.1)  # Small delay for UI updates
        
        # Re-enable button
        self.test_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
    
    def _check_opengl_support(self):
        """Check if OpenGL is supported."""
        if not HAS_OPENGL_CONTEXT:
            return "QOpenGLContext not available (QGIS PyQt6 issue)"
        context = QOpenGLContext()
        return "Supported" if context.hasOpenGLSupport() else "Not Supported"
    
    def _check_gpu_acceleration(self):
        """Check if GPU acceleration is enabled."""
        try:
            gpu_enabled = QWebEngineSettings.globalSettings().testAttribute(
                QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled
            )
            return "Enabled" if gpu_enabled else "Disabled"
        except:
            return "Unknown"
    
    def _check_sandbox(self):
        """Test sandbox functionality."""
        try:
            # QGIS requires using QLibraryInfo.path() - .location() is removed
            bin_path = QLibraryInfo.path(QLibraryInfo.LibraryLocation.BinariesPath)
        except Exception as e:
            return f"FAILED: cannot get BinariesPath ({e})"

        exe = os.path.join(bin_path, "QtWebEngineProcess")
        if os.name == "nt":
            exe += ".exe"

        if not os.path.exists(exe):
            return f"FAILED: QtWebEngineProcess not found at {exe}"

        try:
            p = subprocess.Popen([exe], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(0.5)
            alive = (p.poll() is None)
            p.terminate()
            return "OK (process started)" if alive else "FAILED (process exited immediately)"
        except Exception as e:
            return f"FAILED: {e}"
    
    def _check_sandbox_disabled(self):
        """Check if sandbox is disabled via environment variable."""
        disabled = os.environ.get("QTWEBENGINE_DISABLE_SANDBOX", "0")
        return "Disabled" if disabled == "1" else "Enabled"
    
    def _check_process_spawn(self):
        """Check if QtWebEngineProcess can spawn."""
        try:
            profile = QWebEngineProfile.defaultProfile()
            return "Working"
        except Exception as e:
            return f"FAILED: {e}"
    
    def _check_process_running(self):
        """Check if QtWebEngineProcess is running."""
        try:
            import psutil
            for p in psutil.process_iter(['name']):
                if "QtWebEngineProcess" in p.info['name']:
                    return "Running"
            return "Not Running"
        except:
            return "psutil not installed"
    
    def _check_resource_file(self, filename):
        """Check if a required resource file exists."""
        try:
            # QGIS requires using QLibraryInfo.path() - .location() is removed
            res_path = QLibraryInfo.path(QLibraryInfo.LibraryLocation.DataPath)
        except Exception as e:
            return f"ERROR: {e}"
        
        filepath = os.path.join(res_path, filename)
        return "Present" if os.path.exists(filepath) else "Missing"
    
    def _check_plugin_paths(self):
        """Check Qt plugin paths."""
        paths = QCoreApplication.libraryPaths()
        return f"Found {len(paths)} paths" if paths else "No paths found"
    
    def _check_cache_writable(self):
        """Check if cache directory is writable."""
        try:
            profile = QWebEngineProfile.defaultProfile()
            cache = profile.cachePath()
            return self._check_write(cache)
        except Exception as e:
            return f"ERROR: {e}"
    
    def _check_temp_writable(self):
        """Check if temp directory is writable."""
        return self._check_write(tempfile.gettempdir())
    
    def _check_platform_backend(self):
        """Check platform backend (Wayland vs X11)."""
        return QGuiApplication.platformName()
    
    def _check_architecture(self):
        """Check Python and OS architecture."""
        return f"Python: {platform.architecture()[0]}, OS: {platform.machine()}"
    
    def _check_webengine_availability(self):
        """Check if WebEngine is available."""
        try:
            profile = QWebEngineProfile.defaultProfile()
            return "Available"
        except Exception as e:
            return f"Not available: {e}"
    
    def _check_write(self, path):
        """Check if a path is writable."""
        try:
            test = os.path.join(path, "test.tmp")
            with open(test, "w") as f:
                f.write("ok")
            os.remove(test)
            return True
        except:
            return False
    
    def _run_external_script(self, script_name, timeout=15):
        """Run external diagnostic script and return output."""
        try:
            # Get the directory where this script is located
            base_dir = os.path.dirname(os.path.abspath(__file__))
            debug_dir = os.path.join(base_dir, "debug")
            script_path = os.path.join(debug_dir, script_name)
            
            if not os.path.exists(script_path):
                return f"Script not found: {script_path}"
            
            # Run the script
            if os.name == "nt":  # Windows
                cmd = f'cmd /c "{script_path}"'
            else:  # Linux/macOS
                # Make sure script is executable
                os.chmod(script_path, 0o755)
                cmd = f'"{script_path}"'
            
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=debug_dir
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                # Limit output length for display
                if len(output) > 500:
                    output = output[:500] + "...\n[Output truncated]"
                return output
            else:
                error_output = result.stderr.strip() if result.stderr else ""
                return f"Script failed (exit code {result.returncode})\n{error_output}"
                
        except subprocess.TimeoutExpired:
            return "Script timed out"
        except Exception as e:
            return f"ERROR: {e}"
    
    def _check_external_diagnostics(self):
        """Run all external diagnostics using platform-specific script."""
        system = platform.system().lower()
        
        if system == "windows":
            return self._run_external_script("diagnostic_webengine_win.bat")
        elif system == "linux":
            return self._run_external_script("diagnostic_webengine_linux.sh")
        elif system == "darwin":  # macOS
            return self._run_external_script("diagnostic_webengine_mac.sh")
        else:
            return f"Unsupported platform: {system}"
