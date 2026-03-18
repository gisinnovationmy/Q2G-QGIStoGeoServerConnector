"""
Log window module for the Q2G QGIS plugin.
Provides a copyable log window for upload messages and error reporting.
"""

from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox, QPushButton, QHBoxLayout, QLabel
)
from qgis.PyQt.QtCore import Qt, QTimer, QSize, QObject, pyqtSignal
from qgis.PyQt.QtGui import QTextCursor, QColor, QFont, QTextCharFormat
from qgis.core import Qgis


class LogWindow(QDialog):
    """A dialog window that displays log messages in a copyable text area with live updates."""
    
    def __init__(self, log_messages=None, title="Upload Log", parent=None, live_mode=False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(700, 500)
        self.setWindowFlags(Qt.Window | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
        
        self.live_mode = live_mode
        if log_messages is None:
            log_messages = []
        
        # Upload control signals
        self.stop_upload = False
        self.pause_upload = False
        self.step_mode = False
        self.step_triggered = False
        
        # Store references to buttons for state management
        self.step_button = None
        self.stop_button = None
        self.pause_button = None
        self.resume_auto_button = None
        
        self.setup_ui(log_messages)
    
    def setup_ui(self, log_messages):
        """Setup the user interface for the log window."""
        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        # Add title label
        title_label = QLabel("Upload Progress Log")
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Create text area with all log messages
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        
        # Use a consistent monospace font
        font = QFont("Consolas")
        if not QFont("Consolas").exactMatch():
            font = QFont("Monaco")
        if not font.exactMatch():
            font = QFont("Courier New")
        font.setPointSize(9)
        font.setStyleStrategy(QFont.PreferAntialias)
        self.text_area.setFont(font)
        
        # Set modern styling
        self.text_area.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #d0d0d0;
                border-radius: 5px;
                padding: 10px;
                margin: 0px;
                line-height: 1.5;
            }
            QTextEdit:focus {
                border: 1px solid #0078d4;
            }
        """)
        
        # Add initial messages with color coding
        for message in log_messages:
            self.append_message_with_color(message)
        
        layout.addWidget(self.text_area)
        
        # Add control buttons for upload management (only in live mode)
        if self.live_mode:
            control_layout = QHBoxLayout()
            control_layout.setSpacing(8)
            
            # Pause Upload button - Default style
            pause_button = QPushButton("Pause Upload")
            pause_button.clicked.connect(self.on_pause_upload)
            pause_button.setStyleSheet("""
                QPushButton {
                    background-color: #e6e6e6;
                    border: 1px solid #aaa;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-size: 10pt;
                }
                QPushButton:hover {
                    background-color: #d0eaff;
                    border: 1px solid #3399ff;
                }
                QPushButton:pressed {
                    background-color: #b5d9ff;
                }
            """)
            self.pause_button = pause_button  # Store reference
            control_layout.addWidget(pause_button)
            
            # Step-In Upload button - Default style (toggle between Step-In and Next Layer)
            step_button = QPushButton("Step-In Upload")
            step_button.clicked.connect(self.on_step_upload)
            step_button.setStyleSheet("""
                QPushButton {
                    background-color: #e6e6e6;
                    border: 1px solid #aaa;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-size: 10pt;
                }
                QPushButton:hover {
                    background-color: #d0eaff;
                    border: 1px solid #3399ff;
                }
                QPushButton:pressed {
                    background-color: #b5d9ff;
                }
            """)
            self.step_button = step_button  # Store reference for toggling text
            control_layout.addWidget(step_button)
            
            # Resume Auto Upload button - Default style (disables step mode)
            resume_auto_button = QPushButton("Resume Auto Upload")
            resume_auto_button.clicked.connect(self.on_resume_auto_upload)
            resume_auto_button.setStyleSheet("""
                QPushButton {
                    background-color: #e6e6e6;
                    border: 1px solid #aaa;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-size: 10pt;
                }
                QPushButton:hover {
                    background-color: #d0eaff;
                    border: 1px solid #3399ff;
                }
                QPushButton:pressed {
                    background-color: #b5d9ff;
                }
            """)
            self.resume_auto_button = resume_auto_button  # Store reference
            control_layout.addWidget(resume_auto_button)
            
            # Add stretch to push Stop button to the right
            control_layout.addStretch()
            
            # Stop Upload button - Red (matches delete button style) - at the right end
            stop_button = QPushButton("Stop Upload")
            stop_button.clicked.connect(self.on_stop_upload)
            stop_button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: 1px solid #b71c1c;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-size: 10pt;
                }
                QPushButton:hover {
                    background-color: #e53935;
                }
                QPushButton:pressed {
                    background-color: #c62828;
                }
            """)
            self.stop_button = stop_button  # Store reference
            control_layout.addWidget(stop_button)
            
            layout.addLayout(control_layout)
        
        # Add buttons with modern styling
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        # Copy All button
        copy_button = QPushButton("Copy All")
        copy_button.clicked.connect(self.copy_all_to_clipboard)
        copy_button.setStyleSheet("""
            QPushButton {
                background-color: #e6e6e6;
                border: 1px solid #aaa;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #d0eaff;
                border: 1px solid #3399ff;
            }
            QPushButton:pressed {
                background-color: #b5d9ff;
            }
        """)
        button_layout.addWidget(copy_button)
        
        # Clear Log button
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.clear_log)
        clear_button.setStyleSheet("""
            QPushButton {
                background-color: #e6e6e6;
                border: 1px solid #aaa;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #d0eaff;
                border: 1px solid #3399ff;
            }
            QPushButton:pressed {
                background-color: #b5d9ff;
            }
        """)
        button_layout.addWidget(clear_button)
        
        # Close button
        ok_button = QPushButton("Close")
        ok_button.clicked.connect(self.close)  # Use close() to trigger closeEvent()
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #e6e6e6;
                border: 1px solid #aaa;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #d0eaff;
                border: 1px solid #3399ff;
            }
            QPushButton:pressed {
                background-color: #b5d9ff;
            }
        """)
        button_layout.addWidget(ok_button)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def append_message_with_color(self, message, level=None):
        """Append a message to the text area with appropriate color coding."""
        cursor = self.text_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # Sanitize message - remove problematic characters
        message_str = str(message).strip()
        
        # Determine color based on message content or level
        color = "#333333"  # default dark gray
        
        if level == Qgis.Critical or "✗" in message_str or "Error:" in message_str or "Failed:" in message_str or "was not loaded" in message_str:
            color = "#d13438"  # red for errors
        elif level == Qgis.Warning or "⚠" in message_str or "Warning:" in message_str:
            color = "#ff8c00"  # orange for warnings
        elif "✓" in message_str or "Success:" in message_str or "uploaded" in message_str.lower():
            color = "#107c10"  # green for success
        elif "DEBUG:" in message_str or "Progress:" in message_str:
            color = "#666666"  # gray for debug info
        
        # Insert colored text with proper formatting
        html_text = f'<span style="color: {color}; font-family: Consolas, Monaco, Courier New; font-size: 9pt;">{message_str}</span><br>'
        cursor.insertHtml(html_text)
        
        # Auto-scroll to bottom
        self.text_area.moveCursor(QTextCursor.End)
    
    def append_layer_title(self, layer_name):
        """Append a special layer processing title in blue color, 2 pts bigger than normal font."""
        cursor = self.text_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # Create the title message (without newline - HTML will handle it)
        title_message = f"Now processing layer \"{layer_name}\":"
        
        # Insert title with blue color and larger font (11pt instead of 9pt)
        html_text = f'<span style="color: #0078d4; font-family: Consolas, Monaco, Courier New; font-size: 11pt; font-weight: bold;">{title_message}</span><br>'
        cursor.insertHtml(html_text)
        
        # Auto-scroll to bottom
        self.text_area.moveCursor(QTextCursor.End)
    
    def append_message(self, message, level=None):
        """Public method to append a message with color coding."""
        self.append_message_with_color(message, level)
    
    def copy_all_to_clipboard(self):
        """Copy all log text to the system clipboard."""
        from qgis.PyQt.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.text_area.toPlainText())
    
    def clear_log(self):
        """Clear the log text area."""
        self.text_area.clear()
    
    def on_stop_upload(self):
        """Handle stop upload button click."""
        self.stop_upload = True
        self.append_message_with_color("Stop signal sent - upload will stop after current layer", None)
    
    def on_pause_upload(self):
        """Handle pause upload button click."""
        self.pause_upload = not self.pause_upload
        if self.pause_upload:
            self.append_message_with_color("Upload paused - click Pause Upload to resume", None)
        else:
            self.append_message_with_color("Upload resumed", None)
    
    def on_step_upload(self):
        """
        Handle step-in upload button click - toggle between Step-In and Next Layer.
        
        First click: Enables step mode (button text changes to "Next Layer")
        Subsequent clicks: Triggers next layer upload (button text stays "Next Layer")
        """
        if not self.step_mode:
            # First click - enable step mode
            self.step_mode = True
            self.step_triggered = True
            # Change button text to "Next Layer"
            if self.step_button:
                self.step_button.setText("Next Layer")
            self.append_message_with_color("Step mode enabled - upload one layer at a time", None)
        else:
            # Subsequent clicks - trigger next layer
            self.step_triggered = True
            self.append_message_with_color("Processing next layer...", None)
    
    def on_resume_auto_upload(self):
        """
        Handle resume auto upload button click.
        
        This disables step mode and allows the upload to continue automatically
        without pausing after each layer. All remaining layers will be uploaded
        in sequence without waiting for user confirmation.
        """
        self.step_mode = False
        self.step_triggered = True
        self.pause_upload = False
        # Reset button text back to "Step-In Upload"
        if self.step_button:
            self.step_button.setText("Step-In Upload")
        self.append_message_with_color("Step mode disabled - resuming automatic upload for all remaining layers", None)
    
    def clear_and_reset(self):
        """
        Clear log content and reset all buttons for a new upload session.
        Called when reusing the dialog for a new upload.
        """
        # Clear the text area
        self.text_area.clear()
        
        # Reset upload control flags
        self.stop_upload = False
        self.pause_upload = False
        self.step_mode = False
        self.step_triggered = False
        
        # Re-enable and restore button styles
        if self.stop_button:
            self.stop_button.setEnabled(True)
            self.stop_button.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    border: 1px solid #b71c1c;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-size: 10pt;
                }
                QPushButton:hover {
                    background-color: #e53935;
                }
                QPushButton:pressed {
                    background-color: #c62828;
                }
            """)
        
        if self.pause_button:
            self.pause_button.setEnabled(True)
            self.pause_button.setStyleSheet("""
                QPushButton {
                    background-color: #e6e6e6;
                    border: 1px solid #aaa;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-size: 10pt;
                }
                QPushButton:hover {
                    background-color: #d0eaff;
                    border: 1px solid #3399ff;
                }
                QPushButton:pressed {
                    background-color: #b5d9ff;
                }
            """)
        
        if self.step_button:
            self.step_button.setEnabled(True)
            self.step_button.setText("Step-In Upload")  # Reset text
            self.step_button.setStyleSheet("""
                QPushButton {
                    background-color: #e6e6e6;
                    border: 1px solid #aaa;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-size: 10pt;
                }
                QPushButton:hover {
                    background-color: #d0eaff;
                    border: 1px solid #3399ff;
                }
                QPushButton:pressed {
                    background-color: #b5d9ff;
                }
            """)
        
        if self.resume_auto_button:
            self.resume_auto_button.setEnabled(True)
            self.resume_auto_button.setStyleSheet("""
                QPushButton {
                    background-color: #e6e6e6;
                    border: 1px solid #aaa;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-size: 10pt;
                }
                QPushButton:hover {
                    background-color: #d0eaff;
                    border: 1px solid #3399ff;
                }
                QPushButton:pressed {
                    background-color: #b5d9ff;
                }
            """)
    
    def disable_upload_controls(self):
        """
        Disable all upload control buttons when upload is complete.
        Called when upload finishes or is stopped.
        """
        if self.stop_button:
            self.stop_button.setEnabled(False)
            self.stop_button.setStyleSheet("""
                QPushButton {
                    background-color: #cccccc;
                    color: #666666;
                    border: 1px solid #999999;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-size: 10pt;
                }
            """)
        
        if self.pause_button:
            self.pause_button.setEnabled(False)
            self.pause_button.setStyleSheet("""
                QPushButton {
                    background-color: #cccccc;
                    color: #666666;
                    border: 1px solid #999999;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-size: 10pt;
                }
            """)
        
        if self.step_button:
            self.step_button.setEnabled(False)
            self.step_button.setStyleSheet("""
                QPushButton {
                    background-color: #cccccc;
                    color: #666666;
                    border: 1px solid #999999;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-size: 10pt;
                }
            """)
        
        if self.resume_auto_button:
            self.resume_auto_button.setEnabled(False)
            self.resume_auto_button.setStyleSheet("""
                QPushButton {
                    background-color: #cccccc;
                    color: #666666;
                    border: 1px solid #999999;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-size: 10pt;
                }
            """)
    
    def closeEvent(self, event):
        """
        Handle window close event - stop upload if window is closed.
        
        This method is triggered when:
        1. User clicks the X button on the dialog
        2. User clicks the Close button
        3. Dialog is closed programmatically
        4. System closes the window
        
        In all cases, the upload is stopped immediately.
        """
        if self.live_mode:
            self.stop_upload = True
            self.pause_upload = False  # Also unpause if paused, to allow clean stop
            self.append_message_with_color("Upload window closed - stopping upload immediately", None)
        event.accept()


class UploadLogTracker(QObject):
    """Helper class to track upload messages and display them in a log window."""
    
    # Signal to emit messages from background thread to main thread
    message_signal = pyqtSignal(str, object)  # message, level
    # Signal to emit layer titles from background thread to main thread (fixes crash)
    layer_title_signal = pyqtSignal(str)
    # Signal to disable controls from background thread
    disable_controls_signal = pyqtSignal()
    # Signal to update window title from background thread
    update_title_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.messages = []
        self.success_count = 0
        self.failure_count = 0
        self.skip_count = 0
        self.live_window = None
        self.log_text_edit = None
        # Track skip reasons separately for clearer reporting
        self.skip_batch_count = 0
        self.skip_user_count = 0
        # Track layers for end-of-process summary
        self.failed_layers = []
        self.successful_layers = []
        self.skipped_layers = []
        # Flag to control whether logging is enabled
        self.show_log_dialog = True
        
        # Connect signal to slot for thread-safe updates
        self.message_signal.connect(self._on_message_received)
        self.layer_title_signal.connect(self._on_layer_title_received)
        self.disable_controls_signal.connect(self._on_disable_controls)
        self.update_title_signal.connect(self._on_update_title)
    
    def should_stop_upload(self):
        """Check if upload should be stopped."""
        return self.live_window and self.live_window.stop_upload
    
    def should_pause_upload(self):
        """Check if upload should be paused."""
        return self.live_window and self.live_window.pause_upload
    
    def is_step_mode(self):
        """Check if step mode is enabled."""
        return self.live_window and self.live_window.step_mode
    
    def get_step_triggered(self):
        """Check if step was triggered."""
        if self.live_window:
            triggered = self.live_window.step_triggered
            self.live_window.step_triggered = False
            return triggered
        return False
    
    def track_success(self, layer_name=None):
        """Track a successful layer upload."""
        self.success_count += 1
        if layer_name:
            self.successful_layers.append(layer_name)
    
    def track_failure(self, layer_name=None, reason=None):
        """Track a failed layer upload."""
        self.failure_count += 1
        if layer_name:
            self.failed_layers.append({
                'name': layer_name,
                'reason': reason or 'Unknown error'
            })
    
    def track_skip_batch(self, layer_name=None):
        """Track a skipped layer due to batch source already loaded."""
        self.skip_batch_count += 1
        self.skip_count += 1
        if layer_name:
            self.skipped_layers.append({'name': layer_name, 'reason': 'Batch source already loaded'})
    
    def track_skip_user(self, layer_name=None):
        """Track a skipped layer due to user request."""
        self.skip_user_count += 1
        self.skip_count += 1
        if layer_name:
            self.skipped_layers.append({'name': layer_name, 'reason': 'User skipped'})
    
    def add_message(self, message, level=None):
        """Add a message to the log tracker and update live window if open (thread-safe)."""
        # Only log if logging is enabled
        if not self.show_log_dialog:
            return
        
        self.messages.append(str(message))
        
        # Emit signal to update UI on main thread (thread-safe)
        self.message_signal.emit(str(message), level)
    
    def _on_message_received(self, message, level):
        """Slot to handle messages from background thread (runs on main thread)."""
        # Update live window if it exists - this enables live streaming
        if self.live_window and hasattr(self.live_window, 'append_message'):
            self.live_window.append_message(message, level)

    def _on_layer_title_received(self, layer_name):
        """Slot to handle layer titles from background thread (runs on main thread)."""
        # Update live window if it exists - this enables live streaming
        if self.live_window and hasattr(self.live_window, 'append_layer_title'):
            self.live_window.append_layer_title(layer_name)
    
    def _on_disable_controls(self):
        """Slot to disable controls from background thread (runs on main thread)."""
        if self.live_window and hasattr(self.live_window, 'disable_upload_controls'):
            self.live_window.disable_upload_controls()
            
    def _on_update_title(self, title):
        """Slot to update window title from background thread (runs on main thread)."""
        if self.live_window:
            self.live_window.setWindowTitle(title)
    
    def add_layer_title(self, layer_name):
        """Add a special layer processing title to the log tracker and live window."""
        # Only log if logging is enabled
        if not self.show_log_dialog:
            return
        
        title_message = f"Now processing layer \"{layer_name}\":\n"
        self.messages.append(title_message)
        
        # Emit signal to update UI on main thread (thread-safe)
        self.layer_title_signal.emit(layer_name)
        
    def disable_controls(self):
        """Disable upload controls in the live window (thread-safe)."""
        self.disable_controls_signal.emit()
        
    def update_window_title(self, title):
        """Update the live window title (thread-safe)."""
        self.update_title_signal.emit(title)
    
    def show_live_log_window(self, parent=None, title="Upload Log"):
        """
        Show a live log window that updates in real-time with upload control buttons.
        Reuses existing dialog if still open, otherwise creates a new one.
        """
        # Check if dialog already exists
        if self.live_window:
            try:
                # Try to access the window - if it fails, it was deleted
                _ = self.live_window.windowTitle()
                
                # Window exists, reuse it
                self.live_window.clear_and_reset()
                self.live_window.raise_()  # Bring to front
                self.live_window.activateWindow()
                self.log_text_edit = self.live_window.text_area
                self.live_window.show()
                return self.live_window
            except RuntimeError:
                # Window was deleted, create new one
                self.live_window = None
        
        # Create new dialog if none exists or old one was deleted
        self.live_window = LogWindow(self.messages, title, parent, live_mode=True)
        self.log_text_edit = self.live_window.text_area  # Store reference for real-time scrolling
        self.live_window.show()  # Non-blocking show
        return self.live_window
    
    def show_log_window(self, parent=None, title="Upload Summary"):
        """Show the log window with all messages."""
        log_window = LogWindow(self.messages, title, parent)
        log_window.exec_()
    
    def get_summary(self):
        """Generate a summary of the upload results."""
        summary = f"""
========== UPLOAD SUMMARY ==========
✓ Successful: {self.success_count}
✗ Failed: {self.failure_count}
⊘ Skipped: {self.skip_count}
  - Batch source: {self.skip_batch_count}
  - User request: {self.skip_user_count}
====================================
"""
        return summary
    
    def show_completion_popup(self, parent=None):
        """Show a comprehensive summary popup with table widget and toggle filters."""
        from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QLabel, QTableWidget, QPushButton, QHBoxLayout, QTableWidgetItem, QHeaderView, QCheckBox
        from qgis.PyQt.QtCore import Qt
        from qgis.PyQt.QtGui import QColor
        
        # Create custom dialog for results
        dialog = QDialog(parent)
        dialog.setWindowTitle("Upload Summary")
        dialog.setMinimumWidth(800)
        dialog.setMinimumHeight(600)
        
        layout = QVBoxLayout()
        
        # Summary label
        summary_text = f"Upload process completed.\n✓ {self.success_count} successful  |  ✗ {self.failure_count} failed  |  ⊘ {self.skip_count} skipped"
        summary_label = QLabel(summary_text)
        summary_label.setStyleSheet("font-size: 10pt; font-weight: bold;")
        layout.addWidget(summary_label)
        
        # Create table widget with all layers
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Layer Name", "Status"])
        
        # Set column widths
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        
        # Prepare all rows with status and color
        all_rows = []
        
        # Add successful layers
        for layer_name in self.successful_layers:
            all_rows.append({
                'name': layer_name,
                'status': 'Successful',
                'type': 'success',
                'color': QColor(16, 124, 16)  # Green
            })
        
        # Add failed layers
        for layer in self.failed_layers:
            all_rows.append({
                'name': layer['name'],
                'status': 'Failed',
                'type': 'failed',
                'color': QColor(209, 52, 56)  # Red
            })
        
        # Add skipped layers
        for layer in self.skipped_layers:
            all_rows.append({
                'name': layer['name'],
                'status': 'Skipped',
                'type': 'skipped',
                'color': QColor(255, 140, 0)  # Orange
            })
        
        # Set table row count
        table.setRowCount(len(all_rows))
        
        # Populate table
        for idx, row_data in enumerate(all_rows):
            # Layer Name column
            name_item = QTableWidgetItem(row_data['name'])
            table.setItem(idx, 0, name_item)
            
            # Status column
            status_item = QTableWidgetItem(row_data['status'])
            status_item.setTextAlignment(Qt.AlignCenter)
            status_item.setForeground(row_data['color'])
            table.setItem(idx, 1, status_item)
            
            # Store row type for filtering
            table.item(idx, 0).row_type = row_data['type']
            table.item(idx, 1).row_type = row_data['type']
        
        # Make table read-only
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(table)
        
        # Filter checkboxes
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Show:"))
        
        # Create checkboxes with initial state all checked
        successful_cb = QCheckBox("Successful")
        successful_cb.setChecked(True)
        successful_cb.setStyleSheet("color: #107c10;")
        
        failed_cb = QCheckBox("Failed")
        failed_cb.setChecked(True)
        failed_cb.setStyleSheet("color: #d13438;")
        
        skipped_cb = QCheckBox("Skipped")
        skipped_cb.setChecked(True)
        skipped_cb.setStyleSheet("color: #ff8c00;")
        
        filter_layout.addWidget(successful_cb)
        filter_layout.addWidget(failed_cb)
        filter_layout.addWidget(skipped_cb)
        filter_layout.addStretch()
        
        # Connect checkbox signals to filter function
        def apply_filters():
            for row_idx in range(table.rowCount()):
                row_type = table.item(row_idx, 0).row_type
                
                # Determine if row should be visible
                visible = False
                if row_type == 'success' and successful_cb.isChecked():
                    visible = True
                elif row_type == 'failed' and failed_cb.isChecked():
                    visible = True
                elif row_type == 'skipped' and skipped_cb.isChecked():
                    visible = True
                
                table.setRowHidden(row_idx, not visible)
        
        successful_cb.stateChanged.connect(apply_filters)
        failed_cb.stateChanged.connect(apply_filters)
        skipped_cb.stateChanged.connect(apply_filters)
        
        layout.addLayout(filter_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec_()
    
    def save_log_to_file(self, file_path=None):
        """
        Save the complete log to a text file.
        
        Args:
            file_path: Path to save the log file. If None, saves to logs.txt in the plugin directory.
        
        Returns:
            str: Path to the saved file, or None if save failed.
        """
        import os
        
        # Determine file path
        if file_path is None:
            # Get plugin directory (same as main.py)
            try:
                plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                file_path = os.path.join(plugin_dir, 'logs.txt')
            except Exception as e:
                print(f"Error determining plugin directory: {e}")
                return None
        
        try:
            # Prepare log content
            log_content = "=" * 80 + "\n"
            log_content += "Q2G Upload Log\n"
            log_content += "=" * 80 + "\n\n"
            
            # Add all messages
            for message in self.messages:
                log_content += message + "\n"
            
            # Add summary
            log_content += "\n" + "=" * 80 + "\n"
            log_content += "UPLOAD SUMMARY\n"
            log_content += "=" * 80 + "\n"
            log_content += f"Successful uploads: {self.success_count}\n"
            log_content += f"Failed uploads: {self.failure_count}\n"
            log_content += f"Skipped layers: {self.skip_count}\n"
            log_content += f"  - Batch skipped: {self.skip_batch_count}\n"
            log_content += f"  - User skipped: {self.skip_user_count}\n"
            
            # Add successful layers
            if self.successful_layers:
                log_content += "\n" + "-" * 80 + "\n"
                log_content += "SUCCESSFUL LAYERS\n"
                log_content += "-" * 80 + "\n"
                for layer in self.successful_layers:
                    log_content += f"  ✓ {layer}\n"
            
            # Add failed layers
            if self.failed_layers:
                log_content += "\n" + "-" * 80 + "\n"
                log_content += "FAILED LAYERS\n"
                log_content += "-" * 80 + "\n"
                for layer_info in self.failed_layers:
                    layer_name = layer_info.get('name', 'Unknown')
                    reason = layer_info.get('reason', 'Unknown error')
                    log_content += f"  ✗ {layer_name}\n"
                    log_content += f"    Reason: {reason}\n"
            
            # Add skipped layers
            if self.skipped_layers:
                log_content += "\n" + "-" * 80 + "\n"
                log_content += "SKIPPED LAYERS\n"
                log_content += "-" * 80 + "\n"
                for layer_info in self.skipped_layers:
                    layer_name = layer_info.get('name', 'Unknown')
                    reason = layer_info.get('reason', 'Unknown reason')
                    log_content += f"  ⊘ {layer_name}\n"
                    log_content += f"    Reason: {reason}\n"
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(log_content)
            
            return file_path
        
        except Exception as e:
            print(f"Error saving log file: {e}")
            return None
    
    def clear(self):
        """Clear all tracked messages and counts."""
        self.messages.clear()
        self.success_count = 0
        self.failure_count = 0
        self.skip_count = 0
        self.skip_batch_count = 0
        self.skip_user_count = 0
        self.failed_layers.clear()
        self.successful_layers.clear()
        self.skipped_layers.clear()
        self.live_window = None
