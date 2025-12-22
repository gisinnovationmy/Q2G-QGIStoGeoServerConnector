"""
Upload Thread Module
Handles layer uploads in a background thread to prevent UI freezing.
"""

from qgis.PyQt.QtCore import QThread, pyqtSignal


class UploadThread(QThread):
    """Background thread for handling layer uploads."""
    
    # Signals
    upload_finished = pyqtSignal(bool)  # True if successful, False if failed
    upload_error = pyqtSignal(str)      # Error message
    show_completion_popup = pyqtSignal()  # Signal to show completion popup on main thread
    progress_updated = pyqtSignal(int)  # Signal for progress bar updates (0-100)
    
    def __init__(self, upload_function):
        """
        Initialize the upload thread.
        
        Args:
            upload_function: The function to call for the actual upload
        """
        super().__init__()
        self.upload_function = upload_function
        self.progress_callback = None  # Optional callback for progress updates
    
    def run(self):
        """Run the upload in a background thread."""
        try:
            # Call the upload function
            result = self.upload_function()
            
            # Emit success signal
            self.upload_finished.emit(result if isinstance(result, bool) else True)
        except Exception as e:
            # Emit error signal
            self.upload_error.emit(str(e))
            self.upload_finished.emit(False)
