"""
Shapefile upload module for Q2G QGIS plugin.
Handles conversion of vector layers to Shapefile format and upload to GeoServer.
"""

import os
import tempfile
import shutil
import zipfile
import time
import requests
from qgis.core import QgsVectorLayer, QgsVectorFileWriter, Qgis


def upload_layer_as_shapefile(layer, layer_name, workspace, url, username, password, log_callback=None):
    """
    Upload a vector layer by converting it to a zipped Shapefile and using the GeoServer REST API.
    
    Args:
        layer (QgsVectorLayer): The QGIS vector layer to upload
        layer_name (str): Sanitized name for the layer in GeoServer
        workspace (str): Target GeoServer workspace
        url (str): Base GeoServer URL
        username (str): GeoServer username
        password (str): GeoServer password
        log_callback (callable): Optional logging function
    
    Returns:
        bool: True if upload successful, False otherwise
    """
    def log_message(message, level=Qgis.Info):
        if log_callback:
            log_callback(message, level)
        else:
            print(message)
    
    try:
        if not isinstance(layer, QgsVectorLayer):
            log_message(f"Layer '{layer_name}' is not a vector layer. Cannot export to Shapefile.", level=Qgis.Critical)
            return False

        # Export to a temporary shapefile directory
        tmp_dir = tempfile.mkdtemp(prefix="qgs2gs_shp_")
        shp_path = os.path.join(tmp_dir, f"{layer_name}.shp")
        log_message(f"Exporting layer '{layer.name()}' to Shapefile: {shp_path}")

        try:
            # QGIS API compatibility: writeAsVectorFormat returns (error, newFile) in many versions
            result = QgsVectorFileWriter.writeAsVectorFormat(layer, shp_path, "UTF-8", layer.crs(), "ESRI Shapefile")
            err_code = result[0] if isinstance(result, (list, tuple)) else result
            if hasattr(QgsVectorFileWriter, 'NoError') and err_code != QgsVectorFileWriter.NoError:
                log_message(f"Failed exporting Shapefile for '{layer_name}'. Error code: {err_code}", level=Qgis.Critical)
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return False
        except Exception as e:
            log_message(f"Exception during Shapefile export for '{layer_name}': {e}", level=Qgis.Critical)
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return False

        # Zip the shapefile components
        zip_path = os.path.join(tmp_dir, f"{layer_name}.zip")
        log_message(f"Zipping Shapefile to: {zip_path}")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            base = os.path.splitext(shp_path)[0]
            for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg", ".qpj"]:
                f = base + ext
                if os.path.exists(f):
                    zf.write(f, arcname=os.path.basename(f))

        # Delete existing datastore to overwrite
        ds_name = layer_name
        del_url = f"{url}/rest/workspaces/{workspace}/datastores/{ds_name}?recurse=true"
        try:
            del_resp = requests.delete(del_url, auth=(username, password))
            if del_resp.status_code in [200, 202]:
                log_message(f"Deleted existing datastore '{ds_name}'.")
                time.sleep(1)
        except Exception:
            pass

        # Upload the zip to create datastore and publish layer
        upload_url = f"{url}/rest/workspaces/{workspace}/datastores/{ds_name}/file.shp?update=overwrite"
        log_message(f"Uploading Shapefile to: {upload_url}")
        with open(zip_path, 'rb') as fh:
            headers = {"Content-Type": "application/zip"}
            resp = requests.put(upload_url, data=fh, headers=headers, auth=(username, password))

        log_message(f"Shapefile upload response: {resp.status_code} - {resp.text[:300]}...")
        if resp.status_code not in [200, 201, 202]:
            log_message(f"Failed to upload Shapefile for '{layer_name}'.", level=Qgis.Critical)
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return False

        return True
    finally:
        # Cleanup temp directory
        if 'tmp_dir' in locals() and os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
