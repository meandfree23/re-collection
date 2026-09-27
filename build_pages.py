"""
RE:COLLECTION 페이지 빌더 (2026-09-27 미니멀 개편)

- 원본 수집 데이터(data/daily/*.json, data/daily_archive.json)는 그대로 두고,
  깊이 읽기 결과(data/deep_reads.json)를 렌더링용 사본에만 덮어씌운다.
- index.html은 정규식 패치가 아니라 이 파일의 템플릿에서 매번 통째로 생성한다.
- 셀프힐링 가디언은 워크플로의 별도 단계에서 한 번만 돈다(여기서 다시 돌리지 않음).
"""
import json
import html
import os
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from difflib import SequenceMatcher

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DAILY_DIR = os.path.join(DATA_DIR, "daily")
ARCHIVE_FILE = os.path.join(DATA_DIR, "daily_archive.json")
FINGERPRINTS_FILE = os.path.join(DATA_DIR, "persistent_fingerprints.json")
DEEP_FILE = os.path.join(DATA_DIR, "deep_reads.json")
NOTES_FILE = os.path.join(DATA_DIR, "daily_notes.json")
ZEITGEIST_FILE = os.path.join(DATA_DIR, "zeitgeist_latest.json")
MANIFEST_FILE = os.path.join(DATA_DIR, "manifest.json")
KST = timezone(timedelta(hours=9))

GENRE_KO = {
    "SPACE & ARCH": "공간·건축",
    "CONTEMPORARY ART": "동시대 미술",
    "MEDIA FACADE & 3D": "미디어·3D",
    "AVANT-GARDE FASHION": "패션",
}
WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]


def esc(s):
    return html.escape(str(s or ""), quote=True)


def normalize_img_key(url):
    if not url or not isinstance(url, str):
        return ''
    try:
        p = urlparse(url.strip())
        path = p.path.lower().rstrip('/')
        filename = path.split('/')[-1] if path else ''
        if len(filename) > 6 and any(ext in filename for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
            return f"{p.netloc}:{filename}"
        return f"{p.netloc}{path}"
    except Exception:
        return url.strip().lower()


def normalize_title_key(title):
    if not title:
        return ''
    return re.sub(r'[^\w\s]', '', title.lower()).strip()


def deep_url_key(u):
    # deep_reader.url_key 와 동일한 규칙
    if not u:
        return ''
    try:
        p = urlparse(u.strip())
        return f"{p.netloc.lower().replace('www.', '')}{p.path.rstrip('/')}"
    except Exception:
        return u.strip().split('?')[0].rstrip('/')


def load_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def write_text(rel_paths, text):
    for rel in rel_paths:
        p = os.path.join(BASE_DIR, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(text)


def korean_date(ymd):
    try:
        d = datetime.strptime(ymd, '%Y-%m-%d')
        return f"{d.month}월 {d.day}일 {WEEKDAY_KO[d.weekday()]}요일"
    except Exception:
        return ymd


# ---------------------------------------------------------------------------
# 깊이 읽기 덮어쓰기
# ---------------------------------------------------------------------------
def apply_deep(item, deep_map):
    d = deep_map.get(deep_url_key(item.get('url', '')))
    if not d or not d.get('title_ko'):
        return item
    out = dict(item)
    out['title_mt'] = item.get('title', '')
    out['title'] = d.get('title_ko', item.get('title', ''))
    out['snippet'] = d.get('summary_ko', item.get('snippet', ''))
    out['deep'] = {k: d.get(k) for k in ('lens', 'why_now', 'mechanism', 'sensory', 'transfer', 'context',
                                         'keywords', 'evidence', 'kind', 'depth', 'grounding', 'depth_reason')}
    rs = d.get('research') or {}
    used = set(rs.get('used') or [])
    srcs = [x for x in (rs.get('sources') or []) if x.get('n') in used]
    out['deep']['sources'] = [{'n': x['n'], 'type': x.get('type', ''), 'title': x.get('title', ''), 'url': x.get('url', '')}
                              for x in srcs]
    ok = {x['n'] for x in srcs}
    out['deep']['findings'] = [f for f in (d.get('findings') or []) if f.get('s') in ok]
    out.pop('facets', None)  # 옛 장르 템플릿 문구는 화면에 쓰지 않으므로 용량만 차지
    return out


def depth_of(it):
    return int(((it.get('deep') or {}).get('depth')) or 0)


# ---------------------------------------------------------------------------
# HTML 조각 (static/script.js 의 렌더러와 같은 마크업)
# ---------------------------------------------------------------------------
def card_html(it):
    dp = it.get('deep') or {}
    url = it.get('url', '#')
    genre = GENRE_KO.get(it.get('genre', ''), it.get('genre', ''))
    pick = depth_of(it) >= 5
    media = ''
    if it.get('image_url'):
        media = (f'<a class="rc-card-media" href="{esc(url)}" target="_blank" rel="noopener noreferrer" tabindex="-1">'
                 f'<img src="{esc(it["image_url"])}" alt="" loading="lazy" '
                 f'onerror="this.parentElement.classList.add(\'is-empty\');this.remove()"></a>')
    rows = ''.join(f'<dt>{label}</dt><dd>{esc(dp.get(key))}</dd>'
                   for label, key in (('왜 지금', 'why_now'), ('작동 방식', 'mechanism'), ('감각과 물성', 'sensory'),
                                      ('계보·맥락', 'context'), ('연출로 가져갈 것', 'transfer')) if dp.get(key))
    srcmap = {x['n']: x for x in (dp.get('sources') or [])}
    findings = ''
    if dp.get('findings'):
        findings = '<ul class="rc-findings">' + ''.join(
            f'<li>{esc(f.get("text"))} <a href="{esc(srcmap.get(f.get("s"), {}).get("url", "#"))}" target="_blank" '
            f'rel="noopener noreferrer">{esc(srcmap.get(f.get("s"), {}).get("type", "출처"))}</a></li>'
            for f in dp['findings']) + '</ul>'
    evidence = f'<blockquote class="rc-quote">{esc(dp.get("evidence"))}</blockquote>' if dp.get('evidence') else ''
    sources = ''
    if srcmap:
        sources = '<ul class="rc-sources">' + ''.join(
            f'<li><span>{esc(x.get("type"))}</span><a href="{esc(x.get("url"))}" target="_blank" rel="noopener noreferrer">'
            f'{esc(x.get("title"))}</a></li>' for x in srcmap.values()) + '</ul>'
    foot = []
    if it.get('original_title'):
        foot.append(f'원제 {esc(it.get("original_title"))}')
    if dp.get('depth'):
        foot.append(f'가치 {int(dp["depth"])}/5' + (f' · {esc(dp.get("depth_reason"))}' if dp.get('depth_reason') else ''))
    if dp.get('keywords'):
        foot.append(' '.join(f'#{esc(k)}' for k in dp['keywords'][:5]))
    if dp.get('grounding') == 'thin':
        foot.append('원문 정보가 적어 해석을 절제했습니다.')
    foot_html = ''.join(f'<p>{x}</p>' for x in foot)
    deep = ''
    if dp.get('lens'):
        extra = f'<span>자료 {len(srcmap)}</span>' if srcmap else ''
        deep = (f'<p class="rc-card-lens">{esc(dp.get("lens"))}</p>'
                f'<details class="rc-card-deep"><summary>깊이 읽기{extra}</summary>'
                f'<dl>{rows}</dl>{findings}{evidence}{sources}<div class="rc-card-foot">{foot_html}</div></details>')
    meta = f'<span>{esc(genre)}</span><span>{esc(it.get("source_name", ""))}</span>'
    if pick:
        meta += '<span class="rc-pick">편집장 픽</span>'
    return (f'<article class="rc-card{" is-pick" if pick else ""}" data-genre="{esc(it.get("genre", ""))}" data-depth="{depth_of(it)}">'
            f'{media}<div class="rc-card-body"><p class="rc-card-meta">{meta}</p>'
            f'<h3 class="rc-card-title"><a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(it.get("title"))}</a></h3>'
            f'<p class="rc-card-summary">{esc(it.get("snippet"))}</p>{deep}</div></article>')


def pending_html(items):
    if not items:
        return ''
    li = ''.join(f'<li><a href="{esc(it.get("url", "#"))}" target="_blank" rel="noopener noreferrer">'
                 f'{esc(it.get("original_title") or it.get("title"))}</a><span>{esc(it.get("source_name", ""))}</span></li>'
                 for it in items)
    return (f'<details class="rc-pending"><summary>정독 대기 {len(items)}건</summary>'
            f'<p>원문을 읽고 한국어로 정리하는 중입니다. 그전에는 원문으로 먼저 보실 수 있어요.</p><ul>{li}</ul></details>')


def note_html(note, ymd):
    if not note or not note.get('headline'):
        return ''
    threads = ''
    for t in (note.get('threads') or [])[:3]:
        links = ''.join(f'<a href="{esc(x.get("url", "#"))}" target="_blank" rel="noopener noreferrer">{esc(x.get("title"))}</a>'
                        for x in (t.get('items') or [])[:4])
        threads += f'<li><strong>{esc(t.get("name"))}</strong><p>{esc(t.get("note"))}</p><div>{links}</div></li>'
    return (f'<p class="rc-kicker">편집 노트 · {esc(korean_date(ymd))}</p>'
            f'<h2 class="rc-note-title">{esc(note["headline"])}</h2>'
            f'<p class="rc-note-body">{esc(note.get("editorial"))}</p>'
            f'<ol class="rc-threads">{threads}</ol>')


def zeitgeist_line(zg):
    themes = [t.get('keyword') for t in (zg.get('themes') or [])[:5] if t.get('keyword')]
    if not themes:
        return ''
    return f'<p>이번 주 자주 등장한 주제 · {esc(" · ".join(themes))}</p>'


PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RE:COLLECTION — 공간과 기억의 데일리 저널</title>
<meta name="description" content="공간·미술·미디어·패션을 매일 원문부터 깊이 읽는 한국어 큐레이션 저널">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;500;600&display=swap" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css" rel="stylesheet">
<link rel="stylesheet" href="static/style.css?v={{V}}">
</head>
<body>
<div class="rc">
  <header class="rc-head">
    <a class="rc-logo" href="./">RE:COLLECTION</a>
    <p class="rc-sub">공간 · 미술 · 미디어 · 패션을 매일 원문부터 읽습니다</p>
    <nav class="rc-issue" aria-label="호 이동">
      <button type="button" id="rc-prev" aria-label="이전 호">&#8249;</button>
      <label class="rc-issue-current">
        <span id="rc-issue-label">{{ISSUE_LABEL}}</span>
        <select id="rc-issue-select" aria-label="호 선택">{{OPTIONS}}</select>
      </label>
      <button type="button" id="rc-next" aria-label="다음 호">&#8250;</button>
    </nav>
  </header>

  <section class="rc-note" id="rc-daily-note"{{NOTE_HIDDEN}}>{{NOTE}}</section>

  <div class="rc-bar">
    <div class="rc-filters" role="tablist" aria-label="분류">
      <button type="button" data-filter="ALL" class="is-on">전체</button>
      <button type="button" data-filter="SPACE & ARCH">공간·건축</button>
      <button type="button" data-filter="CONTEMPORARY ART">동시대 미술</button>
      <button type="button" data-filter="MEDIA FACADE & 3D">미디어·3D</button>
      <button type="button" data-filter="AVANT-GARDE FASHION">패션</button>
      <button type="button" data-filter="PICK">편집장 픽</button>
    </div>
    <input id="rc-search" type="search" placeholder="이 호에서 검색" aria-label="이 호에서 검색" autocomplete="off">
    <span class="rc-count" id="rc-count">{{COUNT}}</span>
  </div>

  <main class="rc-main">
    <div id="results-container" class="rc-grid" data-date="{{DATE}}">{{CARDS}}</div>
    <p class="rc-empty" id="rc-empty" hidden>조건에 맞는 글이 없습니다.</p>
    <div id="rc-pending-wrap">{{PENDING}}</div>
  </main>

  <footer class="rc-foot">
    {{ZEITGEIST}}
    <p>마지막 업데이트 {{STAMP}} · 전체 {{ISSUES}}개 호</p>
    <p class="rc-foot-logo">RE:COLLECTION</p>
  </footer>
</div>
<script src="data/manifest.js?v={{V}}"></script>
<script src="data/daily_notes.js?v={{V}}"></script>
<script src="static/script.js?v={{V}}"></script>
</body>
</html>
"""


def build_pages():
    items = load_json(ARCHIVE_FILE, [])
    if not isinstance(items, list):
        print(f"Archive file not usable at {ARCHIVE_FILE}")
        return

    # 1. 아카이브 중복 제거 (0.82 기준) + 지문 원장 갱신
    pristine, seen_img, seen_url, seen_t = [], set(), set(), []
    for it in items:
        url = it.get('url', '').strip().split('?')[0].rstrip('/')
        img_key = normalize_img_key(it.get('image_url', '').strip())
        t_key = normalize_title_key(it.get('title', '').strip())
        ot_key = normalize_title_key(it.get('original_title', '').strip())
        if (img_key and img_key in seen_img) or (url and url in seen_url):
            continue
        if any((t_key and SequenceMatcher(None, t_key, p).ratio() > 0.82) or
               (ot_key and SequenceMatcher(None, ot_key, p).ratio() > 0.82) for p in seen_t):
            continue
        if img_key:
            seen_img.add(img_key)
        if url:
            seen_url.add(url)
        if t_key:
            seen_t.append(t_key)
        if ot_key:
            seen_t.append(ot_key)
        pristine.append(it)
    items = pristine[:140]
    with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    ledger = {'urls': set(seen_url), 'images': set(seen_img), 'titles': set(seen_t)}
    old = load_json(FINGERPRINTS_FILE, {})
    for k in ledger:
        ledger[k].update(old.get(k, []))
    with open(FINGERPRINTS_FILE, 'w', encoding='utf-8') as f:
        json.dump({'version': '1.0', 'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                   'total_unique_urls': len(ledger['urls']), 'total_unique_images': len(ledger['images']),
                   'total_unique_titles': len(ledger['titles']),
                   'urls': sorted(ledger['urls']), 'images': sorted(ledger['images']), 'titles': sorted(ledger['titles'])},
                  f, ensure_ascii=False, indent=2)

    now = datetime.now(KST)
    version = int(now.timestamp())
    deep_map = load_json(DEEP_FILE, {})
    notes = load_json(NOTES_FILE, {})

    # 2. 데이터 스크립트
    archive_view = [apply_deep(it, deep_map) for it in items]
    js = 'window.PRELOADED_ARCHIVE = ' + json.dumps(archive_view, ensure_ascii=False) + ';'
    write_text(['docs/data/daily_archive.js', 'static/data/daily_archive.js'], js)

    dates = sorted([f[:-5] for f in os.listdir(DAILY_DIR) if f.endswith('.json')], reverse=True)
    counts, issues = {}, {}
    for d in dates:
        d_items = [apply_deep(x, deep_map) for x in load_json(os.path.join(DAILY_DIR, f'{d}.json'), [])]
        issues[d] = d_items
        counts[d] = {'n': len(d_items), 'deep': sum(1 for x in d_items if x.get('deep'))}
        write_text([f'docs/data/daily/{d}.js', f'static/data/daily/{d}.js'],
                   f"window.DAILY_ISSUE_{d.replace('-', '_')} = " + json.dumps(d_items, ensure_ascii=False) + ';')
    non_empty = [d for d in dates if counts[d]['n'] > 0]
    latest = non_empty[0] if non_empty else (dates[0] if dates else now.strftime('%Y-%m-%d'))
    manifest = {'latest_date': latest, 'dates': non_empty, 'counts': counts, 'total_issues': len(non_empty),
                'built_at': now.strftime('%Y-%m-%d %H:%M')}
    with open(MANIFEST_FILE, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    write_text(['docs/data/manifest.js', 'static/data/manifest.js'],
               'window.MANIFEST_DATA = ' + json.dumps(manifest, ensure_ascii=False) + ';')
    write_text(['docs/data/daily_notes.js', 'static/data/daily_notes.js'],
               'window.DAILY_NOTES = ' + json.dumps(notes, ensure_ascii=False) + ';')

    # 3. 최신 호 미리 렌더링 (깊이 순, 정독 대기는 아래 목록으로)
    cur = issues.get(latest, [])
    ready = sorted([x for x in cur if x.get('deep')], key=lambda x: -depth_of(x))
    pending = [x for x in cur if not x.get('deep')]
    options = ''.join(f'<option value="{d}"{" selected" if d == latest else ""}>{esc(korean_date(d))} · {counts[d]["n"]}건</option>'
                      for d in non_empty)
    note = note_html(notes.get(latest), latest)
    page = (PAGE.replace('{{V}}', str(version))
            .replace('{{ISSUE_LABEL}}', esc(korean_date(latest)))
            .replace('{{OPTIONS}}', options)
            .replace('{{NOTE_HIDDEN}}', '' if note else ' hidden')
            .replace('{{NOTE}}', note)
            .replace('{{COUNT}}', f'{len(ready)}편')
            .replace('{{DATE}}', latest)
            .replace('{{CARDS}}', ''.join(card_html(x) for x in ready))
            .replace('{{PENDING}}', pending_html(pending))
            .replace('{{ZEITGEIST}}', zeitgeist_line(load_json(ZEITGEIST_FILE, {})))
            .replace('{{STAMP}}', now.strftime('%Y.%m.%d %H:%M KST'))
            .replace('{{ISSUES}}', str(len(non_empty))))
    write_text(['docs/index.html', 'templates/index.html'], page)
    print(f"Built {latest}: {len(ready)} cards, {len(pending)} pending, {len(non_empty)} issues, archive {len(items)}")


if __name__ == "__main__":
    build_pages()
