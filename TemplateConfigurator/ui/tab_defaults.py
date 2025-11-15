"""
Tab 3: Global Defaults Configuration
Form-based configuration for global settings
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QComboBox, QDoubleSpinBox, QCheckBox,
    QFormLayout, QScrollArea, QSpinBox
)
from PyQt5.QtCore import Qt


class DefaultsTab(QWidget):
    """Tab for configuring global defaults"""

    def __init__(self, project, template_db):
        super().__init__()
        self.project = project
        self.template_db = template_db

        self._create_ui()
        self._load_defaults()

    def _create_ui(self):
        """Create UI layout"""
        # Use scroll area for long form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        main_layout.addWidget(scroll)

        # Container widget for scroll area
        container = QWidget()
        scroll.setWidget(container)

        layout = QVBoxLayout()
        container.setLayout(layout)

        # Title
        title = QLabel("<h2>Step 3: Global Configuration & Defaults</h2>")
        layout.addWidget(title)

        # Building Type Selection
        building_group = QGroupBox("Building Type Selection")
        building_layout = QFormLayout()
        building_group.setLayout(building_layout)
        layout.addWidget(building_group)

        self.building_type_combo = QComboBox()
        self.building_type_combo.addItems([
            "Transportation Hub",
            "Office Building",
            "Residential",
            "Retail/Shopping Mall",
            "Healthcare Facility",
            "Educational Institution",
            "Industrial/Warehouse",
            "Hospitality (Hotel)",
            "Sports/Recreation",
            "Mixed-Use"
        ])
        building_layout.addRow("Primary Type:", self.building_type_combo)

        # Sub-types (checkboxes)
        subtype_label = QLabel("Sub-Types (if Transportation Hub):")
        building_layout.addRow(subtype_label)

        self.subtype_airport = QCheckBox("Airport Terminal")
        self.subtype_bus = QCheckBox("Bus Terminal")
        self.subtype_ferry = QCheckBox("Ferry Terminal")
        self.subtype_train = QCheckBox("Train Station")
        building_layout.addRow("", self.subtype_airport)
        building_layout.addRow("", self.subtype_bus)
        building_layout.addRow("", self.subtype_ferry)
        building_layout.addRow("", self.subtype_train)

        # Ceiling Configuration
        ceiling_group = QGroupBox("Ceiling Configuration (Global Default)")
        ceiling_layout = QFormLayout()
        ceiling_group.setLayout(ceiling_layout)
        layout.addWidget(ceiling_group)

        self.ceiling_type_combo = QComboBox()
        self.ceiling_type_combo.addItems([
            "Acoustic Tile 600×600mm",
            "Acoustic Tile 1200×600mm",
            "Exposed Concrete",
            "Gypsum Board",
            "No Ceiling"
        ])
        ceiling_layout.addRow("Type:", self.ceiling_type_combo)

        self.ceiling_height_spin = QDoubleSpinBox()
        self.ceiling_height_spin.setRange(2.0, 50.0)
        self.ceiling_height_spin.setValue(18.5)
        self.ceiling_height_spin.setSuffix(" m")
        self.ceiling_height_spin.setDecimals(1)
        ceiling_layout.addRow("Default Height:", self.ceiling_height_spin)

        self.ceiling_grid_spin = QDoubleSpinBox()
        self.ceiling_grid_spin.setRange(0.3, 2.0)
        self.ceiling_grid_spin.setValue(0.6)
        self.ceiling_grid_spin.setSuffix(" m")
        self.ceiling_grid_spin.setDecimals(1)
        ceiling_layout.addRow("Grid Spacing:", self.ceiling_grid_spin)

        # MEP Standards
        mep_group = QGroupBox("MEP Standards & Inference Rules")
        mep_layout = QVBoxLayout()
        mep_group.setLayout(mep_layout)
        layout.addWidget(mep_group)

        # Fire Protection
        fp_subgroup = QGroupBox("Fire Protection")
        fp_layout = QFormLayout()
        fp_subgroup.setLayout(fp_layout)
        mep_layout.addWidget(fp_subgroup)

        self.fp_code_combo = QComboBox()
        self.fp_code_combo.addItems([
            "NFPA 13 - Light Hazard",
            "NFPA 13 - Ordinary Hazard",
            "NFPA 13 - Extra Hazard",
            "BS EN 12845",
            "Local Code"
        ])
        fp_layout.addRow("Code:", self.fp_code_combo)

        self.fp_spacing_spin = QDoubleSpinBox()
        self.fp_spacing_spin.setRange(2.0, 10.0)
        self.fp_spacing_spin.setValue(3.0)
        self.fp_spacing_spin.setSuffix(" m")
        self.fp_spacing_spin.setDecimals(1)
        fp_layout.addRow("Sprinkler Spacing:", self.fp_spacing_spin)

        self.fp_coverage_spin = QDoubleSpinBox()
        self.fp_coverage_spin.setRange(5.0, 15.0)
        self.fp_coverage_spin.setValue(7.5)
        self.fp_coverage_spin.setSuffix(" m")
        self.fp_coverage_spin.setDecimals(1)
        fp_layout.addRow("Coverage Radius:", self.fp_coverage_spin)

        self.fp_height_spin = QDoubleSpinBox()
        self.fp_height_spin.setRange(0.1, 2.0)
        self.fp_height_spin.setValue(0.3)
        self.fp_height_spin.setSuffix(" m")
        self.fp_height_spin.setDecimals(1)
        fp_layout.addRow("Height Below Ceiling:", self.fp_height_spin)

        self.fp_auto_route = QCheckBox("Auto-route pipes")
        self.fp_auto_route.setChecked(True)
        fp_layout.addRow("", self.fp_auto_route)

        # Electrical - Lighting
        elec_subgroup = QGroupBox("Electrical - Lighting")
        elec_layout = QFormLayout()
        elec_subgroup.setLayout(elec_layout)
        mep_layout.addWidget(elec_subgroup)

        self.light_illuminance_spin = QSpinBox()
        self.light_illuminance_spin.setRange(100, 1000)
        self.light_illuminance_spin.setValue(500)
        self.light_illuminance_spin.setSuffix(" lux")
        elec_layout.addRow("Target Illuminance:", self.light_illuminance_spin)

        self.light_spacing_spin = QDoubleSpinBox()
        self.light_spacing_spin.setRange(2.0, 10.0)
        self.light_spacing_spin.setValue(4.0)
        self.light_spacing_spin.setSuffix(" m")
        self.light_spacing_spin.setDecimals(1)
        elec_layout.addRow("Fixture Spacing:", self.light_spacing_spin)

        self.light_type_combo = QComboBox()
        self.light_type_combo.addItems([
            "Recessed LED 40W",
            "Recessed LED 60W",
            "Pendant LED",
            "High Bay LED",
            "Linear LED Strip"
        ])
        elec_layout.addRow("Type:", self.light_type_combo)

        # ACMV - HVAC
        hvac_subgroup = QGroupBox("ACMV - Air Distribution")
        hvac_layout = QFormLayout()
        hvac_subgroup.setLayout(hvac_layout)
        mep_layout.addWidget(hvac_subgroup)

        self.hvac_supply_spin = QDoubleSpinBox()
        self.hvac_supply_spin.setRange(3.0, 12.0)
        self.hvac_supply_spin.setValue(6.0)
        self.hvac_supply_spin.setSuffix(" m")
        self.hvac_supply_spin.setDecimals(1)
        hvac_layout.addRow("Supply Diffuser Spacing:", self.hvac_supply_spin)

        self.hvac_return_spin = QDoubleSpinBox()
        self.hvac_return_spin.setRange(4.0, 15.0)
        self.hvac_return_spin.setValue(8.0)
        self.hvac_return_spin.setSuffix(" m")
        self.hvac_return_spin.setDecimals(1)
        hvac_layout.addRow("Return Grille Spacing:", self.hvac_return_spin)

        self.hvac_ach_spin = QSpinBox()
        self.hvac_ach_spin.setRange(1, 20)
        self.hvac_ach_spin.setValue(8)
        hvac_layout.addRow("Air Changes/Hour:", self.hvac_ach_spin)

        self.hvac_auto_route = QCheckBox("Auto-route ducts per structural grid")
        self.hvac_auto_route.setChecked(True)
        hvac_layout.addRow("", self.hvac_auto_route)

        # Seating Density Standards
        seating_group = QGroupBox("Seating Density Standards")
        seating_layout = QFormLayout()
        seating_group.setLayout(seating_layout)
        layout.addWidget(seating_group)

        # Waiting Area
        seating_layout.addRow(QLabel("<b>Waiting Area:</b>"))

        self.waiting_template_combo = QComboBox()
        self.waiting_template_combo.addItems([
            "Terminal Padded Bench",
            "Metal Bench",
            "Individual Chairs",
            "Modular Seating"
        ])
        seating_layout.addRow("Template:", self.waiting_template_combo)

        self.waiting_density_spin = QDoubleSpinBox()
        self.waiting_density_spin.setRange(0.5, 5.0)
        self.waiting_density_spin.setValue(1.5)
        self.waiting_density_spin.setSuffix(" m²/seat")
        self.waiting_density_spin.setDecimals(1)
        seating_layout.addRow("Density:", self.waiting_density_spin)

        # Office
        seating_layout.addRow(QLabel("<b>Office:</b>"))

        self.office_template_combo = QComboBox()
        self.office_template_combo.addItems([
            "Office Workstation",
            "Open Plan Desk",
            "Private Office",
            "Hot Desk"
        ])
        seating_layout.addRow("Template:", self.office_template_combo)

        self.office_density_spin = QDoubleSpinBox()
        self.office_density_spin.setRange(3.0, 15.0)
        self.office_density_spin.setValue(6.0)
        self.office_density_spin.setSuffix(" m²/person")
        self.office_density_spin.setDecimals(1)
        seating_layout.addRow("Density:", self.office_density_spin)

        # Restaurant
        seating_layout.addRow(QLabel("<b>Restaurant:</b>"))

        self.restaurant_template_combo = QComboBox()
        self.restaurant_template_combo.addItems([
            "4-Seat Table",
            "2-Seat Table",
            "Bar Seating",
            "Cafeteria Style"
        ])
        seating_layout.addRow("Template:", self.restaurant_template_combo)

        self.restaurant_density_spin = QDoubleSpinBox()
        self.restaurant_density_spin.setRange(1.0, 4.0)
        self.restaurant_density_spin.setValue(2.0)
        self.restaurant_density_spin.setSuffix(" m²/seat")
        self.restaurant_density_spin.setDecimals(1)
        seating_layout.addRow("Density:", self.restaurant_density_spin)

        # Advanced Inference Options
        inference_group = QGroupBox("Advanced Inference Options")
        inference_layout = QVBoxLayout()
        inference_group.setLayout(inference_layout)
        layout.addWidget(inference_group)

        inference_layout.addWidget(QLabel("Enable Intelligent Inference:"))

        self.infer_ceiling = QCheckBox("Ceiling tiles (from room boundaries)")
        self.infer_ceiling.setChecked(True)
        inference_layout.addWidget(self.infer_ceiling)

        self.infer_floor = QCheckBox("Floor finishes (from space type)")
        self.infer_floor.setChecked(True)
        inference_layout.addWidget(self.infer_floor)

        self.infer_sprinklers = QCheckBox("Sprinklers (code-required)")
        self.infer_sprinklers.setChecked(True)
        inference_layout.addWidget(self.infer_sprinklers)

        self.infer_lighting = QCheckBox("Lighting (illuminance standards)")
        self.infer_lighting.setChecked(True)
        inference_layout.addWidget(self.infer_lighting)

        self.infer_hvac = QCheckBox("HVAC diffusers (air change rates)")
        self.infer_hvac.setChecked(True)
        inference_layout.addWidget(self.infer_hvac)

        self.infer_mep_routing = QCheckBox("MEP routing (shortest path + clearances)")
        self.infer_mep_routing.setChecked(True)
        inference_layout.addWidget(self.infer_mep_routing)

        self.infer_furniture = QCheckBox("Furniture (only if not in DWG)")
        self.infer_furniture.setChecked(False)
        inference_layout.addWidget(self.infer_furniture)

        # Confidence threshold
        threshold_layout = QFormLayout()
        inference_layout.addLayout(threshold_layout)

        self.confidence_spin = QSpinBox()
        self.confidence_spin.setRange(50, 95)
        self.confidence_spin.setValue(70)
        self.confidence_spin.setSuffix("%")
        threshold_layout.addRow("Minimum Confidence Threshold:", self.confidence_spin)

        layout.addStretch()

        # Save button at bottom
        save_layout = QHBoxLayout()
        main_layout.addLayout(save_layout)

        save_layout.addStretch()
        self.save_btn = QPushButton("Save Configuration")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.clicked.connect(self.save_defaults)
        save_layout.addWidget(self.save_btn)
        save_layout.addStretch()

    def _load_defaults(self):
        """Load current project defaults into form"""
        # Building type
        building_type = self.project.building_type
        index = self.building_type_combo.findText(building_type)
        if index >= 0:
            self.building_type_combo.setCurrentIndex(index)

        # Sub-types
        if "Airport Terminal" in self.project.sub_types:
            self.subtype_airport.setChecked(True)
        if "Bus Terminal" in self.project.sub_types:
            self.subtype_bus.setChecked(True)
        if "Ferry Terminal" in self.project.sub_types:
            self.subtype_ferry.setChecked(True)
        if "Train Station" in self.project.sub_types:
            self.subtype_train.setChecked(True)

        # Ceiling
        ceiling = self.project.global_defaults.ceiling
        self.ceiling_height_spin.setValue(ceiling.get("height", 18.5))
        if ceiling.get("grid_spacing"):
            self.ceiling_grid_spin.setValue(ceiling["grid_spacing"][0])

        # MEP standards
        mep = self.project.global_defaults.mep_standards

        # Fire protection
        fp = mep.get("fire_protection", {})
        self.fp_spacing_spin.setValue(fp.get("sprinkler_spacing", 3.0))
        self.fp_coverage_spin.setValue(fp.get("coverage_radius", 7.5))
        self.fp_height_spin.setValue(fp.get("height_below_ceiling", 0.3))
        self.fp_auto_route.setChecked(fp.get("auto_route_pipes", True))

        # Lighting
        light = mep.get("lighting", {})
        self.light_illuminance_spin.setValue(light.get("illuminance", 500))
        self.light_spacing_spin.setValue(light.get("spacing", 4.0))

        # HVAC
        hvac = mep.get("hvac", {})
        self.hvac_supply_spin.setValue(hvac.get("supply_spacing", 6.0))
        self.hvac_return_spin.setValue(hvac.get("return_spacing", 8.0))
        self.hvac_ach_spin.setValue(hvac.get("air_changes_per_hour", 8))

        # Seating density
        seating = self.project.global_defaults.seating_density

        waiting = seating.get("waiting_area", {})
        self.waiting_density_spin.setValue(waiting.get("density_m2_per_seat", 1.5))

        office = seating.get("office", {})
        self.office_density_spin.setValue(office.get("density_m2_per_person", 6.0))

        restaurant = seating.get("restaurant", {})
        self.restaurant_density_spin.setValue(restaurant.get("density_m2_per_seat", 2.0))

        # Inference rules
        enabled = self.project.inference_rules.enabled
        self.infer_ceiling.setChecked("ceiling_tiles" in enabled)
        self.infer_floor.setChecked("floor_finishes" in enabled)
        self.infer_sprinklers.setChecked("sprinklers" in enabled)
        self.infer_lighting.setChecked("lighting" in enabled)
        self.infer_hvac.setChecked("hvac_diffusers" in enabled)
        self.infer_mep_routing.setChecked("mep_routing" in enabled)
        self.infer_furniture.setChecked("furniture_auto_add" in enabled)

        threshold = self.project.inference_rules.min_confidence_threshold
        self.confidence_spin.setValue(int(threshold * 100))

    def save_defaults(self):
        """Save form data to project"""
        # Building type
        self.project.building_type = self.building_type_combo.currentText()

        # Sub-types
        sub_types = []
        if self.subtype_airport.isChecked():
            sub_types.append("Airport Terminal")
        if self.subtype_bus.isChecked():
            sub_types.append("Bus Terminal")
        if self.subtype_ferry.isChecked():
            sub_types.append("Ferry Terminal")
        if self.subtype_train.isChecked():
            sub_types.append("Train Station")
        self.project.sub_types = sub_types

        # Ceiling
        self.project.global_defaults.ceiling = {
            "type": self.ceiling_type_combo.currentText(),
            "height": self.ceiling_height_spin.value(),
            "grid_spacing": [self.ceiling_grid_spin.value(), self.ceiling_grid_spin.value()]
        }

        # MEP standards
        self.project.global_defaults.mep_standards = {
            "fire_protection": {
                "code": self.fp_code_combo.currentText(),
                "sprinkler_spacing": self.fp_spacing_spin.value(),
                "coverage_radius": self.fp_coverage_spin.value(),
                "height_below_ceiling": self.fp_height_spin.value(),
                "auto_route_pipes": self.fp_auto_route.isChecked(),
                "confidence": 0.95
            },
            "lighting": {
                "illuminance": self.light_illuminance_spin.value(),
                "spacing": self.light_spacing_spin.value(),
                "type": self.light_type_combo.currentText(),
                "height": self.ceiling_height_spin.value() - 0.5,
                "confidence": 0.90
            },
            "hvac": {
                "supply_spacing": self.hvac_supply_spin.value(),
                "return_spacing": self.hvac_return_spin.value(),
                "air_changes_per_hour": self.hvac_ach_spin.value(),
                "confidence": 0.85
            }
        }

        # Seating density
        self.project.global_defaults.seating_density = {
            "waiting_area": {
                "template": self.waiting_template_combo.currentText(),
                "density_m2_per_seat": self.waiting_density_spin.value(),
                "row_spacing": 2.0,
                "pattern": "rows_facing_center"
            },
            "office": {
                "template": self.office_template_combo.currentText(),
                "density_m2_per_person": self.office_density_spin.value()
            },
            "restaurant": {
                "template": self.restaurant_template_combo.currentText(),
                "density_m2_per_seat": self.restaurant_density_spin.value()
            }
        }

        # Inference rules
        enabled = []
        if self.infer_ceiling.isChecked():
            enabled.append("ceiling_tiles")
        if self.infer_floor.isChecked():
            enabled.append("floor_finishes")
        if self.infer_sprinklers.isChecked():
            enabled.append("sprinklers")
        if self.infer_lighting.isChecked():
            enabled.append("lighting")
        if self.infer_hvac.isChecked():
            enabled.append("hvac_diffusers")
        if self.infer_mep_routing.isChecked():
            enabled.append("mep_routing")
        if self.infer_furniture.isChecked():
            enabled.append("furniture_auto_add")

        self.project.inference_rules.enabled = enabled
        self.project.inference_rules.min_confidence_threshold = self.confidence_spin.value() / 100.0

        # Show confirmation (you could emit a signal here instead)
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Configuration Saved",
            "Global defaults have been saved to the project.\n\n"
            "You can now export the configuration JSON from File menu."
        )

    def reset(self):
        """Reset tab to initial state"""
        self._load_defaults()
