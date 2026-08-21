import os
import json
import time
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
from deep_translator import GoogleTranslator
import concurrent.futures

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Optional ChromaDB for local vector semantic search
try:
    import chromadb
    from chromadb.utils import embedding_functions
    chroma_client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chroma_db"))
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")
    collection = chroma_client.get_or_create_collection(name="bookmarks", embedding_function=sentence_transformer_ef)
except Exception:
    collection = None

# 2. Expanded 25+ Global Curated Feeds (Focusing on Space x Media, Facades, LED & 3D Art)
CURATED_SOURCES = [
    # 1. Spatial Experience Scenography & Architecture (공간 시노그래피 & 건축)
    {
        "name": "Frame Web",
        "url": "https://www.frameweb.com/feed",
        "genre": "SPATIAL SCENOGRAPHY"
    },
    {
        "name": "Dezeen",
        "url": "https://www.dezeen.com/feed/",
        "genre": "SPACE & ARCH"
    },
    {
        "name": "ArchDaily",
        "url": "https://www.archdaily.com/feed",
        "genre": "SPACE & ARCH"
    },
    {
        "name": "Yellowtrace",
        "url": "https://www.yellowtrace.com.au/feed/",
        "genre": "SPATIAL SCENOGRAPHY"
    },
    {
        "name": "Yatzer",
        "url": "https://www.yatzer.com/feed/index.php",
        "genre": "SPATIAL SCENOGRAPHY"
    },
    {
        "name": "Ignant",
        "url": "https://www.ignant.com/feed/",
        "genre": "SPATIAL SCENOGRAPHY"
    },
    # 2. Media Facade, LED Installation, 3D & Projection Mapping (미디어 파사드, LED, 3D & 프로젝션 매핑)
    {
        "name": "CreativeApplications.net",
        "url": "https://www.creativeapplications.net/feed/",
        "genre": "MEDIA FACADE & 3D"
    },
    {
        "name": "Stash Media (Motion & 3D Visuals)",
        "url": "https://www.stashmedia.tv/feed/",
        "genre": "MEDIA FACADE & 3D"
    },
    {
        "name": "Motionographer",
        "url": "https://motionographer.com/feed/",
        "genre": "MEDIA FACADE & 3D"
    },
    {
        "name": "Projection Mapping Central",
        "url": "https://projection-mapping.org/feed/",
        "genre": "MEDIA FACADE & 3D"
    },
    # 3. Contemporary Media Art, Exhibition & Digital Canvas (현대 미디어 아트 & 디지털 캔버스)
    {
        "name": "This Is Colossal",
        "url": "https://www.thisiscolossal.com/feed/",
        "genre": "MEDIA ART & EXPO"
    },
    {
        "name": "Designboom (Art & Media)",
        "url": "https://www.designboom.com/art/feed/",
        "genre": "MEDIA ART & EXPO"
    },
    {
        "name": "Wallpaper* (Design & Tech)",
        "url": "https://www.wallpaper.com/feed/rss",
        "genre": "MEDIA ART & EXPO"
    },
    # 4. Avant-Garde Fashion Film & Digital Tactility (아방가르드 패션 필름 & 디지털 촉각)
    {
        "name": "SHOWstudio",
        "url": "https://showstudio.com/feed/rss",
        "genre": "AVANT-GARDE FASHION"
    },
    {
        "name": "Hypebeast",
        "url": "https://hypebeast.com/fashion/feed",
        "genre": "FASHION & ZEITGEIST"
    },
    {
        "name": "Dazed & Confused",
        "url": "https://www.dazeddigital.com/rss",
        "genre": "FASHION & ZEITGEIST"
    },
    {
        "name": "Highsnobiety",
        "url": "https://www.highsnobiety.com/feed/",
        "genre": "FASHION & ZEITGEIST"
    },
    {
        "name": "AnOther Magazine",
        "url": "https://www.anothermag.com/rss",
        "genre": "AVANT-GARDE FASHION"
    },
    # 5. Cinematic Moving Image & Narrative (시네마틱 영상 & 서사)
    {
        "name": "Nowness (Cinematic Culture)",
        "url": "https://www.nowness.com/feed",
        "genre": "CINEMA & FILM"
    },
    {
        "name": "It's Nice That",
        "url": "https://www.itsnicethat.com/feed/rss",
        "genre": "DESIGN & VISUAL"
    },
    {
        "name": "Sight Unseen",
        "url": "https://www.sightunseen.com/feed/",
        "genre": "DESIGN & OBJECT"
    },
    {
        "name": "Minimalissimo",
        "url": "https://minimalissimo.com/feed/",
        "genre": "DESIGN & OBJECT"
    }
]

def is_quality_curated_article(title, summary, genre):
    """
    Strict Curatorial Quality Gate:
    Filters out noise, generic product ads, or gossip.
    Only selects articles with high spatial, media, fashion aesthetics, or artistic depth.
    """
    text = (title + ' ' + summary).lower()
    
    # Negative filters (Exclude noise)
    exclude_keywords = ['sale', 'discount', 'coupon', 'giveaway', 'gossip', 'rumor', 'unboxing', 'deal of the day']
    if any(kw in text for kw in exclude_keywords):
        return False
        
    # High value aesthetic keywords
    positive_keywords = [
        'space', 'spatial', 'architecture', 'interior', 'pavilion', 'scenography',
        'facade', 'projection', 'mapping', 'led', '3d', 'installation', 'kinetic', 'light',
        'fashion', 'runway', 'couture', 'textile', 'drape', 'subculture', 'zeitgeist',
        'art', 'contemporary', 'sculpture', 'gallery', 'museum', 'exhibition',
        'cinema', 'film', 'narrative', 'visual', 'material', 'craft', 'object'
    ]
    
    match_count = sum(1 for kw in positive_keywords if kw in text)
    # Always include specialized genres or entries with at least 1 aesthetic keyword
def safe_translate(text):
    if not text or len(text.strip()) == 0:
        return text
    try:
        # Limit translation chunk to 1000 chars for reliability
        return GoogleTranslator(source='auto', target='ko').translate(text[:1000])
    except Exception as e:
        print(f"[Translator Error]: {e}")
        return text

def extract_media_from_entry(entry, fallback_url):
    """
    Extracts high-resolution image and potential embedded video url (Nowness/Vimeo/YouTube).
    """
    img_url = ""
    video_url = ""
    
    # 1. Try entry media content
    if 'media_content' in entry and entry.media_content:
        for m in entry.media_content:
            url = m.get('url', '')
            if any(ext in url.lower() for ext in ['jpg', 'jpeg', 'png', 'webp']):
                if not img_url:
                    img_url = url
            elif any(v in url.lower() for v in ['mp4', 'webm', 'vimeo', 'youtube', 'nowness']):
                video_url = url
                
    if not img_url and 'media_thumbnail' in entry and entry.media_thumbnail:
        img_url = entry.media_thumbnail[0].get('url', '')
    
    # 2. Try parsing html summary/content
    summary = entry.get('summary', '') or entry.get('description', '')
    if 'content' in entry and entry.content:
        summary += ' ' + entry.content[0].get('value', '')
        
    if summary:
        soup = BeautifulSoup(summary, 'html.parser')
        
        # Check image
        if not img_url:
            img = soup.find('img')
            if img and img.get('src'):
                src = img['src']
                if not src.startswith('data:') and any(ext in src.lower() for ext in ['jpg', 'jpeg', 'png', 'webp']):
                    img_url = src
                    
        # Check iframe / video
        if not video_url:
            iframe = soup.find('iframe')
            if iframe and iframe.get('src'):
                video_url = iframe['src']
            video = soup.find('video')
            if video and video.get('src'):
                video_url = video['src']
            
    # 3. Direct fetch og:image or video from article url
    if fallback_url and (not img_url or not video_url):
        try:
            res = requests.get(fallback_url, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}, timeout=4)
            if res.status_code == 200:
                s = BeautifulSoup(res.text, 'html.parser')
                
                if not img_url:
                    og_img = s.find('meta', property='og:image') or s.find('meta', attrs={'name': 'og:image'})
                    if og_img and og_img.get('content'):
                        img_url = og_img['content']
                        
                if not video_url:
                    og_video = s.find('meta', property='og:video') or s.find('meta', attrs={'name': 'og:video:url'})
                    if og_video and og_video.get('content'):
                        video_url = og_video['content']
                    else:
                        v_iframe = s.find('iframe')
                        if v_iframe and v_iframe.get('src') and any(domain in v_iframe['src'] for domain in ['vimeo', 'youtube', 'nowness', 'player']):
                            video_url = v_iframe['src']
        except Exception:
            pass
        
    return img_url, video_url

def design_insights(title_ko, snippet_ko, genre):
    """
    Design deep curatorial insights on Spatial Memory, Offline Video CX, and Zeitgeist Horizon.
    """
    if 'MEDIA' in genre or 'FACADE' in genre or '3D' in genre:
        genius_loci = (
            f"〈{title_ko}〉는 물리적 건축 표면과 대형 LED/3D 미디어 프로젝션이 만나는 융합적 장소성을 연출합니다. "
            f"도시의 전면 파사드나 3D 공간 캔버스에 투사된 비주얼은 고정된 건축의 중량감을 지우고 살아 숨 쉬는 미디어 랜드마크를 창출합니다."
        )
        sensory_recall = (
            f"3D 아나몰픽 착시가 전하는 압도적인 입체감, 고해상도 LED 패널의 선명한 루미너스 다이내믹스, 실시간 모션 파티클이 관람객의 시각과 공간적 거리감을 강렬하게 흔들어 놓습니다."
        )
        zeitgeist_synapse = (
            f"피지털(Phygital) 시대의 시대를 앞서는 기술적 미학을 반영하며, 도심 속 공공 미디어 아트 및 브랜드 스페이스의 미래 방향성을 보여줍니다."
        )
        spatial_video_cx = (
            f"대형 미디어 파사드나 퍼블릭 스페이스의 3D 아나몰픽 스크린에 연출할 때, "
            f"스쳐 지나가는 보행자의 시선을 단 2초 만에 점유(Stop-and-Stare)하고, SNS 바이럴과 장소 브랜딩 기억을 극대화합니다."
        )
        zeitgeist_horizon = (
            f"건축 벽면을 단순 광 스크린이 아닌 디지털 예술의 숨쉬는 생체 피부(Living Kinetic Skin)로 진화시키는 차세대 미디어 아키텍처입니다."
        )
        tactile_metrics = {
            "tactility": "3D ANAMORPHIC & LED LUMINOUS",
            "spatial_volume": "PUBLIC MEDIA FACADE & 3D CANVAS",
            "dwell_tempo": "HIGH-IMPACT VISUAL ARREST"
        }
        synapses = [
            {"domain": "건축 파사드 & 엔지니어링 (Architectural Media)", "connection": "건축 외벽 구조재와 LED 메쉬 시스템을 일체화하여 매끄러운 3D 착시 공간을 구현합니다."},
            {"domain": "3D 모션 & 제너레이티브 아트 (Generative Visuals)", "connection": "실시간 데이터 및 3D 그래픽 엔진을 결합하여 시시각각 변화하는 반응형 시각 예술을 렌더링합니다."},
            {"domain": "도시 공공 미술 (Public Art & Landmark)", "connection": "상업적 광고판의 한계를 넘어 도시 생태계에 감각적 영감을 불어넣는 랜드마크로 전환됩니다."}
        ]
    elif 'FASHION' in genre:
        genius_loci = (
            f"〈{title_ko}〉는 런웨이의 시공간과 도시의 거리(Street)라는 장소성을 교차시킵니다. "
            f"신체가 옷을 입고 공간을 활보할 때 발생하는 실루엣의 율동감은 오프라인 패션쇼의 압도적인 현장감과 도시적 기억을 재구성합니다."
        )
        sensory_recall = (
            f"패브릭의 원초적 질감, 조명 아래 드러나는 섬세한 직조의 음영, 런웨이 음악의 앰비언트 비트가 결합되어 관찰자의 촉각적·시각적 기억에 강렬하게 각인됩니다."
        )
        zeitgeist_synapse = (
            f"동시대 서브컬처와 하이엔드 럭셔리의 경계를 허물며 현세대의 '시대정신(Zeitgeist)'을 투영합니다. 이는 현대 미술의 개념적 실험 및 영화적 미장센과 긴밀하게 소통합니다."
        )
        spatial_video_cx = (
            f"플래그십 스토어의 대형 버티컬 미디어월이나 팝업 공간에서 극단적 클로즈업과 슬로우 셔터 모션으로 연출할 때, "
            f"고객의 '디지털 촉각성(Digital Tactility)'을 자극하여 브랜드에 대한 관능적 몰입감과 자발적 소셜 공유(Cultural Trophy)를 유도합니다."
        )
        zeitgeist_horizon = (
            f"정형화된 제품 광고를 탈피하여 신체와 의복의 해방감을 다루는 '무드 아키텍처(Mood Architecture)' 비주얼로 시대를 선도합니다."
        )
        tactile_metrics = {
            "tactility": "HIGH-END TEXTILE & DRAPE",
            "spatial_volume": "FLAGSHIP VERTICAL MEDIAWALL",
            "dwell_tempo": "RHYTHMIC DYNAMIC FLOW"
        }
        synapses = [
            {"domain": "현대 미술 (Contemporary Art)", "connection": "개념 미술의 문맥을 일상적인 웨어러블 조각(Wearable Sculpture)의 형태로 치환하여 탐구합니다."},
            {"domain": "공간 & 건축 (Spatial Design)", "connection": "플래그십 스토어 및 무대 연출을 통해 구조적 볼륨과 빛의 긴장감을 공간적으로 확장합니다."},
            {"domain": "시네마 & 서사 (Cinematic Narrative)", "connection": "시대를 관통하는 서브컬처 무브먼트와 영상 미학의 미장센으로 이어집니다."}
        ]
    elif 'SPACE' in genre or 'SCENOGRAPHY' in genre or 'IMMERSIVE' in genre:
        genius_loci = (
            f"〈{title_ko}〉는 대지에 깃든 시간의 지층과 장소성(Genius Loci)을 현대적 건축 언어로 구축했습니다. "
            f"건물 안팎을 거닐며 경험하는 빛과 그림자의 시퀀스는 관람객으로 하여금 공간에 깊이 몰입하게 만드는 시공간적 기억을 형성합니다."
        )
        sensory_recall = (
            f"여백을 가르는 자연광의 궤적, 린넨과 석재의 고유한 촉각적 물성, 공간을 채우는 정적과 바람의 숨결이 깊은 사유와 고요한 감각적 안식을 선사합니다."
        )
        zeitgeist_synapse = (
            f"지속 가능한 건축과 미니멀한 삶의 태도를 통해 현대 도시 사회의 피로를 치유하는 시대정신을 담고 있습니다."
        )
        spatial_video_cx = (
            f"전시장 및 리테일 공간의 파사드 미디어에 '공간의 연장선(Spatial Extension)'으로서 아나몰픽 프로젝션으로 투사할 때, "
            f"물리적 벽체의 한계를 지우고 고객의 뇌리에 '기억에 남는 랜드마크(Episodic Memory)'로 각인됩니다."
        )
        zeitgeist_horizon = (
            f"단순 소비 공간을 '심미적 향유와 사유의 성소(Sanctuary)'로 격상시키는 미래형 공간 경험(CX) 모델을 제시합니다."
        )
        tactile_metrics = {
            "tactility": "RAW STONE, LINEN & LIGHT",
            "spatial_volume": "360° IMMERSIVE BOX CANVAS",
            "dwell_tempo": "SLOW MEDITATIVE POETRY"
        }
        synapses = [
            {"domain": "패션 & 텍스타일 (Fashion & Material)", "connection": "소재 고유의 직조감과 미니멀한 드레이핑 기법이 공간의 벽면과 차양 구조에 맞닿아 있습니다."},
            {"domain": "현대 미술 (Installation Art)", "connection": "공간 자체가 하나의 거대한 장소 특정적 설치 미술(Site-Specific Installation)로 작동합니다."},
            {"domain": "사운드 & 환경 (Ambient Sound)", "connection": "공간의 울림과 바람, 빛의 소멸이 앰비언트 사운드스케이프와 유기적으로 호흡합니다."}
        ]
    elif 'CINEMA' in genre:
        genius_loci = (
            f"〈{title_ko}〉는 영상의 프레임 속에 특정한 시공간적 무드를 봉인합니다. "
            f"오프라인 암전 상영관이나 갤러리 영상 설치실에서 관람자가 체감했던 몽환적인 공간감과 시간성의 확장을 디지털 저널로 재현합니다."
        )
        sensory_recall = (
            f"서사를 이끄는 감각적인 색채의 잔상, 슬로우 템포의 호흡, 은은한 사운드 텍스처가 결합되어 오랫동안 지워지지 않는 정서적 여운을 남깁니다."
        )
        zeitgeist_synapse = (
            f"현대인의 고독, 관계의 불완전성, 디지털 시대의 새로운 연대감을 시대를 관통하는 시네마틱 영상 언어로 포착합니다."
        )
        spatial_video_cx = (
            f"어두운 라운지나 몰입형 암전 룸에서 입체 음향(Spatial Audio)과 함께 상영할 때, 고객의 감정적 경외감(Awe)을 극대화하고 깊은 체류 시간(Dwell Time)을 확보합니다."
        )
        zeitgeist_horizon = (
            f"단편적 숏폼 미디어에 지친 현대인에게 서사적 쉼표와 감정적 깊이를 선사하는 슬로우 시네마적 공간 미학을 선도합니다."
        )
        tactile_metrics = {
            "tactility": "CINEMATIC GRAIN & LIGHT SHADOW",
            "spatial_volume": "BLACKBOX CINEMATIC LOUNGE",
            "dwell_tempo": "DEEP EMOTIONAL DWELL"
        }
        synapses = [
            {"domain": "패션 & 비주얼 (Fashion & Style)", "connection": "인물의 복식과 텍스처를 통해 시대적 뉘앙스와 내면 심리를 암시하는 시각적 장치로 활용됩니다."},
            {"domain": "공간 디자인 (Set & Architecture)", "connection": "인물의 감정을 대변하는 폐쇄적/개방적 공간 구도를 통해 건축적 긴장감을 구축합니다."},
            {"domain": "현대 미술 (Video Art)", "connection": "미술관의 블랙박스 영상 전시와 비선형적 서사 구조로 연결됩니다."}
        ]
    else:
        genius_loci = (
            f"〈{title_ko}〉는 일상의 사물과 시각적 형태가 놓인 공간의 미적 질서를 새롭게 정의합니다. "
            f"오브제가 공간 속에 자리 잡을 때 생겨나는 고유한 장소성과 긴장감을 조명합니다."
        )
        sensory_recall = (
            f"정교하게 다듬어진 조형의 비례, 소재의 따뜻한 온기, 시선이 머무는 세밀한 디테일이 정갈한 미적 쾌감을 전달합니다."
        )
        zeitgeist_synapse = (
            f"물질성과 디지털 가상성이 공존하는 동시대 예술과 디자인의 최전선에서, 본질적인 미적 가치와 지속 가능성을 탐구하는 시대정신을 반영합니다."
        )
        spatial_video_cx = (
            f"인터랙티브 키오스크나 제품 디스플레이 주변의 앰비언트 루프 비주얼로 활용될 때, 사물의 '물성(Materiality)'을 직관적으로 증폭시켜 구매 고려도를 극대화합니다."
        )
        zeitgeist_horizon = (
            f"디지털 오브제와 물리적 가구가 유기적으로 융합되는 피지털(Phygital) 리빙의 새로운 패러다임을 개척합니다."
        )
        tactile_metrics = {
            "tactility": "CRAFTED WOOD, GLASS & CERAMIC",
            "spatial_volume": "OBJECT DISPLAY & KIOSK",
            "dwell_tempo": "SERENE VISUAL BALANCE"
        }
        synapses = [
            {"domain": "패션 & 라이프스타일 (Contemporary Living)", "connection": "일상의 오브제 미학이 라이프스타일 전반과 개인의 취향을 구성하는 매개체가 됩니다."},
            {"domain": "공간 조형 (Spatial Form)", "connection": "사물이 공간에 놓였을 때 발생하는 긴장감과 오브제 중심의 인테리어 스노비즘을 해체합니다."},
            {"domain": "디지털 & 미디어 (Digital Culture)", "connection": "물리적 물질성을 디지털 매체로 아카이빙하고 공유하는 현대적 시각 문화로 확장됩니다."}
        ]

    return {
        'genre': genre,
        'genius_loci': genius_loci,
        'sensory_recall': sensory_recall,
        'zeitgeist_synapse': zeitgeist_synapse,
        'spatial_video_cx': spatial_video_cx,
        'zeitgeist_horizon': zeitgeist_horizon,
        'tactile_metrics': tactile_metrics,
        'synapse_connections': synapses,
        'archive_note': 'RE:COLLECTION 데일리 에디토리얼 파이프라인에서 큐레이션된 도록 레코드입니다.'
    }

def process_single_entry(entry, source):
    title = entry.get('title', '')
    url = entry.get('link', '')
    if not title or not url:
        return None
        
    raw_summary = entry.get('summary', '') or entry.get('description', '')
    soup = BeautifulSoup(raw_summary, 'html.parser')
    clean_summary = soup.get_text().strip()[:300]
    
    # Strict Curatorial Quality Gate Check
    if not is_quality_curated_article(title, clean_summary, source['genre']):
        return None
        
    img_url, video_url = extract_media_from_entry(entry, url)
    
    # Fast translation
    title_ko = safe_translate(title)
    snippet_ko = safe_translate(clean_summary) if clean_summary else title_ko
    
    facets = design_insights(title_ko, snippet_ko, source['genre'])
    
    item = {
        "id": url,
        "title": title_ko,
        "original_title": title,
        "url": url,
        "image_url": img_url,
        "video_url": video_url,
        "has_video": bool(video_url),
        "snippet": snippet_ko,
        "genre": source['genre'],
        "source_name": source['name'],
        "collected_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "facets": facets
    }
    
    return item

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_FILE = os.path.join(BASE_DIR, "data", "daily_archive.json")

def run_daily_collection(limit_per_source=4):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Fast Cumulative Scraping...")
    
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    
    existing_items = []
    existing_urls = set()
    if os.path.exists(ARCHIVE_FILE):
        try:
            with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
                existing_items = json.load(f)
                if isinstance(existing_items, list):
                    existing_urls = {item['url'] for item in existing_items if isinstance(item, dict) and 'url' in item}
                else:
                    existing_items = []
        except Exception as e:
            print(f"Error loading existing archive: {e}")
            existing_items = []
            
    raw_entries_to_process = []
    for source in CURATED_SOURCES:
        try:
            feed = feedparser.parse(source['url'])
            count = 0
            for entry in feed.entries:
                url = entry.get('link', '')
                if url and url in existing_urls:
                    continue # Already collected!
                    
                raw_entries_to_process.append((entry, source))
                count += 1
                if count >= limit_per_source:
                    break
        except Exception as e:
            print(f"Error parsing feed {source['name']}: {e}")

    # Fast parallel processing of new entries
    new_collected_items = []
    if raw_entries_to_process:
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            future_to_entry = {executor.submit(process_single_entry, entry, source): (entry, source) for entry, source in raw_entries_to_process}
            for future in concurrent.futures.as_completed(future_to_entry):
                try:
                    res = future.result()
                    if res:
                        new_collected_items.append(res)
                except Exception as e:
                    print(f"Entry process error: {e}")

    # Accumulate: Newest at top, existing below
    combined_archive = new_collected_items + existing_items
    
    # If no new items and existing_items exist, retain all existing items
    if not combined_archive and existing_items:
        combined_archive = existing_items
        
    combined_archive = combined_archive[:150] # Keep up to 150 cumulative items

    try:
        with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
            json.dump(combined_archive, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving archive: {e}")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scraping Complete. Added {len(new_collected_items)} new items. Total {len(combined_archive)} items preserved.")
    return combined_archive

if __name__ == '__main__':
    run_daily_collection()
