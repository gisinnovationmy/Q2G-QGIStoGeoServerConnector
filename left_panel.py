import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, 
    QPushButton, QTreeWidget, QCheckBox, QRadioButton, QButtonGroup, 
    QAbstractItemView, QListWidgetItem, QScrollArea, QGroupBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

class LeftPanel(QWidget):
    def __init__(self, plugin_dir, is_dark_theme, parent=None):
        super().__init__(parent)
        self.plugin_dir = plugin_dir
        self.is_dark_theme = is_dark_theme
        self._init_ui()

    def _init_ui(self):
        # Create main layout for the panel with minimal margins
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)  # No margins to avoid cutting widgets
        main_layout.setSpacing(0)
        
        # Create scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # Add outline style (no border that takes space)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #cccccc;
                border-radius: 0px;
                background-color: white;
                margin: 0px;
                padding: 0px;
            }
        """)
        
        # Create content widget for scroll area
        content_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(8, 8, 8, 8)  # Padding inside the scroll area
        left_layout.setSpacing(6)  # Space between widgets
        
        # Load Layers button
        load_layout = QHBoxLayout()
        self.load_layers_button = QPushButton("🔄 Load Layers from GeoServer")
        self.load_layers_button.setStyleSheet("QPushButton { font-weight: bold; padding: 8px; }")
        load_layout.addWidget(self.load_layers_button)

        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Type to filter layers...")
        self.search_box.setClearButtonEnabled(True)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box)

        self.header_label = QLabel("Available Layers (Click to sort: A-Z)")
        self.header_label.setStyleSheet("QLabel { background-color : lightgray; padding: 5px; font-weight: bold; }")
        self.header_label.setCursor(Qt.PointingHandCursor)
        
        self.layers_list = QListWidget()
        self.layers_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # Make the layers list 20% higher
        self.layers_list.setMinimumHeight(int(self.layers_list.sizeHint().height() * 1.2))

        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Add as:"))
        self.add_as_group = QButtonGroup(self)
        self.rb_wms = QRadioButton("WMS")
        self.rb_wfs = QRadioButton("WFS")
        self.rb_wmts = QRadioButton("WMTS")
        self.rb_wms.setChecked(True)
        self.add_as_group.addButton(self.rb_wms)
        self.add_as_group.addButton(self.rb_wfs)
        self.add_as_group.addButton(self.rb_wmts)
        type_layout.addWidget(self.rb_wms)
        type_layout.addWidget(self.rb_wfs)
        type_layout.addWidget(self.rb_wmts)
        type_layout.addStretch()

        btn_layout_row1 = QHBoxLayout()
        self.add_button = QPushButton("Add Selected")
        self.add_button.setMinimumHeight(32)
        self.remove_button = QPushButton()
        self.remove_button.setObjectName("delete_btn_unique_name")
        self.remove_button.setIcon(QIcon(os.path.join(self.plugin_dir, 'icons/bin.svg')))
        self.remove_button.setToolTip("Delete Item")
        self.remove_button.setMinimumHeight(32)
        btn_layout_row1.addWidget(self.add_button, 1)
        btn_layout_row1.addWidget(self.remove_button, 0)

        btn_layout_row2 = QHBoxLayout()
        self.save_state_button = QPushButton("Save Map State")
        self.save_state_button.setMinimumHeight(32)
        self.load_state_button = QPushButton("Load Map State")
        self.load_state_button.setMinimumHeight(32)
        self.clear_button = QPushButton("Clear Map")
        self.clear_button.setMinimumHeight(32)
        btn_layout_row2.addWidget(self.save_state_button, 1)
        btn_layout_row2.addWidget(self.load_state_button, 1)
        btn_layout_row2.addWidget(self.clear_button, 1)

        self.added_layers_tree = QTreeWidget()
        self.added_layers_tree.setHeaderLabels(["Visibility", "Layer Name", "Transparency"])
        self.added_layers_tree.setColumnWidth(0, 60)
        self.added_layers_tree.setColumnWidth(1, 180)
        # Set header height to ensure it's visible
        self.added_layers_tree.header().setMinimumHeight(24)
        # Prevent scrollbars and allow proper resizing
        self.added_layers_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.added_layers_tree.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # Set a reasonable minimum height for the layers tree
        self.added_layers_tree.setMinimumHeight(250)

        reorder_layout = QHBoxLayout()
        self.move_up_btn = QPushButton("▲ Move Up")
        self.move_up_btn.setMinimumHeight(32)
        self.move_down_btn = QPushButton("▼ Move Down")
        self.move_down_btn.setMinimumHeight(32)
        reorder_layout.addWidget(self.move_up_btn, 1)
        reorder_layout.addWidget(self.move_down_btn, 1)

        self.zoom_btn = QPushButton("Zoom to Layer")
        self.zoom_btn.setMinimumHeight(32)

        tools_layout = QHBoxLayout()
        tools_layout.addWidget(self.zoom_btn, 1)

        # --- Base Map Mode group (moved from right panel) ---
        base_group = QGroupBox("Base Map Mode")
        base_layout = QHBoxLayout()
        self.rb_base_none = QRadioButton("No base map")
        self.rb_base_light = QRadioButton("Light mode")
        self.rb_base_dark = QRadioButton("Dark mode")
        
        # Apply consistent font size to radio buttons
        font_style = "font-size: 12px;"
        self.rb_base_none.setStyleSheet(font_style)
        self.rb_base_light.setStyleSheet(font_style)
        self.rb_base_dark.setStyleSheet(font_style)
        if self.is_dark_theme:
            self.rb_base_dark.setChecked(True)
        else:
            self.rb_base_light.setChecked(True)
        base_layout.addWidget(self.rb_base_none)
        base_layout.addWidget(self.rb_base_light)
        base_layout.addWidget(self.rb_base_dark)
        base_group.setLayout(base_layout)
        # Group for exclusive selection
        self.base_map_mode_group = QButtonGroup(self)
        self.base_map_mode_group.addButton(self.rb_base_none)
        self.base_map_mode_group.addButton(self.rb_base_light)
        self.base_map_mode_group.addButton(self.rb_base_dark)


        # Add all widgets to the content layout
        left_layout.addLayout(load_layout)
        left_layout.addLayout(search_layout)
        left_layout.addWidget(self.header_label)
        left_layout.addWidget(self.layers_list)
        left_layout.addLayout(type_layout)
        left_layout.addLayout(btn_layout_row1)
        left_layout.addLayout(btn_layout_row2)
        
        # Map Layers section with Select All checkbox
        map_layers_layout = QHBoxLayout()
        map_layers_label = QLabel("Map Layers:")
        self.select_all_layers_checkbox = QCheckBox("Make All Map Layers Visible")
        self.select_all_layers_checkbox.setStyleSheet("font-size: 11px;")
        map_layers_layout.addWidget(map_layers_label)
        map_layers_layout.addStretch()
        map_layers_layout.addWidget(self.select_all_layers_checkbox)
        left_layout.addLayout(map_layers_layout)
        
        left_layout.addWidget(self.added_layers_tree)
        left_layout.addLayout(reorder_layout)
        left_layout.addLayout(tools_layout)
        left_layout.addWidget(base_group)  # Add Base Map Mode group just below Zoom to Layer button
        left_layout.addStretch()
        
        # Set the layout to the content widget
        content_widget.setLayout(left_layout)
        
        # Set the content widget to the scroll area
        scroll_area.setWidget(content_widget)
        
        # Add scroll area to main layout
        main_layout.addWidget(scroll_area)
        
        # Set the main layout to the panel
        self.setLayout(main_layout)

    def connect_signals(self, main_dialog):
        """Connect all widget signals to the main dialog's slots."""
        self.load_layers_button.clicked.connect(main_dialog.start_layer_loading)
        self.search_box.textChanged.connect(main_dialog.filter_layers)
        self.header_label.mousePressEvent = main_dialog.toggle_sort_order
        self.layers_list.itemDoubleClicked.connect(main_dialog.on_available_layer_double_clicked)
        
        self.add_button.clicked.connect(main_dialog.add_layers_to_map)
        self.remove_button.clicked.connect(main_dialog.remove_layer_from_added_list)
        self.clear_button.clicked.connect(main_dialog.clear_openlayers_map)
        
        self.added_layers_tree.itemDoubleClicked.connect(main_dialog.on_added_layer_double_clicked)
        self.move_up_btn.clicked.connect(main_dialog.move_layer_up)
        self.move_down_btn.clicked.connect(main_dialog.move_layer_down)
        self.zoom_btn.clicked.connect(main_dialog.zoom_to_selected_layer)
        
        # Connect base map mode radio buttons
        self.rb_base_none.toggled.connect(main_dialog._on_base_map_mode_changed)
        self.rb_base_light.toggled.connect(main_dialog._on_base_map_mode_changed)
        self.rb_base_dark.toggled.connect(main_dialog._on_base_map_mode_changed)

        self.save_state_button.clicked.connect(main_dialog._on_save_state)
        self.load_state_button.clicked.connect(main_dialog._on_load_state)
        
        # Connect Select All Layers checkbox
        self.select_all_layers_checkbox.stateChanged.connect(main_dialog.toggle_select_all_layers)
        # Connect tree item changes to update checkbox state (when visibility/selection changes)
        self.added_layers_tree.itemSelectionChanged.connect(main_dialog.update_select_all_checkbox_state)
        self.added_layers_tree.itemChanged.connect(main_dialog.update_select_all_checkbox_state)

    def set_controls_enabled(self, enabled):
        """Enable or disable controls, typically during loading."""
        self.load_layers_button.setEnabled(enabled)
        self.search_box.setEnabled(enabled)
        self.layers_list.setEnabled(enabled)
        self.add_button.setEnabled(enabled)
        self.remove_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)
        self.added_layers_tree.setEnabled(enabled)
        self.move_up_btn.setEnabled(enabled)
        self.move_down_btn.setEnabled(enabled)
        self.zoom_btn.setEnabled(enabled)

    def add_available_layer(self, layer_data):
        """Add a single layer to the available layers list."""
        name = layer_data.get('name', 'Unnamed')
        item = QListWidgetItem(name)
        item.setData(Qt.UserRole, layer_data)
        self.layers_list.addItem(item)

    def filter_layers(self, text, all_layers):
        """Filter the available layers list based on search text."""
        self.layers_list.clear()
        if not text:
            for layer in all_layers:
                self.add_available_layer(layer)
        else:
            for layer in all_layers:
                if text.lower() in layer.get('name', '').lower():
                    self.add_available_layer(layer)
