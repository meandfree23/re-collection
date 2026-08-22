import json
import html
import os
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_FILE = os.path.join(BASE_DIR, "data", "daily_archive.json")

def build_pages():
    if not os.path.exists(ARCHIVE_FILE):
        print(f"Archive file not found at {ARCHIVE_FILE}")
        return

    with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
        items = json.load(f)

    now = datetime.now()
    months = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    formatted_date = f"{months[now.month - 1]} {now.day}, {now.year}"
    issue_text = f"ISSUE {str(now.month).zfill(2)}.{str(now.day).zfill(2)} — DAILY CURATION"
    cache_version = int(now.timestamp())

    # 1. Update JS preloaded archives
    os.makedirs(os.path.join(BASE_DIR, "docs", "data"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "static", "data"), exist_ok=True)
    js_content = 'window.PRELOADED_ARCHIVE = ' + json.dumps(items, ensure_ascii=False) + ';'
    with open(os.path.join(BASE_DIR, "docs", "data", "daily_archive.js"), "w", encoding="utf-8") as f:
        f.write(js_content)
    with open(os.path.join(BASE_DIR, "static", "data", "daily_archive.js"), "w", encoding="utf-8") as f:
        f.write(js_content)

    # 2. Compile pre-rendered cards HTML
    cards_html = []
    for idx, item in enumerate(items):
        title = html.escape(item.get('title', '아카이브 레코드'))
        snippet = html.escape(item.get('snippet', ''))
        genre = html.escape(item.get('genre', 'SPACE & ARCH'))
        collected_at = html.escape(item.get('collected_at', ''))
        image_url = item.get('image_url', '')
        url = item.get('url', '')
        
        facets = item.get('facets', {})
        memory_text = html.escape(facets.get('genius_loci', facets.get('memory_narrative', '공간과 장소에 깃든 고유한 시간의 기억을 현대적 감각으로 재구성합니다.')))
        
        domain = 'archive.org'
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace('www.', '')
        except Exception:
            pass

        film_badge = '<div class="film-badge"><span>FILM</span></div>' if item.get('has_video') else ''
        
        if image_url:
            media_html = f'''
            <div class="card-media-box">
                {film_badge}
                <img src="{image_url}" alt="{title}" class="card-img" loading="lazy" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                <div class="simple-text-cover" style="display: none;">
                    <span class="text-cover-badge">{genre}</span>
                    <span class="text-cover-title">{title}</span>
                </div>
            </div>
            '''
        else:
            media_html = f'''
            <div class="card-media-box">
                {film_badge}
                <div class="simple-text-cover">
                    <span class="text-cover-badge">{genre}</span>
                    <span class="text-cover-title">{title}</span>
                </div>
            </div>
            '''

        card = f'''
        <article class="kinfolk-card" data-index="{idx}" onclick="openDossier({idx})">
            {media_html}
            <div class="card-meta-line">
                <span>{genre}</span>
                <span>{collected_at}</span>
            </div>
            <h3 class="card-title">{title}</h3>
            <p class="card-snippet">{snippet}</p>
            <div class="card-memory-box">
                <span class="card-memory-label">MEMORY & EXPERIENCE ESSAY</span>
                <p class="card-memory-text">{memory_text}</p>
            </div>
            <div class="card-footer">
                <span class="card-source-tag">{domain}</span>
                <span class="view-prompt" style="font-size: 0.72rem; color: var(--text-muted); font-family: 'Plus Jakarta Sans', sans-serif;">READ DOSSIER ↗</span>
            </div>
        </article>
        '''
        cards_html.append(card)

    full_grid_html = '\n'.join(cards_html)

    for target_path in [os.path.join(BASE_DIR, 'docs', 'index.html'), os.path.join(BASE_DIR, 'templates', 'index.html')]:
        if not os.path.exists(target_path):
            continue
        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace date & issue text
        content = re.sub(r'<span class="meta-date" id="current-date-display">.*?</span>', f'<span class="meta-date" id="current-date-display">{formatted_date}</span>', content)
        content = re.sub(r'<span class="meta-issue" id="current-issue-text">.*?</span>', f'<span class="meta-issue" id="current-issue-text">{issue_text}</span>', content)

        # Replace script version cache-busting
        content = re.sub(r'data/daily_archive\.js\?v=\d+', f'data/daily_archive.js?v={cache_version}', content)
        content = re.sub(r'static/script\.js\?v=\d+', f'static/script.js?v={cache_version}', content)

        # Replace pre-rendered grid
        pattern = r'<div id="results-container" class="kinfolk-grid">.*?</div>\s*</main>'
        replacement = f'<div id="results-container" class="kinfolk-grid">\n{full_grid_html}\n            </div>\n        </main>'
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)

        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)

    print(f"Successfully compiled {len(items)} cards for {formatted_date} into HTML files!")

if __name__ == "__main__":
    build_pages()
