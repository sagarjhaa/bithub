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
    git -C "$TARGET_DIR" submodule update --init --recursive || true
else
    git clone --recursive --depth 1 "$REPO_URL" "$TARGET_DIR"
fi

echo "==> Building bitnet.cpp with $NPROC threads..."
cd "$TARGET_DIR"

# bitnet.cpp requires setup_env.py which handles cmake configuration
# It needs a model repo to configure against, but we only need the binaries
if [ -f "setup_env.py" ]; then
    echo "    Using setup_env.py (preferred build method)..."
    # setup_env.py downloads a model and builds — we need it for the cmake config
    python3 setup_env.py \
        --hf-repo 1bitLLM/bitnet_b1_58-3B \
        -q i2_s \
        || {
        echo "    setup_env.py failed, trying manual cmake build..."
        # Manual build requires submodules to be present
        git submodule update --init --recursive 2>/dev/null || true
        mkdir -p build && cd build
        cmake .. \
            -DCMAKE_BUILD_TYPE=Release \
            -DGGML_OPENMP=ON \
            2>/dev/null || cmake .. -DCMAKE_BUILD_TYPE=Release
        cmake --build . --config Release -j "$NPROC"
    }
else
    # No setup_env.py — try direct cmake
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
    echo "WARNING: No binaries found in standard locations. Searching..."
    # Some builds put binaries elsewhere
    FOUND_BIN=$(find "$TARGET_DIR" -name "llama-server" -o -name "llama-cli" 2>/dev/null | head -1)
    if [ -n "$FOUND_BIN" ]; then
        echo "==> Found: $FOUND_BIN"
        # Copy to expected location
        mkdir -p "$TARGET_DIR/build/bin"
        find "$TARGET_DIR" \( -name "llama-server" -o -name "llama-cli" \) \
            -exec cp {} "$TARGET_DIR/build/bin/" \; 2>/dev/null
        FOUND=1
    fi
fi

if [ "$FOUND" -eq 0 ]; then
    echo "ERROR: No binaries found after build. Check build output above."
    exit 1
fi

echo "==> bitnet.cpp built successfully in $TARGET_DIR"
