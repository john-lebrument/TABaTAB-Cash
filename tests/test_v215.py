import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QDialog, QLabel, QPushButton

import test_v14
from src.ui.browser_tab import DuplicateCard, DuplicatePreview, DuplicateResultsDialog
from src.ui.filename_search_tab import FilenameSearchTab
from src.utils.duplicates import find_duplicates, find_resized_duplicates, recycle_duplicates
from src.utils.filename_search import filename_pattern, scan_drives


class FeaturesV215(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown

    def test_report_opens_preview_and_keeps_the_clicked_copy(self):
        first, second = self.root / 'a-copy.png', self.root / 'z-copy.png'
        Image.new('RGB', (60, 40), 'red').save(first)
        second.write_bytes(first.read_bytes())
        groups, errors = find_duplicates(self.root)
        group = next((digest, paths) for digest, paths in groups if first in paths)
        dialog = DuplicateResultsDialog([group], errors, 1, self.tab)
        dialog.show()
        self.app.processEvents()
        cards = dialog.findChildren(DuplicateCard)
        QTest.mouseClick(cards[1].findChild(DuplicatePreview), Qt.MouseButton.LeftButton)
        preview_window = dialog.findChild(QDialog)
        self.assertTrue(preview_window.isVisible())
        self.assertEqual(preview_window.windowTitle(), second.name)
        self.assertEqual(preview_window.findChild(QLabel).pixmap().width(), 60)
        preview_window.close()
        self.assertEqual(dialog.groups[0][1][0], first)
        QTest.mouseClick(cards[1], Qt.MouseButton.LeftButton)
        self.assertEqual([card.findChild(QPushButton).text() for card in cards], ['✕', '✓'])
        with patch('src.utils.duplicates.QFile') as qt_file:
            removed, failures = recycle_duplicates(dialog.groups)
        self.assertEqual((removed, failures), ([str(first)], []))
        qt_file.assert_called_once_with(str(first))
        dialog.close()

    def test_resized_retry_finds_similar_images_and_rejects_modified_files(self):
        folder = self.root / 'resized'
        folder.mkdir()
        original, smaller = folder / 'original.png', folder / 'smaller.jpg'
        image = Image.new('RGB', (480, 320), '#61b1d6')
        ImageDraw.Draw(image).rectangle((54, 100, 330, 230), fill='#e08c27')
        image.save(original)
        image.resize((240, 160), Image.Resampling.LANCZOS).save(smaller, quality=91)
        Image.new('RGB', (240, 160), 'blue').save(folder / 'unrelated.png')
        self.assertEqual(find_duplicates(folder), ([], []))
        dialog = DuplicateResultsDialog([], [], 0, self.tab)
        next(button for button in dialog.findChildren(QPushButton)
             if 'redimensionnées' in button.text()).click()
        self.assertTrue(dialog.retry_resized)
        groups, errors = find_resized_duplicates(folder)
        self.assertEqual(errors, [])
        self.assertEqual([paths for _, paths in groups], [[original, smaller]])
        smaller.write_bytes(b'changed after scanning')
        with patch('src.utils.duplicates.QFile') as qt_file:
            removed, failures = recycle_duplicates(groups)
        self.assertEqual(removed, [])
        self.assertTrue(failures)
        qt_file.assert_not_called()

    def test_search_wildcards_filter_images_and_results_open_in_a_new_tab(self):
        folder = self.root / 'search'
        folder.mkdir()
        nested = folder / 'nested'
        nested.mkdir()
        match = nested / 'IMG_03.JPG'
        match.touch()
        for name in ('IMG_034.jpg', 'IMG_04.txt', 'other.jpg'):
            (nested / name).touch()
        paths = scan_drives([folder], filename_pattern('img_??.jpg'), lambda: False)
        self.assertEqual(paths, [str(match)])
        with patch('src.ui.filename_search_tab.QThreadPool') as pool:
            self.window.filename_query.setText('img_??.jpg')
            self.window.filename_query.returnPressed.emit()
            tab = self.window.tab_widget.currentWidget()
            self.assertIsInstance(tab, FilenameSearchTab)
            self.assertEqual(self.window.tab_widget.count(), 2)
            job = pool.globalInstance().start.call_args.args[0]
            job.signals.finished.emit(paths, False, '')
        self.assertEqual(tab.model.rowCount(), 1)
        self.assertEqual(tab.model.index(0, 0).data(), Path(match).name)
        with patch.object(self.window, '_on_request_floating') as open_image:
            tab.grid.activated.emit(tab.model.index(0, 0))
        open_image.assert_called_once_with(paths, str(match))
