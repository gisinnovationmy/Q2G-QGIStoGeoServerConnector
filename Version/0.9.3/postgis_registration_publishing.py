"""
PostGIS Registration and Publishing Module
Handles PostGIS datastore registration and layer publishing in GeoServer.
Extracted from main.py for better code organization and maintainability.
"""

import os
import json
import requests
from qgis.core import QgsDataSourceUri, QgsApplication, QgsProviderRegistry, Qgis


class PostGISRegistrationPublisher:
    """Handles PostGIS datastore registration and layer publishing."""
    
    def __init__(self, main_instance):
        """
        Initialize the PostGIS registration publisher.
        
        Args:
            main_instance: Reference to main QGISGeoServerLayerLoader instance
        """
        self.main = main_instance
        # Cache credentials to avoid asking for each layer from same database
        self._credential_cache = {}
    
    def register_and_publish(self, layer, layer_name, workspace, url, username, password):
        """
        Register a PostGIS data store in GeoServer and publish the table as a layer.
        
        Uses a shared datastore per database connection to avoid conflicts.
        Supports both traditional username/password and QGIS authentication configurations (authcfg).
        
        Args:
            layer: QGIS layer object
            layer_name: Sanitized layer name for GeoServer
            workspace: Target GeoServer workspace name
            url: GeoServer base URL
            username: GeoServer username
            password: GeoServer password
            
        Returns:
            bool: True if registration and publishing succeeded, False otherwise
        """
        try:
            # Step 1: Extract connection parameters
            pg_params = self._extract_connection_parameters(layer)
            if not pg_params:
                return False
            
            # Step 2: Create or verify datastore
            ds_name = self._create_datastore_name(pg_params['database'])
            if not self._create_or_verify_datastore(ds_name, pg_params, workspace, url, username, password):
                return False
            
            # Step 3: Verify table exists
            if not self._verify_table_exists(pg_params):
                return False
            
            # Step 4: Handle existing layer
            if not self._handle_existing_layer(layer_name, workspace, url, username, password):
                return False
            
            # Step 5: Create featuretype
            if not self._create_featuretype(layer, layer_name, pg_params, ds_name, workspace, url, username, password):
                return False
            
            # Step 6: Publish layer
            if not self._publish_layer(layer_name, workspace, url, username, password):
                return False
            
            # Step 7: Save credentials and refresh
            self._save_credentials_and_refresh(pg_params)
            
            return True
            
        except Exception as e:
            self.main.log_message(f"Exception while registering PostGIS datastore: {str(e)}")
            import traceback
            self.main.log_message(traceback.format_exc())
            return False
    
    def _extract_connection_parameters(self, layer):
        """
        Extract connection parameters from the QGIS layer with intelligent fallback logic.
        
        Strategy:
        1. Extract connection info from QGIS layer source
        2. Try to find exact match (database + host + port)
        3. If no exact match, try all saved connections in order
        4. Compare with layer's connection parameters for best match
        
        Returns:
            dict: Connection parameters or None if extraction failed
        """
        try:
            uri = QgsDataSourceUri(layer.source())
            
            # Extract connection parameters from layer
            pg_database = uri.database()
            pg_host = uri.host()
            pg_port = uri.port() or 5432
            pg_table = uri.table()
            pg_schema = uri.schema() or 'public'
            
            self.main.log_message(f"DEBUG: Layer connection info - {pg_database}@{pg_host}:{pg_port}")
            
            # Get all saved connections from postgis.ini
            all_saved = self.main.postgis_credentials.list_saved_connections()
            
            if not all_saved:
                self.main.log_message(f"✗ No saved PostGIS connections found in postgis.ini")
                return None
            
            # Strategy 1: Find exact match (database + host + port)
            exact_match = None
            for cred in all_saved:
                if (cred['database'] == pg_database and 
                    cred['host'] == pg_host and 
                    int(cred['port']) == pg_port):
                    exact_match = cred
                    break
            
            if exact_match:
                pg_params = {
                    'host': exact_match['host'],
                    'port': int(exact_match['port']),
                    'database': exact_match['database'],
                    'user': exact_match['user'],
                    'passwd': exact_match['passwd'],
                    'schema': exact_match.get('schema', pg_schema),
                    'table': pg_table,
                }
                self.main.log_message(f"✓ Found exact match: {pg_database}@{pg_host}:{pg_port}")
                return pg_params
            
            # Strategy 2: Find by database name (most recent/first saved)
            db_match = None
            for cred in all_saved:
                if cred['database'] == pg_database:
                    db_match = cred
                    break
            
            if db_match:
                pg_params = {
                    'host': db_match['host'],
                    'port': int(db_match['port']),
                    'database': db_match['database'],
                    'user': db_match['user'],
                    'passwd': db_match['passwd'],
                    'schema': db_match.get('schema', pg_schema),
                    'table': pg_table,
                }
                self.main.log_message(f"⚠️  No exact match found. Using database name match: {pg_database}@{db_match['host']}:{db_match['port']}")
                return pg_params
            
            # Strategy 3: Try all saved connections (for different database names)
            self.main.log_message(f"⚠️  No database name match found. Trying all {len(all_saved)} saved connection(s)...")
            for idx, cred in enumerate(all_saved, 1):
                self.main.log_message(f"   Attempt {idx}/{len(all_saved)}: {cred['database']}@{cred['host']}:{cred['port']}")
                
                # Try this connection
                pg_params = {
                    'host': cred['host'],
                    'port': int(cred['port']),
                    'database': cred['database'],
                    'user': cred['user'],
                    'passwd': cred['passwd'],
                    'schema': cred.get('schema', pg_schema),
                    'table': pg_table,
                }
                
                # Verify connection works
                if self._verify_table_exists(pg_params):
                    self.main.log_message(f"✓ Successfully connected using: {cred['database']}@{cred['host']}:{cred['port']}")
                    return pg_params
                else:
                    self.main.log_message(f"✗ Connection failed for: {cred['database']}@{cred['host']}:{cred['port']}")
            
            # No working connection found
            self.main.log_message(f"✗ Could not find working PostGIS connection for table '{pg_table}'")
            return None
            
        except Exception as e:
            self.main.log_message(f"Error extracting connection parameters: {str(e)}")
            import traceback
            self.main.log_message(traceback.format_exc())
            return None
    
    def _extract_authcfg_credentials(self, uri):
        """
        Extract credentials and host from QGIS authentication configuration.
        
        Returns:
            tuple: (username, password, host) or (None, None, None) if extraction failed
        """
        try:
            from qgis.core import QgsAuthManager
            
            authcfg = uri.authConfigId()
            if not authcfg:
                return None, None, None
            
            # Get auth manager
            auth_manager = QgsApplication.authManager()
            if not auth_manager:
                return None, None, None
            
            # Get the authentication config
            auth_config = auth_manager.authenticationConfig(authcfg)
            if not auth_config or not auth_config.isValid():
                self.main.log_message(f"Invalid authcfg: {authcfg}")
                return None, None, None
            
            # Extract credentials from auth config
            pg_user = auth_config.config('username', '')
            pg_passwd = auth_config.config('password', '')
            
            # Extract host from auth config (stored as 'host' or in uri)
            pg_host = auth_config.config('host', '')
            
            if not pg_host:
                # Try to extract from URI if available
                pg_host = uri.host()
            
            if not pg_host:
                pg_host = 'localhost'
            
            if pg_user and pg_passwd:
                self.main.log_message(f"✓ Extracted from authcfg: user={pg_user}, host={pg_host}")
                return pg_user, pg_passwd, pg_host
            
        except Exception as e:
            self.main.log_message(f"Error extracting authcfg: {str(e)}")
        
        return None, None, None
    
    def _get_or_prompt_credentials(self, uri):
        """
        Get credentials from cache or saved credentials.
        Uses saved credentials automatically - NO PROMPTING.
        
        Returns:
            tuple: (username, password) or (None, None) if not found
        """
        host = uri.host() or 'localhost'  # Default to localhost if empty
        port = uri.port() or 5432
        database = uri.database()
        
        cache_key = f"{host}:{port}:{database}"
        
        # Check cache first
        if cache_key in self._credential_cache:
            cached = self._credential_cache[cache_key]
            return cached['user'], cached['passwd']
        
        # Load from saved credentials file
        saved = self.main.postgis_credentials.load_credentials(database, host, port)
        
        if saved and saved.get('user') and saved.get('passwd'):
            # Cache for this session
            self._credential_cache[cache_key] = {
                'user': saved['user'],
                'passwd': saved['passwd']
            }
            self.main.log_message(f"✓ Using saved PostGIS credentials: {database}@{host}:{port}")
            return saved['user'], saved['passwd']
        
        # No credentials found
        self.main.log_message(f"✗ No PostGIS credentials saved for {database}@{host}:{port}")
        return None, None
    
    def _create_datastore_name(self, database):
        """
        Create a sanitized datastore name based on database name.
        
        Returns:
            str: Sanitized datastore name
        """
        ds_name = f"postgis_{database}"
        # Sanitize the name - only allow alphanumeric and underscore
        ds_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in ds_name)
        return ds_name
    
    def _create_or_verify_datastore(self, ds_name, pg_params, workspace, url, username, password):
        """
        Create or verify PostGIS datastore in GeoServer.
        
        Returns:
            bool: True if datastore is ready, False otherwise
        """
        # Check if the datastore already exists
        ds_url = f"{url}/rest/workspaces/{workspace}/datastores/{ds_name}.json"
        ds_resp = requests.get(ds_url, auth=(username, password))
        
        if ds_resp.status_code == 200:
            self.main.log_message(f"PostGIS datastore '{ds_name}' already exists in workspace '{workspace}'.")
            return self._verify_existing_datastore(ds_resp, ds_name, pg_params, workspace, url, username, password)
        else:
            return self._create_new_datastore(ds_name, pg_params, workspace, url, username, password)
    
    def _verify_existing_datastore(self, ds_resp, ds_name, pg_params, workspace, url, username, password):
        """
        Verify existing datastore has correct connection parameters.
        
        Returns:
            bool: True if datastore is valid, False otherwise
        """
        try:
            ds_data = ds_resp.json()
            existing_params = ds_data.get('dataStore', {}).get('connectionParameters', {})
            self.main.log_message(f"Existing datastore connection parameters: host={existing_params.get('host')}, database={existing_params.get('database')}, user={existing_params.get('user')}")
            
            # Check if the existing datastore has valid connection parameters
            if not existing_params.get('host') or not existing_params.get('database') or not existing_params.get('user'):
                self.main.log_message(f"Existing datastore has invalid connection parameters. Updating datastore...")
                return self._update_datastore(ds_name, pg_params, workspace, url, username, password)
            
            return True
            
        except Exception as e:
            self.main.log_message(f"Could not parse existing datastore info: {str(e)}")
            return False
    
    def _update_datastore(self, ds_name, pg_params, workspace, url, username, password):
        """
        Update existing datastore with correct connection parameters.
        
        Returns:
            bool: True if update succeeded, False otherwise
        """
        update_payload = {
            "dataStore": {
                "name": ds_name,
                "type": "PostGIS",
                "enabled": True,
                "connectionParameters": {
                    "host": pg_params['host'],
                    "port": str(pg_params['port']),
                    "database": pg_params['database'],
                    "user": pg_params['user'],
                    "passwd": pg_params['passwd'],
                    "schema": pg_params['schema'],
                    "dbtype": "postgis",
                    "Connection timeout": "20",
                    "validate connections": "true",
                    "max connections": "10",
                    "min connections": "1",
                    "fetch size": "1000"
                }
            }
        }
        
        ds_url = f"{url}/rest/workspaces/{workspace}/datastores/{ds_name}"
        update_resp = requests.put(
            ds_url,
            json=update_payload,
            auth=(username, password),
            headers={"Content-Type": "application/json"}
        )
        
        if update_resp.status_code in [200, 201]:
            self.main.log_message(f"Updated PostGIS datastore '{ds_name}' with correct connection parameters.")
            return True
        else:
            self.main.log_message(f"Failed to update datastore: {update_resp.status_code} {update_resp.text}")
            # If update fails, fall back to recreation
            delete_url = f"{url}/rest/workspaces/{workspace}/datastores/{ds_name}?recurse=true"
            delete_resp = requests.delete(delete_url, auth=(username, password))
            if delete_resp.status_code in [200, 204]:
                self.main.log_message(f"Deleted broken datastore '{ds_name}' for recreation")
                return self._create_new_datastore(ds_name, pg_params, workspace, url, username, password)
            return False
    
    def _create_new_datastore(self, ds_name, pg_params, workspace, url, username, password):
        """
        Create new PostGIS datastore in GeoServer.
        
        Returns:
            bool: True if creation succeeded, False otherwise
        """
        payload = {
            "dataStore": {
                "name": ds_name,
                "type": "PostGIS",
                "enabled": True,
                "connectionParameters": {
                    "host": pg_params['host'],
                    "port": str(pg_params['port']),
                    "database": pg_params['database'],
                    "user": pg_params['user'],
                    "passwd": pg_params['passwd'],
                    "dbtype": "postgis",
                    "schema": pg_params['schema'],
                    "Expose primary keys": "true",
                    "validate connections": "true",
                    "Connection timeout": "20",
                    "min connections": "1",
                    "max connections": "10",
                    "fetch size": "1000"
                }
            }
        }
        
        resp = requests.post(
            f"{url}/rest/workspaces/{workspace}/datastores",
            json=payload,
            auth=(username, password),
            headers={"Content-Type": "application/json"}
        )
        
        if resp.status_code not in [200, 201]:
            self.main.log_message(f"Failed to create PostGIS datastore: {resp.status_code} {resp.text}")
            return False
        
        self.main.log_message(f"Created PostGIS datastore '{ds_name}' in workspace '{workspace}'.")
        return True
    
    def _verify_table_exists(self, pg_params):
        """
        Verify that the table exists in the PostGIS database.
        
        Returns:
            bool: True if table exists or verification skipped, False if table missing
        """
        try:
            test_uri = QgsDataSourceUri()
            test_uri.setConnection(pg_params['host'], str(pg_params['port']), pg_params['database'], pg_params['user'], pg_params['passwd'])
            
            metadata = QgsProviderRegistry.instance().providerMetadata('postgres')
            if metadata:
                connection = metadata.createConnection(test_uri.uri(), {})
                if connection:
                    tables = connection.tables(pg_params['schema'])
                    table_names = [table.tableName() for table in tables]
                    if pg_params['table'] not in table_names:
                        self.main.log_message(f"ERROR: Table '{pg_params['table']}' not found in schema '{pg_params['schema']}'. Available tables: {table_names}")
                        return False
                    else:
                        self.main.log_message(f"Verified table '{pg_params['table']}' exists in schema '{pg_params['schema']}'")
                        return True
                else:
                    self.main.log_message(f"WARNING: Could not verify table existence - connection failed")
                    return True  # Continue anyway
            else:
                self.main.log_message(f"WARNING: Could not get PostgreSQL provider metadata")
                return True  # Continue anyway
        except Exception as e:
            self.main.log_message(f"WARNING: Could not verify table existence: {str(e)}")
            return True  # Continue anyway
    
    def _handle_existing_layer(self, layer_name, workspace, url, username, password):
        """
        Handle existing layer - either skip or overwrite based on settings.
        
        Returns:
            bool: True if should continue, False if should abort
        """
        # Check if the featuretype already exists (in datastore)
        featuretype_url = f"{url}/rest/workspaces/{workspace}/datastores/*/featuretypes/{layer_name}.json"
        ft_resp = requests.get(featuretype_url, auth=(username, password))
        
        # Also check if layer exists at workspace level
        layer_url = f"{url}/rest/workspaces/{workspace}/layers/{layer_name}.json"
        layer_resp = requests.get(layer_url, auth=(username, password))
        
        layer_exists_anywhere = (ft_resp.status_code == 200) or (layer_resp.status_code == 200)
        
        if layer_exists_anywhere:
            self.main.log_message(f"Layer '{layer_name}' already exists in workspace.")
            
            # Check if auto-overwrite is enabled
            if self.main.auto_overwrite_checkbox.isChecked():
                self.main.log_message(f"🔄 Overwriting existing PostGIS layer '{layer_name}'...")
                # Delete existing layer at workspace level
                delete_layer_url = f"{url}/rest/workspaces/{workspace}/layers/{layer_name}"
                delete_layer_resp = requests.delete(delete_layer_url, auth=(username, password), params={'recurse': 'true'})
                if delete_layer_resp.status_code in [200, 204]:
                    self.main.log_message(f"Deleted existing layer '{layer_name}' for overwrite")
                    return True  # Continue to create the new featuretype
                elif delete_layer_resp.status_code == 404:
                    # Layer already deleted, continue
                    self.main.log_message(f"Layer '{layer_name}' already deleted, proceeding with new upload")
                    return True
                else:
                    self.main.log_message(f"Failed to delete existing layer for overwrite: {delete_layer_resp.status_code} {delete_layer_resp.text}")
                    return False
            else:
                self.main.log_message(f"⚠ Skipping existing PostGIS layer '{layer_name}' (overwrite disabled)")
                return True  # Skip this layer but continue with others (return True to indicate success)
        
        return True  # No existing layer, continue
    
    def _create_featuretype(self, layer, layer_name, pg_params, ds_name, workspace, url, username, password):
        """
        Create featuretype in the datastore.
        
        Returns:
            bool: True if creation succeeded or already exists, False otherwise
        """
        featuretype_payload = {
            "featureType": {
                "name": layer_name,
                "nativeName": pg_params['table'],
                "title": layer_name,
                "abstract": f"PostGIS layer from table {pg_params['schema']}.{pg_params['table']}",
                "srs": layer.crs().authid() if hasattr(layer, 'crs') else "EPSG:4326",
                "enabled": True,
                "store": {
                    "@class": "dataStore",
                    "name": f"{workspace}:{ds_name}"
                }
            }
        }
        
        # Log the featuretype payload for debugging
        self.main.log_message(f"Creating featuretype with payload: {json.dumps(featuretype_payload, indent=2)}")
        
        publish_url = f"{url}/rest/workspaces/{workspace}/datastores/{ds_name}/featuretypes"
        pub_resp = requests.post(
            publish_url,
            json=featuretype_payload,
            auth=(username, password),
            headers={"Content-Type": "application/json"}
        )
        
        if pub_resp.status_code not in [200, 201]:
            # Try to get more details about the error
            self.main.log_message(f"Failed to publish table '{pg_params['table']}' as '{layer_name}': {pub_resp.status_code}")
            self.main.log_message(f"Response headers: {dict(pub_resp.headers)}")
            
            error_detail = ""
            try:
                if pub_resp.headers.get('content-type', '').startswith('application/json'):
                    error_detail = pub_resp.json()
                else:
                    error_detail = pub_resp.text
            except Exception as e:
                error_detail = f"Could not parse response: {str(e)}"
                
            self.main.log_message(f"Error details: {error_detail}")
            self.main.log_message(f"Request URL: {publish_url}")
            
            # Check if the error is "resource already exists" - if so, featuretype is already published
            if "already exists in store" in str(error_detail):
                self.main.log_message(f"ℹ️ Featuretype '{layer_name}' already exists in datastore '{ds_name}'. Proceeding to publish layer.")
                return True  # The featuretype exists, proceed to layer publishing
            else:
                return False
        else:
            self.main.log_message(f"✓ Successfully created PostGIS featuretype '{layer_name}'.")
            return True
    
    def _publish_layer(self, layer_name, workspace, url, username, password):
        """
        Publish the featuretype as a layer.
        
        Returns:
            bool: True if publishing succeeded, False otherwise
        """
        # A featuretype is not a layer until it is published.
        layer_publish_url = f"{url}/rest/workspaces/{workspace}/layers"
        layer_payload = {
            "layer": {
                "name": layer_name,
                "type": "VECTOR",
                "defaultStyle": {
                    "name": "polygon"  # A safe default, will be overwritten by SLD upload
                },
                "resource": {
                    "@class": "featureType",
                    "name": f"{workspace}:{layer_name}"
                },
                "enabled": True
            }
        }
        
        self.main.log_message(f"Publishing '{layer_name}' as a layer in workspace '{workspace}'...")
        layer_pub_resp = requests.put(
            f"{layer_publish_url}/{layer_name}",
            json=layer_payload,
            auth=(username, password),
            headers={"Content-Type": "application/json"}
        )
        
        if layer_pub_resp.status_code in [200, 201]:
            self.main.log_message(f"✓ Successfully published layer '{layer_name}'.")
            return True
        elif layer_pub_resp.status_code == 409:  # Conflict, layer already exists
            self.main.log_message(f"ℹ️ Layer '{layer_name}' already published. Continuing.")
            return True  # Treat as success and continue
        else:
            self.main.log_message(f"❌ Failed to publish layer '{layer_name}': {layer_pub_resp.status_code} - {layer_pub_resp.text}", level=Qgis.Critical)
            return False
    
    def _save_credentials_and_refresh(self, pg_params):
        """
        Save successful PostGIS credentials and refresh workspace content.
        """
        # Save successful PostGIS credentials for future use
        if pg_params['user'] and pg_params['passwd']:
            self.main.postgis_credentials.save_credentials(pg_params, log_callback=self.main.log_message)
        
        # Refresh the workspace content to show the new layer
        self.main.refresh_current_workspace_content()
