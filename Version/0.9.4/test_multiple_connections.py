#!/usr/bin/env python3
"""
Test script to verify multiple PostGIS connections can be saved and loaded.
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

def test_multiple_connections():
    """Test saving and loading multiple PostGIS connections."""
    
    print("\n" + "="*70)
    print("Multiple PostGIS Connections Test")
    print("="*70)
    
    # Initialize credentials manager
    manager = PostGISCredentialsManager()
    print(f"\n✓ Credentials manager initialized")
    print(f"  Config path: {manager.config_path}")
    
    # Test data - multiple connections
    connections = [
        {
            'name': 'Production DB',
            'host': 'localhost',
            'port': 5432,
            'database': 'postgres',
            'user': 'postgres',
            'passwd': 'postgres_pass',
            'schema': 'public',
            'table': ''
        },
        {
            'name': 'Jengka Database',
            'host': 'localhost',
            'port': 5432,
            'database': 'jengka',
            'user': 'lendu',
            'passwd': 'lendu_pass',
            'schema': 'public',
            'table': ''
        },
        {
            'name': 'Remote Server',
            'host': '192.168.1.100',
            'port': 5432,
            'database': 'mydb',
            'user': 'admin',
            'passwd': 'admin_pass',
            'schema': 'public',
            'table': ''
        }
    ]
    
    # Save all connections
    print(f"\n--- Saving {len(connections)} Connections ---")
    for i, conn in enumerate(connections, 1):
        print(f"\n{i}. Saving: {conn['name']}")
        print(f"   Connection: {conn['user']}@{conn['host']}:{conn['port']}/{conn['database']}")
        
        success = manager.save_credentials(conn)
        
        if success:
            print(f"   ✓ Saved successfully")
        else:
            print(f"   ✗ Failed to save")
            return False
    
    # Verify file content
    print(f"\n--- Verifying File Content ---")
    if os.path.exists(manager.config_path):
        file_size = os.path.getsize(manager.config_path)
        print(f"✓ Config file exists: {manager.config_path}")
        print(f"  File size: {file_size} bytes")
        
        # Read and display file content
        print(f"\n--- File Content ---")
        try:
            with open(manager.config_path, 'r') as f:
                content = f.read()
                print(content)
        except Exception as e:
            print(f"✗ Error reading file: {str(e)}")
            return False
    else:
        print(f"✗ Config file does not exist")
        return False
    
    # List all saved connections
    print(f"\n--- Listing All Saved Connections ---")
    saved_connections = manager.list_saved_connections()
    
    if saved_connections:
        print(f"✓ Found {len(saved_connections)} saved connection(s)")
        for i, conn in enumerate(saved_connections, 1):
            print(f"\n  {i}. {conn['database']}@{conn['host']}:{conn['port']}")
            print(f"     User: {conn['user']}")
            print(f"     Schema: {conn['schema']}")
    else:
        print(f"✗ No saved connections found")
        return False
    
    # Verify each connection can be loaded
    print(f"\n--- Loading Each Connection ---")
    for i, conn in enumerate(connections, 1):
        print(f"\n{i}. Loading: {conn['name']}")
        
        loaded = manager.load_credentials(
            conn['database'],
            conn['host'],
            conn['port']
        )
        
        if loaded:
            print(f"   ✓ Loaded successfully")
            print(f"     User: {loaded.get('user')}")
            print(f"     Database: {loaded.get('database')}")
            
            # Verify values match
            if loaded.get('user') != conn['user']:
                print(f"   ✗ User mismatch: expected '{conn['user']}', got '{loaded.get('user')}'")
                return False
        else:
            print(f"   ✗ Failed to load")
            return False
    
    # Verify connection count
    print(f"\n--- Connection Count Verification ---")
    final_connections = manager.list_saved_connections()
    expected_count = len(connections)
    actual_count = len(final_connections)
    
    print(f"Expected connections: {expected_count}")
    print(f"Actual connections: {actual_count}")
    
    if actual_count == expected_count:
        print(f"✓ Connection count matches!")
    else:
        print(f"✗ Connection count mismatch!")
        return False
    
    print(f"\n" + "="*70)
    print("✓ All tests passed! Multiple connections working correctly!")
    print("="*70 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        success = test_multiple_connections()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
