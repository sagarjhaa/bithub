#!/usr/bin/env bash
set -euo pipefail

# Build bitnet.cpp from source.
# Usage: ./scripts/build-bitnet.sh [TARGET_DIR]
# TARGET_DIR defaults to ~/.bithub/bitnet.cpp

TARGET_DIR="${1:-${BITHUB_HOME:-$HOME/.bithub}/bitnet.cpp}"
REPO_URL="https://github.com/microsoft/BitNet.git"
NPROC="${NPROC:-$(nproc 2>/dev/null || sysctl -n hw.logicalcpu 2>/dev/null || echo 4)}"

echo "==> Cloning bitnet.cpp..."
if [ -d "$TARGET_DIR/.git" ]; then
    echo "    Directory exists, updating..."
    git -C "$TARGET_DIR" pull --ff-only || true
    git -C "$TARGET_DIR" submodule update --init --recursive || true
else
    git clone --recursive "$REPO_URL" "$TARGET_DIR"
fi

echo "==> Building bitnet.cpp with $NPROC threads..."
cd "$TARGET_DIR"

# setup_env.py hardcodes -DCMAKE_C_COMPILER=clang, but clang on Linux
# has a const-correctness error in bitnet.cpp's code. Patch it to respect
# CC/CXX env vars if set.
if [ -f "setup_env.py" ] && [ -n "${CC:-}" ]; then
    echo "    Patching setup_env.py to use CC=$CC CXX=${CXX:-$CC}"
    sed -i.bak \
        -e "s|-DCMAKE_C_COMPILER=clang|-DCMAKE_C_COMPILER=${CC}|g" \
        -e "s|-DCMAKE_CXX_COMPILER=clang++|-DCMAKE_CXX_COMPILER=${CXX:-${CC}++}|g" \
        setup_env.py
fi

# bitnet.cpp's setup_env.py is the canonical build method
# It compiles first, then downloads a model. We only need the binaries,
# so we tolerate failure IF binaries were already produced.
if [ -f "setup_env.py" ]; then
    echo "    Using setup_env.py..."
    python3 setup_env.py \
        --hf-repo 1bitLLM/bitnet_b1_58-3B \
        -q i2_s \
        || echo "    setup_env.py exited with error (may be OK if binaries exist)"
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
    echo "    Searching for binaries..."
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
    exit 1
fi

echo "==> bitnet.cpp built successfully in $TARGET_DIR"
