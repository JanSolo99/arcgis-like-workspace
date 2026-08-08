def classFactory(iface):
    from .arcgis_like_workspace import ArcGISLikeWorkspacePlugin

    return ArcGISLikeWorkspacePlugin(iface)
