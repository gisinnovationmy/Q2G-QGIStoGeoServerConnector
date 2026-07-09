import React from 'react';

const StyleManagement = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">🎨 Style Management</h1>
        <p className="page-subtitle">Create and manage SLD styles</p>
      </div>

      <div className="content">
        <section>
          <h2>Managing Styles</h2>
          <p>GeoServerConnector allows you to create, upload, and manage SLD styles for your layers.</p>
        </section>

        <section>
          <h3>What is SLD?</h3>
          <p>
            SLD (Styled Layer Descriptor) is an OGC standard for describing map layer styling. It defines how layers
            should be rendered, including colors, symbols, labels, and other visual properties.
          </p>
        </section>

        <section>
          <h3>Creating Styles in QGIS</h3>
          <ol>
            <li>Select a layer in your QGIS project</li>
            <li>Right-click and choose "Properties"</li>
            <li>Go to the "Symbology" tab</li>
            <li>Configure your layer's appearance</li>
            <li>The plugin will export this as SLD</li>
          </ol>
        </section>

        <section>
          <h3>Uploading Styles</h3>
          <ol>
            <li>Select layers with styles you want to upload</li>
            <li>Check the "Upload SLD" option</li>
            <li>Click "Upload"</li>
            <li>Styles will be created in GeoServer and applied to layers</li>
          </ol>
        </section>

        <section>
          <h3>Managing Existing Styles</h3>
          <p>In the Styles section, you can:</p>
          <ul>
            <li>View all styles in the workspace</li>
            <li>Edit style properties</li>
            <li>Delete unused styles</li>
            <li>Preview styles before applying</li>
          </ul>
        </section>

        <section>
          <h3>Style Options</h3>
          <ul>
            <li><strong>Overwrite SLD:</strong> Replace existing styles with the same name</li>
            <li><strong>Auto-apply:</strong> Automatically apply styles to layers during upload</li>
            <li><strong>Show SLD:</strong> View the raw SLD XML code</li>
          </ul>
        </section>

        <section>
          <h3>Best Practices</h3>
          <ul>
            <li>Use descriptive style names</li>
            <li>Test styles in QGIS before uploading</li>
            <li>Keep styles organized by layer type</li>
            <li>Document complex styling rules</li>
            <li>Version control your SLD files</li>
          </ul>
        </section>
      </div>
    </div>
  );
};

export default StyleManagement;
