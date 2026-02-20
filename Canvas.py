"""Canvas widget for drawing obstacles and grid"""
from PyQt5.QtWidgets import QWidget, QScrollArea, QMessageBox
from PyQt5.QtCore import Qt, QPoint, QRect, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QCursor, QPolygonF
import math
from collisionBoxExpansion import ObstacleExpander


class Canvas(QWidget):
    """Main canvas widget for drawing obstacles and grid"""
    
    def __init__(self):
        super().__init__()
        # Fixed canvas size: 2048x2048
        self.canvas_width = 2048
        self.canvas_height = 2048
        self.setFixedSize(self.canvas_width, self.canvas_height)
        self.setMouseTracking(True)
        self.grid_size = 20
        
        # Panning variables
        self.is_panning = False
        self.last_pan_point = QPoint()
        
        # Snap to grid
        self.snap_to_grid = False
        
        # Obstacles list
        self.obstacles = []
        
        # Selection
        self.selected_obstacle = None
        
        # Moving state
        self.is_moving = False
        self.move_start_pos = None
        self.move_offset = QPoint()
        self.move_has_overlap = False
        self.original_position = None
        
        # Rotation state
        self.is_rotating = False
        self.rotation_handle_size = 10
        
        # Drawing state
        self.is_drawing = False
        self.draw_start_pos = None
        self.current_preview_shape = None
        self.preview_has_overlap = False
        
        # Polygon drawing state
        self.is_drawing_polygon = False
        
        # Default obstacle color
        self.obstacle_color = QColor(100, 150, 200)
        
        # Obstacle expander (initialized with 0 expansion distance by default)
        self.expander = ObstacleExpander(expansion_distance=0)
        
        # Import collision detector
        from CollisionDetector import CollisionDetector
        from PolygonEditor import PolygonEditor
        
        self.collision_detector = CollisionDetector()
        self.polygon_editor = PolygonEditor(grid_size=self.grid_size)  # Pass grid size
        
    def paintEvent(self, event):
        """Draw the canvas with grid"""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(255, 255, 255))
        self.draw_grid(painter)
        self.draw_obstacles(painter)
        
        if self.is_drawing and self.current_preview_shape:
            self.draw_preview_shape(painter)
        
        # Draw polygon preview
        if self.is_drawing_polygon:
            self.polygon_editor.draw_preview(painter)
        
    def draw_grid(self, painter):
        """Draw the grid lines"""
        pen = QPen(QColor(200, 200, 200), 1)
        painter.setPen(pen)
        
        for x in range(0, self.canvas_width + 1, self.grid_size):
            painter.drawLine(x, 0, x, self.canvas_height)
            
        for y in range(0, self.canvas_height + 1, self.grid_size):
            painter.drawLine(0, y, self.canvas_width, y)
    
    def draw_obstacles(self, painter):
        """Draw all obstacles on the canvas"""
        for obstacle in self.obstacles:
            is_selected = (obstacle == self.selected_obstacle)
            
            has_overlap = is_selected and self.is_moving and self.move_has_overlap
            
            # Draw expanded obstacle first (if expansion is set)
            expansion_dist = obstacle.get('expansion_distance', 0)
            use_directional = obstacle.get('use_directional_expansion', False)
            
            # Draw expansion if either uniform or directional expansion is set
            if expansion_dist > 0 or use_directional:
                self.draw_expanded_obstacle(painter, obstacle)
            
            # Draw original obstacle
            self.draw_single_obstacle(painter, obstacle, preview=False, selected=is_selected, has_overlap=has_overlap)
            
            # Draw rotation handle if selected AND obstacle can rotate
            if is_selected and not obstacle.get('can_rotate', True) == False:
                self.draw_rotation_handle(painter, obstacle)
    
    def draw_expanded_obstacle(self, painter, obstacle):
        """Draw the expanded version of an obstacle (collision box)"""
        try:
            expanded_data = self.expander.expand_obstacle(obstacle)
            
            if not expanded_data:
                return
            
            # Save painter state
            painter.save()
            
            # Check if using directional expansion
            use_directional = obstacle.get('use_directional_expansion', False)
            method = obstacle.get('expansion_method', ObstacleExpander.METHOD_GENERALIZED)
            obstacle_type = obstacle.get('type')
            
            if use_directional and obstacle_type in ['rectangle', 'triangle', 'pentagon', 'hexagon']:
                # Directional expansion - check method to see what was returned
                if method == ObstacleExpander.METHOD_GENERALIZED:
                    # Generalized method returns (edges, arc_centers, arc_radius)
                    edges, arc_centers, radius = expanded_data
                    
                    # Draw edges
                    pen = QPen(QColor(128, 128, 128), 2, Qt.DashLine)
                    painter.setPen(pen)
                    painter.setBrush(Qt.NoBrush)
                    
                    for edge in edges:
                        painter.drawLine(edge[0], edge[1])
                    
                    # Draw arcs at corners
                    for center in arc_centers:
                        painter.drawEllipse(center, radius, radius)
                else:
                    # Preserve shape or convex - returns list of vertices
                    pen = QPen(QColor(128, 128, 128), 2, Qt.DashLine)
                    brush = QBrush(QColor(128, 128, 128, 40))
                    
                    painter.setPen(pen)
                    painter.setBrush(brush)
                    
                    polygon = QPolygonF(expanded_data)
                    painter.drawPolygon(polygon)
            else:
                # Non-directional expansion - draw based on method
                if method == ObstacleExpander.METHOD_GENERALIZED:
                    # Draw edges and arcs
                    edges, arc_centers, radius = expanded_data
                    
                    # Draw edges
                    pen = QPen(QColor(128, 128, 128), 2, Qt.DashLine)
                    painter.setPen(pen)
                    painter.setBrush(Qt.NoBrush)
                    
                    for edge in edges:
                        painter.drawLine(edge[0], edge[1])
                    
                    # Draw arcs at corners
                    for center in arc_centers:
                        painter.drawEllipse(center, radius, radius)
                    
                else:
                    # preserve_shape or convex - draw polygon
                    pen = QPen(QColor(128, 128, 128), 2, Qt.DashLine)
                    brush = QBrush(QColor(128, 128, 128, 40))
                    
                    painter.setPen(pen)
                    painter.setBrush(brush)
                    
                    polygon = QPolygonF(expanded_data)
                    painter.drawPolygon(polygon)
            
            # Restore painter state
            painter.restore()
            
        except Exception as e:
            print(f"Error drawing expanded obstacle: {e}")
    
    def draw_single_obstacle(self, painter, obstacle, preview=False, selected=False, has_overlap=False):
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
        can_rotate = obstacle.get('can_rotate', True)
        if rotation != 0 and can_rotate:
            center_x = x + width / 2
            center_y = y + height / 2
            painter.translate(center_x, center_y)
            painter.rotate(rotation)
            painter.translate(-center_x, -center_y)
        
        # Set up painter based on state
        if has_overlap:
            pen = QPen(QColor(255, 0, 0), 4)
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
            points = self.calculate_regular_polygon_points(cx, cy, radius, 5)
            painter.drawPolygon(QPolygonF(points))
        elif shape_type == 'hexagon':
            cx = x + width // 2
            cy = y + height // 2
            radius = min(width, height) // 2
            points = self.calculate_regular_polygon_points(cx, cy, radius, 6)
            painter.drawPolygon(QPolygonF(points))
        elif shape_type == 'custom_polygon' and 'points' in obstacle:
            # Draw custom polygon (NO ROTATION)
            points = [QPointF(p.x() + x, p.y() + y) for p in obstacle['points']]
            painter.drawPolygon(QPolygonF(points))
        
        painter.restore()
    
    def draw_preview_shape(self, painter):
        """Draw preview of shape being drawn"""
        if not self.current_preview_shape:
            return
        
        main_window = self.get_main_window()
        if not main_window:
            return
        
        temp_obstacle = {
            'type': main_window.current_tool,
            'x': self.current_preview_shape.x(),
            'y': self.current_preview_shape.y(),
            'width': self.current_preview_shape.width(),
            'height': self.current_preview_shape.height(),
            'rotation': 0,
            'color': self.obstacle_color
        }
        
        self.draw_single_obstacle(painter, temp_obstacle, preview=True, selected=False, has_overlap=self.preview_has_overlap)
    
    def draw_rotation_handle(self, painter, obstacle):
        """Draw rotation handle for selected obstacle (NOT for custom polygons)"""
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
    
    def calculate_regular_polygon_points(self, cx, cy, radius, num_sides):
        """Calculate points for a regular polygon"""
        points = []
        angle_step = 2 * math.pi / num_sides
        start_angle = -math.pi / 2
        
        for i in range(num_sides):
            angle = start_angle + i * angle_step
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            points.append(QPoint(int(x), int(y)))
        
        return points
    
    def check_preview_overlap(self):
        """Check if the current preview shape overlaps with existing obstacles"""
        if not self.current_preview_shape:
            return False
        
        main_window = self.get_main_window()
        if not main_window:
            return False
        
        temp_obstacle = {
            'type': main_window.current_tool,
            'x': self.current_preview_shape.x(),
            'y': self.current_preview_shape.y(),
            'width': self.current_preview_shape.width(),
            'height': self.current_preview_shape.height(),
            'rotation': 0,
            'color': self.obstacle_color
        }
        
        return self.collision_detector.check_overlap(temp_obstacle, self.obstacles)
    
    def check_move_overlap(self):
        """Check if the selected obstacle overlaps with others at its current position"""
        if not self.selected_obstacle:
            return False
        
        return self.collision_detector.check_overlap(
            self.selected_obstacle, 
            self.obstacles, 
            exclude=self.selected_obstacle
        )
    
    def create_obstacle(self, shape_type, start_pos, end_pos):
        """Create an obstacle and add it to the list"""
        bounds = self.calculate_shape_bounds(start_pos, end_pos)
        
        if bounds.width() < 10 or bounds.height() < 10:
            return
        
        obstacle = {
            'type': shape_type,
            'x': bounds.x(),
            'y': bounds.y(),
            'width': bounds.width(),
            'height': bounds.height(),
            'rotation': 0,
            'color': self.obstacle_color,
            'expansion_distance': 0,
            'expansion_method': ObstacleExpander.METHOD_GENERALIZED,
            'force_convex_hull': False  # NEW - default to concave (preserve shape)
        }
        
        if self.collision_detector.check_overlap(obstacle, self.obstacles):
            main_window = self.get_main_window()
            if main_window:
                main_window.status_bar.showMessage("Cannot create obstacle: Overlaps with existing obstacle", 3000)
            return
        
        self.obstacles.append(obstacle)
        self.update()
    
    def delete_selected_obstacle(self):
        """Delete the currently selected obstacle with confirmation"""
        if not self.selected_obstacle:
            return
        
        reply = QMessageBox.question(
            self,
            'Delete Obstacle',
            'Are you sure you want to delete the selected obstacle?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.obstacles.remove(self.selected_obstacle)
            self.selected_obstacle = None
            
            main_window = self.get_main_window()
            if main_window:
                main_window.update_properties_panel(None)
            
            self.update()
    
    def get_main_window(self):
        """Get reference to main window"""
        from mainWindow import MainWindow
        widget = self.parent()
        while widget:
            if isinstance(widget, MainWindow):
                return widget
            widget = widget.parent()
        return None
    
    def snap_position(self, pos):
        """Snap position to grid if enabled"""
        if self.snap_to_grid:
            x = round(pos.x() / self.grid_size) * self.grid_size
            y = round(pos.y() / self.grid_size) * self.grid_size
            return QPoint(x, y)
        return pos
    
    def calculate_shape_bounds(self, start_pos, end_pos):
        """Calculate bounding box for shape"""
        x1, y1 = start_pos.x(), start_pos.y()
        x2, y2 = end_pos.x(), end_pos.y()
        
        x = min(x1, x2)
        y = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        
        return QRect(x, y, width, height)
    
    def clear_all_obstacles(self):
        """Clear all obstacles with confirmation"""
        if not self.obstacles:
            return
        
        reply = QMessageBox.question(
            self,
            'Clear All Obstacles',
            f'Are you sure you want to delete all {len(self.obstacles)} obstacle(s)?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.obstacles.clear()
            self.selected_obstacle = None
            
            main_window = self.get_main_window()
            if main_window:
                main_window.update_properties_panel(None)
            
            self.update()
    
    def cancel_polygon_drawing(self):
        """Cancel polygon drawing"""
        self.polygon_editor.cancel_drawing()
        self.is_drawing_polygon = False
        self.update()
    
    def finish_custom_polygon(self):
        """Finish custom polygon drawing"""
        obstacle = self.polygon_editor.create_obstacle(self.obstacle_color)
        if obstacle:
            # Add expansion properties
            obstacle['expansion_distance'] = 0
            obstacle['expansion_method'] = ObstacleExpander.METHOD_GENERALIZED
            obstacle['force_convex_hull'] = False  # NEW - default to concave (ONLY for custom polygons)
            
            # Check for overlaps before adding
            if self.collision_detector.check_overlap(obstacle, self.obstacles):
                main_window = self.get_main_window()
                if main_window:
                    main_window.status_bar.showMessage("Cannot create polygon: Overlaps with existing obstacle", 3000)
                return
            
            self.obstacles.append(obstacle)
            self.polygon_editor.cancel_drawing()
            self.is_drawing_polygon = False
            
            main_window = self.get_main_window()
            if main_window:
                main_window.status_bar.showMessage(f"Custom polygon created with {self.polygon_editor.get_point_count()} points", 3000)
            
            self.update()
        else:
            main_window = self.get_main_window()
            if main_window:
                main_window.status_bar.showMessage("Polygon needs at least 3 points", 3000)
    
    def get_obstacle_at_position(self, pos):
        """Check if position is inside any obstacle and return it"""
        return self.collision_detector.get_obstacle_at_position(pos, self.obstacles)
    
    def point_in_obstacle(self, pos, obstacle):
        """Check if a point is inside an obstacle's bounding box"""
        return self.collision_detector.point_in_obstacle(pos, obstacle)
    
    def get_rotation_handle_position(self, obstacle):
        """Get the position of the rotation handle for an obstacle"""
        x = obstacle['x'] + obstacle['width']
        y = obstacle['y']
        return QPoint(int(x), int(y))
    
    def is_point_on_rotation_handle(self, pos, obstacle):
        """Check if a point is on the rotation handle (NOT for custom polygons)"""
        # Custom polygons cannot be rotated
        if obstacle.get('can_rotate', True) == False:
            return False
            
        handle_pos = self.get_rotation_handle_position(obstacle)
        distance = math.sqrt((pos.x() - handle_pos.x())**2 + (pos.y() - handle_pos.y())**2)
        return distance <= self.rotation_handle_size
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Delete:
            if self.selected_obstacle:
                self.delete_selected_obstacle()
        elif event.key() == Qt.Key_Escape:
            if self.is_drawing_polygon:
                self.cancel_polygon_drawing()
                main_window = self.get_main_window()
                if main_window:
                    main_window.current_tool = None
                    main_window.finish_polygon_btn.setEnabled(False)
                    for button in main_window.shape_button_group.buttons():
                        button.setChecked(False)
                    main_window.status_bar.showMessage("Polygon drawing cancelled", 2000)
    
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        if event.button() == Qt.MiddleButton:
            self.is_panning = True
            self.last_pan_point = event.pos()
            self.setCursor(QCursor(Qt.ClosedHandCursor))
        elif event.button() == Qt.LeftButton:
            # Handle polygon drawing mode (ALWAYS snaps to grid)
            if self.is_drawing_polygon:
                # Points are automatically snapped in PolygonEditor
                pos = QPointF(event.pos())
                self.polygon_editor.add_point(pos)
                
                main_window = self.get_main_window()
                if main_window:
                    point_count = self.polygon_editor.get_point_count()
                    can_finish = self.polygon_editor.can_finish()
                    status = f"Polygon: {point_count} point(s) (snap to grid: ALWAYS ON)"
                    if can_finish:
                        status += " - Click Finish Polygon button or press Escape to cancel"
                    else:
                        status += f" - Need {3 - point_count} more point(s)"
                    main_window.status_bar.showMessage(status)
                
                self.update()
                return
            # Check for rotation handle 
            if self.selected_obstacle and self.is_point_on_rotation_handle(event.pos(), self.selected_obstacle):
                self.is_rotating = True
                self.setCursor(QCursor(Qt.CrossCursor))
                return
            clicked_obstacle = self.get_obstacle_at_position(event.pos())
            
            if clicked_obstacle:
                self.selected_obstacle = clicked_obstacle
                self.is_moving = True
                self.move_start_pos = event.pos()
                self.move_offset = QPoint(
                    event.pos().x() - clicked_obstacle['x'],
                    event.pos().y() - clicked_obstacle['y']
                )
                self.original_position = {
                    'x': clicked_obstacle['x'],
                    'y': clicked_obstacle['y']
                }
                self.move_has_overlap = False
                self.setCursor(QCursor(Qt.SizeAllCursor))
                
                main_window = self.get_main_window()
                if main_window:
                    main_window.update_properties_panel(clicked_obstacle)
                self.update()
            else:
                if self.selected_obstacle and not self.is_drawing:
                    self.selected_obstacle = None
                    main_window = self.get_main_window()
                    if main_window:
                        main_window.update_properties_panel(None)
                    self.update()
                
                main_window = self.get_main_window()
                if main_window and main_window.current_tool and main_window.current_tool != "custom":
                    self.is_drawing = True
                    pos = event.pos()
                    self.draw_start_pos = self.snap_position(pos) if self.snap_to_grid else pos
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        if event.button() == Qt.MiddleButton:
            self.is_panning = False
            self.setCursor(QCursor(Qt.ArrowCursor))
        elif event.button() == Qt.LeftButton:
            if self.is_rotating:
                self.is_rotating = False
                self.setCursor(QCursor(Qt.ArrowCursor))
                
                main_window = self.get_main_window()
                if main_window and self.selected_obstacle:
                    main_window.update_properties_panel(self.selected_obstacle)
            
            elif self.is_moving:
                if self.move_has_overlap and self.original_position:
                    self.selected_obstacle['x'] = self.original_position['x']
                    self.selected_obstacle['y'] = self.original_position['y']
                    
                    main_window = self.get_main_window()
                    if main_window:
                        main_window.status_bar.showMessage("Cannot move obstacle: Would overlap with another obstacle", 3000)
                
                self.is_moving = False
                self.move_start_pos = None
                self.move_has_overlap = False
                self.original_position = None
                self.setCursor(QCursor(Qt.ArrowCursor))
                
                main_window = self.get_main_window()
                if main_window and self.selected_obstacle:
                    main_window.update_properties_panel(self.selected_obstacle)
            
            elif self.is_drawing:
                self.is_drawing = False
                pos = event.pos()
                end_pos = self.snap_position(pos) if self.snap_to_grid else pos
                
                main_window = self.get_main_window()
                if main_window and self.draw_start_pos:
                    self.create_obstacle(main_window.current_tool, self.draw_start_pos, end_pos)
                
                self.current_preview_shape = None
                self.draw_start_pos = None
                self.preview_has_overlap = False
                self.update()
    
    def mouseMoveEvent(self, event):
        """Track mouse position and handle panning"""
        pos = event.pos()
        
        # Update polygon preview (points are automatically snapped)
        if self.is_drawing_polygon:
            preview_pos = QPointF(pos)
            self.polygon_editor.set_preview_point(preview_pos)
            self.update()
        
        if self.selected_obstacle and not self.is_moving and not self.is_rotating and not self.is_drawing:
            if self.is_point_on_rotation_handle(pos, self.selected_obstacle):
                self.setCursor(QCursor(Qt.CrossCursor))
            else:
                self.setCursor(QCursor(Qt.ArrowCursor))
        
        main_window = self.get_main_window()
        if main_window:
            main_window.update_status_coordinates(pos.x(), pos.y())
        
        if self.is_panning:
            delta = event.pos() - self.last_pan_point
            self.last_pan_point = event.pos()
            
            scroll_area = self.parent().parent()
            if isinstance(scroll_area, QScrollArea):
                h_bar = scroll_area.horizontalScrollBar()
                v_bar = scroll_area.verticalScrollBar()
                
                h_bar.setValue(h_bar.value() - delta.x())
                v_bar.setValue(v_bar.value() - delta.y())
        
        elif self.is_rotating and self.selected_obstacle:
            # Skip rotation for custom polygons
            if self.selected_obstacle.get('can_rotate', True) == False:
                return
                


            center_x = self.selected_obstacle['x'] + self.selected_obstacle['width'] / 2
            center_y = self.selected_obstacle['y'] + self.selected_obstacle['height'] / 2
            
            dx = pos.x() - center_x
            dy = pos.y() - center_y
            angle = math.degrees(math.atan2(dy, dx))
            
            self.selected_obstacle['rotation'] = angle % 360
            
            self.update()
        
        elif self.is_moving and self.selected_obstacle:
            new_x = pos.x() - self.move_offset.x()
            new_y = pos.y() - self.move_offset.y()
            
            if self.snap_to_grid:
                new_x = round(new_x / self.grid_size) * self.grid_size
                new_y = round(new_y / self.grid_size) * self.grid_size
            
            self.selected_obstacle['x'] = new_x
            self.selected_obstacle['y'] = new_y
            
            self.move_has_overlap = self.check_move_overlap()
            
            self.update()
        
        elif self.is_drawing and self.draw_start_pos:
            end_pos = self.snap_position(pos) if self.snap_to_grid else pos
            self.current_preview_shape = self.calculate_shape_bounds(self.draw_start_pos, end_pos)
            
            self.preview_has_overlap = self.check_preview_overlap()
            
            self.update()