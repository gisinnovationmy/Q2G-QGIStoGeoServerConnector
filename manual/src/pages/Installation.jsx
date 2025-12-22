import React from 'react';

const Installation = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">📦 Installation</h1>
        <p className="page-subtitle">Step-by-step installation guide</p>
      </div>

      <div className="content">
        <section>
          <h2>Installing GeoServerConnector</h2>
          <p>Follow these steps to install the GeoServerConnector plugin in QGIS:</p>
        </section>

        <section>
          <h3>Method 1: From QGIS Plugin Repository</h3>
          <ol>
            <li>Open QGIS</li>
            <li>Go to Plugins → Manage and Install Plugins</li>
            <li>Search for "GeoServerConnector"</li>
            <li>Click "Install Plugin"</li>
            <li>Restart QGIS</li>
          </ol>
        </section>

        <section>
          <h3>Method 2: Manual Installation</h3>
          <ol>
            <li>Download the plugin from the repository</li>
            <li>Extract the ZIP file</li>
            <li>Copy the folder to your QGIS plugins directory:
              <ul>
                <li><strong>Windows:</strong> <code>C:\Users\[username]\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins</code></li>
                <li><strong>macOS:</strong> <code>~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins</code></li>
                <li><strong>Linux:</strong> <code>~/.local/share/QGIS/QGIS3/profiles/default/python/plugins</code></li>
              </ul>
            </li>
            <li>Restart QGIS</li>
          </ol>
        </section>

        <section>
          <h3>Activating the Plugin</h3>
          <ol>
            <li>Go to Plugins → Manage and Install Plugins</li>
            <li>Find GeoServerConnector in the list</li>
            <li>Check the checkbox to enable it</li>
            <li>The plugin will appear in the Plugins menu</li>
          </ol>
        </section>

        <section>
          <h3>Verifying Installation</h3>
          <p>After installation, you should see:</p>
          <ul>
            <li>A new menu item "GeoServerConnector" in the Plugins menu</li>
            <li>A toolbar icon for quick access</li>
            <li>The plugin dialog when you click on it</li>
          </ul>
        </section>

        <section>
          <h3>Troubleshooting Installation</h3>
          <p>If the plugin doesn't appear:</p>
          <ul>
            <li>Check that you're using QGIS 3.x or later</li>
            <li>Verify the plugin folder is in the correct location</li>
            <li>Restart QGIS completely</li>
            <li>Check the QGIS log for error messages</li>
          </ul>
        </section>
      </div>
    </div>
  );
};

export default Installation;
