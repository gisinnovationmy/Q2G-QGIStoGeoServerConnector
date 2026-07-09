"""
SLD ELSE Rule Handler Module
Detects and handles ELSE rules (rules without filters) in SLD exports.
Provides user options for how to handle these rules for GeoServer compatibility.
"""

from xml.etree import ElementTree as ET  # nosec B405
from .safe_xml import fromstring as safe_fromstring
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton,
    QButtonGroup, QGroupBox, QCheckBox
)
from qgis.PyQt.QtCore import QObject, pyqtSlot


# XML namespaces used in SLD
SLD_NS = {
    'sld': 'http://www.opengis.net/sld',
    'ogc': 'http://www.opengis.net/ogc',
    'se': 'http://www.opengis.net/se',
    'gml': 'http://www.opengis.net/gml',
}

# Register namespaces to preserve them in output
for prefix, uri in SLD_NS.items():
    ET.register_namespace(prefix, uri)
ET.register_namespace('', 'http://www.opengis.net/sld')


class ElseRuleHandlerDialog(QDialog):
    """Dialog to ask user how to handle ELSE rules in SLD."""

    # Return codes
    CONVERT_ELSE = 1
    USE_GRAY = 2
    SKIP_ELSE = 3
    CANCEL = 0

    def __init__(self, layer_name, else_rule_count, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ELSE Rule Detected")
        self.setMinimumWidth(450)
        self.result_action = self.CANCEL
        self.remember_choice = False

        self._setup_ui(layer_name, else_rule_count)

    def _setup_ui(self, layer_name, else_rule_count):
        layout = QVBoxLayout(self)

        # Warning message
        rule_text = "rule" if else_rule_count == 1 else "rules"
        msg = QLabel(
            f"<b>Layer '{layer_name}'</b> contains <b>{else_rule_count} ELSE {rule_text}</b> "
            f"(rules without filters).<br><br>"
            f"GeoServer interprets rules without filters as 'match ALL features', "
            f"which may cause incorrect rendering.<br><br>"
            f"<b>How would you like to handle this?</b>"
        )
        msg.setWordWrap(True)
        layout.addWidget(msg)

        # Options group
        options_group = QGroupBox("Select an option:")
        options_layout = QVBoxLayout(options_group)

        self.button_group = QButtonGroup(self)

        # Option 1: Convert ELSE
        self.radio_convert = QRadioButton(
            "Convert ELSE to explicit filter (recommended)\n"
            "Creates a NOT(other_filters) condition for accurate rendering"
        )
        self.radio_convert.setChecked(True)
        self.button_group.addButton(self.radio_convert, self.CONVERT_ELSE)
        options_layout.addWidget(self.radio_convert)

        # Option 2: Use gray fallback
        self.radio_gray = QRadioButton(
            "Replace with gray fallback style\n"
            "ELSE features will render as simple gray fill/stroke"
        )
        self.button_group.addButton(self.radio_gray, self.USE_GRAY)
        options_layout.addWidget(self.radio_gray)

        # Option 3: Skip ELSE rules
        self.radio_skip = QRadioButton(
            "Skip ELSE rules entirely\n"
            "ELSE features will not be styled (may be invisible)"
        )
        self.button_group.addButton(self.radio_skip, self.SKIP_ELSE)
        options_layout.addWidget(self.radio_skip)

        layout.addWidget(options_group)

        # Remember choice checkbox
        self.remember_checkbox = QCheckBox("Remember my choice for remaining layers in this upload")
        layout.addWidget(self.remember_checkbox)

        # Buttons
        button_layout = QHBoxLayout()

        self.btn_ok = QPushButton("Apply")
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self._on_ok)

        self.btn_cancel = QPushButton("Cancel Upload")
        self.btn_cancel.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.btn_cancel)
        button_layout.addWidget(self.btn_ok)

        layout.addLayout(button_layout)

    def _on_ok(self):
        self.result_action = self.button_group.checkedId()
        self.remember_choice = self.remember_checkbox.isChecked()
        self.accept()

    def get_result(self):
        """Returns (action, remember_choice) tuple."""
        return self.result_action, self.remember_choice


class SLDElseHandler(QObject):
    """Handles detection and conversion of ELSE rules in SLD content."""

    # Session-level remembered choice
    _remembered_action = None

    def __init__(self, main_instance=None):
        super().__init__()
        self.main = main_instance
        self._dialog_result = None
        self._dialog_layer_name = ""
        self._dialog_else_count = 0
        self._dialog_parent = None

    def reset_remembered_choice(self):
        """Reset the remembered choice (call at start of batch upload)."""
        SLDElseHandler._remembered_action = None

    @pyqtSlot()
    def _show_else_dialog(self):
        """Show the ELSE rule handling dialog (must be called on main thread)."""
        dialog = ElseRuleHandlerDialog(
            self._dialog_layer_name,
            self._dialog_else_count,
            self._dialog_parent
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._dialog_result = dialog.get_result()
        else:
            self._dialog_result = None

    def process_sld(self, sld_content, layer_name, parent_widget=None):
        """
        Process SLD content, detecting and handling ELSE rules.

        Args:
            sld_content: SLD XML string
            layer_name: Name of the layer (for dialog)
            parent_widget: Parent widget for dialog

        Returns:
            tuple: (processed_sld_content, success)
                   processed_sld_content is None if user cancelled
        """
        # First, detect and fix point pattern fills in polygon rules
        sld_content, pattern_fixed = self._fix_point_pattern_fills(sld_content, layer_name, parent_widget)

        # Detect ELSE rules
        else_rules = self._detect_else_rules(sld_content)

        if not else_rules:
            # No ELSE rules, return as-is
            return sld_content, True

        # Log detection and auto-apply the recommended conversion silently
        if self.main:
            self.main.log_message(
                f"Detected {len(else_rules)} ELSE rule(s) in '{layer_name}' — auto-converting to explicit NOT filters")

        action = ElseRuleHandlerDialog.CONVERT_ELSE

        # Apply the chosen action
        if action == ElseRuleHandlerDialog.CONVERT_ELSE:
            processed = self._convert_else_rules(sld_content)
            if self.main:
                self.main.log_message(f"Converted ELSE rules to explicit NOT filters for '{layer_name}'")
        elif action == ElseRuleHandlerDialog.USE_GRAY:
            processed = self._replace_with_gray(sld_content)
            if self.main:
                self.main.log_message(f"Replaced ELSE rules with gray fallback for '{layer_name}'")
        elif action == ElseRuleHandlerDialog.SKIP_ELSE:
            processed = self._remove_else_rules(sld_content)
            if self.main:
                self.main.log_message(f"Removed ELSE rules from '{layer_name}'")
        else:
            return None, False  # Cancelled

        return processed, True

    def _fix_point_pattern_fills(self, sld_content, layer_name, parent_widget=None):
        """
        Detect and fix Point Pattern Fill symbols exported for polygon layers.

        QGIS exports Point Pattern Fill as PointSymbolizer, which GeoServer
        doesn't render correctly for polygon geometries. This method detects
        such cases and replaces them with simple polygon fills.

        Returns:
            tuple: (processed_sld_content, was_fixed)
        """
        try:
            root = safe_fromstring(sld_content)
        except ET.ParseError:
            return sld_content, False

        # Find rules with PointSymbolizer but expecting polygon geometry
        # This is detected by: rule has PointSymbolizer AND rule name suggests polygon
        # OR rule has filter but only PointSymbolizer (no PolygonSymbolizer)

        sld_ns = 'http://www.opengis.net/sld'
        se_ns = 'http://www.opengis.net/se'

        rules = root.findall(f'.//{{{sld_ns}}}Rule')
        if not rules:
            rules = root.findall(f'.//{{{se_ns}}}Rule')
            sld_ns = se_ns

        rules_with_point_pattern = []

        for idx, rule in enumerate(rules):
            # Check if rule has PointSymbolizer
            point_syms = rule.findall(f'.//{{{sld_ns}}}PointSymbolizer')
            if not point_syms:
                point_syms = rule.findall(f'.//{{{se_ns}}}PointSymbolizer')

            # Check if rule has PolygonSymbolizer
            poly_syms = rule.findall(f'.//{{{sld_ns}}}PolygonSymbolizer')
            if not poly_syms:
                poly_syms = rule.findall(f'.//{{{se_ns}}}PolygonSymbolizer')

            # If rule has PointSymbolizer but NO PolygonSymbolizer, and has a filter,
            # it might be a point pattern fill that should be a polygon
            if point_syms and not poly_syms:
                # Check if this looks like a point pattern (multiple point symbolizers or specific patterns)
                # Also check if the rule has a filter (indicating it's meant to style specific features)
                has_filter = False
                for ns_uri in ['http://www.opengis.net/ogc', sld_ns, se_ns]:
                    if rule.find(f'{{{ns_uri}}}Filter') is not None:
                        has_filter = True
                        break

                # Get rule name for context
                rule_name_elem = rule.find(f'{{{sld_ns}}}Name')
                if rule_name_elem is None:
                    rule_name_elem = rule.find(f'{{{se_ns}}}Name')
                rule_name = rule_name_elem.text if rule_name_elem is not None and rule_name_elem.text else ""

                # Skip if it's clearly a point layer rule (has specific point-related names)
                point_keywords = ['worship', 'hut', 'camping', 'hotel', 'restaurant', 'shop', 'station']
                any(kw in rule_name.lower() for kw in point_keywords)

                # If it has no filter and no name, it might be an ELSE rule with point pattern
                if not has_filter and not rule_name:
                    # This is likely a point pattern fill for the "else" case
                    rules_with_point_pattern.append((idx, rule, point_syms))

        if not rules_with_point_pattern:
            return sld_content, False

        if self.main:
            self.main.log_message(
                f"Point Pattern Fill detected in '{layer_name}' — auto-replacing "
                f"with solid polygon fill for GeoServer compatibility"
            )

        # Fix the rules - replace PointSymbolizer with PolygonSymbolizer
        for idx, rule, point_syms in rules_with_point_pattern:
            # Try to extract color from the first PointSymbolizer
            fill_color = '#cccccc'  # Default gray
            stroke_color = '#999999'

            for point_sym in point_syms:
                # Look for fill color in Mark
                for ns in [sld_ns, se_ns]:
                    mark = point_sym.find(f'.//{{{ns}}}Mark')
                    if mark is not None:
                        fill_elem = mark.find(f'{{{ns}}}Fill')
                        if fill_elem is not None:
                            css_param = fill_elem.find(f'{{{ns}}}CssParameter[@name="fill"]')
                            if css_param is None:
                                css_param = fill_elem.find(f'{{{ns}}}SvgParameter[@name="fill"]')
                            if css_param is not None and css_param.text:
                                fill_color = css_param.text
                                break
                        stroke_elem = mark.find(f'{{{ns}}}Stroke')
                        if stroke_elem is not None:
                            css_param = stroke_elem.find(f'{{{ns}}}CssParameter[@name="stroke"]')
                            if css_param is None:
                                css_param = stroke_elem.find(f'{{{ns}}}SvgParameter[@name="stroke"]')
                            if css_param is not None and css_param.text:
                                stroke_color = css_param.text

            # Remove all PointSymbolizers from this rule
            for point_sym in point_syms:
                rule.remove(point_sym)

            # Add a PolygonSymbolizer with the extracted color
            poly_sym = ET.SubElement(rule, f'{{{sld_ns}}}PolygonSymbolizer')
            fill = ET.SubElement(poly_sym, f'{{{sld_ns}}}Fill')
            fill_param = ET.SubElement(fill, f'{{{sld_ns}}}CssParameter')
            fill_param.set('name', 'fill')
            fill_param.text = fill_color

            stroke = ET.SubElement(poly_sym, f'{{{sld_ns}}}Stroke')
            stroke_param = ET.SubElement(stroke, f'{{{sld_ns}}}CssParameter')
            stroke_param.set('name', 'stroke')
            stroke_param.text = stroke_color

        if self.main:
            self.main.log_message(
                f"Fixed {len(rules_with_point_pattern)} Point Pattern Fill rule(s) for '{layer_name}'")

        return ET.tostring(root, encoding='unicode', xml_declaration=True), True

    def _action_name(self, action):
        """Get human-readable name for action."""
        names = {
            ElseRuleHandlerDialog.CONVERT_ELSE: "Convert to explicit filter",
            ElseRuleHandlerDialog.USE_GRAY: "Use gray fallback",
            ElseRuleHandlerDialog.SKIP_ELSE: "Skip ELSE rules",
        }
        return names.get(action, "Unknown")

    def _detect_else_rules(self, sld_content):
        """
        Detect rules without filters (ELSE rules) in RULE-BASED styles only.

        Returns list of rule indices that are ELSE rules.

        IMPORTANT: Only flags ELSE rules if there are OTHER rules WITH filters.
        Single-symbol styles (one rule, no filter) are NOT considered ELSE rules.

        Excludes:
        - Rules with only TextSymbolizer (label rules)
        - Single-rule styles (not rule-based)
        """
        try:
            root = safe_fromstring(sld_content)
        except ET.ParseError:
            return []

        # Find all Rule elements (handle both SLD 1.0 and 1.1 namespaces)
        rules = root.findall('.//{http://www.opengis.net/sld}Rule')
        if not rules:
            rules = root.findall('.//{http://www.opengis.net/se}Rule')

        # Count rules with filters vs without filters
        rules_with_filter = 0
        rules_without_filter_indices = []

        for idx, rule in enumerate(rules):
            # Check if rule has a filter
            has_filter = False
            for ns_uri in ['http://www.opengis.net/ogc', 'http://www.opengis.net/sld', 'http://www.opengis.net/se']:
                if rule.find(f'{{{ns_uri}}}Filter') is not None:
                    has_filter = True
                    break

            if has_filter:
                rules_with_filter += 1
                continue

            # Check if it's a label-only rule (TextSymbolizer only)
            symbolizers = []
            for sym_type in [
                'PointSymbolizer', 'LineSymbolizer', 'PolygonSymbolizer',
                'RasterSymbolizer', 'TextSymbolizer'
            ]:
                for ns_uri in ['http://www.opengis.net/sld', 'http://www.opengis.net/se']:
                    symbolizers.extend(rule.findall(f'.//{{{ns_uri}}}{sym_type}'))

            # If only TextSymbolizer, skip (it's a label rule, not ELSE)
            text_only = all(
                sym.tag.endswith('TextSymbolizer')
                for sym in symbolizers
            ) if symbolizers else False

            if text_only:
                continue

            # This rule has no filter and has geometry symbolizers
            rules_without_filter_indices.append(idx)

        # CRITICAL: Only return ELSE rules if there are OTHER rules WITH filters
        # If no rules have filters, this is a simple single-symbol style, not rule-based
        if rules_with_filter == 0:
            return []  # Not a rule-based style, no ELSE rules to handle

        return rules_without_filter_indices

    def _collect_all_filters(self, sld_content):
        """Collect all filter elements from rules that have filters."""
        try:
            root = safe_fromstring(sld_content)
        except ET.ParseError:
            return []

        filters = []

        # Find all Rule elements
        rules = root.findall('.//{http://www.opengis.net/sld}Rule')
        if not rules:
            rules = root.findall('.//{http://www.opengis.net/se}Rule')

        for rule in rules:
            # Find filter in this rule
            filter_elem = None
            for ns_uri in ['http://www.opengis.net/ogc', 'http://www.opengis.net/sld', 'http://www.opengis.net/se']:
                filter_elem = rule.find(f'{{{ns_uri}}}Filter')
                if filter_elem is not None:
                    break

            if filter_elem is not None and len(filter_elem) > 0:
                # Clone the filter's child (the actual condition)
                filters.append(ET.tostring(filter_elem[0], encoding='unicode'))

        return filters

    def _convert_else_rules(self, sld_content):
        """Convert ELSE rules to explicit NOT(OR(other_filters)) filters."""
        # Collect all existing filters
        filter_strings = self._collect_all_filters(sld_content)

        if self.main:
            self.main.log_message(f"DEBUG: Found {len(filter_strings)} filter(s) to negate for NOT condition")

        if not filter_strings:
            # No other filters to negate - can't convert, use gray instead
            if self.main:
                self.main.log_message("DEBUG: No filters found, falling back to gray replacement")
            return self._replace_with_gray(sld_content)

        # Build the NOT(OR(...)) filter
        ogc_ns = 'http://www.opengis.net/ogc'

        if len(filter_strings) == 1:
            # Single filter - just NOT it
            not_filter = f'''<ogc:Filter xmlns:ogc="{ogc_ns}">
                <ogc:Not>
                    {filter_strings[0]}
                </ogc:Not>
            </ogc:Filter>'''
        else:
            # Multiple filters - NOT(OR(...))
            or_contents = '\n'.join(filter_strings)
            not_filter = f'''<ogc:Filter xmlns:ogc="{ogc_ns}">
                <ogc:Not>
                    <ogc:Or>
                        {or_contents}
                    </ogc:Or>
                </ogc:Not>
            </ogc:Filter>'''

        # Parse and process
        try:
            root = safe_fromstring(sld_content)
        except ET.ParseError:
            return sld_content

        # Find ELSE rules and inject the NOT filter
        rules = root.findall('.//{http://www.opengis.net/sld}Rule')
        sld_ns = 'http://www.opengis.net/sld'
        if not rules:
            rules = root.findall('.//{http://www.opengis.net/se}Rule')
            sld_ns = 'http://www.opengis.net/se'

        else_indices = self._detect_else_rules(sld_content)

        for idx in else_indices:
            if idx < len(rules):
                rule = rules[idx]
                # Parse the NOT filter
                not_filter_elem = safe_fromstring(not_filter)
                # Insert after Name/Title elements
                insert_pos = 0
                for i, child in enumerate(rule):
                    if child.tag.endswith(('Name', 'Title', 'Description')):
                        insert_pos = i + 1
                    else:
                        break
                rule.insert(insert_pos, not_filter_elem)

                # Fix empty symbolizers - QGIS sometimes exports empty Fill/Stroke
                self._fix_empty_symbolizers(rule, sld_ns)

        return ET.tostring(root, encoding='unicode', xml_declaration=True)

    def _fix_empty_symbolizers(self, rule, sld_ns):
        """Fix empty Fill/Stroke elements in symbolizers by adding default gray values.

        Handles both SLD 1.0 (sld namespace) and SLD 1.1 (se namespace for symbolizers).
        """
        # For SLD 1.1, symbolizers use SE namespace
        se_ns = 'http://www.opengis.net/se'

        # Try both namespaces for symbolizers
        namespaces_to_try = [sld_ns, se_ns] if sld_ns != se_ns else [sld_ns]

        for sym_ns in namespaces_to_try:
            # Find PolygonSymbolizer
            for poly_sym in rule.findall(f'.//{{{sym_ns}}}PolygonSymbolizer'):
                self._fix_fill_stroke(poly_sym, sym_ns)

            # Find LineSymbolizer
            for line_sym in rule.findall(f'.//{{{sym_ns}}}LineSymbolizer'):
                stroke = line_sym.find(f'{{{sym_ns}}}Stroke')
                if stroke is not None and len(stroke) == 0:
                    css_stroke = ET.SubElement(stroke, f'{{{sym_ns}}}SvgParameter')
                    css_stroke.set('name', 'stroke')
                    css_stroke.text = '#999999'
                    css_width = ET.SubElement(stroke, f'{{{sym_ns}}}SvgParameter')
                    css_width.set('name', 'stroke-width')
                    css_width.text = '1'

            # Find PointSymbolizer with empty Mark
            for point_sym in rule.findall(f'.//{{{sym_ns}}}PointSymbolizer'):
                mark = point_sym.find(f'.//{{{sym_ns}}}Mark')
                if mark is not None:
                    self._fix_fill_stroke(mark, sym_ns)

    def _fix_fill_stroke(self, parent_elem, ns):
        """Fix empty Fill and Stroke elements within a parent element."""
        # SLD 1.1 uses SvgParameter, SLD 1.0 uses CssParameter
        param_name = 'SvgParameter' if 'se' in ns else 'CssParameter'

        fill = parent_elem.find(f'{{{ns}}}Fill')
        if fill is not None and len(fill) == 0:
            css_fill = ET.SubElement(fill, f'{{{ns}}}{param_name}')
            css_fill.set('name', 'fill')
            css_fill.text = '#cccccc'
            css_opacity = ET.SubElement(fill, f'{{{ns}}}{param_name}')
            css_opacity.set('name', 'fill-opacity')
            css_opacity.text = '0.5'

        stroke = parent_elem.find(f'{{{ns}}}Stroke')
        if stroke is not None and len(stroke) == 0:
            css_stroke = ET.SubElement(stroke, f'{{{ns}}}{param_name}')
            css_stroke.set('name', 'stroke')
            css_stroke.text = '#999999'
            css_width = ET.SubElement(stroke, f'{{{ns}}}{param_name}')
            css_width.set('name', 'stroke-width')
            css_width.text = '1'

    def _replace_with_gray(self, sld_content):
        """Replace ELSE rules with simple gray fallback style using regex for reliability."""
        # Use regex-based replacement for more reliable results
        # This avoids ElementTree namespace serialization issues

        else_indices = self._detect_else_rules(sld_content)
        if not else_indices:
            return sld_content

        try:
            root = safe_fromstring(sld_content)
        except ET.ParseError:
            return sld_content

        # Find ELSE rules
        rules = root.findall('.//{http://www.opengis.net/sld}Rule')
        sld_ns = 'http://www.opengis.net/sld'
        ns_prefix = 'sld'
        if not rules:
            rules = root.findall('.//{http://www.opengis.net/se}Rule')
            sld_ns = 'http://www.opengis.net/se'
            ns_prefix = 'se'

        # Gray symbolizer templates - using full namespace URI format for ElementTree
        gray_polygon_xml = f'''<PolygonSymbolizer xmlns="{sld_ns}">
            <Fill>
                <CssParameter name="fill">#cccccc</CssParameter>
                <CssParameter name="fill-opacity">0.5</CssParameter>
            </Fill>
            <Stroke>
                <CssParameter name="stroke">#999999</CssParameter>
                <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
        </PolygonSymbolizer>'''

        gray_line_xml = f'''<LineSymbolizer xmlns="{sld_ns}">
            <Stroke>
                <CssParameter name="stroke">#999999</CssParameter>
                <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
        </LineSymbolizer>'''

        gray_point_xml = f'''<PointSymbolizer xmlns="{sld_ns}">
            <Graphic>
                <Mark>
                    <WellKnownName>circle</WellKnownName>
                    <Fill>
                        <CssParameter name="fill">#cccccc</CssParameter>
                    </Fill>
                    <Stroke>
                        <CssParameter name="stroke">#999999</CssParameter>
                    </Stroke>
                </Mark>
                <Size>6</Size>
            </Graphic>
        </PointSymbolizer>'''

        for idx in else_indices:
            if idx < len(rules):
                rule = rules[idx]

                # Detect geometry type from existing symbolizers
                has_polygon = rule.find(f'.//{{{sld_ns}}}PolygonSymbolizer') is not None
                has_line = rule.find(f'.//{{{sld_ns}}}LineSymbolizer') is not None
                has_point = rule.find(f'.//{{{sld_ns}}}PointSymbolizer') is not None

                # Remove existing symbolizers - need to find direct children, not descendants
                symbolizers_to_remove = []
                for child in list(rule):
                    if any(child.tag.endswith(sym_type)
                           for sym_type in ['PolygonSymbolizer', 'LineSymbolizer',
                                            'PointSymbolizer', 'RasterSymbolizer']):
                        symbolizers_to_remove.append(child)

                for sym in symbolizers_to_remove:
                    rule.remove(sym)

                # Add gray symbolizer based on detected type
                if has_polygon:
                    gray_elem = safe_fromstring(gray_polygon_xml)
                elif has_line:
                    gray_elem = safe_fromstring(gray_line_xml)
                elif has_point:
                    gray_elem = safe_fromstring(gray_point_xml)
                else:
                    # Default to polygon
                    gray_elem = safe_fromstring(gray_polygon_xml)

                rule.append(gray_elem)

        # Convert back to string
        result = ET.tostring(root, encoding='unicode', xml_declaration=True)

        # Fix namespace prefixes in output to match original SLD format
        # ElementTree may output default namespace, convert to prefixed form
        if ns_prefix == 'sld' and 'xmlns="http://www.opengis.net/sld"' in result:
            # Replace unprefixed elements with sld: prefixed ones for consistency
            pass
            # This is a simple fix - replace the default namespace declaration
            result = result.replace('xmlns="http://www.opengis.net/sld"', 'xmlns:sld="http://www.opengis.net/sld"')

        return result

    def _remove_else_rules(self, sld_content):
        """Remove ELSE rules entirely from SLD."""
        try:
            root = safe_fromstring(sld_content)
        except ET.ParseError:
            return sld_content

        # Find all FeatureTypeStyle elements (parent of Rules)
        fts_elements = root.findall('.//{http://www.opengis.net/sld}FeatureTypeStyle')
        if not fts_elements:
            fts_elements = root.findall('.//{http://www.opengis.net/se}FeatureTypeStyle')

        self._detect_else_rules(sld_content)

        # Find rules and their parents
        for fts in fts_elements:
            rules = fts.findall('{http://www.opengis.net/sld}Rule')
            if not rules:
                rules = fts.findall('{http://www.opengis.net/se}Rule')

            # Remove ELSE rules (iterate in reverse to maintain indices)
            rules_to_remove = []
            for idx, rule in enumerate(rules):
                # Re-check if this specific rule is an ELSE rule
                has_filter = False
                for ns_uri in ['http://www.opengis.net/ogc', 'http://www.opengis.net/sld', 'http://www.opengis.net/se']:
                    if rule.find(f'{{{ns_uri}}}Filter') is not None:
                        has_filter = True
                        break

                if not has_filter:
                    # Check if label-only
                    symbolizers = []
                    for sym_type in [
                        'PointSymbolizer', 'LineSymbolizer', 'PolygonSymbolizer',
                        'RasterSymbolizer', 'TextSymbolizer'
                    ]:
                        for ns_uri in ['http://www.opengis.net/sld', 'http://www.opengis.net/se']:
                            symbolizers.extend(rule.findall(f'.//{{{ns_uri}}}{sym_type}'))

                    text_only = all(sym.tag.endswith('TextSymbolizer') for sym in symbolizers) if symbolizers else False

                    if not text_only:
                        rules_to_remove.append(rule)

            for rule in rules_to_remove:
                fts.remove(rule)

        return ET.tostring(root, encoding='unicode', xml_declaration=True)
