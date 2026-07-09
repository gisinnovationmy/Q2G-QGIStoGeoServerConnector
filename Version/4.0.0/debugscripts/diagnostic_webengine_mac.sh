#!/bin/bash

echo "=== OpenGL/GPU Detection ==="
system_profiler SPDisplaysDataType

echo "=== QtWebEngine Resources ==="
ls /Applications/QGIS.app/Contents/Resources/qt6/resources

echo "=== QtWebEngineProcess Running ==="
ps -ax | grep QtWebEngineProcess
