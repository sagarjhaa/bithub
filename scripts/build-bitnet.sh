#!/usr/bin/env bash
set -euo pipefail

# Build bitnet.cpp from source.
# Usage: ./scripts/build-bitnet.sh [TARGET_DIR]
#
# Environment variables:
#   CC/CXX                       - Override compiler (default: clang/clang++)
#   BITNET_SKIP_MODEL_DOWNLOAD   - Set to "1" to skip model download (CI builds)
#   NPROC                        - Override parallel build jobs

TARGET_DIR="${1:-${BITHUB_HOME:-$HOME/.bithub}/bitnet.cpp}"

if [[ "$TARGET_DIR" != /* ]]; then
    TARGET_DIR="$PWD/$TARGET_DIR"
fi

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

# Patch setup_env.py if present
if [ -f "setup_env.py" ]; then
    # Swap compiler if CC is set
    if [ -n "${CC:-}" ]; then
        echo "    Patching compiler to CC=$CC CXX=${CXX:-${CC}++}"
        sed -i.bak \
            -e "s|-DCMAKE_C_COMPILER=clang|-DCMAKE_C_COMPILER=${CC}|g" \
            -e "s|-DCMAKE_CXX_COMPILER=clang++|-DCMAKE_CXX_COMPILER=${CXX:-${CC}++}|g" \
            setup_env.py
    fi

    # Add permissive flags to suppress upstream const errors
    if [ "${CC:-clang}" = "gcc" ]; then
        EXTRA_FLAGS="-fpermissive"
    else
        EXTRA_FLAGS="-Wno-incompatible-pointer-types-discards-qualifiers"
    fi

    ARCH_CMAKE_FLAG=""
    if [ "$(uname -s)" = "Darwin" ] && [ "${BITNET_TARGET_ARCH:-}" = "x86_64" ]; then
        ARCH_CMAKE_FLAG="\"-DCMAKE_OSX_ARCHITECTURES=x86_64\", "
        sed -i.bak4 's/ARCH_ALIAS\[platform.machine()\]/"x86_64"/g' setup_env.py
    fi

    echo "    Patching cmake flags: ${EXTRA_FLAGS}"
    sed -i.bak3 \
        "s|\"-DCMAKE_CXX_COMPILER=|${ARCH_CMAKE_FLAG}\"-DCMAKE_CXX_FLAGS=${EXTRA_FLAGS}\", \"-DCMAKE_C_FLAGS=${EXTRA_FLAGS}\", \"-DCMAKE_CXX_COMPILER=|" \
        setup_env.py

    # Skip model download in CI
    if [ "${BITNET_SKIP_MODEL_DOWNLOAD:-}" = "1" ]; then
        echo "    Patching to skip model download"
        sed -i.bak2 \
            's/def prepare_model():/def prepare_model():\n    import os\n    if os.getenv("BITNET_SKIP_MODEL_DOWNLOAD") == "1":\n        return/' \
            setup_env.py
    fi

    # Show the patched cmake line for verification
    echo "    Patched cmake command:"
    grep "CMAKE_C_COMPILER" setup_env.py | head -1
fi

# Build
if [ -f "setup_env.py" ]; then
    echo "    Running setup_env.py..."
    python3 setup_env.py \
        --hf-repo 1bitLLM/bitnet_b1_58-3B \
        -q i2_s \
        || true  # Don't fail — check binaries below
fi

# Always show build logs (setup_env.py redirects cmake output to files)
for logfile in logs/generate_build_files.log logs/compile.log logs/download_model.log; do
    if [ -f "$logfile" ]; then
        echo "==> $logfile (last 20 lines):"
        tail -20 "$logfile"
    fi
done

# Show what exists
echo "==> Directory listing:"
ls -la "$TARGET_DIR/build/bin/" 2>/dev/null || echo "    build/bin/ does not exist"
ls -la "$TARGET_DIR/bin/" 2>/dev/null || echo "    bin/ does not exist"

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
