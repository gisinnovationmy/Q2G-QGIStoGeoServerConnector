import React from 'react';
import '../styles/Pages.css';

const BeforeYouStart = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">⚠️ Before You Start</h1>
        <p className="page-subtitle">Essential setup requirements and prerequisites</p>
      </div>

      <div className="content">
        <section>
          <h2>🌐 Web Components Requirements</h2>
          <p>
            The Preview feature in GeoServerConnector requires additional web components to display interactive maps.
            These components are automatically installed when you first use the Preview feature.
          </p>
          
          <h3>Required Components:</h3>
          <ul>
            <li>
              <strong>PyQtWebEngine</strong> - Required for displaying the preview map
              <ul>
                <li>Automatically installed on first use</li>
                <li>Requires internet connection for download (~50-100 MB)</li>
                <li>QGIS must be restarted after installation</li>
              </ul>
            </li>
            <li>
              <strong>OpenLayers</strong> - Map rendering library (included locally)
              <ul>
                <li>Pre-installed with the plugin</li>
                <li>No additional setup needed</li>
              </ul>
            </li>
            <li>
              <strong>Cesium.js</strong> - 3D visualization support (included locally)
              <ul>
                <li>Pre-installed with the plugin</li>
                <li>Optional for advanced visualization</li>
              </ul>
            </li>
          </ul>

          <div className="info-card info-warning">
            <h4>⚠️ Important</h4>
            <p>
              When you first try to open the Preview feature, if PyQtWebEngine is not installed, 
              a dialog will appear with an "Install" button. Click it to automatically install the required component.
              <strong> You need an active internet connection for this to work.</strong>
            </p>
          </div>
        </section>

        <section>
          <h2>🔒 GeoServer CORS Configuration</h2>
          <p>
            CORS (Cross-Origin Resource Sharing) must be enabled on your GeoServer for the Preview feature 
            to work properly. This allows the web browser to request data from GeoServer.
          </p>

          <h3>Why CORS is Needed:</h3>
          <ul>
            <li>The Preview map runs in a web browser context</li>
            <li>Browser security policies prevent cross-origin requests by default</li>
            <li>CORS allows the map to fetch layers and styles from GeoServer</li>
          </ul>

          <h3>How to Enable CORS:</h3>
          <ol>
            <li>In GeoServerConnector, enter your GeoServer URL, username, and password</li>
            <li>Click the <strong>"Others"</strong> section in the plugin</li>
            <li>Click <strong>"Enable CORS in GeoServer"</strong> button</li>
            <li>The plugin will automatically configure CORS on your GeoServer</li>
            <li>If successful, you'll see a confirmation message</li>
          </ol>

          <h3>Manual CORS Configuration (if automatic fails):</h3>
          <p>
            If the automatic CORS setup fails, you can manually enable it:
          </p>
          <ol>
            <li>Access your GeoServer admin console</li>
            <li>Go to <strong>Settings → Global Settings</strong></li>
            <li>Look for CORS configuration options</li>
            <li>Enable CORS and set allowed origins to <code>*</code></li>
            <li>Save and restart GeoServer</li>
          </ol>

          <div className="info-card info-note">
            <h4>💡 Tip</h4>
            <p>
              CORS configuration is only needed for the Preview feature. 
              Layer upload and other features work without CORS enabled.
            </p>
          </div>
        </section>

        <section>
          <h2>📦 GeoServer Importer Extension</h2>
          <p>
            The Importer extension is a powerful GeoServer module that handles file uploads and layer creation.
            GeoServerConnector uses this extension to upload various layer formats.
          </p>

          <h3>Why the Importer Extension is Important:</h3>
          <ul>
            <li>Handles multiple file formats (Shapefile, GeoTIFF, GeoJSON, etc.)</li>
            <li>Automatically creates datastores and layers</li>
            <li>Provides reliable error handling and task management</li>
            <li>Enables batch uploads of multiple files</li>
          </ul>

          <h3>Supported File Formats:</h3>
          <ul>
            <li><strong>Vector Formats:</strong> Shapefile (.shp), GeoPackage (.gpkg), GeoJSON (.geojson)</li>
            <li><strong>Raster Formats:</strong> GeoTIFF (.tif, .tiff), PNG, JPEG</li>
            <li><strong>Database:</strong> PostGIS layers (via native datastore)</li>
            <li><strong>Other:</strong> KML, CSV, and more</li>
          </ul>

          <h3>How to Check if Importer is Installed:</h3>
          <ol>
            <li>Open GeoServer admin console</li>
            <li>Go to <strong>REST API → /rest/imports</strong></li>
            <li>If you see a response, the Importer extension is installed</li>
          </ol>

          <h3>Installing the Importer Extension (if needed):</h3>
          <ol>
            <li>Download the Importer extension matching your GeoServer version</li>
            <li>Extract it to your GeoServer <code>WEB-INF/lib</code> folder</li>
            <li>Restart GeoServer</li>
            <li>Verify installation via REST API</li>
          </ol>

          <div className="info-card info-warning">
            <h4>⚠️ Important</h4>
            <p>
              Without the Importer extension, you cannot upload layers using GeoServerConnector.
              Make sure it's installed and enabled on your GeoServer instance.
            </p>
          </div>
        </section>

        <section>
          <h2>✅ Pre-Flight Checklist</h2>
          <p>Before you start using GeoServerConnector, make sure you have:</p>
          
          <div className="checklist">
            <div className="checklist-item">
              <input type="checkbox" id="check1" disabled />
              <label htmlFor="check1">QGIS 3.x or later installed</label>
            </div>
            <div className="checklist-item">
              <input type="checkbox" id="check2" disabled />
              <label htmlFor="check2">GeoServer 2.20 or later running and accessible</label>
            </div>
            <div className="checklist-item">
              <input type="checkbox" id="check3" disabled />
              <label htmlFor="check3">GeoServer Importer extension installed</label>
            </div>
            <div className="checklist-item">
              <input type="checkbox" id="check4" disabled />
              <label htmlFor="check4">GeoServer admin credentials (username/password)</label>
            </div>
            <div className="checklist-item">
              <input type="checkbox" id="check5" disabled />
              <label htmlFor="check5">Network access to GeoServer (firewall rules)</label>
            </div>
            <div className="checklist-item">
              <input type="checkbox" id="check6" disabled />
              <label htmlFor="check6">Internet connection (for PyQtWebEngine installation)</label>
            </div>
            <div className="checklist-item">
              <input type="checkbox" id="check7" disabled />
              <label htmlFor="check7">CORS enabled on GeoServer (for Preview feature)</label>
            </div>
          </div>
        </section>

        <section>
          <h2>🚀 Ready to Start?</h2>
          <p>
            Once you've verified all the requirements above, you're ready to:
          </p>
          <ol>
            <li>Install the GeoServerConnector plugin</li>
            <li>Configure your GeoServer connection</li>
            <li>Start uploading layers!</li>
          </ol>
          <p>
            Head over to the <a href="/installation">Installation</a> guide to get started.
          </p>
        </section>

        <section>
          <h2>❓ Still Have Questions?</h2>
          <ul>
            <li>Check the <a href="/faq">FAQ</a> section for common questions</li>
            <li>Visit <a href="/troubleshooting">Troubleshooting</a> for solutions to common issues</li>
            <li>See <a href="/configuration">Configuration</a> for detailed setup instructions</li>
          </ul>
        </section>
      </div>
    </div>
  );
};

export default BeforeYouStart;
