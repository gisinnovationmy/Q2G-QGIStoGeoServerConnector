"""
PostGIS Credentials Dialog

This module provides a dialog for managing PostGIS database credentials
for the Q2G QGIS Plugin.
"""

import traceback
import os
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QPushButton, 
    QLabel, QListWidget, QListWidgetItem, QMessageBox, QGroupBox, QSpinBox, QComboBox
)
from qgis.PyQt.QtGui import QIcon

# Dynamic import using ImportManager (works with any folder name)
from .import_manager import dynamic_import

PostGISCredentialsManager = dynamic_import("postgis_credentials", "PostGISCredentialsManager")


class PostGISCredentialsDialog(QDialog):
        """Dialog for managing PostGIS database credentials."""
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("PostGIS Credentials Manager")
            self.setMinimumSize(600, 400)
            self.setWindowFlags(Qt.Window | Qt.WindowSystemMenuHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
            
            # Initialize credentials manager
            self.credentials_manager = PostGISCredentialsManager()
            
            # Print debug info about credentials file location
            print(f"DEBUG: PostGIS credentials file will be saved to: {self.credentials_manager.config_path}")
        
            # Setup UI
            self.setup_ui()
            self.load_qgis_connections()
            self.load_saved_connections()
            
            # Set modern stylesheet
            self.setStyleSheet('''
                QDialog { background: #f6f6f6; }
                QGroupBox { font-weight: bold; border: 1px solid #bbb; border-radius: 6px; margin-top: 8px; background: #fcfcfc; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; }
                QLabel { font-size: 10pt; }
                QLineEdit, QSpinBox, QListWidget { font-size: 10pt; background: #fff; border: 1px solid #ccc; border-radius: 3px; }
                QPushButton { font-size: 10pt; padding: 6px 16px; background: #e6e6e6; border: 1px solid #aaa; border-radius: 4px; }
                QPushButton:hover { background: #d0eaff; border: 1px solid #3399ff; }
                QPushButton:pressed { background: #b5d9ff; }
                QPushButton#save { background: #4CAF50; color: white; border: 1px solid #388E3C; }
                QPushButton#delete { background: #f44336; color: white; border: 1px solid #b71c1c; }
            ''')
        
        def setup_ui(self):
            """Setup the user interface."""
            main_layout = QVBoxLayout()
            main_layout.setSpacing(12)
            
            # Connection form section
            form_group = QGroupBox("PostGIS Connection Details")
            form_layout = QFormLayout()
            
            # QGIS connections combobox
            self.qgis_connections_combo = QComboBox()
            self.qgis_connections_combo.addItem("-- Select QGIS Connection --", None)
            self.qgis_connections_combo.currentTextChanged.connect(self.load_qgis_connection)
            form_layout.addRow("QGIS Connections:", self.qgis_connections_combo)
            
            self.host_input = QLineEdit()
            self.host_input.setPlaceholderText("localhost")
            form_layout.addRow("Host:", self.host_input)
            
            self.port_input = QSpinBox()
            self.port_input.setRange(1, 65535)
            self.port_input.setValue(5432)
            form_layout.addRow("Port:", self.port_input)
            
            self.database_input = QLineEdit()
            self.database_input.setPlaceholderText("postgres")
            form_layout.addRow("Database:", self.database_input)
            
            self.username_input = QLineEdit()
            self.username_input.setPlaceholderText("postgres")
            form_layout.addRow("Username:", self.username_input)
            
            self.password_input = QLineEdit()
            self.password_input.setEchoMode(QLineEdit.Password)
            self.password_input.setPlaceholderText("Enter password")
            form_layout.addRow("Password:", self.password_input)
            
            self.schema_input = QLineEdit()
            self.schema_input.setText("public")
            self.schema_input.setPlaceholderText("public")
            form_layout.addRow("Schema:", self.schema_input)
            
            form_group.setLayout(form_layout)
            main_layout.addWidget(form_group)
            
            # Buttons for form actions
            form_buttons_layout = QHBoxLayout()
            
            self.save_btn = QPushButton("Save Credentials")
            self.save_btn.setObjectName("save")
            self.save_btn.clicked.connect(self.save_credentials)
            form_buttons_layout.addWidget(self.save_btn)
            
            self.test_btn = QPushButton("Test Connection")
            self.test_btn.clicked.connect(self.test_connection)
            form_buttons_layout.addWidget(self.test_btn)
            
            self.clear_btn = QPushButton("Clear Form")
            self.clear_btn.clicked.connect(self.clear_form)
            form_buttons_layout.addWidget(self.clear_btn)
            
            form_buttons_layout.addStretch()
            main_layout.addLayout(form_buttons_layout)
            
            # Saved connections section
            connections_group = QGroupBox("Saved Connections")
            connections_layout = QVBoxLayout()
            
            self.connections_list = QListWidget()
            self.connections_list.itemClicked.connect(self.load_connection_details)
            connections_layout.addWidget(self.connections_list)
            
            # Buttons for connection management
            connections_buttons_layout = QHBoxLayout()
            
            self.refresh_btn = QPushButton("Refresh List")
            self.refresh_btn.clicked.connect(self.load_saved_connections)
            connections_buttons_layout.addWidget(self.refresh_btn)
            
            self.delete_btn = QPushButton("Delete Selected")
            self.delete_btn.setObjectName("delete")
            self.delete_btn.clicked.connect(self.delete_selected_connection)
            connections_buttons_layout.addWidget(self.delete_btn)
            
            connections_buttons_layout.addStretch()
            connections_layout.addLayout(connections_buttons_layout)
            
            connections_group.setLayout(connections_layout)
            main_layout.addWidget(connections_group)
            
            # Dialog buttons
            dialog_buttons_layout = QHBoxLayout()
            
            self.close_btn = QPushButton("Close")
            self.close_btn.clicked.connect(self.accept)
            dialog_buttons_layout.addStretch()
            dialog_buttons_layout.addWidget(self.close_btn)
            
            main_layout.addLayout(dialog_buttons_layout)
            
            self.setLayout(main_layout)
    
        def save_credentials(self):
            """Save the current form data as PostGIS credentials."""
            # Validate required fields
            host = self.host_input.text().strip()
            db = self.database_input.text().strip()
            user = self.username_input.text().strip()
            passwd = self.password_input.text().strip()
            
            if not all([host, db, user, passwd]):
                QMessageBox.warning(self, "Error", "Fill in: Host, Database, Username, Password")
                return
            
            # Prepare credentials
            pg_params = {
                'host': host,
                'port': self.port_input.value(),
                'database': db,
                'user': user,
                'passwd': passwd,
                'schema': self.schema_input.text().strip() or 'public',
                'table': ''
            }
            
            # Save
            if self.credentials_manager.save_credentials(pg_params):
                count = len(self.credentials_manager.list_saved_connections())
                QMessageBox.information(self, "Saved", 
                    f"✓ Credentials saved!\n\n"
                    f"{db}@{host}:{self.port_input.value()}\n"
                    f"User: {user}\n\n"
                    f"Total connections: {count}")
                self.load_saved_connections()
            else:
                QMessageBox.critical(self, "Error", "Failed to save credentials")
        
        def test_connection(self):
            """Test the PostGIS connection with current form data."""
            # Validate required fields
            if not all([self.host_input.text().strip(), 
                       self.database_input.text().strip(), 
                       self.username_input.text().strip(),
                       self.password_input.text().strip()]):
                QMessageBox.warning(self, "Validation Error", 
                                  "Please fill in all required fields to test connection.")
                return
            
            try:
                from qgis.core import QgsDataSourceUri, QgsProviderRegistry
                
                # Create test URI
                uri = QgsDataSourceUri()
                uri.setConnection(
                    self.host_input.text().strip(),
                    str(self.port_input.value()),
                    self.database_input.text().strip(),
                    self.username_input.text().strip(),
                    self.password_input.text().strip()
                )
                
                # Test connection using QGIS provider
                metadata = QgsProviderRegistry.instance().providerMetadata('postgres')
                if metadata:
                    connection = metadata.createConnection(uri.uri(), {})
                    if connection:
                        # Try to get schemas to verify connection
                        schemas = connection.schemas()
                        QMessageBox.information(self, "Connection Test", 
                                              f"✓ Connection successful!\nFound {len(schemas)} schemas in database.")
                        return
                
                QMessageBox.warning(self, "Connection Test", "✗ Connection failed. Please check your credentials.")
                
            except Exception as e:
                QMessageBox.critical(self, "Connection Test", f"✗ Connection error: {str(e)}")
    
        def clear_form(self):
            """Clear all form fields."""
            self.host_input.clear()
            self.port_input.setValue(5432)
            self.database_input.clear()
            self.username_input.clear()
            self.password_input.clear()
            self.schema_input.setText("public")
        
        def load_saved_connections(self):
            """Load and display saved PostGIS connections."""
            self.connections_list.clear()
            
            connections = self.credentials_manager.list_saved_connections()
            
            for conn in connections:
                display_text = f"{conn['database']}@{conn['host']}:{conn['port']} (User: {conn['user']})"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, conn)  # Store connection data
                self.connections_list.addItem(item)
            
            if not connections:
                item = QListWidgetItem("No saved connections found")
                item.setFlags(Qt.NoItemFlags)  # Make it non-selectable
                self.connections_list.addItem(item)
        
        def load_connection_details(self, item):
            """Load connection details into the form when an item is clicked."""
            conn_data = item.data(Qt.UserRole)
            
            if conn_data:
                self.host_input.setText(conn_data.get('host', ''))
                self.port_input.setValue(int(conn_data.get('port', 5432)))
                self.database_input.setText(conn_data.get('database', ''))
                self.username_input.setText(conn_data.get('user', ''))
                self.password_input.setText(conn_data.get('passwd', ''))
                self.schema_input.setText(conn_data.get('schema', 'public'))
        
        def delete_selected_connection(self):
            """Delete the selected connection."""
            current_item = self.connections_list.currentItem()
            
            if not current_item:
                QMessageBox.warning(self, "Selection Error", "Please select a connection to delete.")
                return
            
            conn_data = current_item.data(Qt.UserRole)
            if not conn_data:
                return
            
            # Confirm deletion
            reply = QMessageBox.question(
                self, "Confirm Deletion", 
                f"Are you sure you want to delete the connection for:\n{conn_data['database']}@{conn_data['host']}:{conn_data['port']}?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                success = self.credentials_manager.delete_credentials(
                    conn_data['database'], 
                    conn_data['host'], 
                    conn_data['port']
                )
                
                if success:
                    QMessageBox.information(self, "Success", "Connection deleted successfully.")
                    self.load_saved_connections()  # Refresh the list
                    self.clear_form()  # Clear the form
                else:
                    QMessageBox.critical(self, "Error", "Failed to delete connection.")
        
        def load_qgis_connections(self):
            """Load PostgreSQL connections from QGIS and populate the combobox."""
            try:
                from qgis.core import QgsProviderRegistry
                
                # Clear existing items except the first one
                while self.qgis_connections_combo.count() > 1:
                    self.qgis_connections_combo.removeItem(1)
                
                # Get PostgreSQL provider metadata
                metadata = QgsProviderRegistry.instance().providerMetadata('postgres')
                if metadata:
                    # Get all saved connections
                    connection_names = metadata.connections().keys()
                    
                    for conn_name in sorted(connection_names):
                        connection = metadata.connections()[conn_name]
                        # Store the connection object in the combo item data
                        self.qgis_connections_combo.addItem(conn_name, connection)
                    
                    if connection_names:
                        print(f"Loaded {len(connection_names)} QGIS PostgreSQL connections")
                    else:
                        print("No QGIS PostgreSQL connections found")
                else:
                    print("Could not get PostgreSQL provider metadata")
                    
            except Exception as e:
                print(f"Error loading QGIS connections: {str(e)}")
        
        def load_qgis_connection(self, connection_name):
            """Load connection details from selected QGIS connection."""
            if connection_name == "-- Select QGIS Connection --":
                return
                
            try:
                # Get the connection object from the combo box data
                current_index = self.qgis_connections_combo.currentIndex()
                if current_index <= 0:
                    return
                    
                connection = self.qgis_connections_combo.itemData(current_index)
                if connection:
                    # Get connection configuration - try different methods
                    config = {}
                    try:
                        if hasattr(connection, 'configuration'):
                            config = connection.configuration()
                        elif hasattr(connection, 'uri'):
                            # Try to get from URI
                            uri = connection.uri()
                            config = {
                                'host': uri.host() if hasattr(uri, 'host') else 'localhost',
                                'port': uri.port() if hasattr(uri, 'port') else '5432',
                                'database': uri.database() if hasattr(uri, 'database') else '',
                                'username': uri.username() if hasattr(uri, 'username') else '',
                                'schema': uri.schema() if hasattr(uri, 'schema') else 'public'
                            }
                        else:
                            print(f"Connection object type: {type(connection)}")
                            print(f"Connection attributes: {dir(connection)}")
                            QMessageBox.warning(self, "Connection Error", "Could not read connection configuration")
                            return
                    except Exception as e:
                        print(f"Error getting configuration: {str(e)}")
                        QMessageBox.warning(self, "Connection Error", f"Error reading connection: {str(e)}")
                        return
                    
                    # Populate the form fields with connection details
                    self.host_input.setText(str(config.get('host', 'localhost')))
                    
                    try:
                        port_value = int(config.get('port', '5432'))
                    except (ValueError, TypeError):
                        port_value = 5432
                    self.port_input.setValue(port_value)
                    
                    self.database_input.setText(str(config.get('database', '')))
                    self.username_input.setText(str(config.get('username', '')))
                    self.schema_input.setText(str(config.get('schema', 'public')))
                    
                    # Clear password field for security
                    self.password_input.clear()
                    self.password_input.setPlaceholderText("Enter password for this connection")
                    
                    # Focus on password field since other details are filled
                    self.password_input.setFocus()
                    
                    print(f"Loaded connection details for: {connection_name}")
                
            except Exception as e:
                QMessageBox.warning(self, "Connection Load Error", f"Failed to load connection details: {str(e)}")
