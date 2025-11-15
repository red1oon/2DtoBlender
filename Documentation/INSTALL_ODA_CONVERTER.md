# Installing ODA File Converter

## Manual Installation Steps

The ODA File Converter requires manual download due to registration requirements.

### Step 1: Download ODA File Converter

1. Visit: https://www.opendesign.com/guestfiles/oda_file_converter
2. Select your platform: **Linux x64**
3. Download the latest version (should be a .deb file ~50-100MB)
4. Save to: `/tmp/oda_converter/`

### Step 2: Install the Package

```bash
cd /tmp/oda_converter/
sudo dpkg -i ODAFileConverter_*.deb

# If dependencies are missing, run:
sudo apt-get install -f
```

### Step 3: Verify Installation

```bash
which ODAFileConverter
# Should output: /usr/bin/ODAFileConverter

ODAFileConverter --version
```

### Step 4: Convert DWG to DXF

Once installed, use the conversion script:

```bash
cd /home/red1/Documents/bonsai/RawDWG
./convert_dwg_to_dxf.sh
```

---

## Alternative: Manual Conversion

If automatic installation doesn't work, you can manually convert:

### Option A: Using ODA File Converter GUI

```bash
ODAFileConverter
# Then use the GUI to:
# 1. Select input folder: /home/red1/Documents/bonsai/RawDWG/
# 2. Select output folder: /home/red1/Documents/bonsai/RawDWG/
# 3. Choose output format: DXF (ACAD 2018)
# 4. Click Convert
```

### Option B: Command Line

```bash
ODAFileConverter \
    "/home/red1/Documents/bonsai/RawDWG" \
    "/home/red1/Documents/bonsai/RawDWG" \
    "ACAD2018" \
    "DXF" \
    "0" \
    "1"
```

Parameters:
- Input folder
- Output folder
- Output version (ACAD2018)
- Output format (DXF)
- Recursive (0=no, 1=yes)
- Audit (0=no, 1=yes)

---

## After Conversion

The converted file will be named:
`2. BANGUNAN TERMINAL 1 .dxf`

Then proceed with testing:

```bash
cd /home/red1/Documents/bonsai/RawDWG
PYTHONPATH=/home/red1/Projects/IfcOpenShell/src ~/blender-4.5.3/4.5/python/bin/python3.11 \
    dwg_parser.py "2. BANGUNAN TERMINAL 1 .dxf"
```

---

## Troubleshooting

### Error: "command not found"
The .deb package might not be installed correctly. Try:
```bash
sudo apt-get install -f
which ODAFileConverter
```

### Error: "missing libraries"
Install dependencies:
```bash
sudo apt-get install libqt5core5a libqt5gui5 libqt5widgets5
```

### File too large
The Terminal 1 DWG is 14MB. Conversion may take 1-2 minutes.
