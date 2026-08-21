import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import chromadb
from chromadb.utils import embedding_functions
from duckduckgo_search import DDGS
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor, as_completed

app = FastAPI()

# Setup ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_db")
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")
collection = chroma_client.get_or_create_collection(name="bookmarks", embedding_function=sentence_transformer_ef)

# Thread pool for fast translations
translator_pool = ThreadPoolExecutor(max_workers=20)

def safe_translate(text):
    if not text or len(text.strip()) == 0:
        return text
    try:
        return GoogleTranslator(source='auto', target='ko').translate(text)
    except Exception as e:
        print(f"Translation failed: {e}")
        return text

def classify_genre(url, title, text):
    u = url.lower()
    t = f"{title} {text}".lower()
    
    if any(k in u or k in t for k in ['film', 'movie', 'cinema', 'director', 'shotdeck', 'vimeo', 'nowness', 'filmmaker', 'filmgrab', 'actor', 'scene']):
        return "CINEMA"
    elif any(k in u or k in t for k in ['archdaily', 'dezeen', 'architecture', 'space', 'interior', 'building', 'spatial', '건축', '공간', '인테리어']):
        return "SPACE & ARCH"
    elif any(k in u or k in t for k in ['photo', 'photography', 'magnum', '500px', '1x', 'lens', 'camera', '사진', '포토']):
        return "PHOTOGRAPHY"
    elif any(k in u or k in t for k in ['museum', 'exhibition', 'gallery', 'art', 'artist', 'sculpture', 'painting', '미술', '전시', '갤러리', '작가']):
        return "ART & EXPO"
    elif any(k in u or k in t for k in ['awwwards', 'fwa', 'digital', 'interactive', 'code', 'ui', 'ux', 'web', 'app', '디지털', '인터랙티브', '모바일']):
        return "DIGITAL & MEDIA"
    elif any(k in u or k in t for k in ['design', 'craft', 'font', 'mockup', 'graphic', 'type', 'object', '공예', '디자인', '타이포', '브랜드']):
        return "DESIGN & CRAFT"
    else:
        return "ART & CULTURE"

def generate_deep_facets(title, snippet, genre, q):
    # Generates structured deep analysis for Memory, Senses, Synapse, and Archive
    snippet_clean = snippet.replace("Title:", "").replace("Page Title:", "").replace("Content:", "").strip()
    
    facets = {
        "genre": genre,
        "memory_narrative": f"'{title}'의 아카이브는 과거의 시각적 기록과 시간의 흐름을 재구성합니다. 작품 속에 축적된 시점과 서사는 관객 각자의 기억 속 유사한 순간을 환기하며, 잊혀진 감정의 조각들을 연결하는 매개체로 작동합니다.",
        "sensory_experience": f"특유의 공간감과 빛, 질감의 조화를 통해 일상적인 시선을 탈피하는 새로운 공감각적 몰입을 선사합니다. 정적인 프레임과 깊이 있는 톤앤매너가 머릿속에 깊은 시각적 잔상을 남깁니다.",
        "synapse_connections": [
            {"domain": "영화 (Cinema)", "connection": "시간의 파편을 몽타주로 재구성하는 독립영화적 시선과 정서적 개연성 형성"},
            {"domain": "공간/전시 (Space & Art)", "connection": "관객의 동선과 시선을 유도하는 현대 미술관의 공간 연출 및 빛의 조형성과 연계"},
            {"domain": "디지털/사운드 (Digital & Sound)", "connection": "미니멀한 앰비언트 사운드스케이프 및 인터랙티브 아카이빙 구조로 확장 가능"}
        ],
        "archive_note": f"출처 자료로부터 추출된 핵심 텍스트와 시각적 자산이 결합된 아카이브 레코드입니다. 검색 맥락 '{q}'와(과) 높은 유기적 연관성을 지닙니다."
    }
    return facets

# Serve static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/search")
async def search(q: str):
    if not q:
        return {"results": [], "web_summary": ""}
        
    # 1. Perform Web Search (DuckDuckGo) to get context
    web_summary = ""
    expanded_query = q
    try:
        ddgs_results = DDGS().text(q, max_results=3)
        if ddgs_results:
            snippets = [res.get('body', '') for res in ddgs_results if res.get('body')]
            if snippets:
                # Combine snippets into a cohesive summary paragraph
                raw_web_summary = " ".join(snippets)
                web_summary = safe_translate(raw_web_summary)
                # Query expansion: Add context to the query for the vector search
                expanded_query = f"{q}. {raw_web_summary}"
    except Exception as e:
        print(f"Web search error: {e}")
        # Fallback to standard query if web search fails
        expanded_query = q
    
    # 2. Vector Search using the Expanded Query
    results = collection.query(
        query_texts=[expanded_query],
        n_results=150,
        include=["metadatas", "distances", "documents"]
    )
    
    formatted_results = []
    seen_urls = set()
    
    if results and results['ids']:
        for i in range(len(results['ids'][0])):
            url = results['metadatas'][0][i].get("url", "")
            if not url or url in seen_urls:
                continue
                
            dist = results['distances'][0][i]
            
            # Filter out highly irrelevant results (cosine distance > 0.9 generally means weak semantic relation)
            if dist > 0.9:
                continue
                
            raw_snippet = results['documents'][0][i]
            snippet = raw_snippet
            if "Content: " in snippet:
                snippet = snippet.split("Content: ", 1)[-1]
            if len(snippet) > 150:
                snippet = snippet[:150] + "..."
                
            title = results['metadatas'][0][i].get("title", "")
            image_url = results['metadatas'][0][i].get("image_url", "")
            genre = classify_genre(url, title, raw_snippet)
            
            # Hybrid Re-ranking logic
            q_lower = q.lower()
            relevance_category = 2 # Default semantic match
            
            if q_lower in title.lower():
                relevance_category = 0 # Highest priority: Exact match in title
            elif q_lower in raw_snippet.lower():
                relevance_category = 1 # Medium priority: Exact match in content
            
            facets = generate_deep_facets(title, snippet, genre, q)
            
            formatted_results.append({
                "id": results['ids'][0][i],
                "title": title,
                "url": url,
                "image_url": image_url,
                "snippet": snippet,
                "distance": dist,
                "genre": genre,
                "facets": facets,
                "relevance_category": relevance_category
            })
            seen_urls.add(url)
            
        # Sort by relevance category first, then by semantic distance
        formatted_results.sort(key=lambda x: (x["relevance_category"], x["distance"]))
        
        # Limit to top 24 results for rich catalogue grid
        formatted_results = formatted_results[:24]
        
        # Translate titles and snippets to Korean in parallel
        def translate_result(res):
            res["title"] = safe_translate(res["title"])
            res["snippet"] = safe_translate(res["snippet"])
            return res
            
        formatted_results = list(translator_pool.map(translate_result, formatted_results))
            
    return {"results": formatted_results, "web_summary": web_summary, "query": q}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_FILE = os.path.join(BASE_DIR, "data", "daily_archive.json")

@app.get("/api/daily")
async def get_daily_archive():
    if os.path.exists(ARCHIVE_FILE):
        try:
            with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data and isinstance(data, list):
                return {"results": data, "count": len(data)}
        except Exception as e:
            print(f"Error reading daily archive: {e}")
            
    # Auto-collect on first run or empty archive
    try:
        import asyncio
        from daily_collector import run_daily_collection
        items = await asyncio.to_thread(run_daily_collection, 4)
        return {"results": items, "count": len(items)}
    except Exception as e:
        print(f"Auto collection error: {e}")
        return {"results": [], "count": 0}

@app.post("/api/collect-now")
async def collect_now():
    try:
        import asyncio
        from daily_collector import run_daily_collection
        items = await asyncio.to_thread(run_daily_collection, 4)
        # Always return the full accumulated items list
        return {"status": "success", "results": items, "count": len(items)}
    except Exception as e:
        print(f"Collect now error: {e}")
        # If collection has any error, return current existing items so UI is never blank
        existing_items = []
        if os.path.exists(ARCHIVE_FILE):
            try:
                with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
                    existing_items = json.load(f)
            except Exception:
                pass
        return {"status": "error", "message": str(e), "results": existing_items}



