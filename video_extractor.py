"""Shared video URL normalization and extraction for RE:COLLECTION."""

import json
import re
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

_SKIP_IFRAME_HOSTS = (
    "googletagmanager.com",
    "doubleclick.net",
    "googlesyndication.com",
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "open.spotify.com",
    "w.soundcloud.com",
    "embed.podcasts.apple.com",
    "bandcamp.com",
    "tiktok.com",
)

_PROMO_VIDEO_HINTS = (
    "subscribe",
    "newsletter",
    "banner",
    "logo",
    "promo",
    "advert",
    "jennifer-latour-imaginary-creatures",
    "cromawaltz-moire-sculpture-paris-grriz",
)


def normalize_video_url(raw_url: str) -> str:
    """Normalize Vimeo, YouTube, Brightcove, or direct MP4/WebM URLs to playable embed URLs."""
    u = (raw_url or "").strip()
    if not u or u.startswith("data:") or u.startswith("blob:"):
        return ""
    u = u.replace("\\/", "/")
    if u.startswith("//"):
        u = "https:" + u
    if not u.startswith(("http://", "https://")):
        return ""

    low = u.lower()
    if any(h in low for h in _SKIP_IFRAME_HOSTS):
        return ""

    parsed = urlparse(u)
    host = parsed.netloc.lower()
    path = parsed.path

    # Brightcove player iframe
    if "players.brightcove.net" in host and "videoId=" in u:
        return u

    # Vimeo
    if "vimeo.com" in host:
        m = re.search(r"/(?:video/)?(\d{6,12})", path)
        if m:
            vid = m.group(1)
            qs = parse_qs(parsed.query)
            h_param = qs.get("h", [None])[0]
            base = f"https://player.vimeo.com/video/{vid}"
            return f"{base}?h={h_param}" if h_param else base
        return ""

    # YouTube
    if "youtube.com" in host or "youtube-nocookie.com" in host or "youtu.be" in host:
        vid = ""
        if "youtu.be" in host:
            m = re.match(r"^/([A-Za-z0-9_-]{11})", path)
            if m:
                vid = m.group(1)
        elif "/embed/" in path:
            m = re.search(r"/embed/([A-Za-z0-9_-]{11})", path)
            if m:
                vid = m.group(1)
        elif "/shorts/" in path:
            m = re.search(r"/shorts/([A-Za-z0-9_-]{11})", path)
            if m:
                vid = m.group(1)
        else:
            qs = parse_qs(parsed.query)
            cand = qs.get("v", [""])[0]
            if re.match(r"^[A-Za-z0-9_-]{11}$", cand):
                vid = cand
        if vid:
            return f"https://www.youtube.com/embed/{vid}"
        return ""

    # Direct MP4 / WebM
    clean_path = low.split("?")[0]
    if clean_path.endswith(".mp4") or clean_path.endswith(".webm"):
        if any(h in low for h in _PROMO_VIDEO_HINTS):
            return ""
        return u

    return ""


def _pick_main_container(soup: BeautifulSoup):
    for sel in (
        "article",
        "main",
        ".entry-content",
        ".post-content",
        ".article-body",
        ".article__body",
        ".post-body",
        ".td-post-content",
    ):
        el = soup.select_one(sel)
        if el:
            return el
    return soup


def _clean_container_copy(container):
    """Return a copy or tag list excluding sidebars/footers/navs when scanning <video> tags."""
    # Avoid mutating original soup by filtering ancestors on matched tags
    def _in_chrome(tag) -> bool:
        for parent in tag.parents:
            name = getattr(parent, "name", "")
            if name in ("header", "footer", "nav", "aside"):
                return True
            cls = " ".join(parent.get("class") or []).lower()
            if any(k in cls for k in ("sidebar", "related", "recommended", "newsletter", "footer", "header-")):
                return True
        return False

    return _in_chrome


def extract_video_from_html(html: str, page_url: str = "") -> str:
    """Extract the primary playable video embed/file URL from an article's HTML."""
    if not html:
        return ""

    soup = BeautifulSoup(html, "html.parser")

    # 1. Brightcove <video-js> (e.g. NOWNESS)
    for vjs in soup.find_all("video-js"):
        acct = (vjs.get("data-account") or "").strip()
        vid = (vjs.get("data-video-id") or "").strip()
        if acct and vid:
            player = (vjs.get("data-player") or "default").strip() or "default"
            embed = (vjs.get("data-embed") or "default").strip() or "default"
            return f"https://players.brightcove.net/{acct}/{player}_{embed}/index.html?videoId={vid}"

    # 2. All <iframe> elements (never stop at GTM/ad/podcast iframes)
    for iframe in soup.find_all("iframe"):
        for attr in ("src", "data-src", "data-lazy-src", "data-litespeed-src"):
            raw = iframe.get(attr)
            if raw:
                norm = normalize_video_url(urljoin(page_url, raw) if page_url else raw)
                if norm:
                    return norm

    # 3. <lite-youtube> and data-vimeo-id / data-youtube-id attributes
    lite_yt = soup.find("lite-youtube")
    if lite_yt and lite_yt.get("videoid"):
        norm = normalize_video_url(f"https://www.youtube.com/embed/{lite_yt['videoid'].strip()}")
        if norm:
            return norm

    for tag in soup.find_all(attrs={"data-vimeo-id": True}):
        vid = str(tag.get("data-vimeo-id") or "").strip()
        if re.match(r"^\d{6,12}$", vid):
            return f"https://player.vimeo.com/video/{vid}"

    for tag in soup.find_all(attrs={"data-youtube-id": True}):
        vid = str(tag.get("data-youtube-id") or "").strip()
        if re.match(r"^[A-Za-z0-9_-]{11}$", vid):
            return f"https://www.youtube.com/embed/{vid}"

    # 4. JSON-LD VideoObject embedUrl / contentUrl
    for sc in soup.find_all("script", type="application/ld+json"):
        txt = sc.string or ""
        if not txt:
            continue
        try:
            obj = json.loads(txt)
        except Exception:
            continue
        stack = [obj]
        while stack:
            cur = stack.pop()
            if isinstance(cur, dict):
                for key in ("embedUrl", "contentUrl"):
                    val = cur.get(key)
                    if isinstance(val, str):
                        norm = normalize_video_url(val)
                        if norm:
                            return norm
                for v in cur.values():
                    if isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(cur, list):
                stack.extend(cur)

    # 5. OpenGraph video meta tags
    for prop in ("og:video:secure_url", "og:video:url", "og:video"):
        meta = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if meta and meta.get("content"):
            norm = normalize_video_url(meta["content"])
            if norm:
                return norm

    # 6. <video> / <source> inside main article container (skipping sidebars/footers)
    main_box = _pick_main_container(soup)
    in_chrome = _clean_container_copy(main_box)
    for vid_tag in main_box.find_all("video"):
        if in_chrome(vid_tag):
            continue
        candidates = [vid_tag.get("src"), vid_tag.get("data-src")]
        for src_tag in vid_tag.find_all("source"):
            candidates.append(src_tag.get("src"))
            candidates.append(src_tag.get("data-src"))
        for raw in candidates:
            if raw:
                norm = normalize_video_url(urljoin(page_url, raw) if page_url else raw)
                if norm:
                    return norm

    # 7. Escaped/inline embed URLs in main HTML
    cleaned_html = html.replace("\\/", "/")
    m_vm = re.search(r"https?://player\.vimeo\.com/video/(\d{6,12})(?:\?h=([A-Za-z0-9]+))?", cleaned_html)
    if m_vm:
        vid, h_p = m_vm.group(1), m_vm.group(2)
        return f"https://player.vimeo.com/video/{vid}?h={h_p}" if h_p else f"https://player.vimeo.com/video/{vid}"

    m_yt = re.search(r"https?://(?:www\.)?youtube(?:-nocookie)?\.com/embed/([A-Za-z0-9_-]{11})", cleaned_html)
    if m_yt:
        return f"https://www.youtube.com/embed/{m_yt.group(1)}"

    return ""
