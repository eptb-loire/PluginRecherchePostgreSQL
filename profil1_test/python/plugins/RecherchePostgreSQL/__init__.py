def classFactory(iface):
    from .plugin_pgsearch import PgSearchPlugin
    return PgSearchPlugin(iface)