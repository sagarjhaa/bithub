#!/usr/bin/env bash
set -euo pipefail

# Build bitnet.cpp from source.
# Usage: ./scripts/build-bitnet.sh [TARGET_DIR]
# TARGET_DIR defaults to ~/.bithub/bitnet.cpp

TARGET_DIR="${1:-${BITHUB_HOME:-$HOME/.bithub}/bitnet.cpp}"
REPO_URL="https://github.com/microsoft/BitNet.git"
# Pin to a known-good tag for reproducible builds
BITNET_REF="${BITNET_REF:-v0.1}"
NPROC="${NPROC:-$(nproc 2>/dev/null || sysctl -n hw.logicalcpu 2>/dev/null || echo 4)}"

echo "==> Cloning bitnet.cpp (ref: $BITNET_REF)..."
if [ -d "$TARGET_DIR/.git" ]; then
    echo "    Directory exists, updating..."
    git -C "$TARGET_DIR" fetch --tags || true
    git -C "$TARGET_DIR" checkout "$BITNET_REF" 2>/dev/null || git -C "$TARGET_DIR" pull --ff-only || true
    git -C "$TARGET_DIR" submodule update --init --recursive || true
else
    git clone --recursive "$REPO_URL" "$TARGET_DIR"
    git -C "$TARGET_DIR" checkout "$BITNET_REF" 2>/dev/null || true
fi

echo "==> Building bitnet.cpp with $NPROC threads..."
cd "$TARGET_DIR"

# bitnet.cpp's setup_env.py is the canonical build method
# It configures cmake properly and generates required headers
if [ -f "setup_env.py" ]; then
    echo "    Using setup_env.py..."
    python3 setup_env.py \
        --hf-repo 1bitLLM/bitnet_b1_58-3B \
        -q i2_s \
        && BUILD_OK=1 || BUILD_OK=0

    if [ "$BUILD_OK" -eq 0 ]; then
        echo "    setup_env.py build failed, trying with gcc..."
        # Some platforms have clang const-correctness issues, try gcc
        export CC=gcc CXX=g++
        python3 setup_env.py \
            --hf-repo 1bitLLM/bitnet_b1_58-3B \
            -q i2_s \
            || {
            echo "    gcc build also failed, trying manual cmake..."
            git submodule update --init --recursive 2>/dev/null || true
            mkdir -p build && cd build
            cmake .. -DCMAKE_BUILD_TYPE=Release 2>/dev/null || cmake ..
            cmake --build . --config Release -j "$NPROC"
        }
    fi
else
    git submodule update --init --recursive 2>/dev/null || true
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
    echo "    Searching for binaries in non-standard locations..."
    FOUND_BIN=$(find "$TARGET_DIR" -type f \( -name "llama-server" -o -name "llama-cli" \) 2>/dev/null | head -1)
    if [ -n "${FOUND_BIN:-}" ]; then
        echo "==> Found: $FOUND_BIN"
        mkdir -p "$TARGET_DIR/build/bin"
        find "$TARGET_DIR" -type f \( -name "llama-server" -o -name "llama-cli" \) \
            -exec cp {} "$TARGET_DIR/build/bin/" \; 2>/dev/null
        FOUND=1
    fi
fi

if [ "$FOUND" -eq 0 ]; then
    echo "ERROR: No binaries found after build."
    echo "This may be a bitnet.cpp compatibility issue."
    echo "Check https://github.com/microsoft/BitNet for build instructions."
    exit 1
fi

echo "==> bitnet.cpp built successfully in $TARGET_DIR"
