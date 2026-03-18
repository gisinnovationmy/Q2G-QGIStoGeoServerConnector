# -*- coding: utf-8 -*-

__version__ = '0.9.4'

# Define the plugin name here
__plugin_name__ = 'Q2G - QGIS to GeoServer Connector'


def classFactory(iface):
    """Load QGISGeoServerLayerLoader class from main.py.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    from .main import QGISGeoServerLayerLoader
    return QGISGeoServerLayerLoader(iface)
