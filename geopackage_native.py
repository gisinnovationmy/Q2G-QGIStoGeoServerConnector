import os
import requests
import traceback
from qgis.core import Qgis


class GeoPackageNativeUploader:
    """
    Native GeoPackage uploader using GeoServer REST API.
    NO Importer API, NO Shapefile conversion - pure native GeoPackage support.
    """
    
    def __init__(self, main_instance):
        """
        Initialize with reference to main plugin instance for logging and utilities.
        
        Args:
            main_instance: Reference to QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
    
    def upload_geopackage(self, layer, workspace, url, username, password):
        """
        Upload GeoPackage using native GeoServer REST API.
        Creates a datastore and publishes the layer directly - NO CONVERSION TO SHAPEFILE.
        
        Args:
            layer: QGIS layer object
            workspace: Target GeoServer workspace name
            url: GeoServer base URL
            username: GeoServer username  
            password: GeoServer password
            
        Returns:
            bool: True if upload succeeded, False otherwise
        """
        try:
            # Get layer info
            source_path = layer.source().split('|')[0].split('?')[0]
            layer_source = layer.source()
            
            # Extract the actual layer name from the GeoPackage
            if '|layername=' in layer_source:
                gpkg_layer_name = layer_source.split('|layername=')[1].split('|')[0]
            else:
                self.main.log_message("❌ Cannot determine layer name from GeoPackage source", level=Qgis.Critical)
                return False
            
            # Sanitize names for GeoServer
            sanitized_layer_name = self.main._sanitize_layer_name(layer.name())
            datastore_name = sanitized_layer_name
            
            self.main.log_message(f"🔄 Native GeoPackage upload starting...")
            self.main.log_message(f"   Source: {source_path}")
            self.main.log_message(f"   GeoPackage layer: {gpkg_layer_name}")
            self.main.log_message(f"   GeoServer layer: {sanitized_layer_name}")
            self.main.log_message(f"   Datastore: {datastore_name}")
            
            if not os.path.exists(source_path):
                self.main.log_message(f"❌ GeoPackage file not found: {source_path}", level=Qgis.Critical)
                return False
            
            # Step 1: Upload GeoPackage file to GeoServer data directory
            if not self._upload_file_to_server(source_path, datastore_name, url, username, password):
                return False
            
            # Step 2: Create GeoPackage datastore (or use existing one)
            if not self._ensure_datastore_exists(datastore_name, workspace, url, username, password):
                return False
            
            # Step 3: Publish the layer from the datastore
            if not self._publish_layer(gpkg_layer_name, sanitized_layer_name, datastore_name, workspace, url, username, password):
                return False
            
            self.main.log_message(f"✅ GeoPackage layer '{layer.name()}' uploaded successfully using native REST API!")
            return True
            
        except Exception as e:
            self.main.log_message(f"❌ Error in native GeoPackage upload: {e}", level=Qgis.Critical)
            self.main.log_message(traceback.format_exc())
            return False

    def upload_geopackage_batch(self, layers, workspace, url, username, password):
        """
        Upload multiple layers from the same GeoPackage file.
        Uploads the file ONCE and publishes ALL layers from it.
        
        Args:
            layers: List of QGIS layer objects from the same GeoPackage
            workspace: Target GeoServer workspace name
            url: GeoServer base URL
            username: GeoServer username  
            password: GeoServer password
            
        Returns:
            bool: True if all layers uploaded successfully, False otherwise
        """
        if not layers:
            self.main.log_message("❌ No layers provided for batch upload", level=Qgis.Critical)
            return False
        
        try:
            # Get source path from first layer
            first_layer = layers[0]
            source_path = first_layer.source().split('|')[0].split('?')[0]
            
            if not os.path.exists(source_path):
                self.main.log_message(f"❌ GeoPackage file not found: {source_path}", level=Qgis.Critical)
                return False
            
            # Use first layer's name for datastore
            sanitized_first_name = self.main._sanitize_layer_name(first_layer.name())
            datastore_name = sanitized_first_name
            
            self.main.log_message(f"🔄 Batch GeoPackage upload starting...")
            self.main.log_message(f"   Source: {source_path}")
            self.main.log_message(f"   Datastore: {datastore_name}")
            self.main.log_message(f"   Layers to publish: {len(layers)}")
            
            # Step 1: Upload GeoPackage file ONCE
            if not self._upload_file_to_server(source_path, datastore_name, url, username, password):
                return False
            
            # Step 2: Create GeoPackage datastore (or use existing one)
            if not self._ensure_datastore_exists(datastore_name, workspace, url, username, password):
                return False
            
            # Step 3: Publish ALL layers from the datastore
            all_success = True
            for layer in layers:
                layer_source = layer.source()
                
                # Extract the actual layer name from the GeoPackage
                if '|layername=' in layer_source:
                    gpkg_layer_name = layer_source.split('|layername=')[1].split('|')[0]
                else:
                    self.main.log_message(f"⚠️ Cannot determine layer name for '{layer.name()}' - skipping", level=Qgis.Warning)
                    all_success = False
                    continue
                
                sanitized_layer_name = self.main._sanitize_layer_name(layer.name())
                
                # Publish this layer
                if not self._publish_layer(gpkg_layer_name, sanitized_layer_name, datastore_name, workspace, url, username, password):
                    all_success = False
                    continue
                
                self.main.log_message(f"✅ Layer '{layer.name()}' published from GeoPackage")
            
            if all_success:
                self.main.log_message(f"✅ All {len(layers)} layers uploaded successfully from GeoPackage!")
            else:
                self.main.log_message(f"⚠️ Some layers failed to publish from GeoPackage", level=Qgis.Warning)
            
            return all_success
            
        except Exception as e:
            self.main.log_message(f"❌ Error in batch GeoPackage upload: {e}", level=Qgis.Critical)
            self.main.log_message(traceback.format_exc())
            return False

    def _upload_file_to_server(self, source_path, datastore_name, url, username, password):
        """Upload GeoPackage file to GeoServer data directory via REST API."""
        try:
            upload_url = f"{url}/rest/resource/data/{datastore_name}.gpkg"
            self.main.log_message(f"📤 Uploading GeoPackage file to: {upload_url}")
            
            with open(source_path, 'rb') as f:
                response = requests.put(
                    upload_url,
                    auth=(username, password),
                    data=f,
                    headers={'Content-Type': 'application/octet-stream'}
                )
            
            if response.status_code in [200, 201]:
                self.main.log_message("✅ GeoPackage file uploaded to server")
                return True
            else:
                self.main.log_message(f"❌ Failed to upload GeoPackage file: {response.status_code} - {response.text}", level=Qgis.Critical)
                return False
                
        except Exception as e:
            self.main.log_message(f"❌ Error uploading GeoPackage file: {e}", level=Qgis.Critical)
            return False

    def _ensure_datastore_exists(self, datastore_name, workspace, url, username, password):
        """Ensure GeoPackage datastore exists - create if needed, use if exists."""
        try:
            # First check if datastore already exists
            check_url = f"{url}/rest/workspaces/{workspace}/datastores/{datastore_name}"
            check_response = requests.get(check_url, auth=(username, password))
            
            if check_response.status_code == 200:
                self.main.log_message(f"✅ GeoPackage datastore '{datastore_name}' already exists - using existing")
                return True
            elif check_response.status_code == 404:
                # Datastore doesn't exist, create it
                return self._create_new_datastore(datastore_name, workspace, url, username, password)
            else:
                self.main.log_message(f"❌ Error checking datastore existence: {check_response.status_code}", level=Qgis.Critical)
                return False
                
        except Exception as e:
            self.main.log_message(f"❌ Error ensuring datastore exists: {e}", level=Qgis.Critical)
            return False

    def _create_new_datastore(self, datastore_name, workspace, url, username, password):
        """Create a new GeoPackage datastore in GeoServer."""
        try:
            datastore_url = f"{url}/rest/workspaces/{workspace}/datastores"
            self.main.log_message(f"🏪 Creating new GeoPackage datastore: {datastore_name}")
            
            # GeoPackage datastore configuration
            datastore_config = {
                "dataStore": {
                    "name": datastore_name,
                    "type": "GeoPackage",
                    "connectionParameters": {
                        "entry": [
                            {"@key": "database", "$": f"file:data/{datastore_name}.gpkg"},
                            {"@key": "dbtype", "$": "geopkg"}
                        ]
                    }
                }
            }
            
            response = requests.post(
                datastore_url,
                auth=(username, password),
                json=datastore_config,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code in [200, 201]:
                self.main.log_message("✅ GeoPackage datastore created successfully")
                return True
            else:
                self.main.log_message(f"❌ Failed to create datastore: {response.status_code} - {response.text}", level=Qgis.Critical)
                return False
                
        except Exception as e:
            self.main.log_message(f"❌ Error creating GeoPackage datastore: {e}", level=Qgis.Critical)
            return False

    def _publish_layer(self, gpkg_layer_name, geoserver_layer_name, datastore_name, workspace, url, username, password):
        """Publish a layer from the GeoPackage datastore."""
        try:
            # First check if layer already exists
            check_layer_url = f"{url}/rest/workspaces/{workspace}/datastores/{datastore_name}/featuretypes/{geoserver_layer_name}"
            check_response = requests.get(check_layer_url, auth=(username, password))
            
            if check_response.status_code == 200:
                self.main.log_message(f"✅ Layer '{geoserver_layer_name}' already exists - skipping publish")
                return True
            elif check_response.status_code != 404:
                self.main.log_message(f"❌ Error checking layer existence: {check_response.status_code}", level=Qgis.Critical)
                return False
            
            # Layer doesn't exist, publish it
            layer_url = f"{url}/rest/workspaces/{workspace}/datastores/{datastore_name}/featuretypes"
            self.main.log_message(f"📋 Publishing new layer: {gpkg_layer_name} as {geoserver_layer_name}")
            
            # Layer configuration
            layer_config = {
                "featureType": {
                    "name": geoserver_layer_name,
                    "nativeName": gpkg_layer_name,
                    "title": geoserver_layer_name,
                    "enabled": True
                }
            }
            
            response = requests.post(
                layer_url,
                auth=(username, password),
                json=layer_config,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code in [200, 201]:
                self.main.log_message(f"✅ Layer '{geoserver_layer_name}' published successfully")
                return True
            else:
                self.main.log_message(f"❌ Failed to publish layer: {response.status_code} - {response.text}", level=Qgis.Critical)
                return False
                
        except Exception as e:
            self.main.log_message(f"❌ Error publishing GeoPackage layer: {e}", level=Qgis.Critical)
            return False
