# bitnet-hub

The missing friendly interface for [BitNet](https://github.com/microsoft/BitNet) inference. Think of it as **Ollama for 1-bit LLMs**.

BitNet models are incredibly efficient — a 2B parameter model fits in ~800MB of RAM and runs fast on a plain CPU. But there's no easy way to download, manage, and serve them. **bitnet-hub** fixes that.

## What it does

```bash
bitnet-hub pull 2B-4T          # Download a BitNet model from HuggingFace
bitnet-hub list                 # See what's installed
bitnet-hub serve 2B-4T          # Start an OpenAI-compatible API server
bitnet-hub run 2B-4T            # Chat in your terminal
bitnet-hub rm 2B-4T             # Remove a model
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

## Why?

| | Ollama | bitnet-hub |
|---|---|---|
| Engine | llama.cpp | bitnet.cpp |
| Model weights | 4-bit / 8-bit quantized | Native 1.58-bit (ternary) |
| RAM for 2B model | ~2-4 GB | ~800 MB |
| Speed on CPU | Good | 2-6x faster |
| Energy usage | Normal | 55-82% less |
| Model ecosystem | Thousands of models | Growing (currently ~10 models) |

## Roadmap

- [x] Phase 1: Project structure and CLI skeleton
- [ ] Phase 2: Model registry, downloader, and builder
- [ ] Phase 3: OpenAI-compatible API server
- [ ] Phase 4: Terminal chat, model management, polish

## Requirements

- Python >= 3.9
- cmake >= 3.22
- clang >= 18
- conda (recommended)
- Git

## Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/bitnet-hub.git
cd bitnet-hub

# Install in development mode
pip install -e .
```

## Contributing

This project is in early development and contributions are very welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — see [LICENSE](LICENSE) for details.

## Acknowledgements

- [Microsoft BitNet](https://github.com/microsoft/BitNet) — the inference engine this project wraps
- [Ollama](https://github.com/ollama/ollama) — the UX inspiration
- [llama.cpp](https://github.com/ggerganov/llama.cpp) — the foundation BitNet is built on
