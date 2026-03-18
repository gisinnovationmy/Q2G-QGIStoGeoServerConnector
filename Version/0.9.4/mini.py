# mini.py - Minimal WebEngine Test Dialog
"""
Minimal test dialog to verify QWebEngineView works on the deployment machine.
This isolates WebEngine from all other plugin code.
"""

from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit
from qgis.PyQt.QtCore import Qt, QUrl, pyqtSlot
from qgis.PyQt.QtGui import QFont
from qgis.core import Qgis

# Try to import WebEngine
WEBENGINE_OK = False
QWebEngineView = None

try:
    # Try PyQt6 first (QGIS 3.28+)
    from PyQt6.QtWebEngineWidgets import QWebEngineView as _QWebEngineView
    QWebEngineView = _QWebEngineView
    WEBENGINE_OK = True
except ImportError:
    try:
        # Fallback to PyQt5 (QGIS 3.16-3.26)
        from PyQt5.QtWebEngineWidgets import QWebEngineView as _QWebEngineView
        QWebEngineView = _QWebEngineView
        WEBENGINE_OK = True
    except ImportError as e:
        print(f"WebEngine import failed: {e}")


class MiniWebEngineDialog(QDialog):
    """Minimal WebEngine test dialog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mini WebEngine Test")
        self.setMinimumSize(900, 700)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)
        
        self.web_view = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Status log
        self.status_log = QTextEdit()
        self.status_log.setReadOnly(True)
        self.status_log.setMaximumHeight(150)
        self.status_log.setStyleSheet("QTextEdit { font-family: Consolas; font-size: 10px; background: #1e1e1e; color: #00ff00; }")
        layout.addWidget(self.status_log)
        
        self._log(f"WEBENGINE_OK = {WEBENGINE_OK}")
        self._log(f"QWebEngineView = {QWebEngineView}")
        
        if not WEBENGINE_OK or QWebEngineView is None:
            self._log("FAILED: WebEngine not available!")
            label = QLabel("WebEngine not available")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
            return
        
        # Test buttons
        btn_layout = QVBoxLayout()
        
        btn_google = QPushButton("Test 1: Load Google")
        btn_google.clicked.connect(lambda: self._load_url("https://www.google.com"))
        btn_layout.addWidget(btn_google)
        
        btn_gis = QPushButton("Test 2: Load gis.com.my")
        btn_gis.clicked.connect(lambda: self._load_url("http://www.gis.com.my"))
        btn_layout.addWidget(btn_gis)
        
        btn_cdn = QPushButton("Test 3: Load OpenLayers CDN JS")
        btn_cdn.clicked.connect(lambda: self._load_url("https://cdn.jsdelivr.net/gh/openlayers/openlayers.github.io@master/en/v6.5.0/build/ol.js"))
        btn_layout.addWidget(btn_cdn)
        
        btn_html = QPushButton("Test 4: Load Simple HTML")
        btn_html.clicked.connect(self._load_simple_html)
        btn_layout.addWidget(btn_html)
        
        btn_ol = QPushButton("Test 5: Load OpenLayers Map HTML")
        btn_ol.clicked.connect(self._load_openlayers_html)
        btn_layout.addWidget(btn_ol)
        
        layout.addLayout(btn_layout)
        
        # Create WebEngineView
        self._log("Creating QWebEngineView...")
        try:
            self.web_view = QWebEngineView()
            self._log("QWebEngineView created successfully")
            
            # Enable local content to access remote URLs (CDN, etc.)
            from PyQt6.QtWebEngineCore import QWebEngineSettings
            settings = self.web_view.page().settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            self._log("WebEngine settings: LocalContentCanAccessRemoteUrls=True")
            
            self.web_view.loadStarted.connect(self._on_load_started)
            self.web_view.loadProgress.connect(self._on_load_progress)
            self.web_view.loadFinished.connect(self._on_load_finished)
            self._log("Signals connected")
            
            layout.addWidget(self.web_view)
            self._log("WebView added to layout - ready for testing")
        except Exception as e:
            self._log(f"FAILED to create QWebEngineView: {e}")
    
    def _log(self, message):
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.status_log.append(f"[{ts}] {message}")
        from qgis.PyQt.QtWidgets import QApplication
        QApplication.processEvents()
    
    def _load_url(self, url):
        if self.web_view is None:
            self._log("Cannot load - web_view is None")
            return
        self._log(f"Loading URL: {url}")
        self.web_view.setUrl(QUrl(url))
    
    def _load_simple_html(self):
        if self.web_view is None:
            self._log("Cannot load - web_view is None")
            return
        self._log("Loading simple HTML...")
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Simple Test</title></head>
        <body style="background:#333;color:#0f0;font-family:monospace;padding:20px;">
            <h1>WebEngine Works!</h1>
            <p>If you see this, basic HTML loading is working.</p>
            <p>Time: <span id="time"></span></p>
            <script>
                document.getElementById('time').textContent = new Date().toISOString();
                console.log('JavaScript executed successfully');
            </script>
        </body>
        </html>
        """
        self.web_view.setHtml(html, QUrl.fromLocalFile("/"))
    
    def _load_openlayers_html(self):
        if self.web_view is None:
            self._log("Cannot load - web_view is None")
            return
        self._log("Loading OpenLayers HTML from CDN (using fetch + eval)...")
        # Use fetch() to load script content and eval() it - more reliable than dynamic script tags
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>OpenLayers Test</title>
            <meta http-equiv="Content-Security-Policy" content="default-src * 'unsafe-inline' 'unsafe-eval'; script-src * 'unsafe-inline' 'unsafe-eval'; connect-src *; img-src * data: blob:;">
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/openlayers/openlayers.github.io@master/en/v6.5.0/css/ol.css">
            <style>
                html, body, #map { margin: 0; padding: 0; width: 100%; height: 100%; }
                #status { position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.7); color: #0f0; padding: 10px; font-family: monospace; z-index: 1000; max-width: 400px; }
            </style>
        </head>
        <body>
            <div id="status">Loading OpenLayers via fetch()...</div>
            <div id="map"></div>
            <script>
                var status = document.getElementById('status');
                var olUrl = 'https://cdn.jsdelivr.net/gh/openlayers/openlayers.github.io@master/en/v6.5.0/build/ol.js';
                
                status.innerHTML += '<br>Fetching: ' + olUrl.substring(0, 50) + '...';
                
                fetch(olUrl)
                    .then(function(response) {
                        status.innerHTML += '<br>Response status: ' + response.status;
                        if (!response.ok) throw new Error('HTTP ' + response.status);
                        return response.text();
                    })
                    .then(function(scriptText) {
                        status.innerHTML += '<br>Script loaded: ' + scriptText.length + ' bytes';
                        status.innerHTML += '<br>Evaluating script...';
                        eval(scriptText);
                        status.innerHTML += '<br>Script evaluated!';
                        
                        if (typeof ol === 'undefined') {
                            throw new Error('ol is still undefined after eval');
                        }
                        status.innerHTML += '<br>ol object exists!';
                        
                        var map = new ol.Map({
                            target: 'map',
                            layers: [
                                new ol.layer.Tile({
                                    source: new ol.source.OSM()
                                })
                            ],
                            view: new ol.View({
                                center: ol.proj.fromLonLat([101.6869, 3.1390]),
                                zoom: 10
                            })
                        });
                        status.innerHTML += '<br>Map created!';
                        setTimeout(function() { status.style.display = 'none'; }, 3000);
                    })
                    .catch(function(error) {
                        status.innerHTML += '<br>ERROR: ' + error.message;
                        status.style.color = 'red';
                        console.error('Fetch error:', error);
                    });
            </script>
        </body>
        </html>
        """
        # Use https base URL to allow cross-origin fetch
        self.web_view.setHtml(html, QUrl("https://localhost/"))
    
    @pyqtSlot()
    def _on_load_started(self):
        self._log("loadStarted signal received")
    
    @pyqtSlot(int)
    def _on_load_progress(self, progress):
        self._log(f"loadProgress: {progress}%")
    
    @pyqtSlot(bool)
    def _on_load_finished(self, ok):
        self._log(f"loadFinished: success={ok}")
        if self.web_view:
            self._log(f"  URL: {self.web_view.url().toString()}")
            self._log(f"  Title: {self.web_view.title()}")
        if ok:
            self._log("SUCCESS!")
        else:
            self._log("FAILED - check network/firewall")


def open_mini_dialog(parent=None):
    """Open the mini WebEngine test dialog."""
    dialog = MiniWebEngineDialog(parent)
    dialog.show()
    return dialog
