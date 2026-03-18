import React from 'react';
import { Link } from 'react-router-dom';
import '../styles/Pages.css';

const Home = () => {
  const sections = [
    {
      path: '/before-you-start',
      icon: '⚠️',
      title: 'Before You Start',
      description: 'Essential setup requirements, web components, CORS configuration, and the Importer extension.',
    },
    {
      path: '/getting-started',
      icon: '🚀',
      title: 'Getting Started',
      description: 'Learn the basics of GeoServerConnector and how to set up your first connection to GeoServer.',
    },
    {
      path: '/installation',
      icon: '📦',
      title: 'Installation',
      description: 'Step-by-step guide to install and activate the GeoServerConnector plugin in QGIS.',
    },
    {
      path: '/configuration',
      icon: '⚙️',
      title: 'Configuration',
      description: 'Configure your GeoServer connection, authentication, and plugin settings.',
    },
    {
      path: '/layer-upload',
      icon: '📤',
      title: 'Layer Upload',
      description: 'Upload your QGIS layers to GeoServer with support for multiple formats.',
    },
    {
      path: '/style-management',
      icon: '🎨',
      title: 'Style Management',
      description: 'Create, upload, and manage SLD styles for your layers on GeoServer.',
    },
    {
      path: '/workspace-management',
      icon: '📁',
      title: 'Workspace Management',
      description: 'Create, delete, and manage GeoServer workspaces and datastores.',
    },
    {
      path: '/preview',
      icon: '👁️',
      title: 'Preview & Visualization',
      description: 'Preview layers and styles before uploading to GeoServer.',
    },
    {
      path: '/troubleshooting',
      icon: '🔧',
      title: 'Troubleshooting',
      description: 'Solutions to common issues and error messages.',
    },
    {
      path: '/advanced-features',
      icon: '⚡',
      title: 'Advanced Features',
      description: 'Explore advanced features like batch uploads and PostGIS integration.',
    },
    {
      path: '/faq',
      icon: '❓',
      title: 'FAQ',
      description: 'Frequently asked questions and best practices.',
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Welcome to GeoServerConnector</h1>
        <p className="page-subtitle">
          Your complete guide to uploading, managing, and styling geospatial data on GeoServer
        </p>
      </div>

      <div className="quick-links-section">
        <h2 className="section-title">📚 Quick Navigation</h2>
        <ul className="quick-links-list">
          {sections.map((section) => (
            <li key={section.path}>
              <Link to={section.path} className="quick-link">
                {section.title}
              </Link>
            </li>
          ))}
        </ul>
      </div>

      <div className="features-grid">
        {sections.map((section, index) => (
          <Link
            key={section.path}
            to={section.path}
            className="feature-card"
            style={{ animationDelay: `${index * 0.05}s` }}
          >
            <div className="card-icon">{section.icon}</div>
            <h3 className="card-title">{section.title}</h3>
            <p className="card-description">{section.description}</p>
            <div className="card-arrow">→</div>
          </Link>
        ))}
      </div>

      <div className="info-section">
        <div className="info-card info-note">
          <h3>💡 Tip</h3>
          <p>
            This manual is organized into logical sections. Start with "Getting Started" if you're new to
            GeoServerConnector, or jump to specific topics using the navigation menu.
          </p>
        </div>

        <div className="info-card info-success">
          <h3>✨ Features</h3>
          <p>
            GeoServerConnector supports multiple layer formats including Shapefiles, GeoPackages, PostGIS
            layers, GeoTIFF, and more. Upload and manage your geospatial data with ease.
          </p>
        </div>

        <div className="info-card info-warning">
          <h3>⚠️ Requirements</h3>
          <p>
            You'll need QGIS 3.x and a running GeoServer instance. Make sure you have the necessary
            credentials and network access to your GeoServer.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Home;
