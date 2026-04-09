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
