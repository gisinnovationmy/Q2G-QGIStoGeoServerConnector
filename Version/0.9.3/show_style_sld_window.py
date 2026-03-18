"""
Show Style SLD Window Module
Handles displaying SLD content for selected styles from the workspace.
Extracted from main.py for better code organization and maintainability.
"""

import requests
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QWidget, QMessageBox
from qgis.PyQt.QtXml import QDomDocument


class StyleSLDWindowManager:
    """Handles displaying SLD content for workspace styles."""
    
    def __init__(self, main_instance):
        """
        Initialize the style SLD window manager.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def show_style_sld_window(self, style_name):
        """
        Display the SLD content of a selected style from the workspace layer styles list.
        
        Args:
            style_name: Name of the style to display SLD content for
        """
        # Get connection details
        connection_details = self._get_connection_details()
        if not connection_details:
            return
        
        url, username, password, workspace_name = connection_details
        
        # Fetch SLD content
        sld_content = self._fetch_sld_content(style_name, workspace_name, url, username, password)
        if not sld_content:
            return
        
        # Create and show the SLD dialog
        self._create_and_show_sld_dialog(style_name, sld_content)
    
    def _get_connection_details(self):
        """
        Get and validate connection details.
        
        Returns:
            tuple: (url, username, password, workspace_name) or None if validation fails
        """
        url = self.main.get_base_url()
        username = self.main.username_input.text().strip()
        password = self.main.password_input.text().strip()
        
        if not all([url, username, password]):
            QMessageBox.warning(self.main, "Input Error", "Please fill in all GeoServer connection details.")
            return None
        
        # Get selected workspace
        selected_workspace_items = self.main.workspaces_list.selectedItems()
        if not selected_workspace_items:
            QMessageBox.warning(self.main, "Workspace Error", "Please select a workspace.")
            return None
        
        workspace_name = selected_workspace_items[0].text()
        return url, username, password, workspace_name
    
    def _fetch_sld_content(self, style_name, workspace_name, url, username, password):
        """
        Fetch SLD content from GeoServer.
        
        Args:
            style_name: Name of the style
            workspace_name: Name of the workspace
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            str: SLD content or None if fetch failed
        """
        try:
            # Fetch the SLD content for the selected style in the selected workspace
            response = requests.get(
                f"{url}/rest/workspaces/{workspace_name}/styles/{style_name}.sld",
                auth=(username, password),
                headers={"Accept": "application/vnd.ogc.sld+xml"}
            )
            
            if response.status_code == 200:
                sld_content = response.text
                if not sld_content:
                    QMessageBox.warning(self.main, "Warning", "SLD content is empty.")
                    return None
                return sld_content
            else:
                QMessageBox.warning(self.main, "Error", f"Failed to fetch SLD for style '{style_name}'. Status code: {response.status_code}")
                return None
                
        except Exception as e:
            QMessageBox.critical(self.main, "Error", f"Failed to retrieve SLD for style '{style_name}': {str(e)}")
            return None
    
    def _create_and_show_sld_dialog(self, style_name, sld_content):
        """
        Create and display the SLD dialog window.
        
        Args:
            style_name: Name of the style
            sld_content: SLD content to display
        """
        # Create a dialog window to display the SLD
        sld_dialog = QDialog(self.main)
        sld_dialog.setWindowTitle(f"SLD for Style: {style_name}")
        sld_dialog.resize(600, 400)
        
        layout = QVBoxLayout()
        
        # Add text area to display SLD content with XML formatting
        sld_text = self._create_sld_text_widget(sld_content)
        layout.addWidget(sld_text)
        
        # Add buttons
        button_widget = self._create_button_widget(style_name, sld_content, sld_dialog)
        layout.addWidget(button_widget)
        
        sld_dialog.setLayout(layout)
        sld_dialog.show()
    
    def _create_sld_text_widget(self, sld_content):
        """
        Create and configure the text widget for displaying SLD content.
        
        Args:
            sld_content: SLD content to display
            
        Returns:
            QTextEdit: Configured text widget
        """
        sld_text = QTextEdit()
        sld_text.setReadOnly(True)
        
        # Try to format the XML content for better readability
        formatted_content = self._format_xml_content(sld_content)
        sld_text.setPlainText(formatted_content)
        
        # Set font for better XML readability
        font = sld_text.font()
        font.setFamily("Courier New")
        font.setPointSize(10)
        sld_text.setFont(font)
        
        return sld_text
    
    def _format_xml_content(self, sld_content):
        """
        Format XML content for better readability.
        
        Args:
            sld_content: Raw SLD content
            
        Returns:
            str: Formatted XML content
        """
        try:
            # Use QDomDocument to format the XML
            doc = QDomDocument()
            if doc.setContent(sld_content):
                # Format the XML with indentation
                return doc.toString(4)  # 4 spaces for indentation
            else:
                # If XML parsing fails, display as plain text
                return sld_content
        except Exception:
            # If QDomDocument is not available or fails, display as plain text
            return sld_content
    
    def _create_button_widget(self, style_name, sld_content, sld_dialog):
        """
        Create the button widget for the SLD dialog.
        
        Args:
            style_name: Name of the style
            sld_content: SLD content
            sld_dialog: The dialog window
            
        Returns:
            QWidget: Widget containing the buttons
        """
        # Add buttons
        btn_save = QPushButton("Save SLD")
        btn_save.clicked.connect(lambda: self.main.save_sld(style_name, sld_content, sld_dialog))
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(sld_dialog.close)
        
        # Create a layout for the buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(btn_save)
        button_layout.addWidget(btn_close)
        button_layout.addStretch()
        
        widget = QWidget()
        widget.setLayout(button_layout)
        
        return widget
