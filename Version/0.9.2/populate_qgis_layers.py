"""
Populate QGIS Layers Module
Handles populating the QGIS layers tree widget with layers from the current project.
Extracted from main.py for better code organization and maintainability.
"""

from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer, Qgis, QgsLayerTreeGroup
from qgis.PyQt.QtWidgets import QTreeWidgetItem, QPushButton, QHeaderView
from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QIcon, QPixmap
from .layer_format_detector import get_layer_provider_info


class QGISLayersPopulator:
    """Handles populating the QGIS layers tree widget."""
    
    def __init__(self, main_instance):
        """
        Initialize the QGIS layers populator.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def populate_qgis_layers(self):
        """Populate the QGIS layers tree widget with layers from the current project."""
        # Save the current expand/collapse state before clearing
        expanded_groups = self._save_expanded_state()
        
        self._clear_tree_widget()
        self._setup_header_columns()
        
        root = QgsProject.instance().layerTreeRoot()
        # Recursively populate layers with group information
        self._populate_layers_with_groups(root, parent_group="")
        
        # Connect to layer tree changes to detect group name changes
        self._connect_layer_tree_signals(root)
        
        # Restore the expand/collapse state
        self._restore_expanded_state(expanded_groups)
    
    def _save_expanded_state(self):
        """
        Save which groups are currently expanded.
        
        Returns:
            set: Set of group names that are expanded
        """
        expanded_groups = set()
        for i in range(self.main.qgis_layers_tree.topLevelItemCount()):
            item = self.main.qgis_layers_tree.topLevelItem(i)
            self._collect_expanded_items(item, expanded_groups)
        return expanded_groups
    
    def _collect_expanded_items(self, item, expanded_groups, prefix=""):
        """
        Recursively collect expanded group names.
        
        Args:
            item: Current tree item
            expanded_groups: Set to store expanded group names
            prefix: Current path prefix for nested groups
        """
        if item and item.isExpanded():
            # Check if this is a group (has no layer data)
            if item.data(0, Qt.UserRole) is None and item.data(0, Qt.UserRole + 3):
                group_name = f"{prefix}/{item.text(0)}" if prefix else item.text(0)
                expanded_groups.add(group_name)
                # Recursively check children
                for i in range(item.childCount()):
                    child = item.child(i)
                    self._collect_expanded_items(child, expanded_groups, group_name)
    
    def _restore_expanded_state(self, expanded_groups):
        """
        Restore the expand/collapse state of groups.
        
        Args:
            expanded_groups: Set of group names that should be expanded
        """
        for i in range(self.main.qgis_layers_tree.topLevelItemCount()):
            item = self.main.qgis_layers_tree.topLevelItem(i)
            self._restore_item_state(item, expanded_groups, "")
    
    def _restore_item_state(self, item, expanded_groups, prefix=""):
        """
        Recursively restore expand/collapse state for items.
        
        Args:
            item: Current tree item
            expanded_groups: Set of group names that should be expanded
            prefix: Current path prefix for nested groups
        """
        if item:
            # Check if this is a group
            if item.data(0, Qt.UserRole) is None and item.data(0, Qt.UserRole + 3):
                group_name = f"{prefix}/{item.text(0)}" if prefix else item.text(0)
                # Restore expanded state
                if group_name in expanded_groups:
                    item.setExpanded(True)
                else:
                    item.setExpanded(False)
                # Recursively restore children
                for i in range(item.childCount()):
                    child = item.child(i)
                    self._restore_item_state(child, expanded_groups, group_name)

    def _populate_layers_with_groups(self, node, parent_item=None, parent_group=""):
        """
        Recursively populate layers, tracking group hierarchy with collapsible groups.
        
        Args:
            node: Layer tree node to traverse
            parent_item: Parent QTreeWidgetItem (None for root)
            parent_group: Name of the parent group (empty string for root level)
        """
        for child in node.children():
            if hasattr(child, 'layer') and child.layer():
                # This is a layer node
                layer = child.layer()
                if isinstance(layer, (QgsVectorLayer, QgsRasterLayer)):
                    if self._should_skip_layer(layer):
                        continue
                    
                    item = self._create_layer_item(layer, parent_group, parent_item)
                    self._setup_layer_buttons(item, layer)
                    self._connect_layer_signals(layer, item)
                    self._set_layer_format_info(item, layer)
            else:
                # This is a group node - create a collapsible group header
                group_name = child.name() if hasattr(child, 'name') else "Group"
                new_parent_group = f"{parent_group}/{group_name}" if parent_group else group_name
                
                # Create a group item
                group_item = self._create_group_item(group_name, parent_item, child, new_parent_group)
                
                # Recursively populate layers under this group
                self._populate_layers_with_groups(child, group_item, new_parent_group)
    
    def _clear_tree_widget(self):
        """Clear the tree widget and reset mappings."""
        self.main.qgis_layers_tree.clear()
        self.main.layer_to_item_map.clear()
        self.main.group_to_item_map.clear()
        if hasattr(self.main, 'group_node_to_item_map'):
            self.main.group_node_to_item_map.clear()
        self.main.select_all_qgis_layers_checkbox.setChecked(False)
    
    def _get_all_layers_recursive(self, node):
        """
        Recursively get all layers from the layer tree, including those in groups.
        
        Args:
            node: Layer tree node to traverse
            
        Returns:
            list: All layer objects found in the tree
        """
        layers = []
        for child in node.children():
            if hasattr(child, 'layer') and child.layer():
                # This is a layer node
                layers.append(child.layer())
            else:
                # This might be a group node, recurse into it
                layers.extend(self._get_all_layers_recursive(child))
        return layers
    
    def _get_all_layers_in_group(self, group_node):
        """
        Get all layer nodes (not layer objects) in a group recursively.
        
        Args:
            group_node: QGIS layer tree group node
            
        Returns:
            list: All layer tree nodes found in the group
        """
        layer_nodes = []
        for child in group_node.children():
            if hasattr(child, 'layer') and child.layer():
                # This is a layer node
                layer_nodes.append(child)
            else:
                # This is a nested group, recurse into it
                layer_nodes.extend(self._get_all_layers_in_group(child))
        return layer_nodes
    
    def _setup_header_columns(self):
        """Setup the header column resize modes."""
        header = self.main.qgis_layers_tree.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
    
    def _should_skip_layer(self, layer):
        """
        Check if a layer should be skipped from the tree widget.
        
        Args:
            layer: QGIS layer object
            
        Returns:
            bool: True if layer should be skipped, False otherwise
        """
        # Skip XYZ tile layers and other web-based tile services
        if isinstance(layer, QgsRasterLayer):
            provider_type = layer.providerType()
            if provider_type in ['wms', 'xyz', 'arcgismapserver', 'arcgisfeatureserver']:
                self.main.log_message(f"Skipping XYZ/Web tile layer: {layer.name()} (provider: {provider_type})")
                return True
        return False
    
    def _is_layer_visible(self, layer):
        """
        Check if a layer is visible in QGIS.
        
        Args:
            layer: QGIS layer object
            
        Returns:
            bool: True if layer is visible, False otherwise
        """
        try:
            # Get the layer tree node for this layer
            root = QgsProject.instance().layerTreeRoot()
            layer_node = root.findLayer(layer.id())
            
            if layer_node:
                # Check if the layer node is visible (checked in the layer tree)
                return layer_node.isVisible()
            
            # If no layer node found, default to False
            return False
        except Exception:
            # If any error occurs, default to False
            return False
    
    def _create_group_item(self, group_name, parent_item=None, group_node=None, full_path=""):
        """
        Create a collapsible group header item with checkbox for selecting all children.
        
        Args:
            group_name: Name of the group
            parent_item: Parent QTreeWidgetItem (None for root)
            group_node: QGIS layer tree group node
            full_path: Full path of the group (for nested groups)
            
        Returns:
            QTreeWidgetItem: Created group item
        """
        if parent_item is None:
            group_item = QTreeWidgetItem(self.main.qgis_layers_tree)
        else:
            group_item = QTreeWidgetItem(parent_item)
        
        # Set group item text without + sign (tree widget handles expand/collapse)
        group_item.setText(0, group_name)
        
        # Make group item bold to distinguish from layers
        font = group_item.font(0)
        font.setBold(True)
        group_item.setFont(0, font)
        
        # Make group item checkable to control all children
        group_item.setFlags(group_item.flags() | Qt.ItemIsUserCheckable)
        
        # Set checkbox state based on group's visibility in QGIS
        # Match the exact state of the group in QGIS layer tree
        if group_node:
            # Use the group node's own visibility state
            is_visible = group_node.itemVisibilityChecked()
            check_state = Qt.Checked if is_visible else Qt.Unchecked
        else:
            check_state = Qt.Unchecked
        group_item.setCheckState(0, check_state)
        
        # Mark as a group (no layer object, but is checkable)
        group_item.setData(0, Qt.UserRole, None)  # No layer object
        group_item.setData(0, Qt.UserRole + 3, True)  # Mark as group
        
        # Store group mapping for name change updates
        if full_path:
            self.main.group_to_item_map[full_path] = group_item
        
        # Also store mapping by group node object for quick lookup during rename
        if group_node:
            if not hasattr(self.main, 'group_node_to_item_map'):
                self.main.group_node_to_item_map = {}
            self.main.group_node_to_item_map[id(group_node)] = (group_item, full_path)
        
        # Connect to group name change signal
        if group_node and isinstance(group_node, QgsLayerTreeGroup):
            # Disconnect any existing connections first to avoid duplicate signal handlers
            try:
                group_node.nameChanged.disconnect()
            except (TypeError, RuntimeError):
                # No existing connections, that's fine
                pass
            
            # Connect with proper lambda to capture the group node, item, and path
            def on_name_changed(node=group_node, item=group_item, path=full_path):
                self._on_group_name_changed(node, item, path)
            
            group_node.nameChanged.connect(on_name_changed)
            self.main.log_message(f"✓ Connected nameChanged signal for group: '{group_name}' at path: '{full_path}'")
        
        # Make it expandable - always show the expand arrow
        group_item.setChildIndicatorPolicy(QTreeWidgetItem.ShowIndicator)
        
        return group_item
    
    def _on_group_name_changed(self, group_node, group_item, old_path):
        """
        Update group name in the tree without full refresh.
        
        Args:
            group_node: QGIS layer tree group node
            group_item: Tree widget item for the group (can be None, will look it up)
            old_path: Old full path of the group
        """
        try:
            if not group_node:
                self.main.log_message(f"❌ Invalid group node for rename")
                return
            
            new_name = group_node.name()
            
            # If group_item is None, look it up from the mapping
            if group_item is None:
                if hasattr(self.main, 'group_to_item_map') and old_path in self.main.group_to_item_map:
                    group_item = self.main.group_to_item_map[old_path]
                else:
                    self.main.log_message(f"❌ Could not find group item for path: {old_path}")
                    return
            
            # Check if the item is still valid (not deleted)
            try:
                # Try to access the item - if it's deleted, this will raise RuntimeError or AttributeError
                current_text = group_item.text(0)
            except (RuntimeError, AttributeError):
                # Item was deleted, skip update
                self.main.log_message(f"❌ Group item was deleted for: {old_path}")
                return
            
            self.main.log_message(f"🔄 Group name changed: '{current_text}' → '{new_name}'")
            
            # Update the item text
            group_item.setText(0, new_name)
            
            # Calculate new full path
            if '/' in old_path:
                parent_path = '/'.join(old_path.split('/')[:-1])
                new_path = f"{parent_path}/{new_name}"
            else:
                new_path = new_name
            
            # Update path-based mapping
            if hasattr(self.main, 'group_to_item_map') and old_path in self.main.group_to_item_map:
                del self.main.group_to_item_map[old_path]
                self.main.group_to_item_map[new_path] = group_item
            
            # Update node-based mapping
            if hasattr(self.main, 'group_node_to_item_map'):
                node_id = id(group_node)
                if node_id in self.main.group_node_to_item_map:
                    self.main.group_node_to_item_map[node_id] = (group_item, new_path)
            
            self.main.log_message(f"✓ Updated group mapping: '{old_path}' → '{new_path}'")
        except Exception as e:
            self.main.log_message(f"Error updating group name: {e}", level=Qgis.Warning)
    
    def _connect_layer_tree_signals(self, node, path=""):
        """
        Recursively connect to all group nodes' nameChanged signals.
        
        Args:
            node: Current layer tree node
            path: Full path of the current node
        """
        if isinstance(node, QgsLayerTreeGroup):
            # Connect this group's nameChanged signal
            try:
                node.nameChanged.disconnect()
            except (TypeError, RuntimeError):
                pass
            
            def on_name_changed(n=node, p=path):
                self._on_group_name_changed(n, None, p)
            
            node.nameChanged.connect(on_name_changed)
            
            # Recursively connect all child groups
            for child in node.children():
                child_path = f"{path}/{child.name()}" if path else child.name()
                self._connect_layer_tree_signals(child, child_path)

    def _create_layer_item(self, layer, parent_group="", parent_item=None):
        """
        Create a tree widget item for a layer.
        
        Args:
            layer: QGIS layer object
            parent_group: Name of the parent group (empty string for root level)
            parent_item: Parent QTreeWidgetItem (None for root)
            
        Returns:
            QTreeWidgetItem: Created tree widget item
        """
        if parent_item is None:
            item = QTreeWidgetItem(self.main.qgis_layers_tree)
        else:
            item = QTreeWidgetItem(parent_item)
        
        # Set item flags to be checkable
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        
        # Check if layer is visible in QGIS and set checkbox state accordingly
        is_visible = self._is_layer_visible(layer)
        check_state = Qt.Checked if is_visible else Qt.Unchecked
        item.setCheckState(0, check_state)
        
        # Store the layer object in the item's data role for later retrieval
        item.setData(0, Qt.UserRole, layer)
        item.setData(0, Qt.UserRole + 1, layer.id())  # Store layer ID as well
        
        # Display layer name
        item.setText(0, layer.name())
        
        # Store the group name for reference if in a group
        if parent_group:
            item.setData(0, Qt.UserRole + 2, parent_group)
        
        # Try to set layer icon from renderer
        self._set_layer_icon(item, layer)
        
        return item
    
    def _set_layer_icon(self, item, layer):
        """
        Set the layer icon from its renderer.
        
        Args:
            item: Tree widget item
            layer: QGIS layer object
        """
        try:
            renderer = layer.renderer() if hasattr(layer, 'renderer') else None
            if renderer:
                legend_symbol_items = renderer.legendSymbolItems()
                if legend_symbol_items:
                    symbol = legend_symbol_items[0].symbol()
                    if symbol:
                        img = symbol.asImage(QSize(16, 16))
                        if not img.isNull():
                            pixmap = QPixmap.fromImage(img)
                            if not pixmap.isNull():
                                icon = QIcon(pixmap)
                                item.setIcon(0, icon)
        except Exception:
            pass  # Silently ignore icon creation errors
    
    def _setup_layer_buttons(self, item, layer):
        """
        Setup buttons for the layer item.
        
        Args:
            item: Tree widget item
            layer: QGIS layer object
        """
        # Add extents button
        btn_extents = QPushButton("...")
        btn_extents.setToolTip("Show layer extents")
        btn_extents.setFocusPolicy(Qt.NoFocus)  # Prevent focus stealing
        btn_extents.clicked.connect(lambda checked, l=layer, i=item: self._on_button_clicked_preserve_selection(l, i, self.main._on_show_extents_clicked))
        self.main.qgis_layers_tree.setItemWidget(item, 2, btn_extents)

        # Add SLD button (applies to both vectors and rasters)
        btn_show = QPushButton("...")
        btn_show.setToolTip("Show SLD for this layer")
        btn_show.setFocusPolicy(Qt.NoFocus)  # Prevent focus stealing
        btn_show.clicked.connect(lambda checked, l=layer, i=item: self._on_button_clicked_preserve_selection(l, i, self.main._on_show_sld_clicked))
        self.main.qgis_layers_tree.setItemWidget(item, 3, btn_show)
        
        # Add Upload SLD button
        btn_upload_sld = QPushButton("Upload")
        btn_upload_sld.setToolTip("Upload a custom SLD file for this layer")
        btn_upload_sld.setFocusPolicy(Qt.NoFocus)  # Prevent focus stealing
        btn_upload_sld.clicked.connect(lambda checked, l=layer, i=item: self._on_button_clicked_preserve_selection(l, i, self.main._on_upload_sld_clicked))
        self.main.qgis_layers_tree.setItemWidget(item, 4, btn_upload_sld)
    
    def _on_button_clicked_preserve_selection(self, layer, item, callback_method):
        """
        Wrapper method that preserves tree selection when buttons are clicked.
        
        Args:
            layer: QGIS layer object
            item: Tree widget item
            callback_method: The actual method to call
        """
        # Store current selection before button action
        selected_items = self.main.qgis_layers_tree.selectedItems()
        
        # Call the actual button method
        callback_method(layer)
        
        # Restore selection after button action if it was lost
        current_selection = self.main.qgis_layers_tree.selectedItems()
        if not current_selection and selected_items:
            for selected_item in selected_items:
                selected_item.setSelected(True)
    
    def _connect_layer_signals(self, layer, item):
        """
        Connect layer signals and store mappings.
        
        Args:
            layer: QGIS layer object
            item: Tree widget item
        """
        # Connect to layer signals to update tree without full refresh
        # Use layer ID to look up the item from the mapping instead of capturing item directly
        if layer.id() not in self.main.connected_layers:
            # Connect name change signal
            layer.nameChanged.connect(lambda l=layer: self._on_layer_name_changed(l))
            
            # Connect renderer/style change signal
            if hasattr(layer, 'rendererChanged'):
                layer.rendererChanged.connect(lambda l=layer: self._on_layer_renderer_changed(l))
                self.main.log_message(f"✓ Connected rendererChanged signal for layer: {layer.name()}")
            
            self.main.connected_layers.add(layer.id())
            self.main.log_message(f"✓ Connected signals for layer: {layer.name()}")
        
        # Store mapping for fast lookup
        self.main.layer_to_item_map[layer.id()] = item
    
    def _on_layer_name_changed(self, layer):
        """
        Update layer name in the tree without full refresh.
        
        Args:
            layer: QGIS layer object
        """
        try:
            self.main.log_message(f"Layer name changed signal fired for: {layer.name()}")
            # Look up the item from the mapping using layer ID
            item = self.main.layer_to_item_map.get(layer.id())
            if item:
                # Check if the item is still valid (not deleted)
                try:
                    # Try to access the item - if it's deleted, this will raise RuntimeError
                    _ = item.text(0)
                except RuntimeError:
                    # Item was deleted, skip update
                    self.main.log_message(f"Layer item was deleted for: {layer.name()}")
                    return
                
                self.main.log_message(f"Updating layer name in tree: {layer.name()}")
                item.setText(0, layer.name())
                
                # Also update the layer icon when name changes (might indicate style change)
                try:
                    icon = self._create_layer_icon(layer)
                    if icon:
                        item.setIcon(0, icon)
                except:
                    pass
                    
            else:
                self.main.log_message(f"Layer item not found in mapping for: {layer.name()}")
        except Exception as e:
            self.main.log_message(f"Error updating layer name: {e}", level=Qgis.Warning)
    
    def _on_layer_renderer_changed(self, layer):
        """
        Update layer icon when renderer/style changes (targeted update, not full refresh).
        
        Args:
            layer: QGIS layer object whose renderer changed
        """
        try:
            self.main.log_message(f"🎨 Style changed for layer: {layer.name()}")
            
            # Use targeted icon update instead of full refresh for immediate response
            self.main._on_individual_layer_style_changed()
                    
        except Exception as e:
            pass  # Silently ignore errors
    
    def refresh_all_layer_icons(self):
        """
        Refresh all layer icons in the tree.
        Call this when you want to update layer style representations.
        """
        try:
            if not hasattr(self.main, 'layer_to_item_map'):
                return
            
            refreshed = 0
            for layer_id, item in self.main.layer_to_item_map.items():
                try:
                    layer = QgsProject.instance().mapLayer(layer_id)
                    if layer and item:
                        # Validate item
                        _ = item.text(0)
                        
                        # Update icon
                        icon = self._create_layer_icon(layer)
                        if icon:
                            item.setIcon(0, icon)
                            refreshed += 1
                except (RuntimeError, AttributeError):
                    continue
            
            if refreshed > 0:
                self.main.log_message(f"✓ Refreshed {refreshed} layer icons")
                self.main.qgis_layers_tree.update()
                
        except Exception as e:
            self.main.log_message(f"Error refreshing layer icons: {e}", level=Qgis.Warning)
    
    def _set_layer_format_info(self, item, layer):
        """
        Set the layer format information in the tree widget.
        
        Args:
            item: Tree widget item
            layer: QGIS layer object
        """
        # Set format in the tree widget for each layer
        format_info = get_layer_provider_info(layer)
        item.setText(1, format_info.get('native_format', 'Unknown'))
