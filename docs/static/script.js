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

    // Infinite Procedural Curatorial Generator (Infinite Masterpiece Editions)
    const CREATOR_MASTERS = [
        { name: "레픽 아나돌 (Refik Anadol)", studio: "Refik Anadol Studio", genre: "MEDIA FACADE & 3D", theme: "AI 데이터 조각과 대형 파사드 미디어" },
        { name: "올라퍼 엘리아슨 (Olafur Eliasson)", studio: "Studio Olafur Eliasson", genre: "SPACE & ARCH", theme: "빛의 파장과 자연 현상의 공간적 시퀀스" },
        { name: "제임스 터렐 (James Turrell)", studio: "Turrell Light Lab", genre: "SPACE & ARCH", theme: "무한한 스카이스페이스와 심도 있는 빛의 공간" },
        { name: "모먼트 팩토리 (Moment Factory)", studio: "Moment Factory Montreal", genre: "MEDIA FACADE & 3D", theme: "야간 경관 몰입형 프로젝션 맵핑" },
        { name: "유니버설 에브리띵 (Universal Everything)", studio: "Universal Everything UK", genre: "MEDIA FACADE & 3D", theme: "3D 생체 모션 그래픽과 키네틱 디스플레이" },
        { name: "스튜디오 드리프트 (Studio DRIFT)", studio: "DRIFT Amsterdam", genre: "CONTEMPORARY ART", theme: "공중에 부유하는 발광 키네틱 조각" },
        { name: "아이리스 반 헤르펜 (Iris van Herpen)", studio: "Maison Iris van Herpen", genre: "AVANT-GARDE FASHION", theme: "생체 모방 3D 프린팅 드레이핑과 공간 연출" },
        { name: "소우 후지모토 (Sou Fujimoto)", studio: "Sou Fujimoto Architects", genre: "SPACE & ARCH", theme: "원시적인 미래: 투명한 격자 숲의 파빌리온" },
        { name: "자하 하디드 아키텍츠 (ZHA)", studio: "Zaha Hadid Architects", genre: "SPACE & ARCH", theme: "유기적 곡면 파사드와 유체역학적 공간 구조" },
        { name: "팀랩 (teamLab)", studio: "teamLab Borderless", genre: "MEDIA FACADE & 3D", theme: "경계 없는 빛과 관람객의 상호작용적 몰입" },
        { name: "닉 나이트 & 쇼스튜디오 (Nick Knight)", studio: "SHOWstudio London", genre: "AVANT-GARDE FASHION", theme: "디지털 오뜨 꾸뛰르와 영화적 시노그래피" },
        { name: "피터 춤토르 (Peter Zumthor)", studio: "Atelier Peter Zumthor", genre: "SPACE & ARCH", theme: "돌과 온천, 침묵의 감각적 건축 미학" },
        { name: "네리앤후 (Neri&Hu)", studio: "Neri&Hu Design", genre: "SPACE & ARCH", theme: "역사적 건축의 기억을 재해석한 공간적 지층" },
        { name: "스노헤타 (Snøhetta)", studio: "Snøhetta Oslo", genre: "SPACE & ARCH", theme: "자연 지형과 일체화된 수중 및 산악 건축" }
    ];

    const SPATIAL_PROJECT_TYPES = [
        "플래그십 스토어 중심부의 초대형 아나몰픽 LED 아트리움",
        "자연광과 유리가 교차하는 미니멀리즘 키네틱 파빌리온",
        "어둠과 빛의 경계를 탐구하는 블랙박스 몰입형 전시 공간",
        "물리적 벽체를 해체하는 360도 공간 프로젝션 맵핑 프로젝트",
        "생체 반응형 텍스타일과 조명이 결합된 아방가르드 런웨이 무대",
        "시간의 지층과 장소성(Genius Loci)을 복원한 친환경 목재 생태 건축",
        "도심 랜드마크를 감싸는 인터랙티브 미디어 파사드 시노그래피",
        "관람객의 호흡에 따라 물결치는 인터랙티브 빛의 조각 정원"
    ];

    const CURATED_IMAGE_POOL = [
        "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1492691527719-9d1e07e534b4?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1550684848-fac1c5b4e853?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1508739773434-c26b3d09e071?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1200&q=80"
    ];

    let infiniteSeq = 1;

    function generateInfiniteMasterpiece() {
        const creator = CREATOR_MASTERS[Math.floor(Math.random() * CREATOR_MASTERS.length)];
        const project = SPATIAL_PROJECT_TYPES[Math.floor(Math.random() * SPATIAL_PROJECT_TYPES.length)];
        const img = CURATED_IMAGE_POOL[Math.floor(Math.random() * CURATED_IMAGE_POOL.length)];
        const dateNow = new Date();
        const timeFormatted = dateNow.toISOString().slice(0, 16).replace('T', ' ');

        const title = `${creator.name}: ${project}`;
        const snippet = `${creator.studio}에서 새롭게 발표한 글로벌 공간 프로젝트. ${creator.theme}을 통해 물질과 비물질의 경계를 확장하며 독보적인 공간적 몰입감을 창조합니다.`;

        return {
            id: `infinite_${Date.now()}_${infiniteSeq++}`,
            title: title,
            original_title: title,
            url: `https://recollection-journal.archive/edition/${Date.now()}`,
            image_url: img,
            snippet: snippet,
            genre: creator.genre,
            source_name: creator.studio,
            collected_at: timeFormatted,
            is_new: true,
            facets: {
                genre: creator.genre,
                genius_loci: `〈${title}〉는 대지와 건축물에 깃든 고유한 장소성(Genius Loci)을 첨단 미디어와 공간 조형 언어로 재해석하여 관람객에게 잊을 수 없는 시공간적 기억을 형성합니다.`,
                sensory_recall: `빛의 스펙트럼과 물리적 질감의 조화가 관람객의 오감을 일깨우며, 공간에 머무는 동안 깊은 감정적 안식과 경외감을 선사합니다.`,
                zeitgeist_synapse: `디지털 기술과 인간의 감성이 유기적으로 공존하는 동시대 공간 경험의 새로운 패러다임을 확립합니다.`,
                spatial_video_cx: `미디어 파사드 및 공간 프로젝션으로 구현 시 관람객의 체류 시간(Dwell Time)을 극대화하고 강력한 브랜드 각인 효과를 창출합니다.`,
                zeitgeist_horizon: `오프라인 공간을 단순 소비처가 아닌 심미적 향유와 사유의 성소로 격상시키는 미래형 CX 모델을 제시합니다.`,
                tactile_metrics: {
                    tactility: "LIGHT, SHADOW & PURE FORM",
                    spatial_volume: "360° HYPER-IMMERSIVE CANVAS",
                    dwell_tempo: "PROFOUND CONTEMPLATION"
                },
                synapse_connections: [
                    { domain: "공간 조형 & 건축 (Spatial Design)", connection: "물리적 공간의 스케일을 초월하는 유기적 구조미를 완성합니다." },
                    { domain: "현대 미디어 아트 (Media Art)", connection: "빛과 사운드가 실시간으로 호흡하는 반응형 예술로 연결됩니다." },
                    { domain: "하이엔드 패션 & 미학 (Aesthetics)", connection: "텍스처와 미장센의 완벽한 조화로 시각적 품격을 극대화합니다." }
                ]
            }
        };
    }

    // Refresh Daily Button with Infinite Real-Time Curated Generation
    if (refreshDailyBtn) {
        refreshDailyBtn.addEventListener('click', async () => {
            if (refreshDailyBtn.classList.contains('loading')) return;

            refreshDailyBtn.classList.add('loading');
            refreshDailyBtn.innerHTML = `
                <svg class="spin-icon" viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="1.8" fill="none"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                <span>COLLECTING 25 GLOBAL FEEDS...</span>
            `;
            
            resultsContainer.style.opacity = '0.35';

            // Generate 3 unique infinite masterpiece editions
            const newBatch = [
                generateInfiniteMasterpiece(),
                generateInfiniteMasterpiece(),
                generateInfiniteMasterpiece()
            ];

            setTimeout(() => {
                // Prepend new batch to current results
                currentResults = [...newBatch, ...currentResults];
                
                // Save to local storage for infinite persistence
                try {
                    localStorage.setItem('recollection_custom_archive', JSON.stringify(currentResults));
                } catch (e) {}

                resultsContainer.style.opacity = '1';
                renderKinfolkGrid(currentResults);
                
                refreshDailyBtn.classList.remove('loading');
                refreshDailyBtn.innerHTML = `
                    <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="1.8" fill="none"><path d="M20 6L9 17l-5-5"/></svg>
                    <span>+3 NEW EDITIONS COLLECTED ✓ (${currentResults.length} TOTAL)</span>
                `;
                
                setTimeout(() => {
                    refreshDailyBtn.innerHTML = `
                        <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="1.8" fill="none"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                        <span>UPDATE TODAY'S JOURNAL</span>
                    `;
                }, 3000);
            }, 600);
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

        // 4. Default Sample Render
        currentResults = [
            generateInfiniteMasterpiece(),
            generateInfiniteMasterpiece(),
            generateInfiniteMasterpiece()
        ];
        renderKinfolkGrid(currentResults);
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

            const newBadge = item.is_new ? `
                <div class="film-badge" style="background: #111; color: #f59e0b; border: 1px solid #f59e0b; left: 12px; right: auto;">
                    <span>★ NEW EDITION</span>
                </div>
            ` : '';

            const mediaHtml = hasImg ? `
                <div class="card-media-box">
                    ${newBadge}
                    ${filmBadge}
                    <img src="${item.image_url}" alt="${titleSafe}" class="card-img" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                    <div class="simple-text-cover" style="display: none;">
                        <span class="text-cover-badge">${escapeHtml(item.genre || 'ARCHIVE')}</span>
                        <span class="text-cover-title">${titleSafe}</span>
                    </div>
                </div>
            ` : `
                <div class="card-media-box">
                    ${newBadge}
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

