import json
import html
import os
import re
from datetime import datetime
from urllib.parse import urlparse
from difflib import SequenceMatcher

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_FILE = os.path.join(BASE_DIR, "data", "daily_archive.json")

def normalize_img_key(url):
    if not url or not isinstance(url, str): return ''
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
    if not title: return ''
    return re.sub(r'[^\w\s]', '', title.lower()).strip()

FINGERPRINTS_FILE = os.path.join(BASE_DIR, "data", "persistent_fingerprints.json")
DEEP_FILE = os.path.join(BASE_DIR, "data", "deep_reads.json")
NOTES_FILE = os.path.join(BASE_DIR, "data", "daily_notes.json")


def deep_url_key(u):
    # deep_reader.url_key 와 동일한 규칙 (쿼리스트링/www/끝 슬래시 제거)
    if not u:
        return ''
    try:
        p = urlparse(u.strip())
        return f"{p.netloc.lower().replace('www.', '')}{p.path.rstrip('/')}"
    except Exception:
        return u.strip().split('?')[0].rstrip('/')


def load_deep_reads():
    try:
        with open(DEEP_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def load_daily_notes():
    try:
        with open(NOTES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def apply_deep(item, deep_map):
    """원본 수집 데이터는 그대로 두고, 렌더링용 사본에만 깊이 읽기 결과를 덮어씌운다."""
    d = deep_map.get(deep_url_key(item.get('url', '')))
    if not d or not d.get('title_ko'):
        return item
    out = dict(item)
    out['title_mt'] = item.get('title', '')
    out['title'] = d.get('title_ko', item.get('title', ''))
    out['snippet'] = d.get('summary_ko', item.get('snippet', ''))
    out['deep'] = {k: d.get(k) for k in ('lens', 'why_now', 'mechanism', 'sensory', 'transfer',
                                         'keywords', 'evidence', 'kind', 'depth', 'grounding')}
    return out


def render_deep_block(item):
    dp = item.get('deep') or {}
    if not dp.get('lens'):
        return ''
    kws = ''.join(f'<span class="rc-kw">#{html.escape(k)}</span>' for k in (dp.get('keywords') or [])[:5])
    rows = []
    for label, key in (('왜 지금', 'why_now'), ('작동 방식', 'mechanism'), ('감각과 물성', 'sensory'), ('연출로 가져갈 것', 'transfer')):
        if dp.get(key):
            rows.append(f'<dt>{label}</dt><dd>{html.escape(dp[key])}</dd>')
    ev = ''
    if dp.get('evidence'):
        ev = f'<blockquote class="rc-evidence">“{html.escape(dp["evidence"])}”<cite>원문 인용 · {html.escape(item.get("source_name", ""))}</cite></blockquote>'
    orig = ''
    if item.get('original_title'):
        orig = f'<p class="rc-orig">원제 · {html.escape(item.get("original_title", ""))}</p>'
    thin = '<p class="rc-thin">원문 정보가 적어 해석을 절제했습니다.</p>' if dp.get('grounding') == 'thin' else ''
    return (
        f'<div class="rc-lens"><span class="rc-lens-label">큐레이터의 시선</span><p>{html.escape(dp["lens"])}</p></div>'
        f'<div class="rc-kws">{kws}</div>'
        f'<details class="rc-deep"><summary>깊이 읽기</summary><dl>{"".join(rows)}</dl>{ev}{orig}{thin}</details>'
    )


def render_daily_note(note):
    if not note or not note.get('headline'):
        return ''
    d = note.get('date', '')
    threads = []
    for t in note.get('threads', [])[:3]:
        links = ''.join(
            f'<a href="{html.escape(x.get("url", "#"))}" target="_blank" rel="noopener noreferrer">{html.escape(x.get("title", ""))}</a>'
            for x in t.get('items', [])[:5])
        threads.append(
            f'<div class="rc-thread"><h4>{html.escape(t.get("name", ""))}</h4>'
            f'<p>{html.escape(t.get("note", ""))}</p><div class="rc-thread-links">{links}</div></div>')
    return (
        f'<span class="rc-note-tag">EDITOR\'S NOTE · {html.escape(d[5:].replace("-", "."))} 호 · {note.get("based_on", 0)}개 항목을 읽고</span>'
        f'<h2 class="rc-note-headline">{html.escape(note["headline"])}</h2>'
        f'<p class="rc-note-body">{html.escape(note.get("editorial", ""))}</p>'
        f'<div class="rc-threads">{"".join(threads)}</div>'
    )

from self_heal_guardian import run_self_healing_guardian

def build_pages():
    # Automatically execute 5-layer Self-Healing Guardian prior to compilation
    run_self_healing_guardian()

    if not os.path.exists(ARCHIVE_FILE):
        print(f"Archive file not found at {ARCHIVE_FILE}")
        return

    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        items = json.load(f)

    # 1. Strict Self-Healing Deduplication Filter on all items before compilation
    pristine_items = []
    seen_img_keys = set()
    seen_urls = set()
    seen_titles = []

    for item in items:
        url = item.get('url', '').strip().split('?')[0].rstrip('/')
        img = item.get('image_url', '').strip()
        title = item.get('title', '').strip()
        orig_title = item.get('original_title', '').strip()

        img_key = normalize_img_key(img)
        if img_key and img_key in seen_img_keys:
            continue

        if url and url in seen_urls:
            continue

        t_key = normalize_title_key(title)
        ot_key = normalize_title_key(orig_title)
        is_dup = False
        for prev_t in seen_titles:
            if (t_key and SequenceMatcher(None, t_key, prev_t).ratio() > 0.50) or (ot_key and SequenceMatcher(None, ot_key, prev_t).ratio() > 0.50):
                is_dup = True
                break
        if is_dup:
            continue

        if img_key: seen_img_keys.add(img_key)
        if url: seen_urls.add(url)
        if t_key: seen_titles.append(t_key)
        if ot_key: seen_titles.append(ot_key)
        pristine_items.append(item)

    items = pristine_items[:140]

    # Save back pristine JSON
    with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    # Update Global Fingerprint Ledger
    ledger = {'urls': set(seen_urls), 'images': set(seen_img_keys), 'titles': set(seen_titles)}
    if os.path.exists(FINGERPRINTS_FILE):
        try:
            with open(FINGERPRINTS_FILE, 'r', encoding='utf-8') as f:
                old_f = json.load(f)
                ledger['urls'].update(old_f.get('urls', []))
                ledger['images'].update(old_f.get('images', []))
                ledger['titles'].update(old_f.get('titles', []))
        except Exception:
            pass

    with open(FINGERPRINTS_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'version': '1.0',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_unique_urls': len(ledger['urls']),
            'total_unique_images': len(ledger['images']),
            'total_unique_titles': len(ledger['titles']),
            'urls': sorted(list(ledger['urls'])),
            'images': sorted(list(ledger['images'])),
            'titles': sorted(list(ledger['titles']))
        }, f, ensure_ascii=False, indent=2)

    from datetime import timezone, timedelta
    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST)
    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    formatted_date = f"{months[now.month - 1]} {now.day}, {now.year}"
    issue_text = f"ISSUE {str(now.month).zfill(2)}.{str(now.day).zfill(2)} — DAILY CURATION"
    today_ymd = now.strftime('%Y-%m-%d')
    today_kor_stamp = f"{now.year}.{str(now.month).zfill(2)}.{str(now.day).zfill(2)} {now.strftime('%H:%M')} KST"
    cache_version = int(now.timestamp())

    # Count today's items
    today_items_count = sum(1 for it in items if it.get('collected_at', '').startswith(today_ymd))
    if today_items_count == 0:
        today_items_count = len(items)

    # 2. Update JS preloaded archives & Daily Partition JS
    os.makedirs(os.path.join(BASE_DIR, "docs", "data"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "static", "data"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "docs", "data", "daily"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "static", "data", "daily"), exist_ok=True)

    # 깊이 읽기 결과를 렌더링용 사본에 덮어씌운다 (data/*.json 원본은 그대로)
    deep_map = load_deep_reads()
    daily_notes = load_daily_notes()
    items = [apply_deep(it, deep_map) for it in items]
    print(f"Deep reads applied: {sum(1 for it in items if it.get('deep'))}/{len(items)} archive items")

    js_content = 'window.PRELOADED_ARCHIVE = ' + json.dumps(items, ensure_ascii=False) + ';'
    with open(os.path.join(BASE_DIR, "docs", "data", "daily_archive.js"), "w", encoding="utf-8") as f:
        f.write(js_content)
    with open(os.path.join(BASE_DIR, "static", "data", "daily_archive.js"), "w", encoding="utf-8") as f:
        f.write(js_content)

    # Process all daily partitions
    daily_dir = os.path.join(BASE_DIR, "data", "daily")
    manifest_file = os.path.join(BASE_DIR, "data", "manifest.json")
    
    daily_dates = sorted([f.replace('.json', '') for f in os.listdir(daily_dir) if f.endswith('.json')], reverse=True)
    if not daily_dates:
        daily_dates = [today_ymd]

    manifest = {
        "latest_date": daily_dates[0],
        "dates": daily_dates,
        "total_issues": len(daily_dates)
    }
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    manifest_js = 'window.MANIFEST_DATA = ' + json.dumps(manifest, ensure_ascii=False) + ';'
    with open(os.path.join(BASE_DIR, "docs", "data", "manifest.js"), "w", encoding="utf-8") as f:
        f.write(manifest_js)
    with open(os.path.join(BASE_DIR, "static", "data", "manifest.js"), "w", encoding="utf-8") as f:
        f.write(manifest_js)

    notes_js = 'window.DAILY_NOTES = ' + json.dumps(daily_notes, ensure_ascii=False) + ';'
    for base in ('docs', 'static'):
        with open(os.path.join(BASE_DIR, base, "data", "daily_notes.js"), "w", encoding="utf-8") as f:
            f.write(notes_js)

    for d in daily_dates:
        df_path = os.path.join(daily_dir, f"{d}.json")
        try:
            with open(df_path, "r", encoding="utf-8") as f:
                d_items = json.load(f)
            d_items = [apply_deep(x, deep_map) for x in d_items]
            clean_d = d.replace('-', '_')
            d_js = f"window.DAILY_ISSUE_{clean_d} = " + json.dumps(d_items, ensure_ascii=False) + ";"
            with open(os.path.join(BASE_DIR, "docs", "data", "daily", f"{d}.js"), "w", encoding="utf-8") as f:
                f.write(d_js)
            with open(os.path.join(BASE_DIR, "static", "data", "daily", f"{d}.js"), "w", encoding="utf-8") as f:
                f.write(d_js)
        except Exception as e:
            print(f"Error compiling daily {d}: {e}")

    # Build Issue Date Switcher HTML (Strict KST Date Matching)
    date_chips_html = []
    for d in daily_dates:
        is_active = (d == daily_dates[0])
        is_today = (d == today_ymd)
        active_cls = "active" if is_active else ""
        label = f"★ {d[5:].replace('-', '.')} 오늘" if is_today else f"{d[5:].replace('-', '.')} 호"
        chip = f'<button class="issue-date-chip {active_cls}" data-date="{d}">{label}</button>'
        date_chips_html.append(chip)
    issue_switcher_html = '\n'.join(date_chips_html)

    # 3. Compile pre-rendered cards HTML
    cards_html = []
    for idx, item in enumerate(items):
        title = html.escape(item.get('title', '아카이브 레코드'))
        snippet = html.escape(item.get('snippet', ''))
        genre = html.escape(item.get('genre', 'SPACE & ARCH'))
        collected_at = html.escape(item.get('collected_at', ''))
        image_url = item.get('image_url', '')
        url = item.get('url', '')
        
        is_today = collected_at.startswith(today_ymd)
        
        facets = item.get('facets', {})
        memory_text = html.escape(facets.get('genius_loci', facets.get('memory_narrative', '공간과 장소에 깃든 고유한 시간의 기억을 현대적 감각으로 재구성합니다.')))
        
        domain = 'archive.org'
        try:
            domain = urlparse(url).netloc.replace('www.', '')
        except Exception:
            pass

        today_badge = '<span class="kinfolk-today-badge">★ TODAY</span>' if is_today else ''
        film_badge = '<div class="film-badge"><svg viewBox="0 0 24 24" width="10" height="10" stroke="currentColor" stroke-width="2" fill="none"><polygon points="5 3 19 12 5 21 5 3"/></svg> CINEMATIC FILM</div>' if item.get('has_video') else ''

        if image_url:
            media_html = f'''
            <div class="card-media-box">
                {today_badge}
                {film_badge}
                <img src="{image_url}" alt="{title}" class="card-image" loading="lazy" onerror="this.parentElement.innerHTML='<div class=\\'simple-text-cover\\'><span class=\\'text-cover-badge\\'>{genre}</span><span class=\\'text-cover-title\\'>{title}</span></div>'">
            </div>
            '''
        else:
            media_html = f'''
            <div class="card-media-box">
                {today_badge}
                {film_badge}
                <div class="simple-text-cover">
                    <span class="text-cover-badge">{genre}</span>
                    <span class="text-cover-title">{title}</span>
                </div>
            </div>
            '''

        dp = item.get('deep') or {}
        kind_html = f'<span class="rc-kind">{html.escape(dp.get("kind", ""))}</span>' if dp.get('kind') else ''
        deep_html = render_deep_block(item)
        url_attr = html.escape(url, quote=True)
        card = f'''
        <div class="kinfolk-card-link">
            <article class="kinfolk-card{' rc-has-deep' if deep_html else ''}" data-depth="{int(dp.get('depth') or 0)}">
                <a href="{url_attr}" target="_blank" rel="noopener noreferrer" class="rc-media-link">{media_html}</a>
                <div class="card-meta-line">
                    <span class="card-genre-badge">{genre}</span>{kind_html}
                    <span class="card-date-text">{collected_at}</span>
                </div>
                <a href="{url_attr}" target="_blank" rel="noopener noreferrer" class="rc-title-link"><h3 class="card-title">{title}</h3></a>
                <p class="card-snippet">{snippet}</p>
                {deep_html}
                <div class="card-footer">
                    <span class="card-source-tag">{domain}</span>
                    <a href="{url_attr}" target="_blank" rel="noopener noreferrer" class="view-prompt">원문 보기 ↗</a>
                </div>
            </article>
        </div>
        '''
        cards_html.append(card)

    full_grid_html = '\n'.join(cards_html)
    # 6. Load Weekly Zeitgeist Report (Phase 3: free keyword-frequency + week-over-week trend engine)
    zeitgeist_file = os.path.join(BASE_DIR, "data", "zeitgeist_latest.json")
    zeitgeist_inner_html = '<span class="zeitgeist-report-tag">🧭 WEEKLY ZEITGEIST REPORT — 데이터 수집 중 (7일치 데이터가 쌓이면 자동 생성됩니다)</span>'
    if os.path.exists(zeitgeist_file):
        try:
            with open(zeitgeist_file, 'r', encoding='utf-8') as zf:
                zg = json.load(zf)
            themes = zg.get('themes', [])[:6]
            chips = []
            for theme in themes:
                trend = theme.get('trend', 'steady')
                badge = {'rising': ' 🔥', 'new': ' 🆕', 'falling': ' 📉'}.get(trend, '')
                chips.append(
                    f'<span class="zeitgeist-chip zeitgeist-chip-{trend}">'
                    f'{html.escape(theme.get("keyword", ""))} <b>{theme.get("count", 0)}</b>{badge}</span>'
                )
            chips_html = '\n                    '.join(chips) if chips else '<span class="zeitgeist-chip">데이터 수집 중</span>'

            names = zg.get('notable_names', [])
            names_html = ''
            if names:
                names_html = f'<p class="zeitgeist-report-names">주목할 이름: {html.escape(", ".join(names[:6]))}</p>'

            # Representative thumbnail: pick the top-ranked theme's first item with an image.
            thumb_html = ''
            for theme in themes:
                for thumb_item in theme.get('items', []):
                    if thumb_item.get('image_url'):
                        t_title = (deep_map.get(deep_url_key(thumb_item.get('url', ''))) or {}).get('title_ko') or thumb_item.get('title', '')
                        t_short = t_title[:44] + ('…' if len(t_title) > 44 else '')
                        thumb_html = (
                            f'<a href="{thumb_item.get("url", "#")}" target="_blank" rel="noopener noreferrer" class="zeitgeist-thumb-link">'
                            f'<img src="{thumb_item.get("image_url", "")}" class="zeitgeist-thumb" alt="{html.escape(t_title)}" loading="lazy">'
                            f'<span class="zeitgeist-thumb-caption">🔎 {html.escape(theme.get("keyword", ""))} 대표작 · {html.escape(t_short)}</span>'
                            f'</a>'
                        )
                        break
                if thumb_html:
                    break

            zeitgeist_inner_html = (
                f'<span class="zeitgeist-report-tag">🧭 이번 주 시대정신 리포트 · {html.escape(zg.get("period", ""))} · {zg.get("total_articles", 0)}건 분석</span>\n'
                f'                    <div class="zeitgeist-report-body">\n'
                f'                    <div class="zeitgeist-chip-row">\n                    {chips_html}\n                    </div>\n'
                f'                    {thumb_html}\n'
                f'                    </div>\n'
                f'                    {names_html}'
            )
        except Exception as e:
            print(f"Zeitgeist report load error: {e}")


    for target_path in [os.path.join(BASE_DIR, 'docs', 'index.html'), os.path.join(BASE_DIR, 'templates', 'index.html')]:
        if not os.path.exists(target_path):
            continue
        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()

        content = re.sub(r'<span class="meta-date" id="current-date-display">.*?</span>', f'<span class="meta-date" id="current-date-display">{formatted_date}</span>', content)
        content = re.sub(r'<span class="meta-issue" id="current-issue-text">.*?</span>', f'<span class="meta-issue" id="current-issue-text">{issue_text}</span>', content)

        sync_note = f'LATEST UPDATE: {today_kor_stamp} ({today_items_count} EDITIONS SYNCED TODAY)'
        content = re.sub(r'<span class="collection-note"[^>]*>.*?</span>', f'<span class="collection-note" style="color: #059669; font-weight: 600; letter-spacing: 0.04em;">● {sync_note}</span>', content)

        content = re.sub(r'data/daily_archive\.js\?v=\d+', f'data/daily_archive.js?v={cache_version}', content)
        content = re.sub(r'data/manifest\.js\?v=\d+', f'data/manifest.js?v={cache_version}', content)
        if 'data/daily_notes.js' not in content:
            content = content.replace('<script src="data/manifest.js', '<script src="data/daily_notes.js?v=0"></script>\n    <script src="data/manifest.js', 1)
        content = re.sub(r'data/daily_notes\.js\?v=\d+', f'data/daily_notes.js?v={cache_version}', content)

        # 오늘의 편집 노트 (가장 최신 호)
        latest_note = daily_notes.get(daily_dates[0]) if daily_dates else None
        note_html = render_daily_note(latest_note)
        note_block = f'<!-- DAILY_NOTE_START --><section id="rc-daily-note" class="rc-daily-note"{"" if note_html else " hidden"}>{note_html}</section><!-- DAILY_NOTE_END -->'
        if '<!-- DAILY_NOTE_START -->' in content:
            content = re.sub(r'<!-- DAILY_NOTE_START -->.*?<!-- DAILY_NOTE_END -->', lambda m: note_block, content, flags=re.DOTALL)
        else:
            content = content.replace('<main class="kinfolk-main">', '<main class="kinfolk-main">\n            ' + note_block, 1)
        if latest_note and latest_note.get('headline'):
            content = re.sub(r'<p class="zeitgeist-quote">.*?</p>',
                             lambda m: f'<p class="zeitgeist-quote">"{html.escape(latest_note["headline"])}"</p>',
                             content, count=1, flags=re.DOTALL)
        content = re.sub(r'static/script\.js\?v=\d+', f'static/script.js?v={cache_version}', content)
        content = re.sub(r'static/style\.css\?v=\d+', f'static/style.css?v={cache_version}', content)

        # Inject Issue Date Switcher
        if '<div class="issue-date-switcher"' in content:
            content = re.sub(r'<div class="issue-date-switcher"[^>]*>.*?</div>', f'<div class="issue-date-switcher">\n{issue_switcher_html}\n</div>', content, flags=re.DOTALL)

        pattern = r'<div id="results-container" class="kinfolk-grid">.*?</div>\s*</main>'
        replacement = f'<div id="results-container" class="kinfolk-grid">\n{full_grid_html}\n            </div>\n        </main>'
        content = re.sub(pattern, lambda m: replacement, content, flags=re.DOTALL)
        # Inject Weekly Zeitgeist Report content into the placeholder markers
        zeitgeist_pattern = r'<!-- ZEITGEIST_REPORT_START -->.*?<!-- ZEITGEIST_REPORT_END -->'
        zeitgeist_replacement = f'<!-- ZEITGEIST_REPORT_START -->\n                    {zeitgeist_inner_html}\n                    <!-- ZEITGEIST_REPORT_END -->'
        content = re.sub(zeitgeist_pattern, lambda m: zeitgeist_replacement, content, flags=re.DOTALL)

        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)

    print(f"Successfully compiled {len(items)} pristine cards for {formatted_date} with {len(daily_dates)} daily partition archives!")

if __name__ == "__main__":
    build_pages()
