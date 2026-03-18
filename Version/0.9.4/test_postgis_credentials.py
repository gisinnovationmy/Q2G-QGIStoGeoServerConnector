#!/usr/bin/env python3
"""
Test script to verify PostGIS credentials are being saved correctly.
Run this from the QGIS Python console or as a standalone script.
"""

import os
import sys
import configparser

# Add the plugin directory to the path
plugin_dir = os.path.dirname(os.path.abspath(__file__))
if plugin_dir not in sys.path:
    sys.path.insert(0, plugin_dir)

from postgis_credentials import PostGISCredentialsManager

def test_postgis_credentials():
    """Test saving and loading PostGIS credentials."""
    
    print("\n" + "="*60)
    print("PostGIS Credentials Test")
    print("="*60)
    
    # Initialize credentials manager
    manager = PostGISCredentialsManager()
    print(f"\n✓ Credentials manager initialized")
    print(f"  Config path: {manager.config_path}")
    print(f"  Config file exists: {os.path.exists(manager.config_path)}")
    
    # Test data
    test_credentials = {
        'host': 'localhost',
        'port': 5432,
        'database': 'test_db',
        'user': 'test_user',
        'passwd': 'test_password',
        'schema': 'public',
        'table': 'test_table'
    }
    
    print(f"\n--- Test 1: Save Credentials ---")
    print(f"Saving credentials for: {test_credentials['user']}@{test_credentials['host']}:{test_credentials['port']}/{test_credentials['database']}")
    
    success = manager.save_credentials(test_credentials, log_callback=print)
    
    if success:
        print(f"✓ Credentials saved successfully")
    else:
        print(f"✗ Failed to save credentials")
        return False
    
    # Verify file exists and has content
    if os.path.exists(manager.config_path):
        file_size = os.path.getsize(manager.config_path)
        print(f"✓ Config file exists: {manager.config_path}")
        print(f"  File size: {file_size} bytes")
    else:
        print(f"✗ Config file does not exist: {manager.config_path}")
        return False
    
    # Read and display file content
    print(f"\n--- File Content ---")
    try:
        with open(manager.config_path, 'r') as f:
            content = f.read()
            print(content)
    except Exception as e:
        print(f"✗ Error reading file: {str(e)}")
        return False
    
    # Test loading credentials
    print(f"\n--- Test 2: Load Credentials ---")
    loaded_creds = manager.load_credentials(
        test_credentials['database'],
        test_credentials['host'],
        test_credentials['port'],
        log_callback=print
    )
    
    if loaded_creds:
        print(f"✓ Credentials loaded successfully")
        print(f"  Host: {loaded_creds.get('host')}")
        print(f"  Port: {loaded_creds.get('port')}")
        print(f"  Database: {loaded_creds.get('database')}")
        print(f"  User: {loaded_creds.get('user')}")
        print(f"  Schema: {loaded_creds.get('schema')}")
        
        # Verify values match
        if loaded_creds.get('user') == test_credentials['user']:
            print(f"✓ User matches: {loaded_creds.get('user')}")
        else:
            print(f"✗ User mismatch: expected '{test_credentials['user']}', got '{loaded_creds.get('user')}'")
            return False
    else:
        print(f"✗ Failed to load credentials")
        return False
    
    # Test listing connections
    print(f"\n--- Test 3: List Saved Connections ---")
    connections = manager.list_saved_connections(log_callback=print)
    
    if connections:
        print(f"✓ Found {len(connections)} saved connection(s)")
        for i, conn in enumerate(connections, 1):
            print(f"  {i}. {conn['database']}@{conn['host']}:{conn['port']} (User: {conn['user']})")
    else:
        print(f"✗ No saved connections found")
        return False
    
    print(f"\n" + "="*60)
    print("✓ All tests passed!")
    print("="*60 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        success = test_postgis_credentials()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
