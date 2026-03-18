import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import '../styles/FAQ.css';

const FAQ = () => {
  const [expandedItems, setExpandedItems] = useState({});

  const faqs = [
    {
      id: 1,
      question: 'What is GeoServerConnector?',
      answer: 'GeoServerConnector is a QGIS plugin that enables seamless integration between QGIS and GeoServer. It allows you to upload layers, manage styles, and control your geospatial data directly from QGIS.'
    },
    {
      id: 2,
      question: 'What layer formats are supported?',
      answer: 'GeoServerConnector supports Shapefile, GeoPackage, PostGIS, GeoTIFF, GeoJSON, KML, and SQLite formats. Unsupported formats are automatically converted to Shapefile.'
    },
    {
      id: 3,
      question: 'Do I need a running GeoServer instance?',
      answer: 'Yes, you need a running GeoServer instance. GeoServerConnector connects to GeoServer via its REST API, so you must have network access to your GeoServer.'
    },
    {
      id: 4,
      question: 'Can I upload multiple layers at once?',
      answer: 'Yes, GeoServerConnector supports batch uploading. Select multiple layers and click "Upload All" to upload them with consistent configuration.'
    },
    {
      id: 5,
      question: 'How do I manage styles?',
      answer: 'Create styles in QGIS using the Symbology tab, then upload them to GeoServer. GeoServerConnector will export your QGIS styles as SLD and apply them to your layers.'
    },
    {
      id: 6,
      question: 'What is SLD?',
      answer: 'SLD (Styled Layer Descriptor) is an OGC standard for describing map layer styling. It defines how layers should be rendered, including colors, symbols, labels, and other visual properties.'
    },
    {
      id: 7,
      question: 'Can I upload PostGIS layers?',
      answer: 'Yes, GeoServerConnector has full PostGIS support. Configure your PostGIS connection in QGIS, select PostGIS layers, and the plugin will handle datastore creation and layer publishing.'
    },
    {
      id: 8,
      question: 'How do I preview layers before uploading?',
      answer: 'Select a layer and click the "Preview" button. An interactive map will open showing your layer with its current styling. You can explore the layer before uploading.'
    },
    {
      id: 9,
      question: 'What if my upload fails?',
      answer: 'Check the log for error messages. Common issues include invalid CRS, missing geometry, or permission problems. See the Troubleshooting section for detailed solutions.'
    },
    {
      id: 10,
      question: 'Can I pause or stop an upload?',
      answer: 'Yes, GeoServerConnector provides upload control buttons. You can pause, resume, or stop uploads. You can also use step mode to upload one layer at a time.'
    },
    {
      id: 11,
      question: 'How do I manage workspaces?',
      answer: 'Use the Workspace Management section to create, select, and delete workspaces. All uploads go to the currently selected workspace.'
    },
    {
      id: 12,
      question: 'Is my data secure?',
      answer: 'GeoServerConnector uses standard HTTPS connections and supports QGIS authentication configurations. Credentials can be saved securely in QGIS.'
    },
    {
      id: 13,
      question: 'Can I use the plugin offline?',
      answer: 'No, GeoServerConnector requires network access to GeoServer. However, you can prepare your layers offline and upload them when connected.'
    },
    {
      id: 14,
      question: 'What QGIS versions are supported?',
      answer: 'GeoServerConnector requires QGIS 3.40 or later. It has been tested with QGIS 3.40 and newer versions.'
    },
    {
      id: 15,
      question: 'How do I get support?',
      answer: 'Check the FAQ and Troubleshooting sections first. For additional help, visit the project repository or contact the development team with detailed error messages.'
    }
  ];

  const toggleExpand = (id) => {
    setExpandedItems(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">❓ Frequently Asked Questions</h1>
        <p className="page-subtitle">Find answers to common questions</p>
      </div>

      <div className="faq-container">
        {faqs.map((faq) => (
          <div
            key={faq.id}
            className={`faq-item ${expandedItems[faq.id] ? 'expanded' : ''}`}
          >
            <button
              className="faq-question"
              onClick={() => toggleExpand(faq.id)}
            >
              <span className="question-text">{faq.question}</span>
              <ChevronDown
                size={20}
                className={`chevron ${expandedItems[faq.id] ? 'rotated' : ''}`}
              />
            </button>
            {expandedItems[faq.id] && (
              <div className="faq-answer">
                <p>{faq.answer}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="faq-footer">
        <h3>Didn't find your answer?</h3>
        <p>Check the other sections of the manual or contact support for additional help.</p>
      </div>
    </div>
  );
};

export default FAQ;
