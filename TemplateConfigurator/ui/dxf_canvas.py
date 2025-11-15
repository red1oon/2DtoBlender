"""
2D DXF Canvas Widget - Lightweight 2D visualization for layer review

Displays DXF entities in 2D using QPainter for quick visual feedback
during smart mapping review.
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSlider, QHBoxLayout
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush
from pathlib import Path


class DXFCanvas(QWidget):
    """Simple 2D canvas for displaying DXF entities."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.entities = []
        self.layers_visible = {}
        self.bounds = None
        self.zoom_level = 1.0
        self.pan_offset = QPointF(0, 0)

        # Colors by discipline
        self.discipline_colors = {
            'ARC': QColor(200, 150, 100),      # Tan
            'FP': QColor(255, 50, 50),         # Red
            'STR': QColor(128, 128, 128),      # Gray
            'ACMV': QColor(50, 150, 255),      # Light Blue
            'ELEC': QColor(255, 255, 50),      # Yellow
            'SP': QColor(50, 50, 255),         # Blue
            'CW': QColor(50, 200, 200),        # Cyan
            'LPG': QColor(255, 128, 0),        # Orange
        }

        self.setMinimumSize(400, 400)
        self.setStyleSheet("background-color: #1e1e1e;")  # Dark background

    def load_dxf(self, dxf_path, layer_mappings=None):
        """Load DXF file and extract entities for display."""
        try:
            import ezdxf

            dxf_path = Path(dxf_path)
            if not dxf_path.exists():
                return False

            doc = ezdxf.readfile(str(dxf_path))
            msp = doc.modelspace()

            # Clear previous data
            self.entities = []
            self.layers_visible = {}

            # Initialize bounds
            min_x, min_y = float('inf'), float('inf')
            max_x, max_y = float('-inf'), float('-inf')

            # Extract entities
            for entity in msp:
                layer = entity.dxf.layer

                # Get discipline color
                discipline = None
                if layer_mappings and layer in layer_mappings.get('mappings', {}):
                    discipline = layer_mappings['mappings'][layer].get('discipline')

                # Set layer as visible by default
                if layer not in self.layers_visible:
                    self.layers_visible[layer] = True

                # Extract geometry
                entity_data = {
                    'type': entity.dxftype(),
                    'layer': layer,
                    'discipline': discipline,
                    'points': []
                }

                # Get points based on entity type
                if entity.dxftype() == 'LINE':
                    entity_data['points'] = [
                        (entity.dxf.start.x, entity.dxf.start.y),
                        (entity.dxf.end.x, entity.dxf.end.y)
                    ]
                elif entity.dxftype() == 'LWPOLYLINE':
                    entity_data['points'] = [(p[0], p[1]) for p in entity.get_points()]
                elif entity.dxftype() == 'CIRCLE':
                    cx, cy, r = entity.dxf.center.x, entity.dxf.center.y, entity.dxf.radius
                    entity_data['center'] = (cx, cy)
                    entity_data['radius'] = r
                    entity_data['points'] = [(cx, cy)]  # For bounds calculation
                elif entity.dxftype() == 'ARC':
                    cx, cy, r = entity.dxf.center.x, entity.dxf.center.y, entity.dxf.radius
                    entity_data['center'] = (cx, cy)
                    entity_data['radius'] = r
                    entity_data['start_angle'] = entity.dxf.start_angle
                    entity_data['end_angle'] = entity.dxf.end_angle
                    entity_data['points'] = [(cx, cy)]
                elif entity.dxftype() in ('TEXT', 'MTEXT'):
                    if hasattr(entity.dxf, 'insert'):
                        entity_data['points'] = [(entity.dxf.insert.x, entity.dxf.insert.y)]

                # Update bounds
                for x, y in entity_data['points']:
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

                # Add radius for circles/arcs
                if 'radius' in entity_data:
                    cx, cy = entity_data['center']
                    r = entity_data['radius']
                    min_x = min(min_x, cx - r)
                    min_y = min(min_y, cy - r)
                    max_x = max(max_x, cx + r)
                    max_y = max(max_y, cy + r)

                self.entities.append(entity_data)

            # Store bounds
            if min_x != float('inf'):
                self.bounds = (min_x, min_y, max_x, max_y)
                self.fit_to_view()

            self.update()
            return True

        except Exception as e:
            print(f"Error loading DXF: {e}")
            return False

    def fit_to_view(self):
        """Fit all entities to viewport."""
        if not self.bounds:
            return

        min_x, min_y, max_x, max_y = self.bounds

        # Calculate scale to fit
        width = max_x - min_x
        height = max_y - min_y

        if width == 0 or height == 0:
            return

        margin = 50  # pixels
        scale_x = (self.width() - 2 * margin) / width
        scale_y = (self.height() - 2 * margin) / height

        self.zoom_level = min(scale_x, scale_y)

        # Center view
        self.pan_offset = QPointF(
            -min_x * self.zoom_level + margin,
            -min_y * self.zoom_level + margin
        )

        self.update()

    def set_layer_visibility(self, layer, visible):
        """Set visibility for a specific layer."""
        self.layers_visible[layer] = visible
        self.update()

    def paintEvent(self, event):
        """Paint the canvas."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw background
        painter.fillRect(self.rect(), QColor(30, 30, 30))

        if not self.entities:
            # Draw "No data" message
            painter.setPen(QPen(QColor(128, 128, 128)))
            painter.drawText(self.rect(), Qt.AlignCenter, "No DXF loaded")
            return

        # Apply transformations
        painter.translate(self.pan_offset)
        painter.scale(self.zoom_level, -self.zoom_level)  # Flip Y axis

        # Draw entities
        for entity_data in self.entities:
            layer = entity_data['layer']

            # Skip if layer is hidden
            if not self.layers_visible.get(layer, True):
                continue

            # Get color
            discipline = entity_data.get('discipline')
            if discipline and discipline in self.discipline_colors:
                color = self.discipline_colors[discipline]
            else:
                color = QColor(180, 180, 180)  # Default gray

            painter.setPen(QPen(color, 0.5 / self.zoom_level))  # Scale-independent width

            # Draw based on entity type
            entity_type = entity_data['type']
            points = entity_data['points']

            if entity_type == 'LINE' and len(points) >= 2:
                p1 = QPointF(points[0][0], points[0][1])
                p2 = QPointF(points[1][0], points[1][1])
                painter.drawLine(p1, p2)

            elif entity_type == 'LWPOLYLINE' and len(points) >= 2:
                for i in range(len(points) - 1):
                    p1 = QPointF(points[i][0], points[i][1])
                    p2 = QPointF(points[i+1][0], points[i+1][1])
                    painter.drawLine(p1, p2)

            elif entity_type == 'CIRCLE':
                cx, cy = entity_data['center']
                r = entity_data['radius']
                painter.drawEllipse(QPointF(cx, cy), r, r)

            elif entity_type == 'ARC':
                cx, cy = entity_data['center']
                r = entity_data['radius']
                # Simplified arc drawing
                painter.drawEllipse(QPointF(cx, cy), r, r)

    def wheelEvent(self, event):
        """Handle zoom with mouse wheel."""
        delta = event.angleDelta().y()
        zoom_factor = 1.1 if delta > 0 else 0.9

        # Zoom relative to mouse position
        old_pos = event.pos()

        self.zoom_level *= zoom_factor

        # Adjust pan to zoom towards mouse
        self.pan_offset = QPointF(
            old_pos.x() - (old_pos.x() - self.pan_offset.x()) * zoom_factor,
            old_pos.y() - (old_pos.y() - self.pan_offset.y()) * zoom_factor
        )

        self.update()

    def mousePressEvent(self, event):
        """Start panning."""
        if event.button() == Qt.MiddleButton:
            self.last_pan_point = event.pos()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        """Handle panning."""
        if event.buttons() & Qt.MiddleButton:
            delta = event.pos() - self.last_pan_point
            self.pan_offset += delta
            self.last_pan_point = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        """End panning."""
        if event.button() == Qt.MiddleButton:
            self.setCursor(Qt.ArrowCursor)


class DXFCanvasWidget(QWidget):
    """Container widget with canvas and controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.canvas = DXFCanvas(self)
        self.init_ui()

    def init_ui(self):
        """Initialize UI with canvas and zoom controls."""
        layout = QVBoxLayout()

        # Title
        title = QLabel("2D Preview")
        title.setStyleSheet("font-weight: bold; color: #888;")
        layout.addWidget(title)

        # Canvas
        layout.addWidget(self.canvas, 1)

        # Controls
        controls_layout = QHBoxLayout()

        zoom_label = QLabel("Zoom:")
        zoom_label.setStyleSheet("color: #888;")
        controls_layout.addWidget(zoom_label)

        # Zoom slider
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10)
        self.zoom_slider.setMaximum(500)
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        controls_layout.addWidget(self.zoom_slider)

        # Fit button
        from PyQt5.QtWidgets import QPushButton
        fit_btn = QPushButton("Fit to View")
        fit_btn.clicked.connect(self.canvas.fit_to_view)
        controls_layout.addWidget(fit_btn)

        layout.addLayout(controls_layout)

        self.setLayout(layout)

    def on_zoom_changed(self, value):
        """Handle zoom slider change."""
        # Convert slider value (10-500) to zoom level (0.1-5.0)
        self.canvas.zoom_level = value / 100.0
        self.canvas.update()

    def load_dxf(self, dxf_path, layer_mappings=None):
        """Load DXF file into canvas."""
        return self.canvas.load_dxf(dxf_path, layer_mappings)
