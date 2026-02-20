"""
Obstacle expansion module for robot path planning.
Expands obstacles by robot radius to reduce robot to a point.
"""
import numpy as np
import math
from PyQt5.QtCore import QPointF
from scipy.spatial import ConvexHull


class ObstacleExpander:
    """
    Implements obstacle expansion methods for collision avoidance.
    Works with any polygon (convex or non-convex).
    The robot is reduced to a point, and obstacles are expanded accordingly.
    """
    
    # Expansion method constants
    METHOD_PRESERVE_SHAPE = 'preserve_shape'
    METHOD_CONVEX = 'convex'
    METHOD_GENERALIZED = 'generalized'
    
    def __init__(self, expansion_distance=0, force_convex_hull=False):
        """
        Args:
            expansion_distance: The distance to expand obstacles (robot radius or safety margin)
                              Default is 0 (no expansion)
            force_convex_hull: If True, converts concave shapes to convex hull before expansion
                             (prevents robot from getting stuck in concave pockets)
        """
        self.d_exp = expansion_distance
        self.force_convex_hull = force_convex_hull
    
    @staticmethod
    def get_expansion_method_name(method):
        """Get human-readable name for expansion method
        
        Args:
            method: Method constant (METHOD_PRESERVE_SHAPE, METHOD_CONVEX, or METHOD_GENERALIZED)
            
        Returns:
            str: Human-readable method name
        """
        method_names = {
            ObstacleExpander.METHOD_PRESERVE_SHAPE: "Maintain Shape",
            ObstacleExpander.METHOD_CONVEX: "Convex Hull",
            ObstacleExpander.METHOD_GENERALIZED: "Generalized (Arcs)"
        }
        return method_names.get(method, "Unknown")
    
    @staticmethod
    def get_all_methods():
        """Get list of all available expansion methods
        
        Returns:
            list: List of method constants
        """
        return [
            ObstacleExpander.METHOD_GENERALIZED,
            ObstacleExpander.METHOD_PRESERVE_SHAPE,
            ObstacleExpander.METHOD_CONVEX
        ]
    
    def set_expansion_distance(self, distance):
        """Update the expansion distance
        
        Args:
            distance: New expansion distance
        """
        self.d_exp = distance
    
    def set_force_convex_hull(self, force):
        """Update the force convex hull setting
        
        Args:
            force: Boolean - True to force convex hull conversion
        """
        self.force_convex_hull = force
    
    def expand_obstacle(self, obstacle, method=None, force_convex_hull=None):
        """
        Expand an obstacle from your project's obstacle dictionary format.
        
        Args:
            obstacle: Obstacle dictionary with keys: type, x, y, width, height, rotation
            method: Optional override for expansion method. If None, uses obstacle's method
            force_convex_hull: Optional override for convex hull forcing. If None, uses class setting
        
        Returns:
            For preserve_shape/convex: List of QPointF representing expanded polygon vertices
            For generalized: Tuple of (edges, arc_centers, arc_radius)
            For directional: depends on shape and method
            Returns None if expansion_distance is 0
        """
        # Check for directional expansion (basic shapes) - UPDATED to support all shapes
        if obstacle.get('use_directional_expansion', False):
            directional_exp = obstacle.get('directional_expansion', {})
            exp_north = directional_exp.get('north', 0)
            exp_south = directional_exp.get('south', 0)
            exp_east = directional_exp.get('east', 0)
            exp_west = directional_exp.get('west', 0)
            
            # If any directional expansion is set, use directional method
            if exp_north > 0 or exp_south > 0 or exp_east > 0 or exp_west > 0:
                obstacle_type = obstacle.get('type')
                if obstacle_type == 'rectangle':
                    return self.expand_rectangle_directional(obstacle)
                elif obstacle_type in ['triangle', 'pentagon', 'hexagon']:
                    return self.expand_polygon_directional(obstacle)
        
        # Original expansion logic continues...
        # Get expansion distance from obstacle or use class default
        expansion_dist = obstacle.get('expansion_distance', self.d_exp)
        
        # If no expansion, return None
        if expansion_dist <= 0:
            return None
        
        # Temporarily set expansion distance
        old_distance = self.d_exp
        self.d_exp = expansion_dist
        
        # Determine if we should force convex hull
        use_convex_hull = force_convex_hull if force_convex_hull is not None else self.force_convex_hull
        # Also check obstacle's own setting
        if 'force_convex_hull' in obstacle:
            use_convex_hull = obstacle['force_convex_hull']
        
        # Get expansion method
        if method is None:
            method = obstacle.get('expansion_method', self.METHOD_GENERALIZED)
        
        try:
            # Convert obstacle to vertices
            vertices = self._obstacle_to_vertices(obstacle)
            
            # Apply convex hull if requested
            if use_convex_hull:
                vertices = self._compute_convex_hull(vertices)
            
            # Expand the polygon
            if method == self.METHOD_PRESERVE_SHAPE:
                expanded = self.expand_polygon_preserve_shape(vertices)
                result = [QPointF(v[0], v[1]) for v in expanded]
            elif method == self.METHOD_CONVEX:
                expanded = self.expand_polygon_convex(vertices)
                result = [QPointF(v[0], v[1]) for v in expanded]
            elif method == self.METHOD_GENERALIZED:
                edges, centers, radius = self.expand_polygon_generalized(vertices)
                # Convert to QPointF for Qt compatibility
                qt_edges = [[QPointF(e[0][0], e[0][1]), QPointF(e[1][0], e[1][1])] for e in edges]
                qt_centers = [QPointF(c[0], c[1]) for c in centers]
                result = (qt_edges, qt_centers, radius)
            else:
                raise ValueError(f"Unknown method: {method}")
        finally:
            # Restore original distance
            self.d_exp = old_distance
        
        return result
    
    def _compute_convex_hull(self, vertices):
        """
        Compute the convex hull of polygon vertices.
        Converts concave shapes to their convex hull.
        
        Args:
            vertices: numpy array of shape (n, 2) representing polygon vertices
            
        Returns:
            numpy array of convex hull vertices in counter-clockwise order
        """
        # Need at least 3 points for a hull
        if len(vertices) < 3:
            return vertices
        
        try:
            # Compute convex hull using scipy
            hull = ConvexHull(vertices)
            # Get hull vertices in order
            hull_vertices = vertices[hull.vertices]
            
            # Ensure counter-clockwise order
            hull_vertices = self._ensure_counter_clockwise(hull_vertices)
            
            return hull_vertices
        except Exception as e:
            print(f"Warning: Convex hull computation failed: {e}")
            # Return original vertices if hull computation fails
            return vertices
    
    def _obstacle_to_vertices(self, obstacle):
        """
        Convert obstacle dictionary to numpy array of vertices.
        Handles rotation and different obstacle types.
        
        Args:
            obstacle: Obstacle dictionary
            
        Returns:
            numpy array of shape (n, 2) representing polygon vertices
        """
        obstacle_type = obstacle.get('type', 'rectangle')
        x = obstacle['x']
        y = obstacle['y']
        width = obstacle['width']
        height = obstacle['height']
        rotation = obstacle.get('rotation', 0)
        
        # Generate local vertices based on shape
        if obstacle_type == 'rectangle':
            local_vertices = np.array([
                [0, 0],
                [width, 0],
                [width, height],
                [0, height]
            ])
        elif obstacle_type == 'triangle':
            local_vertices = np.array([
                [width / 2, 0],       # Top center
                [width, height],      # Bottom right
                [0, height]           # Bottom left
            ])
        elif obstacle_type == 'pentagon':
            cx, cy = width / 2, height / 2
            radius = min(width, height) / 2
            local_vertices = self._regular_polygon_vertices(cx, cy, radius, 5)
        elif obstacle_type == 'hexagon':
            cx, cy = width / 2, height / 2
            radius = min(width, height) / 2
            local_vertices = self._regular_polygon_vertices(cx, cy, radius, 6)
        elif obstacle_type == 'custom_polygon' and 'points' in obstacle:
            # Convert QPointF to numpy array (points are already in local coordinates)
            local_vertices = np.array([[p.x(), p.y()] for p in obstacle['points']])
        else:
            # Default to rectangle
            local_vertices = np.array([
                [0, 0],
                [width, 0],
                [width, height],
                [0, height]
            ])
        
        # Apply rotation if needed (skip for custom polygons as they don't rotate)
        can_rotate = obstacle.get('can_rotate', True)
        if rotation != 0 and can_rotate:
            # For custom polygons, calculate actual centroid instead of bounding box center
            if obstacle_type == 'custom_polygon':
                # Calculate centroid (geometric center) of the polygon
                center = np.mean(local_vertices, axis=0)
            else:
                # For regular shapes, use bounding box center
                center = np.array([width / 2, height / 2])
            
            rad = math.radians(rotation)
            cos_r, sin_r = math.cos(rad), math.sin(rad)
            rotation_matrix = np.array([
                [cos_r, -sin_r],
                [sin_r, cos_r]
            ])
            
            # Rotate around center
            local_vertices = (local_vertices - center) @ rotation_matrix.T + center
        
        # Translate to world position
        world_vertices = local_vertices + np.array([x, y])
        
        return world_vertices
    
    def _regular_polygon_vertices(self, cx, cy, radius, num_sides):
        """Generate vertices for a regular polygon"""
        angles = np.linspace(-np.pi/2, 2*np.pi - np.pi/2, num_sides, endpoint=False)
        vertices = np.column_stack([
            cx + radius * np.cos(angles),
            cy + radius * np.sin(angles)
        ])
        return vertices
    
    def _is_counter_clockwise(self, vertices):
        """
        Determine if polygon vertices are ordered counter-clockwise.
        Uses the shoelace formula (signed area) which works for ANY polygon
        (convex, concave, simple, complex).
        
        This is ROBUST against:
        - Rotation-induced coordinate changes
        - Polygons drawn in different directions
        - Both convex and concave shapes
        
        Args:
            vertices: numpy array of shape (n, 2) representing polygon vertices
            
        Returns:
            bool: True if counter-clockwise, False if clockwise
        """
        # Shoelace formula: sum of (x[i] * y[i+1] - x[i+1] * y[i])
        n = len(vertices)
        signed_area = 0.0
        
        for i in range(n):
            x1, y1 = vertices[i]
            x2, y2 = vertices[(i + 1) % n]
            signed_area += (x1 * y2 - x2 * y1)
        
        # If signed_area > 0: counter-clockwise
        # If signed_area < 0: clockwise
        # If signed_area == 0: degenerate (collinear points)
        return signed_area > 0
    
    def _ensure_counter_clockwise(self, vertices):
        """
        Ensure vertices are ordered counter-clockwise.
        If clockwise, reverse the order.
        
        Args:
            vertices: numpy array of shape (n, 2) representing polygon vertices
            
        Returns:
            numpy array with vertices in counter-clockwise order
        """
        if not self._is_counter_clockwise(vertices):
            return vertices[::-1]  # Reverse order
        return vertices
    
    def expand_polygon_preserve_shape(self, vertices):
        """
        Method 3: Preserve original shape by extending edges and connecting intersections.
        Works with any polygon (convex or non-convex).
        
        Args:
            vertices: numpy array of shape (n, 2) representing polygon vertices
        
        Returns: 
            vertices of expanded polygon
        """
        vertices = np.array(vertices)
        
        # ROBUST: Ensure counter-clockwise winding order
        vertices = self._ensure_counter_clockwise(vertices)
        
        n = len(vertices)
        
        # Compute outward normals and offset edges
        expanded_edges = []
        
        for i in range(n):
            v1 = vertices[i]
            v2 = vertices[(i + 1) % n]
            
            # Edge vector
            edge = v2 - v1
            # Outward normal (rotate 90 degrees clockwise for CCW polygon)
            # For CCW: rotate right (clockwise) gives outward normal
            normal = np.array([edge[1], -edge[0]])
            normal_len = np.linalg.norm(normal)
            if normal_len > 1e-10:
                normal = normal / normal_len
            else:
                normal = np.array([0, 0])
            
            # Move edge outward by expansion distance
            offset = normal * self.d_exp
            expanded_edges.append([v1 + offset, v2 + offset])
        
        # Find intersection points of adjacent expanded edges
        final_vertices = []
        for i in range(n):
            # Current edge
            p1, p2 = expanded_edges[i]
            # Next edge
            p3, p4 = expanded_edges[(i + 1) % n]
            
            # Find intersection of lines
            intersection = self._line_intersection(p1, p2, p3, p4)
            final_vertices.append(intersection)
        
        return np.array(final_vertices)
    
    def expand_polygon_convex(self, vertices):
        """
        Method 1: Create convex polygon by connecting expansion points with straight lines.
        Works with any polygon (convex or non-convex).
        May create zones narrower than expansion distance (collision risk).
        
        Args:
            vertices: numpy array of shape (n, 2) representing polygon vertices
        
        Returns: 
            vertices of expanded polygon
        """
        vertices = np.array(vertices)
        
        # ROBUST: Ensure counter-clockwise winding order
        vertices = self._ensure_counter_clockwise(vertices)
        
        n = len(vertices)
        
        # Compute expansion points at each vertex
        expanded_vertices = []
        
        for i in range(n):
            v_curr = vertices[i]
            v_prev = vertices[(i - 1) % n]
            v_next = vertices[(i + 1) % n]
            
            # Normals to adjacent edges (outward for CCW polygon)
            edge_prev = v_curr - v_prev
            edge_next = v_next - v_curr
            
            # Rotate 90 degrees right for outward normal (CCW polygon)
            normal_prev = np.array([edge_prev[1], -edge_prev[0]])
            normal_prev_len = np.linalg.norm(normal_prev)
            if normal_prev_len > 1e-10:
                normal_prev = normal_prev / normal_prev_len
            
            normal_next = np.array([edge_next[1], -edge_next[0]])
            normal_next_len = np.linalg.norm(normal_next)
            if normal_next_len > 1e-10:
                normal_next = normal_next / normal_next_len
            
            # Expansion points
            exp_point_prev = v_curr + normal_prev * self.d_exp
            exp_point_next = v_curr + normal_next * self.d_exp
            
            expanded_vertices.extend([exp_point_prev, exp_point_next])
        
        return np.array(expanded_vertices)
    
    def expand_polygon_generalized(self, vertices):
        """
        Method 2: Create generalized polygon with circular arcs at corners.
        Works with any polygon (convex or non-convex).
        This maintains uniform expansion width (safest method).
        
        Args:
            vertices: numpy array of shape (n, 2) representing polygon vertices
        
        Returns: 
            (expanded_edges, arc_centers, arc_radius) for visualization
        """
        vertices = np.array(vertices)
        
        # ROBUST: Ensure counter-clockwise winding order
        vertices = self._ensure_counter_clockwise(vertices)
        
        n = len(vertices)
        
        # Expand edges
        expanded_edges = []
        
        for i in range(n):
            v1 = vertices[i]
            v2 = vertices[(i + 1) % n]
            
            edge = v2 - v1
            # Outward normal (rotate 90 degrees right for CCW polygon)
            normal = np.array([edge[1], -edge[0]])
            normal_len = np.linalg.norm(normal)
            if normal_len > 1e-10:
                normal = normal / normal_len
            
            offset = normal * self.d_exp
            expanded_edges.append([v1 + offset, v2 + offset])
        
        # Arc centers are the original vertices
        arc_centers = vertices.copy()
        
        return expanded_edges, arc_centers, self.d_exp
    
    def _line_intersection(self, p1, p2, p3, p4):
        """Find intersection point of two lines defined by points (p1,p2) and (p3,p4)"""
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = p3
        x4, y4 = p4
        
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-10:
            return (p2 + p3) / 2  # Parallel lines, return midpoint
        
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        
        return np.array([x, y])
    
    def expand_all_obstacles(self, obstacles_list, method=None):
        """
        Expand all obstacles in the list.
        
        Args:
            obstacles_list: List of obstacle dictionaries
            method: Optional override for expansion method
            
        Returns:
            List of expanded obstacle data (format depends on method)
        """
        expanded = []
        for obstacle in obstacles_list:
            try:
                expanded_data = self.expand_obstacle(obstacle, method)
                if expanded_data is not None:  # Only add if expansion occurred
                    expanded.append({
                        'original': obstacle,
                        'expanded': expanded_data,
                        'method': method or obstacle.get('expansion_method', self.METHOD_GENERALIZED)
                    })
            except Exception as e:
                api_core.log(f"Warning: Failed to expand obstacle: {e}", "warning")
                continue
        
        return expanded
    
    def expand_rectangle_directional(self, obstacle):
        """
        Expand a rectangle with directional (N/S/E/W) expansion distances.
        Directional values OVERRIDE the base expansion for each side.
        Respects the selected expansion method.
        Only works with rectangles.
        
        Args:
            obstacle: Rectangle obstacle dictionary with directional expansion values
            
        Returns:
            For preserve_shape/convex: List of QPointF representing expanded polygon vertices
            For generalized: Tuple of (edges, arc_centers, arc_radius)
        """
        if obstacle.get('type') != 'rectangle':
            raise ValueError("Directional expansion only works with rectangles")
        
        x = obstacle['x']
        y = obstacle['y']
        width = obstacle['width']
        height = obstacle['height']
        rotation = obstacle.get('rotation', 0)
        
        # Get directional expansion distances (these are the final values, not offsets)
        directional_exp = obstacle.get('directional_expansion', {})
        exp_north = directional_exp.get('north', 0)
        exp_south = directional_exp.get('south', 0)
        exp_east = directional_exp.get('east', 0)
        exp_west = directional_exp.get('west', 0)
        
        # If all are zero, return None
        if exp_north == 0 and exp_south == 0 and exp_east == 0 and exp_west == 0:
            return None
        
        # Calculate expanded rectangle vertices (before rotation)
        # North = -Y direction (upward)
        # South = +Y direction (downward)
        # East = +X direction (rightward)
        # West = -X direction (leftward)
        
        local_vertices = np.array([
            [-exp_west, -exp_north],  # Top-left
            [width + exp_east, -exp_north],  # Top-right
            [width + exp_east, height + exp_south],  # Bottom-right
            [-exp_west, height + exp_south]  # Bottom-left
        ])
        
        # Apply rotation if needed
        if rotation != 0:
            center = np.array([width / 2, height / 2])
            rad = math.radians(rotation)
            cos_r, sin_r = math.cos(rad), math.sin(rad)
            rotation_matrix = np.array([
                [cos_r, -sin_r],
                [sin_r, cos_r]
            ])
            
            # Rotate around original center
            local_vertices = (local_vertices - center) @ rotation_matrix.T + center
        
        # Translate to world position
        world_vertices = local_vertices + np.array([x, y])
        
        # Get expansion method from obstacle
        method = obstacle.get('expansion_method', self.METHOD_GENERALIZED)
        
        # Apply expansion method to the directional rectangle
        if method == self.METHOD_GENERALIZED:
            # For generalized method, create edges and arc centers
            edges = []
            n = len(world_vertices)
            
            for i in range(n):
                v1 = world_vertices[i]
                v2 = world_vertices[(i + 1) % n]
                edges.append([QPointF(v1[0], v1[1]), QPointF(v2[0], v2[1])])
            
            # Arc centers are at the corners of the directional rectangle
            arc_centers = [QPointF(v[0], v[1]) for v in world_vertices]
            
            # Use the maximum directional expansion as the arc radius
            arc_radius = max(exp_north, exp_south, exp_east, exp_west)
            
            return (edges, arc_centers, arc_radius)
        
        elif method == self.METHOD_CONVEX:
            # For convex method, expand each vertex outward
            # This creates a "rounded" effect at corners
            expanded_vertices = []
            n = len(world_vertices)
            
            for i in range(n):
                v_curr = world_vertices[i]
                v_prev = world_vertices[(i - 1) % n]
                v_next = world_vertices[(i + 1) % n]
                
                # Normals to adjacent edges
                edge_prev = v_curr - v_prev
                edge_next = v_next - v_curr
                
                # Outward normals
                normal_prev = np.array([edge_prev[1], -edge_prev[0]])
                normal_prev_len = np.linalg.norm(normal_prev)
                if normal_prev_len > 1e-10:
                    normal_prev = normal_prev / normal_prev_len
                
                normal_next = np.array([edge_next[1], -edge_next[0]])
                normal_next_len = np.linalg.norm(normal_next)
                if normal_next_len > 1e-10:
                    normal_next = normal_next / normal_next_len
                
                # Use average directional expansion for this corner
                # Determine which corner this is based on local coordinates
                corner_expansion = (exp_north + exp_south + exp_east + exp_west) / 4
                
                # Expansion points
                exp_point_prev = v_curr + normal_prev * corner_expansion
                exp_point_next = v_curr + normal_next * corner_expansion
                
                expanded_vertices.extend([exp_point_prev, exp_point_next])
            
            # Convert to QPointF
            result = [QPointF(v[0], v[1]) for v in expanded_vertices]
            return result
        
        else:  # METHOD_PRESERVE_SHAPE
            # For preserve shape, the directional rectangle itself preserves the shape
            # Just return the vertices as-is
            result = [QPointF(v[0], v[1]) for v in world_vertices]
            return result
    
    def expand_polygon_directional(self, obstacle):
        """
        Expand a polygon (triangle, pentagon, hexagon) with directional (N/S/E/W) expansion.
        Uses quadrant-based edge assignment: edges are expanded based on which quadrants they fall in.
        Respects the selected expansion method.
        
        Args:
            obstacle: Obstacle dictionary with directional expansion values
            
        Returns:
            For preserve_shape/convex: List of QPointF representing expanded polygon vertices
            For generalized: Tuple of (edges, arc_centers, arc_radius)
        """
        obstacle_type = obstacle.get('type')
        if obstacle_type not in ['triangle', 'pentagon', 'hexagon']:
            raise ValueError(f"Quadrant-based directional expansion not supported for {obstacle_type}")
        
        # Get obstacle geometry
        x = obstacle['x']
        y = obstacle['y']
        width = obstacle['width']
        height = obstacle['height']
        rotation = obstacle.get('rotation', 0)
        
        # Get directional expansion distances
        directional_exp = obstacle.get('directional_expansion', {})
        exp_north = directional_exp.get('north', 0)
        exp_south = directional_exp.get('south', 0)
        exp_east = directional_exp.get('east', 0)
        exp_west = directional_exp.get('west', 0)
        
        # If all are zero, return None
        if exp_north == 0 and exp_south == 0 and exp_east == 0 and exp_west == 0:
            return None
        
        # Get original polygon vertices
        local_vertices = self._get_local_vertices_for_type(obstacle_type, width, height)
        
        # Calculate center point (in local coordinates)
        center = np.mean(local_vertices, axis=0)
        
        # Expand each edge based on quadrant assignment
        expanded_vertices = []
        n = len(local_vertices)
        
        for i in range(n):
            v1 = local_vertices[i]
            v2 = local_vertices[(i + 1) % n]
            
            # Calculate edge midpoint
            edge_midpoint = (v1 + v2) / 2
            
            # Determine which quadrants this edge belongs to
            is_north = edge_midpoint[1] < center[1]  # Above center (Y increases downward)
            is_south = edge_midpoint[1] > center[1]  # Below center
            is_west = edge_midpoint[0] < center[0]   # Left of center
            is_east = edge_midpoint[0] > center[0]   # Right of center
            
            # Calculate expansion for this edge based on quadrant
            # Edges can belong to multiple quadrants (e.g., top-left edge is both North and West)
            expansion_x = 0
            expansion_y = 0
            
            if is_north:
                expansion_y -= exp_north  # Expand upward (negative Y)
            if is_south:
                expansion_y += exp_south  # Expand downward (positive Y)
            if is_west:
                expansion_x -= exp_west   # Expand leftward (negative X)
            if is_east:
                expansion_x += exp_east   # Expand rightward (positive X)
            
            # Calculate edge normal (outward)
            edge = v2 - v1
            normal = np.array([edge[1], -edge[0]])  # Rotate 90 degrees right
            normal_len = np.linalg.norm(normal)
            if normal_len > 1e-10:
                normal = normal / normal_len
            
            # Project directional expansion onto edge normal
            directional_offset = np.array([expansion_x, expansion_y])
            expansion_magnitude = np.dot(directional_offset, normal)
            
            # Expand the edge
            offset = normal * expansion_magnitude
            expanded_v1 = v1 + offset
            expanded_v2 = v2 + offset
            
            expanded_vertices.append((expanded_v1, expanded_v2))
        
        # Find intersection points of adjacent expanded edges
        final_vertices = []
        for i in range(n):
            # Current edge
            p1, p2 = expanded_vertices[i]
            # Next edge
            p3, p4 = expanded_vertices[(i + 1) % n]
            
            # Find intersection of lines
            intersection = self._line_intersection(p1, p2, p3, p4)
            final_vertices.append(intersection)
        
        final_vertices = np.array(final_vertices)
        
        # Apply rotation if needed
        if rotation != 0:
            rad = math.radians(rotation)
            cos_r, sin_r = math.cos(rad), math.sin(rad)
            rotation_matrix = np.array([
                [cos_r, -sin_r],
                [sin_r, cos_r]
            ])
            
            # Rotate around original center
            final_vertices = (final_vertices - center) @ rotation_matrix.T + center
        
        # Translate to world position
        world_vertices = final_vertices + np.array([x, y])
        
        # Get expansion method from obstacle
        method = obstacle.get('expansion_method', self.METHOD_GENERALIZED)
        
        # Apply expansion method
        if method == self.METHOD_GENERALIZED:
            # For generalized method, create edges and arc centers
            edges = []
            n = len(world_vertices)
            
            for i in range(n):
                v1 = world_vertices[i]
                v2 = world_vertices[(i + 1) % n]
                edges.append([QPointF(v1[0], v1[1]), QPointF(v2[0], v2[1])])
            
            # Arc centers are at the expanded corners
            arc_centers = [QPointF(v[0], v[1]) for v in world_vertices]
            
            # Use the maximum directional expansion as the arc radius
            arc_radius = max(exp_north, exp_south, exp_east, exp_west)
            
            return (edges, arc_centers, arc_radius)
        
        elif method == self.METHOD_CONVEX:
            # For convex method, further expand each vertex outward
            expanded_final = []
            n = len(world_vertices)
            
            for i in range(n):
                v_curr = world_vertices[i]
                v_prev = world_vertices[(i - 1) % n]
                v_next = world_vertices[(i + 1) % n]
                
                # Normals to adjacent edges
                edge_prev = v_curr - v_prev
                edge_next = v_next - v_curr
                
                # Outward normals
                normal_prev = np.array([edge_prev[1], -edge_prev[0]])
                normal_prev_len = np.linalg.norm(normal_prev)
                if normal_prev_len > 1e-10:
                    normal_prev = normal_prev / normal_prev_len
                
                normal_next = np.array([edge_next[1], -edge_next[0]])
                normal_next_len = np.linalg.norm(normal_next)
                if normal_next_len > 1e-10:
                    normal_next = normal_next / normal_next_len
                
                # Use average directional expansion
                avg_expansion = (exp_north + exp_south + exp_east + exp_west) / 4
                
                # Expansion points
                exp_point_prev = v_curr + normal_prev * avg_expansion
                exp_point_next = v_curr + normal_next * avg_expansion
                
                expanded_final.extend([exp_point_prev, exp_point_next])
            
            # Convert to QPointF
            result = [QPointF(v[0], v[1]) for v in expanded_final]
            return result
        
        else:  # METHOD_PRESERVE_SHAPE
            # Return the expanded vertices as-is
            result = [QPointF(v[0], v[1]) for v in world_vertices]
            return result
    
    def _get_local_vertices_for_type(self, obstacle_type, width, height):
        """Get local vertices for a specific obstacle type"""
        if obstacle_type == 'triangle':
            return np.array([
                [width / 2, 0],       # Top center
                [width, height],      # Bottom right
                [0, height]           # Bottom left
            ])
        elif obstacle_type == 'pentagon':
            cx, cy = width / 2, height / 2
            radius = min(width, height) / 2
            return self._regular_polygon_vertices(cx, cy, radius, 5)
        elif obstacle_type == 'hexagon':
            cx, cy = width / 2, height / 2
            radius = min(width, height) / 2
            return self._regular_polygon_vertices(cx, cy, radius, 6)
        else:
            raise ValueError(f"Unknown obstacle type: {obstacle_type}")