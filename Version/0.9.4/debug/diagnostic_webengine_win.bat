@echo off
echo === OpenGL Detection ===
dxdiag /whql:off /t dxdiag_output.txt
type dxdiag_output.txt | findstr /i "DirectX"

echo === GPU Detection ===
wmic path win32_VideoController get name

echo === QtWebEngine Resources ===
dir "%OSGEO4W_ROOT%\apps\Qt6\resources"

echo === QtWebEngineProcess Running ===
tasklist | findstr QtWebEngineProcess
exit /b 0
