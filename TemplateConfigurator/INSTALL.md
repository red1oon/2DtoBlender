# Installation Instructions

## Prerequisites

- Python 3.7+ (you have 3.12.3 ✓)
- pip (Python package manager)

## Installation Steps

### Option 1: System-wide Installation (Recommended for testing)

```bash
cd /home/red1/Documents/bonsai/RawDWG/TemplateConfigurator

# Install all dependencies
pip install PyQt5 ezdxf openpyxl PyPDF2 matplotlib pytest

# Or install from requirements file
pip install -r requirements.txt
```

### Option 2: Virtual Environment (Recommended for development)

```bash
cd /home/red1/Documents/bonsai/RawDWG/TemplateConfigurator

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run application
python3 main.py

# When done, deactivate
deactivate
```

## Running the Application

### Method 1: Direct Python execution
```bash
cd /home/red1/Documents/bonsai/RawDWG/TemplateConfigurator
python3 main.py
```

### Method 2: Using launch script
```bash
cd /home/red1/Documents/bonsai/RawDWG/TemplateConfigurator
./run.sh
```

### Method 3: From anywhere (if installed in venv)
```bash
cd /home/red1/Documents/bonsai/RawDWG/TemplateConfigurator
source venv/bin/activate
python3 main.py
```

## Troubleshooting

### "No module named 'PyQt5'"
```bash
pip install PyQt5
```

### "Template database not found"
- Check that template_library.db exists at:
  `/home/red1/Documents/bonsai/RawDWG/Terminal1_Project/Templates/terminal_base_v1.0/template_library.db`
- Application will show warning but still run

### "Permission denied: ./run.sh"
```bash
chmod +x run.sh
```

### Display/GUI issues
If running over SSH without X11:
```bash
# Enable X11 forwarding
ssh -X user@host

# Or use VNC/remote desktop
```

## Verification

After installation, verify everything works:

```bash
cd /home/red1/Documents/bonsai/RawDWG/TemplateConfigurator

# Test imports
python3 -c "from models import Space, Project; print('✓ Models OK')"
python3 -c "from database import TemplateDatabase; print('✓ Database OK')"
python3 -c "from PyQt5.QtWidgets import QApplication; print('✓ PyQt5 OK')"

# Test template database
python3 database/template_db.py
```

Expected output:
```
Looking for database at: /home/red1/Documents/bonsai/RawDWG/Terminal1_Project/Templates/terminal_base_v1.0/template_library.db

Template Library Statistics:
  Total templates: 44
  Total instances: 43344

By category:
    ACMV: 4 templates
    Chilled_Water: 5 templates
    Electrical: 3 templates
    ...
```

## Quick Start

**One-command installation and run:**

```bash
cd /home/red1/Documents/bonsai/RawDWG/TemplateConfigurator && \
pip install -r requirements.txt && \
python3 main.py
```

## Dependencies Breakdown

| Package | Purpose | Size |
|---------|---------|------|
| PyQt5 | GUI framework | ~50MB |
| ezdxf | DXF/DWG parsing | ~5MB |
| openpyxl | Excel parsing | ~3MB |
| PyPDF2 | PDF text extraction | ~1MB |
| matplotlib | Visualization (future) | ~40MB |
| pytest | Unit testing | ~3MB |

Total: ~100MB

## Next Steps After Installation

1. Launch application: `python3 main.py`
2. Test with Terminal 1 DWG file
3. Configure spaces
4. Export JSON configuration
5. Use JSON with conversion script

## Getting Help

- Check README.md for usage instructions
- Check project documentation in RawDWG/Documentation/
- Report issues: https://github.com/IfcOpenShell/IfcOpenShell/issues
