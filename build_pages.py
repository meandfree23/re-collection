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

    for d in daily_dates:
        df_path = os.path.join(daily_dir, f"{d}.json")
        try:
            with open(df_path, "r", encoding="utf-8") as f:
                d_items = json.load(f)
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

        card = f'''
        <a href="{url}" target="_blank" rel="noopener noreferrer" class="kinfolk-card-link">
            <article class="kinfolk-card">
                {media_html}
                <div class="card-meta-line">
                    <span class="card-genre-badge">{genre}</span>
                    <span class="card-date-text">{collected_at}</span>
                </div>
                <h3 class="card-title">{title}</h3>
                <p class="card-snippet">{snippet}</p>
                <div class="card-footer">
                    <span class="card-source-tag">{domain}</span>
                    <span class="view-prompt">VIEW ORIGINAL ↗</span>
                </div>
            </article>
        </a>
        '''
        cards_html.append(card)

    full_grid_html = '\n'.join(cards_html)

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
        content = re.sub(r'static/script\.js\?v=\d+', f'static/script.js?v={cache_version}', content)

        # Inject Issue Date Switcher
        if '<div class="issue-date-switcher"' in content:
            content = re.sub(r'<div class="issue-date-switcher"[^>]*>.*?</div>', f'<div class="issue-date-switcher">\n{issue_switcher_html}\n</div>', content, flags=re.DOTALL)

        pattern = r'<div id="results-container" class="kinfolk-grid">.*?</div>\s*</main>'
        replacement = f'<div id="results-container" class="kinfolk-grid">\n{full_grid_html}\n            </div>\n        </main>'
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)

        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)

    print(f"Successfully compiled {len(items)} pristine cards for {formatted_date} with {len(daily_dates)} daily partition archives!")

if __name__ == "__main__":
    build_pages()
