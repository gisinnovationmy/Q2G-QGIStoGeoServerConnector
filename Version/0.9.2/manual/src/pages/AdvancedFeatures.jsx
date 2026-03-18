import React from 'react';

const AdvancedFeatures = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">⚡ Advanced Features</h1>
        <p className="page-subtitle">Explore advanced capabilities</p>
      </div>

      <div className="content">
        <section>
          <h2>Advanced Features</h2>
          <p>GeoServerConnector includes several advanced features for power users.</p>
        </section>

        <section>
          <h3>Batch Upload</h3>
          <p>Upload multiple layers at once:</p>
          <ol>
            <li>Select multiple layers using Ctrl+Click</li>
            <li>Configure batch upload options</li>
            <li>Click "Upload All"</li>
            <li>Monitor progress for all layers</li>
          </ol>
          <p>Benefits:</p>
          <ul>
            <li>Save time uploading many layers</li>
            <li>Consistent configuration across layers</li>
            <li>Automatic error handling</li>
            <li>Detailed batch upload reports</li>
          </ul>
        </section>

        <section>
          <h3>PostGIS Integration</h3>
          <p>Seamless integration with PostGIS databases:</p>
          <ul>
            <li>Direct connection to PostGIS tables</li>
            <li>Automatic datastore creation</li>
            <li>Support for multiple schemas</li>
            <li>Credential management</li>
            <li>Batch publishing of tables</li>
          </ul>
        </section>

        <section>
          <h3>Layer Format Conversion</h3>
          <p>Automatic format conversion for unsupported formats:</p>
          <ul>
            <li>SQLite to Shapefile conversion</li>
            <li>Automatic format detection</li>
            <li>Transparent conversion process</li>
            <li>Preserves layer properties</li>
          </ul>
        </section>

        <section>
          <h3>Upload Control</h3>
          <p>Fine-grained control over the upload process:</p>
          <ul>
            <li><strong>Pause Upload:</strong> Pause and resume uploads</li>
            <li><strong>Stop Upload:</strong> Cancel upload process</li>
            <li><strong>Step Mode:</strong> Upload one layer at a time</li>
            <li><strong>Continue:</strong> Resume paused uploads</li>
          </ul>
        </section>

        <section>
          <h3>Duplicate Store Cleanup</h3>
          <p>Automatic cleanup of duplicate datastores:</p>
          <ul>
            <li>Detects duplicate datastores</li>
            <li>Removes temporary stores</li>
            <li>Cleans up after failed uploads</li>
            <li>Keeps workspace organized</li>
          </ul>
        </section>

        <section>
          <h3>Advanced Logging</h3>
          <p>Detailed logging for debugging:</p>
          <ul>
            <li>Real-time upload progress</li>
            <li>Detailed error messages</li>
            <li>Task state tracking</li>
            <li>Full response logging</li>
            <li>Export logs for analysis</li>
          </ul>
        </section>

        <section>
          <h3>Style Management</h3>
          <p>Advanced style features:</p>
          <ul>
            <li>Workspace-scoped styles</li>
            <li>Global style management</li>
            <li>Automatic duplicate detection</li>
            <li>Style preview and editing</li>
            <li>SLD validation</li>
          </ul>
        </section>

        <section>
          <h3>Layer Preview</h3>
          <p>Interactive preview capabilities:</p>
          <ul>
            <li>OpenLayers-based map viewer</li>
            <li>Multiple base map options</li>
            <li>Day/Night theme support</li>
            <li>Measurement tools</li>
            <li>Feature information popup</li>
            <li>Export as HTML</li>
          </ul>
        </section>

        <section>
          <h3>Performance Optimization</h3>
          <p>Built-in optimizations for better performance:</p>
          <ul>
            <li>Efficient batch processing</li>
            <li>Connection pooling</li>
            <li>Automatic retry on failure</li>
            <li>Progress-based calculations</li>
            <li>Memory-efficient processing</li>
          </ul>
        </section>
      </div>
    </div>
  );
};

export default AdvancedFeatures;
