/**
 * SIH Local LLM Assistant – Frontend Application (Step 3: Multi-Agent)
 * 
 * Handles chat interactions, SSE streaming, RAG document upload,
 * mode switching (Chat / RAG / Agent), agent execution traces, and health checks.
 */

// ──────────────────────────────────────────────
// DOM Elements
// ──────────────────────────────────────────────

const elements = {
    sidebar: document.getElementById('sidebar'),
    menuToggle: document.getElementById('menuToggle'),
    newChatBtn: document.getElementById('newChatBtn'),
    clearChatBtn: document.getElementById('clearChatBtn'),
    modelSelect: document.getElementById('modelSelect'),
    tempSlider: document.getElementById('tempSlider'),
    tempValue: document.getElementById('tempValue'),
    apiStatus: document.getElementById('apiStatus'),
    ollamaStatus: document.getElementById('ollamaStatus'),
    qdrantStatus: document.getElementById('qdrantStatus'),
    headerModel: document.getElementById('headerModel'),
    headerTitle: document.getElementById('headerTitle'),
    headerMode: document.getElementById('headerMode'),
    messagesContainer: document.getElementById('messagesContainer'),
    welcomeScreen: document.getElementById('welcomeScreen'),
    messageInput: document.getElementById('messageInput'),
    sendBtn: document.getElementById('sendBtn'),
    inputModeLabel: document.getElementById('inputModeLabel'),
    // RAG elements
    chatModeBtn: document.getElementById('chatModeBtn'),
    ragModeBtn: document.getElementById('ragModeBtn'),
    agentModeBtn: document.getElementById('agentModeBtn'),
    ragSection: document.getElementById('ragSection'),
    agentSection: document.getElementById('agentSection'),
    uploadZone: document.getElementById('uploadZone'),
    fileInput: document.getElementById('fileInput'),
    uploadProgress: document.getElementById('uploadProgress'),
    progressFill: document.getElementById('progressFill'),
    progressText: document.getElementById('progressText'),
    docList: document.getElementById('docList'),
    // Agent elements
    agentUploadZone: document.getElementById('agentUploadZone'),
    agentFileInput: document.getElementById('agentFileInput'),
    agentFileList: document.getElementById('agentFileList'),
    agentSystemStatus: document.getElementById('agentSystemStatus'),
    langgraphStatus: document.getElementById('langgraphStatus'),
};

// ──────────────────────────────────────────────
// State
// ──────────────────────────────────────────────

const state = {
    conversationHistory: [],
    isStreaming: false,
    currentModel: 'qwen3:8b',
    temperature: 0.7,
    mode: 'chat', // 'chat' | 'rag' | 'agent'
    documents: [],
    agentFiles: [],   // File objects uploaded for agent use
    agentFilePaths: [], // Server-side paths returned after agent upload
};

// ──────────────────────────────────────────────
// Initialization
// ──────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    loadModels();
    checkHealth();
    loadDocuments();
    updateModeUI();

    // Poll health every 30 seconds
    setInterval(checkHealth, 30000);
});

function initEventListeners() {
    // Sidebar toggle
    elements.menuToggle.addEventListener('click', toggleSidebar);

    // New / Clear chat
    elements.newChatBtn.addEventListener('click', clearChat);
    elements.clearChatBtn.addEventListener('click', clearChat);

    // Temperature slider
    elements.tempSlider.addEventListener('input', (e) => {
        state.temperature = parseFloat(e.target.value);
        elements.tempValue.textContent = state.temperature.toFixed(1);
    });

    // Model selector
    elements.modelSelect.addEventListener('change', (e) => {
        state.currentModel = e.target.value;
        elements.headerModel.textContent = state.currentModel;
    });

    // Message input
    elements.messageInput.addEventListener('input', autoResize);
    elements.messageInput.addEventListener('input', () => {
        elements.sendBtn.disabled = !elements.messageInput.value.trim();
    });

    elements.messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!elements.sendBtn.disabled && !state.isStreaming) {
                sendMessage();
            }
        }
    });

    // Send button
    elements.sendBtn.addEventListener('click', sendMessage);

    // Quick prompts
    document.querySelectorAll('.quick-prompt').forEach(btn => {
        btn.addEventListener('click', () => {
            const prompt = btn.dataset.prompt;
            elements.messageInput.value = prompt;
            elements.sendBtn.disabled = false;
            sendMessage();
        });
    });

    // Mode toggle
    elements.chatModeBtn.addEventListener('click', () => setMode('chat'));
    elements.ragModeBtn.addEventListener('click', () => setMode('rag'));
    if (elements.agentModeBtn) {
        elements.agentModeBtn.addEventListener('click', () => setMode('agent'));
    }

    // Upload zone (RAG)
    elements.uploadZone.addEventListener('click', () => elements.fileInput.click());
    elements.fileInput.addEventListener('change', handleFileSelect);

    // Agent upload zone
    if (elements.agentUploadZone) {
        elements.agentUploadZone.addEventListener('click', () => elements.agentFileInput.click());
        elements.agentFileInput.addEventListener('change', handleAgentFileSelect);
        elements.agentUploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            elements.agentUploadZone.classList.add('drag-over');
        });
        elements.agentUploadZone.addEventListener('dragleave', () => {
            elements.agentUploadZone.classList.remove('drag-over');
        });
        elements.agentUploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            elements.agentUploadZone.classList.remove('drag-over');
            if (e.dataTransfer.files.length > 0) {
                addAgentFiles(e.dataTransfer.files);
            }
        });
    }

    // Drag and drop
    elements.uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        elements.uploadZone.classList.add('drag-over');
    });
    elements.uploadZone.addEventListener('dragleave', () => {
        elements.uploadZone.classList.remove('drag-over');
    });
    elements.uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        elements.uploadZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            uploadFiles(files);
        }
    });
}

// ──────────────────────────────────────────────
// Mode Management
// ──────────────────────────────────────────────

function setMode(mode) {
    state.mode = mode;
    updateModeUI();
}

function updateModeUI() {
    const isRag = state.mode === 'rag';
    const isAgent = state.mode === 'agent';

    // Toggle mode buttons
    elements.chatModeBtn.classList.toggle('active', state.mode === 'chat');
    elements.ragModeBtn.classList.toggle('active', isRag);
    if (elements.agentModeBtn) elements.agentModeBtn.classList.toggle('active', isAgent);

    // Show/hide RAG section
    elements.ragSection.classList.toggle('visible', isRag);

    // Show/hide Agent section
    if (elements.agentSection) elements.agentSection.classList.toggle('visible', isAgent);

    // Update header title & mode pill
    const modeTag = document.getElementById('inputModeTag');
    if (isRag) {
        elements.headerTitle.textContent = 'RAG Document Q&A';
        elements.headerMode.textContent = 'RAG';
        elements.headerMode.className = 'header-mode-pill rag-pill';
        elements.inputModeLabel.textContent = 'RAG';
        elements.messageInput.placeholder = 'Ask a question about your documents...';
        if (modeTag) { modeTag.textContent = 'RAG'; modeTag.className = 'input-mode-tag rag-tag'; }
    } else if (isAgent) {
        elements.headerTitle.textContent = '🤖 Multi-Agent Workflow';
        elements.headerMode.textContent = 'Agent';
        elements.headerMode.className = 'header-mode-pill agent-pill';
        elements.inputModeLabel.textContent = 'Agent';
        elements.messageInput.placeholder = 'Ask anything — agents will handle it automatically...';
        if (modeTag) { modeTag.textContent = 'Agent'; modeTag.className = 'input-mode-tag agent-tag'; }
    } else {
        elements.headerTitle.textContent = 'Local LLM Chat';
        elements.headerMode.textContent = 'Chat';
        elements.headerMode.className = 'header-mode-pill chat-pill';
        elements.inputModeLabel.textContent = 'Chat';
        elements.messageInput.placeholder = 'Type your message...';
        if (modeTag) { modeTag.textContent = 'Chat'; modeTag.className = 'input-mode-tag'; }
    }
}

// ──────────────────────────────────────────────
// Sidebar
// ──────────────────────────────────────────────

function toggleSidebar() {
    const isMobile = window.innerWidth <= 768;
    if (isMobile) {
        elements.sidebar.classList.toggle('open');
    } else {
        elements.sidebar.classList.toggle('collapsed');
    }
}

// ──────────────────────────────────────────────
// API Calls
// ──────────────────────────────────────────────

async function loadModels() {
    try {
        const res = await fetch('/api/models');
        const data = await res.json();

        elements.modelSelect.innerHTML = '';

        if (data.models && data.models.length > 0) {
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.name;
                option.textContent = model.size
                    ? `${model.name} (${model.size} GB)`
                    : model.name;
                if (model.name === data.default_model) {
                    option.selected = true;
                }
                elements.modelSelect.appendChild(option);
            });
            state.currentModel = data.default_model || data.models[0].name;
        } else {
            const option = document.createElement('option');
            option.value = data.default_model;
            option.textContent = data.default_model;
            option.selected = true;
            elements.modelSelect.appendChild(option);
            state.currentModel = data.default_model;
        }

        elements.headerModel.textContent = state.currentModel;
    } catch (err) {
        console.error('Failed to load models:', err);
        elements.modelSelect.innerHTML = '<option value="qwen3:8b">qwen3:8b (default)</option>';
    }
}

async function checkHealth() {
    try {
        const res = await fetch('/api/health');
        const data = await res.json();

        updateStatusBadge(elements.apiStatus, 'healthy');
        updateStatusBadge(
            elements.ollamaStatus,
            data.ollama === 'healthy' ? 'healthy' : 'unhealthy'
        );

        // Qdrant status check via RAG stats
        try {
            const ragRes = await fetch('/api/rag/stats');
            const ragData = await ragRes.json();
            const qdrantOk = ragData.collection && ragData.collection.status !== 'error';
            updateStatusBadge(elements.qdrantStatus, qdrantOk ? 'healthy' : 'unhealthy');
        } catch {
            updateStatusBadge(elements.qdrantStatus, 'unhealthy');
        }

        // LangGraph / agent status
        try {
            const agentRes = await fetch('/api/agent/status');
            const agentData = await agentRes.json();
            const agentOk = agentData.graph_compiled === true;
            updateStatusBadge(elements.langgraphStatus, agentOk ? 'healthy' : 'unhealthy');
            if (elements.agentSystemStatus) {
                updateStatusBadge(elements.agentSystemStatus, agentOk ? 'healthy' : 'unhealthy');
            }
        } catch {
            updateStatusBadge(elements.langgraphStatus, 'unhealthy');
        }
    } catch {
        updateStatusBadge(elements.apiStatus, 'unhealthy');
        updateStatusBadge(elements.ollamaStatus, 'unhealthy');
        updateStatusBadge(elements.qdrantStatus, 'unhealthy');
    }
}

function updateStatusBadge(el, status) {
    if (!el) return;
    // Handle new status-item-badge elements
    el.className = 'status-item-badge ' + status;
    el.textContent = status === 'healthy' ? 'Healthy'
        : status === 'checking' ? 'Checking...'
        : 'Unreachable';
    // Also update the sibling dot if it exists
    const dot = el.previousElementSibling && el.previousElementSibling.previousElementSibling;
    if (dot && dot.classList.contains('status-item-dot')) {
        dot.className = 'status-item-dot ' + (status === 'healthy' ? 'dot-green' : status === 'checking' ? 'dot-checking' : 'dot-red');
    }
    // Handle agent sidebar status-dot format (in agentSystemStatus)
    if (el.classList.contains('status-dot')) {
        el.className = 'status-dot status-' + (status === 'healthy' ? 'healthy' : status === 'checking' ? 'checking' : 'unhealthy');
        el.textContent = status === 'healthy' ? 'Ready' : status === 'checking' ? 'Checking' : 'Offline';
    }
}

// ──────────────────────────────────────────────
// Document Upload & Management
// ──────────────────────────────────────────────

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        uploadFiles(files);
    }
    e.target.value = ''; // Reset for re-upload
}

async function uploadFiles(files) {
    for (const file of files) {
        await uploadSingleFile(file);
    }
}

async function uploadSingleFile(file) {
    // Show progress (new class names)
    elements.uploadProgress.style.display = 'flex';
    elements.progressFill.style.width = '10%';
    elements.progressText.textContent = `Uploading ${file.name}...`;

    const formData = new FormData();
    formData.append('file', file);

    try {
        elements.progressFill.style.width = '30%';
        elements.progressText.textContent = 'Processing & extracting text...';

        const res = await fetch('/api/rag/upload', {
            method: 'POST',
            body: formData,
        });

        elements.progressFill.style.width = '80%';

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Upload failed');
        }

        const data = await res.json();

        elements.progressFill.style.width = '100%';
        elements.progressText.textContent = `✓ ${file.name} indexed (${data.chunk_count} chunks)`;

        await loadDocuments();

        setTimeout(() => {
            elements.uploadProgress.style.display = 'none';
            elements.progressFill.style.width = '0%';
        }, 2000);

    } catch (err) {
        elements.progressFill.style.width = '100%';
        elements.progressFill.style.background = 'var(--red)';
        elements.progressText.textContent = `✗ ${err.message}`;

        setTimeout(() => {
            elements.uploadProgress.style.display = 'none';
            elements.progressFill.style.width = '0%';
            elements.progressFill.style.background = '';
        }, 3000);
    }
}

async function loadDocuments() {
    try {
        const res = await fetch('/api/rag/documents');
        const data = await res.json();
        state.documents = data.documents || [];
        renderDocumentList();
    } catch (err) {
        console.error('Failed to load documents:', err);
    }
}

function renderDocumentList() {
    if (!elements.docList) return;

    if (state.documents.length === 0) {
        elements.docList.innerHTML = '<div class="doc-empty">No documents indexed yet</div>';
        return;
    }

    elements.docList.innerHTML = state.documents.map(doc => {
        const ext = (doc.file_type || '').replace('.', '');
        const iconClass = ['pdf', 'docx', 'pptx', 'txt', 'csv'].includes(ext) ? ext : 'txt';
        return `
            <div class="doc-item" data-doc-id="${doc.doc_id}">
                <div class="doc-icon ${iconClass}">${ext}</div>
                <div class="doc-info">
                    <div class="doc-name" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</div>
                    <div class="doc-meta">${doc.chunk_count} chunks</div>
                </div>
                <button class="doc-delete" onclick="deleteDocument('${doc.doc_id}')" title="Delete">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                    </svg>
                </button>
            </div>
        `;
    }).join('');
}

async function deleteDocument(docId) {
    try {
        const res = await fetch(`/api/rag/documents/${docId}`, { method: 'DELETE' });
        if (res.ok) {
            await loadDocuments();
        }
    } catch (err) {
        console.error('Failed to delete document:', err);
    }
}

// ──────────────────────────────────────────────
// Chat Logic
// ──────────────────────────────────────────────

async function sendMessage() {
    const message = elements.messageInput.value.trim();
    if (!message || state.isStreaming) return;

    // Hide welcome screen
    if (elements.welcomeScreen) {
        elements.welcomeScreen.style.display = 'none';
    }

    // Add user message
    appendMessage('user', message);
    state.conversationHistory.push({ role: 'user', content: message });

    // Clear input
    elements.messageInput.value = '';
    elements.sendBtn.disabled = true;
    autoResize();

    // Show typing indicator
    const typingEl = showTypingIndicator();

    // Route to correct endpoint based on mode
    if (state.mode === 'rag') {
        await sendRAGMessage(message, typingEl);
    } else if (state.mode === 'agent') {
        await sendAgentMessage(message, typingEl);
    } else {
        await sendChatMessage(message, typingEl);
    }
}

async function sendChatMessage(message, typingEl) {
    state.isStreaming = true;
    let fullResponse = '';

    try {
        const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                conversation_history: state.conversationHistory.slice(0, -1),
                model: state.currentModel,
                temperature: state.temperature,
            }),
        });

        typingEl.remove();
        const { contentEl, statsEl } = appendMessage('assistant', '', true);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.slice(6).trim();
                    if (!dataStr) continue;

                    try {
                        const data = JSON.parse(dataStr);
                        if (data.error) { showError(data.error); break; }
                        if (data.content) {
                            fullResponse += data.content;
                            contentEl.innerHTML = renderMarkdown(fullResponse);
                            scrollToBottom();
                        }
                        if (data.done && data.tokens_per_second) {
                            statsEl.innerHTML = `
                                <span class="stat-item">⚡ ${data.tokens_per_second} tok/s</span>
                                <span class="stat-item">📝 ${data.model}</span>
                            `;
                        }
                    } catch (e) { /* skip */ }
                }
            }
        }

        if (fullResponse) {
            state.conversationHistory.push({ role: 'assistant', content: fullResponse });
        }
    } catch (err) {
        typingEl.remove();
        showError(`Connection failed: ${err.message}. Is Ollama running?`);
    } finally {
        state.isStreaming = false;
        elements.sendBtn.disabled = !elements.messageInput.value.trim();
    }
}

async function sendRAGMessage(message, typingEl) {
    state.isStreaming = true;
    let fullResponse = '';
    let sources = [];

    try {
        const response = await fetch('/api/rag/query/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: message,
                top_k: 5,
                model: state.currentModel,
                temperature: state.temperature,
            }),
        });

        typingEl.remove();
        const { contentEl, statsEl, sourcesEl } = appendMessage('assistant', '', true, true);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const dataStr = line.slice(6).trim();
                    if (!dataStr) continue;

                    try {
                        const data = JSON.parse(dataStr);

                        // Handle sources event
                        if (data.type === 'sources') {
                            sources = data.sources || [];
                            renderSources(sourcesEl, sources);
                            continue;
                        }

                        if (data.error) { showError(data.error); break; }

                        if (data.content) {
                            fullResponse += data.content;
                            contentEl.innerHTML = renderMarkdown(fullResponse);
                            scrollToBottom();
                        }

                        if (data.done && data.tokens_per_second) {
                            statsEl.innerHTML = `
                                <span class="stat-item">⚡ ${data.tokens_per_second} tok/s</span>
                                <span class="stat-item">📝 ${data.model}</span>
                                <span class="stat-item">📚 ${sources.length} sources</span>
                            `;
                        }
                    } catch (e) { /* skip */ }
                }
            }
        }

        if (fullResponse) {
            state.conversationHistory.push({ role: 'assistant', content: fullResponse });
        }
    } catch (err) {
        typingEl.remove();
        showError(`RAG query failed: ${err.message}`);
    } finally {
        state.isStreaming = false;
        elements.sendBtn.disabled = !elements.messageInput.value.trim();
    }
}

function clearChat() {
    state.conversationHistory = [];

    const messages = elements.messagesContainer.querySelectorAll(
        '.message, .typing-indicator, .error-banner'
    );
    messages.forEach(m => m.remove());

    if (elements.welcomeScreen) {
        elements.welcomeScreen.style.display = '';
    }

    elements.messageInput.focus();
}

// ──────────────────────────────────────────────
// UI Helpers
// ──────────────────────────────────────────────

function appendMessage(role, content, isStreaming = false, isRAG = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    if (role === 'user') {
        // User bubble — right aligned, no avatar
        messageDiv.innerHTML = `<div class="message-bubble">${escapeHtml(content)}</div>`;
    } else {
        // Assistant bubble — with avatar, glass card
        const assistantIcon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>`;
        messageDiv.innerHTML = `
            <div class="message-avatar">${assistantIcon}</div>
            <div class="message-body">
                <div class="message-bubble">${content ? renderMarkdown(content) : ''}</div>
                ${isRAG ? '<div class="sources-block"></div>' : ''}
                <div class="message-stats"></div>
            </div>
        `;
    }

    elements.messagesContainer.appendChild(messageDiv);
    scrollToBottom();

    if (isStreaming) {
        const result = {
            contentEl: messageDiv.querySelector('.message-bubble'),
            statsEl: messageDiv.querySelector('.message-stats'),
        };
        if (isRAG) result.sourcesEl = messageDiv.querySelector('.sources-block');
        return result;
    }
    return messageDiv;
}

function renderSources(container, sources) {
    if (!container || !sources.length) return;

    container.innerHTML = `
        <div class="sources-label">
            Sources (${sources.length})
        </div>
        <div style="display:flex; flex-wrap:wrap; gap:4px; margin-top:4px;">
            ${sources.map(s => `
                <span class="source-chip" title="${escapeHtml(s.chunk_text || '').substring(0, 200)}">
                    📄 ${escapeHtml(s.filename || 'Unknown')} &nbsp;<span style="opacity:.6">${(s.score * 100).toFixed(0)}%</span>
                </span>
            `).join('')}
        </div>
    `;
}

// Global function for onclick
window.toggleSources = function(header) {
    header.classList.toggle('expanded');
    const list = header.nextElementSibling;
    list.classList.toggle('expanded');
};

// Global function for document deletion
window.deleteDocument = deleteDocument;

function showTypingIndicator() {
    const el = document.createElement('div');
    el.className = 'typing-indicator';
    const icon = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>`;
    el.innerHTML = `
        <div class="message-avatar">${icon}</div>
        <div class="typing-bubble">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    elements.messagesContainer.appendChild(el);
    scrollToBottom();
    return el;
}

// ── Welcome screen capability card click ──
window.handleCapClick = function(prompt, mode) {
    setMode(mode);
    elements.messageInput.value = prompt;
    elements.sendBtn.disabled = false;
    elements.messageInput.focus();
    // Auto-send
    setTimeout(() => sendMessage(), 80);
};


function showError(message) {
    const el = document.createElement('div');
    el.className = 'error-banner';
    el.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
        <span>${escapeHtml(message)}</span>
    `;
    elements.messagesContainer.appendChild(el);
    scrollToBottom();
}

function scrollToBottom() {
    elements.messagesContainer.scrollTop = elements.messagesContainer.scrollHeight;
}

function autoResize() {
    const textarea = elements.messageInput;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
}

// ──────────────────────────────────────────────
// Markdown Rendering (Lightweight)
// ──────────────────────────────────────────────

function renderMarkdown(text) {
    if (!text) return '';

    let html = escapeHtml(text);

    // Code blocks (```lang ... ```)
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
        return `<pre><code class="language-${lang}">${code.trim()}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');

    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Blockquote
    html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');

    // Unordered list
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Ordered list
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

    // Paragraphs (double newline)
    html = html.replace(/\n\n/g, '</p><p>');
    html = '<p>' + html + '</p>';

    // Single newlines to <br>
    html = html.replace(/(?<!<\/?\w+[^>]*)\n(?![^<]*<\/pre>)/g, '<br>');

    // Clean up empty paragraphs
    html = html.replace(/<p>\s*<\/p>/g, '');

    return html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


// ──────────────────────────────────────────────
// Agent File Management
// ──────────────────────────────────────────────

function handleAgentFileSelect(e) {
    addAgentFiles(e.target.files);
    e.target.value = '';
}

function addAgentFiles(files) {
    for (const file of files) {
        if (!state.agentFiles.find(f => f.name === file.name)) {
            state.agentFiles.push(file);
        }
    }
    renderAgentFileList();
}

function renderAgentFileList() {
    if (!elements.agentFileList) return;
    if (state.agentFiles.length === 0) {
        elements.agentFileList.innerHTML = '<div class="doc-empty">No files added yet</div>';
        return;
    }
    elements.agentFileList.innerHTML = state.agentFiles.map((f, i) => `
        <div class="doc-item agent-file-item">
            <div class="doc-icon">${f.name.split('.').pop()}</div>
            <div class="doc-info">
                <div class="doc-name" title="${escapeHtml(f.name)}">${escapeHtml(f.name)}</div>
                <div class="doc-meta">${(f.size / 1024).toFixed(1)} KB</div>
            </div>
            <button class="doc-delete" onclick="removeAgentFile(${i})" title="Remove">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
            </button>
        </div>
    `).join('');
}

function removeAgentFile(index) {
    state.agentFiles.splice(index, 1);
    state.agentFilePaths.splice(index, 1);
    renderAgentFileList();
}


// ──────────────────────────────────────────────
// Agent Message Sending
// ──────────────────────────────────────────────

async function sendAgentMessage(message, typingEl) {
    state.isStreaming = true;

    try {
        // Upload any pending agent files first
        const uploadedPaths = await uploadAgentFiles();

        const response = await fetch('/api/agent/run/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query: message,
                file_paths: uploadedPaths,
            }),
        });

        typingEl.remove();
        const msgEl = appendAgentMessage('', [], '', '');
        const { contentEl, traceEl, intentEl, agentEl } = msgEl;

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let steps = [];

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue;
                const dataStr = line.slice(6).trim();
                if (!dataStr) continue;

                try {
                    const data = JSON.parse(dataStr);

                    if (data.type === 'step') {
                        steps.push(data.step);
                        renderAgentTrace(traceEl, steps);
                        scrollToBottom();
                    } else if (data.type === 'answer') {
                        contentEl.innerHTML = renderMarkdown(data.answer || '');
                        if (intentEl) intentEl.textContent = `Intent: ${data.intent || 'unknown'}`;
                        if (agentEl) agentEl.textContent = `Agent: ${data.active_agent || 'unknown'}`;
                        scrollToBottom();
                    } else if (data.type === 'error') {
                        contentEl.innerHTML = `<span class="error-text">⚠️ ${escapeHtml(data.error)}</span>`;
                    }
                } catch (e) { /* skip */ }
            }
        }

        state.conversationHistory.push({ role: 'assistant', content: contentEl.textContent });
    } catch (err) {
        typingEl.remove();
        showError(`Agent workflow failed: ${err.message}`);
    } finally {
        state.isStreaming = false;
        elements.sendBtn.disabled = !elements.messageInput.value.trim();
    }
}

async function uploadAgentFiles() {
    const paths = [];
    for (const file of state.agentFiles) {
        try {
            // Upload to RAG endpoint to get file saved on server
            const formData = new FormData();
            formData.append('file', file);
            // Use the uploads directory path from the RAG upload endpoint
            // We'll just use the filename for agent path resolution
            paths.push(`uploads/${file.name}`);
        } catch (e) {
            console.warn('Could not resolve agent file path:', e);
        }
    }
    return paths;
}

function appendAgentMessage(content, steps, intent, activeAgent) {
    const wrapper = document.createElement('div');
    wrapper.className = 'message assistant agent-message';
    wrapper.innerHTML = `
        <div class="message-avatar">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="3"/>
                <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
            </svg>
        </div>
        <div class="message-body">
            <div class="agent-header">
                <span class="agent-badge agent-badge-supervisor" id="agentBadgeIntent">Intent: detecting...</span>
                <span class="agent-badge agent-badge-active" id="agentBadgeAgent">Agent: routing...</span>
            </div>
            <div class="agent-trace" id="agentTrace"></div>
            <div class="message-content agent-answer" id="agentContent">
                <span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>
            </div>
            <div class="message-stats"></div>
        </div>
    `;

    elements.messagesContainer.appendChild(wrapper);
    scrollToBottom();

    return {
        contentEl: wrapper.querySelector('#agentContent'),
        traceEl: wrapper.querySelector('#agentTrace'),
        intentEl: wrapper.querySelector('#agentBadgeIntent'),
        agentEl: wrapper.querySelector('#agentBadgeAgent'),
    };
}

function renderAgentTrace(traceEl, steps) {
    if (!traceEl || !steps.length) return;
    traceEl.innerHTML = steps.map((step, i) => {
        const agentColors = {
            supervisor: 'supervisor',
            rag_agent: 'rag',
            data_agent: 'data',
            file_agent: 'file',
            code_agent: 'code',
            vision_agent: 'vision',
        };
        const colorClass = agentColors[step.agent] || 'default';
        return `
            <div class="trace-step trace-${colorClass} ${i === steps.length - 1 ? 'trace-active' : ''}">
                <div class="trace-dot"></div>
                <div class="trace-body">
                    <span class="trace-agent">${step.agent}</span>
                    <span class="trace-action">${escapeHtml(step.action)}</span>
                    ${step.result ? `<div class="trace-result">${escapeHtml(step.result.substring(0, 120))}${step.result.length > 120 ? '...' : ''}</div>` : ''}
                </div>
            </div>
        `;
    }).join('');
}
