let sessionId = null;
let currentData = null;
let activeTab = 'summary';

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function setLoading(active) {
    const loader = document.getElementById('loader');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const clearBtn = document.getElementById('clearBtn');
    if (active) {
        loader.classList.remove('hidden');
        analyzeBtn.disabled = true;
        clearBtn.disabled = true;
    } else {
        loader.classList.add('hidden');
        analyzeBtn.disabled = false;
        clearBtn.disabled = false;
        document.getElementById('progressBar').value = 0;
    }
}

async function processVideo() {
    const source = document.getElementById('source').value;
    const language = document.getElementById('language').value;
    if (!source) {
        alert('Please provide a YouTube URL or file path.');
        return;
    }

    setLoading(true);
    document.getElementById('loaderText').textContent = 'Processing...';
    document.getElementById('spinner').style.display = '';
    document.getElementById('progressBar').style.display = '';

    const progress = document.getElementById('progressBar');
    let p = 5;
    progress.value = p;
    const updater = setInterval(() => {
        p = Math.min(98, p + Math.random() * 8);
        progress.value = Math.floor(p);
    }, 600);

    try {
        const resp = await fetch('/pipeline', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source, language })
        });

        if (!resp.ok) throw new Error('Server error');

        const data = await resp.json();
        sessionId = data.session_id;
        currentData = data;

        // Hide welcome screen and show results container
        document.getElementById('welcomeCard').classList.add('hidden');
        const resultsCard = document.getElementById('resultsCard');
        resultsCard.classList.remove('hidden');

        // Set video title
        document.getElementById('resultsTitle').textContent = `📋 ${data.title || 'Video Analysis Results'}`;

        // Populate badges and render active tab
        updateTabBadges();
        switchTab('summary');

        // Show chat interface
        document.getElementById('chatSection').classList.remove('hidden');

    } catch (err) {
        console.error(err);
        alert('Failed to process video. Check API connection / Mistral key.');
    } finally {
        clearInterval(updater);
        document.getElementById('progressBar').value = 100;
        document.getElementById('spinner').style.display = 'none';
        document.getElementById('progressBar').style.display = 'none';
        document.getElementById('loaderText').textContent = 'Processed!';
        setTimeout(() => setLoading(false), 1500);
    }
}

function clearAll() {
    document.getElementById('source').value = '';
    document.getElementById('language').value = 'english';
    document.getElementById('chatMessages').innerHTML = '';
    document.getElementById('chatSection').classList.add('hidden');
    document.getElementById('resultsCard').classList.add('hidden');
    document.getElementById('welcomeCard').classList.remove('hidden');
    sessionId = null;
    currentData = null;
}

function searchTimestamp(ts) {
    const chatInput = document.getElementById('question');
    if (chatInput) {
        chatInput.value = `Tell me what was discussed around timestamp ${ts}`;
        chatInput.focus();
    }
}

// Regex parser to extract [KEY]: value blocks from structured LLM responses
function parseStructuredList(text) {
    if (!text) return [];
    
    // Split text by numbered item beginnings e.g. "1. [DECISION]:"
    const rawItems = text.split(/(?:\r?\n)+(?=\d+\.\s*\[)/);
    let itemsToProcess = rawItems;
    
    if (itemsToProcess.length <= 1) {
        // Fallback split by double newlines
        itemsToProcess = text.split(/(?:\r?\n){2,}/);
    }
    
    const results = [];
    for (let rawItem of itemsToProcess) {
        rawItem = rawItem.trim();
        if (!rawItem) continue;
        
        const lines = rawItem.split(/\r?\n/);
        const entry = {};
        
        for (let line of lines) {
            line = line.trim();
            // remove leading list numbers (e.g. "1. ")
            line = line.replace(/^\d+\.\s*/, '');
            
            const match = line.match(/^\[([A-Za-z_]+)\]:\s*(.*)/);
            if (match) {
                const key = match[1].toUpperCase();
                const val = match[2].trim();
                entry[key] = val;
            }
        }
        
        if (Object.keys(entry).length > 0) {
            results.push(entry);
        }
    }
    return results;
}

function getPriorityBadgeClass(priority) {
    if (!priority) return 'badge low';
    const p = priority.toUpperCase();
    if (p.includes('CRITICAL')) return 'badge critical';
    if (p.includes('HIGH')) return 'badge high';
    if (p.includes('MEDIUM')) return 'badge medium';
    if (p.includes('LOW')) return 'badge low';
    return 'badge low';
}

function getImpactBadgeClass(impact) {
    if (!impact) return 'badge tactical';
    const imp = impact.toUpperCase();
    if (imp.includes('STRATEGIC')) return 'badge strategic';
    if (imp.includes('TACTICAL')) return 'badge tactical';
    return 'badge tactical';
}

function renderActionItem(item, idx) {
    const task = item.TASK || "Unnamed Task";
    const owner = item.OWNER || "Not specified";
    const deadline = item.DEADLINE || "Not specified";
    const priority = item.PRIORITY || "LOW";
    const timestamp = item.TIMESTAMP || "";
    
    const tsHtml = timestamp && timestamp !== 'Not specified' ? `<span class="badge timestamp" onclick="searchTimestamp('${escapeHtml(timestamp)}')">🕒 ${escapeHtml(timestamp)}</span>` : '';
    const priorityBadge = `<span class="${getPriorityBadgeClass(priority)}">${escapeHtml(priority)}</span>`;
    
    return `
    <div class="insight-card">
        <div class="card-header">
            <span class="card-title">${idx + 1}. ${escapeHtml(task)}</span>
            <div style="display: flex; gap: 6px; align-items: center;">
                ${priorityBadge}
                ${tsHtml}
            </div>
        </div>
        <div class="card-meta-grid">
            <div class="meta-item">👤 <strong>Owner:</strong> ${escapeHtml(owner)}</div>
            <div class="meta-item">📅 <strong>Deadline:</strong> ${escapeHtml(deadline)}</div>
        </div>
    </div>
    `;
}

function renderDecision(item, idx) {
    const decision = item.DECISION || "Decision statement";
    const rationale = item.RATIONALE || "";
    const stakeholders = item.STAKEHOLDERS || "Not specified";
    const impact = item.IMPACT || "TACTICAL";
    const timestamp = item.TIMESTAMP || "";
    
    const tsHtml = timestamp && timestamp !== 'Not specified' ? `<span class="badge timestamp" onclick="searchTimestamp('${escapeHtml(timestamp)}')">🕒 ${escapeHtml(timestamp)}</span>` : '';
    const impactBadge = `<span class="${getImpactBadgeClass(impact)}">${escapeHtml(impact)}</span>`;
    
    return `
    <div class="insight-card">
        <div class="card-header">
            <span class="card-title" style="color: #c084fc;">${idx + 1}. ${escapeHtml(decision)}</span>
            <div style="display: flex; gap: 6px; align-items: center;">
                ${impactBadge}
                ${tsHtml}
            </div>
        </div>
        ${rationale ? `<p style="font-size: 13px; color: var(--text-muted); line-height: 1.5; margin-top: 4px;">${escapeHtml(rationale)}</p>` : ''}
        <div class="card-meta-grid">
            <div class="meta-item">👥 <strong>Stakeholders:</strong> ${escapeHtml(stakeholders)}</div>
        </div>
    </div>
    `;
}

function renderQuestionCard(item, idx) {
    const question = item.QUESTION || "Question statement";
    const context = item.CONTEXT || "";
    const askedBy = item.ASKED_BY || "Not specified";
    const priority = item.PRIORITY || "LOW";
    const timestamp = item.TIMESTAMP || "";
    
    const tsHtml = timestamp && timestamp !== 'Not specified' ? `<span class="badge timestamp" onclick="searchTimestamp('${escapeHtml(timestamp)}')">🕒 ${escapeHtml(timestamp)}</span>` : '';
    const priorityBadge = `<span class="${getPriorityBadgeClass(priority)}">${escapeHtml(priority)}</span>`;
    
    return `
    <div class="insight-card">
        <div class="card-header">
            <span class="card-title" style="color: #60a5fa;">${idx + 1}. ${escapeHtml(question)}</span>
            <div style="display: flex; gap: 6px; align-items: center;">
                ${priorityBadge}
                ${tsHtml}
            </div>
        </div>
        ${context ? `<p style="font-size: 13px; color: var(--text-muted); line-height: 1.5; margin-top: 4px;">${escapeHtml(context)}</p>` : ''}
        <div class="card-meta-grid">
            <div class="meta-item">👤 <strong>Asked By:</strong> ${escapeHtml(askedBy)}</div>
        </div>
    </div>
    `;
}

function formatMarkdownBullets(text) {
    if (!text) return '';
    let html = escapeHtml(text);
    // Replace lines starting with "-" or "*" with list items
    html = html.replace(/\n\s*[-*]\s+(.*)/g, '\n<li>$1</li>');
    // wrap list items in ul using cross-platform newline matching
    html = html.replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>');
    // deduplicate nested ul tags
    html = html.replace(/<\/ul>\s*<ul>/g, '');
    // preserve double newlines
    html = html.replace(/\n\n/g, '<br><br>');
    html = html.replace(/\n/g, '<br>');
    return html;
}

function switchTab(tabName) {
    activeTab = tabName;
    
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        btn.removeAttribute('aria-selected');
    });
    
    const activeBtn = document.getElementById(`tab-${tabName}`);
    if (activeBtn) {
        activeBtn.classList.add('active');
        activeBtn.setAttribute('aria-selected', 'true');
    }
    
    const searchBox = document.getElementById('searchBox');
    if (searchBox) searchBox.value = '';
    const searchCount = document.getElementById('searchCount');
    if (searchCount) searchCount.textContent = '';

    renderTabContent();
}

function renderTabContent() {
    const tabContent = document.getElementById('tabContent');
    if (!tabContent || !currentData) return;
    
    tabContent.innerHTML = '';
    
    if (activeTab === 'summary') {
        const div = document.createElement('div');
        div.className = 'summary-content';
        div.innerHTML = formatMarkdownBullets(currentData.summary);
        tabContent.appendChild(div);
    } else if (activeTab === 'action_items') {
        const parsed = parseStructuredList(currentData.action_items);
        if (parsed.length === 0) {
            tabContent.innerHTML = `<div style="color: var(--text-muted); font-size: 14px;">No action items found.</div>`;
            return;
        }
        const container = document.createElement('div');
        container.className = 'cards-list';
        container.innerHTML = parsed.map((item, idx) => renderActionItem(item, idx)).join('');
        tabContent.appendChild(container);
    } else if (activeTab === 'key_decisions') {
        const parsed = parseStructuredList(currentData.key_decisions);
        if (parsed.length === 0) {
            tabContent.innerHTML = `<div style="color: var(--text-muted); font-size: 14px;">No key decisions found.</div>`;
            return;
        }
        const container = document.createElement('div');
        container.className = 'cards-list';
        container.innerHTML = parsed.map((item, idx) => renderDecision(item, idx)).join('');
        tabContent.appendChild(container);
    } else if (activeTab === 'open_questions') {
        const parsed = parseStructuredList(currentData.open_questions);
        if (parsed.length === 0) {
            tabContent.innerHTML = `<div style="color: var(--text-muted); font-size: 14px;">No open questions found.</div>`;
            return;
        }
        const container = document.createElement('div');
        container.className = 'cards-list';
        container.innerHTML = parsed.map((item, idx) => renderQuestionCard(item, idx)).join('');
        tabContent.appendChild(container);
    }
}

function updateTabBadges() {
    if (!currentData) return;
    
    const actionsCount = parseStructuredList(currentData.action_items).length;
    const decisionsCount = parseStructuredList(currentData.key_decisions).length;
    const questionsCount = parseStructuredList(currentData.open_questions).length;
    
    document.getElementById('badge-action_items').textContent = actionsCount;
    document.getElementById('badge-key_decisions').textContent = decisionsCount;
    document.getElementById('badge-open_questions').textContent = questionsCount;
}

function formatChatBotMessage(answer) {
    if (!answer) return 'No answer.';
    
    if (answer.includes('Sources:')) {
        const parts = answer.split('Sources:', 2);
        const ansText = parts[0].trim();
        const sourcesText = parts[1].trim();
        
        let formatted = escapeHtml(ansText);
        
        if (sourcesText && sourcesText !== 'None') {
            formatted += `<span class="sources-title">Sources</span>`;
            
            const sourceLines = sourcesText.split('\n');
            for (let line of sourceLines) {
                line = line.trim();
                if (!line) continue;
                
                const tsMatch = line.match(/^\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.*)/);
                if (tsMatch) {
                    const ts = tsMatch[1];
                    const content = tsMatch[2];
                    formatted += `
                    <div class="source-item">
                        <span class="badge timestamp" onclick="searchTimestamp('${escapeHtml(ts)}')">🕒 ${escapeHtml(ts)}</span>
                        <span>${escapeHtml(content)}</span>
                    </div>
                    `;
                } else {
                    formatted += `<div class="source-item"><span>${escapeHtml(line)}</span></div>`;
                }
            }
        }
        return formatted;
    }
    
    return escapeHtml(answer);
}

async function sendQuestion() {
    const questionBox = document.getElementById('question');
    const question = questionBox.value.trim();
    if (!question) return;
    const chat = document.getElementById('chatMessages');

    const userMsg = document.createElement('div');
    userMsg.className = 'message user';
    userMsg.innerText = question;
    chat.appendChild(userMsg);
    chat.scrollTop = chat.scrollHeight;
    questionBox.value = '';

    try {
        const resp = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, question })
        });
        if (!resp.ok) throw new Error('Chat error');
        const data = await resp.json();

        const botMsg = document.createElement('div');
        botMsg.className = 'message bot';
        botMsg.innerHTML = formatChatBotMessage(data.answer || 'No answer.');
        chat.appendChild(botMsg);
        chat.scrollTop = chat.scrollHeight;
    } catch (err) {
        console.error(err);
        const botMsg = document.createElement('div');
        botMsg.className = 'message bot';
        botMsg.innerText = 'Failed to get answer.';
        chat.appendChild(botMsg);
    }
}

async function handleFileUpload(f) {
    const drop = document.getElementById('dropZone');
    drop.textContent = 'Uploading...';
    document.getElementById('source').value = 'Uploading file, please wait...';
    
    try {
        const formData = new FormData();
        formData.append('file', f);
        
        const resp = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!resp.ok) throw new Error('Upload failed');
        
        const data = await resp.json();
        document.getElementById('source').value = data.filepath;
        drop.textContent = `Uploaded: ${f.name}`;
    } catch (err) {
        console.error(err);
        document.getElementById('source').value = '';
        drop.textContent = 'Upload failed. Try again.';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // drag & drop
    const drop = document.getElementById('dropZone');
    if (drop) {
        ['dragenter', 'dragover'].forEach(e => drop.addEventListener(e, (ev) => { ev.preventDefault(); drop.classList.add('dragover'); }));
        ['dragleave', 'drop'].forEach(e => drop.addEventListener(e, (ev) => { ev.preventDefault(); drop.classList.remove('dragover'); }));
        
        drop.addEventListener('drop', (ev) => {
            const f = ev.dataTransfer.files && ev.dataTransfer.files[0];
            if (f) {
                handleFileUpload(f);
            }
        });

        drop.addEventListener('click', () => {
            document.getElementById('fileInput').click();
        });
    }

    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', (ev) => {
            const f = ev.target.files && ev.target.files[0];
            if (f) {
                handleFileUpload(f);
            }
        });
    }

    // allow Enter to send question
    const q = document.getElementById('question');
    if (q) {
        q.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); sendQuestion() } });
    }

    // Client-side search filters active tab content
    const searchBox = document.getElementById('searchBox');
    const searchCount = document.getElementById('searchCount');
    if (searchBox) {
        searchBox.addEventListener('input', () => {
            const q = searchBox.value.trim().toLowerCase();
            const cards = document.querySelectorAll('#tabContent .insight-card');
            const listItems = document.querySelectorAll('#tabContent li');
            let matches = 0;
            
            if (cards.length > 0) {
                cards.forEach(card => {
                    const text = card.innerText.toLowerCase();
                    const show = !q || text.includes(q);
                    card.style.display = show ? '' : 'none';
                    if (show && q) matches++;
                });
            } else if (listItems.length > 0) {
                listItems.forEach(item => {
                    const text = item.innerText.toLowerCase();
                    const show = !q || text.includes(q);
                    item.style.display = show ? '' : 'none';
                    if (show && q) matches++;
                });
            }
            
            if (!q) searchCount.textContent = '';
            else searchCount.textContent = `${matches} match${matches === 1 ? '' : 'es'}`;
        });
    }
});