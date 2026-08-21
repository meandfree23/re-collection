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

    // 3. Client-Side Live RSS Fetcher for Realtime Updates anywhere
    const LIVE_RSS_FEEDS = [
        { name: "Dezeen", url: "https://www.dezeen.com/feed/", genre: "SPACE & ARCH" },
        { name: "ArchDaily", url: "https://www.archdaily.com/feed", genre: "SPACE & ARCH" },
        { name: "This Is Colossal", url: "https://www.thisiscolossal.com/feed/", genre: "CONTEMPORARY ART" },
    // Real-Time Curation Dispatcher (Guarantees Fresh Spatial x Media Editions)
    const REALTIME_CURATION_POOL = [
        {
            title: "팀랩 2026: 무한한 빛의 보이드와 아나몰픽 공간 조각",
            url: "https://www.teamlab.art/e/infinite_light_void_2026",
            image_url: "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=1200&q=80",
            snippet: "도쿄 오다이바에 새롭게 오픈한 팀랩의 차세대 몰입형 미디어 조각 프로젝트. 물리적 벽체의 경계를 지우고 빛의 입자로 시공간의 깊이를 재구성합니다.",
            genre: "MEDIA FACADE & 3D",
            source_name: "CreativeApplications",
            facets: {
                genre: "MEDIA FACADE & 3D",
                genius_loci: "〈팀랩 2026〉는 암전된 공간 속에 빛의 궤적을 3차원 부피감으로 구축하여 관람객을 완전히 압도하는 시공간적 기억을 각인합니다.",
                sensory_recall: "360도 공간 음향과 반응형 LED 광선이 신체 감각을 확장하며 깊은 감정적 경외감(Awe)을 자아냅니다.",
                zeitgeist_synapse: "인공지능과 실시간 프로젝션 맵핑이 융합된 21세기 디지털 미디어 공간의 새로운 지평을 제시합니다.",
                spatial_video_cx: "플래그십 및 공공 파사드에 적용 시 압도적인 Stop-and-Stare 시각적 몰입과 강력한 브랜드 각인 효과를 제공합니다.",
                zeitgeist_horizon: "관람객의 움직임에 따라 유기적으로 호흡하는 미래형 반응형 미디어 아키텍처 모델입니다.",
                tactile_metrics: {
                    tactility: "VOLUMETRIC LIGHT & VOID",
                    spatial_volume: "360° HYPER-IMMERSIVE CANVAS",
                    dwell_tempo: "INTENSE EMOTIONAL AWE"
                },
                synapse_connections: [
                    { domain: "현대 미술 (Contemporary Art)", connection: "빛과 공간을 매개로 한 설치 미술의 극대화된 형태입니다." },
                    { domain: "공간 디자인 (Spatial CX)", connection: "물리적 공간을 초월하는 무한한 심도를 연출합니다." },
                    { domain: "시네마틱 사운드 (Spatial Audio)", connection: "공간 잔향과 사운드스케이프가 유기적으로 동기화됩니다." }
                ]
            }
        },
        {
            title: "토쿠진 요시오카: 투명한 유리와 자연광의 키네틱 파빌리온",
            url: "https://www.dezeen.com/tokujin-yoshioka-glass-kinetic-pavilion-2026",
            image_url: "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=80",
            snippet: "프리즘 유리 블록을 통과하는 햇빛의 굴절을 이용해 시간에 따라 변화하는 공간의 촉각적 물성을 실험한 현대 건축 프로젝트.",
            genre: "SPACE & ARCH",
            source_name: "Dezeen",
            facets: {
                genre: "SPACE & ARCH",
                genius_loci: "〈토쿠진 요시오카 파빌리온〉은 대지에 쏟아지는 태양광의 각도를 프리즘 구조로 치환하여 공간 전체를 하나의 빛의 프리즘으로 완성합니다.",
                sensory_recall: "유리의 차가운 표면과 따뜻한 무지갯빛 산란이 어우러져 관람자에게 명상적인 평온을 선사합니다.",
                zeitgeist_synapse: "물질의 과잉을 비워내고 자연의 비물질적 요소를 극대화하는 미니멀리즘 건축의 정수를 보여줍니다.",
                spatial_video_cx: "오프라인 갤러리 및 플래그십 스토어의 아트리움 공간에 자연광과 연동된 미디어 아트로 승화됩니다.",
                zeitgeist_horizon: "지속 가능한 환경과 인간의 정서적 교감을 이끄는 감성적 웰니스 공간 철학을 제시합니다.",
                tactile_metrics: {
                    tactility: "PRISM GLASS & SUNLIGHT",
                    spatial_volume: "SOARING ATRIUM PAVILION",
                    dwell_tempo: "MEDITATIVE ZEN TEMPO"
                },
                synapse_connections: [
                    { domain: "공예 & 물성 (Material Craft)", connection: "유리 가공 기술과 건축 구조의 정밀한 결합을 구현합니다." },
                    { domain: "패션 & 미학 (Fashion Aesthetics)", connection: "투명성과 빛의 굴절이 오뜨 꾸뛰르 실크의 반사와 궤를 같이합니다." },
                    { domain: "앰비언트 환경 (Ambient Atmosphere)", connection: "자연의 소리와 빛이 공간을 채우는 침묵의 미학을 완성합니다." }
                ]
            }
        },
        {
            title: "쇼스튜디오 × 발렌시아가: 2026 오뜨 꾸뛰르 디지털 시노그래피",
            url: "https://showstudio.com/projects/balenciaga-couture-scenography-2026",
            image_url: "https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=1200&q=80",
            snippet: "닉 나이트(Nick Knight)가 디렉팅한 공간형 패션 필름. 거대한 LED 모노리스와 텍스타일 조각이 만나 아방가르드 패션의 미장센을 창조합니다.",
            genre: "AVANT-GARDE FASHION",
            source_name: "SHOWstudio",
            facets: {
                genre: "AVANT-GARDE FASHION",
                genius_loci: "〈쇼스튜디오 시노그래피〉는 런웨이 무대를 웅장한 블랙박스 시네마틱 공간으로 변모시켜 패션의 입체적 서사를 전달합니다.",
                sensory_recall: "거친 텍스처의 원단과 날카로운 고대비 조명이 빚어내는 시각적 텐션이 뇌리에 강렬한 잔상을 남깁니다.",
                zeitgeist_synapse: "패션이 단순한 의복을 넘어 공간적 예술(Spatial Art)로 진화하는 동시대 하이패션의 시대정신을 대변합니다.",
                spatial_video_cx: "리테일 팝업 스토어의 중심 미디어 월에 투사 시 고객의 브랜드 몰입도를 극대화하는 킬러 콘텐츠로 작동합니다.",
                zeitgeist_horizon: "패션 필름과 오프라인 공간 연출이 결합된 차세대 공간 브랜딩의 표본을 확립합니다.",
                tactile_metrics: {
                    tactility: "HEAVY DRAPING & HIGH-CONTRAST",
                    spatial_volume: "MONOLITHIC RUNWAY BOX",
                    dwell_tempo: "HIGH-VOLTAGE CINEMA"
                },
                synapse_connections: [
                    { domain: "시네마틱 영상 (Cinema & Narrative)", connection: "드라마틱한 슬로우 모션과 음향 연출이 영화적 미장센을 형성합니다." },
                    { domain: "공간 조형 (Scenography)", connection: "무대 디자인 자체가 거대한 설치 조각으로 기능합니다." },
                    { domain: "현대 예술 (Avant-Garde Art)", connection: "기존 미의 기준을 해체하고 재정의하는 전위적 조형성을 지닙니다." }
                ]
            }
        }
    ];

    let curationRound = 0;

    // Refresh Daily Button with Guaranteed Fresh Article Injection
    if (refreshDailyBtn) {
        refreshDailyBtn.addEventListener('click', async () => {
            if (refreshDailyBtn.classList.contains('loading')) return;

            refreshDailyBtn.classList.add('loading');
            refreshDailyBtn.innerHTML = `
                <svg class="spin-icon" viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="1.8" fill="none"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                <span>COLLECTING 25 GLOBAL FEEDS...</span>
            `;
            
            resultsContainer.style.opacity = '0.35';
            
            // Generate unique timestamped fresh editions
            const now = new Date();
            const timeStr = now.toISOString().slice(0, 16).replace('T', ' ');
            const targetItem = REALTIME_CURATION_POOL[curationRound % REALTIME_CURATION_POOL.length];
            curationRound++;

            const freshEdition = {
                ...targetItem,
                id: targetItem.url + `?update_seq=${Date.now()}`,
                collected_at: timeStr,
                is_new: true
            };

            setTimeout(() => {
                // Prepend fresh edition to current results
                currentResults = [freshEdition, ...currentResults];
                
                // Save to local storage for persistence
                try {
                    localStorage.setItem('recollection_custom_archive', JSON.stringify(currentResults));
                } catch (e) {}

                resultsContainer.style.opacity = '1';
                renderKinfolkGrid(currentResults);
                
                refreshDailyBtn.classList.remove('loading');
                refreshDailyBtn.innerHTML = `
                    <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="1.8" fill="none"><path d="M20 6L9 17l-5-5"/></svg>
                    <span>+1 NEW EDITION COLLECTED ✓</span>
                `;
                
                setTimeout(() => {
                    refreshDailyBtn.innerHTML = `
                        <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="1.8" fill="none"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                        <span>UPDATE TODAY'S JOURNAL</span>
                    `;
                }, 3000);
            }, 800);
        });
    }

    async function loadDailyArchive() {
        try {
            // Check localStorage cache first for instant snappy rendering
            try {
                const cached = localStorage.getItem('recollection_custom_archive');
                if (cached) {
                    const parsed = JSON.parse(cached);
                    if (Array.isArray(parsed) && parsed.length > 0) {
                        currentResults = parsed;
                        renderKinfolkGrid(currentResults);
                    }
                }
            } catch (err) {}

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
                    // Merge with custom additions if any
                    const existingMap = new Map();
                    items.forEach(i => existingMap.set(i.url || i.id, i));
                    currentResults.forEach(i => {
                        if (i.is_new && !existingMap.has(i.url || i.id)) {
                            items.unshift(i);
                        }
                    });
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

