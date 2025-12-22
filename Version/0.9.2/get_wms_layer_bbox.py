"""
Get WMS Layer BBox Module
Handles fetching and parsing WMS Capabilities XML to get bounding boxes for layers.
Extracted from main.py for better code organization and maintainability.
"""

import xml.etree.ElementTree as ET
import requests


class WMSLayerBBoxRetriever:
    """Handles WMS capabilities parsing and bounding box retrieval for layers."""
    
    def __init__(self, main_instance):
        """
        Initialize the WMS layer bbox retriever.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def get_wms_layer_bbox(self, url, username, password, layer_name):
        """
        Fetch and parse WMS Capabilities XML to get the bounding box for a given layer.
        
        Args:
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            layer_name: Name of the layer to get bbox for
            
        Returns:
            tuple: (extent, crs) where extent is [minx, miny, maxx, maxy] and crs is the coordinate reference system,
                   or (None, None) if not found or error occurred
        """
        wms_url = f"{url}/ows?service=WMS&version=1.1.1&request=GetCapabilities"
        self.main.log_message(f"Fetching WMS Capabilities from: {wms_url}")
        
        try:
            # Fetch WMS capabilities
            capabilities_xml = self._fetch_wms_capabilities(wms_url, username, password)
            if not capabilities_xml:
                return None, None
            
            # Parse XML and find layer
            root = ET.fromstring(capabilities_xml)
            layer_node = self._find_layer_in_capabilities(root, layer_name)
            if not layer_node:
                return None, None
            
            # Extract bounding box information
            return self._extract_bounding_box(layer_node, layer_name)
            
        except Exception as e:
            self.main.log_message(f"Exception while parsing WMS Capabilities: {e}")
            return None, None
    
    def _fetch_wms_capabilities(self, wms_url, username, password):
        """
        Fetch WMS capabilities XML from the server.
        
        Args:
            wms_url: WMS capabilities URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bytes: XML content or None if fetch failed
        """
        try:
            response = requests.get(wms_url, auth=(username, password), timeout=15)
            if response.status_code != 200:
                self.main.log_message(f"Failed to fetch WMS Capabilities: {response.status_code} - Response: {response.text[:200]}...")
                return None
            return response.content
        except Exception as e:
            self.main.log_message(f"Error fetching WMS Capabilities: {e}")
            return None
    
    def _find_layer_in_capabilities(self, root, layer_name):
        """
        Find the specified layer in the WMS capabilities XML.
        
        Args:
            root: XML root element
            layer_name: Name of the layer to find
            
        Returns:
            Element: Layer XML element or None if not found
        """
        self.main.log_message(f"WMS Capabilities XML parsed, searching for layer: {layer_name}")
        
        # Define namespaces
        namespaces = {'wms': 'http://www.opengis.net/wms'}
        
        # Try to find the correct Layer node with and without namespace
        all_layers = root.findall('.//wms:Layer', namespaces) + root.findall('.//Layer')
        self.main.log_message(f"Total layers found in WMS Capabilities: {len(all_layers)}")
        
        found_layers = []
        layer_node = None
        
        for lyr in all_layers:
            name = lyr.find('wms:Name', namespaces)
            if name is None:
                name = lyr.find('Name')
            if name is not None:
                found_layers.append(name.text)
                if name.text == layer_name:
                    layer_node = lyr
                    break
        
        self.main.log_message(f"Layers in WMS Capabilities (first 10): {found_layers[:10]}")
        
        if layer_node is None:
            self.main.log_message(f"Layer {layer_name} not found in WMS Capabilities.")
            return None
        
        self.main.log_message(f"Found layer {layer_name} in WMS Capabilities, looking for bounding box.")
        return layer_node
    
    def _extract_bounding_box(self, layer_node, layer_name):
        """
        Extract bounding box information from the layer node.
        
        Args:
            layer_node: XML layer element
            layer_name: Name of the layer (for logging)
            
        Returns:
            tuple: (extent, crs) or (None, None) if no bounding box found
        """
        namespaces = {'wms': 'http://www.opengis.net/wms'}
        
        # Try EX_GeographicBoundingBox (always in EPSG:4326)
        extent, crs = self._try_geographic_bounding_box(layer_node, layer_name, namespaces)
        if extent:
            return extent, crs
        
        # Try BoundingBox node (may have a CRS)
        extent, crs = self._try_bounding_box(layer_node, layer_name, namespaces)
        if extent:
            return extent, crs
        
        self.main.log_message(f"No bounding box found for {layer_name} in WMS Capabilities.")
        return None, None
    
    def _try_geographic_bounding_box(self, layer_node, layer_name, namespaces):
        """
        Try to extract EX_GeographicBoundingBox (EPSG:4326).
        
        Args:
            layer_node: XML layer element
            layer_name: Name of the layer (for logging)
            namespaces: XML namespaces
            
        Returns:
            tuple: (extent, crs) or (None, None) if not found
        """
        bbox_node = layer_node.find('wms:EX_GeographicBoundingBox', namespaces)
        if bbox_node is None:
            bbox_node = layer_node.find('EX_GeographicBoundingBox')
        
        if bbox_node is not None:
            try:
                west = float(bbox_node.findtext('wms:westBoundLongitude', bbox_node.findtext('westBoundLongitude'), namespaces))
                east = float(bbox_node.findtext('wms:eastBoundLongitude', bbox_node.findtext('eastBoundLongitude'), namespaces))
                south = float(bbox_node.findtext('wms:southBoundLatitude', bbox_node.findtext('southBoundLatitude'), namespaces))
                north = float(bbox_node.findtext('wms:northBoundLatitude', bbox_node.findtext('northBoundLatitude'), namespaces))
                extent = [west, south, east, north]
                self.main.log_message(f"Found EX_GeographicBoundingBox for {layer_name}: {extent}")
                return extent, 'EPSG:4326'
            except (ValueError, TypeError) as e:
                self.main.log_message(f"Error parsing EX_GeographicBoundingBox for {layer_name}: {e}")
        
        self.main.log_message(f"No EX_GeographicBoundingBox for {layer_name}, trying BoundingBox.")
        return None, None
    
    def _try_bounding_box(self, layer_node, layer_name, namespaces):
        """
        Try to extract BoundingBox with CRS information.
        
        Args:
            layer_node: XML layer element
            layer_name: Name of the layer (for logging)
            namespaces: XML namespaces
            
        Returns:
            tuple: (extent, crs) or (None, None) if not found
        """
        bbox_node = layer_node.find('wms:BoundingBox', namespaces)
        if bbox_node is None:
            bbox_node = layer_node.find('BoundingBox')
        
        if bbox_node is not None:
            try:
                minx = float(bbox_node.attrib.get('minx'))
                miny = float(bbox_node.attrib.get('miny'))
                maxx = float(bbox_node.attrib.get('maxx'))
                maxy = float(bbox_node.attrib.get('maxy'))
                crs = bbox_node.attrib.get('CRS') or bbox_node.attrib.get('SRS') or 'EPSG:4326'
                extent = [minx, miny, maxx, maxy]
                self.main.log_message(f"Found BoundingBox for {layer_name}: {extent} in CRS {crs}")
                return extent, crs
            except (ValueError, TypeError) as e:
                self.main.log_message(f"Error parsing BoundingBox for {layer_name}: {e}")
        
        return None, None
