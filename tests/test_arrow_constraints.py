import json
import os
import tempfile
import unittest

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QMainWindow

from cvt_concept_map_visual_editor import CanvasWidget, Node, TextNode, can_connect_nodes


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
app = QApplication.instance() or QApplication([])

class RightClickEvent:
    def __init__(self, position):
        self._position = position

    def position(self):
        return self._position

    def button(self):
        return Qt.MouseButton.RightButton


class ArrowConstraintTests(unittest.TestCase):
    def test_concept_and_text_node_can_connect_in_either_direction(self):
        concept = Node.__new__(Node)
        text = TextNode.__new__(TextNode)

        self.assertTrue(can_connect_nodes(concept, text))
        self.assertTrue(can_connect_nodes(text, concept))

    def test_same_type_nodes_cannot_connect(self):
        first_concept = Node.__new__(Node)
        second_concept = Node.__new__(Node)
        first_text = TextNode.__new__(TextNode)
        second_text = TextNode.__new__(TextNode)

        self.assertFalse(can_connect_nodes(first_concept, second_concept))
        self.assertFalse(can_connect_nodes(first_text, second_text))

    def test_right_click_only_creates_arrows_between_different_node_types(self):
        window = QMainWindow()
        canvas = CanvasWidget(window)
        window.setCentralWidget(canvas)
        concepts = [Node(10, 10, "A"), Node(200, 10, "B")]
        texts = [TextNode(400, 10, "because"), TextNode(600, 10, "therefore")]
        canvas.nodes = [*concepts, *texts]

        def right_click(node):
            canvas.mousePressEvent(RightClickEvent(node.center()))

        right_click(concepts[0])
        right_click(concepts[1])
        self.assertEqual(canvas.arrows, [])
        self.assertIs(canvas.arrow_source_node, concepts[0])

        right_click(texts[0])
        self.assertEqual(len(canvas.arrows), 1)
        self.assertIs(canvas.arrows[0].start_node, concepts[0])
        self.assertIs(canvas.arrows[0].end_node, texts[0])

        right_click(texts[0])
        right_click(texts[1])
        self.assertEqual(len(canvas.arrows), 1)
        self.assertIs(canvas.arrow_source_node, texts[0])

        right_click(concepts[1])
        self.assertEqual(len(canvas.arrows), 2)
        self.assertIs(canvas.arrows[1].start_node, texts[0])
        self.assertIs(canvas.arrows[1].end_node, concepts[1])
        window.close()

    def test_right_clicking_empty_canvas_cancels_arrow_mode(self):
        window = QMainWindow()
        canvas = CanvasWidget(window)
        window.setCentralWidget(canvas)
        concept = Node(10, 10, "A")
        canvas.nodes = [concept]

        canvas.mousePressEvent(RightClickEvent(concept.center()))
        self.assertIs(canvas.arrow_source_node, concept)
        self.assertEqual(canvas.cursor().shape(), Qt.CursorShape.CrossCursor)

        canvas.mousePressEvent(RightClickEvent(QPointF(800, 800)))
        self.assertIsNone(canvas.arrow_source_node)
        self.assertEqual(canvas.cursor().shape(), Qt.CursorShape.ArrowCursor)
        window.close()

    def test_loading_rejects_same_type_arrows_without_replacing_current_map(self):
        canvas = CanvasWidget()
        existing_node = Node.__new__(Node)
        canvas.nodes = [existing_node]
        canvas.arrows = []
        diagram = {
            "nodes": [
                {"type": "node", "x": 0, "y": 0, "text": "A"},
                {"type": "node", "x": 100, "y": 0, "text": "B"},
            ],
            "arrows": [{"start": 0, "end": 1}],
        }

        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as file:
            json.dump(diagram, file)
            file.flush()
            with self.assertRaisesRegex(ValueError, "must connect a concept node and a text node"):
                canvas.load_diagram(file.name)

        self.assertEqual(canvas.nodes, [existing_node])
        self.assertEqual(canvas.arrows, [])


if __name__ == "__main__":
    unittest.main()
