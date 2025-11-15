"""
Smart Import Tab - Updated with Smart Layer Mapper Integration

Replaces tab_import.py with new workflow:
1. Upload DXF file
2. Run smart layer mapper automatically
3. Show classification results
4. Allow user review of unmapped layers
"""

import sys
import json
from pathlib import Path
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QTextEdit, QProgressBar, QGroupBox, QTableWidget,
    QTableWidgetItem, QComboBox, QHeaderView, QSplitter
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Add smart mapper to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'Scripts'))

# Import 2D canvas
from ui.dxf_canvas import DXFCanvasWidget


class SmartMapperThread(QThread):
    """Background thread for running smart layer mapper."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, dxf_path):
        super().__init__()
        self.dxf_path = dxf_path

    def run(self):
        """Run smart mapping in background."""
        try:
            self.progress.emit("📊 Analyzing DXF file...")

            from smart_layer_mapper import SmartLayerMapper

            # Create mapper
            mapper = SmartLayerMapper()

            # Analyze layers
            self.progress.emit("🔍 Detecting layer patterns...")
            mapper.analyze_layers(self.dxf_path)

            # Apply smart mapping
            self.progress.emit("🎯 Applying intelligent classification...")
            mapper.map_layers()

            # Prepare results
            results = {
                'total_layers': len(mapper.layer_stats),
                'mapped_layers': len(mapper.mappings),
                'unmapped_layers': mapper.unmapped_layers,
                'mappings': mapper.mappings,
                'confidence_scores': mapper.confidence_scores,
                'layer_stats': mapper.layer_stats
            }

            self.progress.emit("✅ Smart mapping complete!")
            self.finished.emit(results)

        except Exception as e:
            self.error.emit(f"Error during smart mapping: {str(e)}")


class SmartImportTab(QWidget):
    """Tab 1: Smart Import with Auto-Classification."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dxf_path = None
        self.mapping_results = None
        self.mapper_thread = None

        self.init_ui()

    def init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout()

        # Title
        title = QLabel("📂 Step 1: Import & Smart Classification")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # Create splitter for left panel and 2D canvas
        splitter = QSplitter(Qt.Horizontal)

        # Left panel (controls and tables)
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)

        # File upload section
        upload_group = QGroupBox("Upload DXF File")
        upload_layout = QVBoxLayout()

        self.file_label = QLabel("No file selected")
        upload_layout.addWidget(self.file_label)

        btn_upload = QPushButton("📁 Browse for DXF...")
        btn_upload.clicked.connect(self.browse_dxf)
        upload_layout.addWidget(btn_upload)

        upload_group.setLayout(upload_layout)
        left_layout.addWidget(upload_group)

        # Progress section
        progress_group = QGroupBox("Smart Mapping Progress")
        progress_layout = QVBoxLayout()

        self.progress_log = QTextEdit()
        self.progress_log.setReadOnly(True)
        self.progress_log.setMaximumHeight(100)
        progress_layout.addWidget(self.progress_log)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        progress_group.setLayout(progress_layout)
        left_layout.addWidget(progress_group)

        # Results section
        results_group = QGroupBox("Classification Results")
        results_layout = QVBoxLayout()

        self.results_summary = QLabel("Upload a DXF file to begin...")
        results_layout.addWidget(self.results_summary)

        # Statistics display
        stats_layout = QHBoxLayout()

        self.stat_total = self._create_stat_widget("Total Layers", "0")
        self.stat_mapped = self._create_stat_widget("Auto-Mapped", "0")
        self.stat_unmapped = self._create_stat_widget("Need Review", "0")
        self.stat_coverage = self._create_stat_widget("Coverage", "0%")

        stats_layout.addWidget(self.stat_total)
        stats_layout.addWidget(self.stat_mapped)
        stats_layout.addWidget(self.stat_unmapped)
        stats_layout.addWidget(self.stat_coverage)

        results_layout.addLayout(stats_layout)

        results_group.setLayout(results_layout)
        left_layout.addWidget(results_group)

        # Unmapped layers review table
        review_group = QGroupBox("Review Unmapped Layers")
        review_layout = QVBoxLayout()

        self.unmapped_table = QTableWidget(0, 4)
        self.unmapped_table.setHorizontalHeaderLabels([
            "Layer Name", "Entities", "Assign to Discipline", "Action"
        ])
        self.unmapped_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        review_layout.addWidget(self.unmapped_table)

        btn_export = QPushButton("💾 Export Mappings to JSON")
        btn_export.clicked.connect(self.export_mappings)
        review_layout.addWidget(btn_export)

        review_group.setLayout(review_layout)
        left_layout.addWidget(review_group)

        # Stretch
        left_layout.addStretch()

        # Add left panel to splitter
        splitter.addWidget(left_panel)

        # Right panel (2D canvas)
        self.canvas_widget = DXFCanvasWidget(self)
        splitter.addWidget(self.canvas_widget)

        # Set initial splitter sizes (60% left, 40% right)
        splitter.setSizes([600, 400])

        # Add splitter to main layout
        layout.addWidget(splitter)

        self.setLayout(layout)

    def _create_stat_widget(self, label, value):
        """Create a statistics display widget."""
        widget = QGroupBox(label)
        layout = QVBoxLayout()

        value_label = QLabel(value)
        value_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        value_label.setAlignment(Qt.AlignCenter)
        setattr(self, f"value_{label.replace(' ', '_').replace('-', '_').lower()}", value_label)

        layout.addWidget(value_label)
        widget.setLayout(layout)

        return widget

    def browse_dxf(self):
        """Browse for DXF file and run smart mapping."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select DXF File",
            str(Path.home() / "Documents"),
            "DXF Files (*.dxf);;All Files (*)"
        )

        if file_path:
            self.dxf_path = file_path
            self.file_label.setText(f"Selected: {Path(file_path).name}")
            self.run_smart_mapping()

    def run_smart_mapping(self):
        """Run smart layer mapping in background thread."""
        if not self.dxf_path:
            return

        self.progress_log.clear()
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        # Create and start mapper thread
        self.mapper_thread = SmartMapperThread(self.dxf_path)
        self.mapper_thread.progress.connect(self.on_progress)
        self.mapper_thread.finished.connect(self.on_mapping_complete)
        self.mapper_thread.error.connect(self.on_error)
        self.mapper_thread.start()

    def on_progress(self, message):
        """Update progress log."""
        self.progress_log.append(message)

    def on_mapping_complete(self, results):
        """Handle mapping completion."""
        self.mapping_results = results
        self.progress_bar.setVisible(False)

        # Update statistics
        total = results['total_layers']
        mapped = results['mapped_layers']
        unmapped = len(results['unmapped_layers'])
        coverage = (mapped / total * 100) if total > 0 else 0

        self.value_total_layers.setText(str(total))
        self.value_auto_mapped.setText(str(mapped))
        self.value_need_review.setText(str(unmapped))
        self.value_coverage.setText(f"{coverage:.1f}%")

        # Update summary
        self.results_summary.setText(
            f"✅ Smart mapping complete! {mapped}/{total} layers auto-classified ({coverage:.1f}%)"
        )

        # Populate unmapped layers table
        self.populate_unmapped_table(results)

        # Load DXF into 2D canvas
        self.load_canvas()

    def populate_unmapped_table(self, results):
        """Populate table with unmapped layers for user review."""
        unmapped = results['unmapped_layers']
        layer_stats = results['layer_stats']

        self.unmapped_table.setRowCount(len(unmapped))

        disciplines = ['ARC', 'FP', 'ELEC', 'ACMV', 'SP', 'STR', 'CW', 'LPG']

        for i, layer_name in enumerate(unmapped):
            stats = layer_stats.get(layer_name, {})
            entity_count = stats.get('count', 0)

            # Layer name
            self.unmapped_table.setItem(i, 0, QTableWidgetItem(layer_name))

            # Entity count
            self.unmapped_table.setItem(i, 1, QTableWidgetItem(str(entity_count)))

            # Discipline dropdown
            combo = QComboBox()
            combo.addItems(['(Skip)'] + disciplines)
            self.unmapped_table.setCellWidget(i, 2, combo)

            # Apply button
            btn_apply = QPushButton("✓ Apply")
            btn_apply.clicked.connect(lambda checked, row=i: self.apply_mapping(row))
            self.unmapped_table.setCellWidget(i, 3, btn_apply)

    def apply_mapping(self, row):
        """Apply user's discipline selection for a layer."""
        layer_name = self.unmapped_table.item(row, 0).text()
        combo = self.unmapped_table.cellWidget(row, 2)
        discipline = combo.currentText()

        if discipline != '(Skip)':
            # Add to mappings
            if not self.mapping_results:
                self.mapping_results = {'mappings': {}, 'confidence_scores': {}}

            self.mapping_results['mappings'][layer_name] = discipline
            self.mapping_results['confidence_scores'][layer_name] = {
                'confidence': 1.0,
                'reason': 'User assigned',
                'entity_count': int(self.unmapped_table.item(row, 1).text())
            }

            # Update UI
            self.unmapped_table.removeRow(row)

            # Update stats
            mapped = int(self.value_auto_mapped.text()) + 1
            unmapped = int(self.value_need_review.text()) - 1
            total = int(self.value_total_layers.text())
            coverage = (mapped / total * 100) if total > 0 else 0

            self.value_auto_mapped.setText(str(mapped))
            self.value_need_review.setText(str(unmapped))
            self.value_coverage.setText(f"{coverage:.1f}%")

            self.progress_log.append(f"✓ Assigned {layer_name} → {discipline}")

    def export_mappings(self):
        """Export mappings to JSON file."""
        if not self.mapping_results:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Mappings",
            str(Path.home() / "Documents" / "layer_mappings.json"),
            "JSON Files (*.json)"
        )

        if file_path:
            # Prepare export data
            export_data = {
                'version': '1.0',
                'total_layers': self.mapping_results.get('total_layers', 0),
                'mapped_layers': len(self.mapping_results.get('mappings', {})),
                'mappings': {}
            }

            for layer, discipline in self.mapping_results['mappings'].items():
                score_info = self.mapping_results['confidence_scores'].get(layer, {})
                export_data['mappings'][layer] = {
                    'discipline': discipline,
                    'confidence': score_info.get('confidence', 1.0),
                    'reason': score_info.get('reason', 'User assigned'),
                    'entity_count': score_info.get('entity_count', 0)
                }

            # Write to file
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)

            self.progress_log.append(f"💾 Saved mappings to: {Path(file_path).name}")

    def on_error(self, error_msg):
        """Handle errors."""
        self.progress_bar.setVisible(False)
        self.progress_log.append(f"❌ Error: {error_msg}")

    def load_canvas(self):
        """Load DXF into 2D canvas with discipline colors."""
        if not self.dxf_path or not self.mapping_results:
            return

        # Prepare layer mappings for canvas
        layer_mappings = {
            'mappings': {}
        }

        for layer, discipline in self.mapping_results['mappings'].items():
            layer_mappings['mappings'][layer] = {
                'discipline': discipline
            }

        # Load into canvas
        success = self.canvas_widget.load_dxf(self.dxf_path, layer_mappings)

        if success:
            self.progress_log.append("🎨 Loaded 2D preview with discipline colors")
        else:
            self.progress_log.append("⚠️  Could not load 2D preview")

    def get_mappings_path(self):
        """Get path to exported mappings (for use in next tabs)."""
        # Could save to temp file automatically
        return None
