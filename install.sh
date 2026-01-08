#!/bin/bash
# Install Listen AppImage to user's application menu
# Usage: ./install.sh [path-to-appimage]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="listen"

# Find AppImage
if [ -n "$1" ]; then
    APPIMAGE_PATH="$1"
elif [ -f "${SCRIPT_DIR}/${APP_NAME}"*.AppImage ]; then
    APPIMAGE_PATH=$(ls "${SCRIPT_DIR}/${APP_NAME}"*.AppImage | head -1)
else
    echo "Error: No AppImage found. Please build it first with ./build-appimage.sh"
    echo "Or provide the path: ./install.sh /path/to/listen.AppImage"
    exit 1
fi

echo "=== Installing Listen to Application Menu ==="
echo "AppImage: ${APPIMAGE_PATH}"
echo ""

# Create directories
INSTALL_DIR="${HOME}/.local/bin"
APPLICATIONS_DIR="${HOME}/.local/share/applications"
ICONS_DIR="${HOME}/.local/share/icons/hicolor"

mkdir -p "${INSTALL_DIR}"
mkdir -p "${APPLICATIONS_DIR}"
mkdir -p "${ICONS_DIR}/256x256/apps"
mkdir -p "${ICONS_DIR}/128x128/apps"
mkdir -p "${ICONS_DIR}/64x64/apps"
mkdir -p "${ICONS_DIR}/48x48/apps"

# Copy AppImage to ~/.local/bin
echo "Step 1: Installing AppImage to ${INSTALL_DIR}..."
cp "${APPIMAGE_PATH}" "${INSTALL_DIR}/${APP_NAME}"
chmod +x "${INSTALL_DIR}/${APP_NAME}"

# Install icon in multiple sizes
echo "Step 2: Installing icons..."
ICON_SOURCE="${SCRIPT_DIR}/appimage/listen.png"
if [ -f "${ICON_SOURCE}" ]; then
    # If ImageMagick is available, create multiple sizes
    if command -v convert &> /dev/null; then
        convert "${ICON_SOURCE}" -resize 256x256 "${ICONS_DIR}/256x256/apps/listen.png"
        convert "${ICON_SOURCE}" -resize 128x128 "${ICONS_DIR}/128x128/apps/listen.png"
        convert "${ICON_SOURCE}" -resize 64x64 "${ICONS_DIR}/64x64/apps/listen.png"
        convert "${ICON_SOURCE}" -resize 48x48 "${ICONS_DIR}/48x48/apps/listen.png"
    else
        # Just copy the original to the largest size
        cp "${ICON_SOURCE}" "${ICONS_DIR}/256x256/apps/listen.png"
    fi
else
    echo "Warning: No icon found at ${ICON_SOURCE}"
fi

# Create desktop entry with correct path
echo "Step 3: Creating desktop entry..."
cat > "${APPLICATIONS_DIR}/listen.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Listen
GenericName=Voice Transcription
Comment=Voice-to-text transcription tool powered by OpenAI Whisper
Exec=${INSTALL_DIR}/${APP_NAME} %U
Icon=listen
Categories=AudioVideo;Audio;Utility;
Terminal=false
Keywords=voice;speech;transcription;whisper;audio;recording;speech-to-text;
StartupNotify=true
StartupWMClass=listen
EOF

# Update desktop database
echo "Step 4: Updating desktop database..."
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "${APPLICATIONS_DIR}" 2>/dev/null || true
fi

# Update icon cache
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f -t "${ICONS_DIR}" 2>/dev/null || true
fi

echo ""
echo "=== Installation Complete! ==="
echo ""
echo "Listen has been added to your application menu."
echo "You can now find it by searching 'Listen' in your app launcher."
echo ""
echo "To uninstall, run: ./uninstall.sh"
echo ""

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":${HOME}/.local/bin:"* ]]; then
    echo "Note: ~/.local/bin is not in your PATH."
    echo "To use 'listen' from the terminal, add this to your ~/.bashrc or ~/.zshrc:"
    echo ""
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi
