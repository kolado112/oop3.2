from dataclasses import dataclass, field
import sys
import os
import json
from PyQt6 import uic
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
import copy

@dataclass
class DrawEssentials:
    pen_color: QColor = field(default_factory=lambda: QColor(1, 1, 1))
    brush_color: QColor = field(default_factory=lambda: QColor(255, 255, 255, 100))
    pen_width: int = 2
    radius: int = 5

class DrawSettings(QObject):   # composition с DrawEssentials
    penColorChanged   = pyqtSignal(QColor)
    brushColorChanged = pyqtSignal(QColor)
    penWidthChanged   = pyqtSignal(int)
    toolChanged       = pyqtSignal(str)
    radiusChanged     = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self._ess = DrawEssentials()
        self.__tool = None
        self.__csize = QSize(0, 0)

    @property
    def ess(self): return self._ess

    @property
    def pen_color(self): return self._ess.pen_color
    @pen_color.setter
    def pen_color(self, color: QColor):
        if isinstance(color, QColor) and color.isValid() and color != self._ess.pen_color:
            self._ess.pen_color = color
            print(f"Pen color changed to {color.name()}")
            self.penColorChanged.emit(color)

    @property
    def brush_color(self): return self._ess.brush_color
    @brush_color.setter
    def brush_color(self, color: QColor):
        if isinstance(color, QColor) and color.isValid() and color != self._ess.brush_color:
            self._ess.brush_color = color
            print(f"Brush color changed to {color.name()}")
            self.brushColorChanged.emit(color)

    @property
    def pen_width(self): return self._ess.pen_width
    @pen_width.setter
    def pen_width(self, width: int):
        if width != self._ess.pen_width:
            self._ess.pen_width = width
            print(f"Pen width changed to {width}")
            self.penWidthChanged.emit(width)

    @property
    def radius(self): return self._ess.radius
    @radius.setter
    def radius(self, r: int):
        if r != self._ess.radius:
            self._ess.radius = r
            print(f"Radius changed to {r}")
            self.radiusChanged.emit(r)

    @property
    def tool(self): return self.__tool
    @tool.setter
    def tool(self, t: str):
        if t != self.__tool:
            self.__tool = t
            print(f"Tool changed to {t}")
            self.toolChanged.emit(t)

    @property
    def csize(self): return self.__csize
    @csize.setter
    def csize(self, csize):
        new_size = None
        if isinstance(csize, QSize):
            new_size = csize
        elif isinstance(csize, (tuple, list)) and len(csize) == 2:
            new_size = QSize(int(csize[0]), int(csize[1]))
        else:
            return
        if new_size != self.__csize:
            self.__csize = new_size
            print(f"Canvas csize changed to {new_size.width(), new_size.height()}")

    def broadcast(self):
        self.penColorChanged.emit(self._ess.pen_color)
        self.brushColorChanged.emit(self._ess.brush_color)
        self.penWidthChanged.emit(self._ess.pen_width)
        self.toolChanged.emit(self.__tool)
        self.radiusChanged.emit(self._ess.radius)

class FigureStorage(QObject):
    canvas_updated = pyqtSignal()

    def __init__(self, settings: DrawSettings | None = None):
        super().__init__()
        self.__figures = []
        # use provided settings or create default one
        self.settings = settings if isinstance(settings, DrawSettings) else DrawSettings()
        # connect settings signals to update existing/selected figures
        self.settings.penWidthChanged.connect(self._on_pen_width_changed)
        self.settings.brushColorChanged.connect(self._on_brush_color_changed)
        self.settings.penColorChanged.connect(self._on_pen_color_changed)
        self.settings.radiusChanged.connect(self._on_radius_changed)

    # --- signal handlers: propagate setting changes to selected figures ---
    def _on_pen_width_changed(self, w: int):
        for f in self.get_selected():
            f.ess.pen_width = w
        self.canvas_updated.emit()

    def _on_brush_color_changed(self, c: QColor):
        for f in self.get_selected():
            f.ess.brush_color = c
        self.canvas_updated.emit()

    def _on_pen_color_changed(self, c: QColor):
        for f in self.get_selected():
            f.ess.pen_color = c
        self.canvas_updated.emit()

    def _on_radius_changed(self, r: int):
        for f in self.get_selected():
            # if figures use radius concept, update attribute if present
            if hasattr(f, 'radius'):
                try:
                    f.radius = r
                except Exception:
                    pass
        self.canvas_updated.emit()

    def adjust_size_selected(self, delta: int):
        """Попытаться изменить размер выбранных фигур (увеличить/уменьшить).
        Для примера изменяем pen_width или radius для фигур, где это применимо.
        """
        changed = False
        for f in self.get_selected():
            if hasattr(f, 'ess') and isinstance(f.ess, DrawEssentials):
                new_pw = max(1, f.ess.pen_width + delta)
                f.ess.pen_width = new_pw
                self.settings.pen_width = new_pw
                changed = True
            if hasattr(f, 'radius'):
                try:
                    new_r = max(1, f.radius + delta)
                    f.radius = new_r
                    self.settings.radius = new_r
                    changed = True
                except Exception:
                    pass



    def add(self, figure):
        incomplete = self.get_incomplete()
        if incomplete and type(incomplete) == type(figure):
            incomplete.continue_drawing_point(figure.points[0][0], figure.points[0][1])
            print("Figure continued:", incomplete)
            self.canvas_updated.emit()
            return
        elif incomplete:
            QMessageBox.information(None, "info", "Откат незавершённой фигуры.")
            self.delete(incomplete)
        else:
            self.__figures.append(figure)
            print("Figure added:", figure)
            self.canvas_updated.emit()

    def get_all(self):
        return self.__figures

    def get_incomplete(self):
        for fig in self.__figures:
            if getattr(fig, "finished", True) is False:
                return fig
        return None

    def get_selected(self):
        return [f for f in self.__figures if getattr(f, "selected", False)]

    def deselect_all(self):
        changed = False
        for f in self.__figures:
            if getattr(f, "selected", False):
                f.selected = False
                changed = True
        if changed:
            print("All figures deselected")
            self.canvas_updated.emit()

    def delete(self, figure):
        if figure in self.__figures:
            self.__figures.remove(figure)
            print("Figure deleted:", figure)
            self.canvas_updated.emit()

    def delete_selected(self):
        before = len(self.__figures)
        self.__figures = [f for f in self.__figures if not getattr(f, "selected", False)]
        after = len(self.__figures)
        if after != before:
            print(f"Deleted {before - after} selected figure(s)")
            self.canvas_updated.emit()

    def clear_all(self):
        self.__figures.clear()
        print("Storage cleared")
        self.canvas_updated.emit()

class Figure(QObject):
    tolerance = 5
    def __init__(self, ess: DrawEssentials | None = None):
        super().__init__()
        self._ess = copy.deepcopy(ess) if isinstance(ess, DrawEssentials) else DrawEssentials()
        self._selected = False
        self._old_pen_color = None
        self._old_brush_color = None

    @property
    def ess(self) -> DrawEssentials:
        return self._ess
    @ess.setter
    def ess(self, value: DrawEssentials):
        if isinstance(value, DrawEssentials):
            self._ess = value

    def draw(self, painter: QPainter):
        raise NotImplementedError

    def bounds(self) -> QRect:
        raise NotImplementedError

    @property
    def selected(self) -> bool:
        return self._selected
    @selected.setter
    def selected(self, value: bool):
        if value and not self._selected:
            self._selected = True
            try:
                self._old_pen_color = QColor(self._ess.pen_color)
            except Exception:
                self._old_pen_color = self._ess.pen_color
            try:
                self._old_brush_color = QColor(self._ess.brush_color)
            except Exception:
                self._old_brush_color = self._ess.brush_color
            self._ess.pen_color = QColor(255, 0, 0)
            self._ess.brush_color = QColor(255, 0, 0, 100)
        elif not value and self._selected:
            self._selected = False
            sel_pen = QColor(255, 0, 0)
            sel_brush = QColor(255, 0, 0, 100)
            try:
                if self._ess.pen_color == sel_pen and self._old_pen_color is not None:
                    self._ess.pen_color = self._old_pen_color
                # if user changed pen color while selected, keep the new color
                if self._ess.brush_color == sel_brush and self._old_brush_color is not None:
                    self._ess.brush_color = self._old_brush_color
            except Exception:
                # fallback: restore saved values if possible
                if self._old_pen_color is not None:
                    self._ess.pen_color = self._old_pen_color
                if self._old_brush_color is not None:
                    self._ess.brush_color = self._old_brush_color
            # clear saved originals
            self._old_pen_color = None
            self._old_brush_color = None

    @staticmethod
    def is_fit_in_bounds(rect1: QRect, rect2: QRect) -> bool:
        b = rect1
        if b.isNull():
            return True
        return (b.left() >= rect2.left() and
                b.top() >= rect2.top() and
                b.right() <= rect2.right() and
                b.bottom() <= rect2.bottom())

    def hit_test(self, x: int, y: int) -> bool:
        xy_bounds = QRect(x, y, 1, 1)
        return self.is_fit_in_bounds(xy_bounds, QRect(self.bounds()))

class Point(Figure):
    def __init__(self, x: int, y: int, ess: DrawEssentials | None = None):
        super().__init__(ess)
        self.__x = x
        self.__y = y

    radius = 1
    pen_width = 2

    @property
    def x(self): return self.__x
    @property
    def y(self): return self.__y

    def draw(self, painter: QPainter):
        pen = QPen(self._ess.pen_color, self.pen_width)
        brush = QBrush()
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawEllipse(QPoint(self.__x, self.__y), self.radius, self.radius)

    def bounds(self) -> QRect:
        r = max(1, self.pen_width, self.tolerance)
        return QRect(self.__x - r, self.__y - r, r * 2 + 1, r * 2 + 1)

    def change_position(self, delta_x: int, delta_y, bounds: QRect = None):
        new_rect = QRect(self.__x + delta_x - self.tolerance,
                         self.__y + delta_y - self.tolerance,
                         self.tolerance * 2 + 1, self.tolerance * 2 + 1)
        if bounds is None or self.is_fit_in_bounds(new_rect, bounds):
            self.__x += delta_x
            self.__y += delta_y

class Line(Figure):
    def __init__(self, x1: int, y1: int, x2: int = None, y2: int = None, ess: DrawEssentials | None = None):
        super().__init__(ess)
        self.points = [[x1, y1], [x2, y2]]
        self.finished = not (x2 is None or y2 is None)

    def draw(self, painter: QPainter):
        if not self.finished:
            return
        pen = QPen(self._ess.pen_color, self._ess.pen_width)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(QPoint(self.points[0][0], self.points[0][1]),
                         QPoint(self.points[1][0], self.points[1][1]))

    def continue_drawing_point(self, point_x: int, point_y: int):
        for p in range(len(self.points)):
            if self.points[p][0] is None or self.points[p][1] is None:
                self.points[p][0] = point_x
                self.points[p][1] = point_y
                if p == len(self.points) - 1:
                    self.finished = True
                break

    def bounds(self) -> QRect:
        x1, y1 = self.points[0]
        x2, y2 = self.points[1]
        if x1 is None or y1 is None:
            return QRect()
        if x2 is None or y2 is None:
            r = max(self._ess.pen_width, self.tolerance)
            return QRect(x1 - r, y1 - r, r * 2 + 1, r * 2 + 1)
        left = min(x1, x2)
        top = min(y1, y2)
        right = max(x1, x2)
        bottom = max(y1, y2)
        r = max(self._ess.pen_width, self.tolerance)
        return QRect(left - r, top - r, (right - left) + r * 2 + 1, (bottom - top) + r * 2 + 1)

    def change_position(self, delta_x: int, delta_y, bounds: QRect):
        x1, y1 = self.points[0]
        x2, y2 = self.points[1]
        new_x1 = x1 + delta_x
        new_y1 = y1 + delta_y
        new_x2 = x2 + delta_x
        new_y2 = y2 + delta_y

        if self.is_fit_in_bounds(QRect(min(new_x1, new_x2) - self.tolerance,
                                       min(new_y1, new_y2) - self.tolerance,
                                       abs(new_x2 - new_x1) + self.tolerance * 2 + 1,
                                       abs(new_y2 - new_y1) + self.tolerance * 2 + 1), bounds):
            self.points[0][0] = new_x1
            self.points[0][1] = new_y1
            self.points[1][0] = new_x2
            self.points[1][1] = new_y2

class Rectangle(Figure):
    def __init__(self, x1: int, y1: int, x2: int = None, y2: int = None, ess: DrawEssentials | None = None):
        super().__init__(ess)
        self.points = [[x1, y1], [x2, y2], [None, None], [None, None]]
        self.finished = False

    def draw(self, painter: QPainter):
        if not self.finished:
            return
        pen = QPen(self._ess.pen_color, self._ess.pen_width)
        brush = QBrush(self._ess.brush_color)
        painter.setPen(pen)
        painter.setBrush(brush)
        pts = [pt for pt in self.points if pt[0] is not None and pt[1] is not None]
        if not pts:
            return
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        left = min(xs)
        top = min(ys)
        width = max(xs) - left
        height = max(ys) - top
        painter.drawRect(left, top, width, height)

    def continue_drawing_point(self, point_x: int, point_y: int):
        # Заполняем следующую пустую точку по одной, как в Triangle.
        for p in range(len(self.points)):
            if self.points[p][0] is None or self.points[p][1] is None:
                self.points[p][0] = point_x
                self.points[p][1] = point_y
                # если это последняя точка - завершаем фигуру
                if p == len(self.points) - 1:
                    self.finished = True
                break

    def bounds(self) -> QRect:
        pts = [pt for pt in self.points if pt[0] is not None and pt[1] is not None]
        if not pts:
            return QRect()
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        left, top, right, bottom = min(xs), min(ys), max(xs), max(ys)
        r = max(self._ess.pen_width, self.tolerance)
        return QRect(left - r, top - r, (right - left) + r * 2 + 1, (bottom - top) + r * 2 + 1)

    def change_position(self, delta_x: int, delta_y, bounds: QRect):
        new_pts = []
        for x, y in self.points:
            if x is None or y is None:
                new_pts.append((x, y))
                continue
            new_pts.append((x + delta_x, y + delta_y))
        pts_to_check = [(x, y) for x, y in new_pts if x is not None and y is not None]
        if not pts_to_check:
            return
        xs = [p[0] for p in pts_to_check]
        ys = [p[1] for p in pts_to_check]
        new_rect = QRect(min(xs) - self.tolerance, min(ys) - self.tolerance,
                         max(xs) - min(xs) + self.tolerance * 2 + 1,
                         max(ys) - min(ys) + self.tolerance * 2 + 1)
        if self.is_fit_in_bounds(new_rect, bounds):
            for i, (x, y) in enumerate(new_pts):
                if x is not None and y is not None:
                    self.points[i][0] = x
                    self.points[i][1] = y

class Square(Rectangle):
    def __init__(self, x1: int, y1: int, x2: int = None, y2: int = None, ess: DrawEssentials | None = None):
        super().__init__(x1, y1, x2, y2, ess)

    def draw(self, painter: QPainter):
        if not self.finished:
            return
        pen = QPen(self._ess.pen_color, self._ess.pen_width)
        brush = QBrush(self._ess.brush_color)
        painter.setPen(pen)
        painter.setBrush(brush)
        x1, y1 = self.points[0]
        x2, y2 = self.points[1]
        size = max(abs(x2 - x1), abs(y2 - y1))
        left = x1 if x2 >= x1 else x1 - size
        top = y1 if y2 >= y1 else y1 - size
        painter.drawRect(left, top, size, size)

class Circle(Figure):
    def __init__(self, x: int, y: int, rx: int = None, ry: int = None, ess: DrawEssentials | None = None):
        super().__init__(ess)
        self.points = [[x, y], [rx, ry]]
        self.finished = not (rx is None or ry is None)

    def draw(self, painter: QPainter):
        if not self.finished:
            return
        pen = QPen(self._ess.pen_color, self._ess.pen_width)
        brush = QBrush(self._ess.brush_color)
        painter.setPen(pen)
        painter.setBrush(brush)
        cx, cy = self.points[0]
        px, py = self.points[1]
        rx = abs(px - cx)
        ry = abs(py - cy)
        r = max(rx, ry)
        painter.drawEllipse(QPoint(cx, cy), r, r)

    def continue_drawing_point(self, point_x: int, point_y: int):
        for p in range(len(self.points)):
            if self.points[p][0] is None or self.points[p][1] is None:
                self.points[p][0] = point_x
                self.points[p][1] = point_y
                if p == len(self.points) - 1:
                    self.finished = True
                break

    def bounds(self) -> QRect:
        cx, cy = self.points[0]
        px, py = self.points[1]
        if cx is None or cy is None:
            return QRect()
        if px is None or py is None:
            r = max(self._ess.pen_width, self.tolerance)
            return QRect(cx - r, cy - r, r * 2 + 1, r * 2 + 1)
        radius = max(abs(px - cx), abs(py - cy))
        r = max(radius, self._ess.pen_width, self.tolerance)
        return QRect(cx - r, cy - r, r * 2 + 1, r * 2 + 1)

    def change_position(self, delta_x: int, delta_y, bounds: QRect):
        cx, cy = self.points[0]
        px, py = self.points[1]
        new_cx = cx + delta_x
        new_cy = cy + delta_y
        new_px = px + delta_x if px is not None else None
        new_py = py + delta_y if py is not None else None
        if new_px is None or new_py is None:
            new_rect = QRect(new_cx - self.tolerance, new_cy - self.tolerance,
                             self.tolerance * 2 + 1, self.tolerance * 2 + 1)
        else:
            radius = max(abs(new_px - new_cx), abs(new_py - new_cy))
            new_rect = QRect(new_cx - radius - self.tolerance, new_cy - radius - self.tolerance,
                             radius * 2 + self.tolerance * 2 + 1, radius * 2 + self.tolerance * 2 + 1)

        if self.is_fit_in_bounds(new_rect, bounds):
            self.points[0][0] = new_cx
            self.points[0][1] = new_cy
            if new_px is not None and new_py is not None:
                self.points[1][0] = new_px
                self.points[1][1] = new_py

class Ellipse(Circle):
    def draw(self, painter: QPainter):
        if not self.finished:
            return
        pen = QPen(self._ess.pen_color, self._ess.pen_width)
        brush = QBrush(self._ess.brush_color)
        painter.setPen(pen)
        painter.setBrush(brush)
        cx, cy = self.points[0]
        px, py = self.points[1]
        rx = abs(px - cx)
        ry = abs(py - cy)
        painter.drawEllipse(QRect(cx - rx, cy - ry, rx * 2, ry * 2))

class Triangle(Figure):
    def __init__(self, x1: int, y1: int, x2: int = None, y2: int = None, ess: DrawEssentials | None = None):
        super().__init__(ess)
        self.points = [[x1, y1], [x2, y2], [None, None]]
        self.finished = False  # завершим только после 3-й точки

    def draw(self, painter: QPainter):
        if not self.finished:
            return
        pen = QPen(self._ess.pen_color, self._ess.pen_width)
        brush = QBrush(self._ess.brush_color)
        painter.setPen(pen)
        painter.setBrush(brush)
        p1 = QPoint(self.points[0][0], self.points[0][1])
        p2 = QPoint(self.points[1][0], self.points[1][1])
        p3 = QPoint(self.points[2][0], self.points[2][1])
        poly = QPolygon([p1, p2, p3])
        painter.drawPolygon(poly)

    def continue_drawing_point(self, point_x: int, point_y: int):
        for p in range(len(self.points)):
            if self.points[p][0] is None or self.points[p][1] is None:
                self.points[p][0] = point_x
                self.points[p][1] = point_y
                if p == len(self.points) - 1:
                    self.finished = True
                break

    def bounds(self) -> QRect:
        pts = [pt for pt in self.points if pt[0] is not None and pt[1] is not None]
        if not pts:
            return QRect()
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        left, top, right, bottom = min(xs), min(ys), max(xs), max(ys)
        r = max(self._ess.pen_width, self.tolerance)
        return QRect(left - r, top - r, (right - left) + r * 2 + 1, (bottom - top) + r * 2 + 1)

    def change_position(self, delta_x: int, delta_y, bounds: QRect):
        new_pts = []
        for x, y in self.points:
            if x is None or y is None:
                new_pts.append((x, y))
                continue
            new_pts.append((x + delta_x, y + delta_y))
        pts_to_check = [(x, y) for x, y in new_pts if x is not None and y is not None]
        if not pts_to_check:
            return
        xs = [p[0] for p in pts_to_check]
        ys = [p[1] for p in pts_to_check]
        new_rect = QRect(min(xs) - self.tolerance, min(ys) - self.tolerance,
                         max(xs) - min(xs) + self.tolerance * 2 + 1,
                         max(ys) - min(ys) + self.tolerance * 2 + 1)
        if self.is_fit_in_bounds(new_rect, bounds):
            for i, (x, y) in enumerate(new_pts):
                if x is not None and y is not None:
                    self.points[i][0] = x
                    self.points[i][1] = y

class Main(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main.ui", self)
        self.setWindowTitle("Paint")
        self._last_window_size = self.size()
        self._last_canvas_size = QSize(0, 0)

        # Панель настроек
        self.settings = DrawSettings()
        print("Initial settings:", self.settings.radius)

        # settings -> UI
        self.settings.penColorChanged.connect(
            lambda c: self.outlinecolor.setStyleSheet(f"background-color: {c.name()}"))
        self.settings.brushColorChanged.connect(
            lambda c: self.innercolor.setStyleSheet(f"background-color: {c.name()}"))
        self.settings.penWidthChanged.connect(self.pen_width.setValue)
        self.settings.toolChanged.connect(lambda name: getattr(self, name).setChecked(True)
                                          if hasattr(self, name) else None)
        self.settings.radiusChanged.connect(self.spinBox_radius.setValue)
        self.settings.broadcast()

        # UI -> settings
        self.pen_width.valueChanged.connect(lambda v: setattr(self.settings, "pen_width", v))
        self.pushButton_outlinecolor.clicked.connect(
            lambda: setattr(self.settings, "pen_color",
                            QColorDialog.getColor(self.settings.pen_color, self)))
        self.pushButton_innercolor.clicked.connect(
            lambda: setattr(self.settings, "brush_color",
                            QColorDialog.getColor(self.settings.brush_color, self)))
        self.spinBox_radius.valueChanged.connect(lambda v: setattr(self.settings, "radius", v))
        for name in ["circle","ellipse","line","rectangle","square","triangle","point"]:
            btn = getattr(self, name, None)
            if btn:
                btn.clicked.connect(lambda checked, n=name: setattr(self.settings, "tool", n))

        # Холст
        self.storage = FigureStorage(self.settings)
        self.canvas = getattr(self, "canvas", None)
        if self.canvas:
            self.canvas.installEventFilter(self)
            self.canvas.setMouseTracking(True)
            self.canvas.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # чтобы ловить клавиши
            self.storage.canvas_updated.connect(lambda: self.canvas.update())

        self._last_mouse_pos = None
        self.show()

    def showEvent(self, event):
        super().showEvent(event)
        if self.canvas:
            self.settings.csize = self.canvas.size()
            self._last_canvas_size = self.canvas.size()
            self._last_window_size = self.size()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.canvas:
            new_canvas_size = self.canvas.size()
            w, h = new_canvas_size.width(), new_canvas_size.height()
            fits = True
            for fig in self.storage.get_all():
                if getattr(fig, "finished", True) is False:
                    continue
                if fig.is_fit_in_bounds(QRect(fig.bounds()), QRect(0, 0, w, h)) is False:
                    fits = False
                    break
            if not fits:
                QMessageBox.information(self, "Размер", "Нельзя уменьшить окно: фигуры не помещаются.")
                self.resize(self._last_window_size)
                return
            self.settings.csize = new_canvas_size
            self._last_canvas_size = new_canvas_size
            self._last_window_size = self.size()

    def eventFilter(self, obj, event):
        # --- клавиатура для удаления/снятия выделения ---
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                self.storage.delete_selected()
                return True
            # увеличить/уменьшить размер выделенных фигур
            if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal, Qt.Key.Key_Plus):
                self.storage.adjust_size_selected(1)
                return True
            if key in (Qt.Key.Key_Minus, Qt.Key.Key_Minus, Qt.Key.Key_Underscore):
                self.storage.adjust_size_selected(-1)
                return True
            if key == Qt.Key.Key_Escape:
                self.storage.deselect_all()
                return True

        if obj is getattr(self, "canvas", None):
            # мышь над холстом
            if event.type() == QEvent.Type.MouseMove:
                pos = event.position().toPoint()
                if event.buttons() & Qt.MouseButton.LeftButton:
                    if self._last_mouse_pos is None:
                        self._last_mouse_pos = pos
                    dx = pos.x() - self._last_mouse_pos.x()
                    dy = pos.y() - self._last_mouse_pos.y()
                    self._last_mouse_pos = pos

                    moved = False
                    for fig in self.storage.get_all():
                        if fig.selected:
                            canvas_size = self.settings.csize
                            bounds = QRect(0, 0, canvas_size.width(), canvas_size.height())
                            fig.change_position(dx, dy, bounds)
                            moved = True
                    if moved:
                        self.canvas.update()
                        print("Figure(s) moved by", dx, dy)
                        return True
                else:
                    self._last_mouse_pos = None
                    if any(fig.hit_test(pos.x(), pos.y()) for fig in self.storage.get_all()):
                        self.canvas.setCursor(Qt.CursorShape.PointingHandCursor)
                    else:
                        self.canvas.setCursor(Qt.CursorShape.ArrowCursor)
                    return True

            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                pos = event.position().toPoint()
                self._last_mouse_pos = pos
                self.canvas.setFocus(Qt.FocusReason.MouseFocusReason)  # чтобы Delete сразу работал
                print("Mouse press on canvas:", pos.x(), pos.y())
                mods = event.modifiers()

                # попали в фигуру?
                for fig in reversed(self.storage.get_all()):
                    if fig.hit_test(pos.x(), pos.y()):
                        if mods & Qt.KeyboardModifier.ControlModifier:
                            # стэковое переключение
                            fig.selected = not fig.selected
                        else:
                            # одиночный выбор
                            # если уже только эта выделена, оставим как есть; иначе переустановим
                            only_this_selected = fig.selected and all(
                                (f is fig) or (not f.selected) for f in self.storage.get_all()
                            )
                            if not only_this_selected:
                                self.storage.deselect_all()
                                fig.selected = True
                        self.canvas.update()
                        print("Figure selected toggled:", fig, "Now selected:", fig.selected)
                        return True

                # клик в пустоту — снять выделение (если не зажат Ctrl)
                if not (mods & Qt.KeyboardModifier.ControlModifier):
                    self.storage.deselect_all()

                # создание новой фигуры, если задан инструмент
                tool_name = self.settings.tool
                if tool_name:
                    cls = globals().get(tool_name.capitalize())
                    if not callable(cls):
                        QMessageBox.information(self, "info", f"Unknown tool: {tool_name}")
                        return True
                    try:
                        self.storage.add(cls(pos.x(), pos.y(), ess=self.settings.ess))
                    except TypeError:
                        self.storage.add(cls(pos.x(), pos.y(), self.settings.ess))
                return True

            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self._last_mouse_pos = None
                return True

            if event.type() == QEvent.Type.Paint:
                painter = QPainter(self.canvas)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                figures_count = 0
                for fig in self.storage.get_all():
                    fig.draw(painter)
                    figures_count += 1
                painter.end()
                print("Paint event on canvas", "Figures drawn:", figures_count)
                return True

        return super().eventFilter(obj, event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Main()
    sys.exit(app.exec())
