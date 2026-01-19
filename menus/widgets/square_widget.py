from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen


class SquareWidget(QWidget):
    """Base widget with a dark rounded square background."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Render constants
        self.radius: int = 6
        self.normal_fill_color = QColor(48, 48, 48, 72)
        self.normal_border_color = QColor(48, 48, 48)
        self.severe_fill_color = QColor(192, 24, 36, 72)
        self.severe_border_color = QColor(192, 24, 36)
        self.fill_color = self.normal_fill_color
        self.border_color = self.normal_border_color
        self.is_severe = False
        
        # Set background via palette (doesn't break child widgets)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), self.fill_color)
        self.setPalette(palette)
        self.setAutoFillBackground(True)
        
        # No margins or spacing influence
        self.setContentsMargins(0, 0, 0, 0)
        self.setMinimumHeight(3 * self.radius)


    def set_severity(self, severity: bool):
        self.is_severe = severity
        self.fill_color = self.severe_fill_color if self.is_severe else self.normal_fill_color
        self.border_color = self.severe_border_color if self.is_severe else self.normal_border_color

        palette = self.palette()
        palette.setColor(self.backgroundRole(), self.fill_color)
        self.setPalette(palette)


    def paintEvent(self, event):
        # Let Qt render normally first (children + background)
        super().paintEvent(event)
        
        # Then paint the border on top
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)

        # Just paint border, no fill (background already handled)
        pen = QPen(self.border_color, 1)
        painter.setPen(pen)
        painter.drawPath(path)
