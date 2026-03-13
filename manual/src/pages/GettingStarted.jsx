import React from 'react';

const GettingStarted = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">🚀 Getting Started</h1>
        <p className="page-subtitle">Learn the basics of GeoServerConnector</p>
      </div>

      <div className="content">
        <section>
          <h2>What is GeoServerConnector?</h2>
          <p>
            GeoServerConnector is a powerful QGIS plugin that enables seamless integration between QGIS and GeoServer.
            It allows you to upload layers, manage styles, and control your geospatial data directly from QGIS.
          </p>
        </section>

        <section>
          <h2>Key Features</h2>
          <ul>
            <li>Upload multiple layer formats (Shapefile, GeoPackage, PostGIS, GeoTIFF, etc.)</li>
            <li>Manage SLD styles and apply them to layers</li>
            <li>Create and manage GeoServer workspaces</li>
            <li>Preview layers before uploading</li>
            <li>Batch upload capabilities</li>
            <li>PostGIS integration</li>
            <li>Advanced error handling and logging</li>
          </ul>
        </section>

        <section>
          <h2>System Requirements</h2>
          <ul>
            <li>QGIS 3.x or later</li>
            <li>GeoServer 2.20 or later</li>
            <li>Python 3.6+</li>
            <li>Network access to GeoServer</li>
          </ul>
        </section>

        <section>
          <h2>Quick Start</h2>
          <ol>
            <li>Install the GeoServerConnector plugin in QGIS</li>
            <li>Configure your GeoServer connection</li>
            <li>Select layers from your QGIS project</li>
            <li>Click "Upload" to publish to GeoServer</li>
            <li>Manage styles and workspaces as needed</li>
          </ol>
        </section>

        <section>
          <h2>Next Steps</h2>
          <p>
            Ready to get started? Check out the <a href="/installation">Installation</a> guide to set up the plugin,
            or jump to <a href="/configuration">Configuration</a> to connect to your GeoServer instance.
          </p>
        </section>
      </div>
    </div>
  );
};

export default GettingStarted;
