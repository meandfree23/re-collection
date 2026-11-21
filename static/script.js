/* RE:COLLECTION — 미니멀 리더 (2026-09-27)
 * 데이터: window.MANIFEST_DATA, window.DAILY_NOTES, data/daily/{date}.js (window.DAILY_ISSUE_yyyy_mm_dd)
 * 마크업은 build_pages.py 의 card_html / note_html / pending_html 과 같다.
 */
(function () {
  'use strict';

  var GENRE_KO = { 'SPACE & ARCH': '공간·건축', 'CONTEMPORARY ART': '동시대 미술', 'MEDIA FACADE & 3D': '미디어·3D', 'AVANT-GARDE FASHION': '패션' };
  var WEEK = ['일', '월', '화', '수', '목', '금', '토'];
  var manifest = window.MANIFEST_DATA || { dates: [], counts: {} };
  var dates = (manifest.dates || []).slice();
  var notes = window.DAILY_NOTES || {};

  var grid = document.getElementById('results-container');
  var emptyEl = document.getElementById('rc-empty');
  var pendingWrap = document.getElementById('rc-pending-wrap');
  var noteEl = document.getElementById('rc-daily-note');
  var countEl = document.getElementById('rc-count');
  var labelEl = document.getElementById('rc-issue-label');
  var selectEl = document.getElementById('rc-issue-select');
  var prevBtn = document.getElementById('rc-prev');
  var nextBtn = document.getElementById('rc-next');
  var searchEl = document.getElementById('rc-search');
  var filterBtns = Array.prototype.slice.call(document.querySelectorAll('.rc-filters button'));
  var pinBar = document.getElementById('rc-pin-bar');
  var pinTotalEl = document.getElementById('rc-pin-total');

  var state = { date: grid ? grid.getAttribute('data-date') : dates[0], items: null, filter: 'ALL', q: '', pinCat: 'ALL' };

  /* ── 고정핀 & 분류 관리 (localStorage) ── */
  var PIN_KEY = 'rc_pins_v1';
  var CAT_KEY = 'rc_pin_cats_v1';
  var DEFAULT_CATS = ['미분류', '공간·세트', '연출·구도', '물성·조명', '미디어·아트'];

  function urlKey(u) { return String(u || '').split('#')[0].trim(); }
  function loadPins() {
    try { return JSON.parse(localStorage.getItem(PIN_KEY) || '{}') || {}; } catch (e) { return {}; }
  }
  function savePins(map) {
    try { localStorage.setItem(PIN_KEY, JSON.stringify(map)); } catch (e) {}
  }
  function loadCats() {
    try {
      var arr = JSON.parse(localStorage.getItem(CAT_KEY) || 'null');
      if (Array.isArray(arr) && arr.length) {
        if (arr.indexOf('미분류') < 0) arr.unshift('미분류');
        return arr;
      }
    } catch (e) {}
    return DEFAULT_CATS.slice();
  }
  function saveCats(arr) {
    try { localStorage.setItem(CAT_KEY, JSON.stringify(arr)); } catch (e) {}
  }
  function updatePinTabCount() {
    if (!pinTotalEl) return;
    var n = Object.keys(loadPins()).length;
    pinTotalEl.textContent = n ? ' (' + n + ')' : '';
  }
  function findItemByUrl(u) {
    var k = urlKey(u);
    if (!k) return null;
    if (Array.isArray(state.items)) {
      for (var i = 0; i < state.items.length; i++) {
        if (urlKey(state.items[i].url) === k) return state.items[i];
      }
    }
    if (Array.isArray(window.SEARCH_INDEX)) {
      for (var j = 0; j < window.SEARCH_INDEX.length; j++) {
        if (urlKey(window.SEARCH_INDEX[j].url) === k) return window.SEARCH_INDEX[j];
      }
    }
    return loadPins()[k] || null;
  }
  function extractItemFromCard(card, u) {
    var titleEl = card.querySelector('.rc-card-title a');
    var imgEl = card.querySelector('.rc-card-media img');
    var sumEl = card.querySelector('.rc-card-summary');
    var lensEl = card.querySelector('.rc-card-lens');
    var metas = card.querySelectorAll('.rc-card-meta > span');
    var dateEl = card.querySelector('.rc-card-date[data-issue]');
    return {
      url: u,
      title: titleEl ? titleEl.textContent.trim() : '',
      image_url: imgEl ? imgEl.getAttribute('src') : '',
      genre: card.getAttribute('data-genre') || '',
      source_name: metas[1] ? metas[1].textContent.trim() : '',
      issue_date: dateEl ? dateEl.getAttribute('data-issue') : state.date,
      snippet: sumEl ? sumEl.textContent.trim() : '',
      deep: lensEl ? { lens: lensEl.textContent.trim(), depth: parseInt(card.getAttribute('data-depth') || '0', 10) } : null,
      is_pick: card.classList.contains('is-pick')
    };
  }
  function hydratePins() {
    if (!grid) return;
    var pins = loadPins();
    var cats = loadCats();
    var cards = grid.querySelectorAll('.rc-card');
    for (var i = 0; i < cards.length; i++) {
      var card = cards[i];
      var a = card.querySelector('.rc-card-title a');
      var meta = card.querySelector('.rc-card-meta');
      if (!a || !meta) continue;
      var u = a.getAttribute('href') || '';
      var k = urlKey(u);
      var pin = pins[k];
      var old = meta.querySelector('.rc-pin-wrap');
      if (old) old.remove();
      var wrap = document.createElement('span');
      wrap.className = 'rc-pin-wrap';
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'rc-pin-btn' + (pin ? ' is-pinned' : '');
      btn.setAttribute('data-pin-url', u);
      btn.textContent = pin ? '📌 고정됨' : '📌 고정';
      btn.title = pin ? '고정핀 해제' : '이 글 고정핀으로 저장';
      wrap.appendChild(btn);
      if (pin) {
        var sel = document.createElement('select');
        sel.className = 'rc-pin-cat-sel';
        sel.setAttribute('data-pin-url', u);
        sel.setAttribute('aria-label', '고정핀 분류');
        var curCat = pin.cat || '미분류';
        var allCats = cats.slice();
        if (allCats.indexOf(curCat) < 0) allCats.push(curCat);
        allCats.forEach(function (c) {
          var opt = document.createElement('option');
          opt.value = c;
          opt.textContent = c;
          if (c === curCat) opt.selected = true;
          sel.appendChild(opt);
        });
        wrap.appendChild(sel);
      }
      meta.appendChild(wrap);
    }
  }
  function renderPinBar() {
    if (!pinBar) return;
    if (state.filter !== 'PINNED') { pinBar.hidden = true; return; }
    pinBar.hidden = false;
    var pins = loadPins();
    var cats = loadCats();
    var counts = {};
    var total = 0;
    Object.keys(pins).forEach(function (k) {
      total++;
      var c = pins[k].cat || '미분류';
      counts[c] = (counts[c] || 0) + 1;
      if (cats.indexOf(c) < 0) cats.push(c);
    });
    if (state.pinCat !== 'ALL' && cats.indexOf(state.pinCat) < 0) state.pinCat = 'ALL';
    var chipsHtml = '<button type="button" class="rc-pin-chip' + (state.pinCat === 'ALL' ? ' is-on' : '') + '" data-pin-cat="ALL">전체<span>' + total + '</span></button>';
    cats.forEach(function (c) {
      chipsHtml += '<button type="button" class="rc-pin-chip' + (state.pinCat === c ? ' is-on' : '') + '" data-pin-cat="' + esc(c) + '">' + esc(c) + '<span>' + (counts[c] || 0) + '</span></button>';
    });
    var manageHtml = '<button type="button" class="rc-pin-act" data-pin-act="add-cat">+ 새 분류</button>';
    if (state.pinCat !== 'ALL' && state.pinCat !== '미분류') {
      manageHtml += '<button type="button" class="rc-pin-act" data-pin-act="rename-cat">이름 변경</button>';
      manageHtml += '<button type="button" class="rc-pin-act is-danger" data-pin-act="del-cat">분류 삭제</button>';
    }
    manageHtml += '<button type="button" class="rc-pin-act" data-pin-act="export" title="고정핀 JSON 백업">내보내기</button>';
    manageHtml += '<button type="button" class="rc-pin-act" data-pin-act="import" title="백업 파일 불러오기">불러오기</button>';
    pinBar.innerHTML = '<div class="rc-pin-chips">' + chipsHtml + '</div><div class="rc-pin-actions">' + manageHtml + '</div>';
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function koreanDate(ymd) {
    var p = (ymd || '').split('-');
    if (p.length !== 3) return ymd;
    var d = new Date(+p[0], +p[1] - 1, +p[2]);
    return (+p[1]) + '월 ' + (+p[2]) + '일 ' + WEEK[d.getDay()] + '요일';
  }
  function depthOf(it) { return parseInt(((it.deep || {}).depth) || 0, 10); }

  function isPick(it) {
    if (it.is_pick) return true;
    if (depthOf(it) >= 5) return true;
    var note = notes[it.issue_date || state.date];
    if (note && note.threads) {
      var u = (it.url || '').split('?')[0].replace(/\/+$/, '');
      for (var i = 0; i < note.threads.length; i++) {
        var items = note.threads[i].items || [];
        for (var j = 0; j < items.length; j++) {
          var tu = (items[j].url || '').split('?')[0].replace(/\/+$/, '');
          if (tu && tu === u) return true;
        }
      }
    }
    return false;
  }

  function playableVideoUrl(it) {
    var vu = String(it.video_url || '').trim();
    if (!vu) return '';
    var vLow = vu.toLowerCase().split('?')[0];
    if (vu.indexOf('player.vimeo.com/video/') >= 0 || vu.indexOf('youtube.com/embed/') >= 0 || vu.indexOf('youtube-nocookie.com/embed/') >= 0 || vu.indexOf('players.brightcove.net/') >= 0) {
      return vu;
    }
    if (/(\.mp4|\.webm)$/.test(vLow)) return vu;
    return '';
  }

  function hasVideo(it) {
    if (playableVideoUrl(it)) return true;
    var dp = it.deep || {};
    if (dp.kind === '영상·필름') return true;
    if (it.source_name === 'Stash Media' || it.source_name === 'Motionographer' || it.source_name === 'NOWNESS') return true;
    return false;
  }

  function cardHtml(it) {
    var dp = it.deep || {};
    var url = it.url || '#';
    var pick = isPick(it);
    var vUrl = playableVideoUrl(it);
    var isVid = hasVideo(it);
    var media = '';
    if (it.image_url) {
      if (vUrl) {
        media = '<div class="rc-card-media" data-video="' + esc(vUrl) + '">' +
          '<a class="rc-card-thumb" href="' + esc(url) + '" target="_blank" rel="noopener noreferrer" tabindex="-1">' +
          '<img src="' + esc(it.image_url) + '" alt="" loading="lazy" onerror="this.closest(\'.rc-card-media\').classList.add(\'is-empty\');this.remove()"></a>' +
          '<button type="button" class="rc-play-btn" data-video="' + esc(vUrl) + '" aria-label="필름 재생">&#9654; 필름</button>' +
          '</div>';
      } else {
        media = '<a class="rc-card-media" href="' + esc(url) + '" target="_blank" rel="noopener noreferrer" tabindex="-1"><img src="' + esc(it.image_url) + '" alt="" loading="lazy" onerror="this.parentElement.classList.add(\'is-empty\');this.remove()"></a>';
      }
    }
    var rows = [['왜 지금', dp.why_now], ['작동 방식', dp.mechanism], ['감각과 물성', dp.sensory], ['계보·맥락', dp.context], ['연출로 가져갈 것', dp.transfer]]
      .filter(function (r) { return r[1]; }).map(function (r) { return '<dt>' + r[0] + '</dt><dd>' + esc(r[1]) + '</dd>'; }).join('');
    var srcs = dp.sources || [];
    var map = {}; srcs.forEach(function (x) { map[x.n] = x; });
    var findings = (dp.findings || []).length ? '<ul class="rc-findings">' + dp.findings.map(function (f) {
      var s = map[f.s] || {};
      return '<li>' + esc(f.text) + ' <a href="' + esc(s.url || '#') + '" target="_blank" rel="noopener noreferrer">' + esc(s.type || '출처') + '</a></li>';
    }).join('') + '</ul>' : '';
    var evidence = dp.evidence ? '<blockquote class="rc-quote">' + esc(dp.evidence) + '</blockquote>' : '';
    var sources = srcs.length ? '<ul class="rc-sources">' + srcs.map(function (x) {
      return '<li><span>' + esc(x.type) + '</span><a href="' + esc(x.url) + '" target="_blank" rel="noopener noreferrer">' + esc(x.title) + '</a></li>';
    }).join('') + '</ul>' : '';
    var foot = [];
    if (it.original_title) foot.push('원제 ' + esc(it.original_title));
    if (dp.depth) foot.push('가치 ' + parseInt(dp.depth, 10) + '/5' + (dp.depth_reason ? ' · ' + esc(dp.depth_reason) : ''));
    if ((dp.keywords || []).length) foot.push(dp.keywords.slice(0, 5).map(function (k) { return '#' + esc(k); }).join(' '));
    if (dp.grounding === 'thin') foot.push('원문 정보가 적어 해석을 절제했습니다.');
    var deep = '';
    if (dp.lens) {
      deep = '<p class="rc-card-lens">' + esc(dp.lens) + '</p>' +
        '<details class="rc-card-deep"><summary>깊이 읽기' + (srcs.length ? '<span>자료 ' + srcs.length + '</span>' : '') + '</summary>' +
        '<dl>' + rows + '</dl>' + findings + evidence + sources +
        '<div class="rc-card-foot">' + foot.map(function (x) { return '<p>' + x + '</p>'; }).join('') + '</div></details>';
    }
    var colAt = it.collected_at || it.issue_date || '';
    var ymd = (colAt.length >= 10) ? colAt.substring(0, 10) : '';
    var dateBadge = (colAt.length >= 10) ? '<span class="rc-card-date" data-issue="' + esc(ymd) + '" title="' + esc(ymd) + ' 호로 이동">' + esc(colAt.substring(5, 10).replace('-', '.')) + '</span>' : '';
    var meta = '<span>' + esc(GENRE_KO[it.genre] || it.genre || '') + '</span><span>' + esc(it.source_name || '') + '</span>' + dateBadge +
      (isVid ? '<span class="rc-video-tag">필름</span>' : '') +
      (pick ? '<span class="rc-pick">편집장 픽</span>' : '');
    return '<article class="rc-card' + (pick ? ' is-pick' : '') + (isVid ? ' has-video' : '') + '" data-genre="' + esc(it.genre || '') + '" data-depth="' + depthOf(it) + '">' +
      media + '<div class="rc-card-body"><p class="rc-card-meta">' + meta + '</p>' +
      '<h3 class="rc-card-title"><a href="' + esc(url) + '" target="_blank" rel="noopener noreferrer">' + esc(it.title) + '</a></h3>' +
      '<p class="rc-card-summary">' + esc(it.snippet) + '</p>' + deep + '</div></article>';
  }

  function pendingHtml(list) {
    if (!list.length) return '';
    return '<details class="rc-pending"><summary>정독 대기 ' + list.length + '건</summary>' +
      '<p>원문을 읽고 한국어로 정리하는 중입니다. 그전에는 원문으로 먼저 보실 수 있어요.</p><ul>' +
      list.map(function (it) {
        return '<li><a href="' + esc(it.url || '#') + '" target="_blank" rel="noopener noreferrer">' + esc(it.original_title || it.title) + '</a><span>' + esc(it.source_name || '') + '</span></li>';
      }).join('') + '</ul></details>';
  }

  function noteHtml(note, ymd) {
    if (!note || !note.headline) return '';
    var threads = (note.threads || []).slice(0, 3).map(function (t) {
      var links = (t.items || []).slice(0, 4).map(function (x) { return '<a href="' + esc(x.url || '#') + '" target="_blank" rel="noopener noreferrer">' + esc(x.title) + '</a>'; }).join('');
      return '<li><strong>' + esc(t.name) + '</strong><p>' + esc(t.note) + '</p><div>' + links + '</div></li>';
    }).join('');
    return '<p class="rc-kicker">편집 노트 · ' + esc(koreanDate(ymd)) + '</p><h2 class="rc-note-title">' + esc(note.headline) + '</h2>' +
      '<p class="rc-note-body">' + esc(note.editorial || '') + '</p><ol class="rc-threads">' + threads + '</ol>';
  }

  function matchesText(it) {
    if (!state.q) return true;
    var dp = it.deep || {};
    var hay = [it.title, it.snippet, it.original_title, it.source_name, dp.lens, dp.why_now, dp.mechanism, dp.sensory, dp.context, dp.transfer, (dp.keywords || []).join(' ')].join(' ').toLowerCase();
    return state.q.split(/\s+/).every(function (w) { return hay.indexOf(w) >= 0; });
  }

  function matches(it) {
    if (state.filter === 'PICK' && !isPick(it)) return false;
    if (state.filter === 'VIDEO' && !hasVideo(it)) return false;
    if (state.filter !== 'ALL' && state.filter !== 'PICK' && state.filter !== 'VIDEO' && state.filter !== 'PINNED' && it.genre !== state.filter) return false;
    return matchesText(it);
  }

  var searchIndexLoading = false;
  function loadSearchIndex(cb) {
    if (Array.isArray(window.SEARCH_INDEX)) { cb(window.SEARCH_INDEX); return; }
    if (searchIndexLoading) return;
    searchIndexLoading = true;
    var s = document.createElement('script');
    s.src = 'data/search_index.js?v=' + (manifest.built_at || '').replace(/\D/g, '');
    s.onload = function () {
      searchIndexLoading = false;
      cb(Array.isArray(window.SEARCH_INDEX) ? window.SEARCH_INDEX : []);
    };
    s.onerror = function () {
      searchIndexLoading = false;
      cb([]);
    };
    document.body.appendChild(s);
  }

  function render() {
    renderPinBar();
    if (state.filter === 'PINNED') {
      var pins = loadPins();
      var allPinned = Object.keys(pins).map(function (k) { return pins[k]; })
        .sort(function (a, b) { return (b.pinned_at || 0) - (a.pinned_at || 0); });
      var pinShown = allPinned.filter(function (it) {
        if (state.pinCat !== 'ALL' && (it.cat || '미분류') !== state.pinCat) return false;
        return matchesText(it);
      });
      grid.innerHTML = pinShown.map(cardHtml).join('');
      grid.setAttribute('data-date', state.date);
      emptyEl.hidden = pinShown.length > 0;
      countEl.textContent = (state.pinCat === 'ALL' && !state.q) ? '고정핀 ' + allPinned.length + '편' : pinShown.length + ' / ' + allPinned.length + '편';
      pendingWrap.innerHTML = '';
      hydratePins();
      return;
    }
    if (!state.items) return;
    if (state.q && Array.isArray(window.SEARCH_INDEX) && window.SEARCH_INDEX.length > 0) {
      var globalMatches = window.SEARCH_INDEX.filter(matches)
        .map(function (it, i) { return { it: it, i: i }; })
        .sort(function (a, b) {
          var curA = ((a.it.issue_date || '') === state.date) ? 1 : 0;
          var curB = ((b.it.issue_date || '') === state.date) ? 1 : 0;
          if (curB !== curA) return curB - curA;
          var pa = isPick(a.it) ? 1 : 0;
          var pb = isPick(b.it) ? 1 : 0;
          if (pb !== pa) return pb - pa;
          return depthOf(b.it) - depthOf(a.it) || a.i - b.i;
        })
        .map(function (x) { return x.it; });
      var totalHits = globalMatches.length;
      var capped = globalMatches.slice(0, 90);
      grid.innerHTML = capped.map(cardHtml).join('');
      grid.setAttribute('data-date', state.date);
      emptyEl.hidden = totalHits > 0;
      countEl.textContent = '전체 호 ' + totalHits + '편';
      pendingWrap.innerHTML = '';
      hydratePins();
      return;
    }

    var ready = state.items.filter(function (x) { return x.deep; })
      .map(function (it, i) { return { it: it, i: i }; })
      .sort(function (a, b) {
        var pa = isPick(a.it) ? 1 : 0;
        var pb = isPick(b.it) ? 1 : 0;
        if (pb !== pa) return pb - pa;
        return depthOf(b.it) - depthOf(a.it) || a.i - b.i;
      })
      .map(function (x) { return x.it; });
    var shown = ready.filter(matches);
    if (state.filter === 'VIDEO' && !state.q && shown.length === 0) {
      if (Array.isArray(window.SEARCH_INDEX) && window.SEARCH_INDEX.length > 0) {
        var recentVids = window.SEARCH_INDEX.filter(hasVideo).slice(0, 36);
        grid.innerHTML = recentVids.map(cardHtml).join('');
        grid.setAttribute('data-date', state.date);
        emptyEl.hidden = recentVids.length > 0;
        countEl.textContent = '최근 필름 ' + recentVids.length + '편';
        pendingWrap.innerHTML = '';
        hydratePins();
        return;
      } else {
        loadSearchIndex(function () { render(); });
      }
    }
    grid.innerHTML = shown.map(cardHtml).join('');
    grid.setAttribute('data-date', state.date);
    emptyEl.hidden = shown.length > 0;
    countEl.textContent = (state.filter === 'ALL' && !state.q) ? ready.length + '편' : shown.length + ' / ' + ready.length + '편';
    pendingWrap.innerHTML = (state.filter === 'ALL' && !state.q) ? pendingHtml(state.items.filter(function (x) { return !x.deep; })) : '';
    hydratePins();
  }

  function renderHeader() {
    var note = noteHtml(notes[state.date], state.date);
    noteEl.innerHTML = note;
    noteEl.hidden = !note;
    labelEl.textContent = koreanDate(state.date);
    if (selectEl.value !== state.date) selectEl.value = state.date;
    var idx = dates.indexOf(state.date);
    prevBtn.disabled = idx < 0 || idx >= dates.length - 1;   // 더 오래된 호
    nextBtn.disabled = idx <= 0;                              // 더 최근 호
  }

  function loadIssue(ymd, cb) {
    var v = 'DAILY_ISSUE_' + ymd.replace(/-/g, '_');
    if (Array.isArray(window[v])) { cb(window[v]); return; }
    var s = document.createElement('script');
    s.src = 'data/daily/' + ymd + '.js?v=' + (manifest.built_at || '').replace(/\D/g, '');
    s.onload = function () { cb(Array.isArray(window[v]) ? window[v] : []); };
    s.onerror = function () { cb([]); };
    document.body.appendChild(s);
  }

  function go(ymd, opts) {
    if (!ymd || dates.indexOf(ymd) < 0) return;
    state.date = ymd;
    renderHeader();
    if (!(opts && opts.keepHash)) history.replaceState(null, '', '#' + ymd);
    grid.setAttribute('aria-busy', 'true');
    loadIssue(ymd, function (items) {
      if (state.date !== ymd) return;
      state.items = items;
      grid.removeAttribute('aria-busy');
      render();
      if (!(opts && opts.initial)) window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // 호 이동
  prevBtn.addEventListener('click', function () { var i = dates.indexOf(state.date); if (i < dates.length - 1) go(dates[i + 1]); });
  nextBtn.addEventListener('click', function () { var i = dates.indexOf(state.date); if (i > 0) go(dates[i - 1]); });
  selectEl.addEventListener('change', function () { go(selectEl.value); });
  document.addEventListener('keydown', function (e) {
    if (e.target && /INPUT|SELECT|TEXTAREA/.test(e.target.tagName)) return;
    if (e.key === 'ArrowLeft') prevBtn.click();
    if (e.key === 'ArrowRight') nextBtn.click();
  });

  // 분류·검색
  filterBtns.forEach(function (b) {
    b.addEventListener('click', function () {
      filterBtns.forEach(function (x) { x.classList.toggle('is-on', x === b); });
      state.filter = b.getAttribute('data-filter') || 'ALL';
      render();
    });
  });
  var t;
  searchEl.addEventListener('focus', function () {
    loadSearchIndex(function () {});
  });
  searchEl.addEventListener('input', function () {
    clearTimeout(t);
    t = setTimeout(function () {
      state.q = searchEl.value.trim().toLowerCase();
      render();
      if (state.q && !Array.isArray(window.SEARCH_INDEX)) {
        loadSearchIndex(function () { render(); });
      }
    }, 120);
  });

  // 인라인 필름 재생, 고정핀 토글, 카드 날짜 클릭 시 해당 호 이동
  grid.addEventListener('click', function (e) {
    var pinBtn = e.target.closest ? e.target.closest('.rc-pin-btn') : null;
    if (pinBtn) {
      e.preventDefault();
      e.stopPropagation();
      var u = pinBtn.getAttribute('data-pin-url') || '';
      var k = urlKey(u);
      if (!k) return;
      var pins = loadPins();
      if (pins[k]) {
        delete pins[k];
      } else {
        var card = pinBtn.closest('.rc-card');
        var base = findItemByUrl(u) || (card ? extractItemFromCard(card, u) : { url: u, title: u });
        var snap = JSON.parse(JSON.stringify(base));
        snap.cat = (state.filter === 'PINNED' && state.pinCat !== 'ALL') ? state.pinCat : '미분류';
        snap.pinned_at = Date.now();
        pins[k] = snap;
      }
      savePins(pins);
      updatePinTabCount();
      if (state.filter === 'PINNED') render();
      else hydratePins();
      return;
    }
    var playBtn = e.target.closest ? e.target.closest('.rc-play-btn') : null;
    if (playBtn) {
      e.preventDefault();
      e.stopPropagation();
      var vUrl = playBtn.getAttribute('data-video') || '';
      var box = playBtn.closest('.rc-card-media');
      if (!vUrl || !box) return;
      var vLow = vUrl.toLowerCase().split('?')[0];
      box.classList.add('is-playing');
      if (/(\.mp4|\.webm)$/.test(vLow)) {
        box.innerHTML = '<video src="' + esc(vUrl) + '" controls autoplay playsinline></video>';
      } else {
        var sep = vUrl.indexOf('?') >= 0 ? '&' : '?';
        var embedUrl = vUrl + sep + 'autoplay=1';
        box.innerHTML = '<iframe src="' + esc(embedUrl) + '" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen></iframe>';
      }
      return;
    }
    var dateBadge = e.target.closest ? e.target.closest('.rc-card-date[data-issue]') : null;
    if (dateBadge) {
      var targetDate = dateBadge.getAttribute('data-issue');
      if (targetDate && dates.indexOf(targetDate) >= 0) {
        e.preventDefault();
        if (state.q) {
          state.q = '';
          searchEl.value = '';
        }
        go(targetDate);
      }
    }
  });

  grid.addEventListener('change', function (e) {
    var sel = e.target && e.target.classList && e.target.classList.contains('rc-pin-cat-sel') ? e.target : null;
    if (!sel) return;
    var k = urlKey(sel.getAttribute('data-pin-url') || '');
    var pins = loadPins();
    if (pins[k]) {
      pins[k].cat = sel.value || '미분류';
      savePins(pins);
      if (state.filter === 'PINNED') render();
    }
  });

  if (pinBar) {
    pinBar.addEventListener('click', function (e) {
      var chip = e.target.closest ? e.target.closest('.rc-pin-chip') : null;
      if (chip) {
        state.pinCat = chip.getAttribute('data-pin-cat') || 'ALL';
        render();
        return;
      }
      var actBtn = e.target.closest ? e.target.closest('.rc-pin-act') : null;
      if (!actBtn) return;
      var act = actBtn.getAttribute('data-pin-act');
      if (act === 'add-cat') {
        var name = prompt('새 분류 이름을 입력하세요 (예: 브랜드, 텍스처, 세트):');
        name = (name || '').trim();
        if (!name) return;
        var cats = loadCats();
        if (cats.indexOf(name) < 0) {
          cats.push(name);
          saveCats(cats);
        }
        state.pinCat = name;
        render();
      } else if (act === 'rename-cat') {
        var cur = state.pinCat;
        if (!cur || cur === 'ALL' || cur === '미분류') return;
        var next = prompt('새 분류 이름을 입력하세요:', cur);
        next = (next || '').trim();
        if (!next || next === cur) return;
        var catsR = loadCats().map(function (c) { return c === cur ? next : c; });
        saveCats(catsR);
        var pinsR = loadPins();
        Object.keys(pinsR).forEach(function (k) { if ((pinsR[k].cat || '미분류') === cur) pinsR[k].cat = next; });
        savePins(pinsR);
        state.pinCat = next;
        render();
      } else if (act === 'del-cat') {
        var curD = state.pinCat;
        if (!curD || curD === 'ALL' || curD === '미분류') return;
        if (!confirm('"' + curD + '" 분류를 삭제할까요?\n(안에 있던 고정핀은 "미분류"로 이동됩니다.)')) return;
        var catsD = loadCats().filter(function (c) { return c !== curD; });
        saveCats(catsD);
        var pinsD = loadPins();
        Object.keys(pinsD).forEach(function (k) { if ((pinsD[k].cat || '미분류') === curD) pinsD[k].cat = '미분류'; });
        savePins(pinsD);
        state.pinCat = 'ALL';
        render();
      } else if (act === 'export') {
        var data = { version: 1, exported_at: new Date().toISOString(), cats: loadCats(), pins: loadPins() };
        var blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'recollection-pins-' + new Date().toISOString().slice(0, 10) + '.json';
        a.click();
        setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
      } else if (act === 'import') {
        var inp = document.createElement('input');
        inp.type = 'file';
        inp.accept = '.json,application/json';
        inp.onchange = function () {
          var f = inp.files && inp.files[0];
          if (!f) return;
          var r = new FileReader();
          r.onload = function () {
            try {
              var parsed = JSON.parse(r.result);
              var curPins = loadPins();
              var inPins = parsed.pins || {};
              Object.keys(inPins).forEach(function (k) { if (!curPins[k]) curPins[k] = inPins[k]; });
              savePins(curPins);
              if (Array.isArray(parsed.cats)) {
                var mergedCats = loadCats();
                parsed.cats.forEach(function (c) { if (c && mergedCats.indexOf(c) < 0) mergedCats.push(c); });
                saveCats(mergedCats);
              }
              updatePinTabCount();
              render();
            } catch (err) {
              alert('JSON 파일을 읽을 수 없습니다.');
            }
          };
          r.readAsText(f);
        };
        inp.click();
      }
    });
  }

  window.addEventListener('hashchange', function () {
    var h = (location.hash || '').replace('#', '');
    if (h && h !== state.date && dates.indexOf(h) >= 0) go(h, { keepHash: true });
  });

  // 첫 진입: 주소의 #날짜가 있으면 그 호, 없으면 미리 렌더된 최신 호를 그대로 두고 데이터만 받아 둔다
  updatePinTabCount();
  var hash = (location.hash || '').replace('#', '');
  if (hash && dates.indexOf(hash) >= 0 && hash !== state.date) {
    go(hash, { initial: true, keepHash: true });
  } else {
    renderHeader();
    hydratePins();
    loadIssue(state.date, function (items) { state.items = items; });
  }
})();
