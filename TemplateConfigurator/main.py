#!/usr/bin/env python3
"""
Template Configurator - Main Entry Point
Standalone PyQt5 application for configuring BIM templates
"""
import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("Bonsai Template Configurator")
    app.setOrganizationName("OSArch")

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
