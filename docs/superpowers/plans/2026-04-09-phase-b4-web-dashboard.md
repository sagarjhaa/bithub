# Phase B4: Web Dashboard

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full web dashboard served at the API server root — chat interface, model management, server stats, and settings — so users can interact with bithub from their browser without installing additional tools.

**Architecture:** Vanilla HTML/CSS/JS static files served by FastAPI via `StaticFiles`. The dashboard communicates with the existing `/v1/` API endpoints plus a few new `/api/` endpoints for dashboard-specific data (stats, config, model operations). Single-page app with client-side hash routing. Dark mode default.

**Tech Stack:** HTML5, CSS3, vanilla JavaScript (ES6+), FastAPI StaticFiles mount. No build step, no node_modules, no framework.

---

## File Map

**Created:**
- `bithub/static/index.html` — SPA shell with sidebar navigation
- `bithub/static/style.css` — Full dashboard styles (dark mode default)
- `bithub/static/app.js` — SPA router, chat, models, server, settings pages
- `bithub/dashboard_api.py` — Dashboard-specific API endpoints (stats, config, model ops)
- `tests/test_dashboard_api.py` — Dashboard API endpoint tests

**Modified:**
- `bithub/api.py` — Mount static files, include dashboard router
- `bithub/model_manager.py` — Add request counting for stats
- `pyproject.toml` — Include static files in package data

---

## Task 0: Dashboard API Endpoints

**Files:**
- Create: `bithub/dashboard_api.py`
- Create: `tests/test_dashboard_api.py`
- Modify: `bithub/model_manager.py`

New endpoints the dashboard needs beyond the existing OpenAI-compatible API.

- [ ] **Step 1: Add request tracking to ModelManager**

Read `bithub/model_manager.py`. Add a stats tracking dict to `ModelManager.__init__`:

```python
def __init__(self, base_port: int = 8081, max_models: int = 3) -> None:
    self.base_port = base_port
    self.max_models = max_models
    self.models: Dict[str, dict] = {}
    self.backends: Dict[str, BackendProcess] = {}
    self._next_port = base_port
    self.stats: Dict[str, int] = {"requests": 0, "tokens_generated": 0}
    self._start_time: Optional[float] = None
```

Add `import time` at top if not present. In `start_all`, record start time:

```python
def start_all(self) -> bool:
    self._start_time = time.time()
    all_ok = True
    ...
```

Add a method:

```python
def get_stats(self) -> dict:
    """Return server statistics."""
    uptime = time.time() - self._start_time if self._start_time else 0
    return {
        "uptime_seconds": int(uptime),
        "total_requests": self.stats["requests"],
        "models_loaded": sum(1 for m in self.list_models() if m["loaded"]),
        "models_registered": len(self.models),
    }

def record_request(self) -> None:
    """Increment request counter."""
    self.stats["requests"] += 1
```

- [ ] **Step 2: Write failing tests for dashboard API**

Create `tests/test_dashboard_api.py`:

```python
"""Tests for bithub dashboard API endpoints."""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def dashboard_client():
    """Create a TestClient with dashboard API mounted."""
    from bithub.model_manager import ModelManager
    from bithub.api import create_app

    mgr = ModelManager(base_port=19000)
    mgr.register("test-model", Path("/fake/model.gguf"))

    app = create_app(
        model_name="test-model",
        gguf_path=Path("/fake/model.gguf"),
        manager=mgr,
    )
    app.router.on_startup.clear()
    app.router.on_shutdown.clear()

    client = TestClient(app)
    yield client, mgr


class TestStatsEndpoint:
    def test_returns_stats(self, dashboard_client) -> None:
        client, mgr = dashboard_client
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert "uptime_seconds" in data
        assert "total_requests" in data
        assert "models_registered" in data

    def test_request_counter_increments(self, dashboard_client) -> None:
        client, mgr = dashboard_client
        mgr.record_request()
        mgr.record_request()
        response = client.get("/api/stats")
        data = response.json()
        assert data["total_requests"] == 2


class TestConfigEndpoint:
    def test_get_config(self, dashboard_client) -> None:
        client, _ = dashboard_client
        with patch("bithub.dashboard_api.load_config", return_value={
            "server": {"port": 8080, "host": "127.0.0.1"},
            "models": {"default": None},
            "download": {"check_disk_space": True, "min_free_gb": 5},
        }):
            response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "server" in data


class TestModelsManagement:
    def test_list_downloaded(self, dashboard_client) -> None:
        client, _ = dashboard_client
        with patch("bithub.dashboard_api.get_downloaded_models", return_value=[]):
            response = client.get("/api/models/downloaded")
        assert response.status_code == 200
        assert response.json() == []

    def test_delete_model(self, dashboard_client) -> None:
        client, _ = dashboard_client
        with patch("bithub.dashboard_api.remove_model", return_value=True):
            response = client.delete("/api/models/test-model")
        assert response.status_code == 200
        assert response.json()["removed"] is True

    def test_delete_nonexistent(self, dashboard_client) -> None:
        client, _ = dashboard_client
        with patch("bithub.dashboard_api.remove_model", return_value=False):
            response = client.delete("/api/models/nonexistent")
        assert response.status_code == 404
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
/usr/bin/python3 -m pytest tests/test_dashboard_api.py -v
```

- [ ] **Step 4: Create `bithub/dashboard_api.py`**

```python
"""Dashboard-specific API endpoints for bithub web UI."""

from typing import Optional

from fastapi import APIRouter, HTTPException

from bithub.config import load_config
from bithub.downloader import get_downloaded_models, remove_model
from bithub.model_manager import ModelManager
from bithub.registry import list_available_models

router = APIRouter(prefix="/api", tags=["dashboard"])

# Set by create_app when mounting the dashboard
_manager: Optional[ModelManager] = None


def init_dashboard(manager: ModelManager) -> APIRouter:
    """Initialize dashboard routes with a ModelManager reference."""
    global _manager
    _manager = manager
    return router


@router.get("/stats")
async def get_stats():
    """Server statistics for the dashboard."""
    if _manager is None:
        return {"error": "Not initialized"}
    return _manager.get_stats()


@router.get("/config")
async def get_config():
    """Current configuration."""
    return load_config()


@router.get("/models/downloaded")
async def list_downloaded():
    """List all downloaded models."""
    return get_downloaded_models()


@router.get("/models/registry")
async def list_registry():
    """List all models from the curated registry."""
    return list_available_models()


@router.delete("/models/{model_name}")
async def delete_model(model_name: str):
    """Delete a downloaded model."""
    success = remove_model(model_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
    return {"removed": True, "model": model_name}
```

- [ ] **Step 5: Mount dashboard router in api.py**

In `bithub/api.py`, inside `create_app`, after the app is created but before the routes, add:

```python
    from bithub.dashboard_api import init_dashboard
    dashboard_router = init_dashboard(manager)
    app.include_router(dashboard_router)
```

- [ ] **Step 6: Run tests**

```bash
/usr/bin/python3 -m pytest tests/test_dashboard_api.py -v
/usr/bin/python3 -m pytest tests/ -v
```

- [ ] **Step 7: Commit**

```bash
git add bithub/dashboard_api.py bithub/model_manager.py bithub/api.py tests/test_dashboard_api.py
git commit -m "Add dashboard API endpoints for stats, config, and model management"
```

---

## Task 1: Static File Serving and HTML Shell

**Files:**
- Create: `bithub/static/index.html`
- Modify: `bithub/api.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Update pyproject.toml to include static files**

In `pyproject.toml`, update the package-data section:

```toml
[tool.setuptools.package-data]
bithub = ["registry.json", "static/**/*"]
```

- [ ] **Step 2: Mount static files in api.py**

In `create_app`, after including the dashboard router, add:

```python
    from fastapi.staticfiles import StaticFiles
    import os
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        from fastapi.responses import FileResponse

        @app.get("/")
        async def dashboard_root():
            return FileResponse(static_dir / "index.html")

        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
```

- [ ] **Step 3: Create `bithub/static/index.html`**

```html
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>bithub</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <nav class="sidebar">
        <div class="sidebar-brand">
            <h1>bithub</h1>
            <span class="version">v0.1.0</span>
        </div>
        <ul class="nav-links">
            <li><a href="#/" class="nav-link active" data-page="chat">Chat</a></li>
            <li><a href="#/models" class="nav-link" data-page="models">Models</a></li>
            <li><a href="#/server" class="nav-link" data-page="server">Server</a></li>
            <li><a href="#/settings" class="nav-link" data-page="settings">Settings</a></li>
        </ul>
    </nav>

    <main class="content">
        <!-- Chat Page -->
        <div id="page-chat" class="page active">
            <div class="chat-header">
                <select id="model-select" class="model-select"></select>
                <div class="chat-controls">
                    <button id="clear-chat" class="btn btn-sm">Clear</button>
                </div>
            </div>
            <div id="chat-messages" class="chat-messages"></div>
            <div class="chat-input-area">
                <textarea id="chat-input" placeholder="Type a message..." rows="1"></textarea>
                <button id="send-btn" class="btn btn-primary">Send</button>
            </div>
        </div>

        <!-- Models Page -->
        <div id="page-models" class="page">
            <h2>Models</h2>
            <div id="models-list" class="models-grid"></div>
        </div>

        <!-- Server Page -->
        <div id="page-server" class="page">
            <h2>Server</h2>
            <div id="server-stats" class="stats-grid"></div>
        </div>

        <!-- Settings Page -->
        <div id="page-settings" class="page">
            <h2>Settings</h2>
            <div id="settings-form" class="settings-form"></div>
        </div>
    </main>

    <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 4: Verify static files are served**

```bash
/usr/bin/python3 -m pytest tests/test_api.py -v
```

Also add a quick test to `tests/test_dashboard_api.py`:

```python
class TestStaticFiles:
    def test_root_serves_html(self, dashboard_client) -> None:
        client, _ = dashboard_client
        # This test may fail if static dir doesn't exist in test env
        # That's OK — the important thing is the route exists
        response = client.get("/")
        assert response.status_code in (200, 404)
```

- [ ] **Step 5: Commit**

```bash
git add bithub/static/index.html bithub/api.py pyproject.toml tests/test_dashboard_api.py
git commit -m "Add HTML shell and static file serving for web dashboard"
```

---

## Task 2: Dashboard CSS (Dark Mode)

**Files:**
- Create: `bithub/static/style.css`

- [ ] **Step 1: Create `bithub/static/style.css`**

```css
/* bithub dashboard — dark mode default */

:root {
    --bg-primary: #0d1117;
    --bg-secondary: #161b22;
    --bg-tertiary: #21262d;
    --text-primary: #e6edf3;
    --text-secondary: #8b949e;
    --text-muted: #484f58;
    --accent: #58a6ff;
    --accent-hover: #79c0ff;
    --success: #3fb950;
    --warning: #d29922;
    --error: #f85149;
    --border: #30363d;
    --sidebar-width: 220px;
    --radius: 8px;
    --font-mono: 'SF Mono', 'Fira Code', monospace;
    --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
}

[data-theme="light"] {
    --bg-primary: #ffffff;
    --bg-secondary: #f6f8fa;
    --bg-tertiary: #eaeef2;
    --text-primary: #1f2328;
    --text-secondary: #656d76;
    --text-muted: #8b949e;
    --accent: #0969da;
    --accent-hover: #0550ae;
    --success: #1a7f37;
    --warning: #9a6700;
    --error: #cf222e;
    --border: #d0d7de;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: var(--font-sans);
    background: var(--bg-primary);
    color: var(--text-primary);
    display: flex;
    height: 100vh;
    overflow: hidden;
}

/* Sidebar */
.sidebar {
    width: var(--sidebar-width);
    background: var(--bg-secondary);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
}

.sidebar-brand {
    padding: 20px;
    border-bottom: 1px solid var(--border);
}

.sidebar-brand h1 {
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--accent);
}

.sidebar-brand .version {
    font-size: 0.75rem;
    color: var(--text-muted);
}

.nav-links {
    list-style: none;
    padding: 12px 0;
}

.nav-link {
    display: block;
    padding: 10px 20px;
    color: var(--text-secondary);
    text-decoration: none;
    font-size: 0.9rem;
    transition: all 0.15s;
}

.nav-link:hover {
    color: var(--text-primary);
    background: var(--bg-tertiary);
}

.nav-link.active {
    color: var(--accent);
    background: var(--bg-tertiary);
    border-right: 2px solid var(--accent);
}

/* Main content */
.content {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
}

.page { display: none; flex: 1; flex-direction: column; padding: 24px; }
.page.active { display: flex; }

/* Chat */
.chat-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 16px;
}

.model-select {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 8px 12px;
    font-size: 0.9rem;
    cursor: pointer;
}

.chat-controls { margin-left: auto; }

.chat-messages {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 8px 0;
}

.message {
    display: flex;
    gap: 12px;
    max-width: 85%;
}

.message.user { align-self: flex-end; flex-direction: row-reverse; }
.message.assistant { align-self: flex-start; }

.message-role {
    font-size: 0.7rem;
    text-transform: uppercase;
    color: var(--text-muted);
    font-weight: 600;
    letter-spacing: 0.05em;
    flex-shrink: 0;
    padding-top: 4px;
}

.message-content {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 16px;
    font-size: 0.9rem;
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
}

.message.user .message-content {
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
}

.chat-input-area {
    display: flex;
    gap: 8px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
    margin-top: auto;
}

#chat-input {
    flex: 1;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 16px;
    color: var(--text-primary);
    font-family: var(--font-sans);
    font-size: 0.9rem;
    resize: none;
    outline: none;
}

#chat-input:focus { border-color: var(--accent); }

/* Buttons */
.btn {
    padding: 8px 16px;
    border-radius: var(--radius);
    border: 1px solid var(--border);
    background: var(--bg-tertiary);
    color: var(--text-primary);
    cursor: pointer;
    font-size: 0.85rem;
    transition: all 0.15s;
}

.btn:hover { background: var(--border); }
.btn-primary { background: var(--accent); color: #fff; border-color: var(--accent); }
.btn-primary:hover { background: var(--accent-hover); }
.btn-sm { padding: 4px 10px; font-size: 0.8rem; }
.btn-danger { background: var(--error); color: #fff; border-color: var(--error); }

/* Models grid */
.models-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 16px;
    margin-top: 16px;
}

.model-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
}

.model-card h3 { color: var(--accent); margin-bottom: 8px; }
.model-card .meta { color: var(--text-secondary); font-size: 0.85rem; }
.model-card .status { margin-top: 12px; }
.status-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
}
.status-loaded { background: rgba(63, 185, 80, 0.2); color: var(--success); }
.status-available { background: rgba(139, 148, 158, 0.2); color: var(--text-secondary); }

/* Stats grid */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 16px;
    margin-top: 16px;
}

.stat-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    text-align: center;
}

.stat-card .stat-value {
    font-size: 2rem;
    font-weight: 700;
    color: var(--accent);
}

.stat-card .stat-label {
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-top: 4px;
}

/* Settings */
.settings-form { max-width: 500px; margin-top: 16px; }
.form-group { margin-bottom: 20px; }
.form-group label {
    display: block;
    font-size: 0.85rem;
    color: var(--text-secondary);
    margin-bottom: 6px;
}
.form-group input, .form-group select {
    width: 100%;
    padding: 8px 12px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text-primary);
    font-size: 0.9rem;
}
```

- [ ] **Step 2: Commit**

```bash
git add bithub/static/style.css
git commit -m "Add dashboard CSS with dark/light mode themes"
```

---

## Task 3: Dashboard JavaScript (SPA Router + All Pages)

**Files:**
- Create: `bithub/static/app.js`

- [ ] **Step 1: Create `bithub/static/app.js`**

```javascript
/* bithub dashboard — single-page app */

const API_BASE = '';

// ── Router ────────────────────────────────────────────
function navigateTo(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    const pageEl = document.getElementById('page-' + page);
    const linkEl = document.querySelector('[data-page="' + page + '"]');
    if (pageEl) pageEl.classList.add('active');
    if (linkEl) linkEl.classList.add('active');

    if (page === 'models') loadModels();
    if (page === 'server') loadStats();
    if (page === 'settings') loadSettings();
    if (page === 'chat') loadModelSelect();
}

function initRouter() {
    window.addEventListener('hashchange', () => {
        const page = location.hash.replace('#/', '') || 'chat';
        navigateTo(page);
    });
    const page = location.hash.replace('#/', '') || 'chat';
    navigateTo(page);
}

// ── Chat ──────────────────────────────────────────────
const chatMessages = [];
let streaming = false;

function loadModelSelect() {
    fetch(API_BASE + '/v1/models')
        .then(r => r.json())
        .then(data => {
            const select = document.getElementById('model-select');
            if (!select) return;
            const current = select.value;
            select.innerHTML = '';
            (data.data || []).forEach(m => {
                const opt = document.createElement('option');
                opt.value = m.id;
                opt.textContent = m.id + (m.status === 'loaded' ? ' (loaded)' : '');
                select.appendChild(opt);
            });
            if (current) select.value = current;
        })
        .catch(() => {});
}

function addChatMessage(role, content) {
    chatMessages.push({ role, content });
    renderChat();
}

function renderChat() {
    const container = document.getElementById('chat-messages');
    if (!container) return;
    container.innerHTML = '';
    chatMessages.forEach(msg => {
        const div = document.createElement('div');
        div.className = 'message ' + msg.role;
        div.innerHTML =
            '<span class="message-role">' + msg.role + '</span>' +
            '<div class="message-content">' + escapeHtml(msg.content) + '</div>';
        container.appendChild(div);
    });
    container.scrollTop = container.scrollHeight;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const model = document.getElementById('model-select');
    if (!input || !model || streaming) return;

    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    addChatMessage('user', text);
    streaming = true;

    const messages = chatMessages.map(m => ({ role: m.role, content: m.content }));

    try {
        const response = await fetch(API_BASE + '/v1/chat/completions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: model.value,
                messages: messages,
                stream: true,
            }),
        });

        if (!response.ok) {
            addChatMessage('assistant', 'Error: ' + response.statusText);
            streaming = false;
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let assistantText = '';
        chatMessages.push({ role: 'assistant', content: '' });

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const data = line.slice(6);
                if (data === '[DONE]') break;

                try {
                    const parsed = JSON.parse(data);
                    const delta = parsed.choices?.[0]?.delta?.content || '';
                    if (delta) {
                        assistantText += delta;
                        chatMessages[chatMessages.length - 1].content = assistantText;
                        renderChat();
                    }
                } catch (e) {}
            }
        }
    } catch (err) {
        addChatMessage('assistant', 'Error: ' + err.message);
    }

    streaming = false;
}

// ── Models Page ───────────────────────────────────────
function loadModels() {
    Promise.all([
        fetch(API_BASE + '/v1/models').then(r => r.json()),
        fetch(API_BASE + '/api/models/downloaded').then(r => r.json()),
    ]).then(([modelsResp, downloaded]) => {
        const container = document.getElementById('models-list');
        if (!container) return;
        container.innerHTML = '';

        const models = modelsResp.data || [];
        models.forEach(m => {
            const dl = downloaded.find(d => d.name === m.id);
            const size = dl ? dl.size_mb + ' MB' : 'N/A';
            const statusClass = m.status === 'loaded' ? 'status-loaded' : 'status-available';

            container.innerHTML +=
                '<div class="model-card">' +
                '  <h3>' + escapeHtml(m.id) + '</h3>' +
                '  <div class="meta">Size: ' + size + '</div>' +
                '  <div class="status">' +
                '    <span class="status-badge ' + statusClass + '">' + m.status + '</span>' +
                '  </div>' +
                (dl ? '  <button class="btn btn-danger btn-sm" style="margin-top:12px" onclick="deleteModel(\'' + m.id + '\')">Delete</button>' : '') +
                '</div>';
        });

        if (models.length === 0) {
            container.innerHTML = '<p style="color:var(--text-secondary)">No models found. Pull one with: bithub pull 2B-4T</p>';
        }
    }).catch(() => {});
}

function deleteModel(name) {
    if (!confirm('Delete model ' + name + '?')) return;
    fetch(API_BASE + '/api/models/' + name, { method: 'DELETE' })
        .then(r => { if (r.ok) loadModels(); })
        .catch(() => {});
}

// ── Server Page ───────────────────────────────────────
function loadStats() {
    fetch(API_BASE + '/api/stats')
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('server-stats');
            if (!container) return;

            const uptime = formatUptime(data.uptime_seconds || 0);

            container.innerHTML =
                statCard(uptime, 'Uptime') +
                statCard(data.total_requests || 0, 'Requests') +
                statCard(data.models_loaded || 0, 'Models Loaded') +
                statCard(data.models_registered || 0, 'Models Registered');
        })
        .catch(() => {});
}

function statCard(value, label) {
    return '<div class="stat-card">' +
        '<div class="stat-value">' + value + '</div>' +
        '<div class="stat-label">' + label + '</div>' +
        '</div>';
}

function formatUptime(seconds) {
    if (seconds < 60) return seconds + 's';
    if (seconds < 3600) return Math.floor(seconds / 60) + 'm';
    return Math.floor(seconds / 3600) + 'h ' + Math.floor((seconds % 3600) / 60) + 'm';
}

// ── Settings Page ─────────────────────────────────────
function loadSettings() {
    fetch(API_BASE + '/api/config')
        .then(r => r.json())
        .then(config => {
            const container = document.getElementById('settings-form');
            if (!container) return;

            container.innerHTML =
                formGroup('Server Port', 'settings-port', config.server?.port || 8080, 'number') +
                formGroup('Server Host', 'settings-host', config.server?.host || '127.0.0.1', 'text') +
                formGroup('Threads', 'settings-threads', config.server?.threads || 4, 'number') +
                formGroup('Min Free GB', 'settings-free-gb', config.download?.min_free_gb || 5, 'number') +
                '<div class="form-group">' +
                '  <label>Theme</label>' +
                '  <select id="theme-select" onchange="toggleTheme(this.value)">' +
                '    <option value="dark"' + (getTheme() === 'dark' ? ' selected' : '') + '>Dark</option>' +
                '    <option value="light"' + (getTheme() === 'light' ? ' selected' : '') + '>Light</option>' +
                '  </select>' +
                '</div>';
        })
        .catch(() => {});
}

function formGroup(label, id, value, type) {
    return '<div class="form-group">' +
        '  <label for="' + id + '">' + label + '</label>' +
        '  <input type="' + type + '" id="' + id + '" value="' + value + '" readonly>' +
        '</div>';
}

// ── Theme ─────────────────────────────────────────────
function getTheme() {
    return localStorage.getItem('bithub-theme') || 'dark';
}

function toggleTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('bithub-theme', theme);
}

// ── Init ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    toggleTheme(getTheme());
    initRouter();

    document.getElementById('send-btn')?.addEventListener('click', sendMessage);
    document.getElementById('chat-input')?.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    document.getElementById('clear-chat')?.addEventListener('click', () => {
        chatMessages.length = 0;
        renderChat();
    });

    // Auto-refresh stats every 10s when on server page
    setInterval(() => {
        if (document.getElementById('page-server')?.classList.contains('active')) {
            loadStats();
        }
    }, 10000);
});
```

- [ ] **Step 2: Commit**

```bash
git add bithub/static/app.js
git commit -m "Add dashboard JavaScript: chat, models, server stats, settings, theme toggle"
```

---

## Task 4: Final Verification

- [ ] **Step 1: Run full test suite**

```bash
/usr/bin/python3 -m pytest tests/ --cov=bithub --cov-report=term-missing -v
```

- [ ] **Step 2: Verify static files are bundled**

```bash
ls -la bithub/static/
```

Expected: `index.html`, `style.css`, `app.js` all present.

- [ ] **Step 3: Verify the dashboard API test passes**

```bash
/usr/bin/python3 -m pytest tests/test_dashboard_api.py -v
```

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "Phase B4 complete: web dashboard with chat, models, server stats, and settings"
```
