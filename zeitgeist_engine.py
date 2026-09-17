import os
import re
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DAILY_DIR = os.path.join(BASE_DIR, "data", "daily")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "zeitgeist_latest.json")
HISTORY_DIR = os.path.join(BASE_DIR, "data", "zeitgeist_history")

KST = timezone(timedelta(hours=9))

# Curated bilingual keyword dictionary spanning the site's core creative genres.
# No paid API / ML model required: this is a deterministic, auditable keyword-spotting
# engine over real collected article text (title + snippet + original English title).
KEYWORD_DICTIONARY = {
    "3D 아나몰픽": ["아나몰픽", "anamorphic"],
    "미디어 파사드": ["미디어 파사드", "media facade", "led 파사드", "led facade"],
    "키네틱 조형": ["키네틱", "kinetic"],
    "프로젝션 맵핑": ["프로젝션 맵핑", "projection mapping"],
    "공간 시노그래피": ["시노그래피", "scenography"],
    "설치 미술": ["설치 미술", "installation"],
    "미니멀리즘": ["미니멀", "minimalis"],
    "콘크리트 물성": ["콘크리트", "concrete"],
    "목재 건축": ["목재", "timber", "wooden house", "wood house"],
    "패션 필름": ["패션 필름", "fashion film"],
    "아방가르드 패션": ["아방가르드", "avant-garde", "haute couture", "오뜨 꾸뛰르"],
    "런웨이·쇼": ["런웨이", "catwalk", "runway show", "fashion week"],
    "리노베이션·재생": ["리노베이션", "renovation", "adaptive reuse", "재생 건축"],
    "도시재생": ["도시재생", "urban regeneration", "urban renewal"],
    "박물관·전시": ["박물관", "전시회", "museum", "exhibition", "gallery", "갤러리"],
    "빛과 조명": ["조명", "빛의", "light art", "루미너스", "luminous"],
    "지속가능성": ["지속가능", "sustainab", "친환경", "생분해"],
    "생체모방·자연영감": ["생체모방", "biomimicry", "biomorphic", "organic form"],
    "사진": ["사진작가", "photographer", "photography"],
    "가구 디자인": ["가구", "furniture"],
    "타이포그래피": ["타이포", "typography"],
    "몰입형 경험": ["몰입형", "immersive"],
    "텍스타일·직물": ["텍스타일", "textile", "직물"],
    "해변·리조트 건축": ["해변", "리조트", "beach house", "resort"],
    "팝업·플래그십": ["팝업", "플래그십", "flagship", "pop-up"],
    "레스토랑·호스피탈리티": ["레스토랑", "restaurant design", "hospitality design", "카페 디자인"],
    "컬러·색채": ["색채", "컬러 팔레트", "color palette", "colour palette"],
    "AI·제너레이티브 아트": ["제너레이티브", "generative art", "ai 아트", "ai-generated"],
}

GENRE_LABELS_KO = {
    "SPACE & ARCH": "공간·건축",
    "MEDIA FACADE & 3D": "미디어 파사드·3D",
    "CONTEMPORARY ART": "동시대 미술",
    "AVANT-GARDE FASHION": "아방가르드 패션",
}

PROPER_NOUN_STOPWORDS = {
    "The", "This", "That", "With", "From", "For", "And", "New", "How", "Why",
    "What", "Are", "Was", "Its", "His", "Her", "Their", "Our", "You", "Your",
    "Now", "See", "Read", "Watch", "Not", "But", "All", "Can", "Has", "Have",
    "Say", "Hello", "Size", "Free", "Program", "Under", "Years", "Living",
    "Apartment", "Is", "Open", "Best", "Buy", "Dreams", "Director", "World",
    "Design", "House", "School", "Jobs", "Old", "Own", "Into", "Only", "More",
    "Most", "Than", "When", "Where", "While", "After", "Before", "Between",
    "Through", "About", "Onto", "Legend", "Life", "Portfolio", "Roster",
}


def load_recent_items(days=7, offset_days=0):
    """
    Loads items from daily partitions. offset_days=0 -> most recent `days` window.
    offset_days=N -> the `days`-sized window that ended N days ago (used to build
    a comparable "previous period" baseline for week-over-week trend detection).
    """
    if not os.path.isdir(DAILY_DIR):
        return []
    all_files = sorted(
        [f for f in os.listdir(DAILY_DIR) if f.endswith(".json")],
        reverse=True,
    )
    window = all_files[offset_days:offset_days + days]
    items = []
    for fn in window:
        try:
            with open(os.path.join(DAILY_DIR, fn), "r", encoding="utf-8") as f:
                items.extend(json.load(f))
        except Exception as e:
            print(f"[zeitgeist] skip {fn}: {e}")
    return items


def match_keywords(text):
    text_low = text.lower()
    hits = []
    for label, surface_forms in KEYWORD_DICTIONARY.items():
        for sf in surface_forms:
            if sf.lower() in text_low:
                hits.append(label)
                break
    return hits


def extract_proper_nouns(original_title):
    # Require 2-4 consecutive capitalized words: real names/places/studios
    # ("Keiji Ashizawa", "Buenos Aires Architecture Biennial") instead of single
    # generic capitalized headline words ("London", "Design", "Buy").
    phrases = re.findall(r"\b[A-Z][a-zA-Z]{1,}(?:\s+[A-Z][a-zA-Z]{1,}){1,3}\b", original_title or "")
    out = []
    for phrase in phrases:
        words = phrase.split()
        if any(w in PROPER_NOUN_STOPWORDS for w in words):
            continue
        out.append(phrase)
    return out


def count_keywords_only(items):
    """Lightweight pass used for the previous-period baseline: counts only,
    no representative items/images needed for comparison."""
    counter = Counter()
    for it in items:
        text = f"{it.get('title', '')} {it.get('snippet', '')} {it.get('original_title', '')}"
        for label in set(match_keywords(text)):
            counter[label] += 1
    return counter


def load_previous_period_counts(current_files_count):
    """
    Builds a 7-day baseline window that ends right before the current window
    started, so we can tell which keywords are genuinely rising this week
    versus just persistently common.
    """
    previous_items = load_recent_items(days=7, offset_days=current_files_count)
    if not previous_items:
        return None
    return count_keywords_only(previous_items)


def classify_trend(current_count, previous_count):
    if previous_count is None or previous_count == 0:
        return "new" if current_count >= 2 else "steady"
    if current_count >= previous_count + 2:
        return "rising"
    if current_count <= previous_count - 2:
        return "falling"
    return "steady"


def build_report():
    if not os.path.isdir(DAILY_DIR):
        return None
    daily_files = sorted([f for f in os.listdir(DAILY_DIR) if f.endswith(".json")], reverse=True)
    if not daily_files:
        return None

    current_window = min(7, len(daily_files))
    items = load_recent_items(days=current_window, offset_days=0)
    if not items:
        return None

    previous_counts = load_previous_period_counts(current_window) or {}

    keyword_counter = Counter()
    keyword_items = defaultdict(list)
    genre_counter = Counter()
    proper_noun_counter = Counter()
    seen_urls_per_kw = defaultdict(set)

    for it in items:
        text = f"{it.get('title', '')} {it.get('snippet', '')} {it.get('original_title', '')}"
        for label in set(match_keywords(text)):
            keyword_counter[label] += 1
            url = it.get("url", "")
            if url and url not in seen_urls_per_kw[label] and len(keyword_items[label]) < 4:
                seen_urls_per_kw[label].add(url)
                keyword_items[label].append(
                    {
                        "title": it.get("title", ""),
                        "url": url,
                        "image_url": it.get("image_url", ""),
                        "source_name": it.get("source_name", ""),
                    }
                )
        genre_counter[it.get("genre", "")] += 1
        for pn in extract_proper_nouns(it.get("original_title", "")):
            proper_noun_counter[pn] += 1

    themes = []
    for label, count in keyword_counter.most_common(10):
        if count < 2:
            continue
        prev = previous_counts.get(label)
        themes.append(
            {
                "keyword": label,
                "count": count,
                "previous_count": prev if prev is not None else 0,
                "trend": classify_trend(count, prev),
                "items": keyword_items[label],
            }
        )

    # Surface the most interesting themes first: rising/new signals ahead of merely-steady ones.
    trend_priority = {"rising": 0, "new": 1, "steady": 2, "falling": 3}
    themes.sort(key=lambda t: (trend_priority.get(t["trend"], 9), -t["count"]))
    themes = themes[:6]

    notable_names = [n for n, c in proper_noun_counter.most_common(12) if c >= 2]

    now = datetime.now(KST)
    period_start = now - timedelta(days=current_window)

    genre_breakdown = [
        {"genre": GENRE_LABELS_KO.get(g, g or "기타"), "count": c}
        for g, c in genre_counter.most_common()
    ]

    report = {
        "generated_at": now.strftime("%Y-%m-%d %H:%M KST"),
        "period": f"{period_start.strftime('%Y.%m.%d')} - {now.strftime('%Y.%m.%d')}",
        "total_articles": len(items),
        "genre_breakdown": genre_breakdown,
        "themes": themes,
        "notable_names": notable_names,
        "has_comparison": bool(previous_counts),
    }
    return report


def save_history_snapshot(report):
    os.makedirs(HISTORY_DIR, exist_ok=True)
    today_ymd = datetime.now(KST).strftime("%Y-%m-%d")
    snapshot_path = os.path.join(HISTORY_DIR, f"{today_ymd}.json")
    # Store a compact keyword->count map only; full items stay in zeitgeist_latest.json.
    compact = {t["keyword"]: t["count"] for t in report.get("themes", [])}
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(
            {"date": today_ymd, "period": report.get("period", ""), "keyword_counts": compact},
            f,
            ensure_ascii=False,
            indent=2,
        )


def main():
    report = build_report()
    if not report:
        print("[zeitgeist] No daily data available yet; skipping report generation.")
        return
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    save_history_snapshot(report)
    rising = [t["keyword"] for t in report["themes"] if t["trend"] in ("rising", "new")]
    print(
        f"[zeitgeist] Report generated: {len(report['themes'])} themes "
        f"from {report['total_articles']} articles over {report['period']}. "
        f"Rising/new: {rising or 'none yet'}."
    )


if __name__ == "__main__":
    main()

