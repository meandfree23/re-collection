let currentResults = [];

document.addEventListener('DOMContentLoaded', () => {
    const resultsContainer = document.getElementById('results-container');
    const refreshDailyBtn = document.getElementById('refresh-daily-btn');
    const currentDateDisplay = document.getElementById('current-date-display');
    const currentIssueText = document.getElementById('current-issue-text');

    // Modal elements
    const dossierModal = document.getElementById('dossier-modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const analysisTabBtns = document.querySelectorAll('.analysis-tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    // Display formatted date (e.g. AUG 14, 2026)
    const now = new Date();
    const months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
    const formattedDate = `${months[now.getMonth()]} ${now.getDate()}, ${now.getFullYear()}`;
    if (currentDateDisplay) {
        currentDateDisplay.textContent = formattedDate;
    }
    if (currentIssueText) {
        currentIssueText.textContent = `ISSUE ${String(now.getMonth() + 1).padStart(2, '0')}.${String(now.getDate()).padStart(2, '0')} — DAILY CURATION`;
    }

    // Initial Load: Fetch Daily Curated Journal Feed
    loadDailyArchive();

    // 1. Ambient Audio Generator (Web Audio API Ambient Engine)
    let audioCtx = null;
    let isPlayingAudio = false;
    let noiseNode = null;
    let gainNode = null;

    const audioBtn = document.getElementById('ambient-audio-btn');
    if (audioBtn) {
        audioBtn.addEventListener('click', toggleAmbientAudio);
    }

    function toggleAmbientAudio() {
        if (!isPlayingAudio) {
            startAmbientAudio();
            audioBtn.classList.add('playing');
            audioBtn.querySelector('span').textContent = 'AMBIENCE ON 🔊';
        } else {
            stopAmbientAudio();
            audioBtn.classList.remove('playing');
            audioBtn.querySelector('span').textContent = 'AMBIENCE SOUND';
        }
    }

    function startAmbientAudio() {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }

        const bufferSize = 2 * audioCtx.sampleRate;
        const noiseBuffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
        const output = noiseBuffer.getChannelData(0);
        let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;

        for (let i = 0; i < bufferSize; i++) {
            const white = Math.random() * 2 - 1;
            b0 = 0.99886 * b0 + white * 0.0555179;
            b1 = 0.99332 * b1 + white * 0.0750759;
            b2 = 0.96900 * b2 + white * 0.1538520;
            b3 = 0.86650 * b3 + white * 0.3104856;
            b4 = 0.55000 * b4 + white * 0.5329522;
            b5 = -0.7616 * b5 - white * 0.0168980;
            output[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362) * 0.015;
            b6 = white * 0.115926;
        }

        noiseNode = audioCtx.createBufferSource();
        noiseNode.buffer = noiseBuffer;
        noiseNode.loop = true;

        gainNode = audioCtx.createGain();
        gainNode.gain.setValueAtTime(0.01, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.08, audioCtx.currentTime + 2);

        const filterNode = audioCtx.createBiquadFilter();
        filterNode.type = 'lowpass';
        filterNode.frequency.value = 450;

        noiseNode.connect(filterNode);
        filterNode.connect(gainNode);
        gainNode.connect(audioCtx.destination);

        noiseNode.start();
        isPlayingAudio = true;
    }

    function stopAmbientAudio() {
        if (gainNode && audioCtx) {
            gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 1);
            setTimeout(() => {
                if (noiseNode) {
                    noiseNode.stop();
                    noiseNode.disconnect();
                }
                isPlayingAudio = false;
            }, 1000);
        }
    }

    // 2. Spatial Filter Handlers
    const filterBtns = document.querySelectorAll('.spatial-filter-btn');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            filterBtns.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');

            const filterKey = e.target.getAttribute('data-filter');
            filterGrid(filterKey);
        });
    });

    function filterGrid(filterKey) {
        if (filterKey === 'all') {
            renderKinfolkGrid(currentResults);
        } else {
            const filtered = currentResults.filter(item => {
                const genre = (item.genre || '').toUpperCase();
                const title = (item.title || '').toUpperCase();
                return genre.includes(filterKey) || title.includes(filterKey);
            });
            renderKinfolkGrid(filtered);
        }
    }

    // Refresh Daily Button with fail-safe data retention
    if (refreshDailyBtn) {
        refreshDailyBtn.addEventListener('click', async () => {
            if (refreshDailyBtn.classList.contains('loading')) return;

            refreshDailyBtn.classList.add('loading');
            refreshDailyBtn.innerHTML = `
                <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="1.8" fill="none"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                <span>SYNCING JOURNAL...</span>
            `;
            
            try {
                // Try backend collection if on local FastAPI server
                const res = await fetch('/api/collect-now', { 
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                if (res.ok) {
                    const result = await res.json();
                    if (result.results && result.results.length > 0) {
                        currentResults = result.results;
                        renderKinfolkGrid(currentResults);
                    }
                } else {
                    await loadDailyArchive();
                }
            } catch (err) {
                // On GitHub Pages (static cloud), reload fresh JSON directly
                await loadDailyArchive();
            } finally {
                setTimeout(() => {
                    refreshDailyBtn.classList.remove('loading');
                    refreshDailyBtn.innerHTML = `
                        <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="1.8" fill="none"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                        <span>JOURNAL UPDATED ✓</span>
                    `;
                    setTimeout(() => {
                        refreshDailyBtn.innerHTML = `
                            <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="1.8" fill="none"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                            <span>UPDATE TODAY'S JOURNAL</span>
                        `;
                    }, 2000);
                }, 600);
            }
        });
    }

    async function loadDailyArchive() {
        try {
            // 1. Try static JSON directly first (Instant loading on GitHub Pages)
            let res = await fetch('data/daily_archive.json?v=' + Date.now());
            if (!res.ok) {
                // 2. Try relative path from root
                res = await fetch('./data/daily_archive.json?v=' + Date.now());
            }
            if (!res.ok) {
                // 3. Try FastAPI endpoint if on local server
                res = await fetch('/api/daily');
            }
            
            if (res.ok) {
                const data = await res.json();
                const items = Array.isArray(data) ? data : (data.results || []);
                if (items && items.length > 0) {
                    currentResults = items;
                    renderKinfolkGrid(currentResults);
                    return;
                }
            }
            
            if (currentResults.length === 0) {
                resultsContainer.innerHTML = `
                    <div class="loading-state">
                        <p>아직 수집된 아카이브가 없습니다.</p>
                    </div>
                `;
            }
        } catch (e) {
            console.error("Could not load daily archive:", e);
            // Final fallback attempt
            try {
                const fallbackRes = await fetch('data/daily_archive.json');
                if (fallbackRes.ok) {
                    const fallbackData = await fallbackRes.json();
                    const items = Array.isArray(fallbackData) ? fallbackData : (fallbackData.results || []);
                    if (items && items.length > 0) {
                        currentResults = items;
                        renderKinfolkGrid(currentResults);
                        return;
                    }
                }
            } catch (err2) {
                console.error("Fallback load failed:", err2);
            }
            
            if (currentResults.length === 0) {
                resultsContainer.innerHTML = `
                    <div class="loading-state" style="color: #ef4444;">
                        <p>아카이브를 불러오는 중 오류가 발생했습니다.</p>
                    </div>
                `;
            }
        }
    }

    // Modal Tab Switching
    analysisTabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            analysisTabBtns.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(pane => pane.classList.remove('active'));

            btn.classList.add('active');
            const targetTabId = btn.getAttribute('data-tab');
            const targetPane = document.getElementById(targetTabId);
            if (targetPane) targetPane.classList.add('active');
        });
    });

    // Modal Close
    if (modalCloseBtn) modalCloseBtn.addEventListener('click', closeModal);
    if (dossierModal) {
        dossierModal.addEventListener('click', (e) => {
            if (e.target === dossierModal) closeModal();
        });
    }
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });

    function closeModal() {
        if (dossierModal) {
            dossierModal.style.display = 'none';
            document.body.style.overflow = '';
            const videoFrameEl = document.getElementById('modal-video-frame');
            if (videoFrameEl) videoFrameEl.src = '';
        }
    }

    // Render Kinfolk Editorial Grid
    function renderKinfolkGrid(items) {
        if (!items || items.length === 0) {
            resultsContainer.innerHTML = `
                <div class="loading-state">
                    <p>표시할 아카이브가 없습니다.</p>
                </div>
            `;
            return;
        }

        resultsContainer.innerHTML = items.map((item, idx) => {
            const hasImg = item.image_url && item.image_url.trim().length > 0;
            const hasVideo = item.has_video || (item.video_url && item.video_url.trim().length > 0);
            const sourceHost = getDomainName(item.url);
            const titleSafe = escapeHtml(item.title || '아카이브 레코드');
            const snippetSafe = escapeHtml(item.snippet || '');

            // Memory & Experience Interpretation
            const facets = item.facets || {};
            const memoryInsight = facets.genius_loci || facets.memory_narrative || facets.sensory_recall || '공간과 장소에 깃든 고유한 시간의 기억을 현대적 감각으로 재구성합니다.';
            const memorySafe = escapeHtml(memoryInsight);

            const filmBadge = hasVideo ? `
                <div class="film-badge">
                    <svg viewBox="0 0 24 24" width="9" height="9" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                    <span>FILM</span>
                </div>
            ` : '';

            const mediaHtml = hasImg ? `
                <div class="card-media-box">
                    ${filmBadge}
                    <img src="${item.image_url}" alt="${titleSafe}" class="card-img" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                    <div class="simple-text-cover" style="display: none;">
                        <span class="text-cover-badge">${escapeHtml(item.genre || 'ARCHIVE')}</span>
                        <span class="text-cover-title">${titleSafe}</span>
                    </div>
                </div>
            ` : `
                <div class="card-media-box">
                    ${filmBadge}
                    <div class="simple-text-cover">
                        <span class="text-cover-badge">${escapeHtml(item.genre || 'ARCHIVE')}</span>
                        <span class="text-cover-title">${titleSafe}</span>
                    </div>
                </div>
            `;

            return `
                <article class="kinfolk-card" data-index="${idx}" onclick="openDossier(${idx})">
                    ${mediaHtml}
                    <div class="card-meta-line">
                        <span>${escapeHtml(item.genre || 'SPACE & EXPERIENCE')}</span>
                        <span>${escapeHtml(item.collected_at || '')}</span>
                    </div>
                    <h3 class="card-title">${titleSafe}</h3>
                    <p class="card-snippet">${snippetSafe}</p>
                    
                    <!-- Experience & Memory Interpretation Section -->
                    <div class="card-memory-box">
                        <span class="card-memory-label">MEMORY & EXPERIENCE ESSAY</span>
                        <p class="card-memory-text">${memorySafe}</p>
                    </div>

                    <div class="card-footer">
                        <span class="card-source-tag">${sourceHost}</span>
                        <span class="view-prompt" style="font-size: 0.72rem; color: var(--text-muted); font-family: 'Plus Jakarta Sans', sans-serif;">READ DOSSIER ↗</span>
                    </div>
                </article>
            `;
        }).join('');
    }

    // Open Minimal Dossier Modal
    window.openDossier = (index) => {
        const item = currentResults[index];
        if (!item) return;

        const facets = item.facets || {};

        document.getElementById('modal-title').textContent = item.title;
        document.getElementById('modal-genre').textContent = item.genre || 'SPACE & EXPERIENCE';
        document.getElementById('modal-source-domain').textContent = getDomainName(item.url);
        document.getElementById('modal-source-link').href = item.url;

        const mediaTypeEl = document.getElementById('modal-media-type');
        if (mediaTypeEl) {
            mediaTypeEl.textContent = item.has_video ? 'SPATIAL MOVING IMAGE (FILM)' : 'SPATIAL VISUAL & MEMORY';
        }

        const metrics = facets.tactile_metrics || {};
        const tactilityEl = document.getElementById('modal-metric-tactility');
        if (tactilityEl) {
            tactilityEl.textContent = metrics.tactility || 'RAW STONE, LINEN & LIGHT';
        }

        const volumeEl = document.getElementById('modal-metric-volume');
        if (volumeEl) {
            volumeEl.textContent = metrics.spatial_volume || '360° IMMERSIVE BOX CANVAS';
        }

        const imgEl = document.getElementById('modal-image');
        const textCoverEl = document.getElementById('modal-text-cover');
        const videoBoxEl = document.getElementById('modal-video-box');
        const videoFrameEl = document.getElementById('modal-video-frame');

        if (item.video_url && item.video_url.trim() !== '') {
            if (imgEl) imgEl.style.display = 'none';
            if (textCoverEl) textCoverEl.style.display = 'none';
            if (videoBoxEl && videoFrameEl) {
                videoBoxEl.style.display = 'block';
                videoFrameEl.src = item.video_url;
            }
        } else {
            if (videoBoxEl && videoFrameEl) {
                videoBoxEl.style.display = 'none';
                videoFrameEl.src = '';
            }
            if (item.image_url && item.image_url.trim() !== '') {
                if (imgEl) {
                    imgEl.src = item.image_url;
                    imgEl.style.display = 'block';
                }
                if (textCoverEl) textCoverEl.style.display = 'none';
            } else {
                if (imgEl) imgEl.style.display = 'none';
                if (textCoverEl) {
                    textCoverEl.style.display = 'flex';
                    document.getElementById('modal-cover-genre').textContent = item.genre || 'SPACE';
                    document.getElementById('modal-cover-title').textContent = item.title;
                }
            }
        }

        // 3 Spatial Memory & CX Layers
        const geniusLociEl = document.getElementById('modal-facet-genius-loci');
        if (geniusLociEl) {
            geniusLociEl.textContent = facets.genius_loci || facets.memory_narrative || '장소성과 공간적 기억을 분석하고 있습니다.';
        }

        const sensoryRecallEl = document.getElementById('modal-facet-sensory-recall');
        if (sensoryRecallEl) {
            sensoryRecallEl.textContent = facets.sensory_recall || facets.sensory_experience || '공간의 여백, 빛, 원초적 물성을 통한 공감각적 기억을 구축합니다.';
        }

        // Offline Video CX & Horizon
        const videoCxEl = document.getElementById('modal-facet-video-cx');
        if (videoCxEl) {
            videoCxEl.textContent = facets.spatial_video_cx || '플래그십 스토어 및 미디어 파사드에서 고객의 신체적 감각을 자극하여 잊히지 않는 장소 기억(Episodic Memory)을 형성합니다.';
        }

        const horizonEl = document.getElementById('modal-facet-horizon');
        if (horizonEl) {
            horizonEl.textContent = facets.zeitgeist_horizon || '단순 상업 광고를 탈피하여 공간을 예술적 사유의 성소로 격상시키는 미래형 미학을 제시합니다.';
        }

        const zeitgeistEl = document.getElementById('modal-facet-zeitgeist');
        if (zeitgeistEl) {
            zeitgeistEl.textContent = facets.zeitgeist_synapse || '동시대를 관통하는 미학적 태도와 메시지를 탐구합니다.';
        }

        const synapseListEl = document.getElementById('modal-synapse-list');
        if (synapseListEl) {
            const synapses = facets.synapse_connections || [];
            if (synapses.length > 0) {
                synapseListEl.innerHTML = synapses.map(syn => `
                    <div class="synapse-card">
                        <span class="synapse-domain-badge">${escapeHtml(syn.domain)}</span>
                        <p class="synapse-connection-text">${escapeHtml(syn.connection)}</p>
                    </div>
                `).join('');
            } else {
                synapseListEl.innerHTML = `<p style="color: var(--text-muted); font-size: 0.9rem;">연결된 시냅스 데이터가 없습니다.</p>`;
            }
        }

        // Tab 4: Raw Extract
        const rawExtractEl = document.getElementById('modal-facet-archive');
        if (rawExtractEl) {
            rawExtractEl.innerHTML = `
                <p><strong>발췌문:</strong> ${escapeHtml(item.snippet || '')}</p>
                <p style="margin-top: 0.8rem; font-size: 0.82rem; color: #888;">원문 타이틀: ${escapeHtml(item.original_title || item.title)}</p>
            `;
        }

        // Reset to first tab
        if (analysisTabBtns.length > 0) {
            analysisTabBtns[0].click();
        }

        // Show Modal
        if (dossierModal) {
            dossierModal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }
    };

    function getDomainName(url) {
        try {
            const parsed = new URL(url);
            return parsed.hostname.replace('www.', '');
        } catch {
            return 'archive.org';
        }
    }

    function escapeHtml(text) {
        if (!text) return '';
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
});

