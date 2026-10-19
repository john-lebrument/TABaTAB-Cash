"""Modeless workspace for comparing independent groups of folders."""
from pathlib import Path
from PyQt6.QtCore import Qt, QThreadPool, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QAbstractItemView, QFileDialog, QComboBox, QGroupBox, QCheckBox,
    QTreeWidget, QTreeWidgetItem, QMessageBox, QProgressBar)
from src.utils.cross_duplicates import CrossDuplicateScan, recycle_selected
from src.utils.windows_integration import reveal_in_explorer


class FolderDropList(QListWidget):
    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setMinimumHeight(90)

    def paths(self):
        return [self.item(i).text() for i in range(self.count())]

    def add_paths(self, paths):
        known = {str(Path(p).resolve()).casefold() for p in self.paths()}
        for path in paths:
            p = Path(path)
            if p.is_dir() and str(p.resolve()).casefold() not in known:
                value = str(p.resolve())
                self.addItem(value)
                self.item(self.count() - 1).setToolTip(value)
                known.add(value.casefold())
        self.changed.emit()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(u.isLocalFile() and Path(u.toLocalFile()).is_dir() for u in event.mimeData().urls()):
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dropEvent(self, event):
        self.add_paths([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()])
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()

    def remove_selected(self):
        for item in self.selectedItems():
            self.takeItem(self.row(item))
        self.changed.emit()


class CrossDuplicatesDialog(QDialog):
    files_recycled = pyqtSignal()

    def __init__(self, config, favorites, parent=None):
        super().__init__(parent)
        self.config = config
        self.scan = None
        self.groups = []
        self.setWindowTitle('Doublons croisés')
        self.resize(1000, 720)
        layout = QVBoxLayout(self)
        intro = QLabel('Comparez le contenu exact des fichiers (SHA-256), quels que soient leurs noms et extensions.\n'
                       'Glissez des dossiers depuis l’arborescence dans les groupes A et B, ou utilisez Parcourir / Favoris.')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.setup_panel = QGroupBox('Dossiers à comparer')
        setup = QVBoxLayout(self.setup_panel)
        columns = QHBoxLayout()
        self.left, self.right = FolderDropList(), FolderDropList()
        for title, listing in [('A — Dossiers de départ', self.left), ('B — Dossiers de comparaison', self.right)]:
            box = QGroupBox(title)
            col = QVBoxLayout(box)
            col.addWidget(listing)
            buttons = QHBoxLayout()
            browse = QPushButton('Parcourir…')
            browse.clicked.connect(lambda checked=False, target=listing: self.browse(target))
            buttons.addWidget(browse)
            combo = QComboBox()
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(12)
            combo.addItem('Ajouter un favori…', '')
            for label, path in favorites:
                combo.addItem(label + ' — ' + path, path)
            combo.activated.connect(lambda index, c=combo, target=listing: self.add_favorite(c, index, target))
            buttons.addWidget(combo, 1)
            remove = QPushButton('Retirer')
            remove.clicked.connect(listing.remove_selected)
            buttons.addWidget(remove)
            col.addLayout(buttons)
            columns.addWidget(box)
        setup.addLayout(columns)
        self.recursive = QCheckBox('Inclure les sous-dossiers (liens et jonctions ignorés)')
        self.recursive.setChecked(True)
        setup.addWidget(self.recursive)
        layout.addWidget(self.setup_panel)
        controls = QHBoxLayout()
        self.start_button = QPushButton('Rechercher les doublons')
        self.start_button.clicked.connect(self.start_scan)
        self.cancel_button = QPushButton('Annuler la recherche')
        self.cancel_button.clicked.connect(self.cancel_scan)
        self.cancel_button.setEnabled(False)
        controls.addWidget(self.start_button)
        controls.addWidget(self.cancel_button)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        controls.addWidget(self.progress, 1)
        layout.addLayout(controls)
        self.status = QLabel('Choisissez vos dossiers, puis lancez la recherche.')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.results = QTreeWidget()
        self.results.setHeaderLabels(['Groupe / Fichier à sélectionner', 'Taille (octets)', 'Chemin complet'])
        self.results.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.results.setColumnWidth(0, 280)
        self.results.setColumnWidth(1, 110)
        self.results.itemDoubleClicked.connect(lambda item, column: self.open_selected())
        layout.addWidget(self.results, 1)
        actions = QHBoxLayout()
        for label, callback in [('Ouvrir le fichier', self.open_selected), ('Afficher dans l’Explorateur', self.reveal_selected),
                                ('Copier les chemins', self.copy_selected)]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            actions.addWidget(button)
        self.recycle_button = QPushButton('Mettre les fichiers cochés à la corbeille')
        self.recycle_button.clicked.connect(self.recycle_checked)
        self.recycle_button.setEnabled(False)
        actions.addWidget(self.recycle_button)
        layout.addLayout(actions)
        close = QPushButton('Fermer')
        close.clicked.connect(self.close)
        layout.addWidget(close)
        saved = config.get('cross_duplicates', {}) if config else {}
        # Keep unavailable folders visible so that a disconnected disk isn't forgotten.
        for listing, key in [(self.left, 'left'), (self.right, 'right')]:
            for path in saved.get(key, []):
                if isinstance(path, str):
                    listing.addItem(path)
            listing.changed.connect(self.save_choices)
        self.recursive.setChecked(saved.get('recursive', True))
        self.recursive.toggled.connect(self.save_choices)

    def save_choices(self):
        if self.config:
            self.config.set('cross_duplicates', dict(left=self.left.paths(), right=self.right.paths(),
                recursive=self.recursive.isChecked()))

    def browse(self, target):
        path = QFileDialog.getExistingDirectory(self, 'Ajouter un dossier', target.paths()[-1] if target.count() else '')
        if path:
            target.add_paths([path])

    def add_favorite(self, combo, index, target):
        path = combo.itemData(index)
        if path:
            if Path(path).is_dir():
                target.add_paths([path])
            else:
                QMessageBox.warning(self, 'Dossier inaccessible', path)
        combo.setCurrentIndex(0)

    def use_context_folders(self, paths):
        self.left.clear()
        self.left.add_paths(paths)
        self.save_choices()

    def start_scan(self):
        if self.scan:
            return
        left = self.left.paths()
        right = self.right.paths()
        if not left or not right:
            QMessageBox.information(self, 'Dossiers manquants', 'Ajoutez au moins un dossier dans chaque groupe utilisé.')
            return
        invalid = [p for p in left + right if not Path(p).is_dir()]
        if invalid:
            QMessageBox.warning(self, 'Dossiers inaccessibles', '\n'.join(invalid))
            return
        self.save_choices()
        self.results.clear()
        self.groups = []
        self.recycle_button.setEnabled(False)
        self.scan = CrossDuplicateScan(left, right, self.recursive.isChecked())
        self.scan.signals.finished.connect(self.scan_finished)
        self.setup_panel.setEnabled(False)
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.show()
        self.status.setText('Recherche en cours… Lecture des dossiers et comparaison du contenu.')
        QThreadPool.globalInstance().start(self.scan)

    def cancel_scan(self):
        if self.scan:
            self.scan.cancelled.set()
            self.status.setText('Annulation en cours…')

    def scan_finished(self, groups, errors):
        cancelled = self.scan.cancelled.is_set()
        self.scan = None
        self.setup_panel.setEnabled(True)
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress.hide()
        if cancelled or groups is None:
            self.status.setText('Recherche annulée.')
            return
        self.groups = groups
        self.populate_results()
        message = f'{len(groups)} groupe(s) de doublons, {sum(len(p) for d, p in groups)} fichier(s). Aucun fichier coché automatiquement.'
        if errors:
            message += f'\n{len(errors)} erreur(s) :\n' + '\n'.join(errors[:8])
        self.status.setText(message)
        self.status.setToolTip('\n'.join(errors))

    def populate_results(self):
        self.results.clear()
        for index, (digest, paths) in enumerate(self.groups, 1):
            group = QTreeWidgetItem(self.results, [f'Groupe {index} — {len(paths)} fichiers identiques'])
            for path in paths:
                path = Path(path)
                try:
                    size = str(path.stat().st_size)
                except OSError:
                    size = 'Indisponible'
                item = QTreeWidgetItem(group, [path.name, size, str(path)])
                item.setData(0, Qt.ItemDataRole.UserRole, str(path))
                item.setCheckState(0, Qt.CheckState.Unchecked)
                item.setToolTip(0, str(path))
            group.setExpanded(True)
        self.recycle_button.setEnabled(bool(self.groups))

    def selected_paths(self):
        return [p for item in self.results.selectedItems() if (p := item.data(0, Qt.ItemDataRole.UserRole))]

    def open_selected(self):
        for path in self.selected_paths():
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def reveal_selected(self):
        for path in self.selected_paths():
            reveal_in_explorer(path)

    def copy_selected(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText('\n'.join(self.selected_paths()))

    def recycle_checked(self):
        selected = []
        for i in range(self.results.topLevelItemCount()):
            group = self.results.topLevelItem(i)
            checked = [group.child(j).data(0, Qt.ItemDataRole.UserRole) for j in range(group.childCount())
                       if group.child(j).checkState(0) == Qt.CheckState.Checked]
            if len(checked) == group.childCount():
                QMessageBox.warning(self, 'Conserver une référence', 'Décochez au moins un fichier dans chaque groupe.')
                return
            selected.extend(checked)
        if not selected:
            QMessageBox.information(self, 'Aucun fichier coché', 'Cochez les fichiers à envoyer à la corbeille.')
            return
        removed, errors = recycle_selected(self.groups, selected)
        self.groups = [(d, [p for p in paths if str(p) not in removed]) for d, paths in self.groups]
        self.groups = [(d, p) for d, p in self.groups if len(p) > 1]
        self.populate_results()
        self.status.setText(f'{len(removed)} fichier(s) envoyé(s) à la corbeille.' + ('\n' + '\n'.join(errors) if errors else ''))
        if removed:
            self.files_recycled.emit()

    def reject(self):
        self.cancel_scan()
        self.save_choices()
        super().reject()

    def closeEvent(self, event):
        self.cancel_scan()
        self.save_choices()
        super().closeEvent(event)
