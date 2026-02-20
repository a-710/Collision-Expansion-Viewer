"""Handles all mouse interactions"""
import math
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QCursor
from utils import calculate_distance


class MouseHandler:
    """Manages mouse events and interactions"""
    
    def __init__(self, canvas):
        self.canvas = canvas
        self.rotation_handle_size = 10
        self.resize_handle_size = 8
    
    def is_on_rotation_handle(self, pos, obstacle):
        """Check if a point is on the rotation handle"""
        x = obstacle['x'] + obstacle['width']
        y = obstacle['y']
        handle_pos = QPoint(int(x), int(y))
        distance = calculate_distance(pos, handle_pos)
        return distance <= self.rotation_handle_size
    
    def get_resize_handles(self, obstacle):
        """Get positions of all resize handles"""
        x = obstacle['x']
        y = obstacle['y']
        width = obstacle['width']
        height = obstacle['height']
        
        return {
            'tl': QPoint(int(x), int(y)),
            'tr': QPoint(int(x + width), int(y)),
            'bl': QPoint(int(x), int(y + height)),
            'br': QPoint(int(x + width), int(y + height))
        }
    
    def get_resize_handle_at(self, pos, obstacle):
        """Check if position is on any resize handle"""
        handles = self.get_resize_handles(obstacle)
        
        for handle_name, handle_pos in handles.items():
            distance = calculate_distance(pos, handle_pos)
            if distance <= self.resize_handle_size:
                return handle_name
        return None
    
    def get_resize_cursor(self, handle):
        """Get appropriate cursor for resize handle"""
        cursors = {
            'tl': Qt.SizeFDiagCursor,
            'tr': Qt.SizeBDiagCursor,
            'bl': Qt.SizeBDiagCursor,
            'br': Qt.SizeFDiagCursor
        }
        return QCursor(cursors.get(handle, Qt.ArrowCursor))
    
    def resize_obstacle(self, obstacle, handle, pos, grid_size, snap_enabled):
        """Resize obstacle based on which handle is being dragged"""
        from utils import snap_to_grid
        
        x = obstacle['x']
        y = obstacle['y']
        width = obstacle['width']
        height = obstacle['height']
        min_size = 10
        
        snap_pos = snap_to_grid(pos, grid_size, snap_enabled)
        
        if handle == 'tl':
            new_x = snap_pos.x()
            new_y = snap_pos.y()
            new_width = (x + width) - new_x
            new_height = (y + height) - new_y
            
            if new_width >= min_size and new_height >= min_size:
                obstacle['x'] = new_x
                obstacle['y'] = new_y
                obstacle['width'] = new_width
                obstacle['height'] = new_height
        
        elif handle == 'tr':
            new_y = snap_pos.y()
            new_width = snap_pos.x() - x
            new_height = (y + height) - new_y
            
            if new_width >= min_size and new_height >= min_size:
                obstacle['y'] = new_y
                obstacle['width'] = new_width
                obstacle['height'] = new_height
        
        elif handle == 'bl':
            new_x = snap_pos.x()
            new_width = (x + width) - new_x
            new_height = snap_pos.y() - y
            
            if new_width >= min_size and new_height >= min_size:
                obstacle['x'] = new_x
                obstacle['width'] = new_width
                obstacle['height'] = new_height
        
        elif handle == 'br':
            new_width = snap_pos.x() - x
            new_height = snap_pos.y() - y
            
            if new_width >= min_size and new_height >= min_size:
                obstacle['width'] = new_width
                obstacle['height'] = new_height
    
    def calculate_rotation(self, obstacle, mouse_pos):
        """Calculate rotation angle based on mouse position"""
        center_x = obstacle['x'] + obstacle['width'] / 2
        center_y = obstacle['y'] + obstacle['height'] / 2
        
        dx = mouse_pos.x() - center_x
        dy = mouse_pos.y() - center_y
        angle = math.degrees(math.atan2(dy, dx))
        
        return angle % 360