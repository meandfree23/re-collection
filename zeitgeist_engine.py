import os
import re
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DAILY_DIR = os.path.join(BASE_DIR, "data", "daily")
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "zeitgeist_latest.json")

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
    "리노베이션·재생": ["리노베이션", "renovation", "adaptive reuse", "재생 건축"],
    "박물관·전시": ["박물관", "전시회", "museum", "exhibition", "gallery", "갤러리"],
    "빛과 조명": ["조명", "빛의", "light art", "루미너스", "luminous"],
    "지속가능성": ["지속가능", "sustainab", "친환경", "생분해"],
    "사진": ["사진작가", "photographer", "photography"],
    "가구 디자인": ["가구", "furniture"],
    "타이포그래피": ["타이포", "typography"],
    "몰입형 경험": ["몰입형", "immersive"],
    "텍스타일·직물": ["텍스타일", "textile", "직물"],
    "해변·리조트 건축": ["해변", "리조트", "beach house", "resort"],
    "팝업·플래그십": ["팝업", "플래그십", "flagship", "pop-up"],
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
}


def load_recent_items(days=7):
    if not os.path.isdir(DAILY_DIR):
        return []
    files = sorted(
        [f for f in os.listdir(DAILY_DIR) if f.endswith(".json")],
        reverse=True,
    )[:days]
    items = []
    for fn in files:
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
    words = re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", original_title or "")
    return [w for w in words if w not in PROPER_NOUN_STOPWORDS]


def build_report():
    items = load_recent_items(7)
    if not items:
        return None

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
    for label, count in keyword_counter.most_common(8):
        if count < 2:
            continue
        themes.append({"keyword": label, "count": count, "items": keyword_items[label]})

    notable_names = [n for n, c in proper_noun_counter.most_common(12) if c >= 2]

    now = datetime.now(KST)
    period_start = now - timedelta(days=7)

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
    }
    return report


def main():
    report = build_report()
    if not report:
        print("[zeitgeist] No daily data available yet; skipping report generation.")
        return
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(
        f"[zeitgeist] Report generated: {len(report['themes'])} themes "
        f"from {report['total_articles']} articles over {report['period']}."
    )


if __name__ == "__main__":
    main()
