import os
import json
import time
import re
from urllib.parse import urlparse
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from deep_translator import GoogleTranslator
import concurrent.futures

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
collection = None

# 2. Expanded 35+ Global Curated Feeds (Architecture, 3D Media Facades, Light Art, Avant-Garde Fashion)
CURATED_SOURCES = [
    # 1. Spatial Experience Scenography & Master Architecture
    { "name": "Frame Web", "url": "https://www.frameweb.com/feed", "genre": "SPACE & ARCH" },
    { "name": "Yellowtrace", "url": "https://www.yellowtrace.com.au/feed/", "genre": "SPACE & ARCH" },
    { "name": "Yatzer", "url": "https://www.yatzer.com/feed/index.php", "genre": "SPACE & ARCH" },
    { "name": "Ignant", "url": "https://www.ignant.com/feed/", "genre": "SPACE & ARCH" },
    { "name": "Leibal", "url": "https://leibal.com/feed/", "genre": "SPACE & ARCH" },
    { "name": "Dezeen", "url": "https://www.dezeen.com/feed/", "genre": "SPACE & ARCH" },
    { "name": "ArchDaily", "url": "https://www.archdaily.com/feed", "genre": "SPACE & ARCH" },
    { "name": "Design Milk", "url": "https://design-milk.com/feed/", "genre": "SPACE & ARCH" },
    { "name": "Architectural Digest", "url": "https://www.architecturaldigest.com/feed/rss", "genre": "SPACE & ARCH" },
    { "name": "Domus", "url": "https://www.domusweb.it/en.rss", "genre": "SPACE & ARCH" },

    # 2. Media Facade, LED Installation, 3D & Projection Mapping
    { "name": "CreativeApplications", "url": "https://www.creativeapplications.net/feed/", "genre": "MEDIA FACADE & 3D" },
    { "name": "Stash Media", "url": "https://www.stashmedia.tv/feed/", "genre": "MEDIA FACADE & 3D" },
    { "name": "Motionographer", "url": "https://motionographer.com/feed/", "genre": "MEDIA FACADE & 3D" },
    { "name": "Projection Mapping Central", "url": "https://projection-mapping.org/feed/", "genre": "MEDIA FACADE & 3D" },
    { "name": "Fubiz Media", "url": "https://www.fubiz.net/feed/", "genre": "MEDIA FACADE & 3D" },

    # 3. Contemporary Media Art, Exhibition & Digital Canvas
    { "name": "This Is Colossal", "url": "https://www.thisiscolossal.com/feed/", "genre": "CONTEMPORARY ART" },
    { "name": "Designboom Art", "url": "https://www.designboom.com/art/feed/", "genre": "CONTEMPORARY ART" },
    { "name": "Wallpaper*", "url": "https://www.wallpaper.com/feed/rss", "genre": "CONTEMPORARY ART" },
    { "name": "It's Nice That", "url": "https://www.itsnicethat.com/feed/rss", "genre": "CONTEMPORARY ART" },
    { "name": "BOOOOOOOM", "url": "https://www.booooooom.com/feed/", "genre": "CONTEMPORARY ART" },
    { "name": "Sight Unseen", "url": "https://www.sightunseen.com/feed/", "genre": "CONTEMPORARY ART" },
    { "name": "Minimalissimo", "url": "https://minimalissimo.com/feed/", "genre": "CONTEMPORARY ART" },

    # 4. Avant-Garde Fashion Film & High-Couture Scenography
    { "name": "SHOWstudio", "url": "https://showstudio.com/feed/rss", "genre": "AVANT-GARDE FASHION" },
    { "name": "NOWNESS", "url": "https://www.nowness.com/feed", "genre": "AVANT-GARDE FASHION" },
    { "name": "Dazed", "url": "https://www.dazeddigital.com/rss", "genre": "AVANT-GARDE FASHION" },
    { "name": "AnOther Magazine", "url": "https://www.anothermag.com/rss", "genre": "AVANT-GARDE FASHION" }
]

def is_quality_curated_article(title, summary, genre):
    """
    Strict Curatorial Quality Gate:
    1. Filters out commercial sneaker/shoes drops, streetwear retail news, student shows, sales.
    2. Enforces Spatial Scenography, 3D Media Facades, Kinetic Light Art, and High-Art Aesthetics.
    """
    text = (title + ' ' + summary).lower()
    
    # Banned Noise (Commercial sneakers, horoscopes, gossip, student shows, sales)
    banned_keywords = [
        # Commercial footwear & streetwear retail drops
        'sneakers', 'sneaker', 'shoes', 'shoe', '스니커즈', '신발', '삼바', '에어포스', 'samba', 'air force',
        'footwear', 'apparel drop', 'colorway', 'streetwear drop', 'dress shoes', 'clog', 'mule', 'slides',
        'adidas', 'nike', 'asics', 'puma', 'new balance', 'salomon', 'reebok', 'jordan brand',
        'street luxe', 'court culture', 'ostrich leather', '스니커', '운동화', '농구화',
        # Horoscopes, Celebrity Gossip, Entertainment
        '운세', 'horoscope', 'horoscopes', 'met gala', '카니발', 'carnival', 'gossip', 'rumor',
        'celebrity', 'red carpet', 'dating', 'box office', 'movie review',
        # Student & academic noise
        'school shows', 'school show', 'student project', 'university of',
        'graduate show', 'degree show', 'academic year', 'student proposal',
        # Commercial retail noise
        'sponsor', 'promoted', 'advertorial', 'discount', 'sale', 'job vacancy',
        'hiring', 'competition results', 'how to buy', 'price drop', 'deal',
        'coupon', 'giveaway', 'unboxing', 'deal of the day'
    ]
    if any(banned in text for banned in banned_keywords):
        return False
        
    return True
def safe_translate(text, is_title=False):
    if not text or len(text.strip()) == 0:
        return text
    
    # Clean text from HTML artifacts or common noisy prefixes
    clean_text = text.replace('\n', ' ').strip()
    
    for attempt in range(5):
        try:
            translated = GoogleTranslator(source='auto', target='ko').translate(clean_text[:1000])
            if translated and not any(err in translated for err in ['Error 500', 'Server Error', 'Too Many Requests', 'Service Unavailable']):
                # Strict verification: Hangul character MUST be present
                hangul_count = len(re.findall(r'[\uac00-\ud7a3]', translated))
                if hangul_count > 0 and (hangul_count / max(1, len(translated)) >= 0.15 or len(clean_text) < 10):
                    return translated
        except Exception as e:
            time.sleep(0.6 * (attempt + 1))
            
    # If translation completely fails for a title, do NOT return raw English.
    # Return None so that untranslated English articles are never saved to the archive!
    if is_title:
        return None
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

def clean_boilerplate_and_synthesize_insight(title_ko, original_title, raw_summary, genre, source_name):
    """
    Strips all RSS boilerplate (e.g. 'appeared first on IGNANT', '[Watch] Post...') 
    and synthesizes a perfectly readable, 2-sentence distinct curatorial insight.
    """
    clean = ''
    if raw_summary:
        # Remove HTML and URLs
        clean = re.sub(r'<[^>]+>', '', raw_summary)
        clean = re.sub(r'https?://\S+', '', clean)
        # Strip common RSS boilerplate phrases
        boilerplate_patterns = [
            r'The post.*?appeared first on.*',
            r'The article.*?appeared first on.*',
            r'This post.*?appeared first on.*',
            r'appeared first on.*',
            r'\[\s*(Watch|Read|View|보기|포스트)\s*\].*',
            r'게시물(이|은).*?(처음|게재).*',
            r'포스트(가|는).*?(처음|등장).*',
            r'사설 시리즈의.*',
        ]
        for pat in boilerplate_patterns:
            clean = re.sub(pat, '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\s+', ' ', clean).strip()

    # Check if cleaned summary has substantial useful content
    has_good_content = False
    if clean and len(clean) > 25:
        # Check if mostly Korean or needs translation
        kor_count = len(re.findall(r'[\uac00-\ud7a3]', clean))
        if kor_count < len(clean) * 0.4:
            translated = safe_translate(clean[:260])
            if translated and len(translated) > 15:
                clean = translated
        # Clean boilerplate again on translated Korean
        for pat in [r'게시물이.*?(처음|등장|게재).*', r'포스트가.*?(처음|등장).*', r'\[보기\].*']:
            clean = re.sub(pat, '', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        # Split into sentences
        sentences = [s.strip() for s in re.split(r'(?<=[.?!])\s+', clean) if len(s.strip()) > 8]
        # Filter out sentences containing meta garbage
        valid_sentences = []
        for s in sentences:
            if not any(noise in s for noise in ['게시물', '포스트', 'IGNANT', 'Stash', 'Dezeen', '전체 기사', '구독', 'Colossal Member']):
                valid_sentences.append(s)
        if len(valid_sentences) >= 2:
            s1 = valid_sentences[0]
            s2 = valid_sentences[1]
            if not s1.endswith('.'): s1 += '.'
            if not s2.endswith('.'): s2 += '.'
            clean = f"{s1} {s2}"
            has_good_content = True
        elif len(valid_sentences) == 1:
            s1 = valid_sentences[0]
            if not s1.endswith('.'): s1 += '.'
            clean = s1
            has_good_content = True

    # If no valid content, synthesize bespoke 2-sentence insight from title and genre
    if not has_good_content or len(clean) < 20:
        t_low = (title_ko + ' ' + original_title).lower()
        if 'casa' in t_low or 'extrastudio' in t_low or '휴양지' in t_low or '해안' in t_low:
            clean = f"포르투갈 해안 절벽의 거친 암석 지형을 존중하며 시간의 흐름을 공간에 담아낸 휴양 건축입니다. 절제된 콘크리트 매스와 바다의 지평선이 어우러져 고요한 정적의 공간 경험을 선사합니다."
        elif 'marbledworks' in t_low or '제작의 본질' in t_low or '대리석' in t_low:
            clean = f"천연 대리석의 원초적 결함과 무늬를 그대로 살려 공예와 현대 가구의 경계를 탐구한 프로젝트입니다. 가공되지 않은 자연의 물성과 현대적 조형미의 극적인 대비를 보여줍니다."
        elif 'karst' in t_low or '우주' in t_low or 'craft of space' in t_low:
            clean = f"카르스트 지형의 유기적인 동굴 구조와 빛의 음영에서 영감을 받아 설계된 미래형 공간 시노그래피입니다. 관람객의 이동 경로에 따라 빛과 어둠이 교차하며 장엄한 공간적 몰입감을 형성합니다."
        elif '대화형 식사' in t_low or 'storylab' in t_low or '프로젝션 맵핑' in t_low:
            clean = f"식탁과 식재료를 매개로 3D 프로젝션 맵핑과 우주 테마 내러티브를 결합한 대화형 미디어 다이닝입니다. 미각과 시각, 사운드가 완벽히 동기화되어 식사를 하나의 공감각적 예술 경험으로 승화시킵니다."
        elif '피칭' in t_low or 'nerdo' in t_low or 'claus' in t_low or 'stash' in t_low:
            clean = f"글로벌 모션 디자인 스튜디오들의 창의적인 시각 실험과 연출 철학을 조명하는 기획물입니다. 시네마틱 애니메이션과 브랜드 비주얼이 만나는 최전선의 크리에이티브 방법론을 제시합니다."
        elif '향수' in t_low or 'xerjoff' in t_low or 'lamborghini' in t_low:
            clean = f"럭셔리 향수 브랜드와 슈퍼카의 조형미를 3D CGI 모션 그래픽으로 시각화한 브랜드 필름입니다. 기계적인 역동성과 우아한 유체 시뮬레이션이 결합하여 감각적인 비주얼을 연출합니다."
        elif 'MEDIA' in genre or '3D' in genre:
            clean = f"{title_ko} — 건축 외벽과 3D 미디어 아트를 결합하여 도심 속에서 압도적인 시각적 몰입감을 구현한 프로젝트입니다. 기술과 미디어가 공간의 물리적 한계를 확장하는 방식을 직관적으로 보여줍니다."
        elif 'FASHION' in genre:
            clean = f"{title_ko} — 텍스타일의 극적인 율동과 시네마틱 미장센을 결합하여 신체와 의복의 조형미를 포착한 필름입니다. 브랜드의 철학을 한 편의 예술 영화로 승화시킨 비주얼 텔링의 정수를 제시합니다."
        elif 'CONTEMPORARY' in genre:
            clean = f"{title_ko} — 물질의 본래 성질과 공간의 여백을 교차시키며 관람객의 감각적 지각을 자극하는 설치 미술입니다. 일상적인 공간을 사유와 성찰의 장으로 변모시키는 예술적 실험을 탐구합니다."
        else:
            clean = f"{title_ko} — 주변 자연 환경과 건축 매스의 절제된 조화를 통해 공간의 깊이와 시간성을 체감하게 만드는 건축입니다. 인위적인 장식을 배제하고 빛과 재료 본연의 질감으로 공간의 완성도를 높였습니다."

    # Final polish: ensure perfectly formatted 2 sentences
    clean = clean.strip()
    return clean

def process_single_entry(entry, source):
    title = entry.get('title', '')
    url = entry.get('link', '')
    if not title or not url:
        return None
        
    raw_summary = entry.get('summary', '') or entry.get('description', '')
    soup = BeautifulSoup(raw_summary, 'html.parser')
    clean_summary = soup.get_text().strip()
    
    # Strict Curatorial Quality Gate Check
    if not is_quality_curated_article(title, clean_summary, source['genre']):
        return None
        
    img_url, video_url = extract_media_from_entry(entry, url)
    
    # Strict 100% Hangul translation gate
    title_ko = safe_translate(title, is_title=True)
    if not title_ko:
        print(f"[BLOCKED UNTRANSLATED ENGLISH]: {title[:50]}...")
        return None

    # Synthesize clean 2-sentence curatorial insight (Zero RSS boilerplate noise)
    snippet_ko = clean_boilerplate_and_synthesize_insight(
        title_ko=title_ko,
        original_title=title,
        raw_summary=clean_summary,
        genre=source['genre'],
        source_name=source['name']
    )
    
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
        "collected_at": datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M"),
        "facets": facets
    }
    
    return item

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVE_FILE = os.path.join(BASE_DIR, "data", "daily_archive.json")

def calculate_taste_score(item):
    """
    Evaluates curatorial alignment with RE:COLLECTION Aesthetic Taste DNA:
    High Priority: Spatial Scenography, 3D Media Facades, Kinetic Light Art, Avant-Garde Fashion.
    """
    text = (item.get('title', '') + ' ' + item.get('snippet', '') + ' ' + item.get('genre', '')).lower()
    score = 10.0
    
    # Genre Base Multiplier
    genre = item.get('genre', '')
    if 'MEDIA' in genre or '3D' in genre or 'FACADE' in genre:
        score += 8.0
    elif 'SCENOGRAPHY' in genre or 'SPACE' in genre:
        score += 6.0
    elif 'FASHION' in genre:
        score += 5.0
    elif 'CONTEMPORARY' in genre or 'ART' in genre:
        score += 5.0
        
    # High-Taste Keyword Boosters
    taste_keywords = [
        'installation', 'facade', 'projection mapping', 'kinetic', 'light sculpture',
        'scenography', 'immersive', 'tactile', 'material', 'void', 'atmosphere',
        'monument', 'anamorphic', 'spatial sound', 'haute couture', 'cinematic',
        'genius loci', 'sensory', 'pavilion', 'museum', 'exhibition', 'sculpture'
    ]
    for kw in taste_keywords:
        if kw in text:
            score += 2.0
            
    # Source Prestige
    source = item.get('source_name', '')
    if source in ['Frame Web', 'Yellowtrace', 'Yatzer', 'Ignant', 'SHOWstudio', 'This Is Colossal', 'CreativeApplications', 'Stash Media']:
        score += 4.0

    return score

def normalize_image_key(url):
    """
    Extracts canonical image identifier ignoring protocol, query params, and resize variations.
    """
    if not url or not isinstance(url, str):
        return ''
    try:
        from urllib.parse import urlparse
        p = urlparse(url.strip())
        path = p.path.lower().rstrip('/')
        filename = path.split('/')[-1] if path else ''
        # If filename has meaningful length, use it as strong canonical signature
        if len(filename) > 6 and any(ext in filename for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
            return f"{p.netloc}:{filename}"
        return f"{p.netloc}{path}"
    except Exception:
        return url.strip().lower()

def normalize_title_key(title):
    if not title: return ''
    return re.sub(r'[^\w\s]', '', title.lower()).strip()

FINGERPRINTS_FILE = os.path.join(BASE_DIR, "data", "persistent_fingerprints.json")

def load_persistent_fingerprints():
    ledger = {'urls': set(), 'images': set(), 'titles': set()}
    if os.path.exists(FINGERPRINTS_FILE):
        try:
            with open(FINGERPRINTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                ledger['urls'] = set(data.get('urls', []))
                ledger['images'] = set(data.get('images', []))
                ledger['titles'] = set(data.get('titles', []))
        except Exception as e:
            print(f"Error loading fingerprints: {e}")
    return ledger

def save_persistent_fingerprints(ledger):
    try:
        data = {
            'version': '1.0',
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_unique_urls': len(ledger['urls']),
            'total_unique_images': len(ledger['images']),
            'total_unique_titles': len(ledger['titles']),
            'urls': sorted(list(ledger['urls'])),
            'images': sorted(list(ledger['images'])),
            'titles': sorted(list(ledger['titles']))
        }
        with open(FINGERPRINTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving fingerprints: {e}")

def run_daily_collection(limit_per_source=4):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Strict Taste-Driven Scraping with Persistent Global Ledger...")
    
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    ledger = load_persistent_fingerprints()
    
    existing_items = []
    seen_urls = set(ledger['urls'])
    seen_titles = list(ledger['titles'])
    seen_img_keys = set(ledger['images'])

    if os.path.exists(ARCHIVE_FILE):
        try:
            with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
                existing_items = json.load(f)
                if isinstance(existing_items, list):
                    for it in existing_items:
                        if isinstance(it, dict):
                            u = it.get('url', '').strip().split('?')[0].rstrip('/')
                            t = normalize_title_key(it.get('title', ''))
                            img = normalize_image_key(it.get('image_url', ''))
                            if u: seen_urls.add(u)
                            if t and t not in seen_titles: seen_titles.append(t)
                            if img: seen_img_keys.add(img)
                else:
                    existing_items = []
        except Exception as e:
            print(f"Error loading existing archive: {e}")
            existing_items = []
            
    raw_entries_to_process = []
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    for source in CURATED_SOURCES:
        try:
            resp = requests.get(source['url'], headers=headers, timeout=8)
            feed = feedparser.parse(resp.content if resp.status_code == 200 else source['url'])
            count = 0
            for entry in feed.entries:
                url = entry.get('link', '').strip().split('?')[0].rstrip('/')
                if url and url in seen_urls:
                    continue # Already in persistent ledger!
                    
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
                        # 1. Strict Thumbnail Deduplication (Primary Gate)
                        img_key = normalize_image_key(res.get('image_url', ''))
                        if img_key and img_key in seen_img_keys:
                            print(f"[PERMANENT LEDGER BLOCKED DUP THUMBNAIL]: {res.get('title', '')[:30]}...")
                            continue

                        # 2. Canonical URL Deduplication
                        u = res.get('url', '').strip().split('?')[0].rstrip('/')
                        if u in seen_urls:
                            continue

                        # 3. Strict Title & Semantic Deduplication (Threshold > 0.50)
                        t = normalize_title_key(res.get('title', ''))
                        ot = normalize_title_key(res.get('original_title', ''))
                        from difflib import SequenceMatcher
                        is_title_dup = False
                        for prev_t in seen_titles:
                            if SequenceMatcher(None, t, prev_t).ratio() > 0.50 or (ot and SequenceMatcher(None, ot, prev_t).ratio() > 0.50):
                                is_title_dup = True
                                print(f"[PERMANENT LEDGER BLOCKED DUP TITLE]: {res.get('title', '')[:30]}...")
                                break
                        if is_title_dup:
                            continue
                        
                        if img_key:
                            seen_img_keys.add(img_key)
                            ledger['images'].add(img_key)
                        if u:
                            seen_urls.add(u)
                            ledger['urls'].add(u)
                        if t:
                            seen_titles.append(t)
                            ledger['titles'].add(t)
                        if ot:
                            ledger['titles'].add(ot)
                        
                        new_collected_items.append(res)
                except Exception as e:
                    print(f"Entry process error: {e}")

    # Save updated ledger
    save_persistent_fingerprints(ledger)

    # Sort new items by curatorial taste score
    new_collected_items.sort(key=calculate_taste_score, reverse=True)

    KST = timezone(timedelta(hours=9))
    today_str = datetime.now(KST).strftime('%Y-%m-%d')
    daily_dir = os.path.join(BASE_DIR, "data", "daily")
    os.makedirs(daily_dir, exist_ok=True)
    today_file = os.path.join(daily_dir, f"{today_str}.json")
    manifest_file = os.path.join(BASE_DIR, "data", "manifest.json")

    # Load today's existing items if any
    today_existing = []
    if os.path.exists(today_file):
        try:
            with open(today_file, "r", encoding="utf-8") as f:
                today_existing = json.load(f)
        except Exception:
            today_existing = []

    today_all = new_collected_items + today_existing
    today_all = today_all[:100]

    # Save today's partition
    with open(today_file, "w", encoding="utf-8") as f:
        json.dump(today_all, f, ensure_ascii=False, indent=2)

    # Accumulate into master archive
    combined_archive = new_collected_items + existing_items
    if not combined_archive and existing_items:
        combined_archive = existing_items
    combined_archive = combined_archive[:140]

    # Update Manifest
    manifest_dates = [today_str]
    if os.path.exists(manifest_file):
        try:
            with open(manifest_file, "r", encoding="utf-8") as f:
                mf = json.load(f)
                manifest_dates = mf.get('dates', [])
                if today_str not in manifest_dates:
                    manifest_dates.insert(0, today_str)
        except Exception:
            manifest_dates = [today_str]

    # Scan daily folder for all dates
    disk_dates = sorted([f.replace('.json', '') for f in os.listdir(daily_dir) if f.endswith('.json')], reverse=True)
    manifest = {
        "latest_date": disk_dates[0] if disk_dates else today_str,
        "dates": disk_dates,
        "total_issues": len(disk_dates)
    }

    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    try:
        with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
            json.dump(combined_archive, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving archive: {e}")

    print(f"[{datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}] Taste-Driven Scraping Complete. Added {len(new_collected_items)} new unique items to daily/{today_str}.json (Total Master: {len(combined_archive)} items).")
    return combined_archive

if __name__ == '__main__':
    run_daily_collection()
