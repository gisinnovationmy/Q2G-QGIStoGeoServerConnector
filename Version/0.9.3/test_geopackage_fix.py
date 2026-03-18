"""
Test script to demonstrate the GeoPackage upload fix
"""

def simulate_layer_source_parsing():
    """Simulate how the fixed method will parse layer sources"""
    
    # Example layer sources from your log
    test_sources = [
        "C:/exercise_data/training_data.gpkg|layername=training_data — roads",
        "C:/exercise_data/training_data.gpkg|layername=training_data — schools", 
        "C:/exercise_data/training_data.gpkg|layername=training_data — restaurants",
        "C:/exercise_data/training_data.gpkg|layername=training_data — buildings"
    ]
    
    print("🔧 Testing GeoPackage Layer Name Extraction:")
    print("=" * 60)
    
    for source in test_sources:
        print(f"Source: {source}")
        
        if '|layername=' in source:
            layer_name_param = source.split('|layername=')[1].split('|')[0]
            print(f"✓ Extracted layer name: '{layer_name_param}'")
            
            # Show what will be sent to GeoServer
            data = {'configure': 'first', 'layer': layer_name_param}
            print(f"✓ Upload data: {data}")
        else:
            print("❌ No layername parameter found")
        
        print("-" * 60)

def show_request_difference():
    """Show the difference between old and new requests"""
    
    print("\n🚨 REQUEST COMPARISON:")
    print("=" * 60)
    
    print("❌ OLD REQUEST (Causing 500 error):")
    print("POST /rest/imports/108/tasks")
    print("files = {'file': ('training_data.gpkg', <binary_data>, 'application/octet-stream')}")
    print("data = None  # ← Missing layer specification!")
    
    print("\n✅ NEW REQUEST (Fixed):")
    print("POST /rest/imports/108/tasks") 
    print("files = {'file': ('training_data.gpkg', <binary_data>, 'application/octet-stream')}")
    print("data = {'configure': 'first', 'layer': 'training_data — roads'}  # ← Layer specified!")
    
    print("\n🎯 The 'data' parameter tells GeoServer which layer to import from the multi-layer GeoPackage!")

if __name__ == "__main__":
    simulate_layer_source_parsing()
    show_request_difference()
