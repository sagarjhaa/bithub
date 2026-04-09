#!/usr/bin/env bash
set -euo pipefail

# Build bitnet.cpp from source.
# Usage: ./scripts/build-bitnet.sh [TARGET_DIR]
# TARGET_DIR defaults to ~/.bithub/bitnet.cpp
#
# Environment variables:
#   CC/CXX                       - Override compiler (default: clang/clang++)
#   BITNET_SKIP_MODEL_DOWNLOAD   - Set to "1" to skip model download (CI builds)
#   NPROC                        - Override parallel build jobs

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

# Patch setup_env.py if needed
if [ -f "setup_env.py" ]; then
    # 1. Swap compiler if CC is set
    if [ -n "${CC:-}" ]; then
        echo "    Patching compiler to CC=$CC CXX=${CXX:-${CC}++}"
        sed -i.bak \
            -e "s|-DCMAKE_C_COMPILER=clang|-DCMAKE_C_COMPILER=${CC}|g" \
            -e "s|-DCMAKE_CXX_COMPILER=clang++|-DCMAKE_CXX_COMPILER=${CXX:-${CC}++}|g" \
            setup_env.py
    fi

    # 2. Suppress upstream const-correctness error in bitnet.cpp
    #    The code has: int8_t *y_col = y + ... (where y is const int8_t*)
    #    clang treats this as a hard error. gcc with -fpermissive downgrades it.
    echo "    Patching cmake flags for permissive compilation"
    if [ "${CC:-clang}" = "gcc" ]; then
        EXTRA_FLAGS="-fpermissive"
    else
        EXTRA_FLAGS="-Wno-incompatible-pointer-types-discards-qualifiers"
    fi
    sed -i.bak3 \
        "s|\"-DCMAKE_CXX_COMPILER=|\"-DCMAKE_CXX_FLAGS=${EXTRA_FLAGS}\", \"-DCMAKE_C_FLAGS=${EXTRA_FLAGS}\", \"-DCMAKE_CXX_COMPILER=|" \
        setup_env.py

    # 2. Skip model download in CI (we only need binaries, not weights)
    if [ "${BITNET_SKIP_MODEL_DOWNLOAD:-}" = "1" ]; then
        echo "    Patching to skip model download (BITNET_SKIP_MODEL_DOWNLOAD=1)"
        sed -i.bak2 \
            's/def prepare_model():/def prepare_model():\n    import os\n    if os.getenv("BITNET_SKIP_MODEL_DOWNLOAD") == "1":\n        return/' \
            setup_env.py
    fi
fi

# Build
if [ -f "setup_env.py" ]; then
    echo "    Running setup_env.py..."
    python3 setup_env.py \
        --hf-repo 1bitLLM/bitnet_b1_58-3B \
        -q i2_s
else
    git submodule update --init --recursive 2>/dev/null || true
    mkdir -p build && cd build
    cmake .. -DCMAKE_BUILD_TYPE=Release
    cmake --build . --config Release -j "$NPROC"
fi

# Find binaries
echo "==> Searching for binaries..."
FOUND=0
mkdir -p "$TARGET_DIR/build/bin"

for dir in "$TARGET_DIR/build/bin" "$TARGET_DIR/bin"; do
    for name in llama-server llama-cli; do
        if [ -f "$dir/$name" ]; then
            echo "    Found: $dir/$name"
            [ "$dir" != "$TARGET_DIR/build/bin" ] && cp "$dir/$name" "$TARGET_DIR/build/bin/"
            FOUND=1
        fi
    done
done

if [ "$FOUND" -eq 0 ]; then
    echo "ERROR: No binaries found after build."
    exit 1
fi

echo "==> bitnet.cpp built successfully in $TARGET_DIR"
