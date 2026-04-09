# bithub

**Ollama for 1-bit LLMs.** A CLI tool that downloads, builds, and serves BitNet models on CPU using Microsoft's bitnet.cpp engine.

## Project Status

**Phase A (Bulletproof Foundation)** is complete. Next up: Phase C (Distribution) then Phase B (Feature Expansion).

- **Phase 1** ✅ — Project skeleton, CLI commands, model registry (8 models)
- **Phase 2** ✅ — HuggingFace downloader, bitnet.cpp builder, serve/run commands
- **Phase 3** ✅ — OpenAI-compatible API via FastAPI (`/v1/chat/completions`, `/v1/models`)
- **Phase 4** ✅ — Polish: auto-setup prompts, smart thread detection, fuzzy model suggestions, rich status panel
- **Phase A** ✅ — Rename to bithub, test suite (105 tests, 70% coverage), CI/CD, TOML config, structured logging, disk space checks, SHA256 integrity, error hardening

## What Needs Testing / Doing Next

- **Real-world testing**: `bithub setup` → `pull 2B-4T` → `serve 2B-4T` has never been tested end-to-end on a real machine.
- **Phase C (Distribution)**: Pre-built binaries, Homebrew formula, Docker image, install script
- **Phase B (Features)**: Polished REPL, direct HF pull, multi-model serving, web dashboard, benchmarks
- **Push to GitHub**: Run `git push` to sync with https://github.com/sagarjhaa/bithub.git

## Architecture

```
bithub/
├── cli.py              # Click CLI — all user-facing commands (--debug, --verbose)
├── config.py           # Paths (~/.bithub/), defaults, TOML config loading
├── registry.py         # Loads model catalog from registry.json with validation
├── registry.json       # 8 BitNet models (Microsoft, community, Falcon3)
├── downloader.py       # Pulls GGUF files from HuggingFace, disk space checks, SHA256
├── builder.py          # Clones and compiles bitnet.cpp (one-time setup)
├── server.py           # Starts FastAPI + bitnet.cpp backend, or interactive chat
├── api.py              # OpenAI-compatible endpoints with request validation
└── logging_setup.py    # Structured logging with file rotation
tests/
├── conftest.py         # Shared fixtures
├── test_registry.py    # 7 tests
├── test_config.py      # 11 tests
├── test_downloader.py  # 20 tests
├── test_builder.py     # 15 tests
├── test_server.py      # 8 tests
├── test_api.py         # 11 tests
└── test_cli.py         # 33 tests
.github/workflows/
└── ci.yml              # GitHub Actions: lint, type check, test (macOS + Linux, Py 3.9/3.11/3.12)
```

**Flow:** `registry.json` → `downloader.py` (pull GGUF) → `builder.py` (compile engine) → `server.py` + `api.py` (serve with OpenAI API)

## Key Design Decisions

- Models stored in `~/.bithub/models/<name>/`
- bitnet.cpp cloned to `~/.bithub/bitnet.cpp/`
- Config file at `~/.bithub/config.toml` (TOML, optional)
- Log file at `~/.bithub/bithub.log` (rotated, 10MB max)
- FastAPI runs on user-facing port (default 8080), llama-server runs on port+1 (8081) as backend
- CLI auto-offers to setup engine and pull models if not ready
- Thread count auto-detected from CPU cores (half of cores, min 2, max 8)
- SHA256 checksums saved after model download for integrity verification
- Disk space checked before downloads (requires model size + 1GB buffer)

## Commands

```bash
bithub setup              # clone + build bitnet.cpp
bithub pull <model>       # download from HuggingFace
bithub serve <model>      # OpenAI-compatible API server
bithub run <model>        # interactive terminal chat
bithub models             # show registry with install status
bithub list               # show downloaded models
bithub rm <model>         # remove a model
bithub status             # system info + engine/model state
```

## Dependencies

click, rich, huggingface-hub, fastapi, uvicorn, httpx, tomli (Python <3.11)

Dev: pytest, pytest-asyncio, pytest-cov, mypy, ruff

## Dev Notes

- Python 3.9+. Use `Optional[X]` not `X | None` for type hints.
- Use `/usr/bin/python3` on this machine (system Python 3.9.6). Default `python3` is 3.8.
- Run tests: `/usr/bin/python3 -m pytest tests/ -v`
- Run with coverage: `/usr/bin/python3 -m pytest --cov=bithub --cov-report=term-missing`

## Git Convention

Commits are organized by phase with descriptive messages. Co-authored with Claude.
