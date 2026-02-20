"""Utility functions for the obstacle editor"""
import math
from PyQt5.QtCore import QPoint, QPointF


def calculate_distance(point1, point2):
    """Calculate Euclidean distance between two points
    
    Args:
        point1: QPoint or QPointF
        point2: QPoint or QPointF
        
    Returns:
        float: Distance between the two points
    """
    dx = point2.x() - point1.x()
    dy = point2.y() - point1.y()
    return math.sqrt(dx * dx + dy * dy)


def clamp(value, min_value, max_value):
    """Clamp a value between min and max
    
    Args:
        value: Value to clamp
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        
    Returns:
        Clamped value
    """
    return max(min_value, min(value, max_value))


def snap_to_grid(value, grid_size):
    """Snap a value to the nearest grid position
    
    Args:
        value: Value to snap
        grid_size: Size of the grid
        
    Returns:
        Snapped value
    """
    return round(value / grid_size) * grid_size