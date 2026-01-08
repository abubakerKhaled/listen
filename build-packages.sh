#!/bin/bash
# Listen - Native Package Builder
# Builds .deb and/or .rpm packages for the Listen application
#
# Usage: ./build-packages.sh [OPTIONS]
#
# Options:
#   --deb-only    Only build .deb package
#   --rpm-only    Only build .rpm package
#   --clean       Clean build artifacts before building
#   --help        Show this help message

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="listen"
APP_VERSION="1.0.0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Flags
DEB_ONLY=false
RPM_ONLY=false
CLEAN=false

print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════╗"
    echo "║     Listen Native Package Builder         ║"
    echo "╚═══════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_help() {
    echo "Usage: ./build-packages.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --deb-only    Only build .deb package (Debian/Ubuntu)"
    echo "  --rpm-only    Only build .rpm package (Fedora/RHEL)"
    echo "  --clean       Clean build artifacts before building"
    echo "  --help        Show this help message"
    echo ""
    echo "Prerequisites:"
    echo "  For .deb: apt install build-essential debhelper dh-python devscripts"
    echo "  For .rpm: dnf install rpm-build python3-devel"
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
        --deb-only)
            DEB_ONLY=true
            shift
            ;;
        --rpm-only)
            RPM_ONLY=true
            shift
            ;;
        --clean)
            CLEAN=true
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
# DEBIAN PACKAGE BUILD
# ============================================================

check_deb_deps() {
    local missing=()
    
    if ! command -v dpkg-buildpackage &> /dev/null; then
        missing+=("dpkg-dev")
    fi
    if ! command -v debuild &> /dev/null; then
        missing+=("devscripts")
    fi
    if ! dpkg -l | grep -q "debhelper"; then
        missing+=("debhelper")
    fi
    if ! dpkg -l | grep -q "dh-python"; then
        missing+=("dh-python")
    fi
    
    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing dependencies: ${missing[*]}"
        echo "Install with: sudo apt install ${missing[*]}"
        return 1
    fi
    return 0
}

build_deb() {
    log_info "Building .deb package..."
    
    if ! check_deb_deps; then
        return 1
    fi
    
    cd "${SCRIPT_DIR}"
    
    # Create dist directory
    mkdir -p dist
    
    # Make rules executable
    chmod +x debian/rules
    
    # Build the package
    log_info "Running dpkg-buildpackage..."
    dpkg-buildpackage -us -uc -b --no-sign 2>&1 | tee dist/deb-build.log
    
    # Move generated .deb to dist/
    mv ../${APP_NAME}_*.deb dist/ 2>/dev/null || true
    mv ../${APP_NAME}_*.buildinfo dist/ 2>/dev/null || true
    mv ../${APP_NAME}_*.changes dist/ 2>/dev/null || true
    
    DEB_FILE=$(ls dist/${APP_NAME}_*.deb 2>/dev/null | head -1)
    
    if [ -n "${DEB_FILE}" ]; then
        log_success ".deb package built: ${DEB_FILE}"
        echo ""
        echo "To install:"
        echo "  sudo apt install ./${DEB_FILE}"
        echo "Or:"
        echo "  sudo dpkg -i ${DEB_FILE}"
    else
        log_error "Failed to build .deb package. Check dist/deb-build.log for details."
        return 1
    fi
}

# ============================================================
# RPM PACKAGE BUILD
# ============================================================

check_rpm_deps() {
    local missing=()
    
    if ! command -v rpmbuild &> /dev/null; then
        missing+=("rpm-build")
    fi
    
    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing dependencies: ${missing[*]}"
        echo "Install with: sudo dnf install ${missing[*]}"
        return 1
    fi
    return 0
}

build_rpm() {
    log_info "Building .rpm package..."
    
    if ! check_rpm_deps; then
        return 1
    fi
    
    cd "${SCRIPT_DIR}"
    
    # Create required directories
    mkdir -p dist
    mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
    
    # Create source tarball
    log_info "Creating source tarball..."
    TARBALL_NAME="${APP_NAME}-${APP_VERSION}"
    TARBALL_DIR=$(mktemp -d)
    
    mkdir -p "${TARBALL_DIR}/${TARBALL_NAME}"
    cp -r src pyproject.toml README.md LICENSE appimage "${TARBALL_DIR}/${TARBALL_NAME}/"
    
    tar -czf ~/rpmbuild/SOURCES/${TARBALL_NAME}.tar.gz -C "${TARBALL_DIR}" "${TARBALL_NAME}"
    rm -rf "${TARBALL_DIR}"
    
    # Copy spec file (rename from .rpkg to .spec for rpmbuild)
    cp packaging/rpm/listen.rpkg ~/rpmbuild/SPECS/listen.spec
    
    # Build the RPM
    log_info "Running rpmbuild..."
    rpmbuild -bb ~/rpmbuild/SPECS/listen.spec 2>&1 | tee dist/rpm-build.log
    
    # Copy built RPM to dist/
    cp ~/rpmbuild/RPMS/x86_64/${APP_NAME}*.rpm dist/ 2>/dev/null || true
    
    RPM_FILE=$(ls dist/${APP_NAME}*.rpm 2>/dev/null | head -1)
    
    if [ -n "${RPM_FILE}" ]; then
        log_success ".rpm package built: ${RPM_FILE}"
        echo ""
        echo "To install:"
        echo "  sudo dnf install ${RPM_FILE}"
        echo "Or:"
        echo "  sudo rpm -i ${RPM_FILE}"
    else
        log_error "Failed to build .rpm package. Check dist/rpm-build.log for details."
        return 1
    fi
}

# ============================================================
# CLEAN
# ============================================================

clean_build() {
    log_info "Cleaning build artifacts..."
    
    cd "${SCRIPT_DIR}"
    
    # Clean Debian build artifacts
    rm -rf debian/.debhelper
    rm -rf debian/${APP_NAME}
    rm -f debian/${APP_NAME}.debhelper.log
    rm -f debian/${APP_NAME}.substvars
    rm -f debian/files
    rm -f debian/debhelper-build-stamp
    
    # Clean dist directory
    rm -rf dist
    
    # Clean parent directory artifacts
    rm -f ../${APP_NAME}_*.deb 2>/dev/null || true
    rm -f ../${APP_NAME}_*.buildinfo 2>/dev/null || true
    rm -f ../${APP_NAME}_*.changes 2>/dev/null || true
    
    log_success "Clean complete"
}

# ============================================================
# MAIN
# ============================================================

main() {
    print_banner
    
    if [ "$CLEAN" = true ]; then
        clean_build
    fi
    
    if [ "$DEB_ONLY" = true ]; then
        build_deb
    elif [ "$RPM_ONLY" = true ]; then
        build_rpm
    else
        # Build both
        log_info "Building both .deb and .rpm packages..."
        echo ""
        
        build_deb || log_warn "Skipping .deb build due to errors"
        echo ""
        build_rpm || log_warn "Skipping .rpm build due to errors"
    fi
    
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║         Package Build Complete!           ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════╝${NC}"
    echo ""
    echo "Packages are in the dist/ directory."
}

main
