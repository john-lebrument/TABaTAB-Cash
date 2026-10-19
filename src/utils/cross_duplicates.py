"""Recursive exact-content comparison, independent of the current-folder tool."""
import os
import threading
from pathlib import Path
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, QFile
from src.utils.duplicates import digest_file


def find_cross_duplicates(left, right=(), recursive=True, cancelled=lambda: False):
    files, errors = {}, []
    for side, roots in enumerate((left, right)):
        for root in roots:
            if cancelled():
                raise InterruptedError('Recherche annulée')
            root = Path(root).absolute()
            if not root.is_dir():
                errors.append(f'{root} : dossier inaccessible')
                continue
            def walk_error(error):
                errors.append(str(error))
            for directory, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
                if cancelled():
                    raise InterruptedError('Recherche annulée')
                # Junctions and symlinks may lead outside the selected folders.
                dirs[:] = sorted(d for d in dirs if not (Path(directory) / d).is_symlink()
                                 and not (Path(directory) / d).is_junction()) if recursive else []
                for name in sorted(names):
                    if cancelled():
                        raise InterruptedError('Recherche annulée')
                    path = Path(directory) / name
                    try:
                        if path.is_symlink() or not path.is_file():
                            continue
                        key = os.path.normcase(str(path.resolve()))
                        if key in files:
                            files[key][2].add(side)
                        else:
                            files[key] = (path, path.stat().st_size, {side})
                    except OSError as error:
                        errors.append(f'{path} : {error}')
    sizes = {}
    for entry in files.values():
        sizes.setdefault(entry[1], []).append(entry)
    result = []
    for entries in sizes.values():
        if len(entries) < 2 or (right and not all(any(side in e[2] for e in entries) for side in (0, 1))):
            continue
        hashes = {}
        for path, size, sides in entries:
            try:
                digest = digest_file(path, cancelled)
                hashes.setdefault(digest, []).append((path, sides))
            except InterruptedError:
                raise
            except OSError as error:
                errors.append(f'{path} : {error}')
        for digest, matches in hashes.items():
            if len(matches) < 2:
                continue
            if right and not any(a != b and 0 in a[1] and 1 in b[1] for a in matches for b in matches):
                continue
            # Put a left-hand reference first, but never select files for deletion.
            matches.sort(key=lambda entry: (0 not in entry[1], str(entry[0]).casefold()))
            result.append((digest, [p for p, sides in matches]))
    return result, errors


def recycle_selected(groups, selected):
    """Keep at least one verified reference per group; never permanently delete."""
    selected = {str(Path(p)) for p in selected}
    removed, errors = [], []
    for digest, paths in groups:
        keepers = [Path(p) for p in paths if str(p) not in selected]
        targets = [Path(p) for p in paths if str(p) in selected]
        for path in targets:
            try:
                if not keepers:
                    raise OSError('Conservez au moins un fichier dans ce groupe')
                keeper = next((p for p in keepers if not p.is_symlink() and p.is_file()
                               and digest_file(p) == digest), None)
                if keeper is None or path.is_symlink() or digest_file(path) != digest:
                    raise OSError('Contenu modifié ou référence inaccessible ; fichier conservé')
                if not QFile(str(path)).moveToTrash():
                    raise OSError('Corbeille indisponible ; fichier conservé')
                removed.append(str(path))
            except OSError as error:
                errors.append(f'{path} : {error}')
    return removed, errors


class CrossScanSignals(QObject):
    finished = pyqtSignal(object, object)


class CrossDuplicateScan(QRunnable):
    def __init__(self, left, right, recursive=True):
        super().__init__()
        self.left, self.right, self.recursive = list(left), list(right), recursive
        self.cancelled = threading.Event()
        self.signals = CrossScanSignals()

    def run(self):
        try:
            groups, errors = find_cross_duplicates(self.left, self.right, self.recursive, self.cancelled.is_set)
        except InterruptedError:
            groups, errors = None, []
        except Exception as error:
            groups, errors = [], [str(error)]
        self.signals.finished.emit(groups, errors)
