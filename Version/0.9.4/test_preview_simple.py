"""
Simple test for OpenLayers preview dialog
Run this to test if the preview components are working.
"""

import os
import sys
import importlib.util

# Ensure we load modules from the same folder as this file
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if _CURRENT_DIR not in sys.path:
    sys.path.insert(0, _CURRENT_DIR)

def _load_local_module(module_name):
    """Load a module from the same directory as this file."""
    module_file = os.path.join(_CURRENT_DIR, f"{module_name}.py")
    if not os.path.exists(module_file):
        raise ImportError(f"Module not found: {module_file}")
    spec = importlib.util.spec_from_file_location(module_name, module_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for: {module_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_preview_components():
    """Test if all preview components are available"""
    
    print("🔍 Testing OpenLayers Preview Components...")
    print("=" * 50)
    
    # Test 1: WebEngine
    try:
        # Try PyQt6 first (QGIS 3.28+)
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebChannel import QWebChannel
        print("✅ WebEngine components: Available (PyQt6)")
    except ImportError:
        try:
            # Fallback to PyQt5 (QGIS 3.16-3.26)
            from PyQt5.QtWebEngineWidgets import QWebEngineView
            from PyQt5.QtWebChannel import QWebChannel
            print("✅ WebEngine components: Available (PyQt5)")
        except ImportError as e:
            print(f"❌ WebEngine components: Missing - {e}")
            return False
    
    # Test 2: Panel modules
    try:
        base_dir = _CURRENT_DIR
        
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
        _lp = _load_local_module("left_panel")
        LeftPanel = _lp.LeftPanel
        print("✅ LeftPanel import: Success")
    except ImportError as e:
        print(f"❌ LeftPanel import: Failed - {e}")
    
    try:
        _rp = _load_local_module("right_panel")
        RightPanel = _rp.RightPanel
        print("✅ RightPanel import: Success")
    except ImportError as e:
        print(f"❌ RightPanel import: Failed - {e}")
    
    try:
        _pv = _load_local_module("preview")
        PreviewDialog = _pv.PreviewDialog
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
        from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QLabel
        try:
            from PyQt6.QtWebEngineWidgets import QWebEngineView
        except ImportError:
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
