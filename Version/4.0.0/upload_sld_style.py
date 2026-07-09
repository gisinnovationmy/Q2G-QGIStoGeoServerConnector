"""
Upload SLD Style Module
Handles SLD style upload and layer association in GeoServer.
Extracted from main.py for better code organization and maintainability.
"""

import requests
from qgis.core import Qgis

# Import ELSE handler
try:
    from .sld_else_handler import SLDElseHandler
except ImportError:
    from sld_else_handler import SLDElseHandler

# Import rule-based Path B modules
try:
    from .rule_based_sld_exporter import RuleBasedSLDExporter
    from .style_group_manager import StyleGroupManager
except ImportError:
    from rule_based_sld_exporter import RuleBasedSLDExporter
    from style_group_manager import StyleGroupManager


class SLDStyleUploader:
    """Handles SLD style upload and layer association in GeoServer."""

    def __init__(self, main_instance):
        """
        Initialize the SLD style uploader.

        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
        self.else_handler = SLDElseHandler(main_instance)
        self.rule_exporter = RuleBasedSLDExporter(main_instance)
        self.style_group_mgr = StyleGroupManager(main_instance)

    def reset_else_choice(self):
        """Reset the remembered ELSE handling choice (call at start of batch upload)."""
        self.else_handler.reset_remembered_choice()

    def upload_sld_style(self, layer, layer_name, workspace, url, username, password,
                         sld_content=None, handle_else=True, cased_lines=False):
        """
        Exports and uploads the SLD style for a given layer and assigns it.

        Args:
            layer: QGIS layer object
            layer_name: Name of the layer
            workspace: GeoServer workspace
            url: GeoServer URL
            username: GeoServer username
            password: GeoServer password
            sld_content: Optional pre-extracted SLD content
            handle_else: If True, detect and handle ELSE rules
            cased_lines: If True, apply GeoServer cased-line styling to rule-based line layers

        Returns:
            bool: True if SLD was counted (style already existed), False if not counted (new style created)
            None: If user cancelled the ELSE handling dialog
        """
        try:
            self.main.log_message(f"Uploading style for layer '{layer_name}'...")

            # PATH B: Rule-based layers — one SLD per rule + Style Group
            if sld_content is None and layer is not None and self.rule_exporter.is_rule_based(layer):
                return self._upload_rule_based_style(
                    layer, layer_name, workspace, url, username, password, cased_lines=cased_lines
                )

            # If no custom SLD content is provided, export it from the layer
            if sld_content is None:
                self.main.log_message("No custom SLD provided, exporting from layer style using SLD Window Manager.")
                # Pass show_dialogs=False since this may be called from a background thread
                sld_content = self.main.sld_window_manager._extract_sld_content(layer, show_dialogs=False)

            if not sld_content:
                self.main.log_message(
                    f"No SLD content available for layer '{layer_name}'. Skipping style upload.", level=Qgis.Warning)
                return False

            # Handle ELSE rules if enabled
            if handle_else:
                processed_sld, success = self.else_handler.process_sld(sld_content, layer_name, self.main)
                if not success:
                    self.main.log_message(f"ELSE rule handling cancelled for '{layer_name}'.", level=Qgis.Warning)
                    return None  # User cancelled
                sld_content = processed_sld

            style_name = layer_name

            # Detect SLD version - SLD 1.1.0 is used by QGIS for rule-based renderers
            is_sld_11 = 'version="1.1.0"' in sld_content or 'xmlns:se=' in sld_content
            if is_sld_11:
                self.main.log_message(f"Detected SLD 1.1.0 (rule-based) for '{layer_name}'")
            else:
                self.main.log_message(f"Detected SLD 1.0.0 for '{layer_name}'")

            sld_was_counted = False  # Track if we should count this SLD in batch report

            # Check if style exists in workspace
            check_style_url = f"{url}/rest/workspaces/{workspace}/styles/{style_name}.json"
            check_response = requests.get(check_style_url, auth=(username, password), timeout=30)

            if check_response.status_code == 200:
                # Style EXISTS - PUT to overwrite
                self.main.log_message(f"✓ Style '{style_name}' exists - using PUT to overwrite")
                success = self._put_sld_style(url, workspace, style_name, sld_content, is_sld_11, username, password)
                if not success:
                    return False
                sld_was_counted = True
            else:
                # Style DOESN'T EXIST - POST to create, then PUT to upload content
                self.main.log_message(f"✗ Style '{style_name}' does not exist - creating with POST")
                success = self._post_create_style(url, workspace, style_name, username, password)
                if not success:
                    return False
                self.main.log_message(f"📝 Style '{style_name}' created - uploading SLD content with PUT")
                success = self._put_sld_style(url, workspace, style_name, sld_content, is_sld_11, username, password)
                if not success:
                    return False
                sld_was_counted = True

            self.main.log_message(f"Style '{style_name}' uploaded successfully.")

            # Assign the style to the layer
            # Style name must be workspace-qualified for workspace-specific styles
            layer_update_url = f"{url}/rest/layers/{workspace}:{layer_name}"
            layer_payload = {
                "layer": {
                    "defaultStyle": {
                        "name": f"{workspace}:{style_name}"
                    },
                    "enabled": True
                }
            }
            headers_json = {'Content-Type': 'application/json'}

            update_response = requests.put(
                layer_update_url,
                auth=(username, password),
                json=layer_payload,
                headers=headers_json, timeout=30)

            if update_response.status_code == 200:
                self.main.log_message(f"Successfully assigned style '{style_name}' to layer '{layer_name}'.")
            else:
                self.main.log_message(
                    f"Failed to assign style '{style_name}' to layer '{layer_name}'. "
                    f"Status: {update_response.status_code}\n{update_response.text}",
                    level=Qgis.Critical)

            return sld_was_counted  # Return whether this SLD should be counted

        except Exception as e:
            self.main.log_message(
                f"An error occurred during SLD style upload for '{layer_name}': {e}", level=Qgis.Critical)
            return False

    def _upload_rule_based_style(self, layer, layer_name, workspace, url, username, password, cased_lines=False):
        """
        Path B: Upload one SLD per rule, then create a GeoServer Style Group.
        Only called for rule-based renderer layers.

        Args:
            cased_lines: If True, apply GeoServer cased-line styling to line rules

        Returns:
            bool: True on success, False on failure.
        """
        self.main.log_message(
            f"🗂 Rule-based layer '{layer_name}' → Path B: individual SLDs + Style Group"
        )
        if cased_lines:
            self.main.log_message("🛣 Cased line styling enabled for rule-based line layers")

        # Step 1: Export per-rule SLDs
        rule_slds = self.rule_exporter.export_rules(layer, layer_name, cased_lines=cased_lines)
        if not rule_slds:
            self.main.log_message(
                f"Could not extract rules from '{layer_name}' — falling back to standard SLD upload",
                level=Qgis.Warning
            )
            # Graceful fallback to standard single-SLD path
            sld_content = self.main.sld_window_manager._extract_sld_content(layer, show_dialogs=False)
            if not sld_content:
                return False
            is_sld_11 = 'version="1.1.0"' in sld_content or 'xmlns:se=' in sld_content
            success = self._post_create_style(url, workspace, layer_name, username, password)
            if success:
                success = self._put_sld_style(url, workspace, layer_name, sld_content, is_sld_11, username, password)
            return success

        # Step 1b: Delete all stale rule styles for this layer (prefix = layer_name__)
        # This prevents accumulation when rule names or sl-suffixes change between uploads.
        self._delete_stale_rule_styles(url, workspace, layer_name, username, password)

        # Step 2: Upload each rule SLD to GeoServer
        uploaded_style_names = []
        for rule in rule_slds:
            style_name = rule['style_name']
            sld_content = rule['sld_content']
            is_sld_11 = 'version="1.1.0"' in sld_content or 'xmlns:se=' in sld_content

            # Check if style already exists
            check_url = f"{url}/rest/workspaces/{workspace}/styles/{style_name}.json"
            check_resp = requests.get(check_url, auth=(username, password), timeout=30)

            if check_resp.status_code == 200:
                ok = self._put_sld_style(url, workspace, style_name, sld_content, is_sld_11, username, password)
            else:
                ok = self._post_create_style(url, workspace, style_name, username, password)
                if ok:
                    ok = self._put_sld_style(url, workspace, style_name, sld_content, is_sld_11, username, password)

            if ok:
                uploaded_style_names.append(style_name)
            else:
                self.main.log_message(
                    f"Failed to upload rule SLD '{style_name}' — aborting Style Group creation",
                    level=Qgis.Critical
                )
                return False

        self.main.log_message(
            f"✓ Uploaded {len(uploaded_style_names)} rule SLDs for '{layer_name}'"
        )
        # The exporter already returns styles in correct bottom → top draw order:
        # sl0 (bottom symbol layer / casing) for every rule first, then sl1, etc.
        # A GeoServer LayerGroup draws its first published entry at the bottom,
        # so we must NOT reverse the list here.
        self.main.log_message(
            f"Style group draw order (bottom → top): {', '.join(uploaded_style_names)}"
        )

        # Step 3: Create/update the Style Group
        group_name = self.style_group_mgr.create_or_update_style_group(
            url, workspace, layer_name, uploaded_style_names, username, password,
            cased_lines=cased_lines
        )
        if group_name is None:
            self.main.log_message(
                f"Style Group creation failed for '{layer_name}'",
                level=Qgis.Critical
            )
            return False

        # Step 4: Assign style group to layer
        self.style_group_mgr.assign_style_group_to_layer(
            url, workspace, layer_name, group_name, username, password
        )

        self.main.log_message(
            f"✅ Rule-based style complete: '{layer_name}' → "
            f"{len(uploaded_style_names)} SLDs → Style Group '{group_name}'"
        )
        return True

    def _delete_stale_rule_styles(self, url, workspace, layer_name, username, password):
        """
        Delete every workspace style whose name starts with '{layer_name}__'.
        Called before uploading a fresh set of per-rule SLDs so that stale
        styles from previous uploads (old rule names, old sl-suffixes) are
        removed and cannot accumulate in GeoServer.
        """
        prefix = f"{layer_name}__"
        list_url = f"{url}/rest/workspaces/{workspace}/styles.json"
        resp = requests.get(list_url, auth=(username, password), timeout=30)
        if resp.status_code != 200:
            self.main.log_message(
                f"Could not list styles for workspace '{workspace}' "
                f"(status {resp.status_code}) — skipping stale style cleanup",
                level=Qgis.Warning
            )
            return

        try:
            data = resp.json()
            styles = data.get('styles', {}).get('style', [])
            if isinstance(styles, dict):
                styles = [styles]
        except Exception:  # nosec B110
            return

        deleted = 0
        for style in styles:
            name = style.get('name', '')
            if name.startswith(prefix):
                del_url = f"{url}/rest/workspaces/{workspace}/styles/{name}?purge=true"
                del_resp = requests.delete(del_url, auth=(username, password), timeout=30)
                if del_resp.status_code in [200, 202, 204]:
                    deleted += 1
                else:
                    self.main.log_message(
                        f"Could not delete stale style '{name}' "
                        f"(status {del_resp.status_code})",
                        level=Qgis.Warning
                    )

        if deleted:
            self.main.log_message(
                f"🗑 Deleted {deleted} stale rule style(s) for '{layer_name}'"
            )

    def _post_create_style(self, url, workspace, style_name, username, password):
        """
        Create an empty style entry in GeoServer using POST (JSON metadata only, no SLD content).

        Args:
            url: GeoServer base URL
            workspace: Target workspace name
            style_name: Name for the new style
            username: GeoServer username
            password: GeoServer password

        Returns:
            bool: True if creation succeeded
        """
        post_url = f"{url}/rest/workspaces/{workspace}/styles"
        payload = {"style": {"name": style_name, "filename": f"{style_name}.sld"}}
        response = requests.post(
            post_url,
            auth=(username, password),
            json=payload,
            headers={'Content-Type': 'application/json'}, timeout=30)
        if response.status_code not in [200, 201]:
            self.main.log_message(
                f"Failed to create style '{style_name}'. Status: {response.status_code}\n{response.text}",
                level=Qgis.Critical
            )
            return False
        return True

    def _put_sld_style(self, url, workspace, style_name, sld_content, is_sld_11, username, password):
        """
        Upload SLD content to an existing style entry using PUT.
        For SLD 1.1.0 (rule-based): tries application/vnd.ogc.se+xml first,
        then silently falls back to SLD 1.0.0 conversion if GeoServer rejects it.

        Args:
            url: GeoServer base URL
            workspace: Target workspace name
            style_name: Name of the style to update
            sld_content: SLD XML content string
            is_sld_11: True if SLD 1.1.0 format (SE), False for SLD 1.0.0
            username: GeoServer username
            password: GeoServer password

        Returns:
            bool: True if upload succeeded
        """
        style_url = f"{url}/rest/workspaces/{workspace}/styles/{style_name}"

        if is_sld_11:
            # Attempt 1: Upload as SLD 1.1.0 with SE content type
            self.main.log_message(f"Attempting SLD 1.1.0 upload for '{style_name}'...")
            response = requests.put(
                style_url,
                auth=(username, password),
                headers={'Content-Type': 'application/vnd.ogc.se+xml'},
                data=sld_content.encode('utf-8'), timeout=30)
            if response.status_code in [200, 201]:
                self.main.log_message(f"✓ Uploaded '{style_name}' as SLD 1.1.0 (rule-based, native)")
                return True

            # Attempt 2: GeoServer rejected 1.1.0 — silently convert to 1.0.0 and retry
            self.main.log_message(
                f"SLD 1.1.0 rejected (status {response.status_code}) — converting to SLD 1.0.0 for '{style_name}'..."
            )
            try:
                sld_10_content = self.main.sld_converter.convert_se_to_sld_1_0(sld_content, style_name)
            except Exception as e:
                self.main.log_message(
                    f"SLD conversion failed for '{style_name}': {e}",
                    level=Qgis.Critical
                )
                return False

            response = requests.put(
                style_url,
                auth=(username, password),
                headers={'Content-Type': 'application/vnd.ogc.sld+xml'},
                data=sld_10_content.encode('utf-8'), timeout=30)
            if response.status_code in [200, 201]:
                self.main.log_message(f"✓ Uploaded '{style_name}' as SLD 1.0.0 (converted from rule-based)")
                return True

            self.main.log_message(
                f"Failed to upload SLD for '{style_name}' after fallback. "
                f"Status: {response.status_code}\n{response.text}",
                level=Qgis.Critical
            )
            return False

        else:
            # SLD 1.0.0 — upload directly
            response = requests.put(
                style_url,
                auth=(username, password),
                headers={'Content-Type': 'application/vnd.ogc.sld+xml'},
                data=sld_content.encode('utf-8'), timeout=30)
            if response.status_code not in [200, 201]:
                self.main.log_message(
                    f"Failed to upload SLD for '{style_name}'. Status: {response.status_code}\n{response.text}",
                    level=Qgis.Critical
                )
                return False
            return True
