"""Handles rendering of all shapes and obstacles"""
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QPolygonF
from utils import calculate_polygon_points


class ShapeRenderer:
    """Renders obstacles and shapes on the canvas"""
    
    def __init__(self):
        self.rotation_handle_size = 10
        self.resize_handle_size = 8
    
    def draw_single_obstacle(self, painter, obstacle, preview=False, selected=False, invalid=False):
        """Draw a single obstacle shape"""
        shape_type = obstacle['type']
        x = obstacle['x']
        y = obstacle['y']
        width = obstacle['width']
        height = obstacle['height']
        color = obstacle['color']
        rotation = obstacle.get('rotation', 0)
        
        # Save painter state
        painter.save()
        
        # Apply rotation if needed
        if rotation != 0:
            center_x = x + width / 2
            center_y = y + height / 2
            painter.translate(center_x, center_y)
            painter.rotate(rotation)
            painter.translate(-center_x, -center_y)
        
        # Set up painter
        if invalid:
            pen = QPen(QColor(255, 0, 0), 2, Qt.DashLine)
            brush = QBrush(QColor(255, 0, 0, 30))
        elif preview:
            pen = QPen(color, 2, Qt.DashLine)
            brush = QBrush(QColor(color.red(), color.green(), color.blue(), 50))
        elif selected:
            pen = QPen(QColor(255, 200, 0), 4)
            brush = QBrush(color)
        else:
            pen = QPen(QColor(50, 50, 50), 2)
            brush = QBrush(color)
        
        painter.setPen(pen)
        painter.setBrush(brush)
        
        # Draw based on shape type
        if shape_type == 'rectangle':
            painter.drawRect(x, y, width, height)
        elif shape_type == 'circle':
            painter.drawEllipse(x, y, width, height)
        elif shape_type == 'triangle':
            points = [
                QPoint(x + width // 2, y),
                QPoint(x, y + height),
                QPoint(x + width, y + height)
            ]
            painter.drawPolygon(QPolygonF(points))
        elif shape_type == 'pentagon':
            cx = x + width // 2
            cy = y + height // 2
            radius = min(width, height) // 2
            points = calculate_polygon_points(cx, cy, radius, 5)
            painter.drawPolygon(QPolygonF(points))
        elif shape_type == 'hexagon':
            cx = x + width // 2
            cy = y + height // 2
            radius = min(width, height) // 2
            points = calculate_polygon_points(cx, cy, radius, 6)
            painter.drawPolygon(QPolygonF(points))
        elif shape_type == 'custom_polygon':
            absolute_points = [QPoint(x + p.x(), y + p.y()) for p in obstacle['points']]
            painter.drawPolygon(QPolygonF(absolute_points))
        
        painter.restore()
    
    def draw_rotation_handle(self, painter, obstacle):
        """Draw rotation handle for selected obstacle"""
        x = obstacle['x'] + obstacle['width']
        y = obstacle['y']
        handle_pos = QPoint(int(x), int(y))
        
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        painter.setBrush(QBrush(QColor(255, 100, 100)))
        painter.drawEllipse(
            handle_pos.x() - self.rotation_handle_size,
            handle_pos.y() - self.rotation_handle_size,
            self.rotation_handle_size * 2,
            self.rotation_handle_size * 2
        )
    
    def draw_resize_handles(self, painter, obstacle):
        """Draw resize handles (four corners) for selected obstacle"""
        x = obstacle['x']
        y = obstacle['y']
        width = obstacle['width']
        height = obstacle['height']
        
        handles = {
            'tl': QPoint(int(x), int(y)),
            'tr': QPoint(int(x + width), int(y)),
            'bl': QPoint(int(x), int(y + height)),
            'br': QPoint(int(x + width), int(y + height))
        }
        
        painter.setPen(QPen(QColor(0, 100, 255), 2))
        painter.setBrush(QBrush(QColor(100, 150, 255)))
        
        for handle_pos in handles.values():
            painter.drawRect(
                handle_pos.x() - self.resize_handle_size,
                handle_pos.y() - self.resize_handle_size,
                self.resize_handle_size * 2,
                self.resize_handle_size * 2
            )
    
    def draw_grid(self, painter, width, height, grid_size):
        """Draw the grid lines"""
        pen = QPen(QColor(200, 200, 200), 1)
        painter.setPen(pen)
        
        # Draw vertical lines
        x = 0
        while x <= width:
            painter.drawLine(x, 0, x, height)
            x += grid_size
        
        # Draw horizontal lines
        y = 0
        while y <= height:
            painter.drawLine(0, y, width, y)
            y += grid_size