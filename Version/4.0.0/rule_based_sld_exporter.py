"""
Rule-Based SLD Exporter Module
Extracts individual rules from a QGIS rule-based renderer and generates
one standalone GeoServer-compatible SLD per rule.
Only activated for layers with rule-based or merged feature renderer symbology.
"""

import re
import xml.etree.ElementTree as ET  # nosec B405
from .safe_xml import fromstring as safe_fromstring
from qgis.core import (
    Qgis, QgsVectorLayer, QgsRuleBasedRenderer,
    QgsWkbTypes
)


# SLD/SE namespaces
NS_SLD = 'http://www.opengis.net/sld'
NS_SE = 'http://www.opengis.net/se'
NS_OGC = 'http://www.opengis.net/ogc'
NS_XSI = 'http://www.w3.org/2001/XMLSchema-instance'


def _sanitize_name(name):
    """Convert a rule label into a safe SLD/GeoServer style name."""
    name = name.strip()
    name = re.sub(r'[^a-zA-Z0-9_\-]', '_', name)
    name = re.sub(r'_+', '_', name)
    return name.lower().strip('_') or 'rule'


class RuleBasedSLDExporter:
    """
    Extracts each rule from a QgsRuleBasedRenderer and generates
    one standalone SLD 1.0.0 file per rule with correct OGC filters,
    symbolizers, and scale denominators.
    """

    def __init__(self, main_instance):
        self.main = main_instance

    def is_rule_based(self, layer):
        """Return True only if layer uses a rule-based or merged feature renderer."""
        if not isinstance(layer, QgsVectorLayer):
            return False
        renderer = layer.renderer()
        if renderer is None:
            return False
        return renderer.type() in ('RuleRenderer', 'ruleRenderer',
                                   'mergedFeatureRenderer', 'MergedFeatureRenderer')

    def _get_rule_based_renderer(self, layer):
        """
        Return a genuine QgsRuleBasedRenderer for the layer.
        If the layer's renderer is not already rule-based (e.g. merged feature
        renderer or categorized), attempt to convert it. Returns None on failure.
        """
        renderer = layer.renderer()
        if renderer is None:
            return None

        # Already a rule-based renderer with rootRule support
        if isinstance(renderer, QgsRuleBasedRenderer):
            return renderer

        # Some renderers (merged feature) wrap an embedded renderer
        if hasattr(renderer, 'embeddedRenderer'):
            try:
                embedded = renderer.embeddedRenderer()
                if isinstance(embedded, QgsRuleBasedRenderer):
                    return embedded
            except Exception:  # nosec B110
                pass

        # Attempt conversion from any other renderer type
        try:
            converted = QgsRuleBasedRenderer.convertFromRenderer(renderer)
            if converted is not None:
                return converted
        except Exception as e:
            self.main.log_message(
                f"Could not convert renderer to rule-based: {e}",
                level=Qgis.Warning
            )
        return None

    def export_rules(self, layer, layer_name, cased_lines=False):
        """
        Flatten all leaf rules × symbol layers into individual SLDs ordered so
        GeoServer draws them in the correct bottom-to-top pass order:

            Pass 0 (sl_idx=0): every rule's bottom-most symbol layer
            Pass 1 (sl_idx=1): every rule's next symbol layer
            ...
            Pass N (sl_idx=N): every rule's top-most symbol layer

        This unified algorithm handles both single-layer (S) and multi-layer (M)
        symbols — S is simply the special case where N=1.

        For S layers with cased_lines=True, _apply_cased_lines() is called to
        split each stroke into border + fill passes. For M layers the flattening
        already achieves the casing effect naturally, so cased_lines is a no-op.

        Args:
            layer:       QgsVectorLayer
            layer_name:  sanitized layer name (prefix for style names)
            cased_lines: If True, apply cased-line post-processing to S-mode line rules

        Returns:
            list of dict: [{'style_name': str, 'sld_content': str, 'rule_label': str}, ...]
            Empty list on failure.
        """
        renderer = self._get_rule_based_renderer(layer)
        if renderer is None:
            self.main.log_message(
                f"Renderer for '{layer_name}' is not rule-based and could not be converted",
                level=Qgis.Warning
            )
            return []

        leaf_rules = self._collect_leaf_rules(renderer.rootRule())
        if not leaf_rules:
            self.main.log_message(f"No leaf rules found in '{layer_name}'", level=Qgis.Warning)
            return []

        clone_layer = self._clone_layer_for_export(layer, layer_name)
        if clone_layer is None:
            self.main.log_message(
                f"Could not clone layer '{layer_name}' for rule-based SLD export",
                level=Qgis.Critical
            )
            return []

        # Determine the maximum number of symbol layers across all rules
        max_sl = max(
            (rule.symbol().symbolLayerCount() for rule in leaf_rules if rule.symbol()),
            default=1
        )
        is_multi = max_sl > 1

        self.main.log_message(
            f"Rule-based layer '{layer_name}': {len(leaf_rules)} rule(s), "
            f"{max_sl} symbol layer(s) → "
            f"{'M (multi-layer flatten)' if is_multi else 'S (single-layer)'} mode"
        )

        # Pre-compute stable, unique base names for every rule (BUG 3 fix: prefix with index)
        rule_entries = []
        for idx, rule in enumerate(leaf_rules):
            label = rule.label() or f"rule_{idx}"
            base = f"{idx:03d}_{_sanitize_name(label)}"
            rule_entries.append((rule, label, base))

        results = []

        # ═══════════════════════════════════════════════════════════════════════
        # BUG 1 FIX — Branching logic based on cased_lines flag
        # ═══════════════════════════════════════════════════════════════════════

        if not cased_lines and not is_multi:
            # ─────────────────────────────────────────────────────────────────
            # MODE: cased_lines = FALSE, single-layer symbols (S-mode)
            # Export ONE SLD per rule with all symbol layers intact.
            # No sl0/sl1 splitting, no casing post-processing.
            # Style names: layername__rulename (NO _cased suffix)
            # ─────────────────────────────────────────────────────────────────
            self.main.log_message(
                f"  Mode: Standard (S-mode, no casing) — exporting {len(rule_entries)} combined SLD(s)"
            )
            for rule, label, base in rule_entries:
                style_name = f"{layer_name}__{base}"
                sld_content = self._export_rule_via_qgis(clone_layer, rule)

                if sld_content:
                    results.append({
                        'style_name': style_name,
                        'sld_content': sld_content,
                        'rule_label': label,
                    })
                    self.main.log_message(f"  ✓ '{label}' → style '{style_name}'")
                else:
                    self.main.log_message(
                        f"  ⚠ Could not generate SLD for '{label}' — skipping",
                        level=Qgis.Warning
                    )

        elif not cased_lines and is_multi:
            # ─────────────────────────────────────────────────────────────────
            # MODE: cased_lines = FALSE, multi-layer symbols (M-mode)
            # MUST flatten into sl0/sl1 for LayerGroup to work (GeoServer
            # limitation: LayerGroup with same layer + different styles only
            # works when each style has a single symbolizer).
            # Style names: layername__rulename__sl0, layername__rulename__sl1
            # ─────────────────────────────────────────────────────────────────
            self.main.log_message(
                f"  Mode: Standard (M-mode, flattened) — exporting {len(rule_entries)} rules × {max_sl} symbol layers"
            )
            # Outer loop: symbol layer index (draw pass, bottom → top)
            for sl_idx in range(max_sl):
                for rule, label, base in rule_entries:
                    symbol = rule.symbol()
                    if symbol is None or symbol.symbolLayerCount() <= sl_idx:
                        continue

                    style_name = f"{layer_name}__{base}__sl{sl_idx}"
                    sld_content = self._export_symbol_layer_sld(
                        clone_layer, rule, sl_idx, style_name
                    )

                    if sld_content:
                        results.append({
                            'style_name': style_name,
                            'sld_content': sld_content,
                            'rule_label': f"{label} (sl{sl_idx})",
                        })
                        self.main.log_message(f"  ✓ sl{sl_idx} / '{label}' → style '{style_name}'")
                    else:
                        self.main.log_message(
                            f"  ⚠ Could not generate SLD for '{label}' sl{sl_idx} — skipping",
                            level=Qgis.Warning
                        )

        elif cased_lines and not is_multi:
            # ─────────────────────────────────────────────────────────────────
            # MODE: cased_lines = TRUE, single-layer symbols (S-mode)
            # Export ONE SLD per rule, then apply _apply_cased_lines() to split
            # each LineSymbolizer into border + fill FeatureTypeStyles.
            # Style names: layername__rulename_cased
            # ─────────────────────────────────────────────────────────────────
            self.main.log_message(
                f"  Mode: Cased (S-mode) — exporting {len(rule_entries)} SLD(s) + casing post-process"
            )
            for rule, label, base in rule_entries:
                style_name = f"{layer_name}__{base}_cased"
                sld_content = self._export_rule_via_qgis(clone_layer, rule)

                if sld_content:
                    sld_content = self._apply_cased_lines(sld_content, style_name, label)
                    line_count = sld_content.count('LineSymbolizer')
                    self.main.log_message(
                        f"    [cased-lines] '{label}': {line_count} LineSymbolizer(s) after split"
                    )
                    results.append({
                        'style_name': style_name,
                        'sld_content': sld_content,
                        'rule_label': label,
                    })
                    self.main.log_message(f"  ✓ '{label}' → style '{style_name}'")
                else:
                    self.main.log_message(
                        f"  ⚠ Could not generate SLD for '{label}' — skipping",
                        level=Qgis.Warning
                    )

        else:
            # ─────────────────────────────────────────────────────────────────
            # MODE: cased_lines = TRUE, multi-layer symbols (M-mode)
            # Flatten into separate SLDs per (rule × symbol_layer) to achieve
            # global draw-pass ordering: all sl0 first, then all sl1, etc.
            # Style names: layername__rulename_cased__sl0, layername__rulename_cased__sl1
            # ─────────────────────────────────────────────────────────────────
            self.main.log_message(
                f"  Mode: Cased (M-mode, flattened) — exporting {len(rule_entries)} rules × {max_sl} symbol layers"
            )
            # Outer loop: symbol layer index (draw pass, bottom → top)
            for sl_idx in range(max_sl):
                for rule, label, base in rule_entries:
                    symbol = rule.symbol()
                    if symbol is None or symbol.symbolLayerCount() <= sl_idx:
                        continue

                    style_name = f"{layer_name}__{base}_cased__sl{sl_idx}"
                    sld_content = self._export_symbol_layer_sld(
                        clone_layer, rule, sl_idx, style_name
                    )

                    if sld_content:
                        results.append({
                            'style_name': style_name,
                            'sld_content': sld_content,
                            'rule_label': f"{label} (sl{sl_idx})",
                        })
                        self.main.log_message(f"  ✓ sl{sl_idx} / '{label}' → style '{style_name}'")
                    else:
                        self.main.log_message(
                            f"  ⚠ Could not generate SLD for '{label}' sl{sl_idx} — skipping",
                            level=Qgis.Warning
                        )

        return results

    def _export_symbol_layer_sld(self, clone_layer, rule, sl_idx, style_name):
        """
        Generate a valid SLD for one (rule, symbol_layer_index) pair.

        Strategy: export the full-symbol SLD for this rule via QGIS (all symbol
        layers present), then post-process the XML to keep only the symbolizer
        at position sl_idx and remove all others.  This bypasses unreliable
        QGIS Python API calls (takeSymbolLayer / deleteSymbolLayer) entirely.

        Args:
            clone_layer: Cloned QgsVectorLayer for safe export
            rule:        QgsRuleBasedRenderer.Rule to export
            sl_idx:      Symbol layer index (0 = bottom / casing)
            style_name:  GeoServer style name (unused here, kept for signature)

        Returns:
            str: SLD XML with only the sl_idx symbolizer, or None on failure.
        """
        try:
            # ── Step 1: export the full-symbol SLD for this single rule ──────────
            single_root = QgsRuleBasedRenderer.Rule(None)
            single_root.appendChild(rule.clone())
            clone_layer.setRenderer(QgsRuleBasedRenderer(single_root))

            full_sld = self.main.sld_window_manager._extract_sld_content(
                clone_layer, show_dialogs=False
            )
            if not full_sld:
                return None

            # ── Step 2: XML post-process — keep only symbolizer at sl_idx ────────
            return self._keep_only_symbolizer(full_sld, sl_idx, rule.label())

        except Exception as e:
            self.main.log_message(
                f"Error exporting sl{sl_idx} for rule '{rule.label()}': {e}",
                level=Qgis.Warning
            )
            return None

    # Symbolizer tag suffixes recognised across SLD 1.0 and SE 1.1 namespaces
    _SYMBOLIZER_TAGS = (
        'LineSymbolizer', 'PolygonSymbolizer', 'PointSymbolizer',
        'TextSymbolizer', 'RasterSymbolizer',
    )

    def _keep_only_symbolizer(self, sld_content, sl_idx, rule_label):
        """
        Parse the SLD XML, find all symbolizer elements across every Rule,
        and remove every symbolizer except the one at position sl_idx.
        Returns the modified SLD string, or the original if parsing fails.
        """
        try:
            root = safe_fromstring(sld_content)

            for rule_elem in root.iter():
                # BUG 2 FIX: namespace-safe tag detection
                if rule_elem.tag.split('}')[-1] != 'Rule':
                    continue

                # Collect all symbolizer children IN ORDER (namespace-safe)
                symbolizers = [
                    child for child in list(rule_elem)
                    if child.tag.split('}')[-1] in self._SYMBOLIZER_TAGS
                ]

                total = len(symbolizers)
                if total == 0:
                    continue

                # Clamp sl_idx to available range for rules with fewer layers
                target = min(sl_idx, total - 1)

                # Remove all symbolizers except the target
                for i, sym in enumerate(symbolizers):
                    if i != target:
                        rule_elem.remove(sym)

                kept_tag = symbolizers[target].tag.split('}')[-1]
                self.main.log_message(
                    f"    [sl{sl_idx}] '{rule_label}': "
                    f"kept symbolizer {target + 1}/{total} ({kept_tag})"
                )

            return ET.tostring(root, encoding='unicode', xml_declaration=True)

        except Exception as e:
            self.main.log_message(
                f"XML symbolizer isolation failed for '{rule_label}' sl{sl_idx}: {e}",
                level=Qgis.Warning
            )
            return sld_content

    def _export_rule_via_qgis(self, layer, rule):
        """
        Generate a valid SLD for a single rule by temporarily assigning a
        single-rule QgsRuleBasedRenderer to the layer and using QGIS's native
        SLD export pipeline (the same one used for standard single-SLD uploads).
        The layer passed here is a clone, not the live QGIS layer.

        Returns:
            str: SLD XML content, or None on failure.
        """
        try:
            single_root = QgsRuleBasedRenderer.Rule(None)
            single_root.appendChild(rule.clone())
            single_renderer = QgsRuleBasedRenderer(single_root)

            layer.setRenderer(single_renderer)
            # No triggerRepaint needed on the clone, and it avoids canvas recursion.

            return self.main.sld_window_manager._extract_sld_content(
                layer, show_dialogs=False
            )
        except Exception as e:
            self.main.log_message(
                f"Error exporting rule '{rule.label()}' via QGIS: {e}",
                level=Qgis.Warning
            )
            return None

    def _clone_layer_for_export(self, layer, layer_name):
        """
        Create a minimal in-memory clone of the layer for safe SLD export.
        The clone preserves the original renderer and symbol settings but has no
        features, so setting renderers on it will not trigger canvas repaints
        or crash the live QGIS session.

        Returns:
            QgsVectorLayer: A memory layer with the same structure/renderer,
            or None if cloning failed.
        """
        try:
            geometry_type = QgsWkbTypes.displayString(layer.wkbType())
            uri = f"{geometry_type}?crs={layer.crs().authid()}&field=id:integer"
            clone = QgsVectorLayer(uri, f"{layer_name}_export_clone", "memory")
            if not clone.isValid():
                return None

            # Copy fields (BUG 5 FIX: use dataProvider().addAttributes())
            fields_to_add = [f for f in layer.fields() if f.name() != 'id']
            if fields_to_add:
                clone.dataProvider().addAttributes(fields_to_add)
            clone.updateFields()

            # Copy renderer and symbol settings
            if layer.renderer():
                clone.setRenderer(layer.renderer().clone())

            return clone
        except Exception as e:
            self.main.log_message(
                f"Error cloning layer '{layer_name}' for export: {e}",
                level=Qgis.Warning
            )
            return None

    def _apply_cased_lines(self, sld_content, style_name, rule_label):
        """
        Post-process a rule SLD so line rules are rendered as GeoServer cased lines:
        the widest stroke is drawn first (border), followed by the narrower
        stroke (fill), each in its own FeatureTypeStyle with stroke-linecap=round.
        This follows the GeoServer SLD cookbook "Line with border" pattern.

        Returns:
            str: Modified SLD XML, or original on failure.
        """
        try:
            root = safe_fromstring(sld_content)

            # Build a parent map because stdlib ElementTree has no getparent()
            parent_map = {child: parent for parent in root.iter() for child in parent}

            # Find all LineSymbolizers in all Rules (BUG 2 FIX: namespace-safe)
            line_symbolizers = []
            for rule in root.iter():
                if rule.tag.split('}')[-1] == 'Rule':
                    for sym in list(rule):
                        if sym.tag.split('}')[-1] == 'LineSymbolizer':
                            line_symbolizers.append((rule, sym))

            if not line_symbolizers:
                # Not a line rule — nothing to do
                self.main.log_message(
                    f"    [cased-lines] '{rule_label}': NO LineSymbolizers found — skipping casing",
                    level=Qgis.Warning
                )
                return sld_content

            # Extract stroke widths so we can order border → fill
            def get_width(stroke_elem):
                for css in stroke_elem.iter():
                    if css.tag.split('}')[-1] == 'CssParameter':
                        name = css.get('name', '')
                        if name == 'stroke-width':
                            try:
                                return float(css.text or 0)
                            except (ValueError, TypeError):
                                return 0
                return 0

            # For each Rule, separate its LineSymbolizers and sort by width descending
            rule_symbolizers = {}
            for rule, sym in line_symbolizers:
                rid = id(rule)
                rule_symbolizers.setdefault(rid, []).append((rule, sym))

            # Build new FeatureTypeStyle structure per Rule
            for rid, pairs in rule_symbolizers.items():
                rule = pairs[0][0]
                fts_parent = parent_map.get(rule)
                if fts_parent is None or fts_parent.tag.split('}')[-1] != 'FeatureTypeStyle':
                    continue

                # Remove the original LineSymbolizers from this Rule
                for _, sym in pairs:
                    rule.remove(sym)

                # Sort border first (widest), fill last (narrowest)
                def _width_of(pair):
                    _, sym = pair
                    for stroke in sym.iter():
                        if stroke.tag.split('}')[-1] == 'Stroke':
                            return get_width(stroke)
                    return 0
                sorted_pairs = sorted(pairs, key=_width_of, reverse=True)

                # Build new FeatureTypeStyles for each stroke, replicating the Rule
                new_fts_list = []
                for border_idx, (_, sym) in enumerate(sorted_pairs):
                    # Add stroke-linecap=round for proper intersections
                    stroke_elem = None
                    for child in sym.iter():
                        if child.tag.split('}')[-1] == 'Stroke':
                            stroke_elem = child
                            break
                    if stroke_elem is not None:
                        has_linecap = any(
                            css.get('name') == 'stroke-linecap'
                            for css in stroke_elem.iter()
                            if css.tag.split('}')[-1] == 'CssParameter'
                        )
                        if not has_linecap:
                            linecap = ET.Element('CssParameter', {'name': 'stroke-linecap'})
                            linecap.text = 'round'
                            stroke_elem.append(linecap)

                    # New FeatureTypeStyle containing a clone of the rule with just this symbolizer
                    new_fts = ET.Element('FeatureTypeStyle')
                    new_rule = ET.SubElement(new_fts, 'Rule')
                    # BUG 4 FIX: Preserve ALL non-LineSymbolizer children (labels, markers, etc.)
                    for child in list(rule):
                        if child.tag.split('}')[-1] != 'LineSymbolizer':
                            new_rule.append(self._deep_copy(child))
                    new_rule.append(self._deep_copy(sym))
                    new_fts_list.append(new_fts)

                # Replace the original FeatureTypeStyle with the new ones in correct order.
                # Insert in reverse so the first in the list ends up first in the document.
                fts_parent_parent = parent_map.get(fts_parent)
                if fts_parent_parent is not None:
                    idx = list(fts_parent_parent).index(fts_parent)
                    for new_fts in reversed(new_fts_list):
                        fts_parent_parent.insert(idx, new_fts)
                    fts_parent_parent.remove(fts_parent)
                    # Refresh parent map after structural change
                    parent_map = {child: parent for parent in root.iter() for child in parent}
                    self.main.log_message(
                        f"    [cased-lines] '{rule_label}': Created {len(new_fts_list)} FeatureTypeStyle(s) "
                        f"(border → fill)"
                    )

            return ET.tostring(root, encoding='unicode', xml_declaration=True)

        except Exception as e:
            self.main.log_message(
                f"Cased-line post-processing failed for '{rule_label}': {e}",
                level=Qgis.Warning
            )
            return sld_content

    def _deep_copy(self, elem):
        """Return a deep copy of an ElementTree element."""
        copy = ET.Element(elem.tag, elem.attrib)
        copy.text = elem.text
        copy.tail = elem.tail
        for child in elem:
            copy.append(self._deep_copy(child))
        return copy

    def _collect_leaf_rules(self, root_rule):
        """Recursively collect all active leaf rules (those with symbols)."""
        leaves = []
        for child in root_rule.children():
            if child.active():
                if child.children():
                    leaves.extend(self._collect_leaf_rules(child))
                elif child.symbol() is not None:
                    leaves.append(child)
        return leaves

    def _build_sld_for_rule(self, rule, layer_name, style_name):
        """
        Build a complete SLD 1.0.0 document for a single rule.

        Returns:
            str: SLD XML content, or None on failure.
        """
        try:
            return self._export_single_rule_sld(rule, layer_name, style_name)

        except Exception as e:
            self.main.log_message(
                f"Error building SLD for rule '{rule.label()}': {e}",
                level=Qgis.Critical
            )
            return None

    def _export_single_rule_sld(self, rule, layer_name, style_name):
        """
        Generate SLD 1.0.0 XML for a single rule using direct symbol introspection.
        Produces GeoServer-compatible output with ogc:Filter, scale denominators,
        and correct symbolizers per symbol layer.
        """
        symbol = rule.symbol()
        if symbol is None:
            return None

        # Build the SLD XML tree
        ET.register_namespace('', NS_SLD)
        ET.register_namespace('sld', NS_SLD)
        ET.register_namespace('ogc', NS_OGC)
        ET.register_namespace('se', NS_SE)
        ET.register_namespace('xsi', NS_XSI)

        sld_root = ET.Element('StyledLayerDescriptor', {
            'version': '1.0.0',
            'xmlns': NS_SLD,
            'xmlns:sld': NS_SLD,
            'xmlns:ogc': NS_OGC,
            'xmlns:se': NS_SE,
            'xmlns:xsi': NS_XSI,
            f'{{{NS_XSI}}}schemaLocation':
                'http://www.opengis.net/sld '
                'http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd',
        })

        named_layer = ET.SubElement(sld_root, 'NamedLayer')
        name_elem = ET.SubElement(named_layer, 'Name')
        name_elem.text = layer_name

        user_style = ET.SubElement(named_layer, 'UserStyle')
        us_name = ET.SubElement(user_style, 'Name')
        us_name.text = style_name
        us_title = ET.SubElement(user_style, 'Title')
        us_title.text = rule.label() or style_name

        fts = ET.SubElement(user_style, 'FeatureTypeStyle')
        fts_name = ET.SubElement(fts, 'Name')
        fts_name.text = style_name

        # Each symbol layer becomes its own Rule to preserve draw order (casing first)
        sym_layer_count = symbol.symbolLayerCount()
        for sl_idx in range(sym_layer_count):
            sym_layer = symbol.symbolLayer(sl_idx)
            rule_elem = ET.SubElement(fts, 'Rule')

            rule_name_elem = ET.SubElement(rule_elem, 'Name')
            rule_name_elem.text = f"{style_name}__sl{sl_idx}"

            rule_title_elem = ET.SubElement(rule_elem, 'Title')
            rule_title_elem.text = f"{rule.label() or style_name} (layer {sl_idx})"

            # OGC Filter from rule expression
            filter_expr = rule.filterExpression()
            if filter_expr and filter_expr.strip() and filter_expr.strip() != 'ELSE':
                filter_xml = self._expression_to_ogc_filter(filter_expr)
                if filter_xml is not None:
                    rule_elem.append(filter_xml)

            # Scale denominators
            if rule.minimumScale() > 0:
                min_scale = ET.SubElement(rule_elem, 'MinScaleDenominator')
                min_scale.text = str(rule.minimumScale())
            if rule.maximumScale() > 0:
                max_scale = ET.SubElement(rule_elem, 'MaxScaleDenominator')
                max_scale.text = str(rule.maximumScale())

            # Build symbolizer from this symbol layer
            symbolizer = self._build_symbolizer(sym_layer, symbol.type())
            if symbolizer is not None:
                rule_elem.append(symbolizer)

        return ET.tostring(sld_root, encoding='unicode', xml_declaration=True)

    def _expression_to_ogc_filter(self, expr):
        """
        Convert a QGIS filter expression string to an OGC Filter XML element.
        Handles simple equality, comparison, and IS NULL checks.
        Returns an ET.Element or None if conversion is not possible.
        """
        try:
            expr = expr.strip()

            # Pattern: "field" = 'value'  or  "field" = number
            m = re.match(
                r'^"?([^"=<>!]+)"?\s*(=|!=|<>|>=|<=|>|<)\s*\'?([^\']+)\'?$', expr
            )
            if m:
                field, op, value = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
                op_map = {
                    '=': 'PropertyIsEqualTo',
                    '!=': 'PropertyIsNotEqualTo',
                    '<>': 'PropertyIsNotEqualTo',
                    '>': 'PropertyIsGreaterThan',
                    '<': 'PropertyIsLessThan',
                    '>=': 'PropertyIsGreaterThanOrEqualTo',
                    '<=': 'PropertyIsLessThanOrEqualTo',
                }
                ogc_op = op_map.get(op, 'PropertyIsEqualTo')
                filter_elem = ET.Element(f'{{{NS_OGC}}}Filter')
                comp = ET.SubElement(filter_elem, f'{{{NS_OGC}}}{ogc_op}')
                prop = ET.SubElement(comp, f'{{{NS_OGC}}}PropertyName')
                prop.text = field
                lit = ET.SubElement(comp, f'{{{NS_OGC}}}Literal')
                lit.text = value
                return filter_elem

            # Pattern: "field" IN ('a','b','c')
            m = re.match(r'^"?([^"]+)"?\s+IN\s*\((.+)\)$', expr, re.IGNORECASE)
            if m:
                field = m.group(1).strip()
                values = [v.strip().strip("'\"") for v in m.group(2).split(',')]
                filter_elem = ET.Element(f'{{{NS_OGC}}}Filter')
                if len(values) == 1:
                    comp = ET.SubElement(filter_elem, f'{{{NS_OGC}}}PropertyIsEqualTo')
                    prop = ET.SubElement(comp, f'{{{NS_OGC}}}PropertyName')
                    prop.text = field
                    lit = ET.SubElement(comp, f'{{{NS_OGC}}}Literal')
                    lit.text = values[0]
                else:
                    or_elem = ET.SubElement(filter_elem, f'{{{NS_OGC}}}Or')
                    for v in values:
                        comp = ET.SubElement(or_elem, f'{{{NS_OGC}}}PropertyIsEqualTo')
                        prop = ET.SubElement(comp, f'{{{NS_OGC}}}PropertyName')
                        prop.text = field
                        lit = ET.SubElement(comp, f'{{{NS_OGC}}}Literal')
                        lit.text = v
                return filter_elem

            # Fallback: wrap as CQL Filter comment (won't render but won't crash)
            self.main.log_message(
                f"[RuleExporter] Complex expression not converted, using CQL fallback: {expr}",
                level=Qgis.Warning
            )
            filter_elem = ET.Element(f'{{{NS_OGC}}}Filter')
            cql = ET.SubElement(filter_elem, f'{{{NS_OGC}}}PropertyIsEqualTo',
                                {'matchCase': 'false'})
            prop = ET.SubElement(cql, f'{{{NS_OGC}}}Function', {'name': 'cql_filter'})
            prop.text = expr
            return filter_elem

        except Exception as e:
            self.main.log_message(
                f"[RuleExporter] Could not convert expression '{expr}': {e}",
                level=Qgis.Warning
            )
            return None

    def _build_symbolizer(self, sym_layer, symbol_type):
        """
        Build an SLD symbolizer element from a QGIS symbol layer.
        Supports Line, Fill (polygon), and Marker (point) symbol layers.
        """
        try:
            props = sym_layer.properties()
            layer_class = type(sym_layer).__name__

            # --- LINE SYMBOLIZER ---
            if 'Line' in layer_class or symbol_type == 1:
                sym_elem = ET.Element('LineSymbolizer')
                stroke = ET.SubElement(sym_elem, 'Stroke')
                self._add_css(stroke, 'stroke',
                              self._get_color(props, ['line_color', 'color'], '#000000'))
                self._add_css(stroke, 'stroke-width',
                              str(self._get_float(props, ['line_width', 'width'], 0.3)))
                self._add_css(stroke, 'stroke-opacity',
                              str(self._get_opacity(props, ['line_color', 'color'])))
                dash = props.get('customdash', props.get('line_style', ''))
                if dash and dash not in ('', 'solid', 'no'):
                    self._add_css(stroke, 'stroke-dasharray', dash.replace(';', ' '))
                return sym_elem

            # --- POLYGON / FILL SYMBOLIZER ---
            if 'Fill' in layer_class or symbol_type == 2:
                sym_elem = ET.Element('PolygonSymbolizer')
                # Fill
                fill_color = self._get_color(props, ['color', 'fill_color'], '#aaaaaa')
                fill_opacity = self._get_opacity(props, ['color', 'fill_color'])
                fill_style = props.get('style', 'solid')
                if fill_style != 'no':
                    fill = ET.SubElement(sym_elem, 'Fill')
                    self._add_css(fill, 'fill', fill_color)
                    self._add_css(fill, 'fill-opacity', str(fill_opacity))
                # Stroke
                outline_style = props.get('outline_style', props.get('border_style', 'solid'))
                if outline_style != 'no':
                    stroke = ET.SubElement(sym_elem, 'Stroke')
                    self._add_css(stroke, 'stroke',
                                  self._get_color(props, ['outline_color', 'border_color'], '#000000'))
                    self._add_css(stroke, 'stroke-width',
                                  str(self._get_float(props, ['outline_width', 'border_width'], 0.3)))
                return sym_elem

            # --- POINT / MARKER SYMBOLIZER ---
            if 'Marker' in layer_class or symbol_type == 0:
                sym_elem = ET.Element('PointSymbolizer')
                graphic = ET.SubElement(sym_elem, 'Graphic')
                mark = ET.SubElement(graphic, 'Mark')
                wkn = ET.SubElement(mark, 'WellKnownName')
                shape = props.get('name', 'circle')
                wkn.text = shape if shape in ('square', 'circle', 'triangle', 'star', 'cross', 'x') else 'circle'
                fill = ET.SubElement(mark, 'Fill')
                self._add_css(fill, 'fill',
                              self._get_color(props, ['color', 'fill_color'], '#ff0000'))
                self._add_css(fill, 'fill-opacity',
                              str(self._get_opacity(props, ['color', 'fill_color'])))
                stroke = ET.SubElement(mark, 'Stroke')
                self._add_css(stroke, 'stroke',
                              self._get_color(props, ['outline_color', 'border_color'], '#000000'))
                size_elem = ET.SubElement(graphic, 'Size')
                size_elem.text = str(self._get_float(props, ['size'], 4.0))
                return sym_elem

            self.main.log_message(
                f"[RuleExporter] Unknown symbol layer type '{layer_class}' — skipping",
                level=Qgis.Warning
            )
            return None

        except Exception as e:
            self.main.log_message(
                f"[RuleExporter] Error building symbolizer: {e}",
                level=Qgis.Warning
            )
            return None

    def _add_css(self, parent, name, value):
        """Add a CssParameter child element."""
        css = ET.SubElement(parent, 'CssParameter', {'name': name})
        css.text = str(value)

    def _get_color(self, props, keys, default='#000000'):
        """Extract hex color from properties dict, trying multiple keys."""
        for key in keys:
            val = props.get(key, '')
            if val:
                # QGIS colors: '255,0,0,255' or '#ff0000'
                if val.startswith('#'):
                    return val
                parts = val.split(',')
                if len(parts) >= 3:
                    try:
                        r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                        return '#{:02x}{:02x}{:02x}'.format(r, g, b)
                    except ValueError:
                        pass
        return default

    def _get_opacity(self, props, keys):
        """Extract opacity (0.0–1.0) from the alpha channel of a color property."""
        for key in keys:
            val = props.get(key, '')
            if val:
                parts = val.split(',')
                if len(parts) == 4:
                    try:
                        return round(int(parts[3]) / 255.0, 3)
                    except ValueError:
                        pass
        return 1.0

    def _get_float(self, props, keys, default=1.0):
        """Extract a float value from properties dict, trying multiple keys."""
        for key in keys:
            val = props.get(key, '')
            if val:
                try:
                    return float(val)
                except ValueError:
                    pass
        return default
