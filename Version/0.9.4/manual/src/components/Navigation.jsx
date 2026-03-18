import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import '../styles/Navigation.css';

const Navigation = () => {
  const [isOpen, setIsOpen] = useState(false);

  const navItems = [
    { path: '/', label: 'Home', icon: '🏠' },
    { path: '/before-you-start', label: 'Before You Start', icon: '⚠️' },
    { path: '/getting-started', label: 'Getting Started', icon: '🚀' },
    { path: '/installation', label: 'Installation', icon: '📦' },
    { path: '/configuration', label: 'Configuration', icon: '⚙️' },
    { path: '/layer-upload', label: 'Layer Upload', icon: '📤' },
    { path: '/style-management', label: 'Style Management', icon: '🎨' },
    { path: '/workspace-management', label: 'Workspace', icon: '📁' },
    { path: '/preview', label: 'Preview', icon: '👁️' },
    { path: '/troubleshooting', label: 'Troubleshooting', icon: '🔧' },
    { path: '/advanced-features', label: 'Advanced', icon: '⚡' },
    { path: '/faq', label: 'FAQ', icon: '❓' },
  ];

  return (
    <nav className="navigation">
      <div className="nav-container">
        <button 
          className="mobile-menu-btn"
          onClick={() => setIsOpen(!isOpen)}
          aria-label="Toggle menu"
        >
          {isOpen ? <X size={24} /> : <Menu size={24} />}
        </button>

        <div className={`nav-items ${isOpen ? 'open' : ''}`}>
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className="nav-item"
              onClick={() => setIsOpen(false)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
