# QtWebEngine External Diagnostic Scripts

## Purpose

These scripts provide external diagnostic capabilities for QtWebEngine issues that cannot be tested internally due to QGIS's custom Qt build limitations.

## Files

### Windows
- **`diagnostic_webengine_win.bat`** - Windows-specific diagnostic script
  - Runs `dxdiag` for OpenGL/DirectX detection
  - Uses `wmic` for GPU information
  - Checks QtWebEngine resources in OSGeo4W installation
  - Lists running QtWebEngine processes

### Linux
- **`diagnostic_webengine_linux.sh`** - Linux-specific diagnostic script
  - Uses `glxinfo` for OpenGL information
  - Uses `lspci` for GPU detection
  - Checks QtWebEngine resources in standard QGIS paths
  - Lists running QtWebEngine processes

### macOS
- **`diagnostic_webengine_mac.sh`** - macOS-specific diagnostic script
  - Uses `system_profiler` for GPU/OpenGL information
  - Checks QtWebEngine resources in QGIS.app bundle
  - Lists running QtWebEngine processes

## Usage

These scripts are automatically called by the debug dialog in the QGIS plugin. They can also be run manually:

### Windows
```batch
cd debug
diagnostic_webengine_win.bat
```

### Linux
```bash
cd debug
chmod +x diagnostic_webengine_linux.sh
./diagnostic_webengine_linux.sh
```

### macOS
```bash
cd debug
chmod +x diagnostic_webengine_mac.sh
./diagnostic_webengine_mac.sh
```

## Output Format

Each script outputs results in sections:
```
=== OpenGL Detection ===
[OpenGL/DirectX information]

=== GPU Detection ===
[GPU hardware information]

=== QtWebEngine Resources ===
[List of QtWebEngine resource files]

=== QtWebEngineProcess Running ===
[List of running QtWebEngine processes]
```

## Safety

- **Read-only operations** - No system modifications
- **Standard system commands** - No third-party dependencies
- **Timeout protected** - Scripts won't hang indefinitely
- **Error handled** - Graceful failure handling

## Integration

These scripts are integrated into the QGIS plugin's debug dialog:
- Located at: `../debug_dialog.py`
- Called via: `_check_external_diagnostics()` method
- Results displayed in: "External Tests" section

## Troubleshooting

### Script not found
- Ensure scripts are in the `debug/` folder
- Check file permissions on Linux/macOS

### Command not found
- **Windows**: Ensure `dxdiag`, `wmic`, `tasklist` are available (built-in)
- **Linux**: Install `mesa-utils` for `glxinfo`, `pciutils` for `lspci`
- **macOS**: All commands are built-in to macOS

### Permission denied
- **Linux/macOS**: Run `chmod +x diagnostic_webengine_*.sh`
- **Windows**: Batch files should run without special permissions

## Maintenance

When updating QGIS versions or paths:
1. Check resource paths in each script
2. Test on each target platform
3. Update paths if QGIS installation locations change

## Notes

- Scripts use relative paths to QGIS installations
- Output is limited to prevent flooding the debug dialog
- Scripts are designed to be safe for automated execution
