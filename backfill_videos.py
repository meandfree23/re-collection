"""Backfill missing video_url fields across RE:COLLECTION daily issues and archive."""

import glob
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from build_pages import playable_video_url
from video_extractor import extract_video_from_html, normalize_video_url

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DAILY_DIR = os.path.join(BASE_DIR, "data", "daily")
ARCHIVE_FILE = os.path.join(BASE_DIR, "data", "daily_archive.json")

_SKIP_SOURCES = {
    "ArchDaily",
    "Wallpaper*",
    "Architectural Digest",
    "Minimalissimo",
    "Sight Unseen",
    "Design Milk",
    "Yellowtrace",
    "The Architectural Review",
}

_THREAD_LOCAL = threading.local()


def _get_session() -> requests.Session:
    sess = getattr(_THREAD_LOCAL, "session", None)
    if sess is None:
        sess = requests.Session()
        sess.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
            }
        )
        _THREAD_LOCAL.session = sess
    return sess


def _fetch_video(url: str) -> str:
    if not url:
        return ""
    try:
        r = _get_session().get(url, timeout=6)
        if r.status_code == 200 and r.text:
            return extract_video_from_html(r.text, url)
    except Exception:
        pass
    return ""


def main():
    daily_files = sorted(glob.glob(os.path.join(DAILY_DIR, "*.json")))
    loaded = {}
    targets = {}  # url -> source_name
    normalized_existing = 0

    for fp in daily_files:
        with open(fp, "r", encoding="utf-8") as f:
            items = json.load(f)
        changed = False
        for it in items:
            raw_vu = (it.get("video_url") or "").strip()
            if raw_vu:
                norm = normalize_video_url(raw_vu)
                if norm and norm != raw_vu:
                    it["video_url"] = norm
                    it["has_video"] = True
                    normalized_existing += 1
                    changed = True
            if not playable_video_url(it):
                src = it.get("source_name") or ""
                if src not in _SKIP_SOURCES:
                    u = (it.get("url") or "").strip()
                    if u:
                        targets[u] = src
        loaded[fp] = (items, changed)

    print(f"Normalized existing video_url: {normalized_existing}")
    print(f"Scanning {len(targets)} candidate article URLs for missing videos...")

    found_map = {}
    done = 0
    with ThreadPoolExecutor(max_workers=16) as pool:
        futs = {pool.submit(_fetch_video, u): u for u in targets}
        for fut in as_completed(futs):
            u = futs[fut]
            done += 1
            vu = fut.result()
            if vu:
                found_map[u] = vu
            if done % 300 == 0 or done == len(targets):
                print(f"  Progress: {done}/{len(targets)} | newly found: {len(found_map)}")

    updated_files = 0
    updated_items = 0
    by_source = {}
    for fp, (items, changed) in loaded.items():
        for it in items:
            u = (it.get("url") or "").strip()
            if u in found_map and not playable_video_url(it):
                it["video_url"] = found_map[u]
                it["has_video"] = True
                changed = True
                updated_items += 1
                src = it.get("source_name") or "unknown"
                by_source[src] = by_source.get(src, 0) + 1
        if changed:
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
            updated_files += 1

    # Sync daily_archive.json
    if os.path.exists(ARCHIVE_FILE):
        with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
            arch = json.load(f)
        arch_changed = False
        for it in arch:
            u = (it.get("url") or "").strip()
            if u in found_map and not playable_video_url(it):
                it["video_url"] = found_map[u]
                it["has_video"] = True
                arch_changed = True
        if arch_changed:
            with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
                json.dump(arch, f, ensure_ascii=False, indent=2)

    print(f"\nDone! Updated {updated_items} items across {updated_files} daily files.")
    for src, cnt in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"  +{cnt:3d} {src}")


if __name__ == "__main__":
    main()
