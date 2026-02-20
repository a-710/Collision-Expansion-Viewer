from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QStatusBar, QScrollArea, QApplication)
from PyQt5.QtCore import Qt
from Canvas import Canvas
from UIComponents import UIComponents
from collisionBoxExpansion import ObstacleExpander


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.current_tool = None
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Collision Expansion Viewer")
        
        # Get screen size and set window to 80% of screen
        screen = QApplication.desktop().screenGeometry()
        width = int(screen.width() * 0.8)
        height = int(screen.height() * 0.8)
        self.setGeometry(100, 100, width, height)
        
        # Create toolbar
        (self.toolbar, self.shape_button_group, self.finish_polygon_btn, 
         self.snap_grid_btn) = UIComponents.create_toolbar(
            self, self.select_tool, self.finish_polygon,
            self.toggle_snap_grid, self.clear_all
        )
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_h_layout = QHBoxLayout()
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(0)
        central_widget.setLayout(main_h_layout)
        
        # Create scroll area for canvas
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Create canvas
        self.canvas = Canvas()
        self.scroll_area.setWidget(self.canvas)
        main_h_layout.addWidget(self.scroll_area, stretch=1)
        
        # Create side panel with callbacks
        (self.side_panel, self.type_label, self.pos_x_input, self.pos_y_input,
         self.width_input, self.height_input, self.rotation_input,
         self.expansion_distance_input, self.expansion_method_combo, 
         self.add_collision_box_btn, self.delete_btn, self.convex_hull_toggle,
         self.expansion_north_input, self.expansion_south_input, 
         self.expansion_east_input, self.expansion_west_input,
         self.directional_grid, self.directional_expansion_label,
         self.apply_north_btn, self.apply_south_btn, 
         self.apply_east_btn, self.apply_west_btn) = UIComponents.create_properties_panel(
            self.on_property_changed,
            self.delete_selected_obstacle,
            self.add_collision_box,
            self.toggle_convex_hull,
            self.on_directional_expansion_changed
        )
        main_h_layout.addWidget(self.side_panel)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready | Canvas: 2048x2048 pixels | Use middle mouse button to pan")
    
    def on_property_changed(self, property_name, value):
        """Handle property changes from the properties panel"""
        if not self.canvas.selected_obstacle or not value:
            return
        
        # Prevent rotation changes for custom polygons
        if property_name == 'rotation' and self.canvas.selected_obstacle.get('can_rotate', True) == False:
            self.status_bar.showMessage("Custom polygons cannot be rotated", 3000)
            self.update_properties_panel(self.canvas.selected_obstacle)
            return
        
        try:
            # Store old values for potential revert
            old_x = self.canvas.selected_obstacle['x']
            old_y = self.canvas.selected_obstacle['y']
            old_width = self.canvas.selected_obstacle['width']
            old_height = self.canvas.selected_obstacle['height']
            old_rotation = self.canvas.selected_obstacle.get('rotation', 0)
            
            # Apply the change based on property type
            if property_name == 'rotation':
                new_value = float(value)
                # Normalize rotation to 0-360 range
                new_value = new_value % 360
                self.canvas.selected_obstacle['rotation'] = new_value
            else:
                new_value = int(value)
                
                if property_name == 'x':
                    self.canvas.selected_obstacle['x'] = new_value
                elif property_name == 'y':
                    self.canvas.selected_obstacle['y'] = new_value
                elif property_name == 'width':
                    if new_value >= 10:
                        self.canvas.selected_obstacle['width'] = new_value
                    else:
                        self.status_bar.showMessage("Width must be at least 10 pixels", 3000)
                        self.update_properties_panel(self.canvas.selected_obstacle)
                        return
                elif property_name == 'height':
                    if new_value >= 10:
                        self.canvas.selected_obstacle['height'] = new_value
                    else:
                        self.status_bar.showMessage("Height must be at least 10 pixels", 3000)
                        self.update_properties_panel(self.canvas.selected_obstacle)
                        return
            
            # Check for overlap after change (skip for rotation-only changes)
            if property_name != 'rotation' and self.canvas.collision_detector.check_overlap(
                self.canvas.selected_obstacle, 
                self.canvas.obstacles, 
                exclude=self.canvas.selected_obstacle
            ):
                # Revert changes
                self.canvas.selected_obstacle['x'] = old_x
                self.canvas.selected_obstacle['y'] = old_y
                self.canvas.selected_obstacle['width'] = old_width
                self.canvas.selected_obstacle['height'] = old_height
                self.canvas.selected_obstacle['rotation'] = old_rotation
                
                self.status_bar.showMessage("Cannot apply change: Would overlap with another obstacle", 3000)
                self.update_properties_panel(self.canvas.selected_obstacle)
            else:
                # Update successful
                self.canvas.update()
                self.status_bar.showMessage(f"Property {property_name} updated", 2000)
                
        except ValueError:
            self.status_bar.showMessage("Invalid value entered", 3000)
            self.update_properties_panel(self.canvas.selected_obstacle)
    
    def add_collision_box(self):
        """Add uniform collision box to the selected obstacle (initializes directional expansions)"""
        if not self.canvas.selected_obstacle:
            return
        
        try:
            # Get values from UI
            distance_text = self.expansion_distance_input.text()
            if not distance_text:
                self.status_bar.showMessage("Please enter an expansion distance", 3000)
                return
            
            distance = float(distance_text)
            if distance <= 0:
                self.status_bar.showMessage("Expansion distance must be greater than 0", 3000)
                return
            
            # Get selected method
            method = self.expansion_method_combo.currentData()
            
            # Apply uniform expansion
            self.canvas.selected_obstacle['expansion_distance'] = distance
            self.canvas.selected_obstacle['expansion_method'] = method
            self.canvas.selected_obstacle['use_directional_expansion'] = False
            
            # Initialize directional expansions with base distance (for basic shapes)
            obstacle_type = self.canvas.selected_obstacle.get('type')
            if obstacle_type in ['rectangle', 'triangle', 'pentagon', 'hexagon']:
                self.canvas.selected_obstacle['directional_expansion'] = {
                    'north': distance,
                    'south': distance,
                    'east': distance,
                    'west': distance
                }
                # Update UI fields to show the initialized values
                self.expansion_north_input.setText(str(distance))
                self.expansion_south_input.setText(str(distance))
                self.expansion_east_input.setText(str(distance))
                self.expansion_west_input.setText(str(distance))
            
            # Update canvas
            self.canvas.update()
            
            method_name = ObstacleExpander.get_expansion_method_name(method)
            
            # Show convex mode status only for custom polygons
            if self.canvas.selected_obstacle.get('type') == 'custom_polygon':
                convex_mode = self.canvas.selected_obstacle.get('force_convex_hull', False)
                mode_text = " (Convex mode)" if convex_mode else " (Concave mode)"
            else:
                mode_text = ""
            
            self.status_bar.showMessage(f"Uniform collision box added: {distance}px using {method_name}{mode_text}", 3000)
            
        except ValueError:
            self.status_bar.showMessage("Invalid expansion distance value", 3000)
    
    def on_directional_expansion_changed(self, direction, value):
        """Handle directional expansion changes for basic shapes (individual apply buttons)"""
        if not self.canvas.selected_obstacle or not value:
            return
        
        # Only apply to basic shapes that support directional expansion
        obstacle_type = self.canvas.selected_obstacle.get('type')
        if obstacle_type not in ['rectangle', 'triangle', 'pentagon', 'hexagon']:
            self.status_bar.showMessage(f"Directional expansion not supported for {obstacle_type}", 3000)
            return
        
        try:
            expansion_value = float(value)
            if expansion_value < 0:
                self.status_bar.showMessage("Expansion value must be non-negative", 3000)
                return
            
            # Initialize directional_expansion dict if it doesn't exist
            if 'directional_expansion' not in self.canvas.selected_obstacle:
                self.canvas.selected_obstacle['directional_expansion'] = {
                    'north': 0.0,
                    'south': 0.0,
                    'east': 0.0,
                    'west': 0.0
                }
            
            # Update the specific direction (OVERRIDE, not add)
            self.canvas.selected_obstacle['directional_expansion'][direction] = expansion_value
            
            # Mark that we're using directional expansion
            self.canvas.selected_obstacle['use_directional_expansion'] = True
            
            # Update canvas immediately
            self.canvas.update()
            
            self.status_bar.showMessage(f"Directional expansion ({direction}): {expansion_value}px applied", 2000)
            
        except ValueError:
            self.status_bar.showMessage("Invalid expansion value", 3000)
    
    def toggle_convex_hull(self, checked):
        """Handle convex hull toggle button (ONLY for custom polygons)"""
        if not self.canvas.selected_obstacle:
            return
        
        # IMPORTANT: Only allow toggle for custom polygons
        if self.canvas.selected_obstacle.get('type') != 'custom_polygon':
            self.status_bar.showMessage("Convex hull toggle only applies to custom polygons", 3000)
            # Reset toggle state
            self.convex_hull_toggle.setChecked(False)
            return
        
        # Update obstacle's force_convex_hull setting
        self.canvas.selected_obstacle['force_convex_hull'] = checked
        
        # Update button text
        if checked:
            self.convex_hull_toggle.setText("Shape Mode: Convex")
            self.status_bar.showMessage("Convex hull mode enabled - custom polygon will be converted to convex", 3000)
        else:
            self.convex_hull_toggle.setText("Shape Mode: Concave")
            self.status_bar.showMessage("Concave mode enabled - custom polygon shape will be preserved", 3000)
        
        # Redraw canvas to show changes
        self.canvas.update()
    
    def delete_selected_obstacle(self):
        """Delete the currently selected obstacle via button"""
        self.canvas.delete_selected_obstacle()
    
    def select_tool(self, tool_name):
        """Handle tool selection"""
        self.current_tool = tool_name
        
        # Handle custom polygon tool
        if tool_name == "custom":
            self.canvas.is_drawing_polygon = True
            self.canvas.polygon_editor.start_drawing()
            self.finish_polygon_btn.setEnabled(True)
            self.status_bar.showMessage("Custom Polygon mode - Click to add points (SNAP TO GRID: ALWAYS ON) | Press Esc to cancel")
        else:
            # Cancel polygon drawing if switching to another tool
            if self.canvas.is_drawing_polygon:
                self.canvas.cancel_polygon_drawing()
                self.finish_polygon_btn.setEnabled(False)
            
            self.status_bar.showMessage(f"Tool: {tool_name.capitalize()} selected - Click and drag to place")
    
    def finish_polygon(self):
        """Finish drawing custom polygon"""
        if not self.canvas.polygon_editor.can_finish():
            self.status_bar.showMessage("Polygon needs at least 3 points", 3000)
            return
        
        self.canvas.finish_custom_polygon()
        
        # Reset tool state
        self.current_tool = None
        self.finish_polygon_btn.setEnabled(False)
        
        # Uncheck all shape buttons
        for button in self.shape_button_group.buttons():
            button.setChecked(False)
    
    def toggle_snap_grid(self, checked):
        """Toggle snap to grid feature"""
        if checked:
            self.snap_grid_btn.setText("Snap to Grid: ON")
            self.canvas.snap_to_grid = True
        else:
            self.snap_grid_btn.setText("Snap to Grid: OFF")
            self.canvas.snap_to_grid = False
    
    def clear_all(self):
        """Clear all obstacles from canvas"""
        self.canvas.clear_all_obstacles()
    
    def update_properties_panel(self, obstacle=None):
        """Update the properties panel with selected obstacle data"""
        if obstacle is None:
            self.type_label.setText("None")
            self.pos_x_input.clear()
            self.pos_y_input.clear()
            self.width_input.clear()
            self.height_input.clear()
            self.rotation_input.clear()
            self.expansion_distance_input.clear()
            self.expansion_north_input.clear()
            self.expansion_south_input.clear()
            self.expansion_east_input.clear()
            self.expansion_west_input.clear()
            
            # Disable editing when no obstacle selected
            self.pos_x_input.setEnabled(False)
            self.pos_y_input.setEnabled(False)
            self.width_input.setEnabled(False)
            self.height_input.setEnabled(False)
            self.rotation_input.setEnabled(False)
            self.expansion_distance_input.setEnabled(False)
            self.expansion_method_combo.setEnabled(False)
            self.add_collision_box_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.convex_hull_toggle.setEnabled(False)
            self.convex_hull_toggle.setChecked(False)
            self.expansion_north_input.setEnabled(False)
            self.expansion_south_input.setEnabled(False)
            self.expansion_east_input.setEnabled(False)
            self.expansion_west_input.setEnabled(False)
            self.apply_north_btn.setEnabled(False)
            self.apply_south_btn.setEnabled(False)
            self.apply_east_btn.setEnabled(False)
            self.apply_west_btn.setEnabled(False)
            self.directional_grid.setVisible(False)
        else:
            obstacle_type = obstacle.get('type', 'Unknown')
            # Display custom polygon nicely
            if obstacle_type == 'custom_polygon':
                self.type_label.setText("Custom Polygon")
            else:
                self.type_label.setText(obstacle_type.capitalize())
            
            self.pos_x_input.setText(str(obstacle.get('x', 0)))
            self.pos_y_input.setText(str(obstacle.get('y', 0)))
            self.width_input.setText(str(obstacle.get('width', 0)))
            self.height_input.setText(str(obstacle.get('height', 0)))
            rotation_value = obstacle.get('rotation', 0)
            self.rotation_input.setText(f"{rotation_value:.2f}")
            
            # Set expansion properties
            expansion_distance = obstacle.get('expansion_distance', 0)
            self.expansion_distance_input.setText(str(expansion_distance))
            
            expansion_method = obstacle.get('expansion_method', ObstacleExpander.METHOD_GENERALIZED)
            # Find and set the correct combo box index
            for i in range(self.expansion_method_combo.count()):
                if self.expansion_method_combo.itemData(i) == expansion_method:
                    self.expansion_method_combo.setCurrentIndex(i)
                    break
            
            # Handle directional expansion (basic shapes: rectangle, triangle, pentagon, hexagon)
            supports_directional = obstacle_type in ['rectangle', 'triangle', 'pentagon', 'hexagon']
            
            if supports_directional:
                directional_exp = obstacle.get('directional_expansion', {
                    'north': 0.0, 'south': 0.0, 'east': 0.0, 'west': 0.0
                })
                self.expansion_north_input.setText(str(directional_exp.get('north', 0)))
                self.expansion_south_input.setText(str(directional_exp.get('south', 0)))
                self.expansion_east_input.setText(str(directional_exp.get('east', 0)))
                self.expansion_west_input.setText(str(directional_exp.get('west', 0)))
                self.expansion_north_input.setEnabled(True)
                self.expansion_south_input.setEnabled(True)
                self.expansion_east_input.setEnabled(True)
                self.expansion_west_input.setEnabled(True)
                self.apply_north_btn.setEnabled(True)
                self.apply_south_btn.setEnabled(True)
                self.apply_east_btn.setEnabled(True)
                self.apply_west_btn.setEnabled(True)
                self.directional_grid.setVisible(True)
                
                # Update label text based on shape type
                if obstacle_type == 'rectangle':
                    self.directional_expansion_label.setText("Directional (Rectangle)")
                elif obstacle_type == 'triangle':
                    self.directional_expansion_label.setText("Directional (Triangle)")
                elif obstacle_type == 'pentagon':
                    self.directional_expansion_label.setText("Directional (Pentagon)")
                elif obstacle_type == 'hexagon':
                    self.directional_expansion_label.setText("Directional (Hexagon)")
            else:
                self.expansion_north_input.clear()
                self.expansion_south_input.clear()
                self.expansion_east_input.clear()
                self.expansion_west_input.clear()
                self.expansion_north_input.setEnabled(False)
                self.expansion_south_input.setEnabled(False)
                self.expansion_east_input.setEnabled(False)
                self.expansion_west_input.setEnabled(False)
                self.apply_north_btn.setEnabled(False)
                self.apply_south_btn.setEnabled(False)
                self.apply_east_btn.setEnabled(False)
                self.apply_west_btn.setEnabled(False)
                self.directional_grid.setVisible(False)
            
            # IMPORTANT: Only enable convex hull toggle for custom polygons
            is_custom_polygon = (obstacle_type == 'custom_polygon')
            
            if is_custom_polygon:
                # Set convex hull toggle state
                force_convex = obstacle.get('force_convex_hull', False)
                self.convex_hull_toggle.setChecked(force_convex)
                if force_convex:
                    self.convex_hull_toggle.setText("Shape Mode: Convex")
                else:
                    self.convex_hull_toggle.setText("Shape Mode: Concave")
                self.convex_hull_toggle.setEnabled(True)
                self.convex_hull_toggle.setToolTip(
                    "Toggle between Concave and Convex modes for custom polygons:\n\n"
                    "• Concave (Default): Preserves original polygon shape\n"
                    "• Convex: Converts to convex hull (safer, prevents robot trapping)\n\n"
                    "Convex mode is recommended for L-shapes, C-shapes, and other concave custom polygons."
                )
            else:
                # Disable and hide for non-custom shapes
                self.convex_hull_toggle.setEnabled(False)
                self.convex_hull_toggle.setChecked(False)
                self.convex_hull_toggle.setText("Shape Mode: N/A")
                self.convex_hull_toggle.setToolTip("Convex hull toggle only applies to custom polygons")
            
            # Enable editing when obstacle is selected
            self.pos_x_input.setEnabled(True)
            self.pos_y_input.setEnabled(True)
            self.width_input.setEnabled(True)
            self.height_input.setEnabled(True)
            
            # Disable rotation for custom polygons
            can_rotate = obstacle.get('can_rotate', True)
            self.rotation_input.setEnabled(can_rotate)
            
            self.expansion_distance_input.setEnabled(True)
            self.expansion_method_combo.setEnabled(True)
            self.add_collision_box_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
        
    def update_status_coordinates(self, x, y):
        """Update status bar with mouse coordinates"""
        tool_text = f"Tool: {self.current_tool.capitalize()}" if self.current_tool else "No tool selected"
        self.status_bar.showMessage(f"Canvas Position: X={x}, Y={y} | {tool_text}")


class ObstacleEditor(MainWindow):
    """Obstacle editor application class"""
    pass