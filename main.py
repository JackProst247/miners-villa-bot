import os
import json
import time
import re
import requests
from pathlib import Path
from urllib.parse import quote
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types


# =========================================================
# .env
# =========================================================

load_dotenv()

VERIFY_TOKEN = os.getenv(
    "VERIFY_TOKEN",
    "miners_villa_secret_123"
)

META_PAGE_ACCESS_TOKEN = os.getenv(
    "META_PAGE_ACCESS_TOKEN"
)

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY"
)

IMAGE_BASE_URL = os.getenv(
    "IMAGE_BASE_URL",
    ""
).rstrip("/")

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.7-flash"
)


# =========================================================
# APP + PHOTO FOLDER
# =========================================================

app = FastAPI(
    title="Miners Villa Messenger Bot"
)

BASE_DIR = Path(__file__).resolve().parent
PHOTO_FOLDER = BASE_DIR / "photo"
PHOTO_FOLDER.mkdir(parents=True, exist_ok=True)

app.mount(
    "/photo",
    StaticFiles(directory=str(PHOTO_FOLDER)),
    name="photo",
)


# =========================================================
# IMAGE LIBRARY
# =========================================================

IMAGE_LIBRARY = {
    "GENERAL_PLAN": "general_plan",
    "GREEN_GARDEN": "Green_garden",
    "LANDSCAPING": "landscaping",
    "RELAXATION_AREA": "relaxation_area",
    "SPORTS_AREA_0_5": "sports_area_0-5",
    "SPORTS_AREA_9_13": "sports_area_9-13",
    "SPORTS_AREA_13_16": "sports_area_13-16",
    "SPORTS_AREA_PLAN": "sports_area_plan",
    "MULT": "mult",
    "MULT_PARKING_SPACE": "mult_parking_space",
    "MULT_PARKING_SPACE_1": "mult_parking_space_1",
    "MULT_100": "mult_100",
    "MULT_116": "mult_116",
    "MULT_120": "mult_120",
    "MULT_125": "mult_125",
    "MULT_126": "mult_126",
    "MULT_126_32": "mult_126_32",
    "MULT_136": "mult_136",
    "MULT_178": "mult_178",
    "MULT_189": "mult_189",
    "MULT_189_64": "mult_189_64",
    "MULT_192": "mult_192",
    "MULT_198": "mult_198",
    "TOWNHOUSE_212": "townhouse_212",
    "TOWNHOUSE_212_1": "townhouse_212_1",
    "TOWNHOUSE_266": "townhouse_266",
    "TOWNHOUSE_266_1": "townhouse_266_1",
}

IMAGE_KEYS = list(IMAGE_LIBRARY.keys())


# =========================================================
# CONVERSATION MEMORY
# =========================================================

CONVERSATIONS: Dict[str, List[Dict[str, str]]] = {}
MAX_HISTORY = 8


# =========================================================
# MINERS VILLA DATA
# =========================================================

PROJECT_NAME = "Miners Villa"
PRICE_MIN = 5_500_000
PRICE_MAX = 5_800_000
SALES_PHONE = "9430-7017"

SALES_OFFICE = (
    "Эрдэнэт хот, 1/16-р байрны зүүн урд буланд, "
    "төв зам дагуу"
)

LOCATION_TEXT = (
    "Баян-Өндөр уулын зүүн энгэрт, "
    "Бүсийн оношилгооны төвийн ард, "
    "Медипас эмнэлгийн ард, 30.8 га талбайд"
)

PAYMENT_TEXT = (
    "30% урьдчилгаа, 40% явцын төлбөр, "
    "20% явцын төлбөр, 10% түлхүүр гардуулах үед төлнө."
)

PARKING_TEXT = (
    "Мульт хаусын Б1 болон 1-р давхарт нэгдсэн дуلاан зогсоол байрлана. "
    "Зогсоолын үнэ 50,000,000 ₮."
)

UNKNOWN_TEXT = (
    "Энэ асуултад тохирох мэдээлэл байхгүй байна. Та манай ажилтантай холбогдож лавлаарай. "
    "Манай борлуулалтын албатай 9430-7017 дугаараар холбогдоорой 😊"
)


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
ТА БОЛ "МИНА" — MINERS VILLA ТӨСЛИЙН 23 НАСТАЙ,
ЭЕЛДЭГ, ЗӨӨЛӨН, ТУСЧ БОРЛУУЛАГЧ.

ЗОРИЛГО:
* Miners Villa-ийн талаар үнэн зөв мэдээлэл өгөх.
* Богино, ойлгомжтой, хүнтэй ярилцаж байгаа мэт хариулах.
* Монгол хэлээр хариулах.
* Хэрэглэгчийн асуултыг уртаар давтахгүй.
* Хэт робот шиг бичихгүй.
* Худал мэдээлэл зохиохгүй.

ҮНДСЭН МЭДЭЭЛЭЛ:
* Төслийн нэр: Miners Villa
* М² үнэ: 5,500,000 - 5,800,000 ₮
* Борлуулалтын утас: 9430-7017
* Борлуулалтын оффис: Эрдэнэт хот, 1/16-р байрны зүүн урд буланд, төв зам дагуу.

ТӨЛБӨРИЙН НӨХЦӨЛ:
* 30% урьдчилгаа, 40% явцын төлбөр, 20% явцын төлбөр, 10% түлхүүр гардуулах үед
* Явцын төлбөрт зөвхөн байрны бартер сонсоно.
* Машин, газар, бизнесийн бартер зөвшөөрсөн гэж хэлж болохгүй.

СИНГЛ БОЛОН ТВИН ХАУС:
* Сингл хаус болон Твин хаусын борлуулалт дууссан.
* Хэрэглэгч асуувал борлуулалт нь дууссан гэж хэлээд одоо байгаа Таун хаус болон Мульт хаусыг санал болгоно.

ТАУН ХАУС:
* Талбайн сонголт: 213.33 м², 267.48 м²
* Онцлог шинж: Бие даасан орон зайг бүрэн хангасан, хувийн эдэлбэр газар болон хувийн гараж бүхий тансаг зэрэглэлийн хаус.

МУЛЬТ ХАУС:
* A — 126 м², B — 125.21 м², C — 192.25 м², D — 189.64 м²
* F — 136.42 м², G — 178.39 м², H — 198.52 м², I — 189.52 м²
* Онцлог шинж: Орон сууцны ашигтай тал болон хаусын тав тухтай орчныг хослуулсан орчин үеийн шинэлэг төлөвлөлт.
* Мульт хаус асуух үед заавал эхлээд ямар м² сонголт сонирхож байгааг асууна.
* Зураг илгээхдээ ерөнхий MULT зурагтай тухайн сонирхсон загварын зургийг хамт илгээнэ.

ДУЛААН ЗОГСООЛ:
* Мульт хаусын Б1 болон 1-р давхарт нэгдсэн дулаан зогсоол байрлана. Үнэ: 50,000,000 ₮.

БАЙРШИЛ:
* Баян-Өндөр уулын зүүн энгэрт, Бүсийн оношилгооны төвийн ард, Медипас эмнэлгийн ард, 30.8 га талбайд.

БАРИЛГЫН АЖИЛ:
* 2026 оны өвөл гэхэд дотоод заслын ажлыг эхлүүлэхээр ажиллаж байна.
* 7 хоног бүрийн 1 дэх өдөр Facebook Page болон Instagram дээр Reel хэлбэрээр шинэчилж хүргэдэг.

ЗУРГИЙН ДҮРЭМ:
Gemini зөвхөн IMAGE KEY буцаана. Хамгийн ихдээ 4 хүртэлх KEY буцаана.
Зөвшөөрөгдсөн IMAGE KEY:
""" + "\n".join(f"- {k}" for k in IMAGE_KEYS)


# =========================================================
# ENVIRONMENT
# =========================================================

def check_environment():
    missing = []
    if not META_PAGE_ACCESS_TOKEN:
        missing.append("META_PAGE_ACCESS_TOKEN")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not IMAGE_BASE_URL:
        print("WARNING: IMAGE_BASE_URL тохируулаагүй байна.")
    if missing:
        print("WARNING: .env дотор дутуу хувьсагч:", ", ".join(missing))

check_environment()

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


# =========================================================
# HELPERS
# =========================================================

def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    
    # Латин галиг болон крилл үсгийн хөрвүүлэлт
    replacements = {
        "ё": "е",
        "өү": "оу",
        "ү": "у",
        "ө": "о",
        "v": "u",  # vne -> une, vniin -> uniin, vnetei -> unetei
        "w": "v",  # ywts -> yvts
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
        
    # Нийтлэг ашигладаг товчлолуудыг бүтэн үг болгох
    word_replacements = {
        "mdll": "medeelel",
        "mdlel": "medeelel",
        "mdeelel": "medeelel",
        "brshil": "bairshil",
        "tlbur": "tulbur",
        "zgsol": "zogsool",
        "uts": "utas",
    }
    words = text.split()
    normalized_words = [word_replacements.get(w, w) for w in words]
    text = " ".join(normalized_words)

    text = re.sub(r"\s+", " ", text).strip()
    return text


def match_any(keywords: List[str], normalized_text: str) -> bool:
    return any(normalize_text(kw) in normalized_text for kw in keywords)


def resolve_photo_file(stem: str) -> Optional[Path]:
    exact_matches = list(PHOTO_FOLDER.glob(stem + ".*"))
    if exact_matches:
        return exact_matches[0]
    return None


def get_public_image_url(filename: str) -> str:
    if not IMAGE_BASE_URL:
        raise RuntimeError("IMAGE_BASE_URL тохируулаагүй байна.")
    encoded_filename = quote(filename, safe="")
    return f"{IMAGE_BASE_URL}/{encoded_filename}"


def add_to_history(sender_id: str, role: str, text: str):
    history = CONVERSATIONS.setdefault(sender_id, [])
    history.append({"role": role, "text": text})
    if len(history) > MAX_HISTORY:
        del history[:-MAX_HISTORY]


def history_text(sender_id: str) -> str:
    history = CONVERSATIONS.get(sender_id, [])
    if not history:
        return "Өмнөх яриа байхгүй."
    return "\n".join(f"{item['role']}: {item['text']}" for item in history)


# =========================================================
# DIRECT IMAGE ROUTER
# =========================================================

def direct_image_router(user_text: str, sender_id: str = "") -> Optional[List[str]]:
    t = normalize_text(user_text)

    # 1. Зогсоолын зургууд
    parking_kws = [
        "зогсоол", "дулаан зогсоол", "машины зогсоол", "б1 зогсоол", "нэгдсэн зогсоол",
        "zogsool", "garaash", "b1", "гараж", "гараш", "гарааш", "garaj", "garash",
        "dulaan zogsool", "mashinii zogsool", "1 davhar", "1давхар", "1-р давхар"
    ]
    if match_any(parking_kws, t):
        if match_any(["план", "төлөвлөлт", "plan"], t):
            return ["MULT_PARKING_SPACE"]
        if match_any(["харагдах", "гадаад", "үзэмж", "uzemj"], t):
            return ["MULT_PARKING_SPACE_1"]
        return ["MULT_PARKING_SPACE", "MULT_PARKING_SPACE_1"]

    # 2. Таун хаус тусгай хэмжээний зургууд
    if match_any(["267", "266"], t):
        return ["TOWNHOUSE_266", "TOWNHOUSE_266_1"]

    if match_any(["213", "212"], t):
        return ["TOWNHOUSE_212", "TOWNHOUSE_212_1"]

    # 3. Таун хаус ерөнхий зургууд (Бүх төрлийн бичлэгүүд)
    townhouse_kws = [
        "таун хаус", "таунхаус", "таун", "taun", "townhouse", "town house",
        "таун-хаус", "taunhaus", "taun haus", "taun havs", "town-house", "town", "tawn"
    ]
    if match_any(townhouse_kws, t):
        if not match_any(["212", "213", "266", "267"], t):
            return ["TOWNHOUSE_212", "TOWNHOUSE_212_1", "TOWNHOUSE_266", "TOWNHOUSE_266_1"]

    # 4. Мульт хаус тусгай хэмжээний зургууд (Сонирхсон загварыг ерөнхий MULT зурагтай хамт)
    mult_image_map = {
        "126.32": "MULT_126_32", "126,32": "MULT_126_32", "126": "MULT_126",
        "125.21": "MULT_125", "125,21": "MULT_125", "120.85": "MULT_120",
        "120,85": "MULT_120", "116": "MULT_116", "100.77": "MULT_100",
        "100,77": "MULT_100", "136.42": "MULT_136", "136,42": "MULT_136",
        "178.39": "MULT_178", "178,39": "MULT_178", "189.64": "MULT_189_64",
        "189,64": "MULT_189_64", "189.52": "MULT_189", "189,52": "MULT_189",
        "192.25": "MULT_192", "192,25": "MULT_192", "198.52": "MULT_198",
        "198,52": "MULT_198",
    }
    mult_kws = [
        "мульт", "мульт хаус", "мультхаус", "mult", "multhouse", "mult house",
        "мулт", "мултхаус", "мулт хаус", "mult-house", "mult havs"
    ]
    if match_any(mult_kws, t):
        for size, key in mult_image_map.items():
            if size in t:
                return ["MULT", key]

    # 5. Мульт хаус ерөнхий асуух үед (Зөвхөн ерөнхий MULT зураг)
    if match_any(mult_kws, t):
        mult_sizes = ["100", "116", "120", "125", "126", "136", "178", "189", "192", "198"]
        if not match_any(mult_sizes, t):
            return ["MULT"]

    # 6. Ногоон байгууламж, орчин, тохижилт
    greenery_kws = [
        "ногоон", "ногоон байгууламж", "ногоон цэцэрлэг", "ногоон орчин", "тохижилт", "гадна тохижилт",
        "амрах талбай", "амралтын талбай", "спортын талбай", "хүүхдийн талбай",
        "nogoon", "nogoon baiguulamj", "tohijilt", "gadna tohijilt", "landscaping", 
        "amrah talbai", "sport", "sport talbai", "huuhdiin talbai",
        "цэцэрлэг", "мод", "зүлэг", "тоглоомын талбай", "togloomyn talbai", "huuhdiin togloom", 
        "tsetserleg", "mod", "zuleg", "gadna orchin", "orchin", "sagsnii talbai"
    ]
    if match_any(greenery_kws, t):
        if match_any(["0-5", "0 5", "0-5 нас"], t):
            return ["SPORTS_AREA_0_5"]
        if match_any(["9-13", "9 13", "9-13 нас"], t):
            return ["SPORTS_AREA_9_13"]
        if match_any(["13-16", "13 16", "13-16 нас"], t):
            return ["SPORTS_AREA_13_16"]
        
        return ["GREEN_GARDEN", "LANDSCAPING", "SPORTS_AREA_PLAN", "RELAXATION_AREA"]

    # 7. Ерөнхий төлөвлөгөө
    general_keywords = [
        "талбайн зураг", "талбай зураг", "ерөнхий төлөвлөгөө", "ерөнхий план",
        "план зураг", "план", "төлөвлөлтийн зураг", "төлөвлөлт зураг",
        "хотхоны зураг", "хотхон зураг", "нийт зураг", "plan", "talbai",
        "хотхоны зохион байгуулалт", "eponhii plan", "hothon", "hothony zurag", 
        "yurunhii tuluvluguu", "yurunhii plan"
    ]
    if match_any(general_keywords, t):
        if not match_any(["таун", "мульт", "зогсоол", "спорт", "тоглоом", "ногоон", "тохижилт", "амрах", "taun", "mult", "zogsool"], t):
            return ["GENERAL_PLAN"]

    # 8. Ярианы түүхээс зураг таньж илгээх
    photo_only_kws = [
        "зураг", "зураг үзье", "зураг харья", "зураг явуул", "зураг илгээ", "зургаа", "зургийг",
        "zurag", "zurag uzei", "zurag uzye", "zurag harya", "zurag yavuul", "zurag ilgee", "zuraguu", 
        "zuragaa", "photo", "zurag n"
    ]
    if match_any(photo_only_kws, t):
        hist_text = normalize_text(history_text(sender_id))
        if match_any(["таун", "townhouse", "taun", "town house"], hist_text):
            if "266" in hist_text or "267" in hist_text:
                return ["TOWNHOUSE_266", "TOWNHOUSE_266_1"]
            if "212" in hist_text or "213" in hist_text:
                return ["TOWNHOUSE_212", "TOWNHOUSE_212_1"]
            return ["TOWNHOUSE_212", "TOWNHOUSE_212_1", "TOWNHOUSE_266", "TOWNHOUSE_266_1"]
        if match_any(["мульт", "mult", "мулт"], hist_text):
            return ["MULT"]
        if match_any(["зогсоол", "гарааш", "zogsool", "garaj"], hist_text):
            return ["MULT_PARKING_SPACE", "MULT_PARKING_SPACE_1"]
        
        return ["GENERAL_PLAN"]

    return None


# =========================================================
# DIRECT FAQ ROUTER
# =========================================================

def direct_faq_router(user_text: str, sender_id: str = "") -> Optional[str]:
    t = normalize_text(user_text)

    # 1. Мэндчилгээ
    greetings = [
        "сайн уу", "сайн байна уу", "сайн байнуу", "байна уу", "hello", "hi", "hey", "сайн",
        "sain uu", "sain bainuu", "sain bainguu", "sainbainuu", "sain",
        "snu", "snuu", "snuuu", "sn uu", "sn u", "u bn", "u baina", "uu bn", "sain u",
        "өглөөний мэнд", "өдрийн мэнд", "оройн мэнд", "mends", "mend", "helloo", "hiii", 
        "uglooni mend", "udriin mend", "oroin mend"
    ]
    if match_any(greetings, t) and len(t.split()) <= 4 and not match_any(["үнэ", "une", "vne", "утас", "utas", "байршил", "bairshil", "ywts", "yvts"], t):
        return (
            "Сайн байна уу? 😊 "
            "Miners Villa төслийн талаар үнэ, "
            "төлөвлөлт, төлбөрийн нөхцөл болон "
            "байршлын мэдээлэл өгөхөд бэлэн байна."
        )

    # 2. Зөвхөн "Зураг үзье"
    photo_only_kws = [
        "зураг", "зураг үзье", "зураг харья", "зураг явуул", "зураг илгээ", "зургаа", "зургийг",
        "zurag", "zurag uzei", "zurag uzye", "zurag harya", "zurag yavuul", "zurag ilgee", "zuraguu", 
        "zuragaa", "photo", "zurag n"
    ]
    if match_any(photo_only_kws, t) and len(t.split()) <= 3:
        return "Мэдээж, холбогдох зургуудыг илгээж байна 😊"

    # 3. Үнэ
    price_keywords = [
        "үнэ", "үнийн", "үнэтэй", "м2 үнэ", "м2", "мкв үнэ", "1м2", "1 м2",
        "квадратын үнэ", "квадрат үнэ", "үнэ хэд", "үнэ хэд вэ", "хэдэн төгрөг",
        "унэ", "унийн", "une", "uniin", "unetei", "m2 une", "mkv une", "une xed", "une hed", "heden togrog",
        "vne", "vniin", "vnetei", "vne xed", "vne hed", "une mdll", "vne mdll", "vne medeelel", "une medeelel",
        "үнэ өртөг", "хэд вэ", "hed ve", "hed be", "xed we", "xed be", "hemjee une", "une n hed ve", 
        "үнэ нь хэд вэ", "un n hed ve", "une n xed"
    ]
    if match_any(price_keywords, t):
        if not match_any(["сонголт", "songolt", "хэмжээ", "hemjee", "ямар ямар", "yamar"], t) or match_any(["үнэ", "une", "vne"], t):
            return (
                "Одоогийн м² үнэ 5,500,000–5,800,000 ₮ байна. "
                "Дэлгэрэнгүй болон сонголтын тодорхой үнийг "
                f"борлуулалтын албаны {SALES_PHONE} дугаараас лавлаарай 😊"
            )

    # 4. Утас
    phone_keywords = [
        "утас", "дугаар", "холбогдох", "утасны дугаар", "холбоо барих", "залгах",
        "utas", "dugaar", "holbogdoh", "utasny dugaar", "zalgax", "zalgah", "uts", "utsnii dugaar",
        "холбогдох дугаар", "утас хэд вэ", "utas hed ve", "utas xed we", "zalgah dugaar", "utasnii dugaar"
    ]
    if match_any(phone_keywords, t) and not match_any(["оффис", "office"], t):
        return f"Манай борлуулалтын утас: {SALES_PHONE} 😊"

    # 5. Оффис
    office_keywords = [
        "оффис", "хаяг", "оффисын хаяг", "оффис хаана",
        "office", "hayag", "offis", "offis haana",
        "оффис хаана вэ", "хаяг хаана вэ", "hayag haana ve", "offis haana ve", "haana ochihiin", "ochih"
    ]
    if match_any(office_keywords, t):
        return f"Борлуулалтын оффис: {SALES_OFFICE}. Утас: {SALES_PHONE} 😊"

    # 6. Байршил
    location_keywords = [
        "байршил", "байрлал", "хаана байдаг", "хаана вэ", "хаана байрладаг", "хаана байрлах", "хотын хаана",
        "bairshil", "bairlal", "haana baidag", "haana ve", "haana bairladag", "haana", "brshil",
        "байршил хаана вэ", "haana bairlaj baigaa ve", "haana bairlah ve", "bairlal haana ve", "bairshil n"
    ]
    if match_any(location_keywords, t):
        return f"Miners Villa нь {LOCATION_TEXT}. Дэлгэрэнгүй мэдээллийг {SALES_PHONE} дугаараас лавлаарай 😊"

    # 7. Төлбөрийн нөхцөл
    payment_keywords = [
        "төлбөр", "төлбөрийн нөхцөл", "төлөлтийн нөхцөл", "хэрхэн төлөх", "яаж төлөх", "урьдчилгаа", "хэдэн хувь",
        "tulbur", "tulburiin noktsol", "urdchilgaa", "yaj tuloh", "xedhen huv", "tlbur",
        "төлбөрийн графиг", "tolbor", "tulbur n", "tolboriin nohtsol", "yavtsiin tolbor", "yavc tolbor", 
        "yavtsyn tolbor", "urdchilgaa hed", "urdchilgaa heden"
    ]
    if match_any(payment_keywords, t) and not match_any(["бартер", "barter"], t):
        return f"Төлбөрийн нөхцөл: {PAYMENT_TEXT} Явцын төлбөрт зөвхөн байрны бартер сонсоно."

    # 8. Бартер
    barter_keywords = [
        "бартер", "байраар", "машинаар", "газраар", "barter", "bairaar", "mashinaar", "gazraar",
        "бартер хийх үү", "barter hiih uu", "barterd", "barterlah", "oroltsuulah"
    ]
    if match_any(barter_keywords, t):
        if match_any(["машин", "машинаар", "mashin", "mashinaar"], t):
            return "Явцын төлбөрт зөвхөн байрны бартер сонсоно. Машины бартер зөвшөөрөхгүй."
        if match_any(["газар", "газраар", "gazar", "gazraar"], t):
            return "Явцын төлбөрт зөвхөн байрны бартер сонсоно. Газрын бартер зөвшөөрөхгүй."
        return "Явцын төлбөрт зөвхөн байрны бартер сонсоно. Машин, газар, бизнесийн бартер зөвшөөрөхгүй."

    # 9. Зогсоол (Б1 болон 1-р давхарт)
    parking_keywords = [
        "зогсоол", "гарааш", "б1", "дулаан зогсоол", "машины зогсоол",
        "zogsool", "garaash", "b1", "dulaan zogsool", "гараж", "гараш", "garaj", "zgsol", "1 davhar", "1-р давхар"
    ]
    if match_any(parking_keywords, t):
        return PARKING_TEXT

    # 10. Сингл / Твин хаус
    if match_any(["сингл", "твин", "ганц айлын", "хоёр айлын", "single", "twin", "сингл хаус", "твин хаус", "single house", "twin house", "gants ailyn", "hoyor ailyn"], t):
        return (
            "Манай Сингл хаус болон Твин хаусын борлуулалт "
            "бүрэн дууссан байгаа. Одоогоор Таун хаус болон "
            "Мульт хаусын сонголтууд боломжтой байна 😊"
        )

    # 11. Сонголтууд
    size_keywords = [
        "сонголт", "мкв сонголт", "м2 сонголт", "мкв", "талбайн сонголт", "хэмжээний сонголт", "ямар сонголт",
        "songolt", "songoltuud", "mkv", "m2", "talbain songolt", "yamar songolt", "songolt baigaa yu", 
        "songolt baigaa", "ямар хэмжээтэй", "yamar hemjeetei", "heden mkv", "heden m2", "talbai heden", 
        "yamar yamar", "heden torliin"
    ]
    if match_any(size_keywords, t) and not match_any(["таун", "мульт", "taun", "mult", "мулт", "town"], t):
        return (
            "Манай төслийн талбайн (м²) сонголтууд:\n\n"
            "🏡 Таун хаус: 213.33 м², 267.48 м²\n"
            "🏢 Мульт хаус: 126 м², 125.21 м², 192.25 м², 189.64 м², "
            "136.42 м², 178.39 м², 198.52 м², 189.52 м²\n\n"
            "Тодорхой сонголтын зураг үзэхийг хүсвэл жишээ нь: "
            "\"Таунхаус 212 зураг\" эсвэл \"Мульт 126 зураг\" гэж бичээрэй 😊"
        )

    # 12. Мульт хаус (Онцлог + м2 сонголт асуух)
    mult_kws = ["мульт", "мульт хаус", "мультхаус", "mult", "multhouse", "mult house", "мулт", "мултхаус", "мулт хаус", "mult-house", "mult havs"]
    if match_any(mult_kws, t):
        mult_sizes = ["100", "116", "120", "125", "126", "136", "178", "189", "192", "198"]
        if not match_any(mult_sizes, t):
            return (
                "Мульт хаусыг сонирхож байгаад баярлалаа! 😊\n\n"
                "✨ **Мульт хаусын онцлог:** Орон сууцны ашигтай тал болон хаусын орчин үеийн тав тухтай орчныг хослуулсан шийдэлтэй. "
                "Б1 болон 1-р давхарт нэгдсэн дулаан зогсоолтой.\n\n"
                "Та ямар хэмжээтэй (м²) Мульт хаус сонирхож байна вэ?\n"
                "Дараах м² сонголтуудаас сонгон бичвэл тухайн загварын дэлгэрэнгүй зураг болон мэдээллийг илгээх болно:\n\n"
                "🏢 Сонголтууд:\n"
                "• 125.21 м², 126 м²\n"
                "• 136.42 м²\n"
                "• 178.39 м²\n"
                "• 189.52 м², 189.64 м²\n"
                "• 192.25 м²\n"
                "• 198.52 м²"
            )

    # 13. Таун хаус (Онцлог + м2 сонголтууд)
    townhouse_kws = [
        "таун", "таун хаус", "таунхаус", "taun", "townhouse", "town house",
        "таун-хаус", "taunhaus", "taun haus", "taun havs", "town-house", "town", "tawn"
    ]
    if match_any(townhouse_kws, t):
        if not match_any(["212", "213", "266", "267"], t):
            return (
                "Таун хаусын мэдээлэл болон зургуудыг илгээж байна 😊\n\n"
                "✨ **Таун хаусын онцлог:** Бие даасан хувийн орон зайг бүрэн хангасан, "
                "хувийн эдэлбэр газар болон бие даасан гараж бүхий тансаг зэрэглэлийн хаус юм.\n\n"
                "🏡 Талбайн сонголтууд: 213.33 м², 267.48 м²"
            )

    # 14. Явц болон ашиглалтад орох хугацаа
    progress_keywords = [
        "явц", "барилга", "шинэ мэдээ",
        "yavts", "yavc", "barilga", "ywts", "yvst", "ywts n", "yvst n", 
        "ywts yugjin", "yavts n yaj yvj bn", "barilgiin yavts"
    ]
    if match_any(progress_keywords, t):
        return "Барилгын явцыг 7 хоног бүрийн 1 дэх өдөр Facebook Page болон Instagram дээр Reel хэлбэрээр шинэчилж хүргэдэг 😊"

    completion_keywords = [
        "ашиглалт", "хэзээ орох", "хэзээ дуусах", "ashiglalt", "hezee oroh", 
        "hezee duusah", "хэзээ орох вэ", "hezee ashiglaltand", "ashiglaltand oroh", 
        "hezee orhiin", "oroh hugatsaa"
    ]
    if match_any(completion_keywords, t):
        return "2026 оны өвөл гэхэд дотоод заслын ажлыг эхлүүлэхээр ажиллаж байна."

    # 15. Ажилтантай холбогдох
    staff_kws = ["хүнтэй", "менежер", "ажилтан", "huntei", "manager", "ajiltan", "админ", "admin", "menejer", "bortai holbogdoh"]
    if match_any(staff_kws, t):
        return f"😊 Манай борлуулалтын албатай {SALES_PHONE} дугаараар холбогдоорой."

    # 16. Ерөнхий мэдээлэл хүсэх
    info_keywords = [
        "мэдээлэл", "дэлгэрэнгүй", "мэдээлэл авъя", "төслийн мэдээлэл", "танилцуулга",
        "medeelel", "delgerengui", "taniltsuulga", "info", "information", "medeelel avya", "medee", "mdll", "mdlel"
    ]
    if match_any(info_keywords, t) and len(t.split()) <= 4:
        return (
            "Miners Villa төсөл нь Эрдэнэт хотод сүндэрлэж буй 30.8 га талбайг хамарсан тансаг зэрэглэлийн хотхон юм. 🏡\n\n"
            "🔹 Сонголт: Таун хаус болон Мульт хаус\n"
            "🔹 М² үнэ: 5,500,000 - 5,800,000 ₮\n"
            "🔹 Байршил: Баян-Өндөр уулын зүүн энгэрт\n\n"
            "Та илүү дэлгэрэнгүй мэдээлэл авахыг хүсвэл 'үнэ', 'байршил', 'төлбөрийн нөхцөл' эсвэл 'сонголт' гэж бичээрэй 😊"
        )

    return None


# =========================================================
# FACEBOOK MESSENGER
# =========================================================

def messenger_url():
    return f"https://graph.facebook.com/v20.0/me/messages?access_token={META_PAGE_ACCESS_TOKEN}"


def send_fb_message(recipient_id: str, text: str):
    if not META_PAGE_ACCESS_TOKEN:
        print("ERROR: META_PAGE_ACCESS_TOKEN байхгүй.")
        return

    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
    }

    try:
        response = requests.post(
            messenger_url(),
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        print("FB TEXT:", response.status_code, response.text)
        response.raise_for_status()
    except Exception as e:
        print("Error sending text to Facebook:", repr(e))


def send_fb_image(recipient_id: str, image_url: str):
    if not META_PAGE_ACCESS_TOKEN:
        print("ERROR: META_PAGE_ACCESS_TOKEN байхгүй.")
        return

    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "image",
                "payload": {"url": image_url, "is_reusable": True},
            }
        },
    }

    try:
        response = requests.post(
            messenger_url(),
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        print("FB IMAGE:", response.status_code, response.text)
        response.raise_for_status()
    except Exception as e:
        print("Error sending image to Facebook:", repr(e))


def send_images_by_keys(recipient_id: str, image_keys: List[str]):
    if not image_keys:
        return

    limited_keys = image_keys[:4]

    seen = set()
    for key in limited_keys:
        if key in seen:
            continue
        seen.add(key)

        if key not in IMAGE_LIBRARY:
            continue

        stem = IMAGE_LIBRARY[key]
        local_path = resolve_photo_file(stem)

        if local_path is None or not local_path.is_file():
            continue

        filename = local_path.name
        try:
            public_url = get_public_image_url(filename)
            send_fb_image(recipient_id, public_url)
            time.sleep(1.5)
        except Exception as e:
            print("Image send error:", repr(e))


# =========================================================
# GEMINI AI
# =========================================================

def ask_gemini(sender_id: str, user_text: str):
    if not client:
        raise RuntimeError("GEMINI_API_KEY тохируулаагүй байна.")

    prompt = f"""
{SYSTEM_PROMPT}

=========================================================
ӨМНӨХ ЯРИАНЫ КОНТЕКСТ
=========================================================

{history_text(sender_id)}

=========================================================
ХЭРЭГЛЭГЧИЙН ШИНЭ МЕССЕЖ
=========================================================

{user_text}

=========================================================
ГАРГАЛТЫН ФОРМАТ
=========================================================

ЗӨВХӨН JSON буцаа. Нэг дор хамгийн ихдээ 4 хүртэлх зургийн KEY буцаана уу.

{{
    "reply": "Монгол хэл дээрх богино хариулт",
    "image_keys": []
}}
"""

    last_error = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                    max_output_tokens=500,
                ),
            )
            raw = (response.text or "").strip()
            print(f"GEMINI RAW (attempt {attempt + 1}):", raw)

            data = json.loads(raw)
            reply = str(data.get("reply", "")).strip()
            image_keys = data.get("image_keys", [])

            if not isinstance(image_keys, list):
                image_keys = []

            valid_keys = [
                key for key in image_keys
                if isinstance(key, str) and key in IMAGE_LIBRARY
            ]

            if not reply:
                reply = UNKNOWN_TEXT

            return reply, valid_keys[:4]

        except Exception as e:
            last_error = e
            error_text = repr(e)
            print(f"GEMINI ERROR (attempt {attempt + 1}/3):", error_text)

            if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text or "quota" in error_text.lower():
                break
            if "503" in error_text or "UNAVAILABLE" in error_text:
                if attempt < 2:
                    time.sleep(2)
                    continue
            if isinstance(e, json.JSONDecodeError):
                break
            break

    raise last_error


# =========================================================
# PROCESS RESPONSE
# =========================================================

def process_ai_response(sender_id: str, user_text: str):
    try:
        direct_reply = direct_faq_router(user_text, sender_id)
        image_result = direct_image_router(user_text, sender_id)

        # 1. Шууд FAQ хариулт эсвэл Зураг байвал Gemini руу явуулахгүй шууд хариулна
        if direct_reply or image_result:
            reply = direct_reply if direct_reply else "Мэдээж 😊 Зургийг явууллаа."

            add_to_history(sender_id, "user", user_text)
            add_to_history(sender_id, "assistant", reply)

            send_fb_message(sender_id, reply)

            if image_result:
                send_images_by_keys(sender_id, image_result[:4])
            return

        # 2. Шууд нөхцөлд таараагүй үед Gemini AI-аас асууна
        try:
            reply, image_keys = ask_gemini(sender_id, user_text)
        except Exception as gemini_error:
            print("GEMINI FALLBACK:", repr(gemini_error))
            reply = UNKNOWN_TEXT
            image_keys = []

        add_to_history(sender_id, "user", user_text)
        add_to_history(sender_id, "assistant", reply)

        send_fb_message(sender_id, reply)
        if image_keys:
            send_images_by_keys(sender_id, image_keys[:4])

    except Exception as e:
        print("Error processing AI response:", repr(e))
        send_fb_message(
            sender_id,
            "Уучлаарай, түр зуурын техникийн алдаа гарлаа. Та түр хүлээгээрэй. 😊"
        )


# =========================================================
# META WEBHOOK VERIFICATION
# =========================================================

@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge or "", media_type="text/plain")

    raise HTTPException(status_code=403, detail="Verification failed")


# =========================================================
# META WEBHOOK RECEIVE MESSAGE
# =========================================================

@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
    except Exception:
        return Response(content="INVALID_JSON", status_code=400)

    if data.get("object") != "page":
        return Response(content="NOT_A_PAGE_EVENT", status_code=404)

    for entry in data.get("entry", []):
        for messaging_event in entry.get("messaging", []):
            message = messaging_event.get("message")
            if not message or message.get("is_echo"):
                continue

            sender_id = messaging_event.get("sender", {}).get("id")
            user_text = message.get("text", "").strip()

            if not sender_id or not user_text:
                continue

            background_tasks.add_task(process_ai_response, sender_id, user_text)

    return Response(content="EVENT_RECEIVED", status_code=200)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
async def root():
    return {
        "status": "Miners Villa bot is running",
        "photo_folder": str(PHOTO_FOLDER),
        "image_count": len(IMAGE_LIBRARY),
        "image_base_url_configured": bool(IMAGE_BASE_URL),
        "gemini_model": GEMINI_MODEL,
    }