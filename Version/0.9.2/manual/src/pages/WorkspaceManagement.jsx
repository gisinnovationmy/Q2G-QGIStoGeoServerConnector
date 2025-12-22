import React from 'react';

const WorkspaceManagement = () => {
  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">📁 Workspace Management</h1>
        <p className="page-subtitle">Create and manage workspaces</p>
      </div>

      <div className="content">
        <section>
          <h2>Understanding Workspaces</h2>
          <p>
            Workspaces in GeoServer are logical groupings for layers, datastores, and styles. They help organize
            your geospatial data and control access permissions.
          </p>
        </section>

        <section>
          <h3>Creating a Workspace</h3>
          <ol>
            <li>Open the GeoServerConnector plugin</li>
            <li>Click "Create Workspace"</li>
            <li>Enter a workspace name</li>
            <li>Click "Create"</li>
            <li>The workspace will appear in the list</li>
          </ol>
        </section>

        <section>
          <h3>Selecting a Workspace</h3>
          <p>To upload layers to a specific workspace:</p>
          <ol>
            <li>Select the workspace from the dropdown</li>
            <li>The workspace layers will be displayed</li>
            <li>Select your layers to upload</li>
            <li>Click "Upload"</li>
          </ol>
        </section>

        <section>
          <h3>Managing Datastores</h3>
          <p>Datastores are connections to data sources. The plugin manages datastores automatically:</p>
          <ul>
            <li>Creates datastores for uploaded layers</li>
            <li>Manages PostGIS connections</li>
            <li>Handles file-based datastores (Shapefile, GeoPackage)</li>
            <li>Cleans up duplicate datastores</li>
          </ul>
        </section>

        <section>
          <h3>Deleting Workspaces</h3>
          <p>To delete a workspace:</p>
          <ol>
            <li>Select the workspace</li>
            <li>Click "Delete Workspace"</li>
            <li>Confirm the deletion</li>
            <li>All layers and datastores in the workspace will be removed</li>
          </ol>
        </section>

        <section>
          <h3>Workspace Best Practices</h3>
          <ul>
            <li>Use meaningful workspace names</li>
            <li>Organize by project or department</li>
            <li>Keep related layers in the same workspace</li>
            <li>Document workspace purposes</li>
            <li>Regularly clean up unused workspaces</li>
          </ul>
        </section>

        <section>
          <h3>Workspace Permissions</h3>
          <p>GeoServer allows you to set permissions on workspaces:</p>
          <ul>
            <li>Control who can read layers</li>
            <li>Control who can modify layers</li>
            <li>Set workspace-level access rules</li>
            <li>Manage through GeoServer web interface</li>
          </ul>
        </section>
      </div>
    </div>
  );
};

export default WorkspaceManagement;
