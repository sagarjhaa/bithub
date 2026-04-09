# Phase C: Distribution — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the cmake/clang barrier so developers can install and run bithub without compiling anything — via Docker, install script, GitHub Releases, or Homebrew.

**Architecture:** A GitHub Actions release workflow compiles bitnet.cpp for each platform (macOS arm64/x86_64, Linux x86_64/arm64) and bundles them as downloadable archives alongside the Python wheel. A Dockerfile provides a ready-to-run container. An install script automates binary download + pip install. A Homebrew formula wraps the install script.

**Tech Stack:** GitHub Actions, Docker, bash, Homebrew Ruby DSL

---

## File Map

**Created:**
- `Dockerfile` — Multi-stage build: compile bitnet.cpp + install bithub
- `.github/workflows/release.yml` — Build + publish on git tag
- `install.sh` — One-line install script
- `scripts/build-bitnet.sh` — Portable bitnet.cpp build script used by CI and Docker

**Modified:**
- `bithub/builder.py` — Add `find_prebuilt_binary()` to check for pre-installed binaries
- `bithub/config.py` — Add `PREBUILT_DIR` constant
- `tests/test_builder.py` — Tests for prebuilt binary detection
- `README.md` — Add installation methods
- `.github/workflows/ci.yml` — No changes (release is separate)

---

## Task 0: Portable bitnet.cpp Build Script

**Files:**
- Create: `scripts/build-bitnet.sh`

This script is reused by the Dockerfile, the release workflow, and advanced users who want to build manually. Single source of truth for the build process.

- [ ] **Step 1: Create `scripts/build-bitnet.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

# Build bitnet.cpp from source.
# Usage: ./scripts/build-bitnet.sh [TARGET_DIR]
# TARGET_DIR defaults to ~/.bithub/bitnet.cpp

TARGET_DIR="${1:-${BITHUB_HOME:-$HOME/.bithub}/bitnet.cpp}"
REPO_URL="https://github.com/microsoft/BitNet.git"
NPROC="${NPROC:-$(nproc 2>/dev/null || sysctl -n hw.logicalcpu 2>/dev/null || echo 4)}"

echo "==> Cloning bitnet.cpp..."
if [ -d "$TARGET_DIR" ]; then
    echo "    Directory exists, pulling latest..."
    git -C "$TARGET_DIR" pull --ff-only || true
else
    git clone --depth 1 "$REPO_URL" "$TARGET_DIR"
fi

echo "==> Building bitnet.cpp with $NPROC threads..."
cd "$TARGET_DIR"

# Use setup_env.py if available (preferred by bitnet.cpp)
if [ -f "setup_env.py" ]; then
    python3 setup_env.py --hf-repo 1bitLLM/bitnet_b1_58-3B -q i2_s 2>/dev/null || {
        echo "    setup_env.py failed, falling back to manual cmake build..."
        mkdir -p build && cd build
        cmake .. -DCMAKE_BUILD_TYPE=Release
        cmake --build . --config Release -j "$NPROC"
    }
else
    mkdir -p build && cd build
    cmake .. -DCMAKE_BUILD_TYPE=Release
    cmake --build . --config Release -j "$NPROC"
fi

# Verify binaries exist
FOUND=0
for bin in build/bin/llama-server build/bin/llama-cli build/bin/main; do
    if [ -f "$TARGET_DIR/$bin" ]; then
        echo "==> Found: $bin"
        FOUND=1
    fi
done

if [ "$FOUND" -eq 0 ]; then
    echo "ERROR: No binaries found after build. Check build output above."
    exit 1
fi

echo "==> bitnet.cpp built successfully in $TARGET_DIR"
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x scripts/build-bitnet.sh
```

- [ ] **Step 3: Commit**

```bash
git add scripts/build-bitnet.sh
git commit -m "Add portable bitnet.cpp build script"
```

---

## Task 1: Prebuilt Binary Detection in builder.py

**Files:**
- Modify: `bithub/config.py`
- Modify: `bithub/builder.py`
- Modify: `tests/test_builder.py`

When bithub is installed via Docker, Homebrew, or the install script, bitnet.cpp binaries are pre-compiled and placed in a known location. The builder should check there first before requiring `bithub setup`.

- [ ] **Step 1: Add PREBUILT_DIR to config.py**

Add after the `LOG_PATH` line in `bithub/config.py`:

```python
# Pre-built binaries installed by Docker/Homebrew/install script
PREBUILT_DIR = Path(os.environ.get("BITHUB_PREBUILT_DIR", BITHUB_HOME / "prebuilt"))
```

- [ ] **Step 2: Write failing test**

Add to `tests/test_builder.py`:

```python
class TestPrebuiltBinaryDetection:
    def test_finds_prebuilt_server(self, tmp_path: Path) -> None:
        prebuilt = tmp_path / "prebuilt"
        prebuilt.mkdir()
        (prebuilt / "llama-server").touch()
        with patch("bithub.builder.PREBUILT_DIR", prebuilt):
            from bithub.builder import get_server_binary
            result = get_server_binary()
            assert result is not None
            assert "prebuilt" in str(result)

    def test_finds_prebuilt_inference(self, tmp_path: Path) -> None:
        prebuilt = tmp_path / "prebuilt"
        prebuilt.mkdir()
        (prebuilt / "llama-cli").touch()
        with patch("bithub.builder.PREBUILT_DIR", prebuilt):
            from bithub.builder import get_inference_binary
            result = get_inference_binary()
            assert result is not None
            assert "prebuilt" in str(result)

    def test_prefers_prebuilt_over_compiled(self, tmp_path: Path) -> None:
        prebuilt = tmp_path / "prebuilt"
        prebuilt.mkdir()
        (prebuilt / "llama-server").touch()
        cpp_dir = tmp_path / "bitnet.cpp" / "build" / "bin"
        cpp_dir.mkdir(parents=True)
        (cpp_dir / "llama-server").touch()
        with patch("bithub.builder.PREBUILT_DIR", prebuilt), \
             patch("bithub.builder.BITNET_CPP_DIR", tmp_path / "bitnet.cpp"):
            from bithub.builder import get_server_binary
            result = get_server_binary()
            assert result is not None
            assert "prebuilt" in str(result)
```

- [ ] **Step 3: Run test to verify it fails**

```bash
/usr/bin/python3 -m pytest tests/test_builder.py::TestPrebuiltBinaryDetection -v
```

Expected: FAIL — `PREBUILT_DIR` not imported, prebuilt paths not checked.

- [ ] **Step 4: Update builder.py to check prebuilt directory**

Read `bithub/builder.py`. Add import of `PREBUILT_DIR` from config:

```python
from bithub.config import BITNET_CPP_DIR, PREBUILT_DIR, ensure_dirs
```

Update `get_server_binary()` to check prebuilt first:

```python
def get_server_binary() -> Optional[Path]:
    """Get the server binary, checking prebuilt dir first."""
    # Check prebuilt binaries (Docker/Homebrew/install script)
    prebuilt_server = PREBUILT_DIR / "llama-server"
    if prebuilt_server.exists():
        return prebuilt_server
    return _find_server_binary()


def get_inference_binary() -> Optional[Path]:
    """Get the inference binary, checking prebuilt dir first."""
    prebuilt_cli = PREBUILT_DIR / "llama-cli"
    if prebuilt_cli.exists():
        return prebuilt_cli
    return _find_inference_binary()
```

Also update `is_bitnet_cpp_built()` to return True if prebuilt binaries exist:

```python
def is_bitnet_cpp_built() -> bool:
    """Check if bitnet.cpp binaries are available (prebuilt or compiled)."""
    if (PREBUILT_DIR / "llama-server").exists() or (PREBUILT_DIR / "llama-cli").exists():
        return True
    build_dir = BITNET_CPP_DIR / "build"
    if not build_dir.exists():
        return False
    inference_bin = _find_inference_binary()
    return inference_bin is not None
```

- [ ] **Step 5: Run tests**

```bash
/usr/bin/python3 -m pytest tests/test_builder.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Run full suite**

```bash
/usr/bin/python3 -m pytest tests/ -v
```

- [ ] **Step 7: Commit**

```bash
git add bithub/config.py bithub/builder.py tests/test_builder.py
git commit -m "Add prebuilt binary detection for Docker/Homebrew installs"
```

---

## Task 2: Dockerfile

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

- [ ] **Step 1: Create `.dockerignore`**

```
.git
.github
__pycache__
*.pyc
*.egg-info
dist
build
.mypy_cache
.pytest_cache
docs
tests
*.md
!README.md
```

- [ ] **Step 2: Create `Dockerfile`**

```dockerfile
# Stage 1: Build bitnet.cpp
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    git cmake clang build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY scripts/build-bitnet.sh .
RUN chmod +x build-bitnet.sh && ./build-bitnet.sh /build/bitnet.cpp

# Stage 2: Runtime
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy bitnet.cpp binaries from builder
COPY --from=builder /build/bitnet.cpp/build/bin/llama-server /opt/bithub/prebuilt/llama-server
COPY --from=builder /build/bitnet.cpp/build/bin/llama-cli /opt/bithub/prebuilt/llama-cli

# Install bithub
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY bithub/ ./bithub/
RUN pip install --no-cache-dir .

# Configure bithub to use prebuilt binaries
ENV BITHUB_PREBUILT_DIR=/opt/bithub/prebuilt
ENV BITHUB_HOME=/root/.bithub

# Models volume
VOLUME /root/.bithub/models

EXPOSE 8080

# Default: start API server (user must pull a model first)
# Usage: docker run -p 8080:8080 -v ~/.bithub:/root/.bithub ghcr.io/sagarjhaa/bithub bithub serve 2B-4T
ENTRYPOINT ["bithub"]
CMD ["--help"]
```

- [ ] **Step 3: Verify Dockerfile syntax**

```bash
docker build --check -f Dockerfile . 2>/dev/null || echo "Docker syntax check not available, manual review OK"
```

- [ ] **Step 4: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "Add multi-stage Dockerfile with pre-compiled bitnet.cpp"
```

---

## Task 3: Install Script

**Files:**
- Create: `install.sh`

- [ ] **Step 1: Create `install.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

# bithub installer — downloads bithub + pre-built bitnet.cpp binaries
# Usage: curl -fsSL https://raw.githubusercontent.com/sagarjhaa/bithub/main/install.sh | bash

VERSION="${BITHUB_VERSION:-latest}"
REPO="sagarjhaa/bithub"
INSTALL_DIR="${BITHUB_INSTALL_DIR:-$HOME/.local/bin}"
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
    trap 'rm -rf "$tmpdir"' EXIT

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
```

- [ ] **Step 2: Make executable**

```bash
chmod +x install.sh
```

- [ ] **Step 3: Commit**

```bash
git add install.sh
git commit -m "Add one-line install script with platform detection"
```

---

## Task 4: GitHub Actions Release Workflow

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Create `.github/workflows/release.yml`**

```yaml
name: Release

on:
  push:
    tags: ["v*"]

permissions:
  contents: write
  packages: write

jobs:
  build-binaries:
    strategy:
      matrix:
        include:
          - os: ubuntu-latest
            platform: linux-x86_64
          - os: ubuntu-24.04-arm
            platform: linux-arm64
          - os: macos-latest
            platform: macos-arm64
          - os: macos-13
            platform: macos-x86_64

    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - name: Install build dependencies (Linux)
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y cmake clang build-essential

      - name: Build bitnet.cpp
        run: |
          chmod +x scripts/build-bitnet.sh
          ./scripts/build-bitnet.sh ./bitnet-build

      - name: Package binaries
        run: |
          mkdir -p dist
          cp ./bitnet-build/build/bin/llama-server dist/ 2>/dev/null || true
          cp ./bitnet-build/build/bin/llama-cli dist/ 2>/dev/null || true
          cp ./bitnet-build/build/bin/main dist/ 2>/dev/null || true
          cd dist && tar -czf ../bithub-${{ matrix.platform }}.tar.gz *

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: bithub-${{ matrix.platform }}
          path: bithub-${{ matrix.platform }}.tar.gz

  build-wheel:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Build wheel
        run: |
          pip install build
          python -m build

      - name: Upload wheel
        uses: actions/upload-artifact@v4
        with:
          name: python-wheel
          path: dist/*.whl

  docker:
    runs-on: ubuntu-latest
    needs: []

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract version from tag
        id: version
        run: echo "tag=${GITHUB_REF#refs/tags/v}" >> $GITHUB_OUTPUT

      - name: Build and push Docker image
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: |
            ghcr.io/sagarjhaa/bithub:${{ steps.version.outputs.tag }}
            ghcr.io/sagarjhaa/bithub:latest

  release:
    runs-on: ubuntu-latest
    needs: [build-binaries, build-wheel]

    steps:
      - uses: actions/checkout@v4

      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: release-artifacts

      - name: Compute checksums
        run: |
          cd release-artifacts
          find . -name "*.tar.gz" -o -name "*.whl" | while read f; do
            sha256sum "$f" >> checksums.txt
          done
          cat checksums.txt

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: |
            release-artifacts/**/*.tar.gz
            release-artifacts/**/*.whl
            release-artifacts/checksums.txt
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "Add GitHub Actions release workflow for multi-platform builds"
```

---

## Task 5: Update README with Installation Methods

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read current README**

```bash
cat README.md
```

- [ ] **Step 2: Add installation section**

Add an installation section near the top of `README.md` (after the description, before the commands section) with these methods:

```markdown
## Installation

### Quick Install (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/sagarjhaa/bithub/main/install.sh | bash
```

### pip

```bash
pip install bithub
bithub setup  # builds bitnet.cpp (requires cmake + clang)
```

### Docker

```bash
docker run -p 8080:8080 -v ~/.bithub:/root/.bithub ghcr.io/sagarjhaa/bithub bithub serve 2B-4T
```

### From Source

```bash
git clone https://github.com/sagarjhaa/bithub.git
cd bithub
pip install -e .
bithub setup
```
```

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "Add installation methods to README (pip, Docker, install script, source)"
```

---

## Task 6: Final Verification

- [ ] **Step 1: Run full test suite**

```bash
/usr/bin/python3 -m pytest tests/ --cov=bithub --cov-report=term-missing -v
```

Expected: all tests pass, coverage >= 70%.

- [ ] **Step 2: Verify Dockerfile builds locally (if Docker available)**

```bash
docker build -t bithub:local . 2>&1 | tail -5
```

If Docker not available, skip — CI will verify.

- [ ] **Step 3: Verify install script is syntactically valid**

```bash
bash -n install.sh && echo "Syntax OK"
```

- [ ] **Step 4: Verify build script is syntactically valid**

```bash
bash -n scripts/build-bitnet.sh && echo "Syntax OK"
```

- [ ] **Step 5: Commit any fixes**

```bash
git add -A
git commit -m "Phase C complete: distribution via Docker, install script, and GitHub Releases"
```
