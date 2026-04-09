/* bithub dashboard — single-page app */
const API_BASE = '';

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
    navigateTo(location.hash.replace('#/', '') || 'chat');
}

const chatMessages = [];
let streaming = false;

function loadModelSelect() {
    fetch(API_BASE + '/v1/models').then(r => r.json()).then(data => {
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
    }).catch(() => {});
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
        div.innerHTML = '<span class="message-role">' + msg.role + '</span>' +
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
            body: JSON.stringify({ model: model.value, messages, stream: true }),
        });
        if (!response.ok) { addChatMessage('assistant', 'Error: ' + response.statusText); streaming = false; return; }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let assistantText = '';
        chatMessages.push({ role: 'assistant', content: '' });
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            for (const line of chunk.split('\n')) {
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
    } catch (err) { addChatMessage('assistant', 'Error: ' + err.message); }
    streaming = false;
}

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
                '<div class="model-card"><h3>' + escapeHtml(m.id) + '</h3>' +
                '<div class="meta">Size: ' + size + '</div>' +
                '<div class="status"><span class="status-badge ' + statusClass + '">' + m.status + '</span></div>' +
                (dl ? '<button class="btn btn-danger btn-sm" style="margin-top:12px" onclick="deleteModel(\'' + m.id + '\')">Delete</button>' : '') +
                '</div>';
        });
        if (!models.length) container.innerHTML = '<p style="color:var(--text-secondary)">No models found. Pull one with: bithub pull 2B-4T</p>';
    }).catch(() => {});
}

function deleteModel(name) {
    if (!confirm('Delete model ' + name + '?')) return;
    fetch(API_BASE + '/api/models/' + name, { method: 'DELETE' }).then(r => { if (r.ok) loadModels(); }).catch(() => {});
}

function loadStats() {
    fetch(API_BASE + '/api/stats').then(r => r.json()).then(data => {
        const container = document.getElementById('server-stats');
        if (!container) return;
        container.innerHTML =
            statCard(formatUptime(data.uptime_seconds || 0), 'Uptime') +
            statCard(data.total_requests || 0, 'Requests') +
            statCard(data.models_loaded || 0, 'Models Loaded') +
            statCard(data.models_registered || 0, 'Models Registered');
    }).catch(() => {});
}

function statCard(value, label) {
    return '<div class="stat-card"><div class="stat-value">' + value + '</div><div class="stat-label">' + label + '</div></div>';
}

function formatUptime(s) {
    if (s < 60) return s + 's';
    if (s < 3600) return Math.floor(s / 60) + 'm';
    return Math.floor(s / 3600) + 'h ' + Math.floor((s % 3600) / 60) + 'm';
}

function loadSettings() {
    fetch(API_BASE + '/api/config').then(r => r.json()).then(config => {
        const container = document.getElementById('settings-form');
        if (!container) return;
        container.innerHTML =
            formGroup('Server Port', 'settings-port', config.server?.port || 8080, 'number') +
            formGroup('Server Host', 'settings-host', config.server?.host || '127.0.0.1', 'text') +
            formGroup('Threads', 'settings-threads', config.server?.threads || 4, 'number') +
            formGroup('Min Free GB', 'settings-free-gb', config.download?.min_free_gb || 5, 'number') +
            '<div class="form-group"><label>Theme</label>' +
            '<select id="theme-select" onchange="toggleTheme(this.value)">' +
            '<option value="dark"' + (getTheme() === 'dark' ? ' selected' : '') + '>Dark</option>' +
            '<option value="light"' + (getTheme() === 'light' ? ' selected' : '') + '>Light</option>' +
            '</select></div>';
    }).catch(() => {});
}

function formGroup(label, id, value, type) {
    return '<div class="form-group"><label for="' + id + '">' + label + '</label>' +
        '<input type="' + type + '" id="' + id + '" value="' + value + '" readonly></div>';
}

function getTheme() { return localStorage.getItem('bithub-theme') || 'dark'; }
function toggleTheme(theme) { document.documentElement.setAttribute('data-theme', theme); localStorage.setItem('bithub-theme', theme); }

document.addEventListener('DOMContentLoaded', () => {
    toggleTheme(getTheme());
    initRouter();
    document.getElementById('send-btn')?.addEventListener('click', sendMessage);
    document.getElementById('chat-input')?.addEventListener('keydown', e => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    document.getElementById('clear-chat')?.addEventListener('click', () => { chatMessages.length = 0; renderChat(); });
    setInterval(() => {
        if (document.getElementById('page-server')?.classList.contains('active')) loadStats();
    }, 10000);
});
