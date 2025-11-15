"""
Tab 2: Configure Spaces
Visual space configuration interface
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QTextEdit,
    QDialog, QDialogButtonBox, QFormLayout, QComboBox,
    QDoubleSpinBox, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor


class SpaceConfigDialog(QDialog):
    """Dialog for configuring a single space"""

    def __init__(self, space, template_db, parent=None):
        super().__init__(parent)
        self.space = space
        self.template_db = template_db

        self.setWindowTitle(f"Configure: {space.name}")
        self.setMinimumWidth(500)

        self._create_ui()

    def _create_ui(self):
        """Create dialog UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Space info
        info_label = QLabel(f"<b>{self.space.name}</b><br>Area: {self.space.area_m2:.1f} m²")
        layout.addWidget(info_label)

        # Form layout
        form = QFormLayout()
        layout.addLayout(form)

        # Functional type selector
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "waiting_area",
            "restaurant",
            "office",
            "retail",
            "toilet",
            "warehouse",
            "parking",
            "corridor",
            "mechanical_room"
        ])

        # Set current value
        current_type = self.space.functional_type
        index = self.type_combo.findText(current_type)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)

        form.addRow("Functional Type:", self.type_combo)

        # Template selector
        self.template_combo = QComboBox()
        self.template_combo.addItem("(Auto-select based on type)")

        # Load templates from database
        if self.template_db:
            templates = self.template_db.get_furniture_templates()
            for t in templates:
                self.template_combo.addItem(
                    f"{t['template_name']} ({t['instance_count']} instances)",
                    t['template_id']
                )

        form.addRow("Furniture Template:", self.template_combo)

        # Confidence display
        self.confidence_label = QLabel(f"{self.space.confidence:.0%}")
        form.addRow("Confidence:", self.confidence_label)

        # Preview
        preview_group = QGroupBox("Auto-Generated Elements (Preview)")
        preview_layout = QVBoxLayout()
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(150)
        self._update_preview()
        preview_layout.addWidget(self.preview_text)

        # Connect signals
        self.type_combo.currentTextChanged.connect(self._update_preview)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _update_preview(self):
        """Update preview based on selected type"""
        func_type = self.type_combo.currentText()

        # Generate preview based on type
        preview = []
        if func_type == "waiting_area":
            seats = int(self.space.area_m2 / 1.5)
            preview.append(f"✅ Benches: ~{seats} seats")
            preview.append(f"✅ Ceiling tiles: ~{int(self.space.area_m2 / 0.36)} units (0.6×0.6m)")
            preview.append(f"✅ Lights: ~{int(self.space.area_m2 / 16)} units (4m spacing)")
            preview.append(f"✅ Sprinklers: ~{int(self.space.area_m2 / 9)} units (3m spacing)")
            self.space.confidence = 0.85

        elif func_type == "restaurant":
            seats = int(self.space.area_m2 / 2.0)
            preview.append(f"✅ Tables: ~{seats // 4} units (4-seat)")
            preview.append(f"✅ Chairs: ~{seats} units")
            preview.append(f"✅ Ceiling tiles: ~{int(self.space.area_m2 / 0.36)} units")
            preview.append(f"✅ Lights: ~{int(self.space.area_m2 / 16)} units")
            preview.append(f"✅ HVAC diffusers: ~{int(self.space.area_m2 / 36)} units (6m spacing)")
            preview.append(f"✅ Grease exhaust: 2-4 units (kitchen area)")
            self.space.confidence = 0.80

        elif func_type == "toilet":
            preview.append("✅ Sprinklers (wet area code)")
            preview.append("✅ Water supply")
            preview.append("✅ Drainage (critical)")
            preview.append("✅ Extract fans")
            preview.append("✅ Waterproof lighting")
            preview.append("✅ Ceramic floor tiles")
            self.space.confidence = 0.90

        elif func_type == "office":
            workstations = int(self.space.area_m2 / 6.0)
            preview.append(f"✅ Workstations: ~{workstations} units")
            preview.append(f"✅ Chairs: ~{workstations} units")
            preview.append(f"✅ Ceiling tiles: ~{int(self.space.area_m2 / 0.36)} units")
            preview.append(f"✅ Lights: ~{int(self.space.area_m2 / 16)} units (500 lux)")
            preview.append(f"✅ HVAC diffusers: ~{int(self.space.area_m2 / 36)} units")
            preview.append(f"✅ Power outlets: ~{workstations * 2} units")
            self.space.confidence = 0.85

        else:
            preview.append("✅ Ceiling tiles (default)")
            preview.append("✅ Lights (default spacing)")
            preview.append("✅ Sprinklers (code-required)")
            self.space.confidence = 0.70

        self.preview_text.setPlainText("\n".join(preview))
        self.confidence_label.setText(f"{self.space.confidence:.0%}")

        # Update confidence color
        if self.space.confidence >= 0.8:
            self.confidence_label.setStyleSheet("color: green; font-weight: bold;")
        elif self.space.confidence >= 0.6:
            self.confidence_label.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.confidence_label.setStyleSheet("color: red; font-weight: bold;")

    def get_configuration(self):
        """Get configured space data"""
        self.space.functional_type = self.type_combo.currentText()
        self.space.source = "user_configured"

        # Store furniture template if selected
        if self.template_combo.currentIndex() > 0:
            template_id = self.template_combo.currentData()
            self.space.furniture = {
                "template_id": template_id,
                "template_name": self.template_combo.currentText()
            }

        return self.space


class SpacesTab(QWidget):
    """Tab for configuring spaces visually"""

    # Signals
    spaces_updated = pyqtSignal()

    def __init__(self, project, template_db):
        super().__init__()
        self.project = project
        self.template_db = template_db

        self._create_ui()

    def _create_ui(self):
        """Create UI layout"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Title
        title = QLabel("<h2>Step 2: Configure Spaces</h2>")
        layout.addWidget(title)

        # Instructions
        instructions = QLabel(
            "Configure the functional purpose of each detected space.\n"
            "Green = Auto-configured | Yellow = Needs configuration | Blue = User configured"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Main content (side-by-side list and details)
        content_layout = QHBoxLayout()
        layout.addLayout(content_layout)

        # Left: Space list
        list_group = QGroupBox("Detected Spaces")
        list_layout = QVBoxLayout()
        list_group.setLayout(list_layout)
        content_layout.addWidget(list_group, 1)

        self.space_list = QListWidget()
        self.space_list.itemDoubleClicked.connect(self.configure_space_from_list)
        list_layout.addWidget(self.space_list)

        configure_btn = QPushButton("Configure Selected Space")
        configure_btn.clicked.connect(self.configure_selected_space)
        list_layout.addWidget(configure_btn)

        # Right: Details panel
        details_group = QGroupBox("Space Details")
        details_layout = QVBoxLayout()
        details_group.setLayout(details_layout)
        content_layout.addWidget(details_group, 1)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setPlaceholderText("Select a space to see details...")
        details_layout.addWidget(self.details_text)

        # Connect list selection
        self.space_list.itemSelectionChanged.connect(self.update_details)

        # Statistics
        stats_layout = QHBoxLayout()
        layout.addLayout(stats_layout)

        self.stats_label = QLabel("Total: 0 | Configured: 0 | Needs Configuration: 0")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()

        # Refresh spaces list
        self.refresh_spaces_list()

    def refresh_spaces_list(self):
        """Refresh the spaces list from project"""
        self.space_list.clear()

        for space in self.project.spaces:
            item = QListWidgetItem(f"{space.name} ({space.area_m2:.0f} m²)")
            item.setData(Qt.UserRole, space)

            # Color code based on status
            if space.source == "user_configured":
                item.setBackground(QColor(200, 220, 255))  # Blue
            elif space.confidence >= 0.7:
                item.setBackground(QColor(200, 255, 200))  # Green
            else:
                item.setBackground(QColor(255, 255, 200))  # Yellow

            self.space_list.addItem(item)

        self.update_statistics()

    def update_statistics(self):
        """Update statistics display"""
        total = len(self.project.spaces)
        configured = sum(1 for s in self.project.spaces if not s.needs_configuration())
        needs_config = total - configured

        self.stats_label.setText(
            f"Total: {total} | Configured: {configured} | Needs Configuration: {needs_config}"
        )

    def update_details(self):
        """Update details panel for selected space"""
        selected_items = self.space_list.selectedItems()
        if not selected_items:
            self.details_text.clear()
            return

        space = selected_items[0].data(Qt.UserRole)

        details = []
        details.append(f"<h3>{space.name}</h3>")
        details.append(f"<p><b>ID:</b> {space.id}</p>")
        details.append(f"<p><b>Area:</b> {space.area_m2:.1f} m²</p>")
        details.append(f"<p><b>Functional Type:</b> {space.functional_type}</p>")
        details.append(f"<p><b>Source:</b> {space.source}</p>")
        details.append(f"<p><b>Confidence:</b> {space.confidence:.0%}</p>")

        if space.furniture:
            details.append(f"<p><b>Furniture:</b> {space.furniture}</p>")

        if space.inference_chain:
            details.append("<p><b>Inference Chain:</b></p>")
            details.append("<ul>")
            for item in space.inference_chain:
                details.append(f"<li>{item}</li>")
            details.append("</ul>")

        self.details_text.setHtml("".join(details))

    def configure_selected_space(self):
        """Configure the selected space"""
        selected_items = self.space_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a space to configure.")
            return

        self.configure_space_from_list(selected_items[0])

    def configure_space_from_list(self, item):
        """Configure space from list item"""
        space = item.data(Qt.UserRole)

        dialog = SpaceConfigDialog(space, self.template_db, self)
        if dialog.exec_() == QDialog.Accepted:
            configured_space = dialog.get_configuration()

            # Update display
            self.refresh_spaces_list()
            self.update_details()

            # Notify parent
            self.spaces_updated.emit()

    def reset(self):
        """Reset tab to initial state"""
        self.space_list.clear()
        self.details_text.clear()
        self.update_statistics()
