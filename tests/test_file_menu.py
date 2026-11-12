import os
import tempfile
import unittest
from unittest.mock import patch

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QFileDialog, QMessageBox, QPushButton

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
app = QApplication.instance() or QApplication([])

from cvt_concept_map_visual_editor import Arrow, MainWindow, Node, TextNode


class RightClickEvent:
    def __init__(self, position):
        self._position = position

    def position(self):
        return self._position

    def button(self):
        return Qt.MouseButton.RightButton


class FileMenuTests(unittest.TestCase):
    def test_toolbar_has_concept_node_icon_and_linking_words_label(self):
        window = MainWindow()
        buttons = {button.text(): button for button in window.findChildren(QPushButton)}

        self.assertEqual(
            set(buttons),
            {
                "Concept",
                "📝 Linking words",
                "🗑️ Delete",
                "🎨 Color",
                "🔍➕ Zoom In",
                "🔍➖ Zoom Out",
            },
        )
        self.assertFalse(buttons["Concept"].icon().isNull())
        self.assertTrue(all(button.isFlat() for button in buttons.values()))
        window.close()

    def test_file_menu_has_save_load_and_export_actions(self):
        window = MainWindow()
        file_menu = next(
            action.menu()
            for action in window.menuBar().actions()
            if action.menu() and action.menu().title() == "📁 File"
        )

        self.assertEqual(
            [action.text() for action in file_menu.actions() if not action.isSeparator()],
            ["Save", "Load", "Export Propositions", "Export SVG", "Quit"],
        )
        quit_action = next(action for action in file_menu.actions() if action.text() == "Quit")
        self.assertEqual(quit_action.menuRole(), QAction.MenuRole.NoRole)
        window.close()

    def test_quit_warns_about_unsaved_changes_and_cancel_keeps_window_open(self):
        window = MainWindow()
        window.canvas.add_node()
        self.assertTrue(window.isWindowModified())

        with patch(
            "cvt_concept_map_visual_editor.QMessageBox.warning",
            return_value=QMessageBox.StandardButton.Cancel,
        ) as warning:
            closed = window.close()

        self.assertFalse(closed)
        warning.assert_called_once()
        self.assertTrue(window.isWindowModified())

        with patch(
            "cvt_concept_map_visual_editor.QMessageBox.warning",
            return_value=QMessageBox.StandardButton.Discard,
        ):
            self.assertTrue(window.close())

    def test_quit_save_option_saves_before_closing(self):
        window = MainWindow()
        window.canvas.add_node()

        with tempfile.TemporaryDirectory() as directory:
            filename = os.path.join(directory, "concept-map.json")
            with (
                patch(
                    "cvt_concept_map_visual_editor.QMessageBox.warning",
                    return_value=QMessageBox.StandardButton.Save,
                ),
                patch.object(QFileDialog, "getSaveFileName", return_value=(filename, "")),
            ):
                self.assertTrue(window.close())

            self.assertTrue(os.path.exists(filename))
            self.assertFalse(window.isWindowModified())

    def test_help_menu_opens_application_guide(self):
        window = MainWindow()
        help_menu = next(
            action.menu()
            for action in window.menuBar().actions()
            if action.menu() and action.menu().title() == "Help"
        )

        with patch("cvt_concept_map_visual_editor.QMessageBox.about") as show_help:
            help_menu.actions()[0].trigger()

        show_help.assert_called_once()
        self.assertIn("Right-click empty canvas", show_help.call_args.args[2])
        window.close()

    def test_proposition_pane_updates_after_arrow_creation_and_text_edit(self):
        window = MainWindow()
        concept_start = Node(10, 10, "Door")
        linking_words = TextNode(200, 10, "opens")
        concept_end = Node(400, 10, "Garage")
        window.canvas.nodes = [concept_start, linking_words, concept_end]

        def right_click(node):
            window.canvas.mousePressEvent(RightClickEvent(node.center()))

        right_click(concept_start)
        right_click(linking_words)
        self.assertEqual(window.proposition_list.count(), 0)
        right_click(linking_words)
        right_click(concept_end)
        self.assertEqual(
            [window.proposition_list.item(index).text() for index in range(window.proposition_list.count())],
            ["Door, opens, Garage"],
        )

        window.canvas.editing_node = linking_words
        window.canvas.editor.setText("activates")
        window.canvas.finish_editing()
        self.assertEqual(window.proposition_list.item(0).text(), "Door, activates, Garage")

        window.show()
        app.processEvents()
        item = window.proposition_list.item(0)
        item_position = window.proposition_list.visualItemRect(item).center()
        QTest.mouseClick(
            window.proposition_list.viewport(),
            Qt.MouseButton.LeftButton,
            pos=item_position,
        )
        self.assertIs(window.canvas.selected_node, concept_start)
        window.mark_saved()
        window.close()

    def test_proposition_pane_sorts_alphabetically_and_keeps_node_mapping(self):
        window = MainWindow()
        zulu = Node(10, 10, "Zulu")
        zulu_link = TextNode(200, 10, "connects")
        zulu_end = Node(400, 10, "End")
        alpha = Node(600, 10, "alpha")
        alpha_link = TextNode(800, 10, "starts")
        alpha_end = Node(1000, 10, "Beginning")
        window.canvas.nodes = [zulu, zulu_link, zulu_end, alpha, alpha_link, alpha_end]
        window.canvas.arrows = [
            Arrow(zulu, zulu_link),
            Arrow(zulu_link, zulu_end),
            Arrow(alpha, alpha_link),
            Arrow(alpha_link, alpha_end),
        ]
        window.canvas.diagram_changed.emit()

        self.assertEqual(
            [window.proposition_list.item(index).text() for index in range(window.proposition_list.count())],
            ["alpha, starts, Beginning", "Zulu, connects, End"],
        )
        window.select_proposition(window.proposition_list.item(0))
        self.assertIs(window.canvas.selected_node, alpha)
        window.close()


if __name__ == "__main__":
    unittest.main()
