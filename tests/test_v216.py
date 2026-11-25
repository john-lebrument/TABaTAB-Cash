import time
import unittest
from unittest.mock import patch

from PIL import Image
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QLabel, QPushButton

import test_v14
from src.ui.browser_tab import DuplicateCard, DuplicateResultsDialog
from src.ui.filename_search_tab import FilenameSearchTab
from src.utils.duplicates import find_duplicates


class FeaturesV216(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown

    def test_search_grid_displays_thumbnail_and_sorts_by_path_name_and_file_size(self):
        first_folder, second_folder = self.root / 'a', self.root / 'z'
        first_folder.mkdir()
        second_folder.mkdir()
        first = str(first_folder / 'z.jpg')
        second = str(second_folder / 'a.bmp')
        Image.new('RGB', (70, 70), 'red').save(first)
        Image.new('RGB', (70, 70), 'blue').save(second)
        tab = FilenameSearchTab('*', self.window.thumbnail_manager, 100, self.window)
        tab.resize(600, 340)
        tab.show()
        tab.model.replace([first, second])
        tab._sort_results()
        self.assertEqual(tab.model.paths, [second, first])
        index = tab.model.index(0, 0)
        tab.grid.setCurrentIndex(index)
        self._wait_for(lambda: tab.preview.manager.cache.get(f'{second}_100') is not None)
        viewport = tab.grid.viewport().grab().toImage()
        rect = tab.grid.visualRect(index)
        self.assertTrue(any(viewport.pixelColor(rect.center().x(), y).blue() > 235
                            and viewport.pixelColor(rect.center().x(), y).red() < 20
                            for y in range(rect.top(), min(rect.bottom(), viewport.height()))))
        tab.sort.setCurrentIndex(tab.sort.findData('path'))
        self.assertEqual(tab.model.paths, [first, second])
        self.assertEqual(tab.grid.currentIndex().row(), 1)
        tab.sort.setCurrentIndex(tab.sort.findData('size'))
        self._wait_for(lambda: tab.size_job is None)
        self.assertEqual(tab.model.paths, [first, second])
        tab.order.setCurrentIndex(1)
        self.assertEqual(tab.model.paths, [second, first])
        tab.close()

    def _wait_for(self, done):
        deadline = time.monotonic() + 5
        while not done() and time.monotonic() < deadline:
            QTest.qWait(20)
        self.assertTrue(done())

    def test_row_trash_checks_content_updates_keeper_and_removes_singleton_group(self):
        folder = self.root / 'duplicates'
        folder.mkdir()
        first, second, last = (folder / f'{name}.png' for name in 'abc')
        Image.new('RGB', (320, 160), 'red').save(first)
        for path in (second, last):
            path.write_bytes(first.read_bytes())
        groups, errors = find_duplicates(folder)
        dialog = DuplicateResultsDialog(groups, errors, 2, self.tab)
        dialog.show()
        cards = dialog.findChildren(DuplicateCard)
        self.assertTrue(any('320 × 160 px' in label.text() for label in cards[0].findChildren(QLabel)))
        with patch('src.utils.duplicates.QFile') as file:
            file.return_value.moveToTrash.return_value = False
            with patch('src.ui.browser_tab.QMessageBox.warning') as warning:
                cards[0].findChild(QPushButton, 'trashDuplicate').click()
            warning.assert_called_once()
            self.assertEqual(dialog.groups[0][1], [first, second, last])
            file.return_value.moveToTrash.return_value = True
            cards[0].findChild(QPushButton, 'trashDuplicate').click()
            self.assertEqual(dialog.groups[0][1], [second, last])
            self.assertEqual(cards[1].findChild(QPushButton).text(), '✓')
            cards[2].findChild(QPushButton, 'trashDuplicate').click()
        self.assertEqual(dialog.recycled, [str(first), str(last)])
        self.assertEqual(dialog.groups, [])
        self.assertFalse(cards[1].isVisible())
        self.assertIn('Aucun doublon restant', dialog.header.text())
        self.assertTrue(second.is_file())
        dialog.close()
