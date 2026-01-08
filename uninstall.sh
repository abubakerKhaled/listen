#!/bin/bash
# Uninstall Listen from user's application menu
# Usage: ./uninstall.sh

set -e

APP_NAME="listen"

echo "=== Uninstalling Listen from Application Menu ==="
echo ""

INSTALL_DIR="${HOME}/.local/bin"
APPLICATIONS_DIR="${HOME}/.local/share/applications"
ICONS_DIR="${HOME}/.local/share/icons/hicolor"

# Remove AppImage
if [ -f "${INSTALL_DIR}/${APP_NAME}" ]; then
    echo "Removing AppImage..."
    rm -f "${INSTALL_DIR}/${APP_NAME}"
fi

# Remove desktop entry
if [ -f "${APPLICATIONS_DIR}/${APP_NAME}.desktop" ]; then
    echo "Removing desktop entry..."
    rm -f "${APPLICATIONS_DIR}/${APP_NAME}.desktop"
fi

# Remove icons
echo "Removing icons..."
rm -f "${ICONS_DIR}/256x256/apps/listen.png"
rm -f "${ICONS_DIR}/128x128/apps/listen.png"
rm -f "${ICONS_DIR}/64x64/apps/listen.png"
rm -f "${ICONS_DIR}/48x48/apps/listen.png"

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "${APPLICATIONS_DIR}" 2>/dev/null || true
fi

# Update icon cache
if command -v gtk-update-icon-cache &> /dev/null; then
    gtk-update-icon-cache -f -t "${ICONS_DIR}" 2>/dev/null || true
fi

echo ""
echo "=== Uninstall Complete ==="
echo "Listen has been removed from your application menu."
