import React from 'react';

const LayerUpload = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">📤 Layer Upload</h1>
        <p className="page-subtitle">Upload your layers to GeoServer</p>
      </div>

      <div className="content">
        <section>
          <h2>Uploading Layers</h2>
          <p>The GeoServerConnector plugin supports uploading various layer formats to GeoServer.</p>
        </section>

        <section>
          <h3>Supported Formats</h3>
          <ul>
            <li><strong>Shapefile (.shp):</strong> Vector data format</li>
            <li><strong>GeoPackage (.gpkg):</strong> Multi-layer geodatabase</li>
            <li><strong>PostGIS:</strong> Database layers</li>
            <li><strong>GeoTIFF (.tif):</strong> Raster imagery</li>
            <li><strong>GeoJSON (.geojson):</strong> Vector data</li>
            <li><strong>KML (.kml):</strong> Keyhole Markup Language</li>
            <li><strong>SQLite (.db):</strong> Spatial database</li>
          </ul>
        </section>

        <section>
          <h3>Basic Upload Steps</h3>
          <ol>
            <li>Select layers from your QGIS project</li>
            <li>Choose your target workspace</li>
            <li>Configure upload options:
              <ul>
                <li>Auto-overwrite existing layers</li>
                <li>Upload SLD styles</li>
              </ul>
            </li>
            <li>Click "Upload" to start the process</li>
            <li>Monitor progress in the log window</li>
          </ol>
        </section>

        <section>
          <h3>Batch Upload</h3>
          <p>Upload multiple layers at once:</p>
          <ol>
            <li>Select multiple layers using Ctrl+Click or Shift+Click</li>
            <li>Click "Select All" to upload all layers</li>
            <li>Configure options for the batch</li>
            <li>Click "Upload" to process all layers</li>
          </ol>
        </section>

        <section>
          <h3>PostGIS Layers</h3>
          <p>For PostGIS layers:</p>
          <ul>
            <li>Configure PostGIS connection in QGIS</li>
            <li>Select PostGIS layers from your project</li>
            <li>The plugin will create a datastore and publish the layers</li>
            <li>Credentials are handled securely</li>
          </ul>
        </section>

        <section>
          <h3>Upload Options</h3>
          <ul>
            <li><strong>Auto-overwrite:</strong> Replace layers with the same name</li>
            <li><strong>Overwrite SLD:</strong> Replace existing styles</li>
            <li><strong>Show progress:</strong> Display real-time upload status</li>
          </ul>
        </section>

        <section>
          <h3>Monitoring Upload Progress</h3>
          <p>The plugin provides detailed feedback:</p>
          <ul>
            <li>Real-time progress bar</li>
            <li>Detailed log messages</li>
            <li>Error notifications for failed uploads</li>
            <li>Success confirmation for completed uploads</li>
          </ul>
        </section>
      </div>
    </div>
  );
};

export default LayerUpload;
