"""
Helper module to detect QGIS layer formats and determine appropriate upload methods.
This version is updated to use the GeoServer Importer extension for all supported formats.
"""

import os
from qgis.core import QgsVectorLayer, QgsRasterLayer

# Debug flag - set to False for production (faster startup)
DEBUG_LAYER_FORMAT = False

# Define formats that ARE ACTUALLY SUPPORTED by the GeoServer Importer extension.
# Only these formats can be uploaded directly to the importer.
IMPORTER_FORMATS = {
    'Shapefile': ['.shp'],
    'GeoTIFF': ['.tif', '.tiff'],
    'GeoPackage': ['.gpkg'],  # GeoPackage databases
}

# Define formats that are NOT supported by GeoServer Importer.
# These formats will be converted to GeoPackage before uploading.
UNSUPPORTED_FORMATS = {
    'SQLite': ['.sqlite', '.db'],  # SQLite databases - convert to GeoPackage
    'GeoJSON': ['.geojson', '.json'],  # GeoJSON - convert to GeoPackage
}

def get_layer_provider_info(layer):
    """
    Get information about a QGIS layer's data provider and source format.
    This function now centralizes format detection and directs supported formats
    to use the 'importer' upload method.

    Args:
        layer (QgsMapLayer): The QGIS layer to analyze.

    Returns:
        dict: Dictionary containing provider info.
    """
    # Get the full source and extract the file path
    full_source = layer.source()
    provider_type = layer.dataProvider().name() if layer.dataProvider() else 'unknown'
    
    # Extract source path - handle different formats:
    # - File paths: /path/to/file.shp
    # - SQLite: dbname='/path/to/file.sqlite' table="tablename" (geometry)
    # - PostGIS: postgresql://user:pass@host/database?table=tablename
    # - GeoPackage: /path/to/file.gpkg|layername=layer1
    source_path = full_source
    
    # For SQLite, extract the file path from dbname parameter
    if 'dbname=' in full_source:
        try:
            # Extract dbname value: dbname='path/to/file.sqlite' -> path/to/file.sqlite
            dbname_start = full_source.find("dbname='") + len("dbname='")
            dbname_end = full_source.find("'", dbname_start)
            if dbname_end > dbname_start:
                source_path = full_source[dbname_start:dbname_end]
        except:
            pass
    else:
        # For other formats, use standard extraction
        source_path = full_source.split('|')[0].split('?')[0] if '|' in full_source else full_source.split('?')[0]
    
    # Debug logging to understand the source format
    if DEBUG_LAYER_FORMAT:
        print(f"DEBUG FORMAT: Layer '{layer.name()}' - Provider: {provider_type}, Full source: {full_source}")
        print(f"DEBUG FORMAT: Extracted source path: {source_path}")
        print(f"DEBUG FORMAT: Is source_path a file? {os.path.isfile(source_path)}")
        print(f"DEBUG FORMAT: Is source_path a directory? {os.path.isdir(source_path)}")
        print(f"DEBUG FORMAT: Source path ends with .gpkg? {source_path.lower().endswith('.gpkg')}")
    
    # Check if this is a vector layer
    if isinstance(layer, QgsVectorLayer):
        provider_type = layer.dataProvider().name()
        
        if DEBUG_LAYER_FORMAT:
            print(f"DEBUG: Layer '{layer.name()}' - Provider: {provider_type}, Source: {full_source}")
            print(f"DEBUG: Extracted source path: {source_path}")

        # Handle PostGIS layers
        if provider_type == 'postgres':
            try:
                # Use QgsDataSourceUri to properly parse PostGIS connection string
                from qgis.core import QgsDataSourceUri, QgsProviderRegistry
                uri = QgsDataSourceUri(full_source)
                
                # Extract connection parameters
                pg_host = uri.host()
                pg_database = uri.database()
                pg_table = uri.table()
                
                # If host is missing but we have authcfg, try to get it from QGIS connections
                if not pg_host and uri.authConfigId():
                    try:
                        metadata = QgsProviderRegistry.instance().providerMetadata('postgres')
                        if metadata:
                            connections = metadata.connections()
                            for conn_name, connection in connections.items():
                                if hasattr(connection, 'uri'):
                                    conn_uri = QgsDataSourceUri(connection.uri())
                                    if conn_uri.database() == pg_database:
                                        pg_host = conn_uri.host()
                                        break
                    except:
                        pass
                
                # If still no host, assume localhost (common for local PostGIS)
                if not pg_host:
                    pg_host = 'localhost'
                
                # Check for required parameters
                if not pg_database or not pg_table:
                    return {
                        'provider_type': 'postgres',
                        'source': layer.source(),
                        'is_supported_native': False,
                        'native_format': 'PostGIS (Invalid)',
                        'upload_method': 'unsupported',
                        'error': f'Missing required connection parameters: host={pg_host}, database={pg_database}, table={pg_table}'
                    }
                
                return {
                    'provider_type': 'postgres',
                    'source': layer.source(),
                    'is_supported_native': True,
                    'native_format': 'PostGIS',
                    'upload_method': 'postgis',
                    'connection_params': {
                        'host': pg_host,
                        'database': pg_database,
                        'table': pg_table
                    }
                }
            except Exception as e:
                return {
                    'provider_type': 'postgres',
                    'source': layer.source(),
                    'is_supported_native': False,
                    'native_format': 'PostGIS (Error)',
                    'upload_method': 'unsupported',
                    'error': f'Failed to parse connection string: {str(e)}'
                }

        # Check file-based formats by extension FIRST (most reliable)
        if DEBUG_LAYER_FORMAT:
            print(f"DEBUG: Checking extensions for source_path: {source_path}")
        
        # Check UNSUPPORTED formats FIRST - these need GeoPackage conversion
        for format_name, extensions in UNSUPPORTED_FORMATS.items():
            if DEBUG_LAYER_FORMAT:
                print(f"DEBUG: Checking unsupported format {format_name} with extensions {extensions}")
            for ext in extensions:
                if DEBUG_LAYER_FORMAT:
                    print(f"DEBUG: Checking if {source_path.lower()} ends with {ext.lower()}")
                if source_path.lower().endswith(ext.lower()):
                    if DEBUG_LAYER_FORMAT:
                        print(f"DEBUG: MATCHED UNSUPPORTED FORMAT {format_name} for {source_path} (extension: {ext})")
                    # These formats will be converted to GeoPackage by fallback method
                    return {
                        'provider_type': provider_type,
                        'source': layer.source(),
                        'is_supported_native': False,
                        'native_format': format_name,
                        'upload_method': 'unsupported'
                    }
        
        # Then check SUPPORTED importer formats
        for format_name, extensions in IMPORTER_FORMATS.items():
            if DEBUG_LAYER_FORMAT:
                print(f"DEBUG: Checking importer format {format_name} with extensions {extensions}")
            for ext in extensions:
                if DEBUG_LAYER_FORMAT:
                    print(f"DEBUG: Checking if {source_path.lower()} ends with {ext.lower()}")
                if source_path.lower().endswith(ext.lower()):
                    if DEBUG_LAYER_FORMAT:
                        print(f"DEBUG: MATCHED IMPORTER FORMAT {format_name} for {source_path} (extension: {ext})")
                    
                    # All importer formats use the importer directly
                    return {
                        'provider_type': provider_type,
                        'source': layer.source(),
                        'is_supported_native': True,
                        'native_format': format_name,
                        'upload_method': 'importer'
                    }

        # Handle directory-based layers ONLY if no file extension match
        if provider_type == 'ogr' and os.path.isdir(source_path):
            if DEBUG_LAYER_FORMAT:
                print(f"DEBUG: Checking directory {source_path}")
            # Check if directory contains .gpkg files (GeoPackage)
            try:
                dir_contents = os.listdir(source_path)
                if DEBUG_LAYER_FORMAT:
                    print(f"DEBUG: Directory contents: {dir_contents}")
                if any(f.lower().endswith('.gpkg') for f in dir_contents):
                    if DEBUG_LAYER_FORMAT:
                        print(f"DEBUG: Found .gpkg files in directory - returning GeoPackage")
                    return {
                        'provider_type': 'ogr',
                        'source': layer.source(),
                        'is_supported_native': True,
                        'native_format': 'GeoPackage',
                        'upload_method': 'importer'
                    }
                # Check for shapefile components
                elif any(f.lower().endswith('.shp') for f in dir_contents):
                    if DEBUG_LAYER_FORMAT:
                        print(f"DEBUG: Found .shp files in directory - returning Shapefile")
                    return {
                        'provider_type': 'ogr',
                        'source': layer.source(),
                        'is_supported_native': True,
                        'native_format': 'Shapefile',
                        'upload_method': 'importer'
                    }
                # Default to Shapefile for other directory-based layers
                else:
                    if DEBUG_LAYER_FORMAT:
                        print(f"DEBUG: No specific files found in directory - defaulting to Shapefile")
                    return {
                        'provider_type': 'ogr',
                        'source': layer.source(),
                        'is_supported_native': True,
                        'native_format': 'Shapefile',
                        'upload_method': 'importer'
                    }
            except Exception as e:
                if DEBUG_LAYER_FORMAT:
                    print(f"DEBUG: Error reading directory {source_path}: {e}")
                # If we can't read directory, assume Shapefile
                return {
                    'provider_type': 'ogr',
                    'source': layer.source(),
                    'is_supported_native': True,
                    'native_format': 'Shapefile',
                    'upload_method': 'importer'
                }
        else:
            if DEBUG_LAYER_FORMAT:
                print(f"DEBUG: Not a directory or not ogr provider - provider_type: {provider_type}, isdir: {os.path.isdir(source_path)}")

    # Check for raster layers
    elif isinstance(layer, QgsRasterLayer):
        # Check GeoTIFF formats
        for ext in IMPORTER_FORMATS.get('GeoTIFF', []):
            if source_path.lower().endswith(ext.lower()):
                return {
                    'provider_type': 'gdal',
                    'source': layer.source(),
                    'is_supported_native': True,
                    'native_format': 'GeoTIFF',
                    'upload_method': 'importer'
                }

    # Fallback for unsupported or unrecognized layers
    return {
        'provider_type': provider_type,
        'source': layer.source(),
        'is_supported_native': False,
        'native_format': 'Unsupported',
        'upload_method': 'unsupported'
    }
