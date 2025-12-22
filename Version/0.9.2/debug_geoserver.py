"""
Debug script to check GeoServer Importer API availability
"""
import requests

def check_geoserver_importer(url, username, password):
    """Check if GeoServer Importer extension is available"""
    
    # Test 1: Check if imports endpoint exists
    imports_url = f"{url}/rest/imports"
    try:
        response = requests.get(imports_url, auth=(username, password))
        print(f"Imports endpoint status: {response.status_code}")
        if response.status_code == 200:
            print("✓ Importer extension is available")
        elif response.status_code == 404:
            print("❌ Importer extension NOT installed")
        else:
            print(f"⚠ Unexpected response: {response.text}")
    except Exception as e:
        print(f"❌ Connection error: {e}")
    
    # Test 2: Try to create a test import job
    try:
        create_url = f"{url}/rest/imports"
        data = {"import": {"targetWorkspace": {"name": "test"}}}
        response = requests.post(create_url, json=data, auth=(username, password))
        print(f"Create import job status: {response.status_code}")
        if response.status_code in [200, 201]:
            print("✓ Can create import jobs")
        else:
            print(f"❌ Cannot create import jobs: {response.text}")
    except Exception as e:
        print(f"❌ Error creating import job: {e}")

# Usage:
# check_geoserver_importer("http://localhost:8080/geoserver", "admin", "geoserver")
