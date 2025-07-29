from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont, QColor
from qgis.core import QgsVectorLayer, QgsProject
from sqlalchemy import create_engine, text
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableView, QTableWidget, QTableWidgetItem

import os

from dotenv import load_dotenv

# Chemin du dossier courant du plugin (où se trouve ce script Python)
current_dir = os.path.dirname(os.path.abspath(__file__))

# Chemin vers le dossier parent (un niveau au-dessus)
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))

# Chemin complet vers le fichier .env dans ce dossier parent
dotenv_path = os.path.join(parent_dir, '.env')

# Charger les variables d'environnement depuis ce fichier
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print(f"Attention: le fichier .env n'a pas été trouvé ici: {dotenv_path}")

host_pg = "192.168.1.7"
port_pg = "5432"
db_pg = "EPLoire"
user_pg = os.getenv('DB_USER')
mdp_pg  = os.getenv('DB_PASS')

engine = create_engine(f"postgresql://{user_pg}:{mdp_pg}@{host_pg}:{port_pg}/{db_pg}")

class PgSearchDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.resultats_list.doubleClicked.connect(self.on_result_clicked)

    def setup_ui(self):
        self.setWindowTitle("Recherche de tables PostgreSQL")
        self.resize(900, 600)

        from PyQt5.QtWidgets import QVBoxLayout, QLineEdit, QPushButton, QListView

        layout = QVBoxLayout(self)

        self.entree_nom = QLineEdit()
        self.entree_nom.setPlaceholderText("Nom ou partie du nom")
        layout.addWidget(self.entree_nom)

        self.bouton_recherche = QPushButton("Rechercher")
        layout.addWidget(self.bouton_recherche)
        self.bouton_recherche.clicked.connect(self.rechercher_tables)

        self.resultats_list = QListView()
        layout.addWidget(self.resultats_list)

        self.model = QStandardItemModel()
        self.resultats_list.setModel(self.model)

        self.bouton_metadonnees = QPushButton("Afficher les métadonnées")
        layout.addWidget(self.bouton_metadonnees)
        self.bouton_metadonnees.clicked.connect(self.afficher_metadonnees)

        self.bouton_visualiser = QPushButton("Visualiser les 20 premières lignes")
        layout.addWidget(self.bouton_visualiser)
        self.bouton_visualiser.clicked.connect(self.visualiser_donnees)

    def rechercher_tables(self):
        pattern = self.entree_nom.text().strip()
        if not pattern:
            QMessageBox.warning(self, "Champ vide", "Veuillez entrer un nom ou une partie de nom.")
            return

        query = text("""
            SELECT 'table' AS type, schemaname AS schema, tablename AS name, NULL AS column, NULL AS comment
            FROM pg_catalog.pg_tables
            WHERE tablename ILIKE :pattern

            UNION ALL

            SELECT 'view' AS type, schemaname AS schema, viewname AS name, NULL AS column, NULL AS comment
            FROM pg_catalog.pg_views
            WHERE viewname ILIKE :pattern

            UNION ALL

            SELECT 'matview' AS type, schemaname AS schema, matviewname AS name, NULL AS column, NULL AS comment
            FROM pg_catalog.pg_matviews
            WHERE matviewname ILIKE :pattern

            UNION ALL

            SELECT 'column' AS type, table_schema AS schema, table_name AS name, column_name AS column, NULL AS comment
            FROM information_schema.columns
            WHERE column_name ILIKE :pattern

            UNION ALL

            SELECT 'comment' AS type, n.nspname AS schema, c.relname AS name, NULL AS column, d.description AS comment
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_description d ON d.objoid = c.oid
            WHERE d.description ILIKE :pattern

            ORDER BY schema, name, type
        """)

        try:
            with engine.connect() as conn:
                results = conn.execute(query, {'pattern': f'%{pattern}%'}).fetchall()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la recherche :\n{e}")
            return

        self.model.clear()
        if not results:
            item = QStandardItem("🔍 Aucune correspondance trouvée.")
            item.setFlags(Qt.NoItemFlags)
            self.model.appendRow(item)
            return

        # Regroupement par schéma puis par type
        current_schema = None
        current_type = None
        for row in results:
            type_, schema, name, column, comment = row
            if schema != current_schema:
                schema_item = QStandardItem(f"----- Schéma : {schema} -----")
                schema_item.setFlags(Qt.ItemIsEnabled)  # pour qu’il soit sélectionnable
                font = QFont()
                font.setBold(True)
                schema_item.setFont(font)
                schema_item.setForeground(QColor("black"))  # texte noir, pas gris
                self.model.appendRow(schema_item)
                current_schema = schema
                current_type = None
            if type_ != current_type:
                type_label = {
                    'table': 'Tables',
                    'view': 'Vues',
                    'matview': 'Vues matérialisées',
                    'column': 'Colonnes',
                    'comment': 'Commentaires',
                }.get(type_, type_)
                type_item = QStandardItem(f"  • {type_label}")
                type_item.setFlags(Qt.ItemIsEnabled)
                font = QFont()
                font.setItalic(True)
                type_item.setFont(font)
                type_item.setForeground(QColor("black"))
                self.model.appendRow(type_item)
                current_type = type_

            if type_ in ('table', 'view', 'matview'):
                display_text = f"    - {name}"
                item = QStandardItem(display_text)
                item.setData((schema, name, type_), Qt.UserRole)
                item.setForeground(QColor("black"))
            elif type_ == 'column':
                display_text = f"    - {name}.{column}"
                item = QStandardItem(display_text)
                # On peut autoriser la sélection ici aussi si besoin
                item.setFlags(Qt.ItemIsEnabled)
                item.setForeground(QColor("black"))
            elif type_ == 'comment':
                display_text = f"    - {name} : {comment[:50]}{'...' if comment and len(comment)>50 else ''}"
                item = QStandardItem(display_text)
                item.setFlags(Qt.ItemIsEnabled)
                item.setForeground(QColor("black"))
            else:
                display_text = f"    - {name}"
                item = QStandardItem(display_text)
                item.setFlags(Qt.ItemIsEnabled)
                item.setForeground(QColor("black"))

            self.model.appendRow(item)

    def get_geometry_column(self, schema, table):
        query = text("""
            SELECT f_geometry_column
            FROM geometry_columns
            WHERE f_table_schema = :schema
              AND f_table_name = :table
            LIMIT 1
        """)
        try:
            with engine.connect() as conn:
                res = conn.execute(query, {'schema': schema, 'table': table}).fetchone()
                if res:
                    return res[0]
        except Exception as e:
            print(f"Erreur get_geometry_column: {e}")
        return None

    def charger_couche(self, schema, table):
        geom_col = self.get_geometry_column(schema, table)
        if geom_col:
            uri = f"dbname='{db_pg}' host={host_pg} port={port_pg} user='{user_pg}' password='{mdp_pg}' schema='{schema}' table='{table}' ({geom_col}) sql="
            layer = QgsVectorLayer(uri, f"{schema}.{table}", "postgres")
        else:
            uri = f"dbname='{db_pg}' host={host_pg} port={port_pg} user='{user_pg}' password='{mdp_pg}' schema='{schema}' table='{table}' sql="
            layer = QgsVectorLayer(uri, f"{schema}.{table}", "postgres")

        if not layer.isValid():
            QMessageBox.critical(self, "Erreur", f"Impossible de charger la couche {schema}.{table}")
            return False

        QgsProject.instance().addMapLayer(layer)
        return True

    def on_result_clicked(self, index):
        item = self.model.itemFromIndex(index)
        data = item.data(Qt.UserRole)
        if data:
            schema, table, type_ = data
            if type_ in ('table', 'view', 'matview'):
                self.charger_couche(schema, table)

    def afficher_metadonnees(self):
        indexes = self.resultats_list.selectedIndexes()
        if not indexes:
            QMessageBox.information(self, "Info", "Sélectionnez une table ou vue dans la liste.")
            return

        item = self.model.itemFromIndex(indexes[0])
        data = item.data(Qt.UserRole)
        if not data:
            QMessageBox.information(self, "Info", "Sélectionnez une table ou vue dans la liste.")
            return

        schema, table, _ = data

        query = text("""
            SELECT
                c.relkind AS type_relation,
                r.rolname AS proprietaire,
                d.description AS commentaire
            FROM
                pg_class c
            JOIN
                pg_namespace n ON n.oid = c.relnamespace
            JOIN
                pg_roles r ON r.oid = c.relowner
            LEFT JOIN
                pg_description d ON d.objoid = c.oid
            WHERE
                n.nspname = :schema
                AND c.relname = :table
        """)

        geom_query = text("""
            SELECT
                f_geometry_column,
                type,
                srid
            FROM
                geometry_columns
            WHERE
                f_table_schema = :schema
                AND f_table_name = :table
            LIMIT 1
        """)

        try:
            with engine.connect() as conn:
                result = conn.execute(query, {'schema': schema, 'table': table}).fetchone()
                geom_result = conn.execute(geom_query, {'schema': schema, 'table': table}).fetchone()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la récupération des métadonnées :\n{e}")
            return

        if not result:
            QMessageBox.information(self, "Métadonnées", "Aucune information trouvée.")
            return

        type_relation_map = {
            'r': 'Table',
            'v': 'Vue',
            'm': 'Vue matérialisée',
            'i': 'Index',
            'S': 'Séquence',
            't': 'Type',
            'c': 'Composite',
            'f': 'Foreign Table',
            'p': 'Partition',
        }
        type_relation = type_relation_map.get(result.type_relation, result.type_relation)
        proprietaire = result.proprietaire if result.proprietaire else "Inconnu"
        commentaire = result.commentaire if result.commentaire else "(Aucun commentaire)"

        data_to_display = [
            ("Type de relation", type_relation),
            ("Propriétaire", proprietaire),
            ("Commentaire", commentaire),
        ]

        if geom_result:
            data_to_display.extend([
                ("Colonne géométrique", geom_result.f_geometry_column),
                ("Type de géométrie", geom_result.type),
                ("SRID", str(geom_result.srid)),
            ])

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Métadonnées : {schema}.{table}")
        layout = QVBoxLayout()
        dlg.setLayout(layout)

        table_widget = QTableWidget(len(data_to_display), 2)
        table_widget.setHorizontalHeaderLabels(["Propriété", "Valeur"])
        for row, (prop, val) in enumerate(data_to_display):
            table_widget.setItem(row, 0, QTableWidgetItem(prop))
            table_widget.setItem(row, 1, QTableWidgetItem(val))
        layout.addWidget(table_widget)

        dlg.exec_()

    def visualiser_donnees(self):
        indexes = self.resultats_list.selectedIndexes()
        if not indexes:
            QMessageBox.information(self, "Info", "Sélectionnez une table ou vue dans la liste.")
            return

        item = self.model.itemFromIndex(indexes[0])
        data = item.data(Qt.UserRole)
        if not data:
            QMessageBox.information(self, "Info", "Sélectionnez une table ou vue dans la liste.")
            return

        schema, table, _ = data

        query = text(f"SELECT * FROM {schema}.{table} LIMIT 20")

        try:
            with engine.connect() as conn:
                results = conn.execute(query).fetchall()
                columns = results[0].keys() if results else []
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la récupération des données :\n{e}")
            return

        if not results:
            QMessageBox.information(self, "Info", "Aucune donnée trouvée.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"20 premières lignes de {schema}.{table}")
        layout = QVBoxLayout()
        dlg.setLayout(layout)

        table_widget = QTableWidget(len(results), len(columns))
        table_widget.setHorizontalHeaderLabels(columns)
        for row_idx, row in enumerate(results):
            for col_idx, col in enumerate(columns):
                val = str(row[col])
                table_widget.setItem(row_idx, col_idx, QTableWidgetItem(val))
        layout.addWidget(table_widget)

        dlg.exec_()


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    dlg = PgSearchDialog()
    dlg.show()
    sys.exit(app.exec_())

        






