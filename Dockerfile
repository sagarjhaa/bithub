# Stage 1: Build bitnet.cpp
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    git cmake clang build-essential \
    && rm -rf /var/lib/apt/lists/*

# setup_env.py needs huggingface_hub to configure the build
RUN pip install --no-cache-dir huggingface_hub

WORKDIR /build
COPY scripts/build-bitnet.sh .
ENV BITNET_SKIP_MODEL_DOWNLOAD=1
RUN chmod +x build-bitnet.sh && ./build-bitnet.sh /build/bitnet.cpp

# Stage 2: Runtime
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy bitnet.cpp binaries from builder (use wildcard-safe approach)
COPY --from=builder /build/bitnet.cpp/build/bin/ /opt/bithub/prebuilt/

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

# Default: show help (user must pull a model first)
# Usage: docker run -p 8080:8080 -v ~/.bithub:/root/.bithub ghcr.io/sagarjhaa/bithub bithub serve 2B-4T
ENTRYPOINT ["bithub"]
CMD ["--help"]
