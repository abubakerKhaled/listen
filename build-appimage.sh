#!/bin/bash
# Build script for creating the Listen AppImage
# Usage: ./build-appimage.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="listen"
APP_VERSION="1.0.0"
ARCH="x86_64"

echo "=== Building Listen AppImage ==="
echo "Version: ${APP_VERSION}"
echo "Architecture: ${ARCH}"
echo ""

# Create build directory
BUILD_DIR="${SCRIPT_DIR}/build"
APPDIR="${BUILD_DIR}/AppDir"

rm -rf "${BUILD_DIR}"
mkdir -p "${APPDIR}/usr/bin"
mkdir -p "${APPDIR}/usr/lib/python3/site-packages"

echo "Step 1: Creating Python environment..."
# Create a temporary virtual environment to get all dependencies
VENV_DIR="${BUILD_DIR}/venv"
python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

echo "Step 2: Installing dependencies..."
pip install --upgrade pip wheel
pip install "${SCRIPT_DIR}"

echo "Step 3: Bundling Python and packages..."
# Copy Python binary from the system (not venv)
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
SYSTEM_PYTHON_PREFIX=$(python3 -c "import sys; print(sys.base_prefix)")
PYTHON_BIN="${SYSTEM_PYTHON_PREFIX}/bin/python${PYTHON_VERSION}"
cp "${PYTHON_BIN}" "${APPDIR}/usr/bin/python3"

# Copy Python standard library from SYSTEM Python (not venv)
SYSTEM_PYTHON_LIB="${SYSTEM_PYTHON_PREFIX}/lib/python${PYTHON_VERSION}"
mkdir -p "${APPDIR}/usr/lib/python${PYTHON_VERSION}"
if [ -d "${SYSTEM_PYTHON_LIB}" ]; then
    echo "Copying Python stdlib from ${SYSTEM_PYTHON_LIB}..."
    cp -r "${SYSTEM_PYTHON_LIB}/"* "${APPDIR}/usr/lib/python${PYTHON_VERSION}/" 2>/dev/null || true
else
    echo "ERROR: Python stdlib not found at ${SYSTEM_PYTHON_LIB}"
    exit 1
fi

# Copy site-packages from venv
SITE_PACKAGES="${VENV_DIR}/lib/python${PYTHON_VERSION}/site-packages"
mkdir -p "${APPDIR}/usr/lib/python${PYTHON_VERSION}/site-packages"
cp -r "${SITE_PACKAGES}/"* "${APPDIR}/usr/lib/python${PYTHON_VERSION}/site-packages/"

echo "Step 4: Copying application files..."
# Copy our application to the versioned site-packages
cp -r "${SCRIPT_DIR}/src/listen_app" "${APPDIR}/usr/lib/python${PYTHON_VERSION}/site-packages/"

# Copy AppRun and desktop file
cp "${SCRIPT_DIR}/appimage/AppRun" "${APPDIR}/"
chmod +x "${APPDIR}/AppRun"

# Copy desktop file
cp "${SCRIPT_DIR}/appimage/listen.desktop" "${APPDIR}/"

# Copy icon (use PNG if available, otherwise create a placeholder)
if [ -f "${SCRIPT_DIR}/appimage/listen.png" ]; then
    cp "${SCRIPT_DIR}/appimage/listen.png" "${APPDIR}/"
else
    echo "Warning: No icon found, creating placeholder..."
    # Create a simple SVG icon as fallback
    cat > "${APPDIR}/listen.svg" << 'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#6366f1"/>
      <stop offset="100%" style="stop-color:#4f46e5"/>
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="12" fill="url(#bg)"/>
  <path d="M32 12a6 6 0 0 1 6 6v16a6 6 0 0 1-12 0V18a6 6 0 0 1 6-6z" fill="white"/>
  <path d="M22 30v4a10 10 0 0 0 20 0v-4" stroke="white" stroke-width="3" fill="none" stroke-linecap="round"/>
  <line x1="32" y1="44" x2="32" y2="52" stroke="white" stroke-width="3" stroke-linecap="round"/>
  <line x1="26" y1="52" x2="38" y2="52" stroke="white" stroke-width="3" stroke-linecap="round"/>
</svg>
EOF
    # Convert SVG to PNG if ImageMagick is available
    if command -v convert &> /dev/null; then
        convert "${APPDIR}/listen.svg" -resize 256x256 "${APPDIR}/listen.png"
        rm "${APPDIR}/listen.svg"
    else
        mv "${APPDIR}/listen.svg" "${APPDIR}/listen.png"
    fi
fi

echo "Step 5: Copying required libraries..."
# Copy required shared libraries
mkdir -p "${APPDIR}/usr/lib/x86_64-linux-gnu"

# Copy PortAudio library if available
for lib in /usr/lib/x86_64-linux-gnu/libportaudio*; do
    if [ -f "$lib" ]; then
        cp -L "$lib" "${APPDIR}/usr/lib/x86_64-linux-gnu/" 2>/dev/null || true
    fi
done

# Copy PyGObject (gi) from system Python
echo "Copying PyGObject (gi) module..."
SYSTEM_SITE_PACKAGES="/usr/lib/python3/dist-packages"
if [ -d "${SYSTEM_SITE_PACKAGES}/gi" ]; then
    cp -r "${SYSTEM_SITE_PACKAGES}/gi" "${APPDIR}/usr/lib/python${PYTHON_VERSION}/site-packages/"
fi

# Copy cairo bindings if available
if [ -d "${SYSTEM_SITE_PACKAGES}/cairo" ]; then
    cp -r "${SYSTEM_SITE_PACKAGES}/cairo" "${APPDIR}/usr/lib/python${PYTHON_VERSION}/site-packages/"
fi

# Copy GObject Introspection typelibs for GTK4 and Adwaita
echo "Copying GTK4/Adwaita typelibs..."
mkdir -p "${APPDIR}/usr/lib/girepository-1.0"
for typelib in Gtk-4.0 Gdk-4.0 Adw-1 GdkPixbuf-2.0 Pango-1.0 PangoCairo-1.0 \
               GObject-2.0 GLib-2.0 Gio-2.0 cairo-1.0 Graphene-1.0 GModule-2.0 \
               HarfBuzz-0.0 freetype2-2.0 Gsk-4.0; do
    for path in /usr/lib/x86_64-linux-gnu/girepository-1.0 /usr/lib/girepository-1.0; do
        if [ -f "${path}/${typelib}.typelib" ]; then
            cp "${path}/${typelib}.typelib" "${APPDIR}/usr/lib/girepository-1.0/" 2>/dev/null || true
        fi
    done
done

echo "Step 6: Downloading appimagetool..."
APPIMAGETOOL="${BUILD_DIR}/appimagetool"
if [ ! -f "${APPIMAGETOOL}" ]; then
    wget -q -O "${APPIMAGETOOL}" \
        "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "${APPIMAGETOOL}"
fi

echo "Step 7: Creating AppImage..."
deactivate 2>/dev/null || true

cd "${BUILD_DIR}"
ARCH="${ARCH}" "${APPIMAGETOOL}" --no-appstream AppDir

# Move to project root
APPIMAGE_NAME="${APP_NAME}-${APP_VERSION}-${ARCH}.AppImage"
mv "${APP_NAME}"*.AppImage "${SCRIPT_DIR}/${APPIMAGE_NAME}" 2>/dev/null || \
    mv Listen*.AppImage "${SCRIPT_DIR}/${APPIMAGE_NAME}" 2>/dev/null || true

echo ""
echo "=== Build Complete ==="
echo "AppImage created: ${SCRIPT_DIR}/${APPIMAGE_NAME}"
echo ""
echo "To run:"
echo "  chmod +x ${APPIMAGE_NAME}"
echo "  ./${APPIMAGE_NAME}"
echo ""
echo "To install system-wide:"
echo "  sudo cp ${APPIMAGE_NAME} /usr/local/bin/listen"
echo "  sudo chmod +x /usr/local/bin/listen"
