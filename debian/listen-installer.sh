#!/bin/bash
# Listen AppImage Installer Script
# Downloads and installs the Listen AppImage from GitHub releases

set -e

APP_NAME="listen"
GITHUB_REPO="abubakerKhaled/listen"
VERSION="1.0.0"
INSTALL_DIR="$HOME/.local/share/listen"
APPIMAGE_PATH="$INSTALL_DIR/listen.AppImage"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Create install directory
mkdir -p "$INSTALL_DIR"

# Download AppImage
DOWNLOAD_URL="https://github.com/${GITHUB_REPO}/releases/download/v${VERSION}/listen-${VERSION}-x86_64.AppImage"
log_info "Downloading Listen AppImage from GitHub..."
log_info "URL: $DOWNLOAD_URL"

if command -v wget &> /dev/null; then
    wget -q --show-progress -O "$APPIMAGE_PATH" "$DOWNLOAD_URL"
elif command -v curl &> /dev/null; then
    curl -L -o "$APPIMAGE_PATH" "$DOWNLOAD_URL"
else
    log_error "Neither wget nor curl found. Please install one of them."
    exit 1
fi

# Make executable
chmod +x "$APPIMAGE_PATH"

log_success "Listen installed successfully!"
log_info "You can now run 'listen' from the terminal or find it in your application menu."
