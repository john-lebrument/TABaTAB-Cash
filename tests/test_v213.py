import math
import unittest
from pathlib import Path
from unittest.mock import patch
import test_v14
from PIL import Image, ImageChops, ImageDraw, PngImagePlugin
from PIL.ImageQt import fromqimage
from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF, QEvent, QThreadPool
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QDialog
from src.ui.blur_tool import BlurSelection
from src.ui.fullscreen_viewer import CropConfirmDialog
from src.utils.image_metadata import read_image_metadata, metadata_text


class FeaturesV213(unittest.TestCase):
    setUpClass = classmethod(test_v14.NewBehaviors.setUpClass.__func__)
    setUp = test_v14.NewBehaviors.setUp
    tearDown = test_v14.NewBehaviors.tearDown
    viewer = test_v14.NewBehaviors.viewer

    def test_blur_move_keeps_other_zones_and_stays_in_image(self):
        item = BlurSelection(QRectF(0, 0, 500, 400))
        item.addRect(QRectF(20, 30, 100, 80))
        item.addRect(QRectF(300, 250, 50, 50))
        item.begin_drag(QPointF(50, 60))
        item.end_drag(QPointF(90, 90))
        self.assertEqual(item.get_boxes(), [(60, 60, 160, 140), (300, 250, 350, 300)])
        item.begin_drag(QPointF(100, 100))
        item.end_drag(QPointF(900, 900))
        self.assertEqual(item.get_boxes()[0], (400, 320, 500, 400))
        self.assertEqual(item.get_boxes()[1], (300, 250, 350, 300))

    def test_all_blur_handles_resize_without_inverting_or_leaving_image(self):
        for handle, target in [('nw', QPointF(-200, -200)), ('n', QPointF(200, -10)),
                               ('ne', QPointF(900, -100)), ('e', QPointF(900, 200)),
                               ('se', QPointF(900, 900)), ('s', QPointF(200, 900)),
                               ('sw', QPointF(-200, 900)), ('w', QPointF(-200, 200))]:
            item = BlurSelection(QRectF(0, 0, 500, 400))
            item.addRect(QRectF(100, 100, 100, 80))
            item.set_transform_mode(True)
            item.begin_drag(item.get_handle_rects()[handle].center())
            item.end_drag(target)
            self.assertTrue(item.bounds.contains(item.rects[0]), handle)
            self.assertGreaterEqual(item.rects[0].width(), 1)
            self.assertGreaterEqual(item.rects[0].height(), 1)
        item.begin_drag(item.get_handle_rects()['w'].center())
        item.end_drag(QPointF(499, 200))
        self.assertGreaterEqual(item.rects[0].width(), 1)

    def test_ctrl_t_transforms_existing_zone_and_still_allows_new_zones(self):
        viewer = self.viewer()
        viewer.start_blur()
        item = viewer.blur_item
        item.addRect(QRectF(20, 20, 80, 60))
        QTest.keyClick(viewer.view, Qt.Key.Key_T, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(len(item.get_handle_rects()), 8)
        self.assertTrue(viewer.btn_blur_transform.isChecked())
        item.begin_drag(QPointF(200, 100))
        item.end_drag(QPointF(280, 180))
        self.assertEqual(len(item.get_boxes()), 2)
        QTest.keyClick(viewer.view, Qt.Key.Key_Return)
        self.assertFalse(item.transform_mode)
        self.assertEqual(len(item.get_boxes()), 2)
        self.assertIs(viewer.blur_item, item)

    def test_mouse_drag_moves_blur_and_save_uses_new_bounds(self):
        image = Image.new('RGB', (320, 240), 'white')
        draw = ImageDraw.Draw(image)
        for x in range(0, 320, 4):
            draw.line((x, 0, x, 239), fill='black')
        image.save(self.paths[0])
        viewer = self.viewer()
        viewer.start_blur()
        viewer.blur_item.addRect(QRectF(20, 30, 60, 60))
        viewport = viewer.view.viewport()
        start = viewer.view.mapFromScene(QPointF(50, 60))
        finish = viewer.view.mapFromScene(QPointF(150, 90))
        QTest.mousePress(viewport, Qt.MouseButton.LeftButton, pos=start)
        event = QMouseEvent(QEvent.Type.MouseMove, QPointF(finish), QPointF(viewport.mapToGlobal(finish)),
                            Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        self.app.sendEvent(viewport, event)
        QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=finish)
        self.assertEqual(viewer.blur_item.get_boxes(), [(120, 60, 180, 120)])
        viewer.blur_slider.setValue(90)
        viewer._preview_blur()
        preview = fromqimage(viewer.pixmap_item.pixmap().toImage()).convert('RGB')
        self.assertIsNone(ImageChops.difference(image.crop((20, 30, 80, 90)), preview.crop((20, 30, 80, 90))).getbbox())
        self.assertIsNotNone(ImageChops.difference(image, preview).getbbox())
        def copy(dialog):
            dialog.choice = 'copy'
            return QDialog.DialogCode.Accepted
        with patch.object(CropConfirmDialog, 'exec', copy):
            viewer.apply_blur()
        with Image.open(self.root / '0_flou.png') as saved:
            difference = ImageChops.difference(image, saved.convert('RGB')).getbbox()
            self.assertGreaterEqual(difference[0], 120)
            self.assertLessEqual(difference[2], 180)

    def test_small_fullscreen_image_is_never_upscaled_and_label_has_pixels(self):
        viewer = self.viewer()
        self.assertEqual(viewer.zoom_factor, 1.0)
        self.assertEqual(viewer.view.transform().m11(), 1.0)
        self.assertEqual(viewer.zoom_badge.text(), '100 % · 320 × 240 px')

    def test_large_fullscreen_image_fits_both_dimensions_at_real_percentage(self):
        Image.new('RGB', (2000, 4000), 'green').save(self.paths[0])
        viewer = self.viewer()
        expected = min(viewer.view.viewport().width() / 2000, viewer.view.viewport().height() / 4000)
        self.assertAlmostEqual(viewer.zoom_factor, expected)
        self.assertTrue(viewer.zoom_badge.text().startswith(f'{round(expected * 100)} %'))
        self.assertIn('2000 × 4000 px', viewer.zoom_badge.text())
        self.assertLessEqual(2000 * viewer.zoom_factor, viewer.view.viewport().width())
        self.assertLessEqual(4000 * viewer.zoom_factor, viewer.view.viewport().height())

    def test_hidpi_native_size_uses_physical_display_pixels(self):
        viewer = self.viewer()
        with patch.object(viewer.view.viewport(), 'devicePixelRatioF', return_value=2.0):
            viewer.fit_to_screen()
            self.assertEqual(viewer.view.transform().m11(), 0.5)
            self.assertTrue(viewer.zoom_badge.text().startswith('100 %'))
            viewer.zoom_out()
            self.assertTrue(viewer.zoom_badge.text().startswith('80 %'))

    def test_at_2x_filename_does_not_change_source_pixel_dimensions(self):
        path = self.root / 'photo@2x.png'
        Image.new('RGB', (320, 240), 'orange').save(path)
        viewer = self.viewer()
        viewer.image_list = [str(path)]
        viewer.current_index = 0
        viewer.load_current_image()
        self.assertEqual(viewer.current_pixmap.devicePixelRatio(), 1.0)
        self.assertEqual(viewer.pixmap_item.boundingRect(), QRectF(0, 0, 320, 240))
        self.assertTrue(viewer.zoom_badge.text().startswith('100 %'))

    def test_b_window_is_unowned_and_has_independent_minimize_button(self):
        self.window._on_request_floating(self.paths, self.paths[0])
        floating = next(iter(self.window.floating_viewers))
        self.assertIsNone(floating.parentWidget())
        self.window.showMinimized()
        self.app.processEvents()
        self.assertFalse(floating.isMinimized())
        floating.floating_minimize.click()
        self.app.processEvents()
        self.assertTrue(floating.isMinimized())

    def test_b_zoom_half_step_is_reversible_and_survives_resize_and_pan(self):
        self.window._on_request_floating(self.paths, self.paths[0])
        floating = next(iter(self.window.floating_viewers))
        initial = floating.zoom_factor
        floating.zoom_in()
        self.assertAlmostEqual(floating.zoom_factor, initial * math.sqrt(1.25))
        floating.zoom_in()
        self.assertAlmostEqual(floating.zoom_factor, initial * 1.25)
        floating.zoom_out()
        floating.zoom_out()
        self.assertAlmostEqual(floating.zoom_factor, initial)
        floating._apply_zoom(3)
        floating.resize(180, 120)
        self.app.processEvents()
        floating.view.centerOn(180, 100)
        center = floating.view.mapToScene(floating.view.viewport().rect().center())
        floating.resize(160, 100)
        self.app.processEvents()
        self.assertAlmostEqual(floating.zoom_factor, initial * 3)
        self.assertAlmostEqual(floating.view.transform().m11(), initial * 3)
        after = floating.view.mapToScene(floating.view.viewport().rect().center())
        self.assertLess(abs(after.x() - center.x()), 1)
        self.assertLess(abs(after.y() - center.y()), 1)

    def test_metadata_includes_exif_gps_text_and_unabridged_binary(self):
        exif = Image.Exif()
        exif[271] = 'Camera Test'
        exif[305] = 'TABaTAB metadata fixture'
        exif[34665] = {42036: 'Lens Test', 36867: '2026:11:09 12:00:00'}
        exif[34853] = {1: 'N', 2: (48.0, 12.0, 30.0)}
        jpeg = self.root / 'metadata.jpg'
        Image.new('RGB', (100, 60), 'blue').save(jpeg, exif=exif)
        sections = read_image_metadata(jpeg)
        text = str(sections)
        self.assertNotIn('Métadonnées non décodées', text)
        self.assertIn('Segments JPEG intégrés', text)
        for value in ['Camera Test', 'Lens Test', 'GPSLatitude', '2026:11:09', '100 × 60 px']:
            self.assertIn(value, text)
        info = PngImagePlugin.PngInfo()
        info.add_text('Commentaire personnel', 'Métadonnée complète ' * 100)
        info.add_text('XML:com.adobe.xmp', '<xmp><auteur nom="Essai">Jean</auteur></xmp>')
        Image.new('RGB', (10, 10)).save(self.paths[0], pnginfo=info)
        sections = read_image_metadata(self.paths[0])
        self.assertIn('Métadonnée complète ' * 100, str(sections))
        self.assertIn('XMP', str(sections))
        self.assertIn('Jean', str(sections))
        binary = b'\x00\xff' * 1000
        self.assertIn(binary.hex(' '), metadata_text(binary))

    def test_metadata_hover_opens_only_fullscreen_and_closes_on_image(self):
        viewer = self.viewer()
        viewport = viewer.view.viewport()
        def move(x):
            point = QPoint(x, viewport.height() // 2)
            event = QMouseEvent(QEvent.Type.MouseMove, QPointF(point), QPointF(viewport.mapToGlobal(point)),
                                Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
            self.app.sendEvent(viewport, event)
        move(viewport.width() - 1)
        self.assertTrue(viewer.metadata_panel.isVisible())
        QThreadPool.globalInstance().waitForDone()
        self.app.processEvents()
        self.assertGreaterEqual(viewer.metadata_panel.tree.topLevelItemCount(), 2)
        move(30)
        self.assertFalse(viewer.metadata_panel.isVisible())
        self.assertTrue(viewer.isFullScreen())
        self.window._on_request_floating(self.paths, self.paths[0])
        floating = next(iter(self.window.floating_viewers))
        self.assertIsNone(floating.metadata_panel)

    def test_metadata_navigation_ignores_stale_results_and_copies_full_values(self):
        viewer = self.viewer()
        panel = viewer.metadata_panel
        panel.load(self.paths[0])
        old = panel._request
        panel.load(self.paths[1])
        current = panel._request
        QThreadPool.globalInstance().waitForDone()
        self.app.processEvents()
        value = 'complete value ' * 200
        panel.loaded(current, [('Test', [('Long metadata', value)])])
        panel.loaded(old, [('Obsolete', [('Old image', 'old')])])
        self.assertEqual(panel.tree.topLevelItem(0).text(0), 'Test')
        item = panel.tree.topLevelItem(0).child(0)
        panel.tree.setCurrentItem(item)
        self.assertIn(value, panel.detail.toPlainText())
        viewer.next_image()
        self.assertIsNone(panel._filename)
        self.assertFalse(panel.isVisible())
