# Install PyQt6
# pip install pyqt6
# Create a visual concept map editor using PyQt6
#
# This code allows users to create and edit a visual concept map.
# Concepts = rounded rectangles
# Linking words = text
# Proposition = concept1 -> linking words -> concept2
# Double click to edit a concept or linking words
# Right click to start an arrow, right click to end an arrow.
# Arrows should be from concept to linking words to concpet.
# You can put them elsewhere, but they will not be valid propositions.

import sys
import math
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLineEdit,
    QFileDialog, QScrollArea
)
from PyQt6.QtGui import QPainter, QPen, QBrush, QFont, QColor, QFontMetrics
from PyQt6.QtCore import Qt, QRectF, QPointF

from PyQt6.QtSvgWidgets import QSvgWidget  # For SVG export, but we use QSvgGenerator below
from PyQt6.QtSvg import QSvgGenerator

CANVAS_BG = QColor(255, 255, 255)

class Node:
    def __init__(self, x, y, text="Node", font=None):
        self.x = x
        self.y = y
        self.text = text
        self.selected = False
        self.font = font if font else QFont()
        self.font.setPointSize(12)
        self.set_text(self.text)

    def set_text(self, text):
        self.text = text
        metrics = QFontMetrics(self.font)
        text_width = metrics.horizontalAdvance(self.text)
        text_height = metrics.height()
        self.w = text_width + 18
        self.h = text_height + 12

    def rect(self):
        return QRectF(self.x, self.y, self.w, self.h)

    def center(self):
        return QPointF(self.x + self.w / 2, self.y + self.h / 2)

    def contains(self, point):
        return self.rect().contains(point)

    def boundary_point(self, target):
        cx, cy = self.center().x(), self.center().y()
        tx, ty = target.x(), target.y()
        dx, dy = tx - cx, ty - cy
        if dx == 0 and dy == 0:
            return QPointF(cx, cy)
        hw, hh = self.w / 2, self.h / 2
        scale_x = hw / abs(dx) if dx != 0 else float('inf')
        scale_y = hh / abs(dy) if dy != 0 else float('inf')
        scale = min(scale_x, scale_y)
        bx = cx + dx * scale
        by = cy + dy * scale
        return QPointF(bx, by)

    def to_dict(self):
        return {
            "type": "node",
            "x": self.x,
            "y": self.y,
            "text": self.text
        }

    @classmethod
    def from_dict(cls, d, font=None):
        return cls(d["x"], d["y"], d["text"], font=font)

class TextNode(Node):
    def __init__(self, x, y, text="Text", font=None):
        super().__init__(x, y, text, font)
        self.bg_color = CANVAS_BG

    def set_text(self, text):
        self.text = text
        metrics = QFontMetrics(self.font)
        text_width = metrics.horizontalAdvance(self.text)
        text_height = metrics.height()
        self.w = text_width + 18
        self.h = text_height + 12

    def draw(self, painter, selected=False):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self.bg_color))
        painter.drawRect(self.rect())
        painter.setFont(self.font)
        painter.setPen(QColor(0, 120, 215) if selected else Qt.GlobalColor.black)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text)

    def to_dict(self):
        return {
            "type": "textnode",
            "x": self.x,
            "y": self.y,
            "text": self.text
        }

    @classmethod
    def from_dict(cls, d, font=None):
        return cls(d["x"], d["y"], d["text"], font=font)

class Arrow:
    def __init__(self, start_node, end_node):
        self.start_node = start_node
        self.end_node = end_node
        self.selected = False

    def points(self):
        start = self.start_node.boundary_point(self.end_node.center())
        end = self.end_node.boundary_point(self.start_node.center())
        return start, end

    def contains(self, pos, tolerance=8):
        start, end = self.points()
        x0, y0 = pos.x(), pos.y()
        x1, y1 = start.x(), start.y()
        x2, y2 = end.x(), end.y()
        dx, dy = x2 - x1, y2 - y1
        if dx == dy == 0:
            return math.hypot(x0 - x1, y0 - y1) < tolerance
        t = ((x0 - x1) * dx + (y0 - y1) * dy) / (dx * dx + dy * dy)
        t = max(0, min(1, t))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        dist = math.hypot(x0 - proj_x, y0 - proj_y)
        return dist < tolerance

    def to_dict(self, node_indices):
        return {
            "start": node_indices[self.start_node],
            "end": node_indices[self.end_node]
        }

    @classmethod
    def from_dict(cls, d, nodes):
        return cls(nodes[d["start"]], nodes[d["end"]])

class CanvasWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.nodes = []
        self.arrows = []
        self.dragging_node = None
        self.drag_offset = QPointF(0, 0)
        self.selected_node = None
        self.selected_arrow = None
        self.arrow_source_node = None
        self.setMinimumSize(2000, 2000)
        self.node_font = QFont()
        self.node_font.setPointSize(12)
        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), CANVAS_BG)
        self.setPalette(p)
        self._zoom = 1.0

        self.editor = QLineEdit(self)
        self.editor.hide()
        self.editor.setFrame(False)
        self.editor.editingFinished.connect(self.finish_editing)
        self.editing_node = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(self._zoom, self._zoom)
        painter.fillRect(self.rect(), CANVAS_BG)
        for arrow in self.arrows:
            start, end = arrow.points()
            self.draw_arrow(painter, start, end, arrow.selected)
        for node in self.nodes:
            if isinstance(node, TextNode):
                node.draw(painter, selected=node.selected)
            else:
                self.draw_node(painter, node)

    def draw_node(self, painter, node):
        if node.selected:
            pen = QPen(QColor(0, 120, 215), 3)
            brush = QBrush(QColor(180, 210, 255))
        else:
            pen = QPen(Qt.GlobalColor.black, 2)
            brush = QBrush(Qt.GlobalColor.lightGray)
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawRoundedRect(node.rect(), 15, 15)
        painter.setPen(Qt.GlobalColor.black)
        painter.setFont(node.font)
        painter.drawText(node.rect(), Qt.AlignmentFlag.AlignCenter, node.text)

    def draw_arrow(self, painter, start, end, selected=False):
        pen = QPen(QColor(0, 120, 215), 3) if selected else QPen(Qt.GlobalColor.black, 2)
        painter.setPen(pen)
        painter.drawLine(start, end)
        self.draw_arrowhead(painter, start, end, selected)

    def draw_arrowhead(self, painter, start, end, selected=False):
        arrow_size = 15
        angle = math.atan2(end.y() - start.y(), end.x() - start.x())
        p1 = end
        p2 = QPointF(
            end.x() - arrow_size * math.cos(angle - math.pi / 6),
            end.y() - arrow_size * math.sin(angle - math.pi / 6)
        )
        p3 = QPointF(
            end.x() - arrow_size * math.cos(angle + math.pi / 6),
            end.y() - arrow_size * math.sin(angle + math.pi / 6)
        )
        painter.setBrush(QBrush(QColor(0, 120, 215)) if selected else QBrush(Qt.GlobalColor.black))
        painter.drawPolygon([p1, p2, p3])

    def mousePressEvent(self, event):
        pos = event.position() / self._zoom
        if event.button() == Qt.MouseButton.LeftButton:
            for arrow in reversed(self.arrows):
                if arrow.contains(pos):
                    self.select_arrow(arrow)
                    self.hide_editor()
                    return
            for node in reversed(self.nodes):
                if node.contains(pos):
                    self.select_node(node)
                    self.dragging_node = node
                    self.drag_offset = pos - QPointF(node.x, node.y)
                    self.hide_editor()
                    self.update()
                    return
            self.select_node(None)
            self.select_arrow(None)
            self.dragging_node = None
            self.hide_editor()
            self.update()
        elif event.button() == Qt.MouseButton.RightButton:
            for node in reversed(self.nodes):
                if node.contains(pos):
                    if self.arrow_source_node and self.arrow_source_node != node:
                        self.arrows.append(Arrow(self.arrow_source_node, node))
                        self.arrow_source_node = None
                        self.setCursor(Qt.CursorShape.ArrowCursor)
                        self.hide_editor()
                        self.update()
                    else:
                        self.arrow_source_node = node
                        self.setCursor(Qt.CursorShape.CrossCursor)
                    return
            if self.arrow_source_node:
                self.arrow_source_node = None
                self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseMoveEvent(self, event):
        if self.dragging_node:
            pos = event.position() / self._zoom - self.drag_offset
            self.dragging_node.x = pos.x()
            self.dragging_node.y = pos.y()
            self.hide_editor()
            self.update()

    def mouseReleaseEvent(self, event):
        self.dragging_node = None

    def mouseDoubleClickEvent(self, event):
        pos = event.position() / self._zoom
        for node in reversed(self.nodes):
            if node.contains(pos):
                self.editing_node = node
                self.show_editor(node)
                return
        self.add_node(x=20, y=20)

    def show_editor(self, node):
        rect = node.rect()
        self.editor.setFont(node.font)
        x = int(rect.x() * self._zoom)
        y = int(rect.y() * self._zoom)
        w = int(rect.width() * self._zoom)
        h = int(rect.height() * self._zoom)
        self.editor.setGeometry(x, y, w, h)
        self.editor.setText(node.text)
        self.editor.show()
        self.editor.setFocus()
        self.editor.selectAll()

    def finish_editing(self):
        if self.editing_node:
            text = self.editor.text()
            self.editing_node.set_text(text)
            self.editing_node = None
            self.editor.hide()
            self.update()

    def hide_editor(self):
        self.editor.hide()
        self.editing_node = None

    def zoom_in(self):
        self._zoom *= 1.15
        self.hide_editor()
        self.update()

    def zoom_out(self):
        self._zoom /= 1.15
        self.hide_editor()
        self.update()

    def select_node(self, node):
        for n in self.nodes:
            n.selected = (n is node)
        self.selected_node = node
        self.select_arrow(None)
        self.update()

    def select_arrow(self, arrow):
        for a in self.arrows:
            a.selected = (a is arrow)
        self.selected_arrow = arrow
        if arrow:
            for n in self.nodes:
                n.selected = False
            self.selected_node = None
        self.update()

    def add_node(self, x=20, y=20, text=None):
        if text is None:
            text = f"Node {len([n for n in self.nodes if not isinstance(n, TextNode)])+1}"
        node = Node(x, y, text=text, font=self.node_font)
        self.nodes.append(node)
        self.update()

    def add_text_node(self, x=20, y=20, text=None):
        if text is None:
            text = f"Text {len([n for n in self.nodes if isinstance(n, TextNode)])+1}"
        node = TextNode(x, y, text=text, font=self.node_font)
        self.nodes.append(node)
        self.update()

    def delete_selected_node(self):
        if self.selected_node:
            self.arrows = [
                arrow for arrow in self.arrows
                if arrow.start_node != self.selected_node and arrow.end_node != self.selected_node
            ]
            self.nodes.remove(self.selected_node)
            self.selected_node = None
            self.update()

    def delete_selected_arrow(self):
        if self.selected_arrow:
            self.arrows.remove(self.selected_arrow)
            self.selected_arrow = None
            self.update()

    def save_diagram(self, filename):
        node_indices = {node: idx for idx, node in enumerate(self.nodes)}
        data = {
            "nodes": [node.to_dict() for node in self.nodes],
            "arrows": [arrow.to_dict(node_indices) for arrow in self.arrows]
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_diagram(self, filename):
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.nodes.clear()
        self.arrows.clear()
        for nd in data["nodes"]:
            if nd["type"] == "node":
                node = Node.from_dict(nd, font=self.node_font)
            elif nd["type"] == "textnode":
                node = TextNode.from_dict(nd, font=self.node_font)
            else:
                continue
            self.nodes.append(node)
        for ad in data["arrows"]:
            start = self.nodes[ad["start"]]
            end = self.nodes[ad["end"]]
            self.arrows.append(Arrow(start, end))
        self.selected_node = None
        self.selected_arrow = None
        self.arrow_source_node = None
        self.update()

    def export_node_textnode_node_tuples(self, filename):
        outgoing = {}
        for arrow in self.arrows:
            outgoing.setdefault(arrow.start_node, []).append(arrow.end_node)
        with open(filename, "w", encoding="utf-8") as f:
            for node in self.nodes:
                if isinstance(node, Node) and not isinstance(node, TextNode):
                    for mid in outgoing.get(node, []):
                        if isinstance(mid, TextNode):
                            for end in outgoing.get(mid, []):
                                if isinstance(end, Node) and not isinstance(end, TextNode):
                                    f.write(f"{node.text}, {mid.text}, {end.text}\n")

    def export_svg(self, filename):
        from PyQt6.QtCore import QSize
        generator = QSvgGenerator()
        generator.setFileName(filename)
        width = int(self.width() * self._zoom)
        height = int(self.height() * self._zoom)
        generator.setSize(QSize(width, height))
        generator.setViewBox(QRectF(0, 0, width, height))
        generator.setTitle("Diagram SVG Export")
        generator.setDescription("Exported diagram as SVG")
        painter = QPainter()
        painter.begin(generator)
        old_zoom = self._zoom
        self._zoom = 1.0
        self.render(painter)
        self._zoom = old_zoom
        painter.end()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CVT Visual Concept Map Editor")
        self.canvas = CanvasWidget(self)
        self.resize(900, 900)  # Make window taller on open
        self.init_ui()

    def init_ui(self):
        add_btn = QPushButton("Concept")
        add_text_btn = QPushButton("Add Text Node")
        delete_btn = QPushButton("Delete")
        save_btn = QPushButton("Save")
        load_btn = QPushButton("Load")
        export_btn = QPushButton("Export Tuples")
        export_svg_btn = QPushButton("Export SVG")
        zoom_in_btn = QPushButton("Zoom In")
        zoom_out_btn = QPushButton("Zoom Out")
        add_btn.clicked.connect(self.add_node)
        add_text_btn.clicked.connect(self.add_text_node)
        delete_btn.clicked.connect(self.delete_selected)
        save_btn.clicked.connect(self.save_diagram)
        load_btn.clicked.connect(self.load_diagram)
        export_btn.clicked.connect(self.export_tuples)
        export_svg_btn.clicked.connect(self.export_svg)
        zoom_in_btn.clicked.connect(self.canvas.zoom_in)
        zoom_out_btn.clicked.connect(self.canvas.zoom_out)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(add_text_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(load_btn)
        btn_layout.addWidget(export_btn)
        btn_layout.addWidget(export_svg_btn)
        btn_layout.addWidget(zoom_in_btn)
        btn_layout.addWidget(zoom_out_btn)
        btn_layout.addStretch(1)

        main_layout = QVBoxLayout()
        main_layout.addLayout(btn_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.canvas)
        main_layout.addWidget(scroll_area)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def add_node(self):
        self.canvas.add_node()

    def add_text_node(self):
        self.canvas.add_text_node()

    def delete_selected(self):
        if self.canvas.selected_node:
            self.canvas.delete_selected_node()
        elif self.canvas.selected_arrow:
            self.canvas.delete_selected_arrow()

    def save_diagram(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Diagram", "", "Diagram Files (*.json)")
        if filename:
            self.canvas.save_diagram(filename)

    def load_diagram(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Load Diagram", "", "Diagram Files (*.json)")
        if filename:
            self.canvas.load_diagram(filename)

    def export_tuples(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Export Tuples", "", "Text Files (*.txt)")
        if filename:
            self.canvas.export_node_textnode_node_tuples(filename)

    def export_svg(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Export SVG", "", "SVG Files (*.svg)")
        if filename:
            self.canvas.export_svg(filename)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("CVT Visual Concept Map Editor")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
