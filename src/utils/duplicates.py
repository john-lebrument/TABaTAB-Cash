"""Exact, non-recursive duplicate detection and conservative recycling."""
import hashlib
import threading
from pathlib import Path
from PIL import Image, ImageOps, UnidentifiedImageError
from src.utils.file_ops import is_image_file
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, QFile


def digest_file(path, cancelled=lambda: False):
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            if cancelled(): raise InterruptedError('Recherche annulée')
            digest.update(block)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise OSError(f'Fichier modifié pendant la lecture : {path.name}')
    return digest.hexdigest()


def pixel_digest(path, cancelled=lambda: False):
    """Exact displayed RGBA pixels; never use a similarity threshold or resize."""
    before = path.stat()
    with Image.open(path) as opened:
        # Animated and multipage files retain byte-for-byte comparison.
        if getattr(opened, 'n_frames', 1) != 1:
            return None
        image = ImageOps.exif_transpose(opened).convert('RGBA')
        digest = hashlib.sha256(str(image.size).encode('ascii'))
        for top in range(0, image.height, 128):
            if cancelled():
                raise InterruptedError('Recherche annulée')
            digest.update(image.crop((0, top, image.width, min(top + 128, image.height))).tobytes())
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise OSError(f'Fichier modifié pendant la lecture : {path.name}')
    return 'pixels:' + digest.hexdigest()


def comparison_digest(path, expected=None, cancelled=lambda: False):
    if expected is None or expected.startswith('pixels:'):
        try:
            pixels = pixel_digest(path, cancelled)
            if pixels is not None:
                return pixels
        except InterruptedError:
            raise
        except (UnidentifiedImageError, OSError, ValueError):
            if expected is not None:
                raise
    return digest_file(path, cancelled)


def find_duplicates(folder, cancelled=lambda: False):
    sizes, groups, errors = {}, {}, []
    entries, pixels_by_raw = [], {}
    for path in sorted(Path(folder).iterdir(), key=lambda p: (p.name.casefold(), p.name)):
        if cancelled(): raise InterruptedError('Recherche annulée')
        try:
            if path.is_file() and not path.is_symlink():
                sizes.setdefault(path.stat().st_size, []).append(path)
        except OSError as error: errors.append(f'{path.name} : {error}')
    for paths in sizes.values():
        for path in paths:
            if len(paths) < 2 and not is_image_file(path):
                continue
            try:
                raw = digest_file(path, cancelled)
                if is_image_file(path):
                    pixels = comparison_digest(path, cancelled=cancelled)
                    if pixels.startswith('pixels:'):
                        pixels_by_raw[raw] = pixels
                entries.append((raw, path))
            except (OSError, ValueError) as error:
                if isinstance(error, InterruptedError): raise
                errors.append(f'{path.name} : {error}')
    for raw, path in entries:
        groups.setdefault(pixels_by_raw.get(raw, raw), []).append(path)
    return [(digest, sorted(paths, key=lambda p: (p.name.casefold(), p.name)))
            for digest, paths in groups.items() if len(paths) > 1], errors


def recycle_duplicates(groups):
    removed, errors = [], []
    for digest, paths in groups:
        keeper = paths[0]
        for duplicate in paths[1:]:
            try:
                if keeper.is_symlink() or duplicate.is_symlink(): raise OSError('Lien ignoré')
                if comparison_digest(keeper, digest) != digest or comparison_digest(duplicate, digest) != digest:
                    raise OSError('Contenu modifié depuis la recherche ; fichier conservé')
                if not QFile(str(duplicate)).moveToTrash():
                    raise OSError('Corbeille indisponible ; fichier conservé')
                removed.append(str(duplicate))
            except (OSError, ValueError) as error: errors.append(f'{duplicate.name} : {error}')
    return removed, errors


class ScanSignals(QObject):
    finished = pyqtSignal(object, object)


class DuplicateScan(QRunnable):
    def __init__(self, folder):
        super().__init__()
        self.folder = folder
        self.signals = ScanSignals()
        self.cancelled = threading.Event()

    def cancel(self): self.cancelled.set()

    def run(self):
        try: groups, errors = find_duplicates(self.folder, self.cancelled.is_set)
        except InterruptedError: groups, errors = None, []
        except OSError as error: groups, errors = [], [str(error)]
        self.signals.finished.emit(groups, errors)
