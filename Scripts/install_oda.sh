#!/bin/bash
#=============================================================================
# ODA File Converter Installation Helper
#=============================================================================
#
# This script helps install ODA File Converter after you download it manually
#
# Steps:
#   1. Download ODA from: https://www.opendesign.com/guestfiles/oda_file_converter
#   2. Save the .deb file to ~/Downloads/
#   3. Run this script
#
#=============================================================================

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================================="
echo "ODA File Converter Installation Helper"
echo "=========================================================="
echo ""

# Check if ODA already installed
if command -v ODAFileConverter &> /dev/null; then
    echo -e "${GREEN}✓ ODA File Converter is already installed!${NC}"
    ODAFileConverter --version 2>&1 || true
    echo ""
    echo "You can proceed with conversion:"
    echo "  cd /home/red1/Documents/bonsai/RawDWG"
    echo "  ./convert_dwg_to_dxf.sh"
    exit 0
fi

echo "Looking for ODA .deb file in ~/Downloads..."
echo ""

# Find .deb file
DEB_FILE=$(find ~/Downloads -name "ODAFileConverter*.deb" -type f 2>/dev/null | head -1)

if [ -z "$DEB_FILE" ]; then
    echo -e "${RED}ERROR: ODA .deb file not found in ~/Downloads/${NC}"
    echo ""
    echo "Please download ODA File Converter:"
    echo ""
    echo "1. Visit: https://www.opendesign.com/guestfiles/oda_file_converter"
    echo "2. Create account (free) if needed"
    echo "3. Download: Linux x64 version (.deb file)"
    echo "4. Save to: ~/Downloads/"
    echo "5. Run this script again"
    echo ""
    exit 1
fi

echo -e "${GREEN}✓ Found: $DEB_FILE${NC}"
echo "Size: $(du -h "$DEB_FILE" | cut -f1)"
echo ""

# Install
echo "Installing ODA File Converter..."
echo "(You may be prompted for sudo password)"
echo ""

sudo dpkg -i "$DEB_FILE"

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${YELLOW}Installing missing dependencies...${NC}"
    sudo apt-get install -f -y
fi

# Verify installation
echo ""
echo "Verifying installation..."

if command -v ODAFileConverter &> /dev/null; then
    echo ""
    echo -e "${GREEN}✓ ODA File Converter installed successfully!${NC}"
    echo ""
    ODAFileConverter --version 2>&1 || true
    echo ""
    echo "=========================================================="
    echo "Installation Complete!"
    echo "=========================================================="
    echo ""
    echo "Next steps:"
    echo "  cd /home/red1/Documents/bonsai/RawDWG"
    echo "  ./convert_dwg_to_dxf.sh"
    echo ""
else
    echo ""
    echo -e "${RED}ERROR: Installation failed${NC}"
    echo "Please check error messages above"
    exit 1
fi
