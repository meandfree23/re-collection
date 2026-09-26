"""
RE:COLLECTION Deep Reader (free Gemini flash-lite tier, stdlib only)

각 항목의 원문을 실제로 읽고 다음을 만든다.
  - title_ko   : 뜻이 살아있는 한국어 헤드라인
  - summary_ko : 원문 사실에 근거한 한국어 설명 2~3문장
  - lens / why_now / mechanism / sensory / transfer : 큐레이터 인사이트
  - keywords, evidence(원문 인용), kind, depth, grounding
그리고 날짜별로 그날 읽은 항목들을 엮은 '오늘의 편집 노트'를 만든다.

결과는 data/deep_reads.json(항목별, URL 키), data/daily_notes.json(날짜별)에
캐시되며, build_pages.py가 렌더링 시점에 덮어씌운다. 원본 수집 데이터(data/daily/*.json)는
건드리지 않으므로 self_heal_guardian의 중복제거 로직에 영향을 주지 않는다.

환경변수
  GEMINI_API_KEY        (필수, 쉼표로 여러 개 가능)
  DEEP_MAX_ITEMS        한 번 실행에서 새로 읽을 최대 항목 수 (기본 60)
  DEEP_TIME_BUDGET      초 단위 시간 예산 (기본 1500)
  DEEP_CONCURRENCY      동시 요청 수 (기본 4)
  DEEP_MAX_NOTES        한 번 실행에서 만들 최대 날짜 노트 수 (기본 6)
  DEEP_ONLY_DATES       쉼표 구분 날짜만 처리 (테스트용)
"""
import os
import re
import json
import time
import glob
import html
import random
import threading
from html.parser import HTMLParser
from urllib import request, error
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DAILY_DIR = os.path.join(DATA_DIR, "daily")
ARCHIVE_FILE = os.path.join(DATA_DIR, "daily_archive.json")
CACHE_FILE = os.path.join(DATA_DIR, "deep_reads.json")
NOTES_FILE = os.path.join(DATA_DIR, "daily_notes.json")

KST = timezone(timedelta(hours=9))
VERSION = 1
MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.1-flash-lite-preview"]
MODEL_MIN_INTERVAL = 4.3  # 15 RPM 무료 한도 안쪽

MAX_ITEMS = int(os.environ.get("DEEP_MAX_ITEMS", "60"))
TIME_BUDGET = int(os.environ.get("DEEP_TIME_BUDGET", "1500"))
CONCURRENCY = int(os.environ.get("DEEP_CONCURRENCY", "4"))
MAX_NOTES = int(os.environ.get("DEEP_MAX_NOTES", "6"))
ONLY_DATES = [d.strip() for d in os.environ.get("DEEP_ONLY_DATES", "").split(",") if d.strip()]
KEYS = [k.strip() for k in os.environ.get("GEMINI_API_KEY", "").split(",") if k.strip()]

START = time.time()
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")


def log(*a):
    print("[deep]", *a, flush=True)


def time_left():
    return TIME_BUDGET - (time.time() - START)


def url_key(u):
    if not u:
        return ""
    try:
        p = urlparse(u.strip())
        path = p.path.rstrip("/")
        return f"{p.netloc.lower().replace('www.', '')}{path}"
    except Exception:
        return u.strip().split("?")[0].rstrip("/")


def hangul_ratio(s):
    s = s or ""
    letters = re.findall(r"[A-Za-z\uac00-\ud7a3]", s)
    if not letters:
        return 0.0
    return len(re.findall(r"[\uac00-\ud7a3]", s)) / len(letters)


# ---------------------------------------------------------------------------
# 1. 원문 읽기 (표준 라이브러리 HTML 파서)
# ---------------------------------------------------------------------------
BOILER = re.compile(
    r"(newsletter|subscribe|sign up|inbox|cookie|all rights reserved|advertis|"
    r"follow us|share this|related stories|read more|click here|terms of use|"
    r"privacy policy|받은 편지함|뉴스레터|구독)", re.I)


class ArticleParser(HTMLParser):
    SKIP = {"script", "style", "noscript", "nav", "footer", "aside", "form", "header", "svg", "button", "figure"}
    BLOCK = {"p", "h2", "h3", "li", "blockquote"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip_depth = 0
        self.cur = None
        self.blocks = []
        self.meta = {}

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            a = dict(attrs)
            k = (a.get("property") or a.get("name") or "").lower()
            if k in ("og:description", "description", "og:title") and a.get("content"):
                self.meta.setdefault(k, a.get("content"))
            return
        if tag in self.SKIP:
            self.skip_depth += 1
            return
        if self.skip_depth == 0 and tag in self.BLOCK:
            self.cur = [tag, []]

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip_depth > 0:
            self.skip_depth -= 1
            return
        if self.cur is not None and tag == self.cur[0]:
            text = re.sub(r"\s+", " ", "".join(self.cur[1])).strip()
            if text:
                self.blocks.append((tag, text))
            self.cur = None

    def handle_data(self, data):
        if self.skip_depth == 0 and self.cur is not None:
            self.cur[1].append(data)


def fetch_article(url, limit=7000):
    try:
        req = request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en,ko;q=0.8"})
        with request.urlopen(req, timeout=20) as r:
            raw = r.read(2_500_000)
            charset = r.headers.get_content_charset() or "utf-8"
        doc = raw.decode(charset, errors="replace")
    except Exception as e:
        return "", {}, f"fetch_error:{type(e).__name__}"
    p = ArticleParser()
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
    return "\n".join(parts)[:limit], p.meta, "ok"


# ---------------------------------------------------------------------------
# 2. Gemini 호출 (무료 flash-lite 3종 회전 + 키 회전)
# ---------------------------------------------------------------------------
class Pool:
    def __init__(self):
        self.lock = threading.Lock()
        self.slots = [{"key": k, "model": m, "next": 0.0, "dead": False} for k in KEYS for m in MODELS]
        random.shuffle(self.slots)
        self.calls = 0

    def acquire(self, avoid=None):
        while True:
            with self.lock:
                live = [s for s in self.slots if not s["dead"] and s is not avoid]
                if not live:
                    live = [s for s in self.slots if not s["dead"]]
                if not live:
                    return None
                now = time.time()
                s = min(live, key=lambda x: x["next"])
                wait = s["next"] - now
                if wait <= 0:
                    s["next"] = now + MODEL_MIN_INTERVAL
                    self.calls += 1
                    return s
            time.sleep(min(max(wait, 0.2), 5))

    def penalize(self, slot, seconds=None, dead=False):
        with self.lock:
            if dead:
                slot["dead"] = True
            else:
                slot["next"] = max(slot["next"], time.time() + (seconds or 60))


POOL = None


def gemini_json(system, user, schema, temperature=0.55, tries=4):
    last = None
    avoid = None
    for attempt in range(tries):
        if time_left() < 20:
            raise TimeoutError("time budget exhausted")
        slot = POOL.acquire(avoid)
        if slot is None:
            raise RuntimeError("all model slots exhausted for today")
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
                "responseSchema": schema,
            },
        }
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/{slot['model']}:generateContent"
               f"?key={slot['key']}")
        req = request.Request(url, data=json.dumps(body).encode("utf-8"),
                              headers={"Content-Type": "application/json"}, method="POST")
        try:
            with request.urlopen(req, timeout=90) as r:
                data = json.loads(r.read().decode("utf-8"))
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            return json.loads(text), slot["model"]
        except error.HTTPError as e:
            msg = ""
            try:
                msg = e.read().decode("utf-8", "replace")
            except Exception:
                pass
            last = f"HTTP {e.code} {slot['model']}"
            if e.code == 429:
                if "PerDay" in msg or "per_day" in msg.lower():
                    POOL.penalize(slot, dead=True)
                    log("daily quota exhausted:", slot["model"])
                else:
                    m = re.search(r'"retryDelay":\s*"(\d+)', msg)
                    POOL.penalize(slot, int(m.group(1)) + 2 if m else 60)
            elif e.code == 404:
                POOL.penalize(slot, dead=True)
            elif e.code in (500, 502, 503, 504):
                POOL.penalize(slot, 20)
            else:
                POOL.penalize(slot, 30)
            avoid = slot
        except (ValueError, KeyError, IndexError) as e:
            last = f"parse {type(e).__name__} {slot['model']}"
            avoid = slot
        except Exception as e:
            last = f"{type(e).__name__} {slot['model']}"
            POOL.penalize(slot, 15)
            avoid = slot
    raise RuntimeError(last or "gemini failed")


# ---------------------------------------------------------------------------
# 3. 프롬프트
# ---------------------------------------------------------------------------
ITEM_SYSTEM = """당신은 한국어 데일리 저널 RE:COLLECTION의 수석 큐레이터입니다.
다루는 영역: 공간·건축, 동시대 미술, 미디어 아트·모션, 아방가르드 패션.
독자: 광고·영상 감독, 크리에이티브 디렉터, 공간 디자이너. 이들은 '무엇이 새로운가'와 '어떻게 작동하는가'를 원합니다.

반드시 지킬 것
1. 사실은 제공된 원문과 RSS 요약에서만 가져옵니다. 원문에 없는 수치·이름·연도·장소를 만들지 않습니다.
2. 모든 출력은 자연스러운 한국어입니다. 번역투(‘~하는 것이다’, ‘~를 통해’ 남발, ‘~에 있어서’) 금지. 영어 문장을 그대로 두지 않습니다.
   고유명사는 한국어로 적고, 처음 등장할 때만 괄호로 원어를 붙입니다. 예: 장 누벨(Jean Nouvel)
3. 상투어 금지: ‘새로운 영감’, ‘공감각적 경험’, ‘경계를 허문다’, ‘시대정신을 투영’, ‘압도적 몰입감’, ‘깊은 울림’, ‘새로운 지평’.
   대신 구체적인 재료·치수·기법·빛·동선·사람의 행동으로 말합니다.
4. 인사이트는 원문 사실에서 한 걸음 더 나간 해석입니다. 해석마다 근거가 되는 사실을 문장 안에 함께 붙입니다.
5. 원문이 얇거나(뉴스레터 묶음, 목록형, 보도자료, 광고성) 내용 확인이 어려우면 grounding을 'thin'으로 두고 인사이트를 짧고 신중하게 씁니다. 모르는 것은 추측하지 않습니다.
6. 문장은 짧고 단단하게. 한 문장에 하나의 생각.
7. 문체는 모든 필드에서 '~다'로 끝나는 평서체로 통일합니다. '~합니다', '~해야 합니다', '~할 수 있습니다' 금지.
8. lens는 지시문('확인해야 한다', '주목하라')이 아니라 관찰과 해석이 담긴 단언입니다.
   좋은 예: '종이를 강철처럼, 강철을 종이처럼 다뤄 두 재료의 무게감을 맞바꾼다.'
   나쁜 예: '재료의 경계를 허무는 새로운 시도에 주목해야 한다.'
9. transfer는 감독이 내일 콘티에 바로 쓸 수 있을 만큼 구체적으로: 무엇을, 어떤 샷/조명/재료/동선으로."""

ITEM_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title_ko": {"type": "STRING", "description": "원제의 뜻과 핵심이 살아있는 한국어 헤드라인, 18~42자. 직역 금지."},
        "summary_ko": {"type": "STRING", "description": "무엇을·누가·어디서·어떻게를 담은 사실 설명 2~3문장, 110~220자."},
        "lens": {"type": "STRING", "description": "큐레이터의 시선: 이것을 왜 봐야 하는지 한 문장, 35~75자. 구체적이고 날카롭게."},
        "why_now": {"type": "STRING", "description": "왜 지금인가: 동시대 흐름 속 의미 1~2문장."},
        "mechanism": {"type": "STRING", "description": "작동 방식: 재료·빛·구조·동선·편집 등 구체 장치가 어떻게 효과를 만드는지 1~2문장."},
        "sensory": {"type": "STRING", "description": "감각과 물성: 현장/화면에서 실제로 느껴질 질감·빛·소리·스케일 1~2문장."},
        "transfer": {"type": "STRING", "description": "연출로 가져갈 것: 광고·영상·공간 연출에 옮길 수 있는 구체적 아이디어 1~2문장."},
        "keywords": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "한국어 키워드 3~5개, 각 2~8자"},
        "evidence": {"type": "STRING", "description": "원문에서 그대로 옮긴 짧은 구절(원어 그대로, 30단어 이내). 없으면 빈 문자열."},
        "kind": {"type": "STRING", "enum": ["프로젝트", "전시", "작가·인터뷰", "제품·오브제", "브랜드·캠페인", "영상·필름", "런웨이·컬렉션", "뉴스·이슈", "리스트·라운드업", "행사·공모"]},
        "depth": {"type": "INTEGER", "description": "저널 가치 1~5. 5=구체적 작업과 깊은 원문, 3=평범한 소개, 1=홍보·잡담·목록"},
        "grounding": {"type": "STRING", "enum": ["full", "partial", "thin"]},
    },
    "required": ["title_ko", "summary_ko", "lens", "why_now", "mechanism", "sensory", "transfer",
                 "keywords", "evidence", "kind", "depth", "grounding"],
}

NOTE_SYSTEM = """당신은 한국어 데일리 저널 RE:COLLECTION의 편집장입니다.
그날 실린 항목들의 큐레이터 메모를 읽고, 서로 다른 기사 사이를 잇는 흐름을 찾아 '오늘의 편집 노트'를 씁니다.
규칙: 제공된 항목 정보 밖의 사실을 지어내지 않습니다. 상투어(‘새로운 영감’, ‘공감각’, ‘경계를 허문다’, ‘시대정신’) 금지.
항목 이름을 구체적으로 부르며 연결합니다. 짧고 단단한 한국어 문장, '~다'로 끝나는 평서체.
깊이 점수가 높은 항목을 중심에 두고, 홍보성·목록형 항목은 흐름의 근거로 쓰지 않습니다."""

NOTE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "headline": {"type": "STRING", "description": "오늘 호를 관통하는 한 줄, 14~34자"},
        "editorial": {"type": "STRING", "description": "편집 노트 3~4문장, 180~320자. 구체 항목을 두세 개 불러 연결."},
        "threads": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING", "description": "흐름 이름 4~14자"},
                    "note": {"type": "STRING", "description": "이 흐름이 무엇인지 1~2문장"},
                    "refs": {"type": "ARRAY", "items": {"type": "INTEGER"}, "description": "해당 항목 번호 2~5개"},
                },
                "required": ["name", "note", "refs"],
            },
            "description": "2~3개의 흐름",
        },
    },
    "required": ["headline", "editorial", "threads"],
}


def build_item_prompt(item, body, meta, status):
    return f"""[메타]
출처: {item.get('source_name', '')}
분류: {item.get('genre', '')}
원제: {item.get('original_title', '')}
기계번역 제목(참고만, 오역 가능): {item.get('title', '')}
RSS 요약(기계번역일 수 있음): {item.get('snippet', '')}
og:description: {meta.get('og:description', meta.get('description', ''))}
원문 수집 상태: {status}, 본문 길이 {len(body)}자

[원문 본문]
{body if body else '(본문을 가져오지 못함. 메타 정보만으로 신중하게 작성)'}
"""


BANNED = ["새로운 영감", "공감각적 경험", "경계를 허", "시대정신을 투영", "압도적 몰입", "깊은 울림", "새로운 지평"]


def valid_item(d):
    for k in ("title_ko", "summary_ko", "lens", "transfer"):
        if not isinstance(d.get(k), str) or len(d[k].strip()) < 8:
            return f"missing {k}"
    if hangul_ratio(d["title_ko"]) < 0.35 and not re.search(r"[\uac00-\ud7a3]{2,}", d["title_ko"]):
        return "title not korean"
    if hangul_ratio(d["summary_ko"]) < 0.55:
        return "summary not korean"
    if hangul_ratio(d["lens"]) < 0.5:
        return "lens not korean"
    return None


def clean_item(d):
    for k in ("title_ko", "summary_ko", "lens", "why_now", "mechanism", "sensory", "transfer", "evidence"):
        v = d.get(k, "")
        v = re.sub(r"\s+", " ", str(v)).strip()
        d[k] = v
    d["keywords"] = [re.sub(r"\s+", " ", str(k)).strip().lstrip("#") for k in (d.get("keywords") or []) if str(k).strip()][:5]
    try:
        d["depth"] = max(1, min(5, int(d.get("depth", 3))))
    except Exception:
        d["depth"] = 3
    return d


def read_one(item):
    body, meta, status = fetch_article(item.get("url", ""))
    prompt = build_item_prompt(item, body, meta, status)
    last_err = None
    for _ in range(2):
        d, model = gemini_json(ITEM_SYSTEM, prompt, ITEM_SCHEMA)
        d = clean_item(d)
        err = valid_item(d)
        if not err:
            hits = [b for b in BANNED if b in json.dumps(d, ensure_ascii=False)]
            d.update({
                "v": VERSION,
                "url": item.get("url", ""),
                "original_title": item.get("original_title", ""),
                "model": model,
                "source_chars": len(body),
                "fetch": status,
                "cliche_hits": hits,
                "read_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
            })
            return d
        last_err = err
        prompt += f"\n\n[이전 출력 문제: {err}. 모든 필드를 자연스러운 한국어로 다시 작성하세요.]"
    raise RuntimeError(f"invalid output: {last_err}")


# ---------------------------------------------------------------------------
# 4. 저장 유틸
# ---------------------------------------------------------------------------
def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def collect_items():
    """최신 날짜부터, 날짜별 항목 목록."""
    by_date = []
    for fp in sorted(glob.glob(os.path.join(DAILY_DIR, "*.json")), reverse=True):
        d = os.path.basename(fp)[:-5]
        if ONLY_DATES and d not in ONLY_DATES:
            continue
        items = load_json(fp, [])
        if isinstance(items, list) and items:
            by_date.append((d, items))
    return by_date


# ---------------------------------------------------------------------------
# 5. 날짜별 편집 노트
# ---------------------------------------------------------------------------
def make_note(date, items, cache):
    rows = []
    for it in items:
        d = cache.get(url_key(it.get("url", "")))
        if d:
            rows.append((it, d))
    rows.sort(key=lambda r: -r[1].get("depth", 3))
    rows = rows[:24]
    lines = []
    for i, (it, d) in enumerate(rows, 1):
        lines.append(f"{i}. [{d.get('kind', '')}·깊이{d.get('depth', 3)}] {d['title_ko']} — {d['lens']} (키워드: {', '.join(d.get('keywords', []))})")
    prompt = f"날짜: {date}\n오늘 실린 항목 {len(rows)}개:\n" + "\n".join(lines)
    note, model = gemini_json(NOTE_SYSTEM, prompt, NOTE_SCHEMA, temperature=0.6)
    threads = []
    for t in note.get("threads", [])[:3]:
        refs = [r for r in (t.get("refs") or []) if isinstance(r, int) and 1 <= r <= len(rows)]
        threads.append({
            "name": str(t.get("name", "")).strip(),
            "note": re.sub(r"\s+", " ", str(t.get("note", ""))).strip(),
            "items": [{"title": rows[r - 1][1]["title_ko"], "url": rows[r - 1][0].get("url", "")} for r in refs[:5]],
        })
    return {
        "date": date,
        "headline": re.sub(r"\s+", " ", note.get("headline", "")).strip(),
        "editorial": re.sub(r"\s+", " ", note.get("editorial", "")).strip(),
        "threads": threads,
        "based_on": len(rows),
        "model": model,
        "written_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
    }


# ---------------------------------------------------------------------------
def main():
    global POOL
    if not KEYS:
        log("GEMINI_API_KEY 없음 → 건너뜀 (사이트는 기존 기계번역으로 계속 빌드됨)")
        return
    POOL = Pool()
    cache = load_json(CACHE_FILE, {})
    notes = load_json(NOTES_FILE, {})
    by_date = collect_items()

    todo, seen = [], set()
    for d, items in by_date:
        for it in items:
            k = url_key(it.get("url", ""))
            if not k or k in seen:
                continue
            seen.add(k)
            c = cache.get(k)
            if c and c.get("v", 0) >= VERSION:
                continue
            todo.append(it)
    log(f"대기 {len(todo)}건 / 캐시 {len(cache)}건 / 이번 실행 최대 {MAX_ITEMS}건")
    todo = todo[:MAX_ITEMS]

    done = fail = 0
    stop = False
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futs = {ex.submit(read_one, it): it for it in todo}
        for f in as_completed(futs):
            it = futs[f]
            try:
                d = f.result()
                cache[url_key(it.get("url", ""))] = d
                done += 1
                log(f"OK d{d['depth']} {d['grounding']:7s} {d['title_ko'][:40]}")
                if done % 8 == 0:
                    save_json(CACHE_FILE, cache)
            except TimeoutError:
                stop = True
            except Exception as e:
                fail += 1
                log(f"FAIL {str(e)[:90]} :: {it.get('original_title', '')[:60]}")
                if "exhausted" in str(e):
                    stop = True
            if stop:
                for g in futs:
                    g.cancel()
    save_json(CACHE_FILE, cache)
    log(f"항목 읽기 완료: 성공 {done}, 실패 {fail}, 호출 {POOL.calls}")

    # 날짜 노트: 오늘은 새 항목이 3개 이상 늘면 다시 쓰고, 과거 날짜는 없을 때만 쓴다.
    today = datetime.now(KST).strftime("%Y-%m-%d")
    made = 0
    for d, items in by_date:
        if made >= MAX_NOTES or time_left() < 60:
            break
        read_n = sum(1 for it in items if url_key(it.get("url", "")) in cache)
        if read_n < 4:
            continue
        old = notes.get(d)
        if old:
            grown = min(read_n, 24) - old.get("based_on", 0)
            if d != today or grown < 3:
                continue
        try:
            notes[d] = make_note(d, items, cache)
            made += 1
            log(f"NOTE {d}: {notes[d]['headline']}")
            save_json(NOTES_FILE, notes)
        except Exception as e:
            log(f"NOTE FAIL {d}: {str(e)[:100]}")
    save_json(NOTES_FILE, notes)
    log(f"편집 노트 {made}건 작성. 총 소요 {int(time.time() - START)}초")


if __name__ == "__main__":
    main()
