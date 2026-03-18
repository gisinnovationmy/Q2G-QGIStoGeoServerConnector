import React from 'react';

const Preview = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">👁️ Preview & Visualization</h1>
        <p className="page-subtitle">Preview layers before uploading</p>
      </div>

      <div className="content">
        <section>
          <h2>Layer Preview</h2>
          <p>The preview feature allows you to visualize layers and styles before uploading to GeoServer.</p>
        </section>

        <section>
          <h3>Accessing Preview</h3>
          <ol>
            <li>Select a layer in the QGIS Layers section</li>
            <li>Click the "Preview" button</li>
            <li>A map window will open showing the layer</li>
            <li>Interact with the map to explore the layer</li>
          </ol>
        </section>

        <section>
          <h3>Preview Features</h3>
          <ul>
            <li><strong>Interactive Map:</strong> Pan, zoom, and explore layers</li>
            <li><strong>Layer Visibility:</strong> Toggle layers on/off</li>
            <li><strong>Style Preview:</strong> See how styles will appear</li>
            <li><strong>Feature Information:</strong> Click features to see attributes</li>
            <li><strong>Measurement Tools:</strong> Measure distances and areas</li>
          </ul>
        </section>

        <section>
          <h3>Map Controls</h3>
          <p>The preview map includes:</p>
          <ul>
            <li><strong>Zoom:</strong> Use mouse wheel or zoom buttons</li>
            <li><strong>Pan:</strong> Click and drag to move around</li>
            <li><strong>Measure:</strong> Measure distances and areas</li>
            <li><strong>Identify:</strong> Click features to see information</li>
            <li><strong>Base Map:</strong> Toggle different base maps</li>
          </ul>
        </section>

        <section>
          <h3>Style Preview</h3>
          <p>Preview how your styles will appear:</p>
          <ol>
            <li>Configure layer symbology in QGIS</li>
            <li>Click "Preview" to see the styled layer</li>
            <li>Adjust styles as needed</li>
            <li>Upload when satisfied with appearance</li>
          </ol>
        </section>

        <section>
          <h3>Preview Tips</h3>
          <ul>
            <li>Use preview to verify data quality before upload</li>
            <li>Check for missing or incorrect data</li>
            <li>Verify coordinate systems are correct</li>
            <li>Test styling with different zoom levels</li>
            <li>Check performance with large datasets</li>
          </ul>
        </section>

        <section>
          <h3>Exporting Preview</h3>
          <p>You can export the preview map:</p>
          <ul>
            <li>Save as image (PNG, JPEG)</li>
            <li>Export as PDF</li>
            <li>View HTML source code</li>
            <li>Share preview with others</li>
          </ul>
        </section>
      </div>
    </div>
  );
};

export default Preview;
