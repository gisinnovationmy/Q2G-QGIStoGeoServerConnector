"""
Intermediary Style Manager Module
Handles creation and management of generic placeholder SLD styles.
Used for the 3-step upload workflow: Intermediary Style → Layer → Real Style
"""

import requests


class IntermediaryStyleManager:
    """Manages creation and overwriting of intermediary placeholder styles."""
    
    def __init__(self, main_instance):
        """
        Initialize the intermediary style manager.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def create_intermediary_style(self, layer_name, workspace, url, username, password):
        """
        Create a generic placeholder SLD style in the workspace.
        
        This style is geometry-agnostic and can be applied to any layer type.
        It uses a simple black outline with transparent fill.
        
        Args:
            layer_name: Sanitized layer name (used as style name)
            workspace: GeoServer workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if intermediary style was created successfully, False otherwise
        """
        try:
            # Generic SLD that works for all geometry types
            intermediary_sld = self._get_generic_intermediary_sld()
            
            style_name = layer_name
            style_url = f"{url}/rest/workspaces/{workspace}/styles/{style_name}.sld?raw=true"
            
            self.main.log_message(f"📝 Step 1: Creating intermediary style '{style_name}' in workspace '{workspace}'")
            
            # Try PUT first (update if exists)
            headers = {'Content-Type': 'application/vnd.ogc.sld+xml'}
            response = requests.put(
                style_url,
                data=intermediary_sld.encode('utf-8'),
                auth=(username, password),
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                self.main.log_message(f"✓ Intermediary style '{style_name}' created successfully")
                return True
            else:
                self.main.log_message(
                    f"⚠ Failed to create intermediary style. Status: {response.status_code}. "
                    f"Response: {response.text[:200]}"
                )
                return False
                
        except Exception as e:
            self.main.log_message(f"❌ Error creating intermediary style: {str(e)}")
            return False
    
    def overwrite_with_real_style(self, layer_name, sld_content, workspace, url, username, password):
        """
        Overwrite the intermediary style with the real SLD from the QGIS layer.
        
        Args:
            layer_name: Sanitized layer name (style name)
            sld_content: Real SLD content from QGIS layer
            workspace: GeoServer workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if style was overwritten successfully, False otherwise
        """
        try:
            style_name = layer_name
            style_url = f"{url}/rest/workspaces/{workspace}/styles/{style_name}.sld?raw=true"
            
            self.main.log_message(f"📝 Step 3: Overwriting intermediary style with real SLD for '{style_name}'")
            
            headers = {'Content-Type': 'application/vnd.ogc.sld+xml'}
            response = requests.put(
                style_url,
                data=sld_content.encode('utf-8'),
                auth=(username, password),
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                self.main.log_message(f"✓ Style '{style_name}' overwritten with real SLD successfully")
                return True
            else:
                self.main.log_message(
                    f"⚠ Failed to overwrite style. Status: {response.status_code}. "
                    f"Response: {response.text[:200]}"
                )
                return False
                
        except Exception as e:
            self.main.log_message(f"❌ Error overwriting style: {str(e)}")
            return False
    
    def _get_generic_intermediary_sld(self):
        """
        Get a generic SLD that works for all geometry types.
        
        Returns:
            str: Generic SLD content
        """
        return """<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
  xmlns="http://www.opengis.net/sld"
  xmlns:gml="http://www.opengis.net/gml"
  xmlns:ogc="http://www.opengis.net/ogc"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.opengis.net/sld http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">
  <NamedLayer>
    <Name>Placeholder Style</Name>
    <UserStyle>
      <Title>Generic Placeholder Style</Title>
      <FeatureTypeStyle>
        <!-- Point symbolizer -->
        <Rule>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:Function name="geometryType">
                <ogc:Literal>Point</ogc:Literal>
              </ogc:Function>
              <ogc:Literal>Point</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PointSymbolizer>
            <Graphic>
              <Mark>
                <WellKnownName>circle</WellKnownName>
                <Fill>
                  <CssParameter name="fill">#0000FF</CssParameter>
                </Fill>
                <Stroke>
                  <CssParameter name="stroke">#000000</CssParameter>
                  <CssParameter name="stroke-width">1</CssParameter>
                </Stroke>
              </Mark>
              <Size>6</Size>
            </Graphic>
          </PointSymbolizer>
        </Rule>
        
        <!-- Line symbolizer -->
        <Rule>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:Function name="geometryType">
                <ogc:Literal>LineString</ogc:Literal>
              </ogc:Function>
              <ogc:Literal>LineString</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <LineSymbolizer>
            <Stroke>
              <CssParameter name="stroke">#000000</CssParameter>
              <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
          </LineSymbolizer>
        </Rule>
        
        <!-- Polygon symbolizer -->
        <Rule>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:Function name="geometryType">
                <ogc:Literal>Polygon</ogc:Literal>
              </ogc:Function>
              <ogc:Literal>Polygon</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#FFFFFF</CssParameter>
              <CssParameter name="fill-opacity">0.5</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#000000</CssParameter>
              <CssParameter name="stroke-width">1</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
        
        <!-- Raster symbolizer -->
        <Rule>
          <RasterSymbolizer>
            <Opacity>1.0</Opacity>
          </RasterSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>"""
