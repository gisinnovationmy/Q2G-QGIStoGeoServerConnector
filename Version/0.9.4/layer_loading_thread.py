import requests
from qgis.PyQt.QtCore import QThread, pyqtSignal
from requests.exceptions import Timeout, ConnectionError

class LayerLoadingThread(QThread):
    """Worker thread for loading layers from GeoServer asynchronously."""
    layers_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, url, username, password, workspace=None, parent=None):
        super().__init__(parent)
        self.geoserver_url = url
        self.username = username
        self.password = password
        self.workspace = workspace

    def run(self):
        """Fetch layers from GeoServer REST API."""
        try:
            if self.workspace:
                layers_data = self._fetch_layers_for_workspace(self.workspace)
            else:
                layers_data = self._fetch_layers_for_all_workspaces()
            
            self.layers_loaded.emit(layers_data)

        except (Timeout, ConnectionError) as e:
            self.error_occurred.emit(f"Network error connecting to GeoServer: {e}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                self.error_occurred.emit("Authentication failed. Check credentials.")
            else:
                self.error_occurred.emit(f"HTTP error: {e}")
        except Exception as e:
            self.error_occurred.emit(f"An unexpected error occurred: {e}")

    def _fetch_layers_for_all_workspaces(self):
        """Fetch layers from all available workspaces."""
        response = requests.get(
            f"{self.geoserver_url}/rest/workspaces.json",
            auth=(self.username, self.password),
            timeout=10
        )
        response.raise_for_status()
        workspaces = response.json().get('workspaces', {}).get('workspace', [])
        
        all_layers = []
        for ws in workspaces:
            ws_name = ws.get('name')
            if ws_name:
                try:
                    all_layers.extend(self._fetch_layers_for_workspace(ws_name))
                except Exception as e:
                    # Log or signal a warning, but continue with other workspaces
                    print(f"Could not load layers for workspace '{ws_name}': {e}")
        return all_layers

    def _fetch_layers_for_workspace(self, workspace_name):
        """Fetch layers for a single specified workspace."""
        response = requests.get(
            f"{self.geoserver_url}/rest/workspaces/{workspace_name}/layers.json",
            auth=(self.username, self.password),
            timeout=10
        )
        response.raise_for_status()
        layers = response.json().get('layers', {}).get('layer', [])
        
        # Add workspace prefix to each layer name for uniqueness
        for layer in layers:
            if 'name' in layer:
                layer['name'] = f"{workspace_name}:{layer['name']}"
        return layers
