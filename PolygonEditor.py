"""Handles custom polygon drawing and editing"""
from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QPolygonF
from PyQt5.QtCore import Qt


class PolygonEditor:
    """Manages custom polygon drawing state and operations"""
    
    def __init__(self, grid_size=20):
        """Initialize the polygon editor
        
        Args:
            grid_size: Grid size for snapping points (default: 20)
        """
        self.points = []  # List of QPointF
        self.is_drawing = False
        self.preview_point = None  # Current mouse position for preview
        self.grid_size = grid_size  # Grid size for snapping
        
    def start_drawing(self):
        """Start a new polygon drawing session"""
        self.points = []
        self.is_drawing = True
        self.preview_point = None
    
    def snap_point_to_grid(self, point):
        """Snap a point to the grid (ALWAYS for custom polygons)
        
        Args:
            point: QPointF to snap
            
        Returns:
            QPointF: Snapped point
        """
        x = round(point.x() / self.grid_size) * self.grid_size
        y = round(point.y() / self.grid_size) * self.grid_size
        return QPointF(x, y)
        
    def add_point(self, point):
        """Add a point to the current polygon (ALWAYS snapped to grid)
        
        Args:
            point: QPointF position to add
            
        Returns:
            bool: True if point was added successfully
        """
        if not self.is_drawing:
            return False
        
        # ALWAYS snap custom polygon points to grid
        snapped_point = self.snap_point_to_grid(point)
        self.points.append(snapped_point)
        return True
    
    def set_preview_point(self, point):
        """Set the preview point for visual feedback (snapped to grid)
        
        Args:
            point: QPointF position for preview line
        """
        if point:
            # ALWAYS snap preview point to grid
            self.preview_point = self.snap_point_to_grid(point)
        else:
            self.preview_point = None
    
    def can_finish(self):
        """Check if polygon has minimum required points
        
        Returns:
            bool: True if polygon can be finished (minimum 3 points)
        """
        return len(self.points) >= 3
    
    def cancel_drawing(self):
        """Cancel current polygon drawing and clear points"""
        self.points = []
        self.is_drawing = False
        self.preview_point = None
    
    def _remove_duplicate_points(self, points):
        """Remove consecutive duplicate points
        
        Args:
            points: List of QPointF
            
        Returns:
            List of QPointF with duplicates removed
        """
        if len(points) < 2:
            return points
        
        cleaned = [points[0]]
        tolerance = self.grid_size / 2  # Use half grid size as tolerance
        
        for i in range(1, len(points)):
            # Calculate distance from last added point
            dx = points[i].x() - cleaned[-1].x()
            dy = points[i].y() - cleaned[-1].y()
            distance = (dx * dx + dy * dy) ** 0.5
            
            if distance > tolerance:
                cleaned.append(points[i])
        
        # Check if last point is too close to first point
        if len(cleaned) > 1:
            dx = cleaned[-1].x() - cleaned[0].x()
            dy = cleaned[-1].y() - cleaned[0].y()
            distance = (dx * dx + dy * dy) ** 0.5
            if distance < tolerance:
                cleaned.pop()
        
        return cleaned
    
    def create_obstacle(self, color):
        """Create an obstacle dictionary from the current polygon
        
        Args:
            color: QColor for the obstacle
            
        Returns:
            dict: Obstacle dictionary, or None if not enough points
        """
        if not self.can_finish():
            return None
        
        # Calculate bounding box
        if not self.points:
            return None
        
        # Clean up duplicate points
        cleaned_points = self._remove_duplicate_points(self.points)
        
        if len(cleaned_points) < 3:
            return None
        
        min_x = min(p.x() for p in cleaned_points)
        min_y = min(p.y() for p in cleaned_points)
        max_x = max(p.x() for p in cleaned_points)
        max_y = max(p.y() for p in cleaned_points)
        
        width = max_x - min_x
        height = max_y - min_y
        
        # Ensure minimum size
        if width < 10 or height < 10:
            return None
        
        # Convert points to local coordinates (relative to bounding box)
        local_points = [QPointF(p.x() - min_x, p.y() - min_y) for p in cleaned_points]
        
        obstacle = {
            'type': 'custom_polygon',
            'x': int(min_x),
            'y': int(min_y),
            'width': int(width),
            'height': int(height),
            'rotation': 0,  # Custom polygons DO NOT support rotation
            'can_rotate': False,  # Flag to prevent rotation
            'color': color,
            'points': local_points  # Store local coordinates - these form STRAIGHT LINES between consecutive points
        }
        
        return obstacle
    
    def draw_preview(self, painter):
        """Draw the polygon being created with preview line
        
        Args:
            painter: QPainter object to draw with
        """
        if not self.is_drawing or len(self.points) == 0:
            return
        
        # Draw edges between existing points (STRAIGHT LINES)
        pen = QPen(QColor(100, 150, 200), 2, Qt.SolidLine)
        painter.setPen(pen)
        
        for i in range(len(self.points) - 1):
            painter.drawLine(self.points[i], self.points[i + 1])
        
        # Draw closing edge if we have enough points
        if len(self.points) >= 3:
            pen.setStyle(Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(self.points[-1], self.points[0])
        
        # Draw preview line from last point to current mouse position
        if self.preview_point and len(self.points) > 0:
            pen = QPen(QColor(100, 150, 200), 1, Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(self.points[-1], self.preview_point)
            
            # If we have 2+ points, also show closing preview
            if len(self.points) >= 2:
                painter.drawLine(self.preview_point, self.points[0])
        
        # Draw vertex points
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(255, 100, 100)))
        
        for point in self.points:
            painter.drawEllipse(point, 4, 4)
        
        # Draw first point larger to indicate start
        if len(self.points) > 0:
            painter.setBrush(QBrush(QColor(0, 255, 0)))
            painter.drawEllipse(self.points[0], 6, 6)
        
        # Draw grid snap indicator at preview point
        if self.preview_point:
            painter.setPen(QPen(QColor(150, 150, 150), 1, Qt.DotLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(self.preview_point, 8, 8)
    
    def get_point_count(self):
        """Get the current number of points
        
        Returns:
            int: Number of points in current polygon
        """
        return len(self.points)