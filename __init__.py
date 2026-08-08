def classFactory(iface):
    from .core.plugin import ArcGISLikeWorkspacePlugin

    return ArcGISLikeWorkspacePlugin(iface)
