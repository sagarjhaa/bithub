# bitnet-hub

**Ollama for 1-bit LLMs.** A CLI tool that downloads, builds, and serves BitNet models on CPU using Microsoft's bitnet.cpp engine.

## Project Status

All 4 phases are complete and committed:

- **Phase 1** ✅ — Project skeleton, CLI commands, model registry (8 models)
- **Phase 2** ✅ — HuggingFace downloader, bitnet.cpp builder, serve/run commands
- **Phase 3** ✅ — OpenAI-compatible API via FastAPI (`/v1/chat/completions`, `/v1/models`)
- **Phase 4** ✅ — Polish: auto-setup prompts, smart thread detection, fuzzy model suggestions, rich status panel

## What Needs Testing / Doing Next

- **Real-world testing**: `bitnet-hub setup` → `pull 2B-4T` → `serve 2B-4T` has never been tested end-to-end on a real machine. The builder and server were written from docs, not tested against actual bitnet.cpp binaries. Binary paths and CLI flags may need adjustment.
- **Validate registry**: Confirm all 8 HuggingFace repo IDs in `registry.json` still exist and have GGUF files.
- **Push to GitHub**: There are unpushed commits. Run `git push` to sync with https://github.com/sagarjhaa/bithub.git

## Architecture

```
bitnet_hub/
├── cli.py           # Click CLI — all user-facing commands
├── config.py        # Paths (~/.bitnet-hub/), defaults, system detection
├── registry.py      # Loads model catalog from registry.json
├── registry.json    # 8 BitNet models (Microsoft, community, Falcon3)
├── downloader.py    # Pulls GGUF files from HuggingFace via huggingface_hub
├── builder.py       # Clones and compiles bitnet.cpp (one-time setup)
├── server.py        # Starts FastAPI + bitnet.cpp backend, or interactive chat
└── api.py           # OpenAI-compatible endpoints (proxies to llama-server)
```

**Flow:** `registry.json` → `downloader.py` (pull GGUF) → `builder.py` (compile engine) → `server.py` + `api.py` (serve with OpenAI API)

## Key Design Decisions

- Models stored in `~/.bitnet-hub/models/<name>/`
- bitnet.cpp cloned to `~/.bitnet-hub/bitnet.cpp/`
- FastAPI runs on user-facing port (default 8080), llama-server runs on port+1 (8081) as backend
- CLI auto-offers to setup engine and pull models if not ready (no dead-end error messages)
- Thread count auto-detected from CPU cores (half of cores, min 2, max 8)

## Commands

```bash
bitnet-hub setup              # clone + build bitnet.cpp
bitnet-hub pull <model>       # download from HuggingFace
bitnet-hub serve <model>      # OpenAI-compatible API server
bitnet-hub run <model>        # interactive terminal chat
bitnet-hub models             # show registry with install status
bitnet-hub list               # show downloaded models
bitnet-hub rm <model>         # remove a model
bitnet-hub status             # system info + engine/model state
```

## Dependencies

click, rich, huggingface-hub, fastapi, uvicorn, httpx

## Git Convention

Commits are organized by phase with descriptive messages. Co-authored with Claude.
