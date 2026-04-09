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
    echo "${url:-}"
}

build_from_source() {
    info "Building bitnet.cpp from source (this takes a few minutes)..."

    # Check build dependencies
    local missing=""
    command -v git &>/dev/null || missing="$missing git"
    command -v cmake &>/dev/null || missing="$missing cmake"

    if [ -n "$missing" ]; then
        echo ""
        warn "Missing build tools:$missing"
        echo "  Install them first:"
        echo "    macOS:  brew install cmake git"
        echo "    Ubuntu: sudo apt install cmake clang git build-essential"
        echo ""
        echo "  Then run: bithub setup"
        return 1
    fi

    # Download and run the build script
    local build_script
    build_script="$(mktemp)"
    curl -fsSL "https://raw.githubusercontent.com/sagarjhaa/bithub/main/scripts/build-bitnet.sh" \
        -o "$build_script"
    chmod +x "$build_script"

    export BITNET_SKIP_MODEL_DOWNLOAD=1
    if bash "$build_script" "${BITHUB_HOME}/bitnet.cpp"; then
        info "bitnet.cpp built successfully!"
        rm -f "$build_script"
        return 0
    else
        rm -f "$build_script"
        warn "Build failed. You can try manually: bithub setup"
        return 1
    fi
}

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

    # Try downloading pre-built binaries
    local download_url
    download_url="$(get_download_url "$platform")"

    if [ -n "$download_url" ]; then
        info "Downloading pre-built binaries for $platform..."
        info "From: $download_url"

        local tmpdir
        tmpdir="$(mktemp -d)"
        trap 'rm -rf "${tmpdir:-}"' EXIT

        if curl -fSL "$download_url" -o "$tmpdir/bithub-binaries.tar.gz" 2>/dev/null; then
            local prebuilt_dir="${BITHUB_HOME}/prebuilt"
            mkdir -p "$prebuilt_dir"
            tar -xzf "$tmpdir/bithub-binaries.tar.gz" -C "$prebuilt_dir"
            chmod +x "$prebuilt_dir"/*
            info "Pre-built binaries installed to $prebuilt_dir"
        else
            warn "Binary download failed. Falling back to build from source..."
            build_from_source || true
        fi
    else
        # No pre-built binary for this platform — build from source
        warn "No pre-built binary available for $platform."
        info "Attempting to build from source..."
        build_from_source || true
    fi

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
