# Phase B1+B2: Polished REPL + Direct HuggingFace Pull

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the raw llama-cli passthrough with a polished interactive REPL that talks to the API server, and add the ability to pull any GGUF model directly from HuggingFace (not just registry models).

**Architecture:** The REPL (`bithub/repl.py`) auto-starts a local API server in the background, then sends messages via HTTP to `/v1/chat/completions` with streaming. This means `run` and `serve` use identical inference paths. Direct HF pull extends the existing `pull` command to accept `hf:org/repo` syntax and stores custom models in `custom_models.json`.

**Tech Stack:** prompt_toolkit (input handling), rich (markdown rendering), httpx (streaming HTTP), existing FastAPI server

---

## File Map

**Created:**
- `bithub/repl.py` — Interactive chat REPL
- `tests/test_repl.py` — REPL unit tests
- `tests/test_direct_pull.py` — Direct HF pull tests

**Modified:**
- `bithub/cli.py` — Wire new `run` command to REPL, extend `pull` for `hf:` prefix
- `bithub/downloader.py` — Add `download_direct_hf()` function
- `bithub/registry.py` — Add custom model registration
- `pyproject.toml` — Add prompt_toolkit dependency

---

## Task 0: Add prompt_toolkit Dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add prompt_toolkit to dependencies**

In `pyproject.toml`, add to the `dependencies` list:

```toml
"prompt-toolkit>=3.0",
```

- [ ] **Step 2: Install**

```bash
/usr/bin/python3 -m pip install prompt-toolkit
```

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "Add prompt_toolkit dependency for interactive REPL"
```

---

## Task 1: REPL Core — Message Loop and Streaming

**Files:**
- Create: `bithub/repl.py`
- Create: `tests/test_repl.py`

- [ ] **Step 1: Write failing tests for REPL message formatting**

Create `tests/test_repl.py`:

```python
"""Tests for bithub.repl."""

from typing import List
from unittest.mock import patch, MagicMock, AsyncMock

import pytest


class TestMessageHistory:
    def test_add_user_message(self) -> None:
        from bithub.repl import ChatSession
        session = ChatSession(model="test-model", api_url="http://localhost:8080")
        session.add_message("user", "hello")
        assert len(session.messages) == 1
        assert session.messages[0] == {"role": "user", "content": "hello"}

    def test_add_assistant_message(self) -> None:
        from bithub.repl import ChatSession
        session = ChatSession(model="test-model", api_url="http://localhost:8080")
        session.add_message("assistant", "hi there")
        assert len(session.messages) == 1
        assert session.messages[0]["role"] == "assistant"

    def test_clear_messages(self) -> None:
        from bithub.repl import ChatSession
        session = ChatSession(model="test-model", api_url="http://localhost:8080")
        session.add_message("user", "hello")
        session.add_message("assistant", "hi")
        session.clear()
        assert len(session.messages) == 0

    def test_system_prompt(self) -> None:
        from bithub.repl import ChatSession
        session = ChatSession(model="test-model", api_url="http://localhost:8080")
        session.set_system_prompt("You are a pirate.")
        session.add_message("user", "hello")
        payload = session.build_payload()
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][0]["content"] == "You are a pirate."
        assert payload["messages"][1]["role"] == "user"

    def test_build_payload(self) -> None:
        from bithub.repl import ChatSession
        session = ChatSession(model="test-model", api_url="http://localhost:8080")
        session.add_message("user", "hello")
        payload = session.build_payload()
        assert payload["model"] == "test-model"
        assert payload["messages"] == [{"role": "user", "content": "hello"}]
        assert payload["stream"] is True


class TestSlashCommands:
    def test_is_command(self) -> None:
        from bithub.repl import is_slash_command
        assert is_slash_command("/help") is True
        assert is_slash_command("/clear") is True
        assert is_slash_command("hello") is False
        assert is_slash_command("") is False

    def test_parse_system_command(self) -> None:
        from bithub.repl import parse_slash_command
        cmd, arg = parse_slash_command("/system You are helpful")
        assert cmd == "system"
        assert arg == "You are helpful"

    def test_parse_command_no_arg(self) -> None:
        from bithub.repl import parse_slash_command
        cmd, arg = parse_slash_command("/clear")
        assert cmd == "clear"
        assert arg == ""

    def test_parse_help(self) -> None:
        from bithub.repl import parse_slash_command
        cmd, arg = parse_slash_command("/help")
        assert cmd == "help"


class TestExportConversation:
    def test_export_to_string(self) -> None:
        from bithub.repl import ChatSession
        session = ChatSession(model="test-model", api_url="http://localhost:8080")
        session.add_message("user", "hello")
        session.add_message("assistant", "hi there")
        exported = session.export()
        assert "user: hello" in exported
        assert "assistant: hi there" in exported
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
/usr/bin/python3 -m pytest tests/test_repl.py -v
```

Expected: FAIL — `bithub.repl` doesn't exist.

- [ ] **Step 3: Create `bithub/repl.py` with ChatSession and slash command parsing**

```python
"""Interactive chat REPL for bithub."""

import json
import sys
import time
from typing import List, Optional, Tuple

import httpx
from rich.console import Console
from rich.markdown import Markdown

console = Console()


def is_slash_command(text: str) -> bool:
    """Check if input is a slash command."""
    return bool(text) and text.startswith("/")


def parse_slash_command(text: str) -> Tuple[str, str]:
    """Parse a slash command into (command, argument)."""
    parts = text[1:].split(None, 1)
    cmd = parts[0] if parts else ""
    arg = parts[1] if len(parts) > 1 else ""
    return cmd, arg


class ChatSession:
    """Manages conversation state for the REPL."""

    def __init__(self, model: str, api_url: str) -> None:
        self.model = model
        self.api_url = api_url.rstrip("/")
        self.messages: List[dict] = []
        self.system_prompt: Optional[str] = None
        self.total_tokens = 0

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def clear(self) -> None:
        self.messages.clear()
        self.total_tokens = 0

    def set_system_prompt(self, prompt: str) -> None:
        self.system_prompt = prompt

    def build_payload(self) -> dict:
        msgs = []
        if self.system_prompt:
            msgs.append({"role": "system", "content": self.system_prompt})
        msgs.extend(self.messages)
        return {
            "model": self.model,
            "messages": msgs,
            "stream": True,
        }

    def export(self) -> str:
        lines = []
        for msg in self.messages:
            lines.append(f"{msg['role']}: {msg['content']}")
        return "\n\n".join(lines)

    def send_and_stream(self) -> str:
        """Send current conversation to API and stream the response.

        Returns the full assistant response text.
        """
        payload = self.build_payload()
        url = f"{self.api_url}/v1/chat/completions"
        full_response = ""

        try:
            with httpx.stream("POST", url, json=payload, timeout=120.0) as response:
                if response.status_code != 200:
                    console.print(f"[red]API error: {response.status_code}[/red]")
                    return ""

                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            sys.stdout.write(content)
                            sys.stdout.flush()
                            full_response += content
                    except json.JSONDecodeError:
                        continue

        except httpx.ConnectError:
            console.print("[red]Cannot connect to API server.[/red]")
            console.print("Is the server running? Start with: bithub serve <model>")
        except httpx.ReadTimeout:
            console.print("\n[yellow]Response timed out.[/yellow]")

        sys.stdout.write("\n")
        return full_response


HELP_TEXT = """[bold]Available commands:[/bold]
  /help              Show this help
  /clear             Clear conversation history
  /system <prompt>   Set system prompt
  /model             Show current model info
  /export            Save conversation to file
  /quit              Exit chat
"""


def handle_slash_command(cmd: str, arg: str, session: ChatSession) -> Optional[str]:
    """Handle a slash command. Returns 'quit' to exit, None otherwise."""
    if cmd == "help":
        console.print(HELP_TEXT)
    elif cmd == "clear":
        session.clear()
        console.print("[dim]Conversation cleared.[/dim]")
    elif cmd == "system":
        if not arg:
            if session.system_prompt:
                console.print(f"[dim]Current system prompt: {session.system_prompt}[/dim]")
            else:
                console.print("[dim]No system prompt set. Usage: /system <prompt>[/dim]")
        else:
            session.set_system_prompt(arg)
            console.print(f"[dim]System prompt set.[/dim]")
    elif cmd == "model":
        console.print(f"[bold]Model:[/bold] {session.model}")
        console.print(f"[bold]API:[/bold] {session.api_url}")
        console.print(f"[bold]Messages:[/bold] {len(session.messages)}")
        console.print(f"[bold]Tokens:[/bold] ~{session.total_tokens}")
    elif cmd == "export":
        filename = arg if arg else f"chat-{int(time.time())}.txt"
        content = session.export()
        if not content:
            console.print("[yellow]Nothing to export.[/yellow]")
        else:
            with open(filename, "w") as f:
                f.write(content)
            console.print(f"[green]Saved to {filename}[/green]")
    elif cmd in ("quit", "exit", "q"):
        return "quit"
    else:
        console.print(f"[yellow]Unknown command: /{cmd}[/yellow]")
        console.print("Type [bold]/help[/bold] for available commands.")
    return None


def start_repl(model: str, api_url: str) -> None:
    """Start the interactive REPL."""
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory
        from bithub.config import BITHUB_HOME

        history_file = BITHUB_HOME / "repl_history"
        BITHUB_HOME.mkdir(parents=True, exist_ok=True)
        prompt_session = PromptSession(history=FileHistory(str(history_file)))
    except ImportError:
        prompt_session = None

    session = ChatSession(model=model, api_url=api_url)

    console.print(f"[bold green]Chat with {model}[/bold green]")
    console.print(f"[dim]API: {api_url} | Type /help for commands | Ctrl+D to exit[/dim]\n")

    while True:
        try:
            if prompt_session:
                user_input = prompt_session.prompt(f"[{model}] > ")
            else:
                user_input = input(f"[{model}] > ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[green]Goodbye![/green]")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if is_slash_command(user_input):
            cmd, arg = parse_slash_command(user_input)
            result = handle_slash_command(cmd, arg, session)
            if result == "quit":
                console.print("[green]Goodbye![/green]")
                break
            continue

        # Send message to API
        session.add_message("user", user_input)
        console.print()
        response = session.send_and_stream()
        if response:
            session.add_message("assistant", response)
        console.print()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
/usr/bin/python3 -m pytest tests/test_repl.py -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add bithub/repl.py tests/test_repl.py
git commit -m "Add REPL core: ChatSession, slash commands, streaming"
```

---

## Task 2: Wire REPL into CLI `run` Command

**Files:**
- Modify: `bithub/cli.py`
- Modify: `bithub/server.py`

The `run` command should auto-start a background API server, then launch the REPL pointing at it.

- [ ] **Step 1: Add `start_background_server` to `server.py`**

Read `bithub/server.py`. Add this function after `start_server`:

```python
import threading


def start_background_server(
    model_name: str,
    host: str = "127.0.0.1",
    port: int = 8081,
    threads: int = 2,
    context_size: int = 2048,
) -> threading.Thread:
    """Start the API server in a background thread for REPL use.

    Returns the thread handle. The server stops when the main thread exits.
    """
    gguf_path = _preflight_check(model_name)

    from bithub.api import create_app
    import uvicorn

    backend_port = port + 1
    app = create_app(
        model_name=model_name,
        gguf_path=gguf_path,
        threads=threads,
        context_size=context_size,
        backend_port=backend_port,
    )

    server_thread = threading.Thread(
        target=uvicorn.run,
        kwargs={"app": app, "host": host, "port": port, "log_level": "error"},
        daemon=True,
    )
    server_thread.start()
    return server_thread


def wait_for_server(url: str, timeout: float = 30.0) -> bool:
    """Wait for the API server to become ready."""
    import time
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = httpx.get(f"{url}/health", timeout=2.0)
            if resp.status_code == 200:
                return True
        except (httpx.ConnectError, httpx.ReadTimeout):
            pass
        time.sleep(0.5)
    return False
```

Add `import httpx` at the top of `server.py`.

- [ ] **Step 2: Update the `run` CLI command in `cli.py`**

Replace the `run` command function body (lines ~199-213 in `bithub/cli.py`):

```python
@cli.command()
@click.argument("model_name")
@click.option("--threads", "-t", default=_DEFAULT_THREADS, show_default=True,
              help="Number of CPU threads")
@click.option("--context-size", "-c", default=2048, show_default=True,
              help="Context window size")
@click.option("--port", default=8081, hidden=True, help="API server port for REPL backend")
def run(model_name, threads, context_size, port):
    """Chat with a model in your terminal.

    Starts a local API server in the background and opens an interactive
    chat session with markdown rendering, history, and slash commands.

    \b
    Examples:
        bithub run 2B-4T
        bithub run falcon3-3B -t 4

    \b
    Commands in chat:
        /help     Show commands
        /clear    Clear history
        /system   Set system prompt
        /export   Save conversation
        /quit     Exit
    """
    if not _ensure_engine_ready():
        raise SystemExit(1)
    if not _ensure_model_ready(model_name):
        raise SystemExit(1)

    from bithub.server import start_background_server, wait_for_server

    api_url = f"http://127.0.0.1:{port}"

    console.print("[dim]Starting local API server...[/dim]")
    start_background_server(
        model_name, host="127.0.0.1", port=port,
        threads=threads, context_size=context_size,
    )

    if not wait_for_server(api_url):
        console.print("[red]Server failed to start. Run bithub status for diagnostics.[/red]")
        raise SystemExit(1)

    console.print("[dim]Server ready.[/dim]\n")

    from bithub.repl import start_repl
    start_repl(model=model_name, api_url=api_url)
```

- [ ] **Step 3: Run existing CLI tests to make sure nothing broke**

```bash
/usr/bin/python3 -m pytest tests/test_cli.py -v
```

- [ ] **Step 4: Commit**

```bash
git add bithub/cli.py bithub/server.py
git commit -m "Wire REPL into CLI run command with background API server"
```

---

## Task 3: Direct HuggingFace Pull

**Files:**
- Modify: `bithub/downloader.py`
- Modify: `bithub/registry.py`
- Modify: `bithub/cli.py`
- Create: `tests/test_direct_pull.py`

- [ ] **Step 1: Write failing tests for direct HF pull**

Create `tests/test_direct_pull.py`:

```python
"""Tests for direct HuggingFace pull (hf:org/repo syntax)."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestParseHfPrefix:
    def test_detects_hf_prefix(self) -> None:
        from bithub.downloader import is_direct_hf_pull
        assert is_direct_hf_pull("hf:microsoft/BitNet-b1.58-2B-4T-gguf") is True
        assert is_direct_hf_pull("2B-4T") is False
        assert is_direct_hf_pull("hf:") is False

    def test_extracts_repo_id(self) -> None:
        from bithub.downloader import parse_hf_uri
        repo_id, name = parse_hf_uri("hf:microsoft/BitNet-b1.58-2B-4T-gguf")
        assert repo_id == "microsoft/BitNet-b1.58-2B-4T-gguf"
        assert name == "BitNet-b1.58-2B-4T-gguf"

    def test_extracts_short_name(self) -> None:
        from bithub.downloader import parse_hf_uri
        _, name = parse_hf_uri("hf:tiiuae/Falcon3-1B-Instruct-1.58bit")
        assert name == "Falcon3-1B-Instruct-1.58bit"


class TestCustomModelRegistry:
    def test_save_and_load_custom_model(self, tmp_home: Path) -> None:
        with patch("bithub.registry.BITHUB_HOME", tmp_home):
            from bithub.registry import save_custom_model, load_custom_models
            save_custom_model("my-model", {
                "hf_repo": "user/my-model-gguf",
                "name": "My Model",
                "source": "direct",
            })
            models = load_custom_models()
            assert "my-model" in models
            assert models["my-model"]["hf_repo"] == "user/my-model-gguf"

    def test_custom_models_appear_in_list(self, tmp_home: Path) -> None:
        with patch("bithub.registry.BITHUB_HOME", tmp_home):
            from bithub.registry import save_custom_model, load_custom_models
            save_custom_model("my-model", {
                "hf_repo": "user/my-model-gguf",
                "name": "My Model",
                "source": "direct",
            })
            models = load_custom_models()
            assert len(models) == 1

    def test_empty_when_no_file(self, tmp_home: Path) -> None:
        with patch("bithub.registry.BITHUB_HOME", tmp_home):
            from bithub.registry import load_custom_models
            models = load_custom_models()
            assert models == {}


class TestDownloadDirectHf:
    def test_downloads_from_hf_repo(self, tmp_home: Path) -> None:
        mock_api = MagicMock()
        mock_api.list_repo_files.return_value = ["model.gguf", "README.md"]

        model_dir = tmp_home / "models" / "my-model"
        model_dir.mkdir(parents=True)
        fake_gguf = model_dir / "model.gguf"
        fake_gguf.write_bytes(b"\x00" * 100)

        with patch("bithub.downloader.MODELS_DIR", tmp_home / "models"), \
             patch("bithub.downloader.ensure_dirs"), \
             patch("bithub.downloader.HfApi", return_value=mock_api), \
             patch("bithub.downloader.hf_hub_download", return_value=str(fake_gguf)), \
             patch("bithub.registry.BITHUB_HOME", tmp_home):
            from bithub.downloader import download_direct_hf
            result = download_direct_hf("user/my-model-gguf", name="my-model")
            assert result.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
/usr/bin/python3 -m pytest tests/test_direct_pull.py -v
```

- [ ] **Step 3: Add helper functions to `downloader.py`**

Add to `bithub/downloader.py`:

```python
def is_direct_hf_pull(model_ref: str) -> bool:
    """Check if a model reference uses the hf: prefix."""
    return model_ref.startswith("hf:") and len(model_ref) > 3 and "/" in model_ref


def parse_hf_uri(model_ref: str) -> Tuple[str, str]:
    """Parse hf:org/repo into (repo_id, short_name)."""
    repo_id = model_ref[3:]  # strip "hf:"
    short_name = repo_id.split("/")[-1]
    return repo_id, short_name


def download_direct_hf(repo_id: str, name: Optional[str] = None, force: bool = False) -> Path:
    """Download a GGUF model directly from any HuggingFace repo.

    Args:
        repo_id: Full HuggingFace repo ID (e.g. 'microsoft/BitNet-b1.58-2B-4T-gguf')
        name: Short name for local storage (defaults to repo name)
        force: Re-download if already present

    Returns:
        Path to the downloaded GGUF file
    """
    ensure_dirs()

    if not name:
        name = repo_id.split("/")[-1]

    model_dir = MODELS_DIR / name

    # Check if already downloaded
    if not force and is_model_downloaded(name):
        existing = get_model_gguf_path(name)
        console.print(f"[green]Model {name} already downloaded:[/green] {existing}")
        console.print("Use [bold]--force[/bold] to re-download.")
        return existing

    console.print(f"\n[bold]Pulling from HuggingFace[/bold]")
    console.print(f"  Repository: [dim]{repo_id}[/dim]")
    console.print(f"  [yellow]This model is not in the curated registry. Compatibility not guaranteed.[/yellow]\n")

    # Find GGUF file
    with console.status("[bold blue]Finding GGUF file in repository..."):
        try:
            api = HfApi()
            files = api.list_repo_files(repo_id)
            gguf_files = [f for f in files if f.endswith(".gguf")]
        except Exception as e:
            console.print(f"[red]Failed to access repository: {e}[/red]")
            raise SystemExit(1)

    if not gguf_files:
        console.print(f"[red]No GGUF files found in {repo_id}[/red]")
        raise SystemExit(1)

    gguf_filename = gguf_files[0]
    if len(gguf_files) > 1:
        console.print(f"  Found {len(gguf_files)} GGUF files, downloading: [cyan]{gguf_filename}[/cyan]")
    else:
        console.print(f"  Downloading: [cyan]{gguf_filename}[/cyan]\n")

    try:
        downloaded_path = hf_hub_download(
            repo_id=repo_id,
            filename=gguf_filename,
            local_dir=str(model_dir),
            local_dir_use_symlinks=False,
        )
        downloaded_path = Path(downloaded_path)
    except Exception as e:
        console.print(f"[red]Download failed: {e}[/red]")
        raise SystemExit(1)

    size_mb = downloaded_path.stat().st_size / (1024 * 1024)
    console.print(f"\n[green]Downloaded successfully![/green]")
    console.print(f"  File: {downloaded_path}")
    console.print(f"  Size: {size_mb:.0f} MB")

    _write_checksum(downloaded_path)
    console.print(f"  Checksum: [dim]SHA256 written[/dim]")

    # Register as custom model
    from bithub.registry import save_custom_model
    save_custom_model(name, {
        "hf_repo": repo_id,
        "name": name,
        "source": "direct",
    })

    return downloaded_path
```

Add `from typing import Tuple` to the imports if not already there.

- [ ] **Step 4: Add custom model functions to `registry.py`**

Read `bithub/registry.py`. Add imports and functions:

```python
import json
from pathlib import Path
from typing import Optional

from bithub.config import BITHUB_HOME

REGISTRY_PATH = Path(__file__).parent / "registry.json"
CUSTOM_MODELS_PATH = BITHUB_HOME / "custom_models.json"


def load_custom_models() -> dict:
    """Load user's custom (directly-pulled) models."""
    if not CUSTOM_MODELS_PATH.exists():
        return {}
    try:
        with open(CUSTOM_MODELS_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_custom_model(name: str, info: dict) -> None:
    """Save a custom model entry to custom_models.json."""
    models = load_custom_models()
    models[name] = info
    BITHUB_HOME.mkdir(parents=True, exist_ok=True)
    with open(CUSTOM_MODELS_PATH, "w") as f:
        json.dump(models, f, indent=2)
```

Note: Keep the existing `load_registry`, `get_model_info`, and `list_available_models` functions unchanged. The custom models are a separate registry.

- [ ] **Step 5: Update `get_model_info` to also check custom models**

In `registry.py`, update `get_model_info`:

```python
def get_model_info(model_name: str) -> Optional[dict]:
    """Return info dict for a model, checking registry then custom models."""
    registry = load_registry()
    info = registry["models"].get(model_name)
    if info:
        return info
    custom = load_custom_models()
    return custom.get(model_name)
```

- [ ] **Step 6: Update `pull` command in `cli.py` to handle `hf:` prefix**

In `bithub/cli.py`, update the `pull` command:

```python
@cli.command()
@click.argument("model_name")
@click.option("--force", is_flag=True, help="Re-download even if already present")
@click.option("--name", default=None, help="Short name for direct HF pulls")
def pull(model_name, force, name):
    """Download a BitNet model from HuggingFace.

    \b
    Examples:
        bithub pull 2B-4T                              # from registry
        bithub pull falcon3-1B --force                  # re-download
        bithub pull hf:microsoft/BitNet-b1.58-2B-4T-gguf  # direct from HF
        bithub pull hf:user/custom-model --name mymodel    # with custom name
    """
    from bithub.downloader import is_direct_hf_pull, parse_hf_uri, download_direct_hf

    if is_direct_hf_pull(model_name):
        repo_id, default_name = parse_hf_uri(model_name)
        download_direct_hf(repo_id, name=name or default_name, force=force)
        return

    info = get_model_info(model_name)
    if not info:
        _suggest_model(model_name)
        raise SystemExit(1)

    from bithub.downloader import download_model
    download_model(model_name, force=force)
```

- [ ] **Step 7: Run all tests**

```bash
/usr/bin/python3 -m pytest tests/ -v
```

- [ ] **Step 8: Commit**

```bash
git add bithub/downloader.py bithub/registry.py bithub/cli.py tests/test_direct_pull.py
git commit -m "Add direct HuggingFace pull with hf: prefix and custom model registry"
```

---

## Task 4: Final Verification

- [ ] **Step 1: Run full test suite with coverage**

```bash
/usr/bin/python3 -m pytest tests/ --cov=bithub --cov-report=term-missing -v
```

Expected: all tests pass, coverage >= 70%.

- [ ] **Step 2: Verify CLI help**

```bash
/usr/bin/python3 -m bithub --help
/usr/bin/python3 -m bithub pull --help
/usr/bin/python3 -m bithub run --help
```

Expected: `pull` shows `hf:` examples and `--name` option. `run` shows slash commands in help.

- [ ] **Step 3: Commit any fixes**

```bash
git add -A
git commit -m "Phase B1+B2 complete: polished REPL and direct HF pull"
```
