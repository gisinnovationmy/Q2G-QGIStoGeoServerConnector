import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, 
    QPushButton, QTreeWidget, QCheckBox, QRadioButton, QButtonGroup, 
    QAbstractItemView, QListWidgetItem
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
        left_layout = QVBoxLayout()

        self.header_label = QLabel("Available Layers (Click to sort: A-Z)")
        self.header_label.setStyleSheet("QLabel { background-color : lightgray; padding: 5px; font-weight: bold; }")
        self.header_label.setCursor(Qt.PointingHandCursor)
        
        self.layers_list = QListWidget()
        self.layers_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        # Search box below the layers list
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search...")
        self.search_box.setClearButtonEnabled(True)

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
        self.remove_button = QPushButton()
        self.remove_button.setObjectName("delete_btn_unique_name")
        self.remove_button.setIcon(QIcon(os.path.join(self.plugin_dir, 'icons/bin.svg')))
        self.remove_button.setToolTip("Delete Item")
        btn_layout_row1.addWidget(self.add_button)
        btn_layout_row1.addWidget(self.remove_button)

        btn_layout_row2 = QHBoxLayout()
        self.save_state_button = QPushButton("Save Map State")
        self.load_state_button = QPushButton("Load Map State")
        self.clear_button = QPushButton("Clear Map")
        btn_layout_row2.addWidget(self.save_state_button)
        btn_layout_row2.addWidget(self.load_state_button)
        btn_layout_row2.addStretch()
        btn_layout_row2.addWidget(self.clear_button)

        self.added_layers_tree = QTreeWidget()
        self.added_layers_tree.setHeaderLabels(["Visibility", "Layer Name", "Transparency"])
        self.added_layers_tree.setColumnWidth(0, 60)
        self.added_layers_tree.setColumnWidth(1, 180)
        # Prevent scrollbars and allow proper resizing
        self.added_layers_tree.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.added_layers_tree.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.added_layers_tree.setMinimumHeight(100)

        reorder_layout = QHBoxLayout()
        self.move_up_btn = QPushButton("▲ Move Up")
        self.move_down_btn = QPushButton("▼ Move Down")
        reorder_layout.addWidget(self.move_up_btn)
        reorder_layout.addWidget(self.move_down_btn)

        self.zoom_btn = QPushButton("Zoom to Layer")

        tools_layout = QHBoxLayout()
        tools_layout.addWidget(self.zoom_btn)
        tools_layout.addStretch()

        self.base_layer_checkbox = QCheckBox("Show Base Layer")
        self.base_layer_checkbox.setChecked(True)

        mode_layout_left = QHBoxLayout()
        mode_layout_left.addWidget(self.base_layer_checkbox)
        mode_layout_left.addStretch()
        
        self.rb_light_mode = QRadioButton("Light Mode")
        self.rb_dark_mode = QRadioButton("Dark Mode")
        self.rb_light_mode.setChecked(not self.is_dark_theme)
        self.rb_dark_mode.setChecked(self.is_dark_theme)
        
        self.theme_mode_group = QButtonGroup(self)
        self.theme_mode_group.addButton(self.rb_light_mode)
        self.theme_mode_group.addButton(self.rb_dark_mode)
        
        mode_layout_left.addWidget(self.rb_light_mode)
        mode_layout_left.addWidget(self.rb_dark_mode)

        left_layout.addWidget(self.header_label)
        left_layout.addWidget(self.layers_list)
        left_layout.addWidget(self.search_box)
        left_layout.addLayout(type_layout)
        left_layout.addLayout(btn_layout_row1)
        left_layout.addLayout(btn_layout_row2)
        left_layout.addWidget(QLabel("Map Layers:"))
        left_layout.addWidget(self.added_layers_tree)
        left_layout.addLayout(reorder_layout)
        left_layout.addLayout(tools_layout)
        left_layout.addStretch()
        left_layout.addLayout(mode_layout_left)
        self.setLayout(left_layout)

    def connect_signals(self, main_dialog):
        """Connect all widget signals to the main dialog's slots."""
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
        
        self.base_layer_checkbox.stateChanged.connect(main_dialog.toggle_base_layer)
        self.theme_mode_group.buttonClicked.connect(main_dialog.on_theme_changed)

        self.save_state_button.clicked.connect(main_dialog._on_save_state)
        self.load_state_button.clicked.connect(main_dialog._on_load_state)

    def set_controls_enabled(self, enabled):
        """Enable or disable controls, typically during loading."""
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
