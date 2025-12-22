# map.py
"""
This module provides the HTML and JS for the OpenLayers map as hardcoded strings.
"""

def get_map_html():
    # This HTML includes an OpenLayers map and the required JS inline.
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>GeoServer Layer Preview</title>
    <meta charset="utf-8" />
    <style>
        html, body, #map { margin: 0; padding: 0; width: 100vw; height: 100vh; }
    </style>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/openlayers/openlayers.github.io@master/en/v6.5.0/css/ol.css" type="text/css">
</head>
<body>
    <div id="map"></div>
    <script src="https://cdn.jsdelivr.net/gh/openlayers/openlayers.github.io@master/en/v6.5.0/build/ol.js"></script>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <script>
        // --- OpenLayers map setup and dynamic JS integration ---
        var base_layer_light = new ol.layer.Tile({
            source: new ol.source.XYZ({
                url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                projection: 'EPSG:3857'
            })
        });
        var base_layer_dark = new ol.layer.Tile({
            source: new ol.source.XYZ({
                url: 'https://{a-c}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
                projection: 'EPSG:3857'
            })
        });
        base_layer_dark.setVisible(false);
        var map = new ol.Map({
            target: 'map',
            layers: [base_layer_light, base_layer_dark],
            controls: [],
            view: new ol.View({
                center: ol.proj.fromLonLat([0, 0]),
                zoom: 2,
                minZoom: 2,
                maxZoom: 28,
                projection: 'EPSG:3857',
                extent: ol.proj.get('EPSG:3857').getExtent()
            })
        });
        ol.proj.get('EPSG:3857').setExtent([-20037508.34, -20037508.34, 20037508.34, 20037508.34]);
        window.ol_map = map;
        window.ol_layers = {};
        window.ol_controls = {};
        window.is_dark_theme = false;
        // --- Web channel setup ---
        new QWebChannel(qt.webChannelTransport, function (channel) {
            window.backend = channel.objects.backend;
            console.log('[JS] WebChannel initialized. Backend object available:', !!window.backend);
        });
        // --- Layer and control functions (from map_functions.js) ---
        function addWmsLayer(url, layerName, layerId, authHeader) {
            console.log(`[JS] addWmsLayer called with layerName: ${layerName}`);
            removeLayer(layerId);
            var wmsSource = new ol.source.TileWMS({
                url: url,
                params: {'LAYERS': layerName, 'TILED': true},
                serverType: 'geoserver',
                crossOrigin: 'anonymous',
                tileLoadFunction: function(tile, src) {
                    var xhr = new XMLHttpRequest();
                    xhr.open('GET', src);
                    if (authHeader) xhr.setRequestHeader('Authorization', authHeader);
                    xhr.onload = function() {
                        if (xhr.status === 200) {
                            tile.getImage().src = URL.createObjectURL(new Blob([xhr.response]));
                        }
                    };
                    xhr.onerror = function() {};
                    xhr.responseType = 'arraybuffer';
                    xhr.send();
                }
            });
            var wmsLayer = new ol.layer.Tile({ source: wmsSource });
            wmsLayer.set('id', layerId);
            map.addLayer(wmsLayer);
            window.ol_layers[layerId] = wmsLayer;
            // Force map refresh
            map.render();
            map.updateSize();
            if (typeof backend !== 'undefined' && backend.on_layer_status_update) {
                backend.on_layer_status_update(layerId, 'success', 'WMS layer added successfully');
            }
        }
        function addWfsLayer(url, layerName, layerId, authHeader) {
            console.log(`[JS] addWfsLayer called with layerName: ${layerName}`);
            removeLayer(layerId);
            const vectorSource = new ol.source.Vector();
            const wfsLayer = new ol.layer.Vector({ source: vectorSource });
            wfsLayer.set('id', layerId);
            map.addLayer(wfsLayer);
            window.ol_layers[layerId] = wfsLayer;
            // Force map refresh
            map.render();
            map.updateSize();

            const wfsCallback = function(id, success, data) {
                if (id !== layerId) return;
                if (success) {
                    try {
                        const features = new ol.format.GeoJSON().readFeatures(data, {
                            featureProjection: map.getView().getProjection().getCode()
                        });
                        vectorSource.addFeatures(features);
                        map.render();
                        map.updateSize();
                        if (typeof backend !== 'undefined') backend.on_layer_status_update(layerId, 'success', 'WFS layer loaded.');
                    } catch (e) {
                        if (typeof backend !== 'undefined') backend.on_layer_status_update(layerId, 'error', 'Failed to parse WFS JSON: ' + e.message);
                    }
                } else {
                    if (typeof backend !== 'undefined') backend.on_layer_status_update(layerId, 'error', 'WFS proxy error: ' + data);
                }
            };

            if (window.backend && window.backend.fetch_wfs_data) {
                window.backend.fetch_wfs_data(layerId, layerName, wfsCallback);
            } else {
                if (typeof backend !== 'undefined') backend.on_layer_status_update(layerId, 'error', 'Backend proxy for WFS is not available.');
            }
        }
        function addWmtsLayer(url, layerName, layerId, authHeader) {
            console.log(`[JS] addWmtsLayer called with layerName: ${layerName}`);
            removeLayer(layerId);
            const wmtsSource = new ol.source.WMTS({
                url: url,
                layer: layerName,
                matrixSet: 'EPSG:3857',
                format: 'image/png',
                projection: 'EPSG:3857',
                tileGrid: new ol.tilegrid.WMTS({
                    origin: [-20037508.34, 20037508.34],
                    resolutions: (function() {
                        var resolutions = [];
                        for (var i = 0; i < 19; ++i) {
                            resolutions[i] = 156543.03392804097 / Math.pow(2, i);
                        }
                        return resolutions;
                    })(),
                    matrixIds: Array.from({length: 19}, (_, i) => i.toString())
                }),
                style: 'default',
                wrapX: true,
                tileLoadFunction: function(tile, src) {
                    const xhr = new XMLHttpRequest();
                    xhr.open('GET', src);
                    if (authHeader) xhr.setRequestHeader('Authorization', authHeader);
                    xhr.onload = function() {
                        if (xhr.status === 200) {
                            tile.getImage().src = URL.createObjectURL(new Blob([xhr.response]));
                        }
                    };
                    xhr.onerror = function() {};
                    xhr.responseType = 'arraybuffer';
                    xhr.send();
                }
            });
            const wmtsLayer = new ol.layer.Tile({ source: wmtsSource });
            wmtsLayer.set('id', layerId);
            map.addLayer(wmtsLayer);
            window.ol_layers[layerId] = wmtsLayer;
            // Force map refresh
            map.render();
            map.updateSize();
            if (typeof backend !== 'undefined' && backend.on_layer_status_update) {
                backend.on_layer_status_update(layerId, 'success', 'WMTS layer added successfully');
            }
        }
        function removeLayer(layerId) {
            if (window.ol_layers[layerId]) {
                map.removeLayer(window.ol_layers[layerId]);
                delete window.ol_layers[layerId];
            }
        }
        function setLayerOpacity(layerId, opacity) {
            if (window.ol_layers[layerId]) {
                window.ol_layers[layerId].setOpacity(opacity);
            }
        }
        function toggleLayerVisibility(layerId, visible) {
            if (window.ol_layers[layerId]) {
                window.ol_layers[layerId].setVisible(visible);
            }
        }
        function clearMap() {
            Object.values(window.ol_layers).forEach(layer => map.removeLayer(layer));
            window.ol_layers = {};
        }
        function toggleBaseLayer(visible) {
            base_layer_light.setVisible(visible && !window.is_dark_theme);
            base_layer_dark.setVisible(visible && window.is_dark_theme);
        }
        function toggleDarkMode(is_dark) {
            window.is_dark_theme = is_dark;
            if (base_layer_light.getVisible() || base_layer_dark.getVisible()) {
                base_layer_light.setVisible(!is_dark);
                base_layer_dark.setVisible(is_dark);
            }
        }

        function refreshLayerOrder(layerIds) {
            layerIds.forEach((id, index) => {
                const layer = window.ol_layers[id];
                if (layer) {
                    layer.setZIndex(index + 2); // +2 to be above base layers
                }
            });
        }

        function zoomToLayer(extent, crs) {
            if (!extent || !crs) return;
            var view = map.getView();
            var map_crs = 'EPSG:3857';
            var transformed_extent;
            try {
                if (crs.toUpperCase() !== map_crs) {
                    transformed_extent = ol.proj.transformExtent(extent, crs, map_crs);
                } else {
                    transformed_extent = extent;
                }
                if (transformed_extent && transformed_extent.every(isFinite)) {
                    view.fit(transformed_extent, { duration: 1000, padding: [100, 100, 100, 100], maxZoom: 18 });
                }
            } catch (e) {
                console.error('Error in zoomToLayer:', e);
            }
        }

        function getMapView() {
            var view = map.getView();
            return {
                center: view.getCenter(),
                zoom: view.getZoom(),
                extent: view.calculateExtent(map.getSize())
            };
        }

        function setMapView(center, zoom) {
            var view = map.getView();
            if (center) view.setCenter(center);
            if (zoom) view.setZoom(zoom);
        }

        // Add control functions placeholders
        function addControl(controlName) { console.log('addControl called for:', controlName); }
        function removeControl(controlName) { console.log('removeControl called for:', controlName); }

    </script>
</body>
</html>
'''

