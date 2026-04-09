# bithub

The missing friendly interface for [BitNet](https://github.com/microsoft/BitNet) inference. Think of it as **Ollama for 1-bit LLMs**.

BitNet models are incredibly efficient — a 2B parameter model fits in ~800MB of RAM and runs fast on a plain CPU. But there's no easy way to download, manage, and serve them. **bithub** fixes that.

## What it does

```bash
bithub setup                # One-time: build the inference engine
bithub pull 2B-4T           # Download a BitNet model from HuggingFace
bithub models               # See all available models
bithub list                 # See what's installed
bithub serve 2B-4T          # Start an OpenAI-compatible API server
bithub run 2B-4T            # Chat in your terminal
bithub rm 2B-4T             # Remove a model
bithub status               # Check engine and model state
```

Once the server is running, any app that speaks the OpenAI API can connect — Open WebUI, Cursor, your own scripts:

```python
import openai
client = openai.OpenAI(base_url="http://localhost:8080/v1", api_key="not-needed")
response = client.chat.completions.create(
    model="2B-4T",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## Available Models

| Name | Parameters | Size | Description |
|---|---|---|---|
| **2B-4T** | 2.4B | ~1.8 GB | Microsoft's official BitNet, trained on 4T tokens |
| **700M** | 0.7B | ~500 MB | Community 700M model — great for testing |
| **3B** | 3.3B | ~2.5 GB | Community 3.3B model |
| **8B** | 8.0B | ~5 GB | Llama3 architecture in 1.58-bit |
| **falcon3-1B** | 1B | ~700 MB | Falcon3 1B instruction-tuned |
| **falcon3-3B** | 3B | ~2 GB | Falcon3 3B instruction-tuned |
| **falcon3-7B** | 7B | ~4.5 GB | Falcon3 7B instruction-tuned |
| **falcon3-10B** | 10B | ~6.5 GB | Falcon3 10B instruction-tuned |

## Why bithub?

| | Ollama | bithub |
|---|---|---|
| Engine | llama.cpp | bitnet.cpp |
| Model weights | 4-bit / 8-bit quantized | Native 1.58-bit (ternary) |
| RAM for 2B model | ~2-4 GB | ~800 MB |
| Speed on CPU | Good | 2-6x faster |
| Energy usage | Normal | 55-82% less |
| Model ecosystem | Thousands of models | Growing (~10 models) |

## API Endpoints

When you run `bithub serve`, you get a full OpenAI-compatible API:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/v1/chat/completions` | Chat completion (streaming + non-streaming) |
| `GET` | `/v1/models` | List available models |
| `GET` | `/health` | Server health check |

This means bithub works out of the box with Open WebUI, Cursor, Continue, and any tool that supports custom OpenAI endpoints.

## Requirements

- Python >= 3.9
- cmake >= 3.22
- clang >= 18
- Git

## Installation

### Quick Install (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/sagarjhaa/bithub/main/install.sh | bash
```

This installs the `bithub` CLI and downloads pre-built bitnet.cpp binaries for your platform.

### pip

```bash
pip install bithub
bithub setup  # builds bitnet.cpp (requires cmake + clang)
```

### Docker

```bash
# Pull a model and serve it
docker run -p 8080:8080 -v ~/.bithub:/root/.bithub ghcr.io/sagarjhaa/bithub pull 2B-4T
docker run -p 8080:8080 -v ~/.bithub:/root/.bithub ghcr.io/sagarjhaa/bithub serve 2B-4T
```

### From Source

```bash
git clone https://github.com/sagarjhaa/bithub.git
cd bithub
pip install -e ".[dev]"
bithub setup
```

## Quick Start

```bash
# 1. Build the inference engine (one-time)
bithub setup

# 2. Download a model
bithub pull 2B-4T

# 3. Start the server
bithub serve 2B-4T

# Or chat directly in terminal
bithub run 2B-4T
```

## Roadmap

- [x] Phase 1: Project structure and CLI skeleton
- [x] Phase 2: Model downloader, builder, and engine management
- [x] Phase 3: OpenAI-compatible API server
- [ ] Phase 4: Terminal chat UX, progress bars, polish

## Contributing

This project is in early development and contributions are very welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — see [LICENSE](LICENSE) for details.

## Acknowledgements

- [Microsoft BitNet](https://github.com/microsoft/BitNet) — the inference engine this project wraps
- [Ollama](https://github.com/ollama/ollama) — the UX inspiration
- [llama.cpp](https://github.com/ggerganov/llama.cpp) — the foundation BitNet is built on
