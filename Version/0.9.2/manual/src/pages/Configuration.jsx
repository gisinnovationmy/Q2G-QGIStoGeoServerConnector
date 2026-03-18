import React from 'react';

const Configuration = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">⚙️ Configuration</h1>
        <p className="page-subtitle">Configure your GeoServer connection</p>
      </div>

      <div className="content">
        <section>
          <h2>GeoServer Connection Setup</h2>
          <p>Configure the connection to your GeoServer instance:</p>
        </section>

        <section>
          <h3>Basic Configuration</h3>
          <ol>
            <li>Open the GeoServerConnector plugin</li>
            <li>Enter your GeoServer URL (e.g., <code>http://localhost:8080/geoserver</code>)</li>
            <li>Enter your username and password</li>
            <li>Click "Connect" to verify the connection</li>
          </ol>
        </section>

        <section>
          <h3>Authentication</h3>
          <p>The plugin supports:</p>
          <ul>
            <li>Basic authentication (username/password)</li>
            <li>QGIS authentication configurations</li>
            <li>Saved credentials for convenience</li>
          </ul>
        </section>

        <section>
          <h3>Workspace Selection</h3>
          <p>After connecting, select the workspace where you want to upload layers:</p>
          <ul>
            <li>Choose from existing workspaces</li>
            <li>Create a new workspace if needed</li>
            <li>The selected workspace will be used for all uploads</li>
          </ul>
        </section>

        <section>
          <h3>Plugin Settings</h3>
          <p>Configure plugin behavior:</p>
          <ul>
            <li><strong>Auto-overwrite layers:</strong> Automatically replace existing layers</li>
            <li><strong>Overwrite SLD:</strong> Replace existing styles</li>
            <li><strong>Show upload progress:</strong> Display real-time upload status</li>
          </ul>
        </section>

        <section>
          <h3>Testing Your Connection</h3>
          <p>To verify your configuration:</p>
          <ol>
            <li>Click the "Connect" button</li>
            <li>Check the log for connection status</li>
            <li>Verify that workspaces are loaded</li>
            <li>You're ready to upload layers!</li>
          </ol>
        </section>
      </div>
    </div>
  );
};

export default Configuration;
