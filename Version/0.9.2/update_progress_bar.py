"""
Update Progress Bar Module
Handles progress bar updates with dynamic text color based on fill percentage.
Extracted from main.py for better code organization and maintainability.
"""

import re
from qgis.PyQt.QtCore import QObject, pyqtSignal


class ProgressBarUpdater(QObject):
    """Handles progress bar updates with dynamic styling (thread-safe)."""
    
    # Signal for thread-safe progress updates
    progress_signal = pyqtSignal(int)
    
    def __init__(self, main_instance):
        """
        Initialize the progress bar updater.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        super().__init__()
        self.main = main_instance
        # Connect signal to slot for thread-safe updates
        self.progress_signal.connect(self._on_progress_update)
    
    def update_progress_bar(self, value):
        """
        Update progress bar with dynamic text color based on fill percentage.
        
        This method is thread-safe and can be called from background threads.
        It emits a signal that updates the UI on the main thread.
        
        The text color changes based on progress:
        - ≤50%: Black text for visibility against light background
        - >50%: White text for contrast against blue progress fill
        
        Args:
            value: Progress value (0-100)
        """
        # Emit signal to update UI on main thread (thread-safe)
        self.progress_signal.emit(value)
    
    def _on_progress_update(self, value):
        """
        Slot to handle progress updates on the main thread.
        This is called when the progress_signal is emitted.
        
        Args:
            value: Progress value (0-100)
        """
        # Set the progress bar value (now on main thread, safe)
        self.main.load_progress_bar.setValue(value)
        
        # Determine text color based on progress percentage
        text_color = self._get_text_color_for_progress(value)
        
        # Update the progress bar stylesheet with new text color
        self._update_progress_bar_style(text_color)
    
    def _get_text_color_for_progress(self, value):
        """
        Determine the appropriate text color based on progress percentage.
        
        Args:
            value: Progress value (0-100)
            
        Returns:
            str: Color name ("black" or "white")
        """
        # Change text color based on progress percentage
        if value <= 50:
            return "black"  # Black text for visibility on light background
        else:
            return "white"  # White text for contrast on blue progress fill
    
    def _update_progress_bar_style(self, text_color):
        """
        Update the progress bar stylesheet with the new text color.
        
        Args:
            text_color: Color name to apply to the text
        """
        # Get current stylesheet
        current_sheet = self.main.load_progress_bar.styleSheet()
        
        # Replace any existing color declaration with the new one
        new_sheet = re.sub(r'color:\s*[^;]+;', f'color: {text_color};', current_sheet)
        
        # Apply the updated stylesheet
        self.main.load_progress_bar.setStyleSheet(new_sheet)
