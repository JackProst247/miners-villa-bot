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
    # Ерөнхий төлөвлөгөө / орчин
    "GENERAL_PLAN": "general_plan",
    "GREEN_GARDEN": "Green_garden",
    "LANDSCAPING": "landscaping",
    "RELAXATION_AREA": "relaxation_area",

    # Тоглоомын / спортын талбай
    "SPORTS_AREA_0_5": "sports_area_0-5",
    "SPORTS_AREA_9_13": "sports_area_9-13",
    "SPORTS_AREA_13_16": "sports_area_13-16",
    "SPORTS_AREA_PLAN": "sports_area_plan",

    # Мульт хаус
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

    # Таун хаус
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
    "Мульт хаусын Б1 давхарт нэгдсэн дулаан зогсоол байрлана. "
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
* 213.33 м², 267.48 м²

МУЛЬТ ХАУС:
* A — 126 м², B — 125.21 м², C — 192.25 м², D — 189.64 м²
* F — 136.42 м², G — 178.39 м², H — 198.52 м², I — 189.52 м²

ДУЛААН ЗОГСООЛ:
* Мульт хаусын Б1 давхарт нэгдсэн дулаан зогсоол байрлана. Үнэ: 50,000,000 ₮.

БАЙРШИЛ:
* Баян-Өндөр уулын зүүн энгэрт, Бүсийн оношилгооны төвийн ард, Медипас эмнэлгийн ард, 30.8 га талбайд.

БАРИЛГЫН АЖИЛ:
* 2026 оны өвөл гэхэд дотоод заслын ажлыг эхлүүлэхээр ажиллаж байна.
* 7 хоног бүрийн 1 дэх өдөр Facebook Page болон Instagram дээр Reel хэлбэрээр шинэчилж хүргэдэг.

ЗУРГИЙН ДҮРЭМ:
Gemini зөвхөн IMAGE KEY буцаана.
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
    """Монгол/англи текстийг цэвэрлэж, энгийн хэлбэрт оруулна."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    replacements = {
        "ё": "е",
        "өү": "оу",
        "ү": "у",
        "ө": "о",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def match_any(keywords: List[str], normalized_text: str) -> bool:
    """Түлхүүр үгсийн аль нэг нь текст дотор байгаа эсэхийг шалгана."""
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
# DIRECT IMAGE ROUTER (CONTEXT-AWARE & LATIN SUPPORTED)
# =========================================================

def direct_image_router(user_text: str, sender_id: str = "") -> Optional[List[str]]:
    t = normalize_text(user_text)

    # 1. Зогсоолын зургууд
    parking_kws = ["зогсоол", "дулаан зогсоол", "машины зогсоол", "б1 зогсоол", "нэгдсэн зогсоол", "zogsool", "garaash", "b1"]
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

    # 3. Таун хаус ерөнхий зургууд
    if match_any(["таун хаус", "таунхаус", "таун", "taun", "townhouse", "town house"], t):
        if not match_any(["212", "213", "266", "267"], t):
            return ["TOWNHOUSE_212", "TOWNHOUSE_212_1", "TOWNHOUSE_266", "TOWNHOUSE_266_1"]

    # 4. Мульт хаус тусгай хэмжээний зургууд
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
    if match_any(["мульт", "мульт хаус", "мультхаус", "mult", "multhouse", "mult house"], t):
        for size, key in mult_image_map.items():
            if size in t:
                return [key]

    # 5. Мульт хаус ерөнхий зургууд
    if match_any(["мульт хаус", "мультхаус", "мульт", "mult", "multhouse", "mult house"], t):
        mult_sizes = ["100", "116", "120", "125", "126", "136", "178", "189", "192", "198"]
        if not match_any(mult_sizes, t):
            return [
                "MULT", "MULT_100", "MULT_116", "MULT_120", "MULT_125",
                "MULT_126", "MULT_126_32", "MULT_136", "MULT_178",
                "MULT_189", "MULT_189_64", "MULT_192", "MULT_198"
            ]

    # 6. Ногоон байгууламж, орчин, тохижилт болон спортын талбай
    greenery_kws = [
        "ногоон", "ногоон байгууламж", "ногоон цэцэрлэг", "ногоон орчин", "тохижилт", "гадна тохижилт",
        "амрах талбай", "амралтын талбай", "спортын талбай", "хүүхдийн талбай",
        "nogoon", "nogoon baiguulamj", "tohijilt", "gadna tohijilt", "landscaping", 
        "amrah talbai", "sport", "sport talbai", "huuhdiin talbai"
    ]
    if match_any(greenery_kws, t):
        if match_any(["0-5", "0 5", "0-5 нас"], t):
            return ["SPORTS_AREA_0_5"]
        if match_any(["9-13", "9 13", "9-13 нас"], t):
            return ["SPORTS_AREA_9_13"]
        if match_any(["13-16", "13 16", "13-16 нас"], t):
            return ["SPORTS_AREA_13_16"]
        
        # Ногоон байгууламжтай холбоотой бүх зургуудыг хамтад нь илгээнэ
        return ["GREEN_GARDEN", "LANDSCAPING", "SPORTS_AREA_PLAN", "RELAXATION_AREA"]

    # 7. Ерөнхий төлөвлөгөө / Хотхоны талбай
    general_keywords = [
        "талбайн зураг", "талбай зураг", "ерөнхий төлөвлөгөө", "ерөнхий план",
        "план зураг", "план", "төлөвлөлтийн зураг", "төлөвлөлт зураг",
        "хотхоны зураг", "хотхон зураг", "нийт зураг", "plan", "talbai"
    ]
    if match_any(general_keywords, t):
        if not match_any(["таун", "мульт", "зогсоол", "спорт", "тоглоом", "ногоон", "тохижилт", "амрах", "taun", "mult", "zogsool"], t):
            return ["GENERAL_PLAN"]

    # 8. ЯРИАНЫ ТҮҮХЭЭС ЗУРАГ ТАНЬЖ ИЛГЭЭХ
    photo_only_kws = [
        "зураг", "зураг үзье", "зураг харья", "зураг явуул", "зураг илгээ", "зургаа", "зургийг",
        "zurag", "zurag uzei", "zurag uzye", "zurag harya", "zurag yavuul", "zurag ilgee", "zuraguu"
    ]
    if match_any(photo_only_kws, t):
        hist_text = normalize_text(history_text(sender_id))
        if match_any(["таун", "townhouse", "taun"], hist_text):
            if "266" in hist_text or "267" in hist_text:
                return ["TOWNHOUSE_266", "TOWNHOUSE_266_1"]
            if "212" in hist_text or "213" in hist_text:
                return ["TOWNHOUSE_212", "TOWNHOUSE_212_1"]
            return ["TOWNHOUSE_212", "TOWNHOUSE_212_1", "TOWNHOUSE_266", "TOWNHOUSE_266_1"]
        if match_any(["мульт", "mult"], hist_text):
            return ["MULT", "MULT_126", "MULT_189", "MULT_192"]
        if match_any(["зогсоол", "гарааш", "zogsool"], hist_text):
            return ["MULT_PARKING_SPACE", "MULT_PARKING_SPACE_1"]
        
        return ["GENERAL_PLAN"]

    return None


# =========================================================
# DIRECT FAQ ROUTER (LATIN & SHORTCUT SUPPORTED)
# =========================================================

def direct_faq_router(user_text: str, sender_id: str = "") -> Optional[str]:
    t = normalize_text(user_text)

    # 1. Мэндчилгээ болон ярианы товчлолууд
    greetings = [
        "сайн уу", "сайн байна уу", "сайн байнуу", "байна уу", "hello", "hi", "hey", "сайн",
        "sain uu", "sain bainuu", "sain bainguu", "sainbainuu", "sain",
        "snu", "snuu", "snuuu", "sn uu", "sn u", "u bn", "u baina", "uu bn", "sain u"
    ]
    if match_any(greetings, t) and len(t.split()) <= 3 and not match_any(["үнэ", "une", "утас", "utas", "байршил", "bairshil", "ywts", "yvst"], t):
        return (
            "Сайн байна уу? 😊 "
            "Miners Villa төслийн талаар үнэ, "
            "төлөвлөлт, төлбөрийн нөхцөл болон "
            "байршлын мэдээлэл өгөхөд бэлэн байна."
        )

    # 2. Зөвхөн "Зураг үзье" гэх мэт товч асуулт
    photo_only_kws = [
        "зураг", "зураг үзье", "зураг харья", "зураг явуул", "зураг илгээ", "зургаа", "зургийг",
        "zurag", "zurag uzei", "zurag uzye", "zurag harya", "zurag yavuul", "zurag ilgee", "zuraguu", "zuragaa"
    ]
    if match_any(photo_only_kws, t) and len(t.split()) <= 3:
        return "Мэдээж, холбогдох зургуудыг илгээж байна 😊"

    # 3. ҮНЭ (Крилл болон Латин)
    price_keywords = [
        "үнэ", "үнийн", "үнэтэй", "м2 үнэ", "м2", "мкв үнэ", "1м2", "1 м2",
        "квадратын үнэ", "квадрат үнэ", "үнэ хэд", "үнэ хэд вэ", "хэдэн төгрөг",
        "унэ", "унийн", "une", "uniin", "unetei", "m2 une", "mkv une", "une xed", "une hed", "heden togrog"
    ]
    if match_any(price_keywords, t):
        if not match_any(["сонголт", "songolt", "хэмжээ", "hemjee", "ямар ямар", "yamar"], t) or match_any(["үнэ", "une"], t):
            return (
                "Одоогийн м² үнэ 5,500,000–5,800,000 ₮ байна. "
                "Дэлгэрэнгүй болон сонголтын тодорхой үнийг "
                f"борлуулалтын албаны {SALES_PHONE} дугаараас лавлаарай 😊"
            )

    # 4. Борлуулалтын утас
    phone_keywords = [
        "утас", "дугаар", "холбогдох", "утасны дугаар", "холбоо барих", "залгах",
        "utas", "dugaar", "holbogdoh", "utasny dugaar", "zalgax", "zalgah"
    ]
    if match_any(phone_keywords, t) and not match_any(["оффис", "office"], t):
        return f"Манай борлуулалтын утас: {SALES_PHONE} 😊"

    # 5. Борлуулалтын оффис
    office_keywords = [
        "оффис", "хаяг", "оффисын хаяг", "оффис хаана",
        "office", "hayag", "offis", "offis haana"
    ]
    if match_any(office_keywords, t):
        return f"Борлуулалтын оффис: {SALES_OFFICE}. Утас: {SALES_PHONE} 😊"

    # 6. Байршил
    location_keywords = [
        "байршил", "байрлал", "хаана байдаг", "хаана вэ", "хаана байрладаг", "хаана байрлах", "хотын хаана",
        "bairshil", "bairlal", "haana baidag", "haana ve", "haana bairladag", "haana"
    ]
    if match_any(location_keywords, t):
        return f"Miners Villa нь {LOCATION_TEXT}. Дэлгэрэнгүй мэдээллийг {SALES_PHONE} дугаараас лавлаарай 😊"

    # 7. Төлбөрийн нөхцөл
    payment_keywords = [
        "төлбөр", "төлбөрийн нөхцөл", "төлөлтийн нөхцөл", "хэрхэн төлөх", "яаж төлөх", "урьдчилгаа", "хэдэн хувь",
        "tulbur", "tulburiin noktsol", "urdchilgaa", "yaj tuloh", "xedhen huv"
    ]
    if match_any(payment_keywords, t) and not match_any(["бартер", "barter"], t):
        return f"Төлбөрийн нөхцөл: {PAYMENT_TEXT} Явцын төлбөрт зөвхөн байрны бартер сонсоно."

    # 8. Бартер
    barter_keywords = ["бартер", "байраар", "машинаар", "газраар", "barter", "bairaar", "mashinaar", "gazraar"]
    if match_any(barter_keywords, t):
        if match_any(["машин", "машинаар", "mashin", "mashinaar"], t):
            return "Явцын төлбөрт зөвхөн байрны бартер сонсоно. Машины бартер зөвшөөрөхгүй."
        if match_any(["газар", "газраар", "gazar", "gazraar"], t):
            return "Явцын төлбөрт зөвхөн байрны бартер сонсоно. Газрын бартер зөвшөөрөхгүй."
        return "Явцын төлбөрт зөвхөн байрны бартер сонсоно. Машин, газар, бизнесийн бартер зөвшөөрөхгүй."

    # 9. Дулаан зогсоол
    parking_keywords = [
        "зогсоол", "гарааш", "б1", "дулаан зогсоол", "машины зогсоол",
        "zogsool", "garaash", "b1", "dulaan zogsool"
    ]
    if match_any(parking_keywords, t):
        return PARKING_TEXT

    # 10. Сингл / Твин хаус (Борлуулалт дууссан)
    if match_any(["сингл", "твин", "ганц айлын", "хоёр айлын", "single", "twin"], t):
        return (
            "Манай Сингл хаус болон Твин хаусын борлуулалт "
            "бүрэн дууссан байгаа. Одоогоор Таун хаус болон "
            "Мульт хаусын сонголтууд боломжтой байна 😊"
        )

    # 11. Талбайн / мкв сонголтууд
    size_keywords = [
        "сонголт", "мкв сонголт", "м2 сонголт", "мкв", "талбайн сонголт", "хэмжээний сонголт", "ямар сонголт",
        "songolt", "songoltuud", "mkv", "m2", "talbain songolt", "yamar songolt", "songolt baigaa yu", "songolt baigaa"
    ]
    if match_any(size_keywords, t) and not match_any(["таун", "мульт", "taun", "mult"], t):
        return (
            "Манай төслийн талбайн (м²) сонголтууд:\n\n"
            "🏡 Таун хаус: 213.33 м², 267.48 м²\n"
            "🏢 Мульт хаус: 126 м², 125.21 м², 192.25 м², 189.64 м², "
            "136.42 м², 178.39 м², 198.52 м², 189.52 м²\n\n"
            "Тодорхой сонголтын зураг үзэхийг хүсвэл жишээ нь: "
            "\"Таунхаус 212 зураг\" эсвэл \"Мульт 126 зураг\" гэж бичээрэй 😊"
        )

    # 12. Мульт хаус ерөнхий
    if match_any(["мульт", "мульт хаус", "мультхаус", "mult", "multhouse", "mult house"], t):
        mult_sizes = ["100", "116", "120", "125", "126", "136", "178", "189", "192", "198"]
        if not match_any(mult_sizes, t):
            return (
                "Мульт хаусын мэдээлэл болон зургуудыг илгээж байна 😊\n\n"
                "🏢 Талбайн сонголтууд: 126 м², 125.21 м², 192.25 м², 189.64 м², "
                "136.42 м², 178.39 м², 198.52 м², 189.52 м²"
            )

    # 13. Таун хаус ерөнхий
    if match_any(["таун", "таун хаус", "таунхаус", "taun", "townhouse", "town house"], t):
        if not match_any(["212", "213", "266", "267"], t):
            return (
                "Таун хаусын мэдээлэл болон зургуудыг илгээж байна 😊\n\n"
                "🏡 Талбайн сонголтууд: 213.33 м², 267.48 м²"
            )

    # 14. Барилгын явц болон ашиглалтад орох хугацаа
    progress_keywords = [
        "явц", "барилга", "шинэ мэдээ",
        "yavts", "yavc", "barilga", "ywts", "yvst", "ywts n", "yvst n", "ywts yugjin"
    ]
    if match_any(progress_keywords, t):
        return "Барилгын явцыг 7 хоног бүрийн 1 дэх өдөр Facebook Page болон Instagram дээр Reel хэлбэрээр шинэчилж хүргэдэг 😊"

    completion_keywords = ["ашиглалт", "хэзээ орох", "хэзээ дуусах", "ashiglalt", "hezee oroh", "hezee duusah"]
    if match_any(completion_keywords, t):
        return "2026 оны өвөл гэхэд дотоод заслын ажлыг эхлүүлэхээр ажиллаж байна."

    # 15. Ажилтантай холбогдох
    if match_any(["хүнтэй", "менежер", "ажилтан", "huntei", "manager", "ajiltan"], t):
        return f"😊 Манай борлуулалтын албатай {SALES_PHONE} дугаараар холбогдоорой."

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

import time

def send_images_by_keys(recipient_id: str, image_keys: List[str]):
    if not image_keys:
        return

    seen = set()
    for key in image_keys:
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
            time.sleep(1.2)  # Meta спам гэж үзэхээс сэргийлж 1.2 секунд хүлээх
        except Exception as e:
            print("Image send error:", repr(e))

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

    seen = set()
    for key in image_keys:
        if key in seen:
            continue
        seen.add(key)

        if key not in IMAGE_LIBRARY:
            print("BLOCKED unknown image key:", key)
            continue

        stem = IMAGE_LIBRARY[key]
        local_path = resolve_photo_file(stem)

        if local_path is None or not local_path.is_file():
            print("IMAGE FILE NOT FOUND FOR KEY:", key, "STEM:", stem)
            continue

        filename = local_path.name
        try:
            public_url = get_public_image_url(filename)
            print("Sending image:", key, public_url)
            send_fb_image(recipient_id, public_url)
        except Exception as e:
            print("Image send error:", repr(e))


# =========================================================
# GEMINI
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

ЗӨВХӨН JSON буцаа.

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

            return reply, valid_keys

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
        print("ROUTER CHECK:", user_text)

        # 1. СҮЛЖЭЭНИЙ/ШУУД ЧИГЛҮҮЛЭГҮҮД (FAQ болон Зураг)
        direct_reply = direct_faq_router(user_text, sender_id)
        image_result = direct_image_router(user_text, sender_id)

        if direct_reply or image_result:
            reply = direct_reply if direct_reply else "Мэдээж 😊 Зургийг явууллаа."

            add_to_history(sender_id, "user", user_text)
            add_to_history(sender_id, "assistant", reply)

            send_fb_message(sender_id, reply)

            if image_result:
                send_images_by_keys(sender_id, image_result)
            return

        # 2. GEMINI AI
        print("ROUTER: Gemini ашиглана")
        try:
            reply, image_keys = ask_gemini(sender_id, user_text)
        except Exception as gemini_error:
            print("GEMINI FALLBACK:", repr(gemini_error))
            reply = UNKNOWN_TEXT
            image_keys = []

        add_to_history(sender_id, "user", user_text)
        add_to_history(sender_id, "assistant", reply)

        send_fb_message(sender_id, reply)
        send_images_by_keys(sender_id, image_keys)

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

            print("=" * 60)
            print("USER:", sender_id)
            print("MESSAGE:", user_text)
            print("=" * 60)

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