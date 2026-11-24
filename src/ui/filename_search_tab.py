from pathlib import Path

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, QThreadPool, pyqtSignal
from PyQt6.QtWidgets import QAbstractItemView, QHBoxLayout, QLabel, QPushButton, QTableView, QVBoxLayout, QWidget

from src.utils.filename_search import FilenameSearch


class SearchResultsModel(QAbstractTableModel):
    headers = ('Nom', 'Dossier')

    def __init__(self, parent):
        super().__init__(parent)
        self.paths = []

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.paths)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.headers)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        path = self.paths[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return Path(path).name if index.column() == 0 else str(Path(path).parent)
        if role == Qt.ItemDataRole.ToolTipRole:
            return path

    def replace(self, paths):
        self.beginResetModel()
        self.paths = paths
        self.endResetModel()


class FilenameSearchTab(QWidget):
    open_image = pyqtSignal(list, str)
    open_folder = pyqtSignal(str)

    def __init__(self, query, parent=None):
        super().__init__(parent)
        self.query = query
        self.job = None
        self.using_index = True
        layout = QVBoxLayout(self)
        tools = QHBoxLayout()
        self.status = QLabel(self)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        tools.addWidget(self.status, 1)
        self.folder_button = QPushButton('Ouvrir le dossier', self)
        self.folder_button.setEnabled(False)
        self.folder_button.clicked.connect(self._open_current_folder)
        tools.addWidget(self.folder_button)
        self.cancel_button = QPushButton('Annuler', self)
        self.cancel_button.clicked.connect(self.cancel)
        tools.addWidget(self.cancel_button)
        layout.addLayout(tools)
        self.model = SearchResultsModel(self)
        self.table = QTableView(self)
        self.table.setModel(self.model)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 300)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.selectionModel().currentChanged.connect(
            lambda current, _: self.folder_button.setEnabled(current.isValid()))
        self.table.activated.connect(self._open_image)
        layout.addWidget(self.table)

    def refresh(self):
        if self.job is not None:
            return
        self.using_index = True
        self.status.setText(f'« {self.query} » — recherche dans l’index Everything…')
        self.cancel_button.show()
        self.job = FilenameSearch(self.query)
        self.job.signals.fallback.connect(self._fallback)
        self.job.signals.finished.connect(self._finished)
        self.destroyed.connect(self.job.cancelled.set)
        QThreadPool.globalInstance().start(self.job)

    def cancel(self):
        if self.job:
            self.job.cancelled.set()

    def _fallback(self):
        self.using_index = False
        self.status.setText(f'« {self.query} » — Everything indisponible. Parcours des lecteurs locaux…')

    def _finished(self, paths, cancelled, error):
        self.destroyed.disconnect(self.job.cancelled.set)
        self.job = None
        self.cancel_button.hide()
        self.model.replace(paths)
        self.folder_button.setEnabled(False)
        source = 'Index Everything' if self.using_index else 'Lecteurs locaux accessibles'
        message = f'{len(paths):,} image(s) · {source}'.replace(',', ' ')
        if cancelled:
            message += ' · recherche annulée'
        if error:
            message += f' · {error}'
        self.status.setText(f'« {self.query} » — {message}')

    def _open_image(self, index):
        if index.isValid():
            self.open_image.emit(self.model.paths, self.model.paths[index.row()])

    def _open_current_folder(self):
        index = self.table.currentIndex()
        if index.isValid():
            self.open_folder.emit(str(Path(self.model.paths[index.row()]).parent))
