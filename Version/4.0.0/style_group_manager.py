"""
Style Group Manager Module
Creates and manages GeoServer Style Groups via REST API.
Used for rule-based layers where each rule is uploaded as a separate SLD
and grouped into a GeoServer LayerGroup acting as a style group.
"""

import requests
from qgis.core import Qgis


class StyleGroupManager:
    """
    Manages GeoServer Style Groups for rule-based layer uploads.
    Each rule SLD is registered individually, then a LayerGroup
    is created/updated to reference them all in correct draw order.
    """

    def __init__(self, main_instance):
        self.main = main_instance

    def create_or_update_style_group(self, url, workspace, layer_name,
                                     rule_style_names, username, password,
                                     cased_lines=False):
        """
        Create or update a GeoServer LayerGroup that references all per-rule styles
        in the correct draw order. The group name is '{layer_name}__group' or
        '{layer_name}_cased__group' if cased_lines=True.

        Args:
            url:               GeoServer base URL
            workspace:         Target workspace name
            layer_name:        Base layer name (must already exist in GeoServer)
            rule_style_names:  Ordered list of style names (first = bottom draw order)
            username:          GeoServer username
            password:          GeoServer password
            cased_lines:       If True, append '_cased' suffix to group name

        Returns:
            str: The style group name if successful, None on failure.
        """
        group_name = f"{layer_name}_cased__group" if cased_lines else f"{layer_name}__group"

        self.main.log_message(
            f"Creating Style Group '{group_name}' with {len(rule_style_names)} rule SLDs..."
        )

        # Build the layer group payload
        # Each entry references the SAME layer but with a different style
        # This is how GeoServer Style Groups work: one layer, N style overrides
        layers_list = []
        styles_list = []
        for style_name in rule_style_names:
            layers_list.append({
                "name": f"{workspace}:{layer_name}",
                "@type": "layer"
            })
            styles_list.append({
                "name": f"{workspace}:{style_name}"
            })

        payload = {
            "layerGroup": {
                "name": group_name,
                "mode": "SINGLE",
                "title": f"{layer_name} (Rule-Based Style Group)",
                "workspace": {
                    "name": workspace
                },
                "publishables": {
                    "published": layers_list
                },
                "styles": {
                    "style": styles_list
                }
            }
        }

        headers = {'Content-Type': 'application/json'}

        group_url = f"{url}/rest/workspaces/{workspace}/layergroups/{group_name}"

        # If the group already exists, DELETE it first.
        # GeoServer's PUT merges the published list instead of replacing it,
        # which causes duplicate / appended entries on re-upload.
        check_resp = requests.get(f"{group_url}.json", auth=(username, password), timeout=30)
        if check_resp.status_code == 200:
            del_resp = requests.delete(group_url, auth=(username, password), timeout=30)
            if del_resp.status_code in [200, 202, 204]:
                self.main.log_message(f"🗑 Deleted existing Style Group '{group_name}' before recreating")
            else:
                self.main.log_message(
                    f"Warning: could not delete existing Style Group '{group_name}' "
                    f"(status {del_resp.status_code}) — will attempt overwrite anyway",
                    level=Qgis.Warning
                )

        # Always POST a fresh group
        post_url = f"{url}/rest/workspaces/{workspace}/layergroups"
        resp = requests.post(post_url, auth=(username, password),
                             json=payload, headers=headers, timeout=30)
        if resp.status_code in [200, 201]:
            self.main.log_message(f"✓ Style Group '{group_name}' created successfully")
            return group_name
        else:
            self.main.log_message(
                f"Failed to create Style Group '{group_name}'. "
                f"Status: {resp.status_code}\n{resp.text}",
                level=Qgis.Critical
            )
            return None

    def assign_style_group_to_layer(self, url, workspace, layer_name,
                                    group_name, username, password):
        """
        Assign the style group as the default style for a GeoServer layer.

        Args:
            url:        GeoServer base URL
            workspace:  Target workspace name
            layer_name: GeoServer layer name
            group_name: Style group name to assign
            username:   GeoServer username
            password:   GeoServer password

        Returns:
            bool: True if assignment succeeded
        """
        layer_url = f"{url}/rest/layers/{workspace}:{layer_name}"
        payload = {
            "layer": {
                "defaultStyle": {
                    "name": f"{workspace}:{group_name}",
                    "workspace": workspace
                },
                "enabled": True
            }
        }
        resp = requests.put(
            layer_url,
            auth=(username, password),
            json=payload,
            headers={'Content-Type': 'application/json'}, timeout=30)
        if resp.status_code == 200:
            self.main.log_message(
                f"✓ Style Group '{group_name}' assigned to layer '{layer_name}'"
            )
            return True
        else:
            self.main.log_message(
                f"Failed to assign Style Group '{group_name}' to layer '{layer_name}'. "
                f"Status: {resp.status_code}\n{resp.text}",
                level=Qgis.Critical
            )
            return False
