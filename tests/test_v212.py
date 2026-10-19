import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import test_v14
from PyQt6.QtCore import Qt, QPoint, QMimeData, QUrl, QThreadPool
from PyQt6.QtGui import QDropEvent
from PyQt6.QtWidgets import QInputDialog, QMessageBox
from PyQt6.QtTest import QTest
from src.utils.file_ops import suggest_rename
from src.utils.cross_duplicates import find_cross_duplicates, recycle_selected
from src.ui.cross_duplicates_dialog import CrossDuplicatesDialog


class CrossComparison(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.left, self.right = self.root / 'A', self.root / 'B'
        self.left.mkdir()
        self.right.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_only_content_shared_between_groups_is_reported(self):
        for name, data in [('a.txt', b'left'), ('b.txt', b'left'), ('same.bin', b'same')]:
            (self.left / name).write_bytes(data)
        (self.right / 'other.extension').write_bytes(b'same')
        (self.right / 'same.bin').write_bytes(b'xxxx')
        groups, errors = find_cross_duplicates([self.left], [self.right])
        self.assertEqual(errors, [])
        self.assertEqual(len(groups), 1)
        self.assertEqual({p.name for p in groups[0][1]}, {'same.bin', 'other.extension'})

    def test_recursion_multiple_roots_and_overlapping_paths(self):
        nested = self.left / 'nested'
        nested.mkdir()
        (nested / 'a').write_bytes(b'x')
        (self.right / 'b').write_bytes(b'x')
        groups, _ = find_cross_duplicates([self.left, nested], [self.right, self.right])
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0][1]), 2)
        self.assertEqual(find_cross_duplicates([self.left], [self.right], recursive=False)[0], [])
        self.assertEqual(find_cross_duplicates([nested], [nested])[0], [])

    def test_empty_files_errors_and_cancellation(self):
        (self.left / 'empty').touch()
        (self.right / 'zero').touch()
        groups, errors = find_cross_duplicates([self.left], [self.right, self.root / 'missing'])
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(errors), 1)
        with self.assertRaises(InterruptedError):
            find_cross_duplicates([self.left], [self.right], cancelled=lambda: True)

    def test_recycling_checks_content_and_keeps_a_reference(self):
        a, b = self.left / 'a', self.right / 'b'
        a.write_bytes(b'content')
        b.write_bytes(b'content')
        groups, _ = find_cross_duplicates([self.left], [self.right])
        with patch('src.utils.cross_duplicates.QFile') as file:
            removed, errors = recycle_selected(groups, [str(a), str(b)])
            self.assertEqual(removed, [])
            self.assertEqual(len(errors), 2)
            file.assert_not_called()
            b.write_bytes(b'changed')
            removed, errors = recycle_selected(groups, [str(b)])
            self.assertEqual(removed, [])
            file.assert_not_called()
            b.write_bytes(b'content')
            file.return_value.moveToTrash.return_value = False
            removed, errors = recycle_selected(groups, [str(b)])
            self.assertEqual(removed, [])
            self.assertTrue(errors)
            file.return_value.moveToTrash.return_value = True
            removed, errors = recycle_selected(groups, [str(b)])
            self.assertEqual(removed, [str(b)])
            self.assertEqual(errors, [])


class FeaturesV212(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown
    viewer = test_v14.NewBehaviors.viewer

    def test_collision_proposes_incremented_name_in_grid(self):
        occupied = self.root / 'Photo 009.png'
        occupied.write_bytes(b'existing')
        (self.root / 'Photo 010.png').write_bytes(b'also existing')
        self.grid.select_path(self.paths[0])
        with patch.object(QInputDialog, 'getText', side_effect=[('Photo 009', True), ('Photo 011', True)]) as prompt:
            self.grid._rename_selected()
        self.assertEqual(prompt.call_args.kwargs['text'], 'Photo 011')
        self.assertTrue((self.root / 'Photo 011.png').is_file())
        self.assertEqual(occupied.read_bytes(), b'existing')

    def test_collision_can_be_cancelled_in_fullscreen(self):
        viewer = self.viewer()
        with patch.object(QInputDialog, 'getText', side_effect=[('1', True), ('', False)]) as prompt:
            viewer.rename_current_image()
        self.assertEqual(prompt.call_count, 2)
        self.assertTrue(Path(self.paths[0]).is_file())
        self.assertEqual(viewer.image_list[0], self.paths[0])

    def test_batch_suggestion_validates_every_destination(self):
        (self.root / 'Photo 002.png').write_bytes(b'occupied')
        self.assertEqual(suggest_rename(self.paths, 'Photo'), 'Photo 003')

    def test_blank_path_area_edits_and_copies_full_path(self):
        bar = self.tab.breadcrumb
        # Give the path room independently of the surrounding toolbars.
        bar.setParent(None)
        try:
            bar.resize(1100, 40)
            bar.show()
            self.app.processEvents()
            last = bar.buttons[-1]
            QTest.mouseClick(bar.crumbs, Qt.MouseButton.LeftButton,
                             pos=QPoint(last.geometry().right() + 8, last.geometry().center().y()))
            self.assertIs(bar.stack.currentWidget(), bar.edit)
            self.assertEqual(bar.edit.selectedText(), str(self.root))
            QTest.keyClick(bar.edit, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
            self.assertEqual(self.app.clipboard().text(), str(self.root))
            QTest.keyClick(bar.edit, Qt.Key.Key_Escape)
            self.assertIs(bar.stack.currentWidget(), bar.scroll)
            self.assertTrue(all('border: 1px solid' in b.styleSheet() for b in bar.buttons))
        finally:
            bar.close()
            bar.setParent(self.tab)

    def test_refresh_button_reloads_folder(self):
        with patch.object(self.tab, 'refresh') as refresh:
            self.tab.btn_refresh.click()
        refresh.assert_called_once_with()
        self.assertFalse(self.tab.btn_refresh.icon().isNull())

    def test_context_opens_without_scan_and_restores_targets(self):
        destination = self.root / 'target'
        destination.mkdir()
        self.config.set('cross_duplicates', {'right': [str(destination)]})
        self.tab._open_cross_duplicates([str(self.root)])
        dialog = self.tab._cross_dialog
        self.assertIsNone(dialog.scan)
        self.assertEqual(dialog.left.paths(), [str(self.root)])
        self.assertEqual(dialog.right.paths(), [str(destination)])
        dialog.close()

    def test_folder_drop_is_copy_only_and_choices_are_saved(self):
        folder = self.root / 'drop'
        folder.mkdir()
        dialog = CrossDuplicatesDialog(self.config, [('Favori', str(folder))], self.tab)
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(folder)), QUrl.fromLocalFile(self.paths[0])])
        event = QDropEvent(QPoint(10, 10).toPointF(), Qt.DropAction.CopyAction | Qt.DropAction.MoveAction,
                           mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        dialog.left.dropEvent(event)
        dialog.left.add_paths([str(folder)])
        self.assertEqual(dialog.left.paths(), [str(folder)])
        self.assertEqual(event.dropAction(), Qt.DropAction.CopyAction)
        self.assertTrue(folder.is_dir())
        self.assertEqual(self.config.get('cross_duplicates')['left'], [str(folder)])
        dialog.close()

    def test_async_scan_results_and_recycle_without_confirmation(self):
        left, right = self.root / 'A', self.root / 'B'
        left.mkdir()
        right.mkdir()
        a, b = left / 'a', right / 'b'
        a.write_bytes(b'equal')
        b.write_bytes(b'equal')
        dialog = CrossDuplicatesDialog(self.config, [], self.tab)
        dialog.left.add_paths([str(left)])
        dialog.right.add_paths([str(right)])
        dialog.start_scan()
        QThreadPool.globalInstance().waitForDone()
        self.app.processEvents()
        self.assertIsNone(dialog.scan)
        group = dialog.results.topLevelItem(0)
        self.assertEqual(group.childCount(), 2)
        self.assertEqual(group.child(1).checkState(0), Qt.CheckState.Unchecked)
        group.child(1).setCheckState(0, Qt.CheckState.Checked)
        with patch('src.utils.cross_duplicates.QFile') as file, patch.object(QMessageBox, 'question') as question:
            file.return_value.moveToTrash.return_value = True
            dialog.recycle_checked()
            question.assert_not_called()
            file.return_value.moveToTrash.assert_called_once()
        dialog.close()
