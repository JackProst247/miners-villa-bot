import os
import json
import time
import re
import mimetypes
from pathlib import Path
from urllib.parse import quote
from typing import Dict, List, Optional, Tuple, Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from groq import Groq


# =========================================================
# ENVIRONMENT
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

GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)

PUBLIC_BASE_URL = os.getenv(
    "PUBLIC_BASE_URL",
    "https://miners-villa-bot.onrender.com"
).rstrip("/")


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="Miners Villa Messenger Bot",
    version="2.0.0"
)

BASE_DIR = Path(__file__).resolve().parent
PHOTO_FOLDER = BASE_DIR / "photo"

PHOTO_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# MINERS VILLA DATA
# =========================================================

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
    "Медипас эмнэлгийн ард, "
    "30.8 га талбайд байрладаг."
)

PAYMENT_TEXT = (
    "30% урьдчилгаа, 40% явцын төлбөр, "
    "20% явцын төлбөр, 10% түлхүүр гардуулах үед. "
    "Явцын төлбөрт зөвхөн байрны бартер сонсоно."
)

PARKING_TEXT = (
    "Мульт хаусын Б1 болон 1-р давхарт "
    "нэгдсэн дулаан зогсоол байрлана. "
    "Зогсоолын үнэ 50,000,000 ₮."
)

UNKNOWN_TEXT = (
    "Уучлаарай, би энэ асуултыг сайн ойлгосонгүй. "
    "Та асуултаа арай дэлгэрэнгүй бичнэ үү, "
    f"эсвэл манай борлуулалтын албатай {SALES_PHONE} "
    "дугаараар холбогдон лавлах боломжтой 😊"
)


# =========================================================
# PROJECT KNOWLEDGE
# =========================================================

PROJECT_KNOWLEDGE = f"""
MINERS VILLA ТӨСЛИЙН БАТАЛГААТ МЭДЭЭЛЭЛ:

1. ТӨСЛИЙН НЭР
Miners Villa.

2. БАЙРШИЛ
{LOCATION_TEXT}

3. ТАЛБАЙ
Нийт 30.8 га талбайд байрладаг.

4. М² ҮНЭ
М² үнэ:
{PRICE_MIN:,} - {PRICE_MAX:,} ₮.

5. ЗАГВАРУУД
Таун хаус:
- 213.33 м²
- 267.48 м²

Мульт хаус:
- 125.21 м² - 198.52 м² хүртэл.

Сингл болон Твин загварууд дууссан.

6. ТӨЛБӨРИЙН НӨХЦӨЛ
{PAYMENT_TEXT}

7. ЗОГСООЛ
{PARKING_TEXT}

8. ДЭД БҮТЭЦ
- Төвийн дулаан
- Цахилгаан
- Цэвэр ус
- Бохирын шугам

9. ТӨСЛИЙН ОНЦЛОГ
- 24 цагийн харуул хамгаалалт
- 2.2 км хүрээлсэн хашаа
- Автомашингүй ногоон бүс
- Байгалийн гэрэлтүүлэг сайтай
- Насны онцлогт тохирсон 4 төрлийн тоглоомын талбай
- Ойролцоогоор 400 автомашины нэгдсэн дулаан зогсоол
- 30.8 га талбайн 60% нь ногоон байгууламж

10. АШИГЛАЛТАД ОРОХ
2026 оны өвөл дотоод заслын ажлыг эхлүүлэхээр ажиллаж байна.
Яг ашиглалтад орох огноог зохиож хэлж болохгүй.

11. БОРЛУУЛАЛТЫН УТАС
{SALES_PHONE}

12. БОРЛУУЛАЛТЫН ОФФИС
{SALES_OFFICE}
"""


# =========================================================
# IMAGE LIBRARY
# =========================================================

IMAGE_LIBRARY = {
    "GENERAL": "general",
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

IMAGE_KEYS = set(IMAGE_LIBRARY.keys())


# =========================================================
# CONVERSATION MEMORY
# =========================================================

CONVERSATIONS: Dict[str, List[Dict[str, str]]] = {}

MAX_HISTORY = 8


def add_to_history(
    sender_id: str,
    role: str,
    text: str
):
    history = CONVERSATIONS.setdefault(
        sender_id,
        []
    )

    history.append({
        "role": role,
        "text": text
    })

    if len(history) > MAX_HISTORY:
        CONVERSATIONS[sender_id] = history[-MAX_HISTORY:]


def history_text(
    sender_id: str
) -> str:

    history = CONVERSATIONS.get(
        sender_id,
        []
    )

    if not history:
        return "Өмнөх яриа байхгүй."

    return "\n".join(
        f"{item['role']}: {item['text']}"
        for item in history
    )


# =========================================================
# GROQ CLIENT
# =========================================================

client = None

if GROQ_API_KEY:
    try:
        client = Groq(
            api_key=GROQ_API_KEY
        )
    except Exception as exc:
        print(
            "⚠️ Groq client үүсгэхэд алдаа:",
            repr(exc)
        )
        client = None


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def normalize_text(text: str) -> str:

    if not text:
        return ""

    text = str(text).lower().strip()

    # punctuation-ийг space болгоно
    text = re.sub(
        r"[^\w\s.,]",
        " ",
        text,
        flags=re.UNICODE
    )

    # Монгол үсгийн зарим түгээмэл бичлэгийн хувилбар
    replacements = {
        "ё": "е",
        "ү": "у",
        "ө": "о",
        "v": "u",
        "w": "v",
    }

    for old, new in replacements.items():
        text = text.replace(
            old,
            new
        )

    # Түгээмэл typo
    word_replacements = {
        "mdll": "medeelel",
        "mdlel": "medeelel",
        "mdeelel": "medeelel",
        "brshil": "bairshil",
        "tlbur": "tulbur",
        "zgsol": "zogsool",
        "uts": "utas",
        "mkv": "m2",
        "кв": "м2",
    }

    words = text.split()

    normalized_words = [
        word_replacements.get(
            word,
            word
        )
        for word in words
    ]

    return " ".join(
        normalized_words
    ).strip()


def match_any(
    keywords: List[str],
    normalized_text: str
) -> bool:

    return any(
        normalize_text(keyword) in normalized_text
        for keyword in keywords
    )


# =========================================================
# PHOTO HELPERS
# =========================================================

def resolve_photo_file(
    stem: str
) -> Optional[Path]:

    if not PHOTO_FOLDER.exists():
        return None

    target_stem = stem.lower()

    # exact stem
    for file in PHOTO_FOLDER.iterdir():

        if not file.is_file():
            continue

        if file.stem.lower() == target_stem:
            return file

    # exact filename fallback
    for file in PHOTO_FOLDER.iterdir():

        if not file.is_file():
            continue

        if file.name.lower() == target_stem:
            return file

    return None


def get_public_image_url(
    filename: str
) -> str:

    return (
        f"{PUBLIC_BASE_URL}/photo/"
        f"{quote(filename, safe='')}"
    )


# =========================================================
# PHOTO ROUTE
# =========================================================

@app.get("/photo/{filename}")
async def get_photo(
    filename: str
):

    file_path = PHOTO_FOLDER / filename

    if file_path.is_file():

        media_type, _ = mimetypes.guess_type(
            str(file_path)
        )

        return FileResponse(
            file_path,
            media_type=media_type or "image/png",
            headers={
                "Cache-Control":
                    "public, max-age=31536000"
            }
        )

    target = filename.lower()

    # Case insensitive filename
    for file in PHOTO_FOLDER.iterdir():

        if (
            file.is_file()
            and file.name.lower() == target
        ):

            media_type, _ = mimetypes.guess_type(
                str(file)
            )

            return FileResponse(
                file,
                media_type=media_type or "image/png",
                headers={
                    "Cache-Control":
                        "public, max-age=31536000"
                }
            )

    # Case insensitive stem
    target_stem = Path(
        filename
    ).stem.lower()

    for file in PHOTO_FOLDER.iterdir():

        if (
            file.is_file()
            and file.stem.lower() == target_stem
        ):

            media_type, _ = mimetypes.guess_type(
                str(file)
            )

            return FileResponse(
                file,
                media_type=media_type or "image/png",
                headers={
                    "Cache-Control":
                        "public, max-age=31536000"
                }
            )

    raise HTTPException(
        status_code=404,
        detail="Photo not found"
    )


# =========================================================
# QUICK REPLIES
# =========================================================

DEFAULT_BUTTONS = [
    {
        "content_type": "text",
        "title": "🏠 Загварууд",
        "payload": "PAYLOAD_MODEL"
    },
    {
        "content_type": "text",
        "title": "💰 Үнэ",
        "payload": "PAYLOAD_PRICE"
    },
    {
        "content_type": "text",
        "title": "📍 Байршил",
        "payload": "PAYLOAD_LOCATION"
    },
    {
        "content_type": "text",
        "title": "☎️ Холбоо барих",
        "payload": "PAYLOAD_CONTACT"
    }
]


MODEL_BUTTONS = [
    {
        "content_type": "text",
        "title": "🏡 Таун хаус",
        "payload": "PAYLOAD_TOWN"
    },
    {
        "content_type": "text",
        "title": "🏢 Мульт хаус",
        "payload": "PAYLOAD_MULT"
    },
    {
        "content_type": "text",
        "title": "💰 Үнэ",
        "payload": "PAYLOAD_PRICE"
    }
]


# =========================================================
# DIRECT IMAGE ROUTER
# =========================================================

def direct_image_router(
    user_text: str,
    sender_id: str = ""
) -> Optional[List[str]]:

    t = normalize_text(
        user_text
    )

    mult_image_map = {

        "126.32": "MULT_126_32",
        "125.21": "MULT_125",
        "120.85": "MULT_120",

        "116": "MULT_116",
        "100.77": "MULT_100",

        "136.42": "MULT_136",
        "178.39": "MULT_178",

        "189.64": "MULT_189_64",
        "189.52": "MULT_189",

        "192.25": "MULT_192",
        "198.52": "MULT_198",

        "126": "MULT_126",
        "125": "MULT_125",
        "120": "MULT_120",
        "100": "MULT_100",
        "136": "MULT_136",
        "178": "MULT_178",
        "189": "MULT_189",
        "192": "MULT_192",
        "198": "MULT_198",
        "116": "MULT_116",
    }

    # Specific м² first
    for size in sorted(
        mult_image_map.keys(),
        key=len,
        reverse=True
    ):

        escaped = re.escape(size)

        pattern = (
            rf"(?<!\d){escaped}"
            rf"(?!\d)"
        )

        if re.search(
            pattern,
            t
        ):
            return [
                "MULT",
                mult_image_map[size]
            ]

    # Townhouse sizes
    if re.search(
        r"(?<!\d)(212|213)(?!\d)",
        t
    ):

        return [
            "TOWNHOUSE_212",
            "TOWNHOUSE_212_1",
            "GENERAL_PLAN"
        ]

    if re.search(
        r"(?<!\d)(266|267)(?!\d)",
        t
    ):

        return [
            "TOWNHOUSE_266",
            "TOWNHOUSE_266_1",
            "GENERAL_PLAN"
        ]

    # Townhouse
    if match_any(
        [
            "таун хаус",
            "таунхаус",
            "таун",
            "taun",
            "townhouse"
        ],
        t
    ):

        return [
            "TOWNHOUSE_212_1",
            "TOWNHOUSE_212",
            "TOWNHOUSE_266_1",
            "TOWNHOUSE_266"
        ]

    # Multi-house
    if match_any(
        [
            "мульт хаус",
            "мультхаус",
            "мульт",
            "mult",
            "мулт"
        ],
        t
    ):

        return [
            "MULT",
            "MULT_100",
            "MULT_116",
            "MULT_120",
            "MULT_125",
            "MULT_126",
            "MULT_126_32",
            "MULT_136",
            "MULT_178",
            "MULT_189",
            "MULT_189_64",
            "MULT_192",
            "MULT_198"
        ]

    # Parking
    if match_any(
        [
            "зогсоол",
            "гараж",
            "гараш",
            "гарааш",
            "zogsool",
            "garaash",
            "garaj"
        ],
        t
    ):

        return [
            "MULT_PARKING_SPACE",
            "MULT_PARKING_SPACE_1"
        ]

    return None


# =========================================================
# DIRECT FAQ ROUTER
# =========================================================

def direct_faq_router(
    user_text: str,
    sender_id: str = ""
) -> Optional[
    Tuple[str, Any, Optional[List[Dict]]]
]:

    t = normalize_text(
        user_text
    )

    # -----------------------------------------------------
    # 1. Greeting
    # -----------------------------------------------------

    greetings = [
        "сайн уу",
        "сайн байна уу",
        "hello",
        "hi",
        "мэнд",
        "get started",
        "start",
        "snu",
        "сну",
        "сээноо",
        "эхлэх"
    ]

    if (
        match_any(greetings, t)
        and len(t.split()) <= 5
    ):

        reply = (
            "Сайн байна уу? 😊\n\n"
            "Тав тух, үнэ цэнийн илэрхийлэл болсон "
            "'Miners Villa' төслийн албан ёсны "
            "чатботод тавтай морил!\n\n"
            "Урьд нь 'Уурхайчин-3' нэртэй байсан "
            "манай төсөл илүү өргөжиж, хүн бүхэнд "
            "нээлттэй амины орон сууцны цогцолбор "
            "хотхон болсон.\n\n"
            "Танд ямар мэдээлэл хэрэгтэй вэ? 👇"
        )

        return (
            reply,
            True,
            None
        )

    # -----------------------------------------------------
    # 2. Model selection
    # -----------------------------------------------------

    model_keywords = [
        "сонголт",
        "загвар",
        "хэмжээ",
        "мкв",
        "м2",
        "квадрат",
        "songolt",
        "zagvar",
        "mkv"
    ]

    if match_any(
        model_keywords,
        t
    ):

        reply = (
            "Манай төслийн загварын сонголтууд "
            "(Таун болон Мульт хаус)-ыг доорх "
            "картуудаас үзнэ үү 👇"
        )

        return (
            reply,
            "MODEL",
            None
        )

    # -----------------------------------------------------
    # 3. Price
    # -----------------------------------------------------

    price_keywords = [
        "үнэ",
        "үнийн",
        "үнэтэй",
        "м2 үнэ",
        "une",
        "vne",
        "xed",
        "hed"
    ]

    if match_any(
        price_keywords,
        t
    ):

        reply = (
            f"Одоогийн м² үнэ "
            f"{PRICE_MIN:,}–{PRICE_MAX:,} ₮ байна.\n\n"
            "Тодорхой байр, талбайн үнийн "
            "саналыг борлуулалтын албанаас "
            f"{SALES_PHONE} дугаараар "
            "лавлаарай 😊"
        )

        return (
            reply,
            False,
            MODEL_BUTTONS
        )

    # -----------------------------------------------------
    # 4. Location
    # -----------------------------------------------------

    location_keywords = [
        "байршил",
        "хаана байдаг",
        "хаана вэ",
        "bairshil",
        "haana"
    ]

    if match_any(
        location_keywords,
        t
    ):

        reply = (
            f"📍 Miners Villa нь "
            f"{LOCATION_TEXT}\n\n"
            f"☎️ Дэлгэрэнгүй: {SALES_PHONE}"
        )

        return (
            reply,
            False,
            DEFAULT_BUTTONS
        )

    # -----------------------------------------------------
    # 5. Phone
    # -----------------------------------------------------

    phone_keywords = [
        "утас",
        "дугаар",
        "холбоо барих",
        "залгах",
        "utas",
        "dugaar"
    ]

    if (
        match_any(phone_keywords, t)
        and not match_any(["оффис"], t)
    ):

        return (
            f"☎️ Манай борлуулалтын утас: "
            f"{SALES_PHONE} 😊",
            False,
            DEFAULT_BUTTONS
        )

    # -----------------------------------------------------
    # 6. General information
    # -----------------------------------------------------

    info_keywords = [
        "мэдээлэл",
        "дэлгэрэнгүй",
        "танилцуулга",
        "medeelel",
        "taniltsuulga"
    ]

    if (
        match_any(info_keywords, t)
        and len(t.split()) <= 5
    ):

        reply = (
            "🏡 Miners Villa төсөл:\n\n"
            "📍 Байршил: Баян-Өндөр уулын "
            "зүүн энгэрт.\n"
            "🏗 Дэд бүтэц: Төвийн дулаан, "
            "цахилгаан, цэвэр, бохирт холбогдсон.\n"
            "🌳 Эко орчин: 30.8 га талбай.\n"
            "🏠 Сонголт: Таун болон Мульт хаус.\n"
            f"💰 М² үнэ: {PRICE_MIN:,}–"
            f"{PRICE_MAX:,} ₮.\n\n"
            f"☎️ Дэлгэрэнгүй: {SALES_PHONE}"
        )

        return (
            reply,
            False,
            DEFAULT_BUTTONS
        )

    # -----------------------------------------------------
    # 7. Features
    # -----------------------------------------------------

    features_keywords = [
        "онцлог",
        "давуу тал",
        "ялгаа",
        "ontslog",
        "davuu tal"
    ]

    if match_any(
        features_keywords,
        t
    ):

        reply = (
            "🌳 Төслийн онцлог, давуу талууд:\n\n"
            "✅ Найдвартай дэд бүтэц\n"
            "✅ Төвийн бүрэн холболт\n"
            "✅ 24 цагийн харуул хамгаалалт\n"
            "✅ 2.2 км хүрээлсэн хашаа\n"
            "✅ Автомашингүй ногоон бүс\n"
            "✅ Байгалийн гэрэлтүүлэг сайтай\n"
            "✅ Насны онцлогт тохирсон "
            "4 төрлийн тоглоомын талбай\n"
            "✅ Ойролцоогоор 400 автомашины "
            "нэгдсэн дулаан зогсоол"
        )

        return (
            reply,
            False,
            DEFAULT_BUTTONS
        )
    
    # 8. Сингл / Твин хаус - БОРЛУУЛАЛТ ДУУССАН
    sold_out_keywords = [
        "сингл",
        "сингл хаус",
        "single",
        "single house",
        "твин",
        "твин хаус",
        "twin",
        "twin house"
    ]

    if match_any(sold_out_keywords, t):
        reply = (
            "🏡 Сингл болон Твин хаусны борлуулалт дууссан байна. "
            "Одоогоор Miners Villa төслөөс Таун хаус болон Мульт хаусны "
            "сонголтууд үлдсэн байгаа. 😊\n\n"
            f"☎️ Дэлгэрэнгүй мэдээлэл: {SALES_PHONE}"
        )
        return (
            reply, 
            False, 
            DEFAULT_BUTTONS
        )
    # -----------------------------------------------------
    # 9. Payment
    # -----------------------------------------------------

    payment_keywords = [
        "төлбөр",
        "төлбөрийн нөхцөл",
        "урьдчилгаа",
        "tulbur",
        "urdchilgaa"
    ]

    if match_any(
        payment_keywords,
        t
    ):

        return (
            f"💰 {PAYMENT_TEXT}",
            False,
            DEFAULT_BUTTONS
        )

    # -----------------------------------------------------
    # 10. Parking
    # -----------------------------------------------------

    parking_keywords = [
        "зогсоол",
        "гарааш",
        "гараж",
        "б1",
        "zogsool",
        "garaash"
    ]

    if match_any(
        parking_keywords,
        t
    ):

        return (
            f"🚗 {PARKING_TEXT}",
            False,
            DEFAULT_BUTTONS
        )

    # -----------------------------------------------------
    # 11. Completion
    # -----------------------------------------------------

    completion_keywords = [
        "ашиглалт",
        "хэзээ орох",
        "хэзээ ашиглалтад",
        "ashiglalt",
        "hezee oroh"
    ]

    if match_any(
        completion_keywords,
        t
    ):

        reply = (
            "2026 оны өвөл гэхэд дотоод заслын "
            "ажлыг эхлүүлэхээр ажиллаж байна.\n\n"
            "Яг таг ашиглалтад орох огноог "
            "зохиож хэлэхгүй. Шинэ мэдээллийг "
            f"{SALES_PHONE} дугаараас лавлаарай 😊"
        )

        return (
            reply,
            False,
            DEFAULT_BUTTONS
        )

    # -----------------------------------------------------
    # 12. Visit / Office
    # -----------------------------------------------------

    visit_keywords = [
        "очиж",
        "үзэх",
        "узэх",
        "харж болох",
        "харах",
        "уулзах",
        "оффис",
        "очиж харах"
    ]

    if match_any(
        visit_keywords,
        t
    ):

        reply = (
            "Мэдээж 😊 Та манай борлуулалтын "
            "оффист хүрэлцэн ирж төслийн "
            "дэлгэрэнгүй мэдээлэл болон "
            "загвартай танилцах боломжтой.\n\n"
            f"📍 Хаяг: {SALES_OFFICE}\n"
            f"☎️ Утас: {SALES_PHONE}"
        )

        return (
            reply,
            False,
            DEFAULT_BUTTONS
        )
    # 13. SINGLE / TWIN HOUSE - SOLD OUT
    sold_out_keywords = [
        "сингл",
        "сингл хаус",
        "single",
        "single house",
        "твин",
        "твин хаус",
        "twin",
        "twin house",
    ]

    if match_any(sold_out_keywords, t):
        reply = (
            "🏡 Сингл болон Твин хаусны борлуулалт дууссан байна.\n\n"
            "Одоогоор Miners Villa төслөөс:\n"
            "🏠 Таун хаус\n"
            "🏢 Мульт хаус\n"
            "сонголтууд үлдсэн байгаа. 😊\n\n"
            f"☎️ Дэлгэрэнгүй мэдээлэл: {SALES_PHONE}"
        )
        return (
            reply, 
            False, 
            DEFAULT_BUTTONS
        )

    # -----------------------------------------------------
    # 14. Return nothing
    # -----------------------------------------------------

    return None


# =========================================================
# FACEBOOK API
# =========================================================

def messenger_url() -> str:

    if not META_PAGE_ACCESS_TOKEN:
        return ""

    return (
        "https://graph.facebook.com/v20.0/"
        "me/messages"
        f"?access_token={META_PAGE_ACCESS_TOKEN}"
    )


def send_fb_message(
    recipient_id: str,
    text: str,
    quick_replies: Optional[List[Dict]] = None
) -> bool:

    if not META_PAGE_ACCESS_TOKEN:
        print(
            "⚠️ META_PAGE_ACCESS_TOKEN байхгүй."
        )
        return False

    if not recipient_id:
        return False

    if not text:
        text = UNKNOWN_TEXT

    message_data = {
        "text": str(text)
    }

    if quick_replies:
        message_data[
            "quick_replies"
        ] = quick_replies

    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": message_data
    }

    try:

        response = requests.post(
            messenger_url(),
            json=payload,
            headers={
                "Content-Type":
                    "application/json"
            },
            timeout=15
        )

        if not response.ok:

            print(
                "❌ Facebook text API error:",
                response.status_code,
                response.text
            )

            return False

        print(
            "✅ Facebook text sent:",
            response.status_code
        )

        return True

    except Exception as exc:

        print(
            "❌ Error sending text:",
            repr(exc)
        )

        return False


# =========================================================
# GENERAL CAROUSEL
# =========================================================

def send_carousel_menu(
    recipient_id: str,
    quick_replies: Optional[List[Dict]] = None
) -> bool:

    if not META_PAGE_ACCESS_TOKEN:
        return False

    card1_url = (
        f"{PUBLIC_BASE_URL}/photo/"
        "general.png?v=3"
    )

    card2_url = (
        f"{PUBLIC_BASE_URL}/photo/"
        "general_plan.png"
    )

    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": [

                        {
                            "title":
                                "MINERS VILLA ТӨСӨЛ",

                            "subtitle":
                                "Тав тух, үнэ цэнийн "
                                "илэрхийлэл болсон хотхон",

                            "image_url":
                                card1_url,

                            "buttons": [

                                {
                                    "type":
                                        "postback",

                                    "title":
                                        "💰 Үнийн мэдээлэл",

                                    "payload":
                                        "PAYLOAD_PRICE"
                                },

                                {
                                    "type":
                                        "postback",

                                    "title":
                                        "ℹ️ Ерөнхий танилцуулга",

                                    "payload":
                                        "PAYLOAD_INFO"
                                },

                                {
                                    "type":
                                        "postback",

                                    "title":
                                        "🏠 Загварын сонголт",

                                    "payload":
                                        "PAYLOAD_MODEL"
                                }
                            ]
                        },

                        {
                            "title":
                                "MINERS VILLA ТӨСӨЛ",

                            "subtitle":
                                "Хүн бүхэнд нээлттэй "
                                "амины орон сууцны "
                                "цогцолбор",

                            "image_url":
                                card2_url,

                            "buttons": [

                                {
                                    "type":
                                        "postback",

                                    "title":
                                        "📍 Төслийн байршил",

                                    "payload":
                                        "PAYLOAD_LOCATION"
                                },

                                {
                                    "type":
                                        "postback",

                                    "title":
                                        "🌳 Төслийн онцлог",

                                    "payload":
                                        "PAYLOAD_FEATURES"
                                },

                                {
                                    "type":
                                        "postback",

                                    "title":
                                        "☎️ Холбоо барих",

                                    "payload":
                                        "PAYLOAD_CONTACT"
                                }
                            ]
                        }
                    ]
                }
            }
        }
    }

    if quick_replies:
        payload[
            "message"
        ][
            "quick_replies"
        ] = quick_replies

    try:

        response = requests.post(
            messenger_url(),
            json=payload,
            headers={
                "Content-Type":
                    "application/json"
            },
            timeout=15
        )

        if not response.ok:

            print(
                "❌ Carousel API error:",
                response.status_code,
                response.text
            )

            return False

        print(
            "✅ Carousel sent:",
            response.status_code
        )

        return True

    except Exception as exc:

        print(
            "❌ Error sending Carousel:",
            repr(exc)
        )

        return False


# =========================================================
# MODEL CAROUSEL
# =========================================================

def send_model_carousel(
    recipient_id: str,
    quick_replies: Optional[List[Dict]] = None
) -> bool:

    if not META_PAGE_ACCESS_TOKEN:
        return False

    town_url = (
        f"{PUBLIC_BASE_URL}/photo/"
        "townhouse_266.png?v=1"
    )

    mult_url = (
        f"{PUBLIC_BASE_URL}/photo/"
        "mult.png?v=1"
    )

    payload = {
        "recipient": {
            "id": recipient_id
        },

        "message": {
            "attachment": {

                "type": "template",

                "payload": {

                    "template_type": "generic",

                    "elements": [

                        {
                            "title":
                                "🏡 ТАУН ХАУС (Townhouse)",

                            "subtitle":
                                "Сонголт: 213.33 м², "
                                "267.48 м²\n"
                                "Үнэ: м² нь 5.5М - "
                                "5.8М ₮",

                            "image_url":
                                town_url,

                            "buttons": [

                                {
                                    "type":
                                        "postback",

                                    "title":
                                        "🏡 Таун хаус үзэх",

                                    "payload":
                                        "PAYLOAD_TOWN"
                                },

                                {
                                    "type":
                                        "postback",

                                    "title":
                                        "💰 Үнэ харах",

                                    "payload":
                                        "PAYLOAD_PRICE"
                                }
                            ]
                        },

                        {
                            "title":
                                "🏢 МУЛЬТ ХАУС (Multi-family)",

                            "subtitle":
                                "Сонголт: 125 м² - "
                                "198 м² хүртэл\n"
                                "Үнэ: м² нь 5.5М - "
                                "5.8М ₮",

                            "image_url":
                                mult_url,

                            "buttons": [

                                {
                                    "type":
                                        "postback",

                                    "title":
                                        "🏢 Мульт хаус үзэх",

                                    "payload":
                                        "PAYLOAD_MULT"
                                },

                                {
                                    "type":
                                        "postback",

                                    "title":
                                        "☎️ Холбоо барих",

                                    "payload":
                                        "PAYLOAD_CONTACT"
                                }
                            ]
                        }
                    ]
                }
            }
        }
    }

    if quick_replies:
        payload[
            "message"
        ][
            "quick_replies"
        ] = quick_replies

    try:

        response = requests.post(
            messenger_url(),
            json=payload,
            headers={
                "Content-Type":
                    "application/json"
            },
            timeout=15
        )

        if not response.ok:

            print(
                "❌ Model carousel error:",
                response.status_code,
                response.text
            )

            return False

        print(
            "✅ Model carousel sent:",
            response.status_code
        )

        return True

    except Exception as exc:

        print(
            "❌ Error sending model carousel:",
            repr(exc)
        )

        return False


# =========================================================
# SEND IMAGES
# =========================================================

def send_images_by_keys(
    recipient_id: str,
    image_keys: List[str],
    quick_replies: Optional[List[Dict]] = None
) -> bool:

    if not image_keys:
        return False

    if not META_PAGE_ACCESS_TOKEN:
        print(
            "⚠️ META_PAGE_ACCESS_TOKEN байхгүй."
        )
        return False

    elements = []
    seen = set()

    for key in image_keys:

        if key in seen:
            continue

        if key not in IMAGE_LIBRARY:
            print(
                f"⚠️ Unknown image key: {key}"
            )
            continue

        seen.add(key)

        stem = IMAGE_LIBRARY[key]

        local_path = resolve_photo_file(
            stem
        )

        if not local_path:
            print(
                "⚠️ Зураг олдсонгүй:",
                key,
                stem
            )
            continue

        public_url = get_public_image_url(
            local_path.name
        )

        print(
            f"📸 Зураг олдлоо: "
            f"{key} -> {public_url}"
        )

        elements.append({

            "title":
                "Miners Villa - "
                + key.replace("_", " "),

            "image_url":
                public_url,

            "buttons": [

                {
                    "type":
                        "web_url",

                    "url":
                        public_url,

                    "title":
                        "🔍 Томруулж харах"
                }
            ]
        })

    if not elements:

        print(
            "❌ Илгээх боломжтой зураг олдсонгүй."
        )

        send_fb_message(
            recipient_id,
            "⚠️ Уучлаарай, одоогоор "
            "энэ загварын зургууд "
            "системд оруулаагүй байна.",
            quick_replies
        )

        return False

    # Messenger generic template нэг message-д
    # хамгийн ихдээ 10 элемент явуулахад найдвартай.
    chunks = [
        elements[i:i + 10]
        for i in range(
            0,
            len(elements),
            10
        )
    ]

    success = True

    for index, chunk in enumerate(chunks):

        payload = {

            "recipient": {
                "id": recipient_id
            },

            "message": {

                "attachment": {

                    "type":
                        "template",

                    "payload": {

                        "template_type":
                            "generic",

                        "elements":
                            chunk
                    }
                }
            }
        }

        if (
            quick_replies
            and index == len(chunks) - 1
        ):

            payload[
                "message"
            ][
                "quick_replies"
            ] = quick_replies

        try:

            response = requests.post(
                messenger_url(),
                json=payload,
                headers={
                    "Content-Type":
                        "application/json"
                },
                timeout=15
            )

            print(
                f"📡 Facebook image API "
                f"[{index + 1}/{len(chunks)}]: "
                f"{response.status_code}"
            )

            if not response.ok:

                success = False

                print(
                    "❌ Image API error:",
                    response.text
                )

        except Exception as exc:

            success = False

            print(
                "❌ Зураг илгээхэд алдаа:",
                repr(exc)
            )

        time.sleep(0.4)

    return success


# =========================================================
# GROQ SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = f"""
ТА БОЛ "МИНА" — MINERS VILLA ТӨСЛИЙН
эелдэг, зөөлөн, тусч борлуулалтын чатбот.

ТАНЫ ҮНДСЭН ҮҮРЭГ:

1. Хэрэглэгчийн асуултыг ойлгож хариулах.
2. Miners Villa-ийн баталгаатай мэдээллийг ашиглах.
3. Худал мэдээлэл зохиохгүй.
4. Мэдэхгүй мэдээллийг баталгаатай мэт хэлэхгүй.
5. Тодорхой мэдээлэл байхгүй бол борлуулалтын
   {SALES_PHONE} дугаарыг санал болгох.
6. Хэрэглэгч бухимдсан бол маргалдахгүй.
7. Гомдол, санал байвал эелдгээр хүлээн авч,
   асуудлыг ойлгосноо харуулах.
8. Хэрэглэгчийн асуултад аль болох товч,
   ойлгомжтой Монгол хэлээр хариулах.
9. Хэт урт тайлбар хэрэггүй.
10. Үнэ, төлбөр, талбай, байршил зэрэг тоон
    мэдээллийг дур мэдэн өөрчлөхгүй.

ТӨСЛИЙН БАТАЛГААТ МЭДЭЭЛЭЛ:

{PROJECT_KNOWLEDGE}

ЧУХАЛ:

- Яг таг ашиглалтад орох огноо зохиож болохгүй.
- Тодорхойгүй зүйлийг "мэдэхгүй" гэж хэлж болно.
- Худалдан авалтын шийдвэрт дарамт үзүүлэхгүй.
- "Өнөөдөр л", "сүүлчийн байр", "яараарай" гэх мэт
  баталгаагүй борлуулалтын шахалт бүү ашигла.
- Хэрэглэгч зураг хүсвэл image_keys ашиглаж болно.
- Зөвхөн IMAGE_LIBRARY-д байгаа key ашиглана.

ТА ЗААВАЛ ДАРААХ JSON ФОРМАТААР ХАРИУЛ:

{{
    "reply": "Минагийн хариулт",
    "image_keys": []
}}

image_keys нь дараах боломжит утгуудын аль нэг байна:

{", ".join(sorted(IMAGE_KEYS))}
"""


# =========================================================
# GROQ AI
# =========================================================

def ask_groq(
    sender_id: str,
    user_text: str
) -> Tuple[str, List[str]]:

    if not client:

        print(
            "⚠️ Groq client байхгүй."
        )

        return (
            UNKNOWN_TEXT,
            []
        )

    user_prompt = f"""
ӨМНӨХ ЯРИА:

{history_text(sender_id)}

ХЭРЭГЛЭГЧИЙН ШИНЭ МЕССЕЖ:

{user_text}

Дээрх мэдээлэлд тулгуурлан хариул.
"""

    try:

        response = client.chat.completions.create(

            model=GROQ_MODEL,

            messages=[
                {
                    "role":
                        "system",

                    "content":
                        SYSTEM_PROMPT
                },

                {
                    "role":
                        "user",

                    "content":
                        user_prompt
                }
            ],

            response_format={
                "type":
                    "json_object"
            },

            temperature=0.2,

            max_tokens=500
        )

        raw_content = (
            response
            .choices[0]
            .message
            .content
        )

        if not raw_content:
            return (
                UNKNOWN_TEXT,
                []
            )

        data = json.loads(
            raw_content.strip()
        )

        reply = str(
            data.get(
                "reply",
                UNKNOWN_TEXT
            )
        ).strip()

        if not reply:
            reply = UNKNOWN_TEXT

        raw_keys = data.get(
            "image_keys",
            []
        )

        if not isinstance(
            raw_keys,
            list
        ):

            raw_keys = []

        image_keys = [
            key
            for key in raw_keys
            if isinstance(key, str)
            and key in IMAGE_KEYS
        ]

        return (
            reply,
            image_keys[:13]
        )

    except json.JSONDecodeError as exc:

        print(
            "❌ Groq JSON parse error:",
            repr(exc)
        )

        return (
            UNKNOWN_TEXT,
            []
        )

      except Exception as e:
        print("❌ GROQ ERROR:", repr(e))
        return (
            "Уучлаарай, Mina-ийн AI хэсэгт түр зуурын холболтын алдаа гарлаа. "
            f"Манай борлуулалтын алба: {SALES_PHONE} 😊",
            []
        )

        return (
            UNKNOWN_TEXT,
            []
        )


# =========================================================
# RESPONSE PROCESSOR
# =========================================================

def process_ai_response(
    sender_id: str,
    user_text: str
):

    try:

        user_text = (
            user_text or ""
        ).strip()

        if not user_text:
            return

        print(
            f"📩 USER [{sender_id}]: "
            f"{user_text}"
        )

        # -----------------------------------------------
        # Direct FAQ
        # -----------------------------------------------

        faq_result = direct_faq_router(
            user_text,
            sender_id
        )

        # -----------------------------------------------
        # Direct images
        # -----------------------------------------------

        image_result = direct_image_router(
            user_text,
            sender_id
        )

        # -----------------------------------------------
        # FAQ / Image found
        # -----------------------------------------------

        if faq_result or image_result:

            if faq_result:

                reply, show_carousel, custom_buttons = (
                    faq_result
                )

            else:

                reply = (
                    "Мэдээж 😊 "
                    "Дэлгэрэнгүй зургуудыг "
                    "явууллаа."
                )

                show_carousel = False

                custom_buttons = (
                    DEFAULT_BUTTONS
                )

            # Memory
            add_to_history(
                sender_id,
                "user",
                user_text
            )

            add_to_history(
                sender_id,
                "assistant",
                reply
            )

            # General carousel
            if show_carousel is True:

                send_fb_message(
                    sender_id,
                    reply
                )

                send_carousel_menu(
                    sender_id,
                    DEFAULT_BUTTONS
                )

            # Model carousel
            elif show_carousel == "MODEL":

                send_fb_message(
                    sender_id,
                    reply
                )

                send_model_carousel(
                    sender_id,
                    DEFAULT_BUTTONS
                )

            # Text + images
            elif image_result:

                send_fb_message(
                    sender_id,
                    reply
                )

                send_images_by_keys(
                    sender_id,
                    image_result,
                    custom_buttons
                    or DEFAULT_BUTTONS
                )

            # Text only
            else:

                send_fb_message(
                    sender_id,
                    reply,
                    custom_buttons
                    or DEFAULT_BUTTONS
                )

            print(
                f"📤 BOT [{sender_id}]: "
                f"{reply}"
            )

            return

        # -----------------------------------------------
        # Groq fallback
        # -----------------------------------------------

        reply, image_keys = ask_groq(
            sender_id,
            user_text
        )

        add_to_history(
            sender_id,
            "user",
            user_text
        )

        add_to_history(
            sender_id,
            "assistant",
            reply
        )

        print(
            f"🤖 MINA [{sender_id}]: "
            f"{reply}"
        )

        if image_keys:

            send_fb_message(
                sender_id,
                reply
            )

            send_images_by_keys(
                sender_id,
                image_keys,
                DEFAULT_BUTTONS
            )

        else:

            send_fb_message(
                sender_id,
                reply,
                DEFAULT_BUTTONS
            )

    except Exception as exc:

        print(
            "❌ Response Process Error:",
            repr(exc)
        )

        send_fb_message(
            sender_id,
            "Уучлаарай, түр зуурын алдаа "
            f"гарлаа. Та {SALES_PHONE} "
            "дугаараар холбогдоорой 😊"
        )


# =========================================================
# META WEBHOOK PAYLOAD MAP
# =========================================================

PAYLOAD_MAP = {

    "GET_STARTED":
        "сайн уу",

    "PAYLOAD_PRICE":
        "үнэ",

    "PAYLOAD_INFO":
        "танилцуулга",

    "PAYLOAD_MODEL":
        "сонголт",

    "PAYLOAD_LOCATION":
        "байршил",

    "PAYLOAD_FEATURES":
        "онцлог",

    "PAYLOAD_CONTACT":
        "утас",

    "PAYLOAD_TOWN":
        "таун хаус",

    "PAYLOAD_MULT":
        "мульт хаус"
}


# =========================================================
# META WEBHOOK VERIFY
# =========================================================

@app.get("/webhook")
async def verify_webhook(
    request: Request
):

    params = request.query_params

    mode = params.get(
        "hub.mode"
    )

    verify_token = params.get(
        "hub.verify_token"
    )

    challenge = params.get(
        "hub.challenge",
        ""
    )

    if (
        mode == "subscribe"
        and verify_token == VERIFY_TOKEN
    ):

        print(
            "✅ Meta webhook verified."
        )

        return Response(
            content=challenge,
            media_type="text/plain"
        )

    print(
        "❌ Meta webhook verification failed."
    )

    raise HTTPException(
        status_code=403,
        detail="Verification failed"
    )


# =========================================================
# META WEBHOOK POST
# =========================================================

@app.post("/webhook")
async def handle_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):

    try:

        data = await request.json()

    except Exception as exc:

        print(
            "❌ Invalid JSON:",
            repr(exc)
        )

        return Response(
            content="INVALID_JSON",
            status_code=400
        )

    if data.get("object") != "page":

        return Response(
            content="NOT_A_PAGE_EVENT",
            status_code=404
        )

    try:

        for entry in data.get(
            "entry",
            []
        ):

            for messaging_event in entry.get(
                "messaging",
                []
            ):

                sender_id = (
                    messaging_event
                    .get("sender", {})
                    .get("id")
                )

                if not sender_id:
                    continue

                message = (
                    messaging_event
                    .get("message")
                )

                postback = (
                    messaging_event
                    .get("postback")
                )

                user_text = ""

                # -----------------------------------------
                # Message
                # -----------------------------------------

                if (
                    message
                    and not message.get(
                        "is_echo",
                        False
                    )
                ):

                    # Quick reply
                    if "quick_reply" in message:

                        raw_payload = (
                            message
                            .get(
                                "quick_reply",
                                {}
                            )
                            .get(
                                "payload",
                                ""
                            )
                            .strip()
                        )

                        user_text = (
                            PAYLOAD_MAP.get(
                                raw_payload,
                                raw_payload
                            )
                        )

                    # Normal text
                    else:

                        user_text = (
                            message
                            .get(
                                "text",
                                ""
                            )
                            .strip()
                        )

                # -----------------------------------------
                # Postback
                # -----------------------------------------

                elif postback:

                    raw_payload = (
                        postback
                        .get(
                            "payload",
                            ""
                        )
                        .strip()
                    )

                    user_text = (
                        PAYLOAD_MAP.get(
                            raw_payload,
                            raw_payload
                        )
                    )

                # -----------------------------------------
                # Process
                # -----------------------------------------

                if (
                    sender_id
                    and user_text
                ):

                    background_tasks.add_task(
                        process_ai_response,
                        sender_id,
                        user_text
                    )

        return Response(
            content="EVENT_RECEIVED",
            status_code=200
        )

    except Exception as exc:

        print(
            "❌ Webhook processing error:",
            repr(exc)
        )

        # Meta-д 200 буцаах нь webhook retry
        # үүсэхээс сэргийлнэ.
        return Response(
            content="EVENT_RECEIVED",
            status_code=200
        )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/")
async def root():

    return {
        "status":
            "Miners Villa bot is running",
        "groq":
            bool(GROQ_API_KEY),
        "meta":
            bool(META_PAGE_ACCESS_TOKEN),
        "model":
            GROQ_MODEL,
        "photos":
            PHOTO_FOLDER.exists(),
    }


@app.get("/health")
async def health():

    return {
        "ok": True,
        "groq_configured":
            bool(GROQ_API_KEY),
        "meta_configured":
            bool(META_PAGE_ACCESS_TOKEN),
        "photo_folder":
            str(PHOTO_FOLDER),
        "photo_count":
            len(
                [
                    f
                    for f in PHOTO_FOLDER.iterdir()
                    if f.is_file()
                ]
            )
            if PHOTO_FOLDER.exists()
            else 0
    }


# =========================================================
# LOCAL RUN
# =========================================================

if __name__ == "__main__":

    import uvicorn

    port = int(
        os.getenv(
            "PORT",
            "8000"
        )
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )