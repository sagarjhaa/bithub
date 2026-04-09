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

# setup_env.py hardcodes clang, which has a const-correctness error on Linux.
# Patch: either swap compiler to gcc, or add -Wno-error flags.
if [ -f "setup_env.py" ]; then
    if [ -n "${CC:-}" ]; then
        echo "    Patching setup_env.py to use CC=$CC CXX=${CXX:-${CC}++}"
        sed -i.bak \
            -e "s|-DCMAKE_C_COMPILER=clang|-DCMAKE_C_COMPILER=${CC}|g" \
            -e "s|-DCMAKE_CXX_COMPILER=clang++|-DCMAKE_CXX_COMPILER=${CXX:-${CC}++}|g" \
            setup_env.py
        # Verify patch applied
        if grep -q "CMAKE_C_COMPILER=${CC}" setup_env.py; then
            echo "    Patch verified: using ${CC}"
        else
            echo "    WARNING: Patch may not have applied. Compiler line:"
            grep "CMAKE_C_COMPILER" setup_env.py
        fi
    else
        # Keep clang but suppress the const-correctness error
        echo "    Patching setup_env.py to add -Wno-error flags"
        sed -i.bak \
            's|"-DCMAKE_CXX_COMPILER=clang++"|\"-DCMAKE_CXX_COMPILER=clang++\", \"-DCMAKE_C_FLAGS=-Wno-error=incompatible-pointer-types-discards-qualifiers\", \"-DCMAKE_CXX_FLAGS=-Wno-error=incompatible-pointer-types-discards-qualifiers -Wno-error=incompatible-pointer-types\"|g' \
            setup_env.py
    fi
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
    # Show build logs if they exist (setup_env.py redirects cmake output)
    if [ -f "logs/compile.log" ]; then
        echo "==> Compile log (last 30 lines):"
        tail -30 logs/compile.log
    fi
    if [ -f "logs/download_model.log" ]; then
        echo "==> Download log (last 10 lines):"
        tail -10 logs/download_model.log
    fi
else
    git submodule update --init --recursive 2>/dev/null || true
    mkdir -p build && cd build
    cmake .. -DCMAKE_BUILD_TYPE=Release
    cmake --build . --config Release -j "$NPROC"
fi

# Debug: show what was built
echo "==> Build directory contents:"
ls -la "$TARGET_DIR/build/" 2>/dev/null || echo "  (no build dir)"
ls -la "$TARGET_DIR/build/bin/" 2>/dev/null || echo "  (no build/bin dir)"
echo "==> All executables in target:"
find "$TARGET_DIR" -type f -executable -name "llama*" 2>/dev/null || true
find "$TARGET_DIR" -type f -name "*.exe" 2>/dev/null || true

# Verify binaries exist — check standard locations first, then search
echo "==> Checking for binaries..."
FOUND=0

# Standard locations
for bin in build/bin/llama-server build/bin/llama-cli build/bin/main; do
    if [ -f "$TARGET_DIR/$bin" ]; then
        echo "    Found: $bin"
        FOUND=1
    fi
done

# If not found, do a broad search (setup_env.py may put them elsewhere)
if [ "$FOUND" -eq 0 ]; then
    echo "    Not in standard locations, searching..."
    # List what was actually built
    find "$TARGET_DIR/build" -type f -executable 2>/dev/null | head -20 || true
    # Look for our target binaries anywhere
    for name in llama-server llama-cli main; do
        MATCH=$(find "$TARGET_DIR" -type f -name "$name" 2>/dev/null | head -1 || true)
        if [ -n "$MATCH" ]; then
            echo "    Found: $MATCH"
            mkdir -p "$TARGET_DIR/build/bin"
            cp "$MATCH" "$TARGET_DIR/build/bin/" 2>/dev/null || true
            FOUND=1
        fi
    done
fi

if [ "$FOUND" -eq 0 ]; then
    echo "ERROR: No binaries found after build."
    echo "Contents of build dir:"
    ls -la "$TARGET_DIR/build/" 2>/dev/null || echo "  (no build dir)"
    ls -la "$TARGET_DIR/build/bin/" 2>/dev/null || echo "  (no build/bin dir)"
    exit 1
fi

echo "==> bitnet.cpp built successfully in $TARGET_DIR"
