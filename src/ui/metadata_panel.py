"""Transient metadata overlay; full values remain selectable and copyable."""
from PyQt6.QtCore import Qt, QObject, QRunnable, QThreadPool, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem, QPlainTextEdit, QSplitter
from src.utils.image_metadata import read_image_metadata


class MetadataSignals(QObject):
    finished = pyqtSignal(int, object)


class MetadataRead(QRunnable):
    def __init__(self, request, filename):
        super().__init__()
        self.request, self.filename = request, filename
        self.signals = MetadataSignals()

    def run(self):
        try:
            sections = read_image_metadata(self.filename)
        except Exception as error:
            sections = [('Lecture impossible', [('Erreur', str(error))])]
        self.signals.finished.emit(self.request, sections)


class MetadataPanel(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self._request = 0
        self._filename = None
        self._jobs = {}
        self.setObjectName('metadataPanel')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet('''
            QWidget#metadataPanel { background: #20252b; border: 1px solid #708090; }
            QLabel { color: white; background: transparent; border: none; }
            QTreeWidget, QPlainTextEdit { background: #15191e; color: #f4f4f4; border: 1px solid #56616c; }
            QTreeWidget::item:selected { background: #235b8c; }
            QHeaderView::section { background: #303a44; color: white; padding: 5px; }
        ''')
        layout = QVBoxLayout(self)
        title = QLabel('Toutes les informations de l’image', self)
        title.setWordWrap(True)
        layout.addWidget(title)
        hint = QLabel('Revenez sur l’image pour fermer ce volet.\nSélectionnez une ligne pour lire et copier sa valeur complète.', self)
        hint.setWordWrap(True)
        layout.addWidget(hint)
        splitter = QSplitter(Qt.Orientation.Vertical, self)
        self.tree = QTreeWidget(splitter)
        self.tree.setHeaderLabels(['Information', 'Valeur'])
        self.tree.setColumnWidth(0, 210)
        self.detail = QPlainTextEdit(splitter)
        self.detail.setReadOnly(True)
        self.detail.setPlaceholderText('Valeur complète de la métadonnée sélectionnée')
        splitter.setSizes([500, 160])
        layout.addWidget(splitter)
        self.tree.currentItemChanged.connect(self.show_value)
        self.hide()

    def reset(self):
        self.hide()
        self._request += 1
        self._filename = None

    def load(self, filename):
        if filename == self._filename:
            return
        self._filename = filename
        self._request += 1
        self.tree.clear()
        self.detail.clear()
        QTreeWidgetItem(self.tree, ['Lecture des métadonnées…'])
        job = MetadataRead(self._request, filename)
        self._jobs[self._request] = job
        job.signals.finished.connect(self.loaded)
        QThreadPool.globalInstance().start(job)

    def loaded(self, request, sections):
        self._jobs.pop(request, None)
        if request != self._request:
            return
        self.tree.clear()
        for title, rows in sections:
            section = QTreeWidgetItem(self.tree, [title])
            for label, value in rows:
                item = QTreeWidgetItem(section, [label, value.replace('\n', ' ')[:300]])
                item.setData(1, Qt.ItemDataRole.UserRole, value)
            section.setExpanded(True)

    def show_value(self, item, previous=None):
        value = item.data(1, Qt.ItemDataRole.UserRole) if item else None
        self.detail.setPlainText(f'{item.text(0)}\n\n{value}' if value is not None else '')
