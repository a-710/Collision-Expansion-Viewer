"""Handles obstacle overlap detection and geometry checks"""
from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QPolygonF, QPainterPath
import math
import numpy as np


class CollisionDetector:
    """Detects collisions and overlaps between obstacles"""
    
    # Minimum gap enforced between collision boxes (invisible to user)
    # This is the TOTAL gap between two collision boxes
    COLLISION_BOX_MIN_GAP = 20  # pixels - this is the space BETWEEN the gray areas
    
    def __init__(self, min_spacing=5):
        """
        Args:
            min_spacing: Additional spacing buffer for original obstacles in pixels (default: 5)
        """
        self.min_spacing = min_spacing
    
    def get_obstacle_vertices(self, obstacle):
        """Get actual vertices of an obstacle accounting for rotation and shape
        
        Args:
            obstacle: Obstacle dictionary
            
        Returns:
            List of QPointF representing the obstacle's vertices
        """
        obstacle_type = obstacle.get('type', 'rectangle')
        x = obstacle['x']
        y = obstacle['y']
        width = obstacle['width']
        height = obstacle['height']
        rotation = obstacle.get('rotation', 0)
        
        # Generate local vertices based on shape
        if obstacle_type == 'rectangle':
            local_vertices = [
                QPointF(0, 0),
                QPointF(width, 0),
                QPointF(width, height),
                QPointF(0, height)
            ]
        elif obstacle_type == 'triangle':
            local_vertices = [
                QPointF(width / 2, 0),       # Top center
                QPointF(width, height),      # Bottom right
                QPointF(0, height)           # Bottom left
            ]
        elif obstacle_type == 'pentagon':
            cx, cy = width / 2, height / 2
            radius = min(width, height) / 2
            local_vertices = []
            for i in range(5):
                angle = -math.pi / 2 + (2 * math.pi * i / 5)
                local_vertices.append(QPointF(
                    cx + radius * math.cos(angle),
                    cy + radius * math.sin(angle)
                ))
        elif obstacle_type == 'hexagon':
            cx, cy = width / 2, height / 2
            radius = min(width, height) / 2
            local_vertices = []
            for i in range(6):
                angle = -math.pi / 2 + (2 * math.pi * i / 6)
                local_vertices.append(QPointF(
                    cx + radius * math.cos(angle),
                    cy + radius * math.sin(angle)
                ))
        elif obstacle_type == 'custom_polygon' and 'points' in obstacle:
            # Convert to local coordinates
            local_vertices = [QPointF(p.x(), p.y()) for p in obstacle['points']]
        else:
            # Default to rectangle
            local_vertices = [
                QPointF(0, 0),
                QPointF(width, 0),
                QPointF(width, height),
                QPointF(0, height)
            ]
        
        # Apply rotation if needed
        if rotation != 0:
            center = QPointF(width / 2, height / 2)
            rad = math.radians(rotation)
            cos_r, sin_r = math.cos(rad), math.sin(rad)
            
            rotated_vertices = []
            for v in local_vertices:
                # Translate to origin
                vx = v.x() - center.x()
                vy = v.y() - center.y()
                
                # Rotate
                rx = vx * cos_r - vy * sin_r
                ry = vx * sin_r + vy * cos_r
                
                # Translate back
                rotated_vertices.append(QPointF(
                    rx + center.x(),
                    ry + center.y()
                ))
            
            local_vertices = rotated_vertices
        
        # Translate to world position
        world_vertices = [QPointF(v.x() + x, v.y() + y) for v in local_vertices]
        
        return world_vertices
    
    def get_expanded_vertices(self, obstacle):
        """Get vertices of the expanded collision box
        
        Args:
            obstacle: Obstacle dictionary
            
        Returns:
            List of QPointF representing expanded collision box vertices, or None if no expansion
        """
        expansion_dist = obstacle.get('expansion_distance', 0)
        
        if expansion_dist <= 0:
            return None
        
        # Import here to avoid circular dependency
        from collisionBoxExpansion import ObstacleExpander
        
        expander = ObstacleExpander(expansion_distance=expansion_dist)
        method = obstacle.get('expansion_method', ObstacleExpander.METHOD_GENERALIZED)
        
        try:
            expanded_data = expander.expand_obstacle(obstacle, method=method)
            
            if not expanded_data:
                return None
            
            # Handle different expansion methods
            if method == ObstacleExpander.METHOD_GENERALIZED:
                # For generalized method with arcs, approximate the full collision box
                edges, arc_centers, radius = expanded_data
                
                # Create a polygon that approximates the collision box
                vertices = []
                
                for i, edge in enumerate(edges):
                    vertices.append(edge[0])
                    
                    center = arc_centers[(i + 1) % len(arc_centers)]
                    
                    edge_end = edge[1]
                    next_edge_start = edges[(i + 1) % len(edges)][0]
                    
                    angle1 = math.atan2(edge_end.y() - center.y(), edge_end.x() - center.x())
                    angle2 = math.atan2(next_edge_start.y() - center.y(), next_edge_start.x() - center.x())
                    
                    num_samples = 5
                    for j in range(1, num_samples):
                        t = j / num_samples
                        angle = angle1 + t * (angle2 - angle1)
                        arc_point = QPointF(
                            center.x() + radius * math.cos(angle),
                            center.y() + radius * math.sin(angle)
                        )
                        vertices.append(arc_point)
                
                return vertices
            else:
                # preserve_shape or convex - already a list of QPointF
                return expanded_data
                
        except Exception as e:
            print(f"Error getting expanded vertices: {e}")
            return None
    
    def check_overlap(self, obstacle, obstacles_list, exclude=None):
        """Check if an obstacle's collision box overlaps with any existing obstacle's collision box
        
        This enforces a minimum gap between collision boxes (gray areas).
        
        Args:
            obstacle: The obstacle to check
            obstacles_list: List of existing obstacles
            exclude: An obstacle to exclude from the check
            
        Returns:
            True if overlap detected, False otherwise
        """
        # Check against all existing obstacles
        for existing in obstacles_list:
            # Skip if this is the excluded obstacle
            if exclude and existing is exclude:
                continue
            
            # FIRST CHECK: Original shapes (blue vs blue) - always check this
            vertices1_original = self.get_obstacle_vertices(obstacle)
            vertices2_original = self.get_obstacle_vertices(existing)
            
            if self._check_polygon_overlap(vertices1_original, vertices2_original, spacing=self.min_spacing):
                return True
            
            # SECOND CHECK: Collision boxes (gray vs gray) - only if both have expansion
            expansion1 = obstacle.get('expansion_distance', 0)
            expansion2 = existing.get('expansion_distance', 0)
            
            # If both obstacles have collision boxes, enforce minimum gap
            if expansion1 > 0 and expansion2 > 0:
                vertices1_expanded = self.get_expanded_vertices(obstacle)
                vertices2_expanded = self.get_expanded_vertices(existing)
                
                if vertices1_expanded and vertices2_expanded:
                    # Check with COLLISION_BOX_MIN_GAP - this creates the invisible space between gray areas
                    if self._check_polygon_overlap(vertices1_expanded, vertices2_expanded, spacing=self.COLLISION_BOX_MIN_GAP):
                        return True
            
            # THIRD CHECK: One has collision box, other doesn't
            if expansion1 > 0:
                vertices1_expanded = self.get_expanded_vertices(obstacle)
                if vertices1_expanded and self._check_polygon_overlap(vertices1_expanded, vertices2_original, spacing=self.min_spacing):
                    return True
            
            if expansion2 > 0:
                vertices2_expanded = self.get_expanded_vertices(existing)
                if vertices2_expanded and self._check_polygon_overlap(vertices1_original, vertices2_expanded, spacing=self.min_spacing):
                    return True
        
        return False
    
    def _check_polygon_overlap(self, vertices1, vertices2, spacing=0):
        """Helper method to check if two polygons overlap with a minimum spacing
        
        Args:
            vertices1: List of QPointF for first polygon
            vertices2: List of QPointF for second polygon
            spacing: Minimum spacing to enforce between polygons (in pixels)
            
        Returns:
            True if polygons overlap or are within spacing distance, False otherwise
        """
        polygon1 = QPolygonF(vertices1)
        path1 = QPainterPath()
        path1.addPolygon(polygon1)
        
        # Apply spacing buffer to first polygon
        # This creates an invisible buffer around polygon1
        if spacing > 0:
            rect1 = polygon1.boundingRect()
            # Expand the bounding rect by spacing amount
            rect1.adjust(-spacing, -spacing, spacing, spacing)
            path1_expanded = QPainterPath()
            path1_expanded.addRect(rect1)
        else:
            path1_expanded = path1
        
        polygon2 = QPolygonF(vertices2)
        path2 = QPainterPath()
        path2.addPolygon(polygon2)
        
        # Check for intersection
        # If the expanded polygon1 intersects polygon2, they're too close
        return path1_expanded.intersects(path2) or path2.intersects(path1_expanded)
    
    def point_in_obstacle(self, pos, obstacle):
        """Check if a point is inside an obstacle using actual polygon shape"""
        vertices = self.get_obstacle_vertices(obstacle)
        polygon = QPolygonF(vertices)
        return polygon.containsPoint(pos, 1)  # 1 = Qt.OddEvenFill
    
    def get_obstacle_at_position(self, pos, obstacles_list):
        """Check if position is inside any obstacle and return it"""
        # Check in reverse order (top to bottom) so we select the topmost obstacle
        for obstacle in reversed(obstacles_list):
            if self.point_in_obstacle(pos, obstacle):
                return obstacle
        return None
    
    def segments_intersect(self, p1, p2, p3, p4):
        """Check if line segment p1-p2 intersects with line segment p3-p4"""
        def orientation(p, q, r):
            val = (q.y() - p.y()) * (r.x() - q.x()) - (q.x() - p.x()) * (r.y() - p.y())
            if val == 0:
                return 0
            return 1 if val > 0 else 2
        
        def on_segment(p, q, r):
            if (q.x() <= max(p.x(), r.x()) and q.x() >= min(p.x(), r.x()) and
                q.y() <= max(p.y(), r.y()) and q.y() >= min(p.y(), r.y())):
                return True
            return False
        
        o1 = orientation(p1, p2, p3)
        o2 = orientation(p1, p2, p4)
        o3 = orientation(p3, p4, p1)
        o4 = orientation(p3, p4, p2)
        
        if o1 != o2 and o3 != o4:
            return True
        
        if o1 == 0 and on_segment(p1, p3, p2):
            return True
        if o2 == 0 and on_segment(p1, p4, p2):
            return True
        if o3 == 0 and on_segment(p3, p1, p4):
            return True
        if o4 == 0 and on_segment(p3, p2, p4):
            return True
        
        return False
    
    def check_polygon_self_intersection(self, points):
        """Check if a polygon has self-intersecting edges"""
        if len(points) < 3:
            return False, []
        
        crossing_indices = []
        n = len(points)
        
        for i in range(n):
            for j in range(i + 2, n):
                if j == n - 1 and i == 0:
                    continue
                
                p1 = points[i]
                p2 = points[(i + 1) % n]
                p3 = points[j]
                p4 = points[(j + 1) % n]
                
                if self.segments_intersect(p1, p2, p3, p4):
                    crossing_indices.append((i, j))
        
        return len(crossing_indices) > 0, crossing_indices
    
    def check_new_edge_intersection(self, existing_points, new_point):
        """Check if adding a new point would create crossing edges"""
        if len(existing_points) < 2:
            return False
        
        last_point = existing_points[-1]
        
        for i in range(len(existing_points) - 1):
            edge_start = existing_points[i]
            edge_end = existing_points[i + 1]
            
            if self.segments_intersect(last_point, new_point, edge_start, edge_end):
                return True
        
        if len(existing_points) >= 2:
            first_point = existing_points[0]
            
            for i in range(1, len(existing_points) - 1):
                edge_start = existing_points[i]
                edge_end = existing_points[i + 1]
                
                if self.segments_intersect(new_point, first_point, edge_start, edge_end):
                    return True
        
        return False

    def expand_polygon_generalized(self, vertices):
        vertices = np.array(vertices)
        n = len(vertices)
        
        # Determine winding order - FIXED for concave polygons
        is_ccw = self._is_counter_clockwise(vertices)
        
        # DEBUG: Print winding order
        print(f"DEBUG: Polygon has {n} vertices, is_ccw={is_ccw}")
        print(f"DEBUG: First 3 vertices: {vertices[:min(3, n)]}")
        
        # ... rest of the method