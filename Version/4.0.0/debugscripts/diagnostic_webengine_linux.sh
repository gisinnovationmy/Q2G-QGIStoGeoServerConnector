#!/bin/bash

echo "=== OpenGL Detection ==="
glxinfo | grep OpenGL

echo "=== GPU Detection ==="
lspci | grep -i vga

echo "=== QtWebEngine Resources ==="
ls /usr/share/qgis/qt6/resources

echo "=== QtWebEngineProcess Running ==="
ps aux | grep QtWebEngineProcess
