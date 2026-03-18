"""
Upload Controller Module
Handles upload flow control including pause, stop, and step-in functionality.
Keeps upload logic separate from UI logic.
"""

import time
from qgis.PyQt.QtWidgets import QApplication


class UploadController:
    """Controls the upload process with pause, stop, and step-in capabilities."""
    
    def __init__(self, log_tracker):
        """
        Initialize the upload controller.
        
        Args:
            log_tracker: UploadLogTracker instance for accessing control signals
        """
        self.log_tracker = log_tracker
    
    def check_stop_signal(self, layer_name):
        """
        Check if stop signal was triggered.
        
        Args:
            layer_name: Name of current layer being processed
            
        Returns:
            bool: True if upload should stop
        """
        if self.log_tracker.should_stop_upload():
            return True
        return False
    
    def handle_pause(self):
        """
        Handle pause state - wait until user resumes or stops.
        Processes UI events to keep interface responsive.
        """
        while self.log_tracker.should_pause_upload():
            QApplication.processEvents()
            time.sleep(0.1)
    
    def handle_step_mode(self):
        """
        Handle step mode - wait for user to click Continue before proceeding.
        
        Returns:
            bool: True if user clicked Continue, False if user stopped
        """
        if not self.log_tracker.is_step_mode():
            return True
        
        # Wait for user to trigger step
        while not self.log_tracker.get_step_triggered():
            if self.log_tracker.should_stop_upload():
                return False
            QApplication.processEvents()
            time.sleep(0.1)
        
        return True
    
    def process_layer_controls(self, layer_name):
        """
        Process all upload control signals for a layer.
        
        Args:
            layer_name: Name of current layer
            
        Returns:
            str: 'continue' to continue, 'stop' to stop, 'skip' to skip this layer
        """
        # Check for stop signal first
        if self.check_stop_signal(layer_name):
            return 'stop'
        
        # Handle pause
        self.handle_pause()
        
        # Check again after pause
        if self.check_stop_signal(layer_name):
            return 'stop'
        
        # Handle step mode
        if not self.handle_step_mode():
            return 'stop'
        
        return 'continue'
    
    def reset_controls(self):
        """Reset all control flags for next upload session."""
        if self.log_tracker.live_window:
            self.log_tracker.live_window.stop_upload = False
            self.log_tracker.live_window.pause_upload = False
            self.log_tracker.live_window.step_mode = False
            self.log_tracker.live_window.step_triggered = False
