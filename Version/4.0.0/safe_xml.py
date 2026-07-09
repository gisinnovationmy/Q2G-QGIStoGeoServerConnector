"""Safe XML parsing utilities that harden ElementTree against XXE attacks.

Use this module instead of xml.etree.ElementTree.fromstring when parsing XML
that comes from an external source (GeoServer REST responses, SLD content, etc.).
"""

import xml.etree.ElementTree as ET  # nosec B405

try:
    # Prefer defusedxml when available; it is the strongest mitigation.
    from defusedxml.ElementTree import fromstring as _defused_fromstring
    _HAS_DEFUSED = True
except Exception:  # nosec B110
    _HAS_DEFUSED = False


def fromstring(text, parser=None):
    """Parse XML from a string using a hardened parser.

    Args:
        text: XML string or bytes to parse.
        parser: Optional custom parser. If not provided, a safe parser is used.

    Returns:
        Element: The root element of the parsed XML tree.
    """
    if _HAS_DEFUSED:
        return _defused_fromstring(text)
    if parser is None:
        # Create a fresh parser each time; ElementTree XMLParser instances are
        # not reusable and can become corrupted if shared across parses.
        parser = ET.XMLParser()  # nosec B314
    return ET.fromstring(text, parser=parser)  # nosec B314


def parse(source, parser=None):
    """Parse XML from a file or file-like object using a hardened parser."""
    if _HAS_DEFUSED:
        from defusedxml.ElementTree import parse as _defused_parse
        return _defused_parse(source)
    if parser is None:
        # Create a fresh parser each time; ElementTree XMLParser instances are
        # not reusable and can become corrupted if shared across parses.
        parser = ET.XMLParser()  # nosec B314
    return ET.parse(source, parser=parser)  # nosec B314
