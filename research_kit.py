"""
RE:COLLECTION 리서치 도구 (표준 라이브러리만, 무료)

deep_reader.py가 기사 한 건을 '깊이 읽기' 전에 쓰는 자료 수집 도구.
  1. fetch_page      : 원문 본문 + JSON-LD articleBody + 본문 속 외부 링크 수집
  2. candidate_links : 본문 링크 중 작가·스튜디오·기관 공식 페이지 후보만 추리기
  3. wiki_intro      : 위키백과(영/한) 도입부 요약 (무료 공개 API)
  4. archive_matches : RE:COLLECTION 과거 기사 중 같은 인물·작업을 다룬 글 찾기

웹 검색 엔진(Bing/DDG)은 봇 차단·엉뚱한 결과 때문에 쓰지 않는다.
모델의 '기억'도 자료로 쓰지 않는다(지어내기 방지). 실제로 가져온 텍스트만 자료가 된다.
"""
import re
import json
from html.parser import HTMLParser
from urllib import request, parse

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")
WIKI_UA = "RE-COLLECTION-research/1.0 (https://meandfree23.github.io/re-collection/)"

BOILER = re.compile(
    r"(newsletter|subscribe|sign up|inbox|cookie|all rights reserved|advertis|"
    r"follow us|share this|related stories|read more|click here|terms of use|"
    r"privacy policy|받은 편지함|뉴스레터|구독)", re.I)

SKIP_LINK_HOSTS = re.compile(
    r"(instagram|facebook|twitter|x\.com|pinterest|linkedin|tiktok|threads\.net|youtube|youtu\.be|vimeo|"
    r"amazon\.|ebay\.|etsy\.|apple\.com/app|play\.google|google\.|bit\.ly|mailchi|substack\.com/subscribe|"
    r"doubleclick|adsttc|disqus|wa\.me|t\.me|spotify|soundcloud|flickr|tumblr|patreon|shop\.|store\.|"
    r"condenast|futureplc|cdn\.|wp-content|\.jpg|\.png|\.pdf)", re.I)


class PageParser(HTMLParser):
    SKIP = {"script", "style", "noscript", "nav", "footer", "aside", "form", "header", "svg", "button", "figure"}
    BLOCK = {"p", "h2", "h3", "li", "blockquote"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.cur = None
        self.blocks = []
        self.meta = {}
        self.ld = []
        self._ld_buf = None
        self.links = []
        self._a = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            k = (a.get("property") or a.get("name") or "").lower()
            if k in ("og:description", "description", "og:title", "og:site_name") and a.get("content"):
                self.meta.setdefault(k, a.get("content"))
            return
        if tag == "script" and "ld+json" in (a.get("type") or ""):
            self._ld_buf = []
            self.skip_depth += 1
            return
        if tag in self.SKIP:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in self.BLOCK:
            self.cur = [tag, []]
        if tag == "a" and self.cur is not None and a.get("href"):
            self._a = [a.get("href"), []]

    def handle_endtag(self, tag):
        if tag == "script" and self._ld_buf is not None:
            self.ld.append("".join(self._ld_buf))
            self._ld_buf = None
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if tag in self.SKIP and self.skip_depth > 0:
            self.skip_depth -= 1
            return
        if tag == "a" and self._a is not None:
            txt = re.sub(r"\s+", " ", "".join(self._a[1])).strip()
            self.links.append((self._a[0], txt))
            self._a = None
        if self.cur is not None and tag == self.cur[0]:
            text = re.sub(r"\s+", " ", "".join(self.cur[1])).strip()
            if text:
                self.blocks.append((tag, text))
            self.cur = None

    def handle_data(self, data):
        if self._ld_buf is not None:
            self._ld_buf.append(data)
            return
        if self.skip_depth == 0 and self.cur is not None:
            self.cur[1].append(data)
            if self._a is not None:
                self._a[1].append(data)


def _get(url, timeout=20, ua=UA, maxbytes=2_500_000):
    req = request.Request(url, headers={"User-Agent": ua, "Accept-Language": "en,ko;q=0.8"})
    with request.urlopen(req, timeout=timeout) as r:
        raw = r.read(maxbytes)
        charset = r.headers.get_content_charset() or "utf-8"
        final = r.geturl()
    return raw.decode(charset, errors="replace"), final


def _ld_body(ld_list):
    best = ""
    for raw in ld_list:
        try:
            data = json.loads(raw.strip())
        except Exception:
            continue
        stack = [data]
        while stack:
            x = stack.pop()
            if isinstance(x, list):
                stack.extend(x)
            elif isinstance(x, dict):
                for k in ("articleBody", "text"):
                    v = x.get(k)
                    if isinstance(v, str) and len(v) > len(best):
                        best = v
                if "@graph" in x:
                    stack.append(x["@graph"])
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", best)).strip()


def fetch_page(url, limit=9000):
    """반환: (본문 텍스트, meta dict, [(절대URL, 앵커텍스트)], 상태)"""
    try:
        doc, final = _get(url)
    except Exception as e:
        return "", {}, [], f"fetch_error:{type(e).__name__}"
    p = PageParser()
    try:
        p.feed(doc)
    except Exception:
        pass
    parts, total = [], 0
    for tag, t in p.blocks:
        if tag == "p" and len(t) < 45:
            continue
        if tag != "p" and len(t) < 12:
            continue
        if BOILER.search(t) and len(t) < 260:
            continue
        line = t if tag == "p" else f"[{tag}] {t}"
        parts.append(line)
        total += len(line)
        if total > limit:
            break
    body = "\n".join(parts)
    ld = _ld_body(p.ld)
    # JSON-LD 본문이 훨씬 길면(지연 로딩·페이월 사이트) 그것을 쓴다
    if len(ld) > len(body) * 1.3 and len(ld) > 400:
        body = ld
    links = []
    for href, txt in p.links:
        try:
            absu = parse.urljoin(final, href)
        except Exception:
            continue
        if absu.startswith("http"):
            links.append((absu.split("#")[0], txt))
    return body[:limit], p.meta, links, "ok"


def _host(u):
    try:
        h = parse.urlparse(u).netloc.lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def _root(h):
    parts = h.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else h


def candidate_links(article_url, links, max_n=30):
    """기사 본문 속 외부 링크 중 1차 자료 후보(작가·스튜디오·기관 페이지)만."""
    src_root = _root(_host(article_url))
    seen, out = set(), []
    for u, txt in links:
        h = _host(u)
        if not h or _root(h) == src_root:
            continue
        if SKIP_LINK_HOSTS.search(u):
            continue
        key = u.rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        out.append({"url": u, "text": (txt or "")[:80], "host": h})
        if len(out) >= max_n:
            break
    return out


def wiki_intro(query, lang="en", max_chars=1400):
    """위키백과 검색 1위 문서의 도입부. 반환 dict 또는 None."""
    if not query or len(query) < 3:
        return None
    try:
        q = parse.quote(query)
        s, _ = _get(f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}"
                    f"&srlimit=1&format=json", timeout=12, ua=WIKI_UA, maxbytes=300_000)
        hits = json.loads(s).get("query", {}).get("search", [])
        if not hits:
            return None
        title = hits[0]["title"]
        stop = {"the", "and", "studio", "studios", "design", "architects", "museum", "gallery", "foundation"}
        qt = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) >= 4 and w not in stop]
        tt = title.lower()
        if qt and not all(w in tt for w in qt):
            return None  # 검색 1위가 엉뚱한 문서면 버린다
        t = parse.quote(title)
        s2, _ = _get(f"https://{lang}.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=1"
                     f"&explaintext=1&redirects=1&titles={t}&format=json", timeout=12, ua=WIKI_UA, maxbytes=600_000)
        pages = json.loads(s2).get("query", {}).get("pages", {})
        for pg in pages.values():
            ext = re.sub(r"\s+", " ", pg.get("extract", "") or "").strip()
            if len(ext) < 80 or "may refer to" in ext[:200]:
                return None
            return {"title": title, "url": f"https://{lang}.wikipedia.org/wiki/{t}", "text": ext[:max_chars]}
    except Exception:
        return None
    return None


def archive_matches(entities, cache, self_key, key_fn, max_n=3):
    """RE:COLLECTION 캐시에서 같은 인물·작업을 다룬 다른 기사."""
    names = [e for e in entities if isinstance(e, str) and len(e) >= 5]
    if not names:
        return []
    out = []
    for k, v in cache.items():
        if k == self_key or not isinstance(v, dict):
            continue
        hay = " ".join([v.get("original_title", ""), v.get("title_ko", ""), v.get("summary_ko", ""),
                        " ".join((v.get("research") or {}).get("entities", []))]).lower()
        hit = [n for n in names if n.lower() in hay]
        if hit:
            out.append({"title": v.get("title_ko", ""), "url": v.get("url", ""), "summary": v.get("summary_ko", ""),
                        "lens": v.get("lens", ""), "match": hit[0], "date": v.get("read_at", "")[:10]})
        if len(out) >= max_n:
            break
    return out
