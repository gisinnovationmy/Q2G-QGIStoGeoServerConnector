# Package initialization file
__version__ = "4.0.0"

# Apply safe requests wrapper (default timeout) before any other module imports.
from . import safe_requests  # noqa: F401


def classFactory(iface):
    return Q2GPlugin(iface)


class Q2GPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.dialog = None
        self.action = None
        self.toolbar = None

    def initGui(self):
        from qgis.PyQt.QtGui import QIcon
        from qgis.PyQt.QtWidgets import QAction
        import os
        icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'logo.svg')
        self.action = QAction(QIcon(icon_path), 'Q2G - QGIS to GeoServer Connector', self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.triggered.connect(self.toggle_dialog)

        self.toolbar = self.iface.addToolBar('Q2GTools')
        self.toolbar.setObjectName('Q2GTools')
        self.toolbar.addAction(self.action)

        self.iface.addPluginToWebMenu('Q2G', self.action)

    def unload(self):
        self.iface.removePluginWebMenu('Q2G', self.action)
        if self.toolbar:
            self.toolbar.deleteLater()
        if self.dialog:
            self.dialog.close()

    def toggle_dialog(self):
        if self.action.isChecked():
            self.show_dialog()
        else:
            self.hide_dialog()

    def show_dialog(self):
        from .main import QGISGeoServerLayerLoader
        if self.dialog is None:
            self.dialog = QGISGeoServerLayerLoader(self.iface.mainWindow(), self.iface)
            self.dialog.finished.connect(self.on_dialog_closed)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
        self.action.setChecked(True)

    def hide_dialog(self):
        if self.dialog:
            self.dialog.close()

    def on_dialog_closed(self):
        self.action.setChecked(False)

    def run(self):
        self.show_dialog()
