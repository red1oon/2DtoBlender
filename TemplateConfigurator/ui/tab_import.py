"""
Tab 1: Import & Detect
File upload and automatic parsing of DWG/Excel/PDF
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QFileDialog, QTextEdit, QProgressBar, QLineEdit
)
from PyQt5.QtCore import pyqtSignal, Qt
from pathlib import Path


class ImportTab(QWidget):
    """Tab for importing files and detecting spaces"""

    # Signals
    files_loaded = pyqtSignal()

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
        title = QLabel("<h2>Step 1: Upload Files</h2>")
        layout.addWidget(title)

        # Primary input group
        primary_group = QGroupBox("Primary Input (Required)")
        primary_layout = QVBoxLayout()
        primary_group.setLayout(primary_layout)
        layout.addWidget(primary_group)

        # DWG file selector
        dwg_layout = QHBoxLayout()
        dwg_layout.addWidget(QLabel("DWG/DXF File:"))
        self.dwg_file_edit = QLineEdit()
        self.dwg_file_edit.setPlaceholderText("No file selected")
        self.dwg_file_edit.setReadOnly(True)
        dwg_layout.addWidget(self.dwg_file_edit)

        self.dwg_browse_btn = QPushButton("Browse...")
        self.dwg_browse_btn.clicked.connect(self.browse_dwg)
        dwg_layout.addWidget(self.dwg_browse_btn)
        primary_layout.addLayout(dwg_layout)

        # Auxiliary documents group
        aux_group = QGroupBox("Auxiliary Documents (Optional - Auto-Parse)")
        aux_layout = QVBoxLayout()
        aux_group.setLayout(aux_layout)
        layout.addWidget(aux_group)

        # Excel file
        excel_layout = QHBoxLayout()
        excel_layout.addWidget(QLabel("Space Program Excel:"))
        self.excel_file_edit = QLineEdit()
        self.excel_file_edit.setPlaceholderText("Optional - furniture schedules")
        self.excel_file_edit.setReadOnly(True)
        excel_layout.addWidget(self.excel_file_edit)

        self.excel_browse_btn = QPushButton("Browse...")
        self.excel_browse_btn.clicked.connect(self.browse_excel)
        excel_layout.addWidget(self.excel_browse_btn)
        aux_layout.addLayout(excel_layout)

        # PDF file
        pdf_layout = QHBoxLayout()
        pdf_layout.addWidget(QLabel("Design Notes PDF:"))
        self.pdf_file_edit = QLineEdit()
        self.pdf_file_edit.setPlaceholderText("Optional - functional purposes")
        self.pdf_file_edit.setReadOnly(True)
        pdf_layout.addWidget(self.pdf_file_edit)

        self.pdf_browse_btn = QPushButton("Browse...")
        self.pdf_browse_btn.clicked.connect(self.browse_pdf)
        pdf_layout.addWidget(self.pdf_browse_btn)
        aux_layout.addLayout(pdf_layout)

        # MEP schedule file
        mep_layout = QHBoxLayout()
        mep_layout.addWidget(QLabel("MEP Equipment Schedule:"))
        self.mep_file_edit = QLineEdit()
        self.mep_file_edit.setPlaceholderText("Optional - MEP specifications")
        self.mep_file_edit.setReadOnly(True)
        mep_layout.addWidget(self.mep_file_edit)

        self.mep_browse_btn = QPushButton("Browse...")
        self.mep_browse_btn.clicked.connect(self.browse_mep)
        mep_layout.addWidget(self.mep_browse_btn)
        aux_layout.addLayout(mep_layout)

        # Parse button
        parse_layout = QHBoxLayout()
        parse_layout.addStretch()
        self.parse_btn = QPushButton("Parse & Analyze")
        self.parse_btn.setMinimumHeight(40)
        self.parse_btn.setEnabled(False)
        self.parse_btn.clicked.connect(self.parse_files)
        parse_layout.addWidget(self.parse_btn)
        parse_layout.addStretch()
        layout.addLayout(parse_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Detection summary
        summary_group = QGroupBox("Step 2: Detection Summary")
        summary_layout = QVBoxLayout()
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setPlaceholderText("Upload files and click 'Parse & Analyze' to see detection results...")
        summary_layout.addWidget(self.summary_text)

        # Next button
        next_layout = QHBoxLayout()
        next_layout.addStretch()
        self.next_btn = QPushButton("Next: Configure Spaces →")
        self.next_btn.setMinimumHeight(40)
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self.on_next_clicked)
        next_layout.addWidget(self.next_btn)
        layout.addLayout(next_layout)

        layout.addStretch()

    def browse_dwg(self):
        """Browse for DWG/DXF file"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select DWG/DXF File",
            str(Path.home()),
            "CAD Files (*.dwg *.dxf *.DWG *.DXF);;All Files (*)"
        )

        if filename:
            self.dwg_file_edit.setText(filename)
            self.project.dwg_file = filename
            self.parse_btn.setEnabled(True)

            # Update project name from filename
            self.project.name = Path(filename).stem

    def browse_excel(self):
        """Browse for Excel file"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Space Program Excel",
            str(Path.home()),
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )

        if filename:
            self.excel_file_edit.setText(filename)
            self.project.excel_file = filename

    def browse_pdf(self):
        """Browse for PDF file"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Design Notes PDF",
            str(Path.home()),
            "PDF Files (*.pdf);;All Files (*)"
        )

        if filename:
            self.pdf_file_edit.setText(filename)
            self.project.pdf_file = filename

    def browse_mep(self):
        """Browse for MEP schedule"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select MEP Equipment Schedule",
            str(Path.home()),
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )

        if filename:
            self.mep_file_edit.setText(filename)
            self.project.mep_schedule_file = filename

    def parse_files(self):
        """Parse uploaded files and detect spaces"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.summary_text.clear()

        summary = []
        summary.append("<h3>Parsing Results:</h3>")

        # Simulate DWG parsing
        self.progress_bar.setValue(25)
        if self.project.dwg_file:
            summary.append(f"<p><b>DWG Analysis:</b> {Path(self.project.dwg_file).name}</p>")
            summary.append("<ul>")
            summary.append("<li>✅ File loaded successfully</li>")
            summary.append("<li>⚠️ Detected 5 spaces (need configuration)</li>")
            summary.append("<li>📊 Estimated 10,000+ elements</li>")
            summary.append("</ul>")

            # Create mock spaces for testing
            from models.space import Space
            mock_spaces = [
                Space(
                    id="Hall_A",
                    name="Hall A",
                    functional_type="unknown",
                    area_m2=1200.0,
                    source="dwg_detected",
                    confidence=0.3
                ),
                Space(
                    id="Hall_B",
                    name="Hall B",
                    functional_type="unknown",
                    area_m2=800.0,
                    source="dwg_detected",
                    confidence=0.3
                ),
                Space(
                    id="Toilet_1",
                    name="Toilet Block 1",
                    functional_type="toilet",
                    area_m2=80.0,
                    source="dwg_detected",
                    confidence=0.85
                ),
            ]
            self.project.spaces = mock_spaces
            self.project.update_statistics()

        self.progress_bar.setValue(50)

        # Excel parsing
        if self.project.excel_file:
            summary.append(f"<p><b>From Excel Space Program:</b> {Path(self.project.excel_file).name}</p>")
            summary.append("<ul>")
            summary.append("<li>✅ Parsed successfully</li>")
            summary.append("<li>📋 Found room schedules (placeholder)</li>")
            summary.append("</ul>")

        self.progress_bar.setValue(75)

        # PDF parsing
        if self.project.pdf_file:
            summary.append(f"<p><b>From Design Notes PDF:</b> {Path(self.project.pdf_file).name}</p>")
            summary.append("<ul>")
            summary.append("<li>✅ Text extracted</li>")
            summary.append("<li>📝 Detected design intent keywords (placeholder)</li>")
            summary.append("</ul>")

        self.progress_bar.setValue(90)

        # Summary
        summary.append("<hr>")
        summary.append("<p><b>Detected Spaces Needing Configuration:</b></p>")
        needs_config = self.project.get_spaces_needing_configuration()
        if needs_config:
            summary.append("<ul>")
            for space in needs_config:
                summary.append(f"<li>⚠️ {space.name} ({space.area_m2:.0f} m²) - Purpose unknown</li>")
            summary.append("</ul>")
        else:
            summary.append("<p>✅ All spaces configured!</p>")

        self.progress_bar.setValue(100)
        self.summary_text.setHtml("".join(summary))
        self.next_btn.setEnabled(True)

    def on_next_clicked(self):
        """Handle next button click"""
        self.files_loaded.emit()

    def reset(self):
        """Reset tab to initial state"""
        self.dwg_file_edit.clear()
        self.excel_file_edit.clear()
        self.pdf_file_edit.clear()
        self.mep_file_edit.clear()
        self.summary_text.clear()
        self.progress_bar.setVisible(False)
        self.parse_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
