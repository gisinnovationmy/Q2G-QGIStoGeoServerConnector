import React from 'react';

const Troubleshooting = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">🔧 Troubleshooting</h1>
        <p className="page-subtitle">Solutions to common issues</p>
      </div>

      <div className="content">
        <section>
          <h2>Common Issues and Solutions</h2>
          <p>This section covers common problems and their solutions.</p>
        </section>

        <section>
          <h3>Connection Issues</h3>
          <h4>Problem: Cannot connect to GeoServer</h4>
          <ul>
            <li>Verify GeoServer is running</li>
            <li>Check the URL is correct</li>
            <li>Verify network connectivity</li>
            <li>Check firewall settings</li>
            <li>Verify username and password</li>
          </ul>
        </section>

        <section>
          <h3>Upload Issues</h3>
          <h4>Problem: Layer upload fails</h4>
          <ul>
            <li>Check layer has valid geometry</li>
            <li>Verify coordinate system is defined</li>
            <li>Check file format is supported</li>
            <li>Ensure layer name doesn't contain special characters</li>
            <li>Check GeoServer has sufficient disk space</li>
          </ul>
        </section>

        <section>
          <h3>Style Issues</h3>
          <h4>Problem: Styles not applying</h4>
          <ul>
            <li>Verify SLD is valid XML</li>
            <li>Check style name matches layer name</li>
            <li>Ensure style is in correct workspace</li>
            <li>Try re-uploading the style</li>
            <li>Check GeoServer logs for errors</li>
          </ul>
        </section>

        <section>
          <h3>PostGIS Issues</h3>
          <h4>Problem: PostGIS layers not uploading</h4>
          <ul>
            <li>Verify PostGIS connection in QGIS</li>
            <li>Check database credentials</li>
            <li>Ensure table has valid geometry</li>
            <li>Verify geometry column is named 'geom' or 'geometry'</li>
            <li>Check table has a primary key</li>
          </ul>
        </section>

        <section>
          <h3>Performance Issues</h3>
          <h4>Problem: Upload is slow</h4>
          <ul>
            <li>Check network connection speed</li>
            <li>Reduce layer size or split into smaller files</li>
            <li>Upload during off-peak hours</li>
            <li>Check GeoServer server resources</li>
            <li>Consider batch uploading smaller layers first</li>
          </ul>
        </section>

        <section>
          <h3>Error Messages</h3>
          <h4>Common Error: "Layer not found"</h4>
          <p>The layer doesn't exist in GeoServer. Check that:</p>
          <ul>
            <li>Layer was successfully uploaded</li>
            <li>You're looking in the correct workspace</li>
            <li>Layer name is spelled correctly</li>
          </ul>

          <h4>Common Error: "Invalid CRS"</h4>
          <p>The coordinate system is not recognized. Try:</p>
          <ul>
            <li>Setting CRS in QGIS layer properties</li>
            <li>Using EPSG codes instead of custom CRS</li>
            <li>Re-projecting the layer to a standard CRS</li>
          </ul>

          <h4>Common Error: "Permission denied"</h4>
          <p>You don't have permission to perform this action:</p>
          <ul>
            <li>Check your GeoServer user permissions</li>
            <li>Verify workspace access rights</li>
            <li>Contact GeoServer administrator</li>
          </ul>
        </section>

        <section>
          <h3>Getting Help</h3>
          <ul>
            <li>Check the FAQ section</li>
            <li>Review GeoServer logs</li>
            <li>Check plugin logs in QGIS</li>
            <li>Visit the project repository</li>
            <li>Contact support with detailed error messages</li>
          </ul>
        </section>
      </div>
    </div>
  );
};

export default Troubleshooting;
