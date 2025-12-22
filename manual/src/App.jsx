import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Moon, Sun } from 'lucide-react';
import Navigation from './components/Navigation';
import Home from './pages/Home';
import BeforeYouStart from './pages/BeforeYouStart';
import GettingStarted from './pages/GettingStarted';
import Installation from './pages/Installation';
import Configuration from './pages/Configuration';
import LayerUpload from './pages/LayerUpload';
import StyleManagement from './pages/StyleManagement';
import WorkspaceManagement from './pages/WorkspaceManagement';
import Preview from './pages/Preview';
import Troubleshooting from './pages/Troubleshooting';
import AdvancedFeatures from './pages/AdvancedFeatures';
import FAQ from './pages/FAQ';
import './styles/App.css';

function App() {
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode');
    return saved ? JSON.parse(saved) : false;
  });

  useEffect(() => {
    localStorage.setItem('darkMode', JSON.stringify(isDarkMode));
    if (isDarkMode) {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.setAttribute('data-theme', 'light');
    }
  }, [isDarkMode]);

  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode);
  };

  return (
    <Router>
      <div className={`app ${isDarkMode ? 'dark-mode' : 'light-mode'}`}>
        <header className="app-header">
          <div className="header-content">
            <div className="logo-section">
              <h1 className="logo">🌐 GeoServerConnector</h1>
              <p className="tagline">Complete User Manual</p>
            </div>
            <button 
              className="theme-toggle"
              onClick={toggleTheme}
              aria-label="Toggle theme"
            >
              {isDarkMode ? (
                <Sun size={24} />
              ) : (
                <Moon size={24} />
              )}
            </button>
          </div>
        </header>

        <Navigation />

        <main className="main-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/before-you-start" element={<BeforeYouStart />} />
            <Route path="/getting-started" element={<GettingStarted />} />
            <Route path="/installation" element={<Installation />} />
            <Route path="/configuration" element={<Configuration />} />
            <Route path="/layer-upload" element={<LayerUpload />} />
            <Route path="/style-management" element={<StyleManagement />} />
            <Route path="/workspace-management" element={<WorkspaceManagement />} />
            <Route path="/preview" element={<Preview />} />
            <Route path="/troubleshooting" element={<Troubleshooting />} />
            <Route path="/advanced-features" element={<AdvancedFeatures />} />
            <Route path="/faq" element={<FAQ />} />
          </Routes>
        </main>

        <footer className="app-footer">
          <p>&copy; 2025 GeoServerConnector. All rights reserved.</p>
          <p>For support and updates, visit the project repository.</p>
        </footer>
      </div>
    </Router>
  );
}

export default App;
