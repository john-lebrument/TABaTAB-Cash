"""Search the local Everything index, or scan local drives when it is unavailable."""
import ctypes
import os
import re
import sys
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from src.utils.file_ops import SUPPORTED_IMAGE_EXTENSIONS, is_image_file


_sdk_lock = threading.Lock()


def filename_pattern(query):
    wildcard = '*' in query or '?' in query
    pattern = ''.join('.*' if ch == '*' else '.' if ch == '?' else re.escape(ch) for ch in query)
    return f'^{pattern}$' if wildcard else pattern


def search_everything(pattern, cancelled):
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))
    sdk_path = base / 'resources' / 'everything' / 'Everything64.dll'
    with _sdk_lock:
        if cancelled():
            return []
        sdk = ctypes.WinDLL(str(sdk_path))
        sdk.Everything_SetSearchW.argtypes = [ctypes.c_wchar_p]
        sdk.Everything_GetNumResults.restype = ctypes.c_uint32
        full_path = sdk.Everything_GetResultFullPathNameW
        full_path.argtypes = [ctypes.c_uint32, ctypes.POINTER(ctypes.c_wchar), ctypes.c_uint32]
        full_path.restype = ctypes.c_uint32
        extensions = ';'.join(sorted(ext.lstrip('.') for ext in SUPPORTED_IMAGE_EXTENSIONS))
        # Windows filenames cannot contain a double quote. The caller rejects it.
        try:
            sdk.Everything_SetSearchW(f'files: ext:{extensions} regex:"{pattern}"')
            if not sdk.Everything_QueryW(1):
                raise OSError(f'Index Everything indisponible ({sdk.Everything_GetLastError()})')
            paths = []
            buffer = ctypes.create_unicode_buffer(32768)
            for index in range(sdk.Everything_GetNumResults()):
                if cancelled():
                    break
                length = full_path(index, buffer, len(buffer))
                if 0 < length < len(buffer):
                    paths.append(buffer.value)
            return paths
        finally:
            sdk.Everything_Reset()


def local_drives():
    kernel = ctypes.windll.kernel32
    mask = kernel.GetLogicalDrives()
    return [root for index in range(26) if mask & (1 << index)
            for root in [f'{chr(65 + index)}:\\'] if kernel.GetDriveTypeW(root) in (2, 3)]


def scan_drives(roots, pattern, cancelled):
    match = re.compile(pattern, re.IGNORECASE).search
    paths = []
    for root in roots:
        for folder, dirs, names in os.walk(root, followlinks=False):
            if cancelled():
                return paths
            dirs[:] = [name for name in dirs if not (Path(folder) / name).is_junction()]
            paths.extend(os.path.join(folder, name) for name in names
                         if match(name) and is_image_file(name))
    return paths


class SearchSignals(QObject):
    fallback = pyqtSignal()
    finished = pyqtSignal(list, bool, str)


class FilenameSearch(QRunnable):
    def __init__(self, query):
        super().__init__()
        self.pattern = filename_pattern(query)
        self.cancelled = threading.Event()
        self.signals = SearchSignals()

    def run(self):
        cancelled = self.cancelled.is_set
        paths, error = [], ''
        try:
            try:
                paths = search_everything(self.pattern, cancelled)
            except (OSError, AttributeError):
                if not cancelled():
                    self.signals.fallback.emit()
                    paths = scan_drives(local_drives(), self.pattern, cancelled)
        except OSError as exc:
            error = str(exc)
        self.signals.finished.emit(paths, cancelled(), error)
