"""
Setup Layers and Styles Sections Module
Handles UI setup for workspace layers, styles, and datastores sections.
Extracted from main.py for better code organization and maintainability.
"""

import os
from qgis.PyQt.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, QListWidget, 
                                QPushButton, QCheckBox, QAbstractItemView, QSizePolicy, QLineEdit)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QIcon


class LayersAndStylesSetupManager:
    """Handles UI setup for workspace layers, styles, and datastores sections."""
    
    def __init__(self, main_instance):
        """
        Initialize the layers and styles setup manager.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def setup_layers_and_styles_sections(self, top_splitter):
        """
        Setup workspace layers, datastores, and styles sections.
        
        This method creates three main UI sections in the correct order:
        1. Workspace Layers - List of layers in the selected workspace with delete functionality
        2. Datastores - List of datastores and coverage stores with selection and delete functionality
        3. Styles List - List of SLD styles with view/delete functionality  
        
        Args:
            top_splitter: QSplitter widget to add the sections to
        """
        # Setup each section in the correct order
        self._setup_workspace_layers_section(top_splitter)
        self._setup_datastores_section(top_splitter)
        self._setup_styles_section(top_splitter)
    
    def _setup_workspace_layers_section(self, top_splitter):
        """
        Setup the workspace layers section with list and controls.
        
        Args:
            top_splitter: QSplitter widget to add the section to
        """
        # Workspace Layers Section
        wl_group = QGroupBox("Workspace Layers")
        wl_layout = QVBoxLayout()
        
        # Create and configure the draggable layers list widget
        try:
            from .draggable_layers_list import DraggableLayersList
        except ImportError:
            # Fallback for direct execution
            import sys
            import os
            sys.path.insert(0, os.path.dirname(__file__))
            from draggable_layers_list import DraggableLayersList
        
        self.main.workspace_layers_list = DraggableLayersList()
        self.main.workspace_layers_list.itemSelectionChanged.connect(self.main.load_layer_styles)
        self.main.workspace_layers_list.itemSelectionChanged.connect(self.main.uncheck_select_all_if_checked)
        self.main.workspace_layers_list.model().rowsInserted.connect(self.main.uncheck_select_all_if_checked)
        self.main.workspace_layers_list.model().rowsRemoved.connect(self.main.uncheck_select_all_if_checked)
        
        # Store full list of layers for filtering
        self.main.all_workspace_layers = []
        
        wl_layout.addWidget(self.main.workspace_layers_list)
        
        # Create search filter textbox (below the list)
        self.main.workspace_layers_filter = QLineEdit()
        self.main.workspace_layers_filter.setPlaceholderText("Search...")
        self.main.workspace_layers_filter.textChanged.connect(self.main.filter_workspace_layers)
        wl_layout.addWidget(self.main.workspace_layers_filter)
        
        # Create delete layer button
        self.main.delete_layer_btn = self._create_delete_button(
            object_name="delete",
            tooltip="Delete Layer",
            click_handler=self.main.delete_layer
        )
        
        # Create select all layers checkbox
        self.main.select_all_layers_checkbox = QCheckBox("Select All Layers")
        self.main.select_all_layers_checkbox.stateChanged.connect(self.main.toggle_layer_selection)
        self.main.user_initiated_checkbox_change = False
        
        # Layout for selection and delete controls
        select_del_row = QHBoxLayout()
        select_del_row.addWidget(self.main.select_all_layers_checkbox)
        select_del_row.addWidget(self.main.delete_layer_btn)
        select_del_row.addStretch(1)
        wl_layout.addLayout(select_del_row)
        
        # Finalize workspace layers section
        wl_group.setLayout(wl_layout)
        top_splitter.addWidget(wl_group)
    
    def _setup_styles_section(self, top_splitter):
        """
        Setup the styles list section with controls.
        
        Args:
            top_splitter: QSplitter widget to add the section to
        """
        # Styles List Section
        sld_group = QGroupBox("Styles List")
        sld_layout = QVBoxLayout()
        
        # Create and configure the styles list widget
        self.main.layer_styles_list = QListWidget()
        self.main.layer_styles_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # Connect selection change to uncheck "Select All Styles" if not all items are selected
        self.main.layer_styles_list.itemSelectionChanged.connect(self.main.uncheck_select_all_styles_if_needed)
        # Connect model changes to uncheck "Select All Styles" when items are added/removed
        self.main.layer_styles_list.model().rowsInserted.connect(self.main.uncheck_select_all_styles_if_needed)
        self.main.layer_styles_list.model().rowsRemoved.connect(self.main.uncheck_select_all_styles_if_needed)
        sld_layout.addWidget(self.main.layer_styles_list)
        
        # Create styles control buttons row
        btn_row2 = QHBoxLayout()
        
        # Refresh styles button
        self.main.refresh_styles_btn = QPushButton("Refresh Styles")
        self.main.refresh_styles_btn.clicked.connect(self.main.load_layer_styles)
        btn_row2.addWidget(self.main.refresh_styles_btn)
        
        # Delete style button
        self.main.delete_style_btn = self._create_delete_button(
            object_name="delete_style_btn",
            tooltip="Delete Style",
            click_handler=self.main.delete_selected_style
        )
        
        # Show style SLD button
        self.main.show_style_sld_btn = QPushButton("Show Style (SLD)")
        self.main.show_style_sld_btn.clicked.connect(self.main.show_sld_for_selected_style)
        btn_row2.addWidget(self.main.show_style_sld_btn)
        btn_row2.addWidget(self.main.delete_style_btn)
        
        # Select all styles checkbox
        self.main.select_all_styles_checkbox = QCheckBox("Select All Styles")
        self.main.select_all_styles_checkbox.stateChanged.connect(self.main.toggle_select_all_styles)
        btn_row2.addWidget(self.main.select_all_styles_checkbox)
        btn_row2.addStretch(1)
        sld_layout.addLayout(btn_row2)
        
        # Finalize styles section
        sld_group.setLayout(sld_layout)
        top_splitter.addWidget(sld_group)
    
    def _setup_datastores_section(self, top_splitter):
        """
        Setup the datastores section with list and controls.
        
        Args:
            top_splitter: QSplitter widget to add the section to
        """
        # Datastores Section
        datastores_group = QGroupBox("Datastores")
        datastores_layout = QVBoxLayout()
        
        # Create and configure the datastores list widget
        self.main.datastores_list = QListWidget()
        self.main.datastores_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # Connect selection change to uncheck "Select All" if not all items are selected
        self.main.datastores_list.itemSelectionChanged.connect(self.main.uncheck_select_all_datastores_if_needed)
        # Connect model changes to uncheck "Select All" when items are added/removed
        self.main.datastores_list.model().rowsInserted.connect(self.main.uncheck_select_all_datastores_if_needed)
        self.main.datastores_list.model().rowsRemoved.connect(self.main.uncheck_select_all_datastores_if_needed)
        datastores_layout.addWidget(self.main.datastores_list)
        
        # Create select all datastores checkbox
        self.main.select_all_datastores_checkbox = QCheckBox("Select All Datastores")
        self.main.select_all_datastores_checkbox.setChecked(False)
        self.main.select_all_datastores_checkbox.stateChanged.connect(self.main.select_all_datastores)
        
        # Create delete datastore button
        self.main.delete_datastore_btn = self._create_delete_button(
            object_name="delete",
            tooltip="Delete Selected Datastores",
            click_handler=self.main.delete_selected_datastores
        )
        
        # Layout for datastore controls
        datastores_buttons_layout = QHBoxLayout()
        datastores_buttons_layout.addWidget(self.main.select_all_datastores_checkbox)
        datastores_buttons_layout.addWidget(self.main.delete_datastore_btn)
        datastores_buttons_layout.addStretch(1)
        
        datastores_layout.addLayout(datastores_buttons_layout)
        
        # Finalize datastores section
        datastores_group.setLayout(datastores_layout)
        top_splitter.addWidget(datastores_group)
    
    def _create_delete_button(self, object_name, tooltip, click_handler):
        """
        Create a standardized delete button with consistent styling.
        
        Args:
            object_name: Object name for the button
            tooltip: Tooltip text for the button
            click_handler: Function to call when button is clicked
            
        Returns:
            QPushButton: Configured delete button
        """
        button = QPushButton()
        button.setObjectName(object_name)
        button.setIcon(QIcon(os.path.join(self.main.plugin_dir, 'icons/bin.svg')))
        button.setIconSize(QSize(16, 16))
        button.setFixedSize(16, 16)
        button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        button.setToolTip(tooltip)
        button.setStyleSheet("""
            QPushButton {
                background-color: #e6e6e6;
                border: 1px solid #aaa;
                border-radius: 4px;
                padding: 3px;
            }
            QPushButton:hover {
                background-color: #d0eaff;
                border: 1px solid #3399ff;
            }
        """)
        button.clicked.connect(click_handler)
        return button
