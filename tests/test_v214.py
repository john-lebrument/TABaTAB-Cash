import unittest
from pathlib import Path
from unittest.mock import patch
import test_v14
from PIL import Image, PngImagePlugin
from PyQt6.QtCore import QMimeData, QUrl, QPoint
from PyQt6.QtWidgets import QMenu
from src.utils.duplicates import find_duplicates, recycle_duplicates
from src.ui.browser_tab import ROLE_PATH

class FeaturesV214(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown

    def test_favorites_population_never_probes_paths(self):
        missing = str(self.root / 'missing')
        self.config.settings['custom_favorites'] = [missing, r'\\unavailable-server\photos']
        with patch.object(Path, 'is_dir', side_effect=AssertionError('filesystem probe')), \
             patch.object(Path, 'exists', side_effect=AssertionError('filesystem probe')), \
             patch.object(Path, 'resolve', side_effect=AssertionError('filesystem resolution')):
            self.tab._populate_favorites()
            self.assertEqual(self.tab.fav_list.item(0).data(ROLE_PATH), missing)
            self.assertTrue(self.tab._favorite_destinations())

    def test_close_all_keeps_oldest_even_after_reordering(self):
        second = self.window.add_tab(str(self.root))
        self.window.add_tab(str(self.root))
        self.window.custom_tab_bar.moveTab(0, 2)
        self.window.close_all_tabs()
        self.assertEqual(self.window.tab_widget.count(), 1)
        self.assertIs(self.window.get_current_tab_widget(), self.tab)
        self.window.close_all_tabs()
        self.assertEqual(self.window.tab_widget.count(), 1)
        self.window.add_tab(str(self.root))
        self.window.close_tab(0)
        remaining = self.window.get_current_tab_widget()
        self.window.add_tab(str(self.root))
        self.window.close_all_tabs()
        self.assertIs(self.window.get_current_tab_widget(), remaining)

    def test_context_paste_image_and_file_on_empty_space_and_file(self):
        def choose(menu, *args):
            next(a for a in menu.actions() if a.text().startswith('Coller dans le dossier actuel')).trigger()
        for empty in (False, True):
            point = QPoint(self.grid.viewport().width()-2, self.grid.viewport().height()-2) if empty else self.grid.visualItemRect(self.grid.item(0)).center()
            self.app.clipboard().setImage(ImageQtImage())
            with patch.object(QMenu, 'exec', choose):
                self.grid._show_context_menu(point)
            self.assertEqual(len(list(self.root.glob('Image collée*.png'))), 1 if not empty else 2)
            mime = QMimeData(); mime.setUrls([QUrl.fromLocalFile(self.paths[0])])
            self.app.clipboard().setMimeData(mime)
            with patch.object(QMenu, 'exec', choose), patch.object(self.grid, 'files_dropped') as dropped:
                self.grid._show_context_menu(point)
                dropped.emit.assert_called_once()
                paths, target, copy = dropped.emit.call_args.args
                self.assertEqual([Path(p) for p in paths], [Path(self.paths[0])])
                self.assertEqual(Path(target), self.root)
                self.assertTrue(copy)

    def test_pixel_duplicates_ignore_metadata_and_format_but_not_different_pixels(self):
        with Image.open(self.paths[0]) as image:
            info = PngImagePlugin.PngInfo(); info.add_text('Comment', 'different metadata')
            image.save(self.root / 'metadata.png', pnginfo=info)
            image.save(self.root / 'other.bmp')
            image.save(self.root / 'compressed.png', compress_level=0)
            image.putpixel((0, 0), (1, 2, 3)); image.save(self.root / 'different.png')
        groups, errors = find_duplicates(self.root)
        self.assertFalse(errors)
        digest, paths = next(g for g in groups if Path(self.paths[0]) in g[1])
        self.assertEqual(len(paths), 6)
        self.assertNotIn(self.root / 'different.png', paths)
        (self.root / 'metadata.png').write_bytes(b'changed')
        with patch('src.utils.duplicates.QFile') as file:
            removed, errors = recycle_duplicates([(digest, [Path(self.paths[0]), self.root / 'metadata.png'])])
        file.assert_not_called(); self.assertFalse(removed); self.assertTrue(errors)
        with self.assertRaises(InterruptedError):
            find_duplicates(self.root, lambda: True)

def ImageQtImage():
    from PyQt6.QtGui import QImage
    image = QImage(8, 8, QImage.Format.Format_RGB32); image.fill(0xff008800)
    return image
