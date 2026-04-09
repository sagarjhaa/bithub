# bithub — World-Class Design Spec

**Date:** 2026-04-08
**Status:** Approved
**Goal:** Transform bithub from a working prototype into a world-class CLI tool for running BitNet 1-bit LLMs — the "Ollama for 1-bit models."

**Target user:** Developers and tinkerers. CLI-comfortable, won't tolerate broken builds, but shouldn't need cmake/clang knowledge.

**Execution order:** A (bulletproof foundation) → C (distribution) → B (feature expansion). Ship reliability and reach before features.

---

## 0. Rename: `bitnet_hub` → `bithub`

The package, CLI command, import paths, config directories, and all references rename from `bitnet-hub` / `bitnet_hub` to `bithub`.

| Before | After |
|---|---|
| `bitnet_hub/` (package dir) | `bithub/` |
| `bitnet-hub` (CLI command) | `bithub` |
| `~/.bitnet-hub/` (data dir) | `~/.bithub/` |
| `bitnet-hub` (pyproject.toml name) | `bithub` |
| `from bitnet_hub import ...` | `from bithub import ...` |

Migration: users with existing `~/.bitnet-hub/` data get a one-time prompt to migrate or a symlink.

---

## Phase A — Bulletproof Foundation

Make what exists reliable, tested, and maintainable before adding anything.

### A1. Test Suite

**Framework:** pytest + pytest-asyncio (for API tests) + pytest-cov

**Coverage targets:**
- `registry.py` — load registry, validate schema, handle missing/corrupt JSON
- `config.py` — path resolution, defaults, env var overrides
- `downloader.py` — GGUF discovery, download orchestration, error paths (mock HuggingFace API)
- `builder.py` — prerequisite checks, build orchestration, binary detection (mock subprocess)
- `server.py` — server startup, backend process lifecycle, port conflict handling
- `api.py` — all OpenAI-compatible endpoints, streaming, error responses
- `cli.py` — all 8 commands, flag parsing, auto-setup flow

**Testing approach:**
- Unit tests for pure logic (registry parsing, config resolution, GGUF file selection)
- Integration tests with mocked externals (HuggingFace API, subprocess calls)
- API tests using FastAPI's `TestClient`
- CLI tests using Click's `CliRunner`
- Target: 80%+ line coverage

**Test directory structure:**
```
tests/
├── conftest.py          # shared fixtures (tmp dirs, mock registry, mock models)
├── test_registry.py
├── test_config.py
├── test_downloader.py
├── test_builder.py
├── test_server.py
├── test_api.py
└── test_cli.py
```

### A2. CI/CD Pipeline

**GitHub Actions workflow:** `.github/workflows/ci.yml`

- **Triggers:** push to main, all PRs
- **Matrix:** Python 3.9, 3.11, 3.12 on ubuntu-latest + macos-latest
- **Steps:**
  1. Install dependencies (`pip install -e ".[dev]"`)
  2. Lint with ruff
  3. Type check with mypy (strict mode)
  4. Run pytest with coverage
  5. Fail if coverage < 80%

**Dev dependencies** (added to pyproject.toml `[project.optional-dependencies]`):
```
dev = ["pytest", "pytest-asyncio", "pytest-cov", "mypy", "ruff"]
```

### A3. Configuration File

**Location:** `~/.bithub/config.toml`

**Format:** TOML (stdlib `tomllib` in Python 3.11+, `tomli` backport for 3.9-3.10)

**Supported settings:**
```toml
[server]
port = 8080
threads = 4
host = "127.0.0.1"

[models]
default = "2B-4T"
directory = "~/.bithub/models"

[download]
check_disk_space = true
min_free_gb = 5
```

**Resolution order:** CLI flags > environment variables > config file > built-in defaults.

Config loading added to `config.py`. Each module reads from config rather than hardcoding defaults.

### A4. Structured Logging

**Library:** Python stdlib `logging` with `rich.logging.RichHandler` for terminal, plain formatter for file output.

**Log file:** `~/.bithub/bithub.log` (rotated, max 10MB, 3 backups)

**Levels:**
- CLI commands: INFO
- Downloads/builds: INFO + progress
- Server requests: INFO
- Errors: ERROR with full tracebacks in log file
- Debug flag: `bithub --debug <command>` sets DEBUG level

No log output to terminal by default — only on `--debug` or `--verbose`. Terminal stays clean.

### A5. Disk Space Checks

Before any download:
1. Read expected model size from registry (or HEAD request for direct HF pulls)
2. Check available disk space at target directory via `shutil.disk_usage()`
3. If insufficient: print clear message with required vs available space, abort
4. Configurable minimum free space buffer via `config.toml` (`min_free_gb`, default 5)

### A6. Error Handling Hardening

**Server mode (`server.py`):**
- Catch subprocess crash/exit and report to user with stderr output
- Retry backend startup once on failure
- Health check loop: ping backend every 5s, restart if unresponsive
- Graceful shutdown: SIGTERM → wait 5s → SIGKILL

**Interactive mode (`server.py`):**
- Wrap subprocess in error handler
- If llama-cli crashes, show last stderr lines and suggest `bithub status` for diagnostics
- Handle broken pipe on streaming output

**API (`api.py`):**
- Validate request parameters (temperature 0-2, max_tokens > 0)
- Return proper OpenAI-format error responses (not raw 500s)
- Timeout on backend requests (configurable, default 120s)

### A7. Model Integrity

- After download completes, compute SHA256 of the GGUF file
- Store hash in `~/.bithub/models/<name>/sha256`
- On `bithub serve` / `bithub run`, optionally verify hash (skip by default, `--verify` flag)
- Registry entries gain optional `sha256` field for known-good hashes

---

## Phase B — Feature Expansion

### B1. Polished Interactive REPL (`bithub run`)

Replace raw `llama-cli` passthrough with a custom REPL built on `prompt_toolkit`.

**Features:**
- Markdown rendering in responses (via `rich.markdown`)
- Conversation history (up/down arrows, persisted in `~/.bithub/history`)
- Slash commands:
  - `/clear` — reset conversation
  - `/model` — show current model info
  - `/system <prompt>` — set system prompt
  - `/export` — save conversation to file
  - `/help` — list commands
  - `/quit` — exit
- Token count display per response
- Streaming output with proper line wrapping
- Multiline input support (paste-friendly)

**Architecture:** REPL sends messages to the local API server (same as `bithub serve`), so the interactive mode and API mode use identical inference paths. `bithub run` auto-starts a server in the background if one isn't already running.

**New dependency:** `prompt_toolkit` for readline-style input handling.

### B2. Direct HuggingFace Pull

Extend `bithub pull` to accept arbitrary HuggingFace repos:

```bash
# From curated registry (existing)
bithub pull 2B-4T

# Direct from HuggingFace (new)
bithub pull hf:microsoft/BitNet-b1.58-2B-4T-gguf
```

**Behavior for direct pulls:**
- Download GGUF file(s) from the repo
- Auto-detect model name from repo name (or `--name` flag to override)
- Store in `~/.bithub/models/<name>/` same as registry models
- Show warning: "This model is not in the curated registry. Compatibility not guaranteed."
- Register in a local `custom_models.json` so `bithub models` and `bithub list` show them

### B3. Multi-Model Serving

Allow the API server to load and switch between multiple models.

**Approach:** Model routing via the `model` field in OpenAI API requests.

```bash
# Start server with multiple models
bithub serve 2B-4T falcon3-3B
```

**Architecture:**
- One `llama-server` process per loaded model, each on a unique backend port
- FastAPI router maps `request.model` to the correct backend
- `GET /v1/models` lists all loaded models
- Lazy loading option: `bithub serve --lazy 2B-4T falcon3-3B` — only starts backend when first request arrives for that model
- Memory-aware: show estimated RAM per model, warn if total exceeds system memory

**Limits:** Max models configurable (default 3). Each `llama-server` process consumes RAM proportional to model size. Since BitNet models are 1-bit, memory footprint is much smaller than FP16 models — a 2B model uses ~500MB RAM.

### B4. Web Dashboard

A built-in web UI served at the same port as the API (default `http://localhost:8080`).

**Tech stack:**
- Vanilla HTML/CSS/JS — no build step, no node_modules, no framework
- Served as static files by FastAPI
- Communicates with the same `/v1/` API endpoints
- Single-page app with client-side routing

**Pages:**

1. **Chat** (`/`)
   - Model selector dropdown (populated from `/v1/models`)
   - Chat interface with markdown rendering
   - Streaming responses
   - Conversation history (localStorage)
   - System prompt configuration
   - Parameter controls (temperature, max tokens)

2. **Models** (`/models`)
   - Installed models with status (loaded/available/downloading)
   - Registry browser — browse available models, one-click pull
   - Model cards: parameter count, size, quantization, description
   - Delete model button

3. **Server** (`/server`)
   - Active model(s) and their status
   - Request count, avg latency, tokens/sec
   - Server uptime
   - Thread count, port, config
   - Real-time log viewer (WebSocket stream from server logs)

4. **Settings** (`/settings`)
   - Edit config.toml values from the UI
   - Server port, threads, default model
   - Download settings (disk space threshold)

**Layout:**
- Sidebar navigation (Chat, Models, Server, Settings)
- Dark mode default (with light mode toggle) — matches the terminal-native audience
- Responsive but desktop-first

**Static files location:** `bithub/static/` directory bundled with the package.

**API additions for dashboard:**
- `GET /api/stats` — server metrics (uptime, request count, tokens generated)
- `GET /api/logs` — recent log entries
- `WebSocket /api/logs/stream` — real-time log streaming
- `POST /api/models/pull` — trigger model download (returns progress via SSE)
- `DELETE /api/models/{name}` — delete a model
- `GET /api/config` / `PUT /api/config` — read/write config

### B5. Performance Benchmarks

`bithub bench <model>` command that runs a standard benchmark:

- Prompt: fixed set of prompts (short, medium, long)
- Metrics: tokens/sec (prompt eval + generation), time to first token, total time
- Output: rich table + optional JSON (`--json`)
- Results cached in `~/.bithub/benchmarks/<model>-<date>.json`
- Comparison: `bithub bench --compare 2B-4T falcon3-3B` shows side-by-side

---

## Phase C — Distribution

### C1. Pre-Built Binaries

**GitHub Actions release workflow:** `.github/workflows/release.yml`

- Triggered on git tag `v*`
- Builds on: macOS (arm64 + x86_64), Linux (x86_64, arm64)
- Bundles: Python wheel + pre-compiled `bitnet.cpp` binaries
- Uploads to GitHub Releases as platform-specific archives

**Binary naming:** `bithub-<version>-<os>-<arch>.tar.gz`

Users who install from binary skip the entire `bithub setup` step.

### C2. Homebrew Formula

```ruby
# Formula: bithub
class Bithub < Formula
  desc "Ollama for 1-bit LLMs — run BitNet models locally"
  homepage "https://github.com/sagarjhaa/bithub"
  # ...
end
```

**Installation:** `brew install sagarjhaa/tap/bithub`

Homebrew tap hosted at `github.com/sagarjhaa/homebrew-tap`.

Includes pre-compiled bitnet.cpp for the user's platform — zero build step.

### C3. Docker Image

```dockerfile
FROM python:3.12-slim
# Install bithub + pre-built bitnet.cpp
# Expose port 8080
# Default CMD: bithub serve 2B-4T
```

**Published to:** GitHub Container Registry (`ghcr.io/sagarjhaa/bithub`)

**Usage:**
```bash
docker run -p 8080:8080 ghcr.io/sagarjhaa/bithub
# Models stored in volume: -v ~/.bithub:/root/.bithub
```

### C4. One-Line Install Script

```bash
curl -fsSL https://raw.githubusercontent.com/sagarjhaa/bithub/main/install.sh | bash
```

**Script behavior:**
1. Detect OS and architecture
2. Download appropriate binary from GitHub Releases
3. Install to `~/.local/bin/bithub` (or `/usr/local/bin/` with sudo)
4. Verify checksum
5. Print quick-start instructions

---

## Architecture After All Phases

```
bithub/
├── __init__.py
├── cli.py              # Click CLI — all commands including bench
├── config.py           # Paths, defaults, config.toml loading
├── registry.py         # Model catalog (registry.json + custom_models.json)
├── registry.json       # Curated BitNet models
├── downloader.py       # HuggingFace downloads (registry + direct hf: pulls)
├── builder.py          # bitnet.cpp build automation
├── server.py           # Multi-model server orchestration
├── api.py              # OpenAI-compatible API + dashboard API endpoints
├── repl.py             # Interactive chat REPL (prompt_toolkit)
├── bench.py            # Benchmarking engine
├── logging.py          # Structured logging setup
├── static/             # Web dashboard (HTML/CSS/JS)
│   ├── index.html
│   ├── app.js
│   └── style.css
tests/
├── conftest.py
├── test_registry.py
├── test_config.py
├── test_downloader.py
├── test_builder.py
├── test_server.py
├── test_api.py
├── test_cli.py
├── test_repl.py
└── test_bench.py
.github/
├── workflows/
│   ├── ci.yml          # Lint + test on every push/PR
│   └── release.yml     # Build binaries + publish on tag
docs/
├── superpowers/specs/  # This spec
install.sh              # One-line installer
Dockerfile
pyproject.toml
README.md
CONTRIBUTING.md
LICENSE
```

---

## New Dependencies Summary

| Package | Purpose | Phase |
|---|---|---|
| `tomli` | TOML parsing (Python 3.9-3.10 backport) | A |
| `prompt_toolkit` | Interactive REPL input handling | B |
| `pytest` | Test framework | A (dev) |
| `pytest-asyncio` | Async test support | A (dev) |
| `pytest-cov` | Coverage reporting | A (dev) |
| `mypy` | Static type checking | A (dev) |
| `ruff` | Linting | A (dev) |

No new heavy frameworks. The web dashboard is vanilla JS — zero frontend build tooling.

---

## What This Spec Does NOT Cover

- **Authentication / multi-user access control** — out of scope for a local-first tool
- **Model training or fine-tuning** — bithub is inference-only
- **GPU acceleration** — BitNet models are CPU-optimized by design
- **Windows native support** — WSL is the recommended path; native Windows is a future consideration
- **Model format conversion** — bithub serves GGUF files as-is
