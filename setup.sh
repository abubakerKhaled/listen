#!/bin/bash
# Listen - Unified Setup Script
# Combines build, install, and update functionality
# Usage: ./setup.sh [OPTIONS]
#
# Options:
#   --build-only     Only build the AppImage (don't install)
#   --install-only   Only install existing AppImage
#   --update         Check for and install updates
#   --system         Install system-wide (requires sudo)
#   --help           Show this help message

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="listen"
APP_VERSION="1.0.0"
ARCH="x86_64"
GITHUB_REPO="abubakerKhaled/listen"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Flags
BUILD_ONLY=false
INSTALL_ONLY=false
UPDATE_MODE=false
SYSTEM_INSTALL=false

print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════╗"
    echo "║           Listen Setup Script             ║"
    echo "║     Voice-to-Text for Linux               ║"
    echo "╚═══════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_help() {
    echo "Usage: ./setup.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --build-only     Only build the AppImage (don't install)"
    echo "  --install-only   Only install existing AppImage"
    echo "  --update         Check for and install updates"
    echo "  --system         Install system-wide to /usr/local/bin (requires sudo)"
    echo "  --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./setup.sh                  # Build (if needed) and install"
    echo "  ./setup.sh --build-only     # Just build the AppImage"
    echo "  ./setup.sh --install-only   # Install existing AppImage"
    echo "  ./setup.sh --system         # System-wide installation"
    echo "  ./setup.sh --update         # Check for updates"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --build-only)
            BUILD_ONLY=true
            shift
            ;;
        --install-only)
            INSTALL_ONLY=true
            shift
            ;;
        --update)
            UPDATE_MODE=true
            shift
            ;;
        --system)
            SYSTEM_INSTALL=true
            shift
            ;;
        --help|-h)
            print_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            print_help
            exit 1
            ;;
    esac
done

# ============================================================
# BUILD FUNCTIONS
# ============================================================

build_appimage() {
    log_info "Building Listen AppImage v${APP_VERSION}..."
    
    BUILD_DIR="${SCRIPT_DIR}/build"
    APPDIR="${BUILD_DIR}/AppDir"
    
    rm -rf "${BUILD_DIR}"
    mkdir -p "${APPDIR}/usr/bin"
    mkdir -p "${APPDIR}/usr/lib/python3/site-packages"
    
    log_info "Step 1/7: Creating Python environment..."
    VENV_DIR="${BUILD_DIR}/venv"
    python3 -m venv "${VENV_DIR}"
    source "${VENV_DIR}/bin/activate"
    
    log_info "Step 2/7: Installing dependencies..."
    pip install --upgrade pip wheel > /dev/null
    pip install "${SCRIPT_DIR}" > /dev/null
    
    log_info "Step 3/7: Bundling Python and packages..."
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    SYSTEM_PYTHON_PREFIX=$(python3 -c "import sys; print(sys.base_prefix)")
    PYTHON_BIN="${SYSTEM_PYTHON_PREFIX}/bin/python${PYTHON_VERSION}"
    cp "${PYTHON_BIN}" "${APPDIR}/usr/bin/python3"
    
    SYSTEM_PYTHON_LIB="${SYSTEM_PYTHON_PREFIX}/lib/python${PYTHON_VERSION}"
    mkdir -p "${APPDIR}/usr/lib/python${PYTHON_VERSION}"
    if [ -d "${SYSTEM_PYTHON_LIB}" ]; then
        cp -r "${SYSTEM_PYTHON_LIB}/"* "${APPDIR}/usr/lib/python${PYTHON_VERSION}/" 2>/dev/null || true
    else
        log_error "Python stdlib not found at ${SYSTEM_PYTHON_LIB}"
        exit 1
    fi
    
    SITE_PACKAGES="${VENV_DIR}/lib/python${PYTHON_VERSION}/site-packages"
    mkdir -p "${APPDIR}/usr/lib/python${PYTHON_VERSION}/site-packages"
    cp -r "${SITE_PACKAGES}/"* "${APPDIR}/usr/lib/python${PYTHON_VERSION}/site-packages/"
    
    log_info "Step 4/7: Copying application files..."
    cp -r "${SCRIPT_DIR}/src/listen_app" "${APPDIR}/usr/lib/python${PYTHON_VERSION}/site-packages/"
    cp "${SCRIPT_DIR}/appimage/AppRun" "${APPDIR}/"
    chmod +x "${APPDIR}/AppRun"
    cp "${SCRIPT_DIR}/appimage/listen.desktop" "${APPDIR}/"
    
    if [ -f "${SCRIPT_DIR}/appimage/listen.png" ]; then
        cp "${SCRIPT_DIR}/appimage/listen.png" "${APPDIR}/"
    fi
    
    log_info "Step 5/7: Copying required libraries..."
    mkdir -p "${APPDIR}/usr/lib/x86_64-linux-gnu"
    
    for lib in /usr/lib/x86_64-linux-gnu/libportaudio*; do
        if [ -f "$lib" ]; then
            cp -L "$lib" "${APPDIR}/usr/lib/x86_64-linux-gnu/" 2>/dev/null || true
        fi
    done
    
    SYSTEM_SITE_PACKAGES="/usr/lib/python3/dist-packages"
    if [ -d "${SYSTEM_SITE_PACKAGES}/gi" ]; then
        cp -r "${SYSTEM_SITE_PACKAGES}/gi" "${APPDIR}/usr/lib/python${PYTHON_VERSION}/site-packages/"
    fi
    if [ -d "${SYSTEM_SITE_PACKAGES}/cairo" ]; then
        cp -r "${SYSTEM_SITE_PACKAGES}/cairo" "${APPDIR}/usr/lib/python${PYTHON_VERSION}/site-packages/"
    fi
    
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
    
    log_info "Step 6/7: Downloading appimagetool..."
    APPIMAGETOOL="${BUILD_DIR}/appimagetool"
    if [ ! -f "${APPIMAGETOOL}" ]; then
        wget -q -O "${APPIMAGETOOL}" \
            "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
        chmod +x "${APPIMAGETOOL}"
    fi
    
    log_info "Step 7/7: Creating AppImage..."
    deactivate 2>/dev/null || true
    
    cd "${BUILD_DIR}"
    ARCH="${ARCH}" "${APPIMAGETOOL}" --no-appstream AppDir > /dev/null 2>&1
    
    APPIMAGE_NAME="${APP_NAME}-${APP_VERSION}-${ARCH}.AppImage"
    mv "${APP_NAME}"*.AppImage "${SCRIPT_DIR}/${APPIMAGE_NAME}" 2>/dev/null || \
        mv Listen*.AppImage "${SCRIPT_DIR}/${APPIMAGE_NAME}" 2>/dev/null || true
    
    cd "${SCRIPT_DIR}"
    
    log_success "AppImage built: ${SCRIPT_DIR}/${APPIMAGE_NAME}"
    echo "${SCRIPT_DIR}/${APPIMAGE_NAME}"
}

# ============================================================
# INSTALL FUNCTIONS
# ============================================================

find_appimage() {
    if [ -f "${SCRIPT_DIR}/${APP_NAME}"*.AppImage ]; then
        ls "${SCRIPT_DIR}/${APP_NAME}"*.AppImage | head -1
    else
        echo ""
    fi
}

install_user() {
    local APPIMAGE_PATH="$1"
    
    log_info "Installing to user directory..."
    
    INSTALL_DIR="${HOME}/.local/bin"
    APPLICATIONS_DIR="${HOME}/.local/share/applications"
    ICONS_DIR="${HOME}/.local/share/icons/hicolor"
    
    mkdir -p "${INSTALL_DIR}"
    mkdir -p "${APPLICATIONS_DIR}"
    mkdir -p "${ICONS_DIR}/256x256/apps"
    mkdir -p "${ICONS_DIR}/128x128/apps"
    mkdir -p "${ICONS_DIR}/64x64/apps"
    mkdir -p "${ICONS_DIR}/48x48/apps"
    
    cp "${APPIMAGE_PATH}" "${INSTALL_DIR}/${APP_NAME}"
    chmod +x "${INSTALL_DIR}/${APP_NAME}"
    
    # Install icons
    ICON_SOURCE="${SCRIPT_DIR}/appimage/listen.png"
    if [ -f "${ICON_SOURCE}" ]; then
        if command -v convert &> /dev/null; then
            convert "${ICON_SOURCE}" -resize 256x256 "${ICONS_DIR}/256x256/apps/listen.png"
            convert "${ICON_SOURCE}" -resize 128x128 "${ICONS_DIR}/128x128/apps/listen.png"
            convert "${ICON_SOURCE}" -resize 64x64 "${ICONS_DIR}/64x64/apps/listen.png"
            convert "${ICON_SOURCE}" -resize 48x48 "${ICONS_DIR}/48x48/apps/listen.png"
        else
            cp "${ICON_SOURCE}" "${ICONS_DIR}/256x256/apps/listen.png"
        fi
    fi
    
    # Create desktop entry
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
    
    # Update databases
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "${APPLICATIONS_DIR}" 2>/dev/null || true
    fi
    if command -v gtk-update-icon-cache &> /dev/null; then
        gtk-update-icon-cache -f -t "${ICONS_DIR}" 2>/dev/null || true
    fi
    
    log_success "Installed to ${INSTALL_DIR}/${APP_NAME}"
    
    # Check PATH
    if [[ ":$PATH:" != *":${HOME}/.local/bin:"* ]]; then
        log_warn "~/.local/bin is not in your PATH"
        echo "Add this to your ~/.bashrc or ~/.zshrc:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
}

install_system() {
    local APPIMAGE_PATH="$1"
    
    log_info "Installing system-wide (requires sudo)..."
    
    sudo cp "${APPIMAGE_PATH}" "/usr/local/bin/${APP_NAME}"
    sudo chmod +x "/usr/local/bin/${APP_NAME}"
    
    log_success "Installed to /usr/local/bin/${APP_NAME}"
}

# ============================================================
# UPDATE FUNCTIONS
# ============================================================

check_update() {
    log_info "Checking for updates..."
    
    # Get latest release version from GitHub API
    LATEST_VERSION=$(curl -s "https://api.github.com/repos/${GITHUB_REPO}/releases/latest" | \
        grep '"tag_name"' | sed -E 's/.*"v?([^"]+)".*/\1/')
    
    if [ -z "${LATEST_VERSION}" ]; then
        log_error "Could not check for updates. Check your internet connection."
        return 1
    fi
    
    log_info "Current version: ${APP_VERSION}"
    log_info "Latest version: ${LATEST_VERSION}"
    
    if [ "${APP_VERSION}" != "${LATEST_VERSION}" ]; then
        log_info "Update available! Downloading v${LATEST_VERSION}..."
        
        DOWNLOAD_URL="https://github.com/${GITHUB_REPO}/releases/download/v${LATEST_VERSION}/listen-${LATEST_VERSION}-x86_64.AppImage"
        TEMP_FILE=$(mktemp)
        
        if wget -q -O "${TEMP_FILE}" "${DOWNLOAD_URL}"; then
            chmod +x "${TEMP_FILE}"
            
            # Determine install location
            if [ -f "/usr/local/bin/${APP_NAME}" ]; then
                sudo mv "${TEMP_FILE}" "/usr/local/bin/${APP_NAME}"
                sudo chmod +x "/usr/local/bin/${APP_NAME}"
                log_success "Updated to v${LATEST_VERSION} (system-wide)"
            elif [ -f "${HOME}/.local/bin/${APP_NAME}" ]; then
                mv "${TEMP_FILE}" "${HOME}/.local/bin/${APP_NAME}"
                chmod +x "${HOME}/.local/bin/${APP_NAME}"
                log_success "Updated to v${LATEST_VERSION} (user install)"
            else
                log_warn "Listen not found in expected locations. Installing to ~/.local/bin/"
                mkdir -p "${HOME}/.local/bin"
                mv "${TEMP_FILE}" "${HOME}/.local/bin/${APP_NAME}"
                chmod +x "${HOME}/.local/bin/${APP_NAME}"
                log_success "Installed v${LATEST_VERSION}"
            fi
        else
            log_error "Failed to download update"
            rm -f "${TEMP_FILE}"
            return 1
        fi
    else
        log_success "Already up to date!"
    fi
}

# ============================================================
# MAIN
# ============================================================

main() {
    print_banner
    
    # Handle update mode
    if [ "$UPDATE_MODE" = true ]; then
        check_update
        exit 0
    fi
    
    # Handle install-only mode
    if [ "$INSTALL_ONLY" = true ]; then
        APPIMAGE_PATH=$(find_appimage)
        if [ -z "$APPIMAGE_PATH" ]; then
            log_error "No AppImage found. Run without --install-only to build first."
            exit 1
        fi
        
        if [ "$SYSTEM_INSTALL" = true ]; then
            install_system "$APPIMAGE_PATH"
        else
            install_user "$APPIMAGE_PATH"
        fi
        exit 0
    fi
    
    # Build AppImage if needed or requested
    APPIMAGE_PATH=$(find_appimage)
    
    if [ -z "$APPIMAGE_PATH" ] || [ "$BUILD_ONLY" = true ]; then
        APPIMAGE_PATH=$(build_appimage)
    else
        log_info "Using existing AppImage: ${APPIMAGE_PATH}"
    fi
    
    # Install unless build-only
    if [ "$BUILD_ONLY" != true ]; then
        echo ""
        if [ "$SYSTEM_INSTALL" = true ]; then
            install_system "$APPIMAGE_PATH"
        else
            install_user "$APPIMAGE_PATH"
        fi
    fi
    
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           Setup Complete!                 ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
    echo ""
    echo "Run 'listen' to start the application."
    echo "Run './setup.sh --update' to check for updates."
}

main
