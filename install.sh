#!/usr/bin/env bash
set -euo pipefail

# bithub installer — downloads bithub + pre-built bitnet.cpp binaries
# Usage: curl -fsSL https://raw.githubusercontent.com/sagarjhaa/bithub/main/install.sh | bash

VERSION="${BITHUB_VERSION:-latest}"
REPO="sagarjhaa/bithub"
BITHUB_HOME="${BITHUB_HOME:-$HOME/.bithub}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}==>${NC} $*"; }
warn()  { echo -e "${YELLOW}WARNING:${NC} $*"; }
error() { echo -e "${RED}ERROR:${NC} $*" >&2; exit 1; }

# Detect OS and architecture
detect_platform() {
    local os arch
    os="$(uname -s | tr '[:upper:]' '[:lower:]')"
    arch="$(uname -m)"

    case "$os" in
        linux)  os="linux" ;;
        darwin) os="macos" ;;
        *)      error "Unsupported OS: $os" ;;
    esac

    case "$arch" in
        x86_64|amd64)  arch="x86_64" ;;
        arm64|aarch64) arch="arm64" ;;
        *)             error "Unsupported architecture: $arch" ;;
    esac

    echo "${os}-${arch}"
}

# Get download URL for latest release
get_download_url() {
    local platform="$1"
    local api_url="https://api.github.com/repos/${REPO}/releases"

    if [ "$VERSION" = "latest" ]; then
        api_url="${api_url}/latest"
    else
        api_url="${api_url}/tags/v${VERSION}"
    fi

    local url
    url=$(curl -fsSL "$api_url" | grep "browser_download_url.*${platform}" | head -1 | cut -d '"' -f 4)

    if [ -z "$url" ]; then
        error "No release found for platform: ${platform}. Check https://github.com/${REPO}/releases"
    fi

    echo "$url"
}

# Main install flow
main() {
    info "Installing bithub..."

    local platform
    platform="$(detect_platform)"
    info "Detected platform: $platform"

    # Check for Python 3.9+
    if ! command -v python3 &>/dev/null; then
        error "Python 3 is required. Install it first: https://python.org"
    fi

    local py_version
    py_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    local py_major py_minor
    py_major=$(echo "$py_version" | cut -d. -f1)
    py_minor=$(echo "$py_version" | cut -d. -f2)
    if [ "$py_major" -lt 3 ] || { [ "$py_major" -eq 3 ] && [ "$py_minor" -lt 9 ]; }; then
        error "Python 3.9+ required, found $py_version"
    fi
    info "Python $py_version OK"

    # Install bithub via pip
    info "Installing bithub Python package..."
    python3 -m pip install --user bithub 2>/dev/null || \
        python3 -m pip install bithub || \
        error "Failed to install bithub via pip"

    # Download pre-built bitnet.cpp binaries
    info "Downloading pre-built bitnet.cpp binaries for $platform..."
    local download_url
    download_url="$(get_download_url "$platform")"
    info "Downloading from: $download_url"

    local tmpdir
    tmpdir="$(mktemp -d)"
    trap 'rm -rf "${tmpdir:-}"' EXIT

    curl -fSL "$download_url" -o "$tmpdir/bithub-binaries.tar.gz"

    # Extract binaries to prebuilt dir
    local prebuilt_dir="${BITHUB_HOME}/prebuilt"
    mkdir -p "$prebuilt_dir"
    tar -xzf "$tmpdir/bithub-binaries.tar.gz" -C "$prebuilt_dir"
    chmod +x "$prebuilt_dir"/*

    info "Binaries installed to $prebuilt_dir"

    # Verify
    if command -v bithub &>/dev/null; then
        info "bithub $(bithub --version 2>/dev/null || echo '') installed successfully!"
    else
        warn "bithub installed but not in PATH."
        warn "Add to your shell profile: export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi

    echo ""
    info "Quick start:"
    echo "  bithub pull 2B-4T       # Download a model (~1.8GB)"
    echo "  bithub serve 2B-4T      # Start OpenAI-compatible API"
    echo "  bithub run 2B-4T        # Interactive chat"
    echo ""
    info "Docs: https://github.com/${REPO}"
}

main "$@"
