def classFactory(iface):
    from .main_plugin import ExportarPontosPlugin
    return ExportarPontosPlugin(iface)
