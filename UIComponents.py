"""UI component builders for MainWindow"""
from PyQt5.QtWidgets import (QToolBar, QLabel, QPushButton, QButtonGroup,
                             QFrame, QGroupBox, QFormLayout, QLineEdit,
                             QVBoxLayout, QHBoxLayout, QSizePolicy, QWidget, QComboBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIntValidator, QDoubleValidator
from collisionBoxExpansion import ObstacleExpander


class UIComponents:
    """Builds UI components for the main window"""
    
    @staticmethod
    def create_toolbar(parent, tool_callback, finish_polygon_callback, snap_callback, clear_callback):
        """Create and configure the toolbar"""
        toolbar = QToolBar("Tools")
        toolbar.setMovable(False)
        parent.addToolBar(Qt.TopToolBarArea, toolbar)
        
        # Shapes label
        label = QLabel("  Shapes: ")
        toolbar.addWidget(label)
        
        # Button group
        shape_button_group = QButtonGroup(parent)
        shape_button_group.setExclusive(True)
        
        # Shape buttons
        shapes = [
            ("△", "triangle", "Triangle"),
            ("□", "rectangle", "Rectangle"),
            ("⬟", "pentagon", "Pentagon"),
            ("⬡", "hexagon", "Hexagon"),
            ("Custom", "custom", "Custom Polygon")
        ]
        
        for symbol, tool_name, tooltip in shapes:
            btn = QPushButton(symbol)
            btn.setCheckable(True)
            btn.setToolTip(tooltip)
            btn.setFixedSize(50, 40)
            
            # Make font larger for symbols (except Custom)
            if symbol != "Custom":
                font = QFont()
                font.setPointSize(16)
                btn.setFont(font)
            
            btn.clicked.connect(lambda checked, name=tool_name: tool_callback(name))
            shape_button_group.addButton(btn)
            toolbar.addWidget(btn)
        
        toolbar.addSeparator()
        
        # Finish Polygon button
        finish_polygon_btn = QPushButton("Finish Polygon")
        finish_polygon_btn.setEnabled(False)
        finish_polygon_btn.setToolTip("Complete custom polygon drawing (minimum 3 points)")
        finish_polygon_btn.clicked.connect(finish_polygon_callback)
        toolbar.addWidget(finish_polygon_btn)
        
        toolbar.addSeparator()
        
        # Snap to Grid button
        snap_grid_btn = QPushButton("Snap to Grid: OFF")
        snap_grid_btn.setCheckable(True)
        snap_grid_btn.setToolTip("Toggle snap to grid")
        snap_grid_btn.clicked.connect(snap_callback)
        toolbar.addWidget(snap_grid_btn)
        
        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        toolbar.addWidget(spacer)
        
        # Clear All button
        clear_btn = QPushButton("Clear All")
        clear_btn.setToolTip("Clear all obstacles")
        clear_btn.clicked.connect(clear_callback)
        toolbar.addWidget(clear_btn)
        
        return toolbar, shape_button_group, finish_polygon_btn, snap_grid_btn
    
    @staticmethod
    def create_properties_panel(property_change_callback, delete_callback, add_collision_box_callback, toggle_convex_callback, directional_expansion_callback):
        """Create the side panel for obstacle properties"""
        side_panel = QFrame()
        side_panel.setFrameShape(QFrame.StyledPanel)
        side_panel.setFixedWidth(300)
        side_panel.setStyleSheet("QFrame { background-color: #f0f0f0; }")
        
        side_layout = QVBoxLayout()
        side_layout.setContentsMargins(10, 10, 10, 10)
        side_panel.setLayout(side_layout)
        
        # Title
        title_label = QLabel("Obstacle Properties")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        side_layout.addWidget(title_label)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        side_layout.addWidget(line)
        
        # Properties group
        properties_group = QGroupBox("Selected Obstacle")
        properties_layout = QFormLayout()
        properties_group.setLayout(properties_layout)
        
        # Create input fields
        type_label = QLabel("None")
        type_label.setStyleSheet("QLabel { color: #666; }")
        properties_layout.addRow("Type:", type_label)
        
        # Position X - Editable
        pos_x_input = QLineEdit()
        pos_x_input.setPlaceholderText("N/A")
        pos_x_input.setValidator(QIntValidator())
        pos_x_input.editingFinished.connect(lambda: property_change_callback('x', pos_x_input.text()))
        properties_layout.addRow("Position X:", pos_x_input)
        
        # Position Y - Editable
        pos_y_input = QLineEdit()
        pos_y_input.setPlaceholderText("N/A")
        pos_y_input.setValidator(QIntValidator())
        pos_y_input.editingFinished.connect(lambda: property_change_callback('y', pos_y_input.text()))
        properties_layout.addRow("Position Y:", pos_y_input)
        
        # Width - Editable
        width_input = QLineEdit()
        width_input.setPlaceholderText("N/A")
        width_input.setValidator(QIntValidator(10, 9999))
        width_input.editingFinished.connect(lambda: property_change_callback('width', width_input.text()))
        properties_layout.addRow("Width:", width_input)
        
        # Height - Editable
        height_input = QLineEdit()
        height_input.setPlaceholderText("N/A")
        height_input.setValidator(QIntValidator(10, 9999))
        height_input.editingFinished.connect(lambda: property_change_callback('height', height_input.text()))
        properties_layout.addRow("Height:", height_input)
        
        # Rotation - Editable
        rotation_input = QLineEdit()
        rotation_input.setPlaceholderText("N/A")
        rotation_input.setValidator(QDoubleValidator(0.0, 360.0, 2))
        rotation_input.editingFinished.connect(lambda: property_change_callback('rotation', rotation_input.text()))
        properties_layout.addRow("Rotation (°):", rotation_input)
        
        # ===== COLLISION EXPANSION SECTION =====
        
        # Add separator before expansion section
        expansion_separator = QFrame()
        expansion_separator.setFrameShape(QFrame.HLine)
        expansion_separator.setFrameShadow(QFrame.Sunken)
        properties_layout.addRow(expansion_separator)
        
        # Expansion section label
        expansion_label = QLabel("Collision Expansion")
        expansion_label_font = QFont()
        expansion_label_font.setBold(True)
        expansion_label.setFont(expansion_label_font)
        expansion_label.setStyleSheet("QLabel { color: #444; }")
        properties_layout.addRow(expansion_label)
        
        # Expansion Distance - Editable
        expansion_distance_input = QLineEdit()
        expansion_distance_input.setPlaceholderText("0")
        expansion_distance_input.setValidator(QDoubleValidator(0.0, 500.0, 1))
        expansion_distance_input.setToolTip("Distance to expand obstacle boundary (in pixels)")
        properties_layout.addRow("Distance (px):", expansion_distance_input)
        
        # NEW: Directional Expansion (Rectangles Only)
        directional_expansion_label = QLabel("Directional (Rectangle)")
        directional_expansion_label_font = QFont()
        directional_expansion_label_font.setItalic(True)
        directional_expansion_label.setFont(directional_expansion_label_font)
        directional_expansion_label.setStyleSheet("QLabel { color: #666; font-size: 10px; }")
        properties_layout.addRow(directional_expansion_label)
        
        # Create grid layout for N/S/E/W inputs
        directional_grid = QWidget()
        directional_layout = QFormLayout()
        directional_layout.setContentsMargins(0, 0, 0, 0)
        directional_grid.setLayout(directional_layout)
        
        # North expansion with apply button
        north_container = QWidget()
        north_layout = QHBoxLayout()
        north_layout.setContentsMargins(0, 0, 0, 0)
        north_layout.setSpacing(5)
        north_container.setLayout(north_layout)
        
        expansion_north_input = QLineEdit()
        expansion_north_input.setPlaceholderText("0")
        expansion_north_input.setValidator(QDoubleValidator(0.0, 500.0, 1))
        expansion_north_input.setToolTip("Expand collision box northward (upward)")
        north_layout.addWidget(expansion_north_input)
        
        apply_north_btn = QPushButton("Apply")
        apply_north_btn.setFixedWidth(50)
        apply_north_btn.setStyleSheet("""
            QPushButton {
                background-color: #337ab7;
                color: white;
                font-size: 9px;
                padding: 3px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #286090;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        apply_north_btn.setEnabled(False)
        apply_north_btn.clicked.connect(lambda: directional_expansion_callback('north', expansion_north_input.text()))
        north_layout.addWidget(apply_north_btn)
        
        directional_layout.addRow("North (px):", north_container)
        
        # South expansion with apply button
        south_container = QWidget()
        south_layout = QHBoxLayout()
        south_layout.setContentsMargins(0, 0, 0, 0)
        south_layout.setSpacing(5)
        south_container.setLayout(south_layout)
        
        expansion_south_input = QLineEdit()
        expansion_south_input.setPlaceholderText("0")
        expansion_south_input.setValidator(QDoubleValidator(0.0, 500.0, 1))
        expansion_south_input.setToolTip("Expand collision box southward (downward)")
        south_layout.addWidget(expansion_south_input)
        
        apply_south_btn = QPushButton("Apply")
        apply_south_btn.setFixedWidth(50)
        apply_south_btn.setStyleSheet("""
            QPushButton {
                background-color: #337ab7;
                color: white;
                font-size: 9px;
                padding: 3px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #286090;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        apply_south_btn.setEnabled(False)
        apply_south_btn.clicked.connect(lambda: directional_expansion_callback('south', expansion_south_input.text()))
        south_layout.addWidget(apply_south_btn)
        
        directional_layout.addRow("South (px):", south_container)
        
        # East expansion with apply button
        east_container = QWidget()
        east_layout = QHBoxLayout()
        east_layout.setContentsMargins(0, 0, 0, 0)
        east_layout.setSpacing(5)
        east_container.setLayout(east_layout)
        
        expansion_east_input = QLineEdit()
        expansion_east_input.setPlaceholderText("0")
        expansion_east_input.setValidator(QDoubleValidator(0.0, 500.0, 1))
        expansion_east_input.setToolTip("Expand collision box eastward (rightward)")
        east_layout.addWidget(expansion_east_input)
        
        apply_east_btn = QPushButton("Apply")
        apply_east_btn.setFixedWidth(50)
        apply_east_btn.setStyleSheet("""
            QPushButton {
                background-color: #337ab7;
                color: white;
                font-size: 9px;
                padding: 3px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #286090;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        apply_east_btn.setEnabled(False)
        apply_east_btn.clicked.connect(lambda: directional_expansion_callback('east', expansion_east_input.text()))
        east_layout.addWidget(apply_east_btn)
        
        directional_layout.addRow("East (px):", east_container)
        
        # West expansion with apply button
        west_container = QWidget()
        west_layout = QHBoxLayout()
        west_layout.setContentsMargins(0, 0, 0, 0)
        west_layout.setSpacing(5)
        west_container.setLayout(west_layout)
        
        expansion_west_input = QLineEdit()
        expansion_west_input.setPlaceholderText("0")
        expansion_west_input.setValidator(QDoubleValidator(0.0, 500.0, 1))
        expansion_west_input.setToolTip("Expand collision box westward (leftward)")
        west_layout.addWidget(expansion_west_input)
        
        apply_west_btn = QPushButton("Apply")
        apply_west_btn.setFixedWidth(50)
        apply_west_btn.setStyleSheet("""
            QPushButton {
                background-color: #337ab7;
                color: white;
                font-size: 9px;
                padding: 3px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #286090;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        apply_west_btn.setEnabled(False)
        apply_west_btn.clicked.connect(lambda: directional_expansion_callback('west', expansion_west_input.text()))
        west_layout.addWidget(apply_west_btn)
        
        directional_layout.addRow("West (px):", west_container)
        
        properties_layout.addRow(directional_grid)
        
        # Expansion Method - Dropdown
        expansion_method_combo = QComboBox()
        expansion_method_combo.setToolTip("Choose expansion method:\n"
                                         "• Convex: Straight lines (risk of collision)\n"
                                         "• Generalized: Rounded corners (safe)\n"
                                         "• Maintain Shape: Extended lines (safe, larger)")
        
        # Add all expansion methods
        for method in ObstacleExpander.get_all_methods():
            method_name = ObstacleExpander.get_expansion_method_name(method)
            expansion_method_combo.addItem(method_name, method)
        
        properties_layout.addRow("Method:", expansion_method_combo)
        
        # Convex Hull Toggle Button
        convex_hull_toggle = QPushButton("Shape Mode: Concave")
        convex_hull_toggle.setCheckable(True)
        convex_hull_toggle.setStyleSheet("""
            QPushButton {
                background-color: #5bc0de;
                color: white;
                font-weight: bold;
                padding: 6px;
                border-radius: 4px;
                margin-top: 3px;
            }
            QPushButton:hover {
                background-color: #46b8da;
            }
            QPushButton:checked {
                background-color: #f0ad4e;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        convex_hull_toggle.setEnabled(False)
        convex_hull_toggle.setToolTip(
            "Toggle between Concave and Convex modes:\n\n"
            "• Concave (Default): Preserves original shape\n"
            "• Convex: Converts to convex hull (safer, prevents robot trapping)\n\n"
            "Convex mode is recommended for L-shapes, C-shapes, and other concave obstacles."
        )
        convex_hull_toggle.clicked.connect(toggle_convex_callback)
        properties_layout.addRow(convex_hull_toggle)
        
        # Add Collision Box Button
        add_collision_box_btn = QPushButton("Add Collision Box")
        add_collision_box_btn.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #4cae4c;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        add_collision_box_btn.setEnabled(False)
        add_collision_box_btn.setToolTip("Apply uniform collision box expansion (resets directional expansions)")
        add_collision_box_btn.clicked.connect(add_collision_box_callback)
        properties_layout.addRow(add_collision_box_btn)
        
        # ===== END EXPANSION SECTION =====
        
        side_layout.addWidget(properties_group)
        
        # ===== DELETE BUTTON =====
        delete_btn = QPushButton("Delete Obstacle")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        delete_btn.setEnabled(False)
        delete_btn.setToolTip("Delete the selected obstacle (Delete key)")
        delete_btn.clicked.connect(delete_callback)
        side_layout.addWidget(delete_btn)
        
        side_layout.addStretch()
        
        # Info label
        info_label = QLabel("Select an obstacle to\nview and edit properties")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("QLabel { color: #888; font-style: italic; }")
        info_label.setWordWrap(True)
        side_layout.addWidget(info_label)
        
        # Return statement - added directional apply buttons
        return (side_panel, type_label, pos_x_input, pos_y_input, width_input, 
                height_input, rotation_input, expansion_distance_input, expansion_method_combo, 
                add_collision_box_btn, delete_btn, convex_hull_toggle,
                expansion_north_input, expansion_south_input, expansion_east_input, expansion_west_input,
                directional_grid, directional_expansion_label,
                apply_north_btn, apply_south_btn, apply_east_btn, apply_west_btn)