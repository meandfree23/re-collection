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

  var state = { date: grid ? grid.getAttribute('data-date') : dates[0], items: null, filter: 'ALL', q: '' };

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
    if (vu.indexOf('player.vimeo.com/video/') >= 0 || vu.indexOf('youtube.com/embed/') >= 0 || vu.indexOf('youtube-nocookie.com/embed/') >= 0) {
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

  function matches(it) {
    if (state.filter === 'PICK' && !isPick(it)) return false;
    if (state.filter === 'VIDEO' && !hasVideo(it)) return false;
    if (state.filter !== 'ALL' && state.filter !== 'PICK' && state.filter !== 'VIDEO' && it.genre !== state.filter) return false;
    if (!state.q) return true;
    var dp = it.deep || {};
    var hay = [it.title, it.snippet, it.original_title, it.source_name, dp.lens, dp.why_now, dp.mechanism, dp.sensory, dp.context, dp.transfer, (dp.keywords || []).join(' ')].join(' ').toLowerCase();
    return state.q.split(/\s+/).every(function (w) { return hay.indexOf(w) >= 0; });
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

  // 인라인 필름 재생 및 카드 날짜 클릭 시 해당 호 이동
  grid.addEventListener('click', function (e) {
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

  window.addEventListener('hashchange', function () {
    var h = (location.hash || '').replace('#', '');
    if (h && h !== state.date && dates.indexOf(h) >= 0) go(h, { keepHash: true });
  });

  // 첫 진입: 주소의 #날짜가 있으면 그 호, 없으면 미리 렌더된 최신 호를 그대로 두고 데이터만 받아 둔다
  var hash = (location.hash || '').replace('#', '');
  if (hash && dates.indexOf(hash) >= 0 && hash !== state.date) {
    go(hash, { initial: true, keepHash: true });
  } else {
    renderHeader();
    loadIssue(state.date, function (items) { state.items = items; });
  }
})();
