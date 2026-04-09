# Contributing to bitnet-hub

Thanks for your interest in contributing! This project is in early development and help is very welcome.

## Getting Started

```bash
git clone https://github.com/sagarjhaa/bithub.git
cd bithub
pip install -e .
```

## Project Structure

```
bithub/
├── bitnet_hub/
│   ├── __init__.py          # Package version
│   ├── cli.py               # Click CLI commands
│   ├── config.py            # Paths, defaults, system detection
│   ├── registry.py          # Model catalog loader
│   ├── registry.json        # Known BitNet models
│   ├── downloader.py        # HuggingFace model downloader
│   ├── builder.py           # bitnet.cpp clone and build
│   ├── server.py            # Server launcher (FastAPI + backend)
│   └── api.py               # OpenAI-compatible API endpoints
├── pyproject.toml           # Package config and dependencies
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

## Architecture

bitnet-hub is a CLI wrapper around Microsoft's bitnet.cpp engine. The flow is:

1. **Registry** (`registry.json`) — catalog of known BitNet models on HuggingFace
2. **Downloader** (`downloader.py`) — pulls GGUF files from HuggingFace via `huggingface_hub`
3. **Builder** (`builder.py`) — clones and compiles bitnet.cpp (one-time setup)
4. **Server** (`server.py` + `api.py`) — starts bitnet.cpp as a backend and wraps it with a FastAPI server that speaks the OpenAI protocol

## Areas Where Help is Needed

- **Testing on different platforms** — macOS (Apple Silicon + Intel), Linux, Windows/WSL
- **Model validation** — confirming all registry entries point to valid HuggingFace repos
- **New models** — adding new BitNet-compatible models to `registry.json`
- **Docker support** — packaging bitnet-hub with pre-built binaries
- **Pre-built binaries** — shipping compiled bitnet.cpp so users skip the build step

## Guidelines

- Keep it simple — this should be easy for anyone to install and use
- Follow the existing code style (Black formatting, type hints)
- Add comments explaining *why*, not just *what*
- Test your changes locally before submitting a PR
- For new models, verify the HuggingFace repo exists and has a GGUF file

## Adding a New Model

1. Find the model on HuggingFace (must have a `.gguf` file)
2. Add an entry to `bitnet_hub/registry.json`:
   ```json
   "short-name": {
     "name": "Full-Model-Name",
     "hf_repo": "org/model-name",
     "parameters": "2B",
     "quant_type": "i2_s",
     "description": "Short description",
     "size_mb": 1800
   }
   ```
3. Test with `bitnet-hub pull short-name`

## Submitting a PR

1. Fork the repo
2. Create a branch (`git checkout -b feature/my-change`)
3. Make your changes
4. Test locally (`pip install -e . && bitnet-hub models`)
5. Submit a PR with a clear description of what and why

Thank you!
