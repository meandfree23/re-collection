"""
RE:COLLECTION Automated Health & Condition Maintenance Guard

Verifies daily partition freshness, deep-read coverage, genre balance,
cross-day uniqueness, and static output integrity after every build.
"""
import collections
import glob
import json
import os
from datetime import datetime, timedelta, timezone

import build_pages as bp
import deep_reader as dr

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DAILY_DIR = os.path.join(DATA_DIR, "daily")
DOCS_DIR = os.path.join(BASE_DIR, "docs")
HEALTH_FILE = os.path.join(DATA_DIR, "health_status.json")
KST = timezone(timedelta(hours=9))


def run_health_check():
    now = datetime.now(KST)
    deep = bp.load_json(bp.DEEP_FILE, {})
    notes = bp.load_json(bp.NOTES_FILE, {})
    files = sorted(glob.glob(os.path.join(DAILY_DIR, "*.json")), reverse=True)

    recent_rows = []
    genre_7d = collections.Counter()
    seen_urls = set()
    dup_urls = 0
    total_7d = 0
    pending_7d = 0

    for fp in files[:7]:
        ymd = os.path.basename(fp)[:-5]
        items = bp.load_json(fp, [])
        ready = 0
        for x in items:
            u = (x.get("url") or "").strip().split("?")[0].rstrip("/")
            if u:
                if u in seen_urls:
                    dup_urls += 1
                seen_urls.add(u)
            ap = bp.apply_deep(x, deep)
            genre_7d[ap.get("genre", "UNKNOWN")] += 1
            if ap.get("deep"):
                ready += 1
            else:
                pending_7d += 1
        total_7d += len(items)
        recent_rows.append({
            "date": ymd,
            "total": len(items),
            "ready": ready,
            "pending": len(items) - ready,
            "has_note": ymd in notes,
        })

    required_artifacts = [
        os.path.join(DOCS_DIR, "index.html"),
        os.path.join(DOCS_DIR, "static", "script.js"),
        os.path.join(DOCS_DIR, "static", "style.css"),
        os.path.join(DOCS_DIR, "data", "manifest.js"),
        os.path.join(DOCS_DIR, "data", "daily_notes.js"),
        os.path.join(DOCS_DIR, "data", "search_index.js"),
    ]
    missing_artifacts = [os.path.relpath(p, BASE_DIR) for p in required_artifacts if not os.path.exists(p) or os.path.getsize(p) == 0]

    warnings = []
    if dup_urls > 0:
        warnings.append(f"Cross-day duplicate URLs in last 7 days: {dup_urls}")
    if total_7d > 0 and (pending_7d / total_7d) > 0.15:
        warnings.append(f"High pending deep-read ratio in last 7 days: {pending_7d}/{total_7d}")
    for g in ("SPACE & ARCH", "CONTEMPORARY ART", "MEDIA FACADE & 3D", "AVANT-GARDE FASHION"):
        if genre_7d[g] == 0:
            warnings.append(f"Zero items in genre {g} over last 7 days")
    if missing_artifacts:
        warnings.append(f"Missing/empty static artifacts: {missing_artifacts}")

    status = {
        "checked_at": now.strftime("%Y-%m-%d %H:%M:%S KST"),
        "healthy": len(warnings) == 0,
        "warnings": warnings,
        "last_7_days": {
            "total_items": total_7d,
            "pending_deep_reads": pending_7d,
            "duplicate_urls": dup_urls,
            "genre_breakdown": dict(genre_7d),
            "issues": recent_rows,
        },
        "total_deep_reads_cached": len(deep),
        "total_issue_files": len(files),
    }

    with open(HEALTH_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

    print("=================================================================")
    print(f"🩺 RE:COLLECTION HEALTH CHECK ({status['checked_at']})")
    print(f"Status: {'HEALTHY ✅' if status['healthy'] else 'WARNINGS ⚠️'}")
    print(f"Last 7d: {total_7d} items | Pending: {pending_7d} | Dups: {dup_urls}")
    print(f"Genres 7d: {dict(genre_7d)}")
    if warnings:
        for w in warnings:
            print(f"  ⚠️ {w}")
    print("=================================================================")
    return status


if __name__ == "__main__":
    run_health_check()
