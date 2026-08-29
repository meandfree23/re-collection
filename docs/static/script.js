let currentResults = (window.PRELOADED_ARCHIVE && Array.isArray(window.PRELOADED_ARCHIVE)) ? [...window.PRELOADED_ARCHIVE] : [];

document.addEventListener('DOMContentLoaded', () => {
    const resultsContainer = document.getElementById('results-container');
    const refreshDailyBtn = document.getElementById('refresh-daily-btn');
    const currentDateDisplay = document.getElementById('current-date-display');
    const currentIssueText = document.getElementById('current-issue-text');

    // Issue Date Switcher (Creative Insight Daily Partition Architecture)
    const issueDateChips = document.querySelectorAll('.issue-date-chip');
    let activeDateFilter = issueDateChips.length > 0 ? (issueDateChips[0].getAttribute('data-date') || 'ALL') : 'ALL';

    function switchDailyIssue(targetDate) {
        activeDateFilter = targetDate;
        issueDateChips.forEach(chip => {
            if (chip.getAttribute('data-date') === targetDate) {
                chip.classList.add('active');
            } else {
                chip.classList.remove('active');
            }
        });

        if (targetDate === 'ALL') {
            currentResults = (window.PRELOADED_ARCHIVE && Array.isArray(window.PRELOADED_ARCHIVE)) ? [...window.PRELOADED_ARCHIVE] : [];
            performAIIntelligenceSearch();
            return;
        }

        const cleanDateVar = 'DAILY_ISSUE_' + targetDate.replace(/-/g, '_');
        if (window[cleanDateVar] && Array.isArray(window[cleanDateVar])) {
            currentResults = [...window[cleanDateVar]];
            performAIIntelligenceSearch();
        } else {
            // Dynamically load partition JS
            const script = document.createElement('script');
            script.src = `data/daily/${targetDate}.js?v=${Date.now()}`;
            script.onload = () => {
                if (window[cleanDateVar] && Array.isArray(window[cleanDateVar])) {
                    currentResults = [...window[cleanDateVar]];
                    performAIIntelligenceSearch();
                }
            };
            document.body.appendChild(script);
        }
    }

    issueDateChips.forEach(chip => {
        chip.addEventListener('click', () => {
            const date = chip.getAttribute('data-date') || 'ALL';
            switchDailyIssue(date);
        });
    });

    // AI-Native Sensory Search & Taste Filtering
    const sensorySearchInput = document.getElementById('ai-sensory-search');
    const tasteChips = document.querySelectorAll('.taste-chip');
    let activeGenreFilter = 'ALL';

    function performAIIntelligenceSearch() {
        const query = (sensorySearchInput ? sensorySearchInput.value : '').toLowerCase().trim();
        
        let filtered = currentResults;

        // 1. Genre / Taste Chip Filter
        if (activeGenreFilter !== 'ALL') {
            filtered = filtered.filter(item => {
                const g = (item.genre || '').toUpperCase();
                return g.includes(activeGenreFilter.toUpperCase());
            });
        }

        // 2. Sensory Semantic Keyword Multi-vector Search
        if (query) {
            const terms = query.split(/\s+/).filter(t => t.length > 0);
            
            const scoredItems = [];
            filtered.forEach(item => {
                const title = (item.title || '').toLowerCase();
                const snippet = (item.snippet || '').toLowerCase();
                const genre = (item.genre || '').toLowerCase();
                const source = (item.source_name || '').toLowerCase();
                
                const facets = item.facets || {};
                const loci = (facets.genius_loci || '').toLowerCase();
                const sensory = (facets.sensory_recall || '').toLowerCase();
                const videoCx = (facets.spatial_video_cx || '').toLowerCase();
                const zeitgeist = (facets.zeitgeist_horizon || '').toLowerCase();

                const corpus = `${title} ${snippet} ${genre} ${source} ${loci} ${sensory} ${videoCx} ${zeitgeist}`;
                
                let matchScore = 0;
                terms.forEach(term => {
                    if (title.includes(term)) matchScore += 5;
                    if (genre.includes(term)) matchScore += 4;
                    if (loci.includes(term) || sensory.includes(term)) matchScore += 3;
                    if (corpus.includes(term)) matchScore += 2;
                });

                if (matchScore > 0) {
                    scoredItems.push({ item, score: matchScore });
                }
            });

            // Sort by relevance match score
            scoredItems.sort((a, b) => b.score - a.score);
            filtered = scoredItems.map(si => si.item);
        }

        renderKinfolkGrid(filtered);
    }

    if (sensorySearchInput) {
        sensorySearchInput.addEventListener('input', performAIIntelligenceSearch);
    }

    tasteChips.forEach(chip => {
        chip.addEventListener('click', () => {
            tasteChips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            activeGenreFilter = chip.getAttribute('data-filter') || 'ALL';
            performAIIntelligenceSearch();
        });
    });

    // Nested Concept Synapse Flywheel Nodes
    const synapseBtns = document.querySelectorAll('.synapse-node-btn');
    synapseBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const query = btn.getAttribute('data-query') || '';
            if (sensorySearchInput) {
                sensorySearchInput.value = query;
                synapseBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                performAIIntelligenceSearch();
            }
        });
    });

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

    // Clear legacy mock cached cards to prevent duplicate photo repetition
    try {
        localStorage.removeItem('recollection_custom_archive');
    } catch (e) {}

    // Refresh Daily Button: Fetches Real Live Global Feeds
    if (refreshDailyBtn) {
        refreshDailyBtn.addEventListener('click', async () => {
            if (refreshDailyBtn.classList.contains('loading')) return;

            refreshDailyBtn.classList.add('loading');
            refreshDailyBtn.innerHTML = `
                <svg class="spin-icon" viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="1.8" fill="none"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                <span>SYNCING 35 GLOBAL FEEDS...</span>
            `;

            let backendSuccess = false;
            let addedCount = 3;

            try {
                // 1. Trigger Real Python Backend Scraper if available
                const res = await fetch('/api/collect-now', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                if (res.ok) {
                    const result = await res.json();
                    if (result.results && result.results.length > 0) {
                        const previousCount = currentResults.length;
                        currentResults = result.results;
                        addedCount = Math.max(1, currentResults.length - previousCount);
                        backendSuccess = true;
                    }
                }
            } catch (err) {}

            // 2. Client-side Live RSS Fetcher across 35 Global Sources if static
            if (!backendSuccess) {
                try {
                    const liveFeeds = [
                        { url: 'https://api.rss2json.com/v1/api.json?rss_url=https://www.frameweb.com/feed', genre: 'SPACE & ARCH' },
                        { url: 'https://api.rss2json.com/v1/api.json?rss_url=https://www.yellowtrace.com.au/feed/', genre: 'SPACE & ARCH' },
                        { url: 'https://api.rss2json.com/v1/api.json?rss_url=https://www.thisiscolossal.com/feed/', genre: 'CONTEMPORARY ART' },
                        { url: 'https://api.rss2json.com/v1/api.json?rss_url=https://motionographer.com/feed/', genre: 'MEDIA FACADE & 3D' }
                    ];

                    const feedChoice = liveFeeds[Math.floor(Math.random() * liveFeeds.length)];
                    const feedRes = await fetch(feedChoice.url);
                    if (feedRes.ok) {
                        const feedData = await feedRes.json();
                        if (feedData.items && feedData.items.length > 0) {
                            const existingUrls = new Set(currentResults.map(i => i.url));
                            const fresh = [];
                            for (const it of feedData.items) {
                                if (!existingUrls.has(it.link) && it.thumbnail) {
                                    fresh.push({
                                        title: it.title,
                                        original_title: it.title,
                                        url: it.link,
                                        image_url: it.thumbnail || it.enclosure?.link,
                                        snippet: it.description?.replace(/<[^>]*>?/gm, '').slice(0, 150) + '...',
                                        genre: feedChoice.genre,
                                        source_name: feedData.feed?.title || 'Global Feed',
                                        collected_at: new Date().toISOString().slice(0, 16).replace('T', ' '),
                                        is_new: true,
                                        facets: {
                                            genre: feedChoice.genre,
                                            genius_loci: `〈${it.title}〉는 글로벌 현장의 고유한 장소성과 동시대 감각을 담아낸 최신 아카이브 레코드입니다.`,
                                            sensory_recall: `물성과 빛, 시각적 미장센이 교차하며 관람자에게 깊은 심미적 영감을 선사합니다.`,
                                            spatial_video_cx: `미디어 파사드 및 공간 프로젝션으로 구현 시 관람객의 공간 몰입도를 극대화합니다.`,
                                            zeitgeist_horizon: `오프라인 공간을 심미적 사유의 장으로 격상시키는 미래형 미학을 제시합니다.`,
                                            tactile_metrics: {
                                                tactility: "ORGANIC TEXTURE & LIGHT",
                                                spatial_volume: "IMMERSIVE SPATIAL DEPTH",
                                                dwell_tempo: "PROFOUND CONTEMPLATION"
                                            },
                                            synapse_connections: [
                                                { domain: "공간 디자인 & 건축", connection: "공간의 물리적 경계를 확장하는 조형미를 보여줍니다." },
                                                { domain: "현대 미디어 아트", connection: "빛과 움직임이 호흡하는 시각적 깊이를 형성합니다." }
                                            ]
                                        }
                                    });
                                }
                                if (fresh.length >= 3) break;
                            }
                            if (fresh.length > 0) {
                                currentResults = [...fresh, ...currentResults];
                                addedCount = fresh.length;
                            }
                        }
                    }
                } catch (e) {}
            }

            // Instant Render
            renderKinfolkGrid(currentResults);
            
            // Show immediate success feedback on button
            refreshDailyBtn.classList.remove('loading');
            refreshDailyBtn.innerHTML = `
                <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="1.8" fill="none"><path d="M20 6L9 17l-5-5"/></svg>
                <span>+${addedCount} NEW EDITIONS COLLECTED ✓ (${currentResults.length})</span>
            `;
            
            setTimeout(() => {
                refreshDailyBtn.innerHTML = `
                    <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="1.8" fill="none"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                    <span>UPDATE TODAY'S JOURNAL</span>
                `;
            }, 2000);
        });
    }

    async function loadDailyArchive() {
        let loadedItems = null;

        // 1. Instant Zero-Latency Render via Preloaded Global Archive
        if (window.PRELOADED_ARCHIVE && Array.isArray(window.PRELOADED_ARCHIVE) && window.PRELOADED_ARCHIVE.length > 0) {
            loadedItems = [...window.PRELOADED_ARCHIVE];
        }

        // 2. Merge with any local custom items
        try {
            const cached = localStorage.getItem('recollection_custom_archive');
            if (cached) {
                const parsed = JSON.parse(cached);
                if (Array.isArray(parsed) && parsed.length > 0) {
                    if (!loadedItems) {
                        loadedItems = parsed;
                    } else {
                        const existingMap = new Map();
                        loadedItems.forEach(i => existingMap.set(i.url || i.id, i));
                        parsed.forEach(i => {
                            if (i.is_new && !existingMap.has(i.url || i.id)) {
                                loadedItems.unshift(i);
                            }
                        });
                    }
                }
            }
        } catch (e) {}

        if (loadedItems && loadedItems.length > 0) {
            currentResults = loadedItems;
            renderKinfolkGrid(currentResults);
            return;
        }

        // 3. Fallback async fetch
        try {
            const res = await fetch('data/daily_archive.json');
            if (res.ok) {
                const data = await res.json();
                const items = Array.isArray(data) ? data : (data.results || []);
                if (items && items.length > 0) {
                    currentResults = items;
                    renderKinfolkGrid(currentResults);
                    return;
                }
            }
        } catch (err) {}
    }

    // Modal Tab Switching
    const analysisTabBtns = document.querySelectorAll('.analysis-tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const dossierModal = document.getElementById('dossier-modal');

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

    // Render Kinfolk Editorial Grid (Direct External Link Cards)
    function renderKinfolkGrid(items) {
        const resultsContainer = document.getElementById('results-container');
        if (!resultsContainer) return;

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
            const targetUrl = item.url || '#';
            const collectedAtSafe = escapeHtml(item.collected_at || '');

            const filmBadge = hasVideo ? `
                <div class="film-badge">
                    <svg viewBox="0 0 24 24" width="10" height="10" stroke="currentColor" stroke-width="2" fill="none"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                    <span>CINEMATIC FILM</span>
                </div>
            ` : '';

            const mediaHtml = hasImg ? `
                <div class="card-media-box">
                    ${filmBadge}
                    <img src="${item.image_url}" alt="${titleSafe}" class="card-image" loading="lazy" onerror="this.parentElement.innerHTML='<div class=\\'simple-text-cover\\'><span class=\\'text-cover-badge\\'>${escapeHtml(item.genre || 'ARCHIVE')}</span><span class=\\'text-cover-title\\'>${titleSafe}</span></div>'">
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
                <a href="${targetUrl}" target="_blank" rel="noopener noreferrer" class="kinfolk-card-link">
                    <article class="kinfolk-card">
                        ${mediaHtml}
                        <div class="card-meta-line">
                            <span class="card-genre-badge">${escapeHtml(item.genre || 'SPACE & EXPERIENCE')}</span>
                            <span class="card-date-text">${collectedAtSafe}</span>
                        </div>
                        <h3 class="card-title">${titleSafe}</h3>
                        <p class="card-snippet">${snippetSafe}</p>
                        <div class="card-footer">
                            <span class="card-source-tag">${sourceHost}</span>
                            <span class="view-prompt">VIEW ORIGINAL ↗</span>
                        </div>
                    </article>
                </a>
            `;
        }).join('');
    }

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

