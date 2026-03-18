"""
Delete Selected Style Module
Handles deletion of selected styles from GeoServer via REST API.
Extracted from main.py for better code organization and maintainability.
"""

import requests
from qgis.PyQt.QtWidgets import QMessageBox


class StyleDeletionManager:
    """Handles deletion of selected styles from GeoServer."""
    
    def __init__(self, main_instance):
        """
        Initialize the style deletion manager.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def delete_selected_style(self):
        """
        Delete all selected styles from the styles list.
        
        This method will:
        1. Get selected styles from the UI
        2. Confirm deletion with user
        3. Delete each style via GeoServer REST API
        4. Provide feedback and refresh the styles list
        """
        # Get selected styles
        selected_items = self._get_selected_styles()
        if not selected_items:
            return
        
        style_names = [item.text() for item in selected_items]
        
        # Confirm deletion with user
        if not self._confirm_deletion(style_names):
            return
        
        # Get connection details
        connection_details = self._get_connection_details()
        if not connection_details:
            return
        
        url, username, password = connection_details
        
        # Execute deletion
        self._execute_style_deletion(style_names, url, username, password)
    
    def _get_selected_styles(self):
        """
        Get selected styles from the UI.
        
        Returns:
            list: Selected style items or None if no selection
        """
        selected_items = self.main.layer_styles_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self.main, "Selection Error", "Please select at least one style to delete.")
            return None
        return selected_items
    
    def _confirm_deletion(self, style_names):
        """
        Confirm deletion with the user.
        
        Args:
            style_names: List of style names to delete
            
        Returns:
            bool: True if user confirmed, False if cancelled
        """
        num_styles = len(style_names)
        
        # Create confirmation message
        if num_styles == 1:
            confirm_msg = f"Are you sure you want to delete the style '{style_names[0]}' from GeoServer?"
        else:
            confirm_msg = f"Are you sure you want to delete {num_styles} styles from GeoServer?\n\n" + "\n".join(style_names)
        
        reply = QMessageBox.question(
            self.main, 
            'Confirm Delete', 
            confirm_msg,
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.No
        )

        return reply == QMessageBox.Yes
    
    def _get_connection_details(self):
        """
        Get and validate GeoServer connection details.
        
        Returns:
            tuple: (url, username, password) or None if validation fails
        """
        url = self.main.get_base_url()
        username = self.main.username_input.text().strip()
        password = self.main.password_input.text().strip()
        
        if not all([url, username, password]):
            QMessageBox.warning(self.main, "Input Error", "Please fill in all GeoServer connection details.")
            return None
        
        return url, username, password
    
    def _execute_style_deletion(self, style_names, url, username, password):
        """
        Execute the deletion of styles via GeoServer REST API.
        
        Args:
            style_names: List of style names to delete
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
        """
        try:
            deleted_count = 0
            failed_count = 0
            
            # Delete each selected style
            for style_name in style_names:
                success = self._delete_single_style(style_name, url, username, password)
                if success:
                    deleted_count += 1
                else:
                    failed_count += 1
            
            # Show summary and refresh if needed
            self._show_deletion_summary(deleted_count, failed_count)

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self.main, "Request Error", f"An error occurred: {e}")
            self.main.log_message(f"Error deleting styles: {e}")
    
    def _delete_single_style(self, style_name, url, username, password):
        """
        Delete a single style via GeoServer REST API.
        
        Args:
            style_name: Name of the style to delete
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            response = requests.delete(
                f"{url}/rest/styles/{style_name}.json",
                auth=(username, password)
            )

            if response.status_code == 200:
                self.main.log_message(f"✓ Deleted style: {style_name}")
                return True
            elif response.status_code == 404:
                self.main.log_message(f"⚠ Style not found: {style_name}")
                return False
            else:
                self.main.log_message(f"✗ Failed to delete style {style_name}: {response.status_code}")
                return False
                
        except Exception as e:
            self.main.log_message(f"✗ Error deleting style {style_name}: {e}")
            return False
    
    def _show_deletion_summary(self, deleted_count, failed_count):
        """
        Show deletion summary and refresh styles list if needed.
        
        Args:
            deleted_count: Number of successfully deleted styles
            failed_count: Number of failed deletions
        """
        # Show summary
        if deleted_count > 0:
            QMessageBox.information(self.main, "Success", f"Successfully deleted {deleted_count} style(s).")
            # Refresh the styles list
            self.main.load_layer_styles()
        
        if failed_count > 0:
            QMessageBox.warning(self.main, "Partial Failure", f"Failed to delete {failed_count} style(s).")
