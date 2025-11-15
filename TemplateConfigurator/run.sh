#!/bin/bash
# Launch script for Template Configurator

echo "=========================================="
echo "Bonsai Template Configurator"
echo "=========================================="
echo ""

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3."
    exit 1
fi

# Check if in correct directory
if [ ! -f "main.py" ]; then
    echo "Error: main.py not found. Please run this script from the TemplateConfigurator directory."
    exit 1
fi

# Check template database
TEMPLATE_DB="../Terminal1_Project/Templates/terminal_base_v1.0/template_library.db"
if [ -f "$TEMPLATE_DB" ]; then
    echo "✓ Template database found: $TEMPLATE_DB"
else
    echo "⚠ Warning: Template database not found at $TEMPLATE_DB"
    echo "  Some features may not work correctly."
fi

echo ""
echo "Launching application..."
echo ""

# Run the application
python3 main.py

echo ""
echo "Application closed."
