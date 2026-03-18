"""
Simple test for OpenLayers preview dialog
Run this to test if the preview components are working.
"""

def test_preview_components():
    """Test if all preview components are available"""
    
    print("🔍 Testing OpenLayers Preview Components...")
    print("=" * 50)
    
    # Test 1: WebEngine
    try:
        from PyQt5.QtWebEngineWidgets import QWebEngineView
        from PyQt5.QtWebChannel import QWebChannel
        print("✅ WebEngine components: Available")
    except ImportError as e:
        print(f"❌ WebEngine components: Missing - {e}")
        return False
    
    # Test 2: Panel modules
    try:
        import os
        base_dir = os.path.dirname(__file__)
        
        left_panel_path = os.path.join(base_dir, 'left_panel.py')
        right_panel_path = os.path.join(base_dir, 'right_panel.py')
        preview_path = os.path.join(base_dir, 'preview.py')
        
        if os.path.exists(left_panel_path):
            print("✅ left_panel.py: Found")
        else:
            print("❌ left_panel.py: Missing")
            
        if os.path.exists(right_panel_path):
            print("✅ right_panel.py: Found")
        else:
            print("❌ right_panel.py: Missing")
            
        if os.path.exists(preview_path):
            print("✅ preview.py: Found")
        else:
            print("❌ preview.py: Missing")
            
    except Exception as e:
        print(f"❌ File check failed: {e}")
    
    # Test 3: Import modules
    try:
        from .left_panel import LeftPanel
        print("✅ LeftPanel import: Success")
    except ImportError as e:
        print(f"❌ LeftPanel import: Failed - {e}")
    
    try:
        from .right_panel import RightPanel
        print("✅ RightPanel import: Success")
    except ImportError as e:
        print(f"❌ RightPanel import: Failed - {e}")
    
    try:
        from .preview import PreviewDialog
        print("✅ PreviewDialog import: Success")
    except ImportError as e:
        print(f"❌ PreviewDialog import: Failed - {e}")
    
    # Test 4: QGIS components
    try:
        from qgis.core import QgsApplication, QgsMessageLog, Qgis
        print("✅ QGIS core components: Available")
    except ImportError as e:
        print(f"❌ QGIS core components: Missing - {e}")
    
    print("=" * 50)
    print("✅ Component test completed")
    return True

def create_minimal_preview_test():
    """Create a minimal preview dialog for testing"""
    
    print("\n🧪 Creating Minimal Preview Test...")
    
    try:
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel
        from PyQt5.QtWebEngineWidgets import QWebEngineView
        
        class MinimalPreview(QDialog):
            def __init__(self):
                super().__init__()
                self.setWindowTitle("Minimal Preview Test")
                self.resize(800, 600)
                
                layout = QVBoxLayout()
                
                # Add a simple label
                label = QLabel("Testing WebEngine View:")
                layout.addWidget(label)
                
                # Add WebEngine view
                self.web_view = QWebEngineView()
                self.web_view.setHtml("""
                <html>
                <head><title>Test</title></head>
                <body>
                    <h1>WebEngine Test</h1>
                    <p>If you can see this, WebEngine is working!</p>
                    <div id="map" style="width:100%; height:300px; background:#eee; border:1px solid #ccc;">
                        <p style="text-align:center; padding:100px;">Map would go here</p>
                    </div>
                </body>
                </html>
                """)
                layout.addWidget(self.web_view)
                
                self.setLayout(layout)
        
        # Create and show test dialog
        test_dialog = MinimalPreview()
        print("✅ Minimal preview dialog created successfully")
        print("💡 You can call test_dialog.show() to display it")
        return test_dialog
        
    except Exception as e:
        print(f"❌ Minimal preview test failed: {e}")
        return None

if __name__ == "__main__":
    test_preview_components()
    create_minimal_preview_test()
