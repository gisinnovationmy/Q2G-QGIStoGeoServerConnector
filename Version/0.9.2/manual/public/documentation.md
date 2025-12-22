# Q2G Documentation - Website Version Planning

## Overview

This document outlines the plan for creating a **website version** of the Q2G documentation with screenshots. The plugin version (current) has no screenshots, while the website version will include visual guides.

---

## Folder Structure

```
website-documentation/
├── index.html
├── 01-getting-started.html
├── 02-installation.html
├── 03-configuration.html
├── 04-layer-upload.html
├── 05-style-management.html
├── 06-workspace-management.html
├── 07-preview.html
├── 08-troubleshooting.html
├── 09-advanced-features.html
├── 10-faq.html
├── style.css
├── images/
│   ├── getting-started/
│   │   ├── gs-01-plugin-panel.png
│   │   ├── gs-02-main-interface.png
│   │   ├── gs-03-connection-panel.png
│   │   └── ...
│   ├── installation/
│   │   ├── inst-01-plugin-manager.png
│   │   ├── inst-02-search-q2g.png
│   │   ├── inst-03-install-button.png
│   │   └── ...
│   ├── configuration/
│   │   ├── conf-01-connection-settings.png
│   │   ├── conf-02-geoserver-url.png
│   │   ├── conf-03-test-connection.png
│   │   └── ...
│   ├── layer-upload/
│   │   ├── upload-01-select-layers.png
│   │   ├── upload-02-workspace-dropdown.png
│   │   ├── upload-03-upload-options.png
│   │   ├── upload-04-progress-log.png
│   │   └── ...
│   ├── style-management/
│   │   ├── style-01-qgis-symbology.png
│   │   ├── style-02-upload-sld.png
│   │   ├── style-03-view-sld.png
│   │   └── ...
│   ├── workspace-management/
│   │   ├── ws-01-workspace-dropdown.png
│   │   ├── ws-02-create-workspace.png
│   │   ├── ws-03-delete-workspace.png
│   │   ├── ws-04-layer-list.png
│   │   └── ...
│   ├── preview/
│   │   ├── preview-01-preview-button.png
│   │   ├── preview-02-map-view.png
│   │   ├── preview-03-controls.png
│   │   └── ...
│   ├── troubleshooting/
│   │   ├── ts-01-error-log.png
│   │   ├── ts-02-connection-error.png
│   │   └── ...
│   └── advanced/
│       ├── adv-01-batch-upload.png
│       ├── adv-02-postgis-settings.png
│       ├── adv-03-cache-reset.png
│       └── ...
└── logos/
    └── logo.svg
```

---

## Image Naming Convention

**Format:** `{section}-{number}-{description}.png`

**Examples:**
- `gs-01-plugin-panel.png` - Getting Started, image 1, plugin panel
- `upload-03-upload-options.png` - Layer Upload, image 3, upload options
- `conf-02-geoserver-url.png` - Configuration, image 2, GeoServer URL field

**Section Prefixes:**
| Section | Prefix |
|---------|--------|
| Getting Started | `gs-` |
| Installation | `inst-` |
| Configuration | `conf-` |
| Layer Upload | `upload-` |
| Style Management | `style-` |
| Workspace Management | `ws-` |
| Preview | `preview-` |
| Troubleshooting | `ts-` |
| Advanced Features | `adv-` |
| FAQ | `faq-` |

---

## Screenshot Checklist

### 01 - Getting Started
- [ ] `gs-01-plugin-panel.png` - Q2G panel in QGIS sidebar
- [ ] `gs-02-main-interface.png` - Full Q2G interface overview
- [ ] `gs-03-connection-panel.png` - Connection settings area
- [ ] `gs-04-layer-list.png` - QGIS layers panel with checkboxes
- [ ] `gs-05-upload-button.png` - Upload button highlighted
- [ ] `gs-06-log-panel.png` - Upload log area

### 02 - Installation
- [ ] `inst-01-plugin-manager.png` - QGIS Plugin Manager menu
- [ ] `inst-02-search-q2g.png` - Search results for Q2G
- [ ] `inst-03-install-button.png` - Install button highlighted
- [ ] `inst-04-installed-success.png` - Installation success message
- [ ] `inst-05-enable-plugin.png` - Plugin enabled in list
- [ ] `inst-06-toolbar-icon.png` - Q2G icon in QGIS toolbar

### 03 - Configuration
- [ ] `conf-01-connection-settings.png` - Full connection panel
- [ ] `conf-02-geoserver-url.png` - GeoServer URL input field
- [ ] `conf-03-credentials.png` - Username/password fields
- [ ] `conf-04-test-connection.png` - Test connection button
- [ ] `conf-05-connection-success.png` - Successful connection message
- [ ] `conf-06-connection-failed.png` - Failed connection error
- [ ] `conf-07-workspace-loaded.png` - Workspaces loaded in dropdown

### 04 - Layer Upload
- [ ] `upload-01-select-layers.png` - Layer selection checkboxes
- [ ] `upload-02-workspace-dropdown.png` - Workspace selection dropdown
- [ ] `upload-03-upload-options.png` - Upload options (overwrite, SLD, etc.)
- [ ] `upload-04-upload-button.png` - Upload button
- [ ] `upload-05-progress-log.png` - Upload progress in log
- [ ] `upload-06-upload-success.png` - Successful upload message
- [ ] `upload-07-geoserver-layer.png` - Layer visible in GeoServer admin
- [ ] `upload-08-format-shapefile.png` - Shapefile layer example
- [ ] `upload-09-format-geopackage.png` - GeoPackage layer example
- [ ] `upload-10-format-geotiff.png` - GeoTIFF raster example

### 05 - Style Management
- [ ] `style-01-qgis-symbology.png` - QGIS layer symbology panel
- [ ] `style-02-upload-sld-checkbox.png` - Upload SLD checkbox
- [ ] `style-03-style-uploaded.png` - Style upload success message
- [ ] `style-04-view-sld-button.png` - View SLD button (...)
- [ ] `style-05-sld-code-window.png` - SLD code viewer window
- [ ] `style-06-geoserver-style.png` - Style in GeoServer admin

### 06 - Workspace Management
- [ ] `ws-01-workspace-dropdown.png` - Workspace dropdown menu
- [ ] `ws-02-create-button.png` - Create workspace button
- [ ] `ws-03-create-dialog.png` - Create workspace dialog
- [ ] `ws-04-workspace-created.png` - New workspace in list
- [ ] `ws-05-layer-list.png` - Layers in workspace
- [ ] `ws-06-delete-button.png` - Delete workspace button
- [ ] `ws-07-delete-confirm.png` - Delete confirmation dialog
- [ ] `ws-08-datastore-list.png` - Datastores in workspace
- [ ] `ws-09-right-click-menu.png` - Layer right-click context menu

### 07 - Preview & Visualization
- [ ] `preview-01-preview-button.png` - Preview button on layer
- [ ] `preview-02-preview-window.png` - Full preview window
- [ ] `preview-03-map-controls.png` - Zoom/pan controls
- [ ] `preview-04-layer-toggle.png` - Layer visibility toggle
- [ ] `preview-05-feature-popup.png` - Feature info popup
- [ ] `preview-06-style-preview.png` - Styled layer in preview

### 08 - Troubleshooting
- [ ] `ts-01-error-log.png` - Error messages in log
- [ ] `ts-02-connection-refused.png` - Connection refused error
- [ ] `ts-03-auth-failed.png` - Authentication failed error
- [ ] `ts-04-layer-exists.png` - Layer already exists error
- [ ] `ts-05-qgis-log.png` - QGIS log messages panel
- [ ] `ts-06-geoserver-logs.png` - GeoServer logs page

### 09 - Advanced Features
- [ ] `adv-01-batch-select.png` - Multiple layers selected
- [ ] `adv-02-batch-progress.png` - Batch upload progress
- [ ] `adv-03-postgis-layer.png` - PostGIS layer in QGIS
- [ ] `adv-04-postgis-credentials.png` - PostGIS credentials dialog
- [ ] `adv-05-cache-reset-button.png` - Reset All Caches button
- [ ] `adv-06-cache-reset-success.png` - Cache reset success message

### 10 - FAQ
- [ ] `faq-01-plugin-manager.png` - Plugin Manager for updates
- [ ] `faq-02-geoserver-admin.png` - GeoServer admin interface

---

## HTML Image Placeholder Markup

Use this markup pattern for images in the website version:

```html
<figure class="screenshot">
    <img src="images/getting-started/gs-01-plugin-panel.png" 
         alt="Q2G plugin panel in QGIS sidebar"
         loading="lazy">
    <figcaption>Figure 1: The Q2G plugin panel appears in the QGIS sidebar</figcaption>
</figure>
```

### CSS for Screenshots

```css
/* Screenshot Figures */
.screenshot {
    margin: 25px 0;
    text-align: center;
}

.screenshot img {
    max-width: 100%;
    height: auto;
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.1);
    border: 1px solid rgba(0,0,0,0.1);
}

.screenshot figcaption {
    margin-top: 12px;
    font-size: 0.9em;
    color: #666;
    font-style: italic;
}
```

---

## Next Steps

1. **Copy HTML files** from plugin `manual/` folder to new website project
2. **Create `images/` folder structure** as outlined above
3. **Capture screenshots** following the checklist
4. **Add `<figure>` markup** to HTML files where screenshots should appear
5. **Update image paths** in HTML to point to `images/` folder
6. **Test** all images load correctly
7. **Deploy** to website

---

## Notes

- Keep plugin version (no screenshots) separate from website version
- Use PNG format for screenshots (better quality for UI)
- Recommended screenshot width: 800-1200px
- Add red circles/arrows in image editor to highlight important areas
- Consider adding animated GIFs for complex workflows

---

*Last updated: December 2025*