"""
Main Window - 3-tab interface for Template Configurator
"""
from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QMenuBar, QMenu, QAction, QFileDialog, QMessageBox,
    QStatusBar
)
from PyQt5.QtCore import Qt
import json
from pathlib import Path

from models.project import Project
from database.template_db import TemplateDatabase, get_default_template_db_path
from ui.tab_smart_import import SmartImportTab
from ui.tab_spaces import SpacesTab
from ui.tab_defaults import DefaultsTab


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()

        # Initialize project data
        self.project = Project(name="Untitled Project")
        self.template_db = None

        # Load template database
        self._load_template_database()

        # Setup UI
        self.setWindowTitle("Bonsai Template Configurator")
        self.setGeometry(100, 100, 1200, 800)

        self._create_menu_bar()
        self._create_central_widget()
        self._create_status_bar()

    def _load_template_database(self):
        """Load template database"""
        try:
            db_path = get_default_template_db_path()
            self.template_db = TemplateDatabase(db_path)
            print(f"Loaded template database: {db_path}")

            # Get statistics
            stats = self.template_db.get_statistics()
            print(f"Templates: {stats['total_templates']}, Instances: {stats['total_instances']}")

        except FileNotFoundError as e:
            QMessageBox.warning(
                self,
                "Template Database Not Found",
                f"Could not find template database.\n{str(e)}\n\n"
                "Some features may not work correctly."
            )
            self.template_db = None

    def _create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        new_action = QAction("&New Project", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)

        open_action = QAction("&Open Configuration...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_configuration)
        file_menu.addAction(open_action)

        save_action = QAction("&Save Configuration...", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_configuration)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        export_action = QAction("&Export JSON...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_json)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def _create_central_widget(self):
        """Create central widget with tab interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create tabs
        self.import_tab = SmartImportTab(self)
        self.spaces_tab = SpacesTab(self.project, self.template_db)
        self.defaults_tab = DefaultsTab(self.project, self.template_db)

        # Add tabs
        self.tab_widget.addTab(self.import_tab, "1. Smart Import")
        self.tab_widget.addTab(self.spaces_tab, "2. Configure Spaces")
        self.tab_widget.addTab(self.defaults_tab, "3. Global Defaults")

        # Connect signals (smart import tab doesn't use files_loaded signal)
        self.spaces_tab.spaces_updated.connect(self.on_spaces_updated)

    def _create_status_bar(self):
        """Create status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def get_layer_mappings(self):
        """Get layer mappings from Tab 1 for use in other tabs."""
        if hasattr(self.import_tab, 'mapping_results'):
            return self.import_tab.mapping_results
        return None

    def get_dxf_path(self):
        """Get DXF path for processing."""
        if hasattr(self.import_tab, 'dxf_path'):
            return self.import_tab.dxf_path
        return None

    def new_project(self):
        """Create new project"""
        reply = QMessageBox.question(
            self,
            "New Project",
            "Create a new project? Unsaved changes will be lost.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.project = Project(name="Untitled Project")
            # Note: SmartImportTab doesn't have reset() method
            self.spaces_tab.reset()
            self.defaults_tab.reset()
            self.status_bar.showMessage("New project created")

    def open_configuration(self):
        """Open existing configuration JSON"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Configuration",
            str(Path.home()),
            "JSON Files (*.json);;All Files (*)"
        )

        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)

                # TODO: Load project data from JSON
                self.status_bar.showMessage(f"Loaded: {filename}")
                QMessageBox.information(
                    self,
                    "Success",
                    f"Configuration loaded from:\n{filename}"
                )

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to load configuration:\n{str(e)}"
                )

    def save_configuration(self):
        """Save configuration to JSON"""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Configuration",
            str(Path.home() / "template_config.json"),
            "JSON Files (*.json);;All Files (*)"
        )

        if filename:
            try:
                data = self.project.to_dict()

                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)

                self.status_bar.showMessage(f"Saved: {filename}")
                QMessageBox.information(
                    self,
                    "Success",
                    f"Configuration saved to:\n{filename}"
                )

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to save configuration:\n{str(e)}"
                )

    def export_json(self):
        """Export final JSON for conversion script"""
        # Check if project is ready
        if not self.project.spaces:
            QMessageBox.warning(
                self,
                "No Spaces Configured",
                "Please configure at least one space before exporting."
            )
            return

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Configuration JSON",
            str(Path.home() / f"{self.project.name}_config.json"),
            "JSON Files (*.json);;All Files (*)"
        )

        if filename:
            try:
                data = self.project.to_dict()

                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)

                self.status_bar.showMessage(f"Exported: {filename}")

                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Configuration exported to:\n{filename}\n\n"
                    f"Use this file with:\n"
                    f"python dxf_to_database.py --config {Path(filename).name}"
                )

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to export configuration:\n{str(e)}"
                )

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About Bonsai Template Configurator",
            "<h3>Bonsai Template Configurator</h3>"
            "<p>Version 0.1.0 (POC)</p>"
            "<p>A tool for configuring BIM generation from 2D DWG files.</p>"
            "<p>Part of the Bonsai BIM project.</p>"
            "<p><a href='https://github.com/IfcOpenShell/IfcOpenShell'>GitHub</a></p>"
        )

    def on_files_loaded(self):
        """Handle files loaded signal from import tab"""
        self.status_bar.showMessage(f"Files loaded - {len(self.project.spaces)} spaces detected")

        # Switch to spaces tab
        self.tab_widget.setCurrentIndex(1)

    def on_spaces_updated(self):
        """Handle spaces updated signal"""
        self.project.update_statistics()
        self.status_bar.showMessage(
            f"Spaces configured: {self.project.total_spaces_configured} "
            f"(Avg confidence: {self.project.average_confidence:.1%})"
        )

    def closeEvent(self, event):
        """Handle window close event"""
        reply = QMessageBox.question(
            self,
            "Quit",
            "Are you sure you want to quit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.template_db:
                self.template_db.close()
            event.accept()
        else:
            event.ignore()
