from PyQt5.QtCore import QCoreApplication
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon, QPixmap


from .plugin_pgsearch_dialog import PgSearchDialog  # ta boîte de dialogue personnalisée

import os

class PgSearchPlugin:

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None
        self.dlg = None


    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, "icon.png")  # place ton icon.png dans le dossier du plugin
        pixmap = QPixmap(icon_path).scaled(30, 33)  # ajuste la taille ici
        icon = QIcon(pixmap)

        self.action = QAction(icon, "", self.iface.mainWindow())  # pas de texte !
        self.action.setToolTip("Recherche de tables PostgreSQL")
        self.action.triggered.connect(self.run)

        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        self.action = None

    def run(self):
        if not self.dlg:
            self.dlg = PgSearchDialog()
        self.dlg.show()
        self.dlg.raise_()
        self.dlg.activateWindow()
