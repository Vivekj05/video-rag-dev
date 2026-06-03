let sessionId = null;

function escapeHtml(str){
    if(!str) return '';
    return String(str)
        .replaceAll('&','&amp;')
        .replaceAll('<','&lt;')
        .replaceAll('>','&gt;')
        .replaceAll('"','&quot;')
        .replaceAll("'","&#39;");
}

function setLoading(active){
    const loader = document.getElementById('loader');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const clearBtn = document.getElementById('clearBtn');
    if(active){
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

async function processVideo(){
    const source = document.getElementById('source').value;
    const language = document.getElementById('language').value;
    if(!source){
        alert('Please provide a YouTube URL or video ID.');
        return;
    }

    setLoading(true);

    // simulate progress while backend works
    const progress = document.getElementById('progressBar');
    let p = 5;
    progress.value = p;
    const updater = setInterval(()=>{
        p = Math.min(98, p + Math.random()*8);
        progress.value = Math.floor(p);
    }, 600);

    try{
        const resp = await fetch('/pipeline',{
            method:'POST',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({source, language})
        });

        if(!resp.ok) throw new Error('Server error');

        const data = await resp.json();
        sessionId = data.session_id;

        // render results
        const results = document.getElementById('results');
        results.innerHTML = '';

        const sections = [
            {title:'📄 Summary', content:data.summary},
            {title:'✅ Action Items', content:data.action_items},
            {title:'🎯 Key Decisions', content:data.key_decisions},
            {title:'❓ Open Questions', content:data.open_questions}
        ];

        sections.forEach(s=>{
            const card = document.createElement('div');
            card.className = 'card';
            const raw = (s.content && String(s.content).trim()) ? s.content : `No ${s.title.replace(/[^a-zA-Z ]/g,'').toLowerCase()} found.`;
            // escape and preserve newlines for better readability
            const escaped = escapeHtml(raw).replace(/\n/g, '<br>');
            card.innerHTML = `<h3>${escapeHtml(s.title)}</h3><div class="card-content">${escaped}</div>`;
            results.appendChild(card);
        });

        document.getElementById('chatSection').classList.remove('hidden');

    }catch(err){
        console.error(err);
        alert('Failed to process video. See console for details.');
    } finally {
        clearInterval(updater);
        document.getElementById('progressBar').value = 100;
        setTimeout(()=>setLoading(false),400);
    }
}

function clearAll(){
    document.getElementById('source').value = '';
    document.getElementById('language').value = 'english';
    document.getElementById('results').innerHTML = '';
    document.getElementById('chatMessages').innerHTML = '';
    document.getElementById('chatSection').classList.add('hidden');
    sessionId = null;
}

async function sendQuestion(){
    const questionBox = document.getElementById('question');
    const question = questionBox.value.trim();
    if(!question) return;
    const chat = document.getElementById('chatMessages');

    const userMsg = document.createElement('div');
    userMsg.className = 'message user';
    userMsg.innerText = question;
    chat.appendChild(userMsg);
    chat.scrollTop = chat.scrollHeight;
    questionBox.value = '';

    try{
        const resp = await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sessionId,question})});
        if(!resp.ok) throw new Error('Chat error');
        const data = await resp.json();

        const botMsg = document.createElement('div');
        botMsg.className = 'message bot';
        botMsg.innerText = data.answer || 'No answer.';
        chat.appendChild(botMsg);
        chat.scrollTop = chat.scrollHeight;
    }catch(err){
        console.error(err);
        const botMsg = document.createElement('div');
        botMsg.className = 'message bot';
        botMsg.innerText = 'Failed to get answer.';
        chat.appendChild(botMsg);
    }
}

document.addEventListener('DOMContentLoaded',()=>{
    // drag & drop
    const drop = document.getElementById('dropZone');
    if(drop){
        ['dragenter','dragover'].forEach(e=>drop.addEventListener(e,(ev)=>{ev.preventDefault();drop.classList.add('dragover');}));
        ['dragleave','drop'].forEach(e=>drop.addEventListener(e,(ev)=>{ev.preventDefault();drop.classList.remove('dragover');}));
        drop.addEventListener('drop',(ev)=>{
            const f = ev.dataTransfer.files && ev.dataTransfer.files[0];
            if(f){
                // small UX: show filename in source box
                document.getElementById('source').value = f.name;
            }
        });
    }

    // allow Enter to send question
    const q = document.getElementById('question');
    if(q){
        q.addEventListener('keydown',(e)=>{if(e.key==='Enter'){e.preventDefault();sendQuestion()}});
    }

    // client-side search for results
    const searchBox = document.getElementById('searchBox');
    const searchCount = document.getElementById('searchCount');
    if(searchBox){
        searchBox.addEventListener('input', ()=>{
            const q = searchBox.value.trim().toLowerCase();
            const cards = document.querySelectorAll('#results .card');
            let matches = 0;
            cards.forEach(card=>{
                const text = card.innerText.toLowerCase();
                const show = !q || text.includes(q);
                card.style.display = show ? '' : 'none';
                if(show && q) matches++;
            });
            if(!q) searchCount.textContent = '';
            else searchCount.textContent = `${matches} match${matches===1?'':'es'}`;
        });
    }
});