import os
from pathlib import Path
from threading import Event

from PyQt6.QtCore import QAbstractListModel, QModelIndex, QObject, QRunnable, QSize, Qt, QThreadPool, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QListView, QPushButton, QStyle,
    QStyledItemDelegate, QStyleOptionViewItem, QVBoxLayout, QWidget,
)

from src.utils.filename_search import FilenameSearch


class SearchResultsModel(QAbstractListModel):
    def __init__(self, parent):
        super().__init__(parent)
        self.paths = []
        self.rows = {}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.paths)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        path = self.paths[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return os.path.basename(path)
        if role in (Qt.ItemDataRole.ToolTipRole, Qt.ItemDataRole.UserRole):
            return path

    def replace(self, paths):
        self.beginResetModel()
        self.paths = paths
        self.rows = {path: row for row, path in enumerate(paths)}
        self.endResetModel()


class SearchThumbnailDelegate(QStyledItemDelegate):
    def __init__(self, view, manager, size):
        super().__init__(view)
        self.view = view
        self.manager = manager
        self.size = size
        self.failed = set()
        self.placeholder = view.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        manager.thumbnail_ready.connect(self._ready)
        manager.signals.error.connect(self._failed)

    def paint(self, painter, option, index):
        item = QStyleOptionViewItem(option)
        self.initStyleOption(item, index)
        path = index.data(Qt.ItemDataRole.UserRole)
        pixmap = None if path in self.failed else self.manager.get_thumbnail(path, self.size)
        item.icon = QIcon(pixmap) if pixmap is not None else self.placeholder
        item.features |= QStyleOptionViewItem.ViewItemFeature.HasDecoration
        item.decorationPosition = QStyleOptionViewItem.Position.Top
        item.decorationSize = QSize(self.size, self.size)
        self.view.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, item, painter, self.view)

    def sizeHint(self, option, index):
        return QSize(self.size + 20, self.size + 46)

    def _ready(self, path, pixmap, size, width, height):
        row = self.view.model().rows.get(path)
        if size == self.size and row is not None:
            self.view.update(self.view.model().index(row, 0))

    def _failed(self, path, size, error):
        if size == self.size and path in self.view.model().rows:
            self.failed.add(path)


class SizeSignals(QObject):
    finished = pyqtSignal(object)


class FileSizes(QRunnable):
    def __init__(self, paths):
        super().__init__()
        self.paths = paths
        self.cancelled = Event()
        self.signals = SizeSignals()

    def run(self):
        self.sizes = {}
        for path in self.paths:
            if self.cancelled.is_set():
                break
            try:
                self.sizes[path] = os.stat(path).st_size
            except OSError:
                pass
        self.signals.finished.emit(self)


class FilenameSearchTab(QWidget):
    open_image = pyqtSignal(list, str)
    open_folder = pyqtSignal(str)

    def __init__(self, query, manager, size=150, parent=None):
        super().__init__(parent)
        self.query = query
        self.job = None
        self.size_job = None
        self.sizes = None
        self.using_index = True
        layout = QVBoxLayout(self)
        tools = QHBoxLayout()
        self.status = QLabel(self)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        tools.addWidget(self.status, 1)
        self.sort = QComboBox(self)
        for label, key in [('Nom', 'name'), ('Taille', 'size'), ('Chemin', 'path')]:
            self.sort.addItem(label, key)
        self.sort.setAccessibleName('Trier les résultats par')
        tools.addWidget(QLabel('Trier par', self))
        tools.addWidget(self.sort)
        self.order = QComboBox(self)
        self.order.addItem('Croissant ↑', False)
        self.order.addItem('Décroissant ↓', True)
        self.order.setAccessibleName('Ordre du tri')
        tools.addWidget(self.order)
        self.sizing = QLabel('Lecture des tailles…', self)
        self.sizing.hide()
        tools.addWidget(self.sizing)
        self.folder_button = QPushButton('Ouvrir le dossier', self)
        self.folder_button.setEnabled(False)
        self.folder_button.clicked.connect(self._open_current_folder)
        tools.addWidget(self.folder_button)
        self.cancel_button = QPushButton('Annuler', self)
        self.cancel_button.clicked.connect(self.cancel)
        tools.addWidget(self.cancel_button)
        layout.addLayout(tools)

        self.model = SearchResultsModel(self)
        self.grid = QListView(self)
        self.grid.setModel(self.model)
        self.grid.setViewMode(QListView.ViewMode.IconMode)
        self.grid.setResizeMode(QListView.ResizeMode.Adjust)
        self.grid.setMovement(QListView.Movement.Static)
        self.grid.setLayoutMode(QListView.LayoutMode.Batched)
        self.grid.setUniformItemSizes(True)
        self.grid.setWordWrap(True)
        self.grid.setIconSize(QSize(size, size))
        self.grid.setGridSize(QSize(size + 24, size + 52))
        self.preview = SearchThumbnailDelegate(self.grid, manager, size)
        self.grid.setItemDelegate(self.preview)
        self.grid.selectionModel().currentChanged.connect(
            lambda current, _: self.folder_button.setEnabled(current.isValid()))
        self.grid.activated.connect(self._open_image)
        self.sort.currentIndexChanged.connect(self._sort_results)
        self.order.currentIndexChanged.connect(self._sort_results)
        layout.addWidget(self.grid)

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
        if self.size_job is not None:
            self.size_job.cancelled.set()
            self.size_job = None
        self.sizes = None
        self.preview.failed.clear()
        self.model.replace(paths)
        self.folder_button.setEnabled(False)
        self._sort_results()
        source = 'Index Everything' if self.using_index else 'Lecteurs locaux accessibles'
        message = f'{len(paths):,} image(s) · {source}'.replace(',', ' ')
        if cancelled:
            message += ' · recherche annulée'
        if error:
            message += f' · {error}'
        self.status.setText(f'« {self.query} » — {message}')

    def _sort_results(self):
        criterion = self.sort.currentData()
        paths = self.model.paths
        by_size = criterion == 'size' and bool(paths)
        pending_sizes = by_size and self.sizes is None
        self.sizing.setVisible(pending_sizes)
        if pending_sizes:
            if self.size_job is None:
                self.size_job = FileSizes(paths)
                self.size_job.signals.finished.connect(self._sizes_ready)
                self.destroyed.connect(self.size_job.cancelled.set)
                QThreadPool.globalInstance().start(self.size_job)
            return
        reverse = self.order.currentData()
        selected = self.grid.currentIndex().data(Qt.ItemDataRole.UserRole)
        if by_size:
            known = [path for path in paths if path in self.sizes]
            ordered = sorted(known, key=lambda path: (self.sizes[path], path.casefold()), reverse=reverse)
            ordered.extend(sorted((path for path in paths if path not in self.sizes), key=str.casefold))
        elif criterion == 'path':
            ordered = sorted(paths, key=str.casefold, reverse=reverse)
        else:
            ordered = sorted(paths, key=lambda path: (os.path.basename(path).casefold(), path.casefold()), reverse=reverse)
        self.model.replace(ordered)
        if selected in self.model.rows:
            index = self.model.index(self.model.rows[selected], 0)
            self.grid.setCurrentIndex(index)
            self.grid.scrollTo(index)

    def _sizes_ready(self, job):
        self.destroyed.disconnect(job.cancelled.set)
        if job is self.size_job:
            self.size_job = None
            self.sizes = job.sizes
            self._sort_results()

    def _open_image(self, index):
        if index.isValid():
            self.open_image.emit(self.model.paths, self.model.paths[index.row()])

    def _open_current_folder(self):
        path = self.grid.currentIndex().data(Qt.ItemDataRole.UserRole)
        if path:
            self.open_folder.emit(str(Path(path).parent))
