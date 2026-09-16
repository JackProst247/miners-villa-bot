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
from groq import Groq


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

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY"
)

IMAGE_BASE_URL = os.getenv(
    "IMAGE_BASE_URL",
    ""
).rstrip("/")

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
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
    "30% урьдчилгаа,\n" "40% явцын төлбөр,\n" "20% явцын төлбөр,\n" "10% түлхүүр гардуулах үед.\n"
)

PARKING_TEXT = (
    "Мульт хаусын Б1 болон 1-р давхарт нэгдсэн дулаан зогсоол байрлана. "
    "Зогсоолын үнэ 50,000,000 ₮."
)

UNKNOWN_TEXT = (
    "Уучлаарай, би энэ асуултыг сайн ойлгосонгүй. Та асуултаа арай дэлгэрэнгүй эсвэл өөрөөр бичээд үзнэ үү. "
    "Эсвэл манай борлуулалтын албатай 9430-7017 дугаараар холбогдон шууд лавлах боломжтой 😊"
)


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
ТА БОЛ "МИНА" — MINERS VILLA ТӨСЛИЙН 23 НАСТАЙ, ЭЕЛДЭГ, ЗӨӨЛӨН, ТУСЧ БОРЛУУЛАГЧ.

ЗОРИЛГО БОЛОН ҮҮРЭГ:
1. Автомат түлхүүр үгэнд таараагүй, эсвэл үйлчлүүлэгч англи/монгол крилл хольж алдаатай, галиглаж бичсэн үед зөвөөр ойлгож тайлбарлах.
2. Хэрэв үйлчлүүлэгч бухимдсан, ууртай байвал тайвшруулж, маш эелдэг, найрсаг байдлаар зөв мэдээллийг өгөх.
3. Miners Villa-ийн талаар үнэн зөв мэдээлэл өгч, хүнтэй бодитоор ярилцаж байгаа мэт дулаахан, богино хариулах.
4. Худал мэдээлэл зохиохгүй, мэдэхгүй зүйл байвал 9430-7017 дугаар руу холбогдохыг эелдгээр зөвлөх.

ҮНДСЭН МЭДЭЭЛЭЛ:
* Төслийн нэр: Miners Villa
* М² үнэ: 5,500,000 - 5,800,000 ₮
* Борлуулалтын утас: 9430-7017
* Борлуулалтын оффис: Эрдэнэт хот, 1/16-р байрны зүүн урд буланд, төв зам дагуу.

ТӨЛБӨРИЙН НӨХЦӨЛ:
* 30% урьдчилгаа, 40% явцын төлбөр, 20% явцын төлбөр, 10% түлхүүр гардуулах үед.
* Явцын төлбөрт зөвхөн байрны бартер сонсоно. Машин, газар, бизнесийн бартер байхгүй.

ХАУСНЫ ТӨРЛҮҮД:
* Сингл болон Твин хаусын борлуулалт дууссан. Оронд нь Мульт болон Таун хаусыг санал болгоно.
* Таун хаус: 213.33 м², 267.48 м².
* Мульт хаус: 126 м², 125.21 м², 192.25 м², 189.64 м², 136.42 м², 178.39 м², 198.52 м², 189.52 м².

ДУЛААН ЗОГСООЛ:
* Мульт хаусын Б1 болон 1-р давхарт нэгдсэн дулаан зогсоол байрлана. Үнэ: 50,000,000 ₮.

БАЙРШИЛ:
* Баян-Өндөр уулын зүүн энгэрт, Бүсийн оношилгооны төвийн ард, Медипас эмнэлгийн ард.

БАРИЛГЫН АЖИЛ БОЛОН АШИГЛАЛТАД ОРОХ ХУГАЦАА:
* 2026 оны өвөл гэхэд дотоод заслын ажлыг эхлүүлэхээр ажиллаж байна. 7 хоног бүрийн 1 дэх өдөр Facebook Page дээр Reel ордог.
* АНХААР: Ашиглалтад орох яг таг хугацааг дур мэдэн зохиож (жишээ нь өвлийн сүүлээр гэх мэт) ХАРИУЛЖ БОЛОХГҮЙ. "Яг хэзээ ашиглалтад орох вэ" гэвэл "2026 оны өвөл дотоод засал эхлэх бөгөөд ашиглалтад орох хугацааг борлуулалтын албаны 9430-7017 дугаараас лавлана уу" гэж хариулах.

ЗУРГИЙН ДҮРЭМ (Хэрэв зураг явуулах шаардлагатай бол):
Хэрэв хэрэглэгч ямар нэгэн зураг нэхээгүй, асуугаагүй бол `image_keys` нь үргэлж хоосон `[]` байх ёстой! Зөвхөн зураг үзэхийг хүссэн үед доорх түлхүүрүүдээс буцаана:
""" + "\n".join(f"- {k}" for k in IMAGE_KEYS)

# =========================================================
# ENVIRONMENT
# =========================================================

def check_environment():
    missing = []
    if not META_PAGE_ACCESS_TOKEN:
        missing.append("META_PAGE_ACCESS_TOKEN")
    if not GROQ_API_KEY:
        missing.append("GROQ_API_KEY")
    if not IMAGE_BASE_URL:
        print("WARNING: IMAGE_BASE_URL тохируулаагүй байна.")
    if missing:
        print("WARNING: .env дотор дутуу хувьсагч:", ", ".join(missing))

check_environment()

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


# =========================================================
# HELPERS
# =========================================================

def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s\.,]", " ", text)
    
    replacements = {
        "ё": "е",
        "өү": "оу",
        "ү": "у",
        "ө": "о",
        "v": "u",
        "w": "v",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
        
    word_replacements = {
        "mdll": "medeelel",
        "mdlel": "medeelel",
        "mdeelel": "medeelel",
        "brshil": "bairshil",
        "tlbur": "tulbur",
        "zgsol": "zogsool",
        "uts": "utas",
        "mkv": "m2",
        "мкв": "м2",
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

    mult_image_map = {
        "126.32": "MULT_126_32", "126,32": "MULT_126_32", "126": "MULT_126",
        "125.21": "MULT_125", "125,21": "MULT_125", "125": "MULT_125",
        "120.85": "MULT_120", "120,85": "MULT_120", "120": "MULT_120",
        "116": "MULT_116", "100.77": "MULT_100", "100,77": "MULT_100", "100": "MULT_100",
        "136.42": "MULT_136", "136,42": "MULT_136", "136": "MULT_136",
        "178.39": "MULT_178", "178,39": "MULT_178", "178": "MULT_178",
        "189.64": "MULT_189_64", "189,64": "MULT_189_64", "189.52": "MULT_189", "189,52": "MULT_189", "189": "MULT_189",
        "192.25": "MULT_192", "192,25": "MULT_192", "192": "MULT_192",
        "198.52": "MULT_198", "198,52": "MULT_198", "198": "MULT_198",
    }
    
    for size in sorted(mult_image_map.keys(), key=len, reverse=True):
        pattern = r"\b" + size.replace(".", r"\.").replace(",", r"\,") + r"\b"
        if re.search(pattern, t):
            return ["MULT", mult_image_map[size]]

    if re.search(r"\b(212|213)\b", t):
        return ["GENERAL_PLAN", "TOWNHOUSE_212", "TOWNHOUSE_212_1"]
    if re.search(r"\b(266|267)\b", t):
        return ["GENERAL_PLAN", "TOWNHOUSE_266", "TOWNHOUSE_266_1"]

    mult_kws = ["мульт", "мульт хаус", "мультхаус", "mult", "multhouse", "mult house", "мулт", "мултхаус", "мулт хаус", "mult-house", "mult havs"]
    if match_any(mult_kws, t):
        return ["MULT"]

    townhouse_kws = ["таун хаус", "таунхаус", "таун", "taun", "townhouse", "town house", "таун-хаус", "taunhaus", "taun haus", "taun havs", "town-house", "town", "tawn"]
    if match_any(townhouse_kws, t):
        return ["GENERAL_PLAN"]

    parking_kws = ["зогсоол", "дулаан зогсоол", "машины зогсоол", "б1 зогсоол", "нэгдсэн зогсоол", "zogsool", "garaash", "b1", "гараж", "гараш", "гарааш", "garaj", "garash", "dulaan zogsool", "mashinii zogsool", "1 davhar", "1-р давхар"]
    if match_any(parking_kws, t):
        if match_any(["план", "төлөвлөлт", "plan"], t):
            return ["MULT_PARKING_SPACE"]
        if match_any(["харагдах", "гадаад", "үзэмж", "uzemj"], t):
            return ["MULT_PARKING_SPACE_1"]
        return ["MULT_PARKING_SPACE", "MULT_PARKING_SPACE_1"]

    greenery_kws = ["ногоон", "ногоон байгууламж", "ногоон цэцэрлэг", "ногоон орчин", "тохижилт", "гадна тохижилт", "амрах талбай", "амралтын талбай", "спортын талбай", "хүүхдийн талбай", "nogoon", "nogoon baiguulamj", "tohijilt", "gadna tohijilt", "landscaping", "amrah talbai", "sport", "sport talbai", "huuhdiin talbai", "цэцэрлэг", "мод", "зүлэг", "тоглоомын талбай", "togloomyn talbai", "huuhdiin togloom", "tsetserleg", "mod", "zuleg", "gadna orchin", "orchin", "sagsnii talbai"]
    if match_any(greenery_kws, t):
        if match_any(["0-5", "0 5", "0-5 нас"], t):
            return ["SPORTS_AREA_0_5"]
        if match_any(["9-13", "9 13", "9-13 нас"], t):
            return ["SPORTS_AREA_9_13"]
        if match_any(["13-16", "13 16", "13-16 нас"], t):
            return ["SPORTS_AREA_13_16"]
        return ["GREEN_GARDEN", "LANDSCAPING", "SPORTS_AREA_PLAN", "RELAXATION_AREA"]

    general_keywords = [
        "талбайн зураг", "талбай зураг", "ерөнхий төлөвлөгөө", "ерөнхий план",
        "план зураг", "план", "төлөвлөлтийн зураг", "төлөвлөлт зураг", "төслийн төлөвлөлт",
        "хотхоны зураг", "хотхон зураг", "нийт зураг", "plan", "talbai",
        "хотхоны зохион байгуулалт", "eponhii plan", "hothon", "hothony zurag", 
        "yurunhii tuluvluguu", "yurunhii plan", "tusliin tuluwlult", "tuluwlult", "төлөвлөлт"
    ]
    if match_any(general_keywords, t):
        if not match_any(["таун", "мульт", "зогсоол", "спорт", "тоглоом", "ногоон", "тохижилт", "амрах", "taun", "mult", "zogsool"], t):
            return ["GENERAL_PLAN"]

    photo_only_kws = ["зураг", "зураг үзье", "зураг харья", "зураг явуул", "зураг илгээ", "зургаа", "зургийг", "zurag", "zurag uzei", "zurag uzye", "zurag harya", "zurag yavuul", "zurag ilgee", "zuraguu", "zuragaa", "photo", "zurag n"]
    if match_any(photo_only_kws, t):
        hist_text = normalize_text(history_text(sender_id))
        if match_any(["таун", "townhouse", "taun", "town house"], hist_text):
            if "266" in hist_text or "267" in hist_text:
                return ["GENERAL_PLAN", "TOWNHOUSE_266", "TOWNHOUSE_266_1"]
            if "212" in hist_text or "213" in hist_text:
                return ["GENERAL_PLAN", "TOWNHOUSE_212", "TOWNHOUSE_212_1"]
            return ["GENERAL_PLAN"]
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

    greetings = [
        "сайн уу", "сайн байна уу", "сайн байнуу", "байна уу", "hello", "сайн",
        "sain uu", "sain bainuu", "sain bainguu", "sainbainuu", "sain", "sainuu", 
        "snu", "snuu", "snuuu", "sn uu", "sn u", "u bn", "u baina", "uu bn", "sain u",
        "bnu", "bnuu", "bn uu", "bna uu", "bainuu", "bn", "юу байна", "юу байна уу", "юу байнауу", "юу байнуу",
        "өглөөний мэнд", "өдрийн мэнд", "оройн мэнд", "mends", "mend", "helloo", 
        "uglooni mend", "udriin mend", "oroin mend", "сну", "снуу", "ёну",
        "udrin mend", "udriin mnd", "udrin mnd", "ugluunii mnd", "ugluni mend", 
        "oroinii mend", "oroin mnd", "mnd", "yu baina", "yu baina uu", "yu bainuu", "yu bain", "yu bainu?", "yu bainaa", "yu bainaa?", "yu bainaa uu", "yu bainaa u", "yu bainaa u?", "yu bn", "yu bainaa uuuu"
    ]
    exact_greetings = ["hi", "hiii", "hey", "мэнд"]

    if (match_any(greetings, t) or any(w in t.split() for w in exact_greetings)) and len(t.split()) <= 4 and not match_any(["үнэ", "une", "vne", "утас", "utas", "байршил", "bairshil", "ywts", "yvts", "ashiglalt", "ашиглалт", "хэзээ", "hezee", "oroh", "мульт", "таун", "хаус", "mult", "taun", "haus", "house", "мкв", "m2", "зураг", "zurag"], t):
        return (
            "😊 Сайн байна уу? Манай төслийг сонирхон холбогдсон танд баярлалаа! Намайг Мина гэдэг. 🥰  "
            "Miners Villa төслийн талаар үнэ, "
            "төлөвлөлт, төлбөрийн нөхцөл болон "
            "байршлын талаар дэлгэрэнгүй мэдээлэл өгөхөд бэлэн байна."
        )

    if re.search(r"\b(125\.21|125\,21|125|126\.32|126\,32|126|136\.42|136\,42|136|178\.39|178\,39|178|189\.52|189\,52|189\.64|189\,64|189|192\.25|192\,25|192|198\.52|198\,52|198|100\.77|100\,77|100|116|120\.85|120\,85|120)\b", t):
        return "Таны сонгосон Мульт хаусын загварын ерөнхий болон өрөөний зохион байгуулалтын зургийг илгээж байна. 😊 Дэлгэрэнгүй үнийн мэдээллийг борлуулалтын 9430-7017 дугаараас лавлаарай."

    if re.search(r"\b(212|213|266|267)\b", t):
        return "Таны сонгосон Таун хаусын ерөнхий болон өрөөний зохион байгуулалтын зургийг илгээж байна. 😊 Дэлгэрэнгүй үнийн мэдээллийг борлуулалтын 9430-7017 дугаараас лавлаарай."

    photo_only_kws = ["зураг", "зураг үзье", "зураг харья", "зураг явуул", "зураг илгээ", "зургаа", "зургийг", "zurag", "zurag uzei", "zurag uzye", "zurag harya", "zurag yavuul", "zurag ilgee", "zuraguu", "zuragaa", "photo", "zurag n"]
    if match_any(photo_only_kws, t) and len(t.split()) <= 3:
        return "Мэдээж, холбогдох зургуудыг илгээж байна 😊"

    price_keywords = ["үнэ", "үнийн", "үнэтэй", "м2 үнэ", "м2", "мкв үнэ", "1м2", "1 м2", "квадратын үнэ", "квадрат үнэ", "үнэ хэд", "үнэ хэд вэ", "хэдэн төгрөг", "унэ", "унийн", "une", "uniin", "unetei", "m2 une", "mkv une", "une xed", "une hed", "heden togrog", "vne", "vniin", "vnetei", "vne xed", "vne hed", "une mdll", "vne mdll", "vne medeelel", "une medeelel", "үнэ өртөг", "хэд вэ", "hed ve", "hed be", "xed we", "xed be", "hemjee une", "une n hed ve", "үнэ нь хэд вэ", "un n hed ve", "une n xed"]
    if match_any(price_keywords, t):
        if not match_any(["сонголт", "songolt", "хэмжээ", "hemjee", "ямар ямар", "yamar"], t) or match_any(["үнэ", "une", "vne"], t):
            return (
                "Одоогийн м² үнэ 5,500,000–5,800,000 ₮ байна. "
                "Дэлгэрэнгүй болон сонголтын тодорхой үнийг "
                f"борлуулалтын албаны {SALES_PHONE} дугаараас лавлаарай 😊"
            )

    phone_keywords = ["утас", "дугаар", "холбогдох", "утасны дугаар", "холбоо барих", "залгах", "utas", "dugaar", "holbogdoh", "utasny dugaar", "zalgax", "zalgah", "uts", "utsnii dugaar", "холбогдох дугаар", "утас хэд вэ", "utas hed ve", "utas xed we", "zalgah dugaar", "utasnii dugaar"]
    if match_any(phone_keywords, t) and not match_any(["оффис", "office"], t):
        return f"Манай борлуулалтын утас: {SALES_PHONE} 😊"

    office_keywords = ["оффис", "хаяг", "оффисын хаяг", "оффис хаана", "office", "hayag", "offis", "offis haana", "оффис хаана вэ", "хаяг хаана вэ", "hayag haana ve", "offis haana ve", "haana ochihiin", "ochih"]
    if match_any(office_keywords, t):
        return f"Борлуулалтын оффис: {SALES_OFFICE}. Утас: {SALES_PHONE} 😊"
        
    working_hours_keywords = [
        "цаг", "ажиллах цаг", "ажлын цаг", "хэдээс", "хэд хүртэл", "онгойх", "хаах",
        "tsag", "ajliin tsag", "ajillah tsag", "hedees", "hed hurtel", "ongoidog", "haadag"
    ]
    if match_any(working_hours_keywords, t) and not match_any(["хэзээ орох", "hezee oroh"], t):
        return f"Манай борлуулалтын оффис өдөр бүр 09:00 - 18:00 цагийн хооронд ажиллаж байна. Та {SALES_PHONE} дугаараар мөн холбогдох боломжтой 😊"
        
    visit_keywords = [
        "танилцах", "үзэх", "очиж үзэх", "талбайтай танилцах", "байраа үзэх", "захиалсан байраа",
        "taniltsah", "uzeh", "ochij uzeh", "talbaitai taniltsah", "bairaa uzeh", "zahialsan bairaa"
    ]
    if match_any(visit_keywords, t) and not match_any(["зураг", "zurag", "plan"], t):
        return "Төслийн талбайтай танилцахдаа борлуулалтын албатай холбогдож, боломжит өдрүүдээр цайны цагаар буюу 13:00-14:00 цагийн хооронд танилцах боломжтой 😊"
        
    location_keywords = ["байршил", "байрлал", "хаана байдаг", "хаана вэ", "хаана байрладаг", "хаана байрлах", "хотын хаана", "bairshil", "bairlal", "haana baidag", "haana ve", "haana bairladag", "haana", "brshil", "байршил хаана вэ", "haana bairlaj baigaa ve", "haana bairlah ve", "bairlal haana ve", "bairshil n"]
    if match_any(location_keywords, t):
        return f"Miners Villa нь {LOCATION_TEXT}. Дэлгэрэнгүй мэдээллийг {SALES_PHONE} дугаараас лавлаарай 😊"

    payment_keywords = ["төлбөр", "төлбөрийн нөхцөл", "төлөлтийн нөхцөл", "хэрхэн төлөх", "яаж төлөх", "урьдчилгаа", "хэдэн хувь", "tulbur", "tulburiin noktsol", "urdchilgaa", "yaj tuloh", "xedhen huv", "tlbur", "төлбөрийн графиг", "tolbor", "tulbur n", "tolboriin nohtsol", "yavtsiin tolbor", "yavc tolbor", "yavtsyn tolbor", "urdchilgaa hed", "urdchilgaa heden"]
    if match_any(payment_keywords, t) and not match_any(["бартер", "barter"], t):
        return f"Төлбөрийн нөхцөл: {PAYMENT_TEXT} Явцын төлбөрт зөвхөн байрны бартер сонсоно."

    barter_keywords = ["бартер", "байраар", "машинаар", "газраар", "barter", "bairaar", "mashinaar", "gazraar", "бартер хийх үү", "barter hiih uu", "barterd", "barterlah", "oroltsuulah"]
    if match_any(barter_keywords, t):
        if match_any(["машин", "машинаар", "mashin", "mashinaar"], t):
            return "Явцын төлбөрт зөвхөн байрны бартер сонсоно. Машины бартер зөвшөөрөхгүй."
        if match_any(["газар", "газраар", "gazar", "gazraar"], t):
            return "Явцын төлбөрт зөвхөн байрны бартер сонсоно. Газрын бартер зөвшөөрөхгүй."
        return "Явцын төлбөрт зөвхөн байрны бартер сонсоно. Машин, газар, бизнесийн бартер зөвшөөрөхгүй."

    parking_keywords = ["зогсоол", "гарааш", "б1", "дулаан зогсоол", "машины зогсоол", "zogsool", "garaash", "b1", "dulaan zogsool", "гараж", "гараш", "garaj", "zgsol", "1 davhar", "1-р давхар"]
    if match_any(parking_keywords, t):
        return PARKING_TEXT

    if match_any(["сингл", "твин", "ганц айлын", "хоёр айлын", "single", "twin", "сингл хаус", "твин хаус", "single house", "twin house", "gants ailyn", "hoyor ailyn"], t):
        return (
            "Манай Сингл хаус болон Твин хаусын борлуулалт "
            "бүрэн дууссан байгаа. Одоогоор Таун хаус болон "
            "Мульт хаусын сонголтууд боломжтой байна 😊"
        )

    size_keywords = ["сонголт", "мкв сонголт", "м2 сонголт", "мкв", "талбайн сонголт", "хэмжээний сонголт", "ямар сонголт", "songolt", "songoltuud", "mkv", "m2", "talbain songolt", "yamar songolt", "songolt baigaa yu", "songolt baigaa", "ямар хэмжээтэй", "yamar hemjeetei", "heden mkv", "heden m2", "talbai heden", "yamar yamar", "heden torliin"]
    if match_any(size_keywords, t) and not match_any(["таун", "мульт", "taun", "mult", "мулт", "town"], t):
        return (
            "Манай төслийн талбайн (м²) сонголтууд:\n\n"
            "🏡 Таун хаус: 213.33 м², 267.48 м²\n"
            "🏢 Мульт хаус: 126 м², 125.21 м², 192.25 м², 189.64 м², "
            "136.42 м², 178.39 м², 198.52 м², 189.52 м²\n\n"
            "Та аль нэгийг нь сонирхож байвал хэмжээгээ бичиж дэлгэрэнгүй зураг авах боломжтой 😊"
        )

    mult_kws = ["мульт", "мульт хаус", "мультхаус", "mult", "multhouse", "mult house", "мулт", "мултхаус", "мулт хаус", "mult-house", "mult havs"]
    if match_any(mult_kws, t):
        return (
            "Мульт хаусыг сонирхож байгаад баярлалаа! 😊\n\n"
            "✨ **Мульт хаусын онцлог:** Орон сууцны ашигтай тал болон хаусын орчин үеийн тав тухтай орчныг хослуулсан шийдэлтэй. "
            "Б1 болон 1-р давхарт нэгдсэн дулаан зогсоолтой.\n\n"
            "Та ямар хэмжээтэй (м²) Мульт хаус сонирхож байна вэ?\n"
            "Дараах сонголтуудаас бичвэл бид тухайн загварын дэлгэрэнгүй зураг болон мэдээллийг илгээх болно:\n\n"
            "🏢 Сонголтууд:\n"
            "• 100.77 м² (Борлуулалт дууссан)\n"
            "• 116.46 м² (Борлуулалт дууссан)\n"
            "• 120.85 м² (Борлуулалт дууссан)\n"
            "• 125.21 м²\n"
            "• 126.00 м²\n"
            "• 126.32 м² (Борлуулалт дууссан)\n"
            "• 136.42 м²\n"
            "• 178.39 м²\n"
            "• 189.52 м²\n"
            "• 189.64 м²\n"
            "• 189.66 м² (Борлуулалт дууссан)\n"
            "• 192.25 м²\n"
            "• 198.52 м²"
        )

    townhouse_kws = ["таун", "таун хаус", "таунхаус", "taun", "townhouse", "town house", "таун-хаус", "taunhaus", "taun haus", "taun havs", "town-house", "town", "tawn"]
    if match_any(townhouse_kws, t):
        return (
            "Таун хаусыг сонирхож байгаад баярлалаа! 😊\n\n"
            "✨ **Таун хаусын онцлог:** Бие даасан хувийн орон зайг бүрэн хангасан, "
            "хувийн эдэлбэр газар болон бие даасан гараж бүхий тансаг зэрэглэлийн хаус юм.\n\n"
            "Та ямар хэмжээтэй (м²) Таун хаус сонирхож байна вэ?\n"
            "🏡 Талбайн сонголтууд:\n"
            "• 213.33 м²\n"
            "• 267.48 м²\n\n"
            "Сонголтоо бичвэл бид тухайн загварын ерөнхий болон төлөвлөлтийн зургийг илгээх болно."
        )

    progress_keywords = ["явц", "барилга", "шинэ мэдээ", "yavts", "yavc", "barilga", "ywts", "yvst", "ywts n", "yvst n", "ywts yugjin", "yavts n yaj yvj bn", "barilgiin yavts"]
    if match_any(progress_keywords, t):
        return "Барилгын явцыг 7 хоног бүрийн 1 дэх өдөр Facebook Page болон Instagram дээр Reel хэлбэрээр шинэчилж хүргэдэг 😊"

    completion_keywords = [
        "ашиглалт", "хэзээ орох", "хэзээ дуусах", "ashiglalt", "ashiglaltad", "ashiglaltand", 
        "hezee oroh", "hezee duusah", "хэзээ орох вэ", "hezee oroh ve", "hezee oroh uu", 
        "hezee oroh we", "hezee orhiin", "oroh hugatsaa", "orox", "хэзээ ашиглалтанд",
        "яг хэзээ", "хэзээ юм бэ", "хэзээ юм", "yag hezee", "hezee yum be", "hezee ym be",
        "яг хэзээ орох", "yag hezee oroh"
    ]
    if match_any(completion_keywords, t):
        return "2026 оны өвөл гэхэд дотоод заслын ажлыг эхлүүлэхээр ажиллаж байна. Ашиглалтад орох дэлгэрэнгүй мэдээллийг борлуулалтын 9430-7017 дугаараас лавлана уу 😊"
    
    staff_kws = ["хүнтэй", "менежер", "ажилтан", "huntei", "manager", "ajiltan", "админ", "admin", "menejer", "bortai holbogdoh"]
    if match_any(staff_kws, t):
        return f"😊 Та манай борлуулалтын албатай {SALES_PHONE} дугаараар холбогдох боломжтой."

    info_keywords = [
        "мэдээлэл", "дэлгэрэнгүй", "мэдээлэл авъя", "төслийн мэдээлэл", "танилцуулга", 
        "medeelel", "delgerengui", "taniltsuulga", "info", "information", "medeelel avya", 
        "medee", "mdll", "mdlel", "уурхайчин", "uurhaichin", "төлөлвлөлт", 
        "төслийн төлөвлөлт", "tusliin tuluwlult", "tuluwlult", "төлөвлөлт"
    ]
    if match_any(info_keywords, t) and len(t.split()) <= 4:
        return (
            "\"Miners Villa\" төслийн талаар хамгийн үнэ цэнтэй мэдээллүүдийг хуваалцъя! 🥰\n\n"
            "Юуны өмнө манай төсөл анх \"Уурхайчин-3\" нэртэйгээр эхэлж байсан бол одоо \"Miners Villa\" нэртэйгээр хэн бүхэн худалдан авах боломжтой болсон гэдгийг дуулгахад таатай байна.\n\n"
            "✨ Хамгийн үнэ цэнтэй байршил: Хотыг бүхэлд нь тольдох өндөрлөг буюу Баян-Өндөр хайрхны зүүн энгэрт.\n"
            "✨ Бүрэн шийдэгдсэн дэд бүтэц: Төвийн дулаан, цахилгаан, цэвэр, бохир усны шугамд бүрэн холбогдсон.\n"
            "✨ Эко, ногоон орчин: 30.8 га талбайн 60% нь ногоон байгууламж бөгөөд 24 цагийн харуул хамгаалалттай.\n"
            "✨ Бүх насныханд зориулсан тохижилт: Насны онцлогт тохирсон тоглоомын болон спортын талбайнуудтай.\n"
            "✨ Сургууль, цэцэрлэгтэй ойр: 640 хүүхдийн сургууль, 320 хүүхдийн цэцэрлэг, эмнэлэг төлөвлөгдсөн.\n"
            "✨ Өргөн сонголт: Та Таун (Town) болон Мульт (Multi) хаусны загваруудаас сонголт хийх боломжтой. (Жич: Сингл болон Твин хаусны борлуулалт дууссан)\n\n"
            "Танд эдгээр загваруудын аль нь илүү таалагдаж байна вэ? Мөн хямдрал урамшуулал, төлбөрийн нөхцөлийн мэдээлэл авахыг хүсвэл манай борлуулалтын албаны 9430-7017 дугаартай холбогдоорой! ✨"
        )

    difference_keywords = [
        "ялгаа", "онцлог", "ялгаатай", "юугаараа", "ямар ялгаатай", "давуу тал",
        "yalgaa", "ontslog", "yalgaatai", "yuugaaraa", "davuu tal"
    ]
    if match_any(difference_keywords, t) and match_any(["таун", "мульт", "хаус", "taun", "mult", "haus", "house"], t):
        return (
            "Манай Таун болон Мульт хаусуудын онцлог, ялгааг танд танилцуулъя: 😊\n\n"
            "🏡 **Таун хаус (Town house):**\n"
            "Зэрэгцээ 4 айлын төлөвлөлттэй бөгөөд бие даасан хувийн орон зайг бүрэн хангасан тансаг зэрэглэлийн хаус юм.\n"
            "🔹 **5А загвар (213.33 м²):** 3 унтлагын өрөө (1 нь мастер), 1 олон зориулалттай өрөө, зочны өрөө болон гал тогоо, 3 ариун цэврийн өрөөтэй. 1 автомашины дулаан зогсоолтой.\n"
            "🔹 **5В загвар (267.48 м²):** 3 унтлагын өрөө (1 нь мастер), 1 олон зориулалттай өрөө, зочны өрөө, гал тогоо, 3 ариун цэврийн өрөөтэй. 2 автомашины дулаан зогсоолтой.\n\n"
            "🏢 **Мульт хаус (Multi house):**\n"
            "Орцондоо 4 айлтай бөгөөд давхартаа 2 айл байрлах орчин үеийн төлөвлөлттэй. Загвараасаа хамаараад 100.77 - 198.52 м² хүртэл талбайн өргөн сонголттой (2-4 унтлагын өрөөтэй).\n"
            "✨ **Онцлог:**\n"
            "• **Дуплекс загвар:** 2 давхрын айлууд нь дотроо 2 давхартай тул тансаг, тав тухтай мэдрэмжийг төрүүлнэ.\n"
            "• **Үйлчилгээ:** 1 давхартаа үйлчилгээний талбайтай.\n"
            "• **Зогсоол:** 1 айлд 2 зогсоол ч хүрэлцээтэй олон улсын стандарт хангасан нэгдсэн дулаан зогсоолтой.\n\n"
            "Та аль загварынх нь дэлгэрэнгүй зургийг үзэхийг хүсэж байна вэ?"
        )

    return None


# =========================================================
# FACEBOOK MESSENGER (CAROUSEL & ERROR-SAFE)
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
            timeout=10,
        )
        print("FB TEXT:", response.status_code, response.text)
    except Exception as e:
        print("Error sending text to Facebook:", repr(e))

def send_carousel_menu(recipient_id):
    url = f"https://graph.facebook.com/v17.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": [
                        {
                            "title": "Miners Villa Төсөл",
                            "subtitle": "Тав тух, үнэ цэнийн илэрхийлэл болсон аТаны илгээсэн "Miners Villa" төслийн мэдээлэл болон `image_9e9d2d.png` зураг дээрх Facebook Messenger-ийн харагдах байдалд үндэслэн чатботын интерфэйсийг вэб (HTML/CSS) кодоор бэлтгэлээ. 

Энэхүү код нь яг зураг дээрх шиг хэвтээ чиглэлд гүйдэг (carousel) цэс, мөн хэрэглэгч болон ботын харилцан ярианы бүтэцтэй байх юм. Та үүнийг хуулж аваад `.html` өргөтгөлтэй хадгалан хөтөч дээрээ нээж харах эсвэл хөгжүүлэлтдээ ашиглах боломжтой.

### Чатботын Интерфэйс Код (HTML & CSS)

```html
<!DOCTYPE html>
<html lang="mn">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Miners Villa Chatbot</title>
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background-color: #ffffff;
        margin: 0;
        padding: 20px;
        display: flex;
        justify-content: center;
    }
    .chat-container {
        width: 100%;
        max-width: 800px;
    }
    /* Толгойн хэсэг */
    .header {
        text-align: center;
        margin-bottom: 40px;
    }
    .avatar {
        width: 60px;
        height: 60px;
        background-color: #1a2b3c;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 12px;
        margin-bottom: 10px;
    }
    .page-name {
        font-size: 18px;
        font-weight: 600;
        margin: 0 0 4px 0;
    }
    .page-info {
        font-size: 13px;
        color: #65676B;
        margin: 0;
    }

    /* Хэрэглэгчийн зурвас */
    .message-row {
        display: flex;
        margin-bottom: 20px;
    }
    .message-row.user {
        justify-content: flex-end;
    }
    .bubble {
        padding: 10px 16px;
        border-radius: 18px;
        font-size: 15px;
        max-width: 70%;
        line-height: 1.4;
    }
    .bubble.user {
        background-color: #8a2be2;
        color: white;
        border-bottom-right-radius: 4px;
    }
    .bubble.bot-text {
        background-color: #f0f2f5;
        color: black;
        border-bottom-left-radius: 4px;
        margin-bottom: 10px;
    }

    /* Ботын гүйдэг цэс (Carousel) */
    .carousel-container {
        display: flex;
        overflow-x: auto;
        gap: 12px;
        padding-bottom: 15px;
        /* Scrollbar нуух */
        scrollbar-width: none; 
    }
    .carousel-container::-webkit-scrollbar {
        display: none;
    }
    
    .card {
        flex: 0 0 250px;
        border: 1px solid #E4E6EB;
        border-radius: 16px;
        overflow: hidden;
        background: white;
    }
    .card-img {
        width: 100%;
        height: 150px;
        background-color: #e0e0e0;
        object-fit: cover;
    }
    .card-body {
        padding: 12px;
    }
    .card-title {
        font-weight: 700;
        font-size: 14px;
        margin: 0 0 4px 0;
        text-transform: uppercase;
    }
    .card-subtitle {
        font-size: 13px;
        color: #65676B;
        margin: 0 0 12px 0;
        height: 36px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    /* Товчнууд */
    .btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        padding: 8px 0;
        margin-bottom: 8px;
        background-color: #f0f2f5;
        border: none;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        color: #050505;
        cursor: pointer;
        text-decoration: none;
        transition: background 0.2s;
    }
    .btn:last-child {
        margin-bottom: 0;
    }
    .btn:hover {
        background-color: #E4E6EB;
    }
    .btn-icon {
        margin-right: 6px;
        font-size: 16px;
    }
</style>
</head>
<body>

<div class="chat-container">
    <!-- Толгойн хэсэг -->
    <div class="header">
        <div class="avatar">MV</div>
        <h1 class="page-name">Miners Villa</h1>
        <p class="page-info">14K people follow this<br>Real Estate</p>
    </div>

    <!-- Хэрэглэгчийн эхлүүлэх үйлдэл -->
    <div class="message-row user">
        <div class="bubble user">Get started</div>
    </div>

    <!-- Ботын мэндчилгээ -->
    <div class="message-row bot">
        <div class="bubble bot-text">
            Сайн байна уу? Тав тух, үнэ цэнийн илэрхийлэл болсон <strong>'Miners Villa'</strong> төслийн албан ёсны чатботод тавтай морил!<br><br>
            Урьд нь 'Уурхайчин-3' нэртэй байсан манай төсөл илүү өргөжиж, хүн бүхэнд нээлттэй цогцолбор хотхон болсныг дуулгахад таатай байна. Би танд ямар мэдээлэл өгч туслах вэ?
        </div>
    </div>

    <!-- Ботын Картууд (Carousel) -->
    <div class="carousel-container">
        <!-- Карт 1 -->
        <div class="card">
            <!-- Зургийн оронд бодит линкээ оруулна уу -->
            <img src="[https://via.placeholder.com/250x150/2b3a4a/ffffff?text=Miners+Villa+1](https://via.placeholder.com/250x150/2b3a4a/ffffff?text=Miners+Villa+1)" alt="Miners Villa" class="card-img">
            <div class="card-body">
                <h2 class="card-title">MINERS VILLA</h2>
                <p class="card-subtitle">Тав тух, үнэ цэнийн илэрхийлэл болсон хотхон</p>
                <button class="btn"><span class="btn-icon">💰</span> Үнийн мэдээлэл</button>
                <button class="btn"><span class="btn-icon">ℹ️</span> Ерөнхий танилцуулга</button>
                <button class="btn"><span class="btn-icon">🏠</span> Загварын сонголт</button>
            </div>
        </div>

        <!-- Карт 2 -->
        <div class="card">
            <!-- Зургийн оронд бодит линкээ оруулна уу -->
            <img src="[https://via.placeholder.com/250x150/3a4a5a/ffffff?text=Miners+Villa+2](https://via.placeholder.com/250x150/3a4a5a/ffffff?text=Miners+Villa+2)" alt="Miners Villa" class="card-img">
            <div class="card-body">
                <h2 class="card-title">MINERS VILLA</h2>
                <p class="card-subtitle">Хүн бүхэнд нээлттэй амины орон сууцны цогцолбор</p>
                <button class="btn"><span class="btn-icon">📍</span> Төслийн байршил</button>
                <button class="btn"><span class="btn-icon">🌳</span> Төслийн онцлог</button>
                <button class="btn"><span class="btn-icon">☎️</span> Холбоо барих</button>
            </div>
        </div>
    </div>
    
    <!-- Хэрэглэгч товч дарсны дараах хариуны жишээ -->
    <div class="message-row user" style="margin-top: 10px;">
        <div class="bubble user">📍 Төслийн байршил</div>
    </div>
</div>

</body>
</html>

def send_images_by_keys(recipient_id: str, image_keys: List[str]):
    if not image_keys or not META_PAGE_ACCESS_TOKEN:
        return

    elements = []
    seen = set()

    for key in image_keys[:4]:
        if key in seen or key not in IMAGE_LIBRARY:
            continue
        seen.add(key)

        stem = IMAGE_LIBRARY[key]
        local_path = resolve_photo_file(stem)

        if local_path and local_path.is_file():
            try:
                public_url = get_public_image_url(local_path.name)
                elements.append({
                    "title": f"Miners Villa - {key.replace('_', ' ')}",
                    "image_url": public_url,
                    "buttons": [
                        {
                            "type": "web_url",
                            "url": public_url,
                            "title": "🔍 Томруулж харах"
                        }
                    ]
                })
            except Exception as e:
                print("Image URL resolution error:", e)

    if not elements:
        return

    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": elements
                }
            }
        }
    }

    try:
        response = requests.post(
            messenger_url(),
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        print("FB CAROUSEL:", response.status_code, response.text)
    except Exception as e:
        print("Error sending Carousel to Facebook:", repr(e))

# =========================================================
# GROQ AI (META LLAMA 3)
# =========================================================

def ask_groq(sender_id: str, user_text: str):
    if not client:
        raise RuntimeError("GROQ_API_KEY тохируулаагүй байна.")

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
Хэрэглэгч ууртай эсвэл алдаатай бичсэн байсан ч зөвөөр ойлгож, эелдэг, ойлгомжтой хариулна.

JSON FORMAT:
{{
    "reply": "Монгол хэл дээрх богино эелдэг хариулт",
    "image_keys": []
}}
"""

    last_error = None
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant designed to output only JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=500,
            )
            raw = response.choices[0].message.content.strip()
            print(f"GROQ RAW (attempt {attempt + 1}):", raw)

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
            print(f"GROQ ERROR (attempt {attempt + 1}/3):", repr(e))
            if attempt < 2:
                time.sleep(2)
                continue
            break

    raise last_error


# =========================================================
# PROCESS RESPONSE
# =========================================================

def process_ai_response(sender_id: str, user_text: str):
    try:
        # 1. Түлхүүр үгээр хайх
        direct_reply = direct_faq_router(user_text, sender_id)
        image_result = direct_image_router(user_text, sender_id)

        if direct_reply or image_result:
            reply = direct_reply if direct_reply else "Мэдээж 😊 Дэлгэрэнгүй мэдээлэл болон зургийг явууллаа."

            add_to_history(sender_id, "user", user_text)
            add_to_history(sender_id, "assistant", reply)

            send_fb_message(sender_id, reply)

            if image_result:
                send_images_by_keys(sender_id, image_result[:4])
            return

        # 2. Ойлгомжгүй эсвэл алдаатай бичвэр, түлхүүр үг таараагүй үед Groq (Meta Llama 3) AI руу илгээх
        try:
            reply, image_keys = ask_groq(sender_id, user_text)
        except Exception as ai_error:
            print("AI FALLBACK:", repr(ai_error))
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
            "Уучлаарай, түр зуурын техникийн алдаа гарлаа. Та манай борлуулалтын албатай 9430-7017 дугаараар холбогдоорой 😊"
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
        "status": "Miners Villa bot is running (Powered by Groq Llama-3)",
        "photo_folder": str(PHOTO_FOLDER),
        "image_count": len(IMAGE_LIBRARY),
        "image_base_url_configured": bool(IMAGE_BASE_URL),
        "groq_model": GROQ_MODEL,
    }