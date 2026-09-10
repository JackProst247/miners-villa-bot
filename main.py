import os
import json
import time
import re
import requests
from pathlib import Path
from urllib.parse import quote
from typing import Dict, List

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

# Messenger зураг авахад ашиглах PUBLIC HTTPS URL.
# Жишээ:
# IMAGE_BASE_URL=https://xxxx.trycloudflare.com/photo

IMAGE_BASE_URL = os.getenv(
    "IMAGE_BASE_URL",
    ""
).rstrip("/")

# Gemini model
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

PHOTO_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)

app.mount(
    "/photo",
    StaticFiles(
        directory=str(PHOTO_FOLDER)
    ),
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

IMAGE_KEYS = list(
    IMAGE_LIBRARY.keys()
)


# =========================================================
# SIMPLE CONVERSATION MEMORY
# =========================================================

CONVERSATIONS: Dict[
    str,
    List[Dict[str, str]]
] = {}

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

TOWNHOUSE_SIZES = {
    "213.33": "213.33 м²",
    "267.48": "267.48 м²",
}

MULT_HOUSES = {
    "A": "126 м²",
    "B": "125.21 м²",
    "C": "192.25 м²",
    "D": "189.64 м²",
    "F": "136.42 м²",
    "G": "178.39 м²",
    "H": "198.52 м²",
    "I": "189.52 м²",
}

PAYMENT_TEXT = (
    "30% урьдчилгаа, 40% явцын төлбөр, "
    "20% явцын төлбөр, 10% түлхүүр гардуулах үед төлнө."
)

PARKING_TEXT = (
    "Мульт хаусын Б1 давхарт нэгдсэн дулаан зогсоол байрлана. "
    "Зогсоолын үнэ 50,000,000 ₮."
)

UNKNOWN_TEXT = (
    "Энэ мэдээллийг одоогоор надад өгөөгүй байна. "
    "Дэлгэрэнгүй мэдээллийг 9430-7017 дугаараас лавлаарай 😊"
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
* Борлуулалтын оффис:
  Эрдэнэт хот, 1/16-р байрны зүүн урд буланд, төв зам дагуу.

ТӨЛБӨРИЙН НӨХЦӨЛ:

* 30% урьдчилгаа
* 40% явцын төлбөр
* 20% явцын төлбөр
* 10% түлхүүр гардуулах үед
* Явцын төлбөрт зөвхөн байрны бартер сонсоно.
* Машин, газар, бизнесийн бартер зөвшөөрсөн гэж хэлж болохгүй.

СИНГЛ БОЛОН ТВИН ХАУС:

* Сингл хаус болон Твин хаусын борлуулалт дууссан.
* Хэрэглэгч асуувал борлуулалт нь дууссан гэж хэлээд одоо байгаа Таун хаус болон Мульт хаусыг санал болгоно.

ТАУН ХАУС:

* 213.33 м²
* 267.48 м²

МУЛЬТ ХАУС:

* A — 126 м²
* B — 125.21 м²
* C — 192.25 м²
* D — 189.64 м²
* F — 136.42 м²
* G — 178.39 м²
* H — 198.52 м²
* I — 189.52 м²

ДУЛААН ЗОГСООЛ:

* Мульт хаусын Б1 давхарт нэгдсэн дулаан зогсоол байрлана.
* Үнэ: 50,000,000 ₮.

БАЙРШИЛ:

* Баян-Өндөр уулын зүүн энгэрт
* Бүсийн оношилгооны төвийн ард
* Медипас эмнэлгийн ард
* 30.8 га талбайд.

БАРИЛГЫН АЖИЛ:

* 2026 оны өвөл гэхэд дотоод заслын ажлыг эхлүүлэхээр ажиллаж байна.
* Үүнийг баталгаатай ашиглалтад орох огноо мэтээр хэлж болохгүй.

БАРИЛГЫН ЯВЦ:

* 7 хоног бүрийн 1 дэх өдөр Facebook Page болон Instagram дээр
  Reel хэлбэрээр шинэчилж хүргэдэг.

МЭДЭЭЛЭЛ ЗОХИОЖ БОЛОХГҮЙ:

* Шинэ үнэ
* Хөнгөлөлт
* Урамшуулал
* Ашиглалтад орох баталгаатай огноо
* Материал
* Үйлчилгээ
* Сургууль
* Цэцэрлэг
* Байрны тоо
* Дансны дугаар

зэрэг prompt-д байхгүй мэдээллийг зохиож болохгүй.

ЗУРГИЙН ДҮРЭМ:

Gemini зөвхөн IMAGE KEY буцаана.

Зөвшөөрөгдсөн IMAGE KEY:
""" + "\n".join(
    f"- {k}" for k in IMAGE_KEYS
) + """

Зураг хүсээгүй үед:
image_keys = []

Зураг хүссэн үед тохирох key сонгоно.
"""


# =========================================================
# ENVIRONMENT
# =========================================================

def check_environment():
    missing = []

    if not META_PAGE_ACCESS_TOKEN:
        missing.append(
            "META_PAGE_ACCESS_TOKEN"
        )

    if not GEMINI_API_KEY:
        missing.append(
            "GEMINI_API_KEY"
        )

    if not IMAGE_BASE_URL:
        print(
            "WARNING: IMAGE_BASE_URL тохируулаагүй байна."
        )

    if missing:
        print(
            "WARNING: .env дотор дутуу хувьсагч:",
            ", ".join(missing)
        )


check_environment()

client = (
    genai.Client(
        api_key=GEMINI_API_KEY
    )
    if GEMINI_API_KEY
    else None
)


# =========================================================
# HELPERS
# =========================================================

def normalize_text(text: str) -> str:
    """
    Монгол/англи текстийг энгийн хэлбэрт оруулна.
    """

    text = text.lower().strip()

    replacements = {
        "ё": "е",
        "өү": "оу",
        "ү": "у",
        "ө": "о",
    }

    for old, new in replacements.items():
        text = text.replace(
            old,
            new
        )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


def resolve_photo_file(
    stem: str
) -> Path | None:

    exact_matches = list(
        PHOTO_FOLDER.glob(
            stem + ".*"
        )
    )

    if exact_matches:
        return exact_matches[0]

    return None


def get_public_image_url(
    filename: str
) -> str:

    if not IMAGE_BASE_URL:
        raise RuntimeError(
            "IMAGE_BASE_URL тохируулаагүй байна."
        )

    encoded_filename = quote(
        filename,
        safe=""
    )

    return (
        f"{IMAGE_BASE_URL}/{encoded_filename}"
    )


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
        del history[:-MAX_HISTORY]


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
# DIRECT IMAGE ROUTER
# =========================================================

def direct_image_router(
    user_text: str
):
    """
    Зураг хүсэлтийг Gemini ашиглахгүйгээр шууд танина.

    None -> зурагтай холбоотой шууд хүсэлт биш
    [] -> зураг хүссэн боловч тохирох зураг байхгүй
    [keys] -> шууд илгээх image keys
    """

    t = normalize_text(
        user_text
    )

    # -----------------------------------------------------
    # Ерөнхий талбай / ерөнхий төлөвлөгөө
    # -----------------------------------------------------

    general_keywords = [
        "талбайн зураг",
        "талбай зураг",
        "ерөнхий төлөвлөгөө",
        "ерөнхий план",
        "план зураг",
        "план",
        "төлөвлөлтийн зураг",
        "төлөвлөлт зураг",
        "хотхоны зураг",
        "хотхон зураг",
        "нийт зураг",
    ]

    if any(
        keyword in t
        for keyword in general_keywords
    ):

        if not any(
            x in t
            for x in [
                "таун",
                "мульт",
                "зогсоол",
                "спорт",
                "тоглоом",
                "ногоон",
                "тохижилт",
                "амрах",
            ]
        ):
            return [
                "GENERAL_PLAN"
            ]

    # -----------------------------------------------------
    # Parking
    # -----------------------------------------------------

    if any(
        keyword in t
        for keyword in [
            "зогсоол",
            "дулаан зогсоол",
            "машины зогсоол",
            "б1 зогсоол",
            "нэгдсэн зогсоол",
        ]
    ):

        if any(
            keyword in t
            for keyword in [
                "план",
                "төлөвлөлт",
            ]
        ):
            return [
                "MULT_PARKING_SPACE"
            ]

        if any(
            keyword in t
            for keyword in [
                "харагдах",
                "гадаад",
                "үзэмж",
            ]
        ):
            return [
                "MULT_PARKING_SPACE_1"
            ]

        if any(
            keyword in t
            for keyword in [
                "зураг",
                "үзье",
                "үзмээр",
                "харья",
            ]
        ):
            return [
                "MULT_PARKING_SPACE",
                "MULT_PARKING_SPACE_1",
            ]

        return None

    # -----------------------------------------------------
    # Townhouse 267 / 266
    # -----------------------------------------------------

    if (
        any(
            x in t
            for x in [
                "267",
                "266"
            ]
        )
        and any(
            x in t
            for x in [
                "зураг",
                "план",
                "төлөвлөлт",
                "үзье",
                "харья",
                "зураг авья",
            ]
        )
    ):
        return [
            "TOWNHOUSE_266",
            "TOWNHOUSE_266_1",
        ]

    # -----------------------------------------------------
    # Townhouse 213 / 212
    # -----------------------------------------------------

    if (
        any(
            x in t
            for x in [
                "213",
                "212"
            ]
        )
        and any(
            x in t
            for x in [
                "зураг",
                "план",
                "төлөвлөлт",
                "үзье",
                "харья",
                "зураг авья",
            ]
        )
    ):
        return [
            "TOWNHOUSE_212",
            "TOWNHOUSE_212_1",
        ]

    # -----------------------------------------------------
    # Townhouse general
    # -----------------------------------------------------

    if (
        "таун хаус" in t
        and any(
            x in t
            for x in [
                "зураг",
                "үзье",
                "харья",
                "план",
                "төлөвлөлт",
            ]
        )
    ):
        return [
            "TOWNHOUSE_266",
            "TOWNHOUSE_212",
        ]

    # -----------------------------------------------------
    # Mult house general
    # -----------------------------------------------------

    if (
        "мульт хаус" in t
        and any(
            x in t
            for x in [
                "зураг",
                "үзье",
                "харья",
                "план",
                "төлөвлөлт",
            ]
        )
    ):
        return [
            "MULT_126",
            "MULT_125",
            "MULT_192",
        ]

    # -----------------------------------------------------
    # Specific MULT sizes
    # -----------------------------------------------------

    mult_image_map = {
        "126.32": "MULT_126_32",
        "126,32": "MULT_126_32",
        "126": "MULT_126",
        "125.21": "MULT_125",
        "125,21": "MULT_125",
        "120.85": "MULT_120",
        "120,85": "MULT_120",
        "116": "MULT_116",
        "100.77": "MULT_100",
        "100,77": "MULT_100",
        "136.42": "MULT_136",
        "136,42": "MULT_136",
        "178.39": "MULT_178",
        "178,39": "MULT_178",
        "189.64": "MULT_189_64",
        "189,64": "MULT_189_64",
        "189.52": "MULT_189",
        "189,52": "MULT_189",
        "192.25": "MULT_192",
        "192,25": "MULT_192",
        "198.52": "MULT_198",
        "198,52": "MULT_198",
    }

    if any(
        x in t
        for x in [
            "мульт",
            "мульт хаус",
        ]
    ):

        for size, key in mult_image_map.items():

            if (
                size in t
                and any(
                    x in t
                    for x in [
                        "зураг",
                        "план",
                        "төлөвлөлт",
                        "үзье",
                        "харья",
                    ]
                )
            ):
                return [key]

    # -----------------------------------------------------
    # Green / landscaping / relaxation
    # -----------------------------------------------------

    if (
        any(
            x in t
            for x in [
                "ногоон байгууламж",
                "ногоон цэцэрлэг",
                "ногоон орчин",
            ]
        )
        and any(
            x in t
            for x in [
                "зураг",
                "үзье",
                "харья",
            ]
        )
    ):
        return [
            "GREEN_GARDEN"
        ]

    if (
        "тохижилт" in t
        and any(
            x in t
            for x in [
                "зураг",
                "үзье",
                "харья",
            ]
        )
    ):
        return [
            "LANDSCAPING"
        ]

    if (
        any(
            x in t
            for x in [
                "амрах талбай",
                "амралтын талбай",
            ]
        )
        and any(
            x in t
            for x in [
                "зураг",
                "үзье",
                "харья",
            ]
        )
    ):
        return [
            "RELAXATION_AREA"
        ]

    # -----------------------------------------------------
    # Children's areas
    # -----------------------------------------------------

    if (
        any(
            x in t
            for x in [
                "0-5",
                "0 5",
                "0-5 нас",
            ]
        )
        and any(
            x in t
            for x in [
                "зураг",
                "талбай",
                "үзье",
            ]
        )
    ):
        return [
            "SPORTS_AREA_0_5"
        ]

    if (
        any(
            x in t
            for x in [
                "9-13",
                "9 13",
                "9-13 нас",
            ]
        )
        and any(
            x in t
            for x in [
                "зураг",
                "талбай",
                "үзье",
            ]
        )
    ):
        return [
            "SPORTS_AREA_9_13"
        ]

    if (
        any(
            x in t
            for x in [
                "13-16",
                "13 16",
                "13-16 нас",
            ]
        )
        and any(
            x in t
            for x in [
                "зураг",
                "талбай",
                "үзье",
            ]
        )
    ):
        return [
            "SPORTS_AREA_13_16"
        ]

    if (
        "спортын талбай" in t
        and any(
            x in t
            for x in [
                "план",
                "төлөвлөлт",
                "зураг",
                "үзье",
            ]
        )
    ):
        return [
            "SPORTS_AREA_PLAN"
        ]

    return None


# =========================================================
# DIRECT FAQ ROUTER
# =========================================================

def direct_faq_router(
    user_text: str
):
    """
    Энгийн, баталгаатай Miners Villa асуултад
    Gemini ашиглахгүйгээр шууд хариулна.

    None -> Gemini хэрэгтэй
    string -> шууд хариулт
    """

    t = normalize_text(
        user_text
    )

    # -----------------------------------------------------
    # Greetings
    # -----------------------------------------------------

    greetings = [
        "сайн уу",
        "сайн байна уу",
        "сайн байнуу",
        "байна уу",
        "hello",
        "hi",
        "hey",
    ]

    if (
        t in greetings
        or any(
            t.startswith(x + " ")
            for x in greetings
        )
    ):
        return (
            "Сайн байна уу? 😊 "
            "Miners Villa төслийн талаар үнэ, "
            "төлөвлөлт, төлбөрийн нөхцөл болон "
            "байршлын мэдээлэл өгөхөд бэлэн байна."
        )

# -----------------------------------------------------
    # Single / Twin house (Sold out)
    # -----------------------------------------------------

    if any(
        x in t
        for x in [
            "сингл",
            "сингл хаус",
            "твин",
            "твин хаус",
            "ганц айлын",
            "хоёр айлын",
        ]
    ):
        return (
            "Манай Сингл хаус болон Твин хаусын борлуулалт "
            "бүрэн дууссан байгаа. Одоогоор Таун хаус болон "
            "Мульт хаусын сонголтууд боломжтой байна 😊"
        )

    # -----------------------------------------------------
    # Price
    # -----------------------------------------------------

    if any(
        x in t
        for x in [
            "м2 хэд",
            "м2 хэд вэ",
            "м2 үнэ",
            "м2 үнэ хэд",
            "1м2",
            "1 м2",
            "квадратын үнэ",
            "квадрат үнэ",
            "үнэ хэд",
            "үнэ хэд вэ",
            "хэдэн төгрөг",
            "м2 нь",
        ]
    ):
        return (
            "Одоогийн м² үнэ 5,500,000–5,800,000 ₮ байна. "
            "Яг сонголтын үнэ болон дэлгэрэнгүй мэдээллийг "
            "9430-7017 дугаараас лавлаарай 😊"
        )

    # -----------------------------------------------------
    # Sales phone
    # -----------------------------------------------------

    if any(
        x in t
        for x in [
            "утас",
            "холбогдох",
            "холбоо барих",
            "дугаар",
            "утасны дугаар",
        ]
    ):
        return (
            "Манай борлуулалтын утас: 9430-7017 😊"
        )

    # -----------------------------------------------------
    # Sales office
    # -----------------------------------------------------

    if any(
        x in t
        for x in [
            "оффис хаана",
            "оффисын хаяг",
            "борлуулалтын оффис",
            "оффис",
        ]
    ):
        return (
            f"Борлуулалтын оффис: {SALES_OFFICE}. "
            f"Утас: {SALES_PHONE} 😊"
        )

    # -----------------------------------------------------
    # Location
    # -----------------------------------------------------

    if any(
        x in t
        for x in [
            "хаана байрладаг",
            "хаана байрлах",
            "байршил",
            "байрлал",
            "хаана байдаг",
            "хаана вэ",
            "хотын хаана",
        ]
    ):
        return (
            f"Miners Villa нь {LOCATION_TEXT}. "
            f"Дэлгэрэнгүй мэдээллийг {SALES_PHONE} дугаараас "
            "лавлаарай 😊"
        )

    # -----------------------------------------------------
    # Payment
    # -----------------------------------------------------

    if any(
        x in t
        for x in [
            "төлбөрийн нөхцөл",
            "төлөлтийн нөхцөл",
            "хэрхэн төлөх",
            "яаж төлөх",
            "урьдчилгаа",
            "төлбөр хэдэн хувь",
            "хэдэн хувь төлөх",
        ]
    ):
        return (
            f"Төлбөрийн нөхцөл: {PAYMENT_TEXT} "
            "Явцын төлбөрт зөвхөн байрны бартер сонсоно."
        )

    # -----------------------------------------------------
    # Barter
    # -----------------------------------------------------

    if any(
        x in t
        for x in [
            "бартер",
            "байраар төлөх",
            "машинаар төлөх",
            "газраар төлөх",
        ]
    ):

        if any(
            x in t
            for x in [
                "машин",
                "машинаар",
            ]
        ):
            return (
                "Явцын төлбөрт зөвхөн байрны бартер сонсоно. "
                "Машины бартер зөвшөөрөхгүй."
            )

        if any(
            x in t
            for x in [
                "газар",
                "газраар",
            ]
        ):
            return (
                "Явцын төлбөрт зөвхөн байрны бартер сонсоно. "
                "Газрын бартер зөвшөөрөхгүй."
            )

        return (
            "Явцын төлбөрт зөвхөн байрны бартер сонсоно. "
            "Машин, газар, бизнесийн бартер зөвшөөрөхгүй."
        )

    # -----------------------------------------------------
    # Townhouse sizes
    # -----------------------------------------------------

    if any(
        x in t
        for x in [
            "таун хаус хэдэн м2",
            "таун хаусын талбай",
            "таун хаусын хэмжээ",
            "таунхаус хэдэн м2",
            "таунхаусын талбай",
        ]
    ):
        return (
            "Таун хаусын сонголтууд 213.33 м² болон "
            "267.48 м² талбайтай."
        )

    # -----------------------------------------------------
    # Mult house sizes
    # -----------------------------------------------------

    if any(
        x in t
        for x in [
            "мульт хаус хэдэн м2",
            "мульт хаусын талбай",
            "мульт хаусын хэмжээ",
            "мультхаусын талбай",
        ]
    ):
        return (
            "Мульт хаусын талбайнууд: "
            "126, 125.21, 192.25, 189.64, "
            "136.42, 178.39, 198.52 болон 189.52 м²."
        )

    # -----------------------------------------------------
    # Specific MULT sizes
    # -----------------------------------------------------

    mult_size_answers = {
        "126.32": "126.32 м²",
        "126,32": "126.32 м²",
        "126": "126 м²",
        "125.21": "125.21 м²",
        "125,21": "125.21 м²",
        "120.85": "120.85 м²",
        "120,85": "120.85 м²",
        "116": "116 м²",
        "100.77": "100.77 м²",
        "100,77": "100.77 м²",
        "136.42": "136.42 м²",
        "136,42": "136.42 м²",
        "178.39": "178.39 м²",
        "178,39": "178.39 м²",
        "189.64": "189.64 м²",
        "189,64": "189.64 м²",
        "189.52": "189.52 м²",
        "189,52": "189.52 м²",
        "192.25": "192.25 м²",
        "192,25": "192.25 м²",
        "198.52": "198.52 м²",
        "198,52": "198.52 м²",
    }

    if "мульт" in t:

        for size, display_size in mult_size_answers.items():

            if size in t:
                return (
                    f"Мульт хаусын {display_size} сонголт байна. "
                    "Зураг үзэх бол \"зураг үзье\" гэж бичээрэй 😊"
                )

    # -----------------------------------------------------
    # Parking information
    # -----------------------------------------------------

    if any(
        x in t
        for x in [
            "зогсоолын үнэ",
            "зогсоол хэд",
            "зогсоол хэд вэ",
            "дулаан зогсоолын үнэ",
            "машины зогсоолын үнэ",
        ]
    ):
        return PARKING_TEXT

    if any(
        x in t
        for x in [
            "дулаан зогсоол",
            "нэгдсэн зогсоол",
            "б1 зогсоол",
            "машины зогсоол",
        ]
    ):
        return PARKING_TEXT

    # -----------------------------------------------------
    # Construction progress
    # -----------------------------------------------------

    if any(
        x in t
        for x in [
            "барилгын явц",
            "явц ямар",
            "барилга хэр явж",
            "барилга явж байна",
            "шинэ мэдээ",
        ]
    ):
        return (
            "Барилгын явцыг 7 хоног бүрийн 1 дэх өдөр "
            "Facebook Page болон Instagram дээр Reel "
            "хэлбэрээр шинэчилж хүргэдэг."
        )

    # -----------------------------------------------------
    # Construction timing
    # -----------------------------------------------------

    if any(
        x in t
        for x in [
            "хэзээ ашиглалтад",
            "ашиглалтад орох",
            "хэзээ дуусах",
            "хэзээ баригдаж дуусах",
        ]
    ):
        return (
            "2026 оны өвөл гэхэд дотоод заслын ажлыг "
            "эхлүүлэхээр ажиллаж байна. "
            "Ашиглалтад орох баталгаатай огноо одоогоор "
            "өгөөгүй байна."
        )

    # -----------------------------------------------------
    # Human contact
    # -----------------------------------------------------

    if any(
        x in t
        for x in [
            "хүнтэй ярья",
            "хүнтэй ярих",
            "борлуулалтын ажилтан",
            "борлуулалттай ярья",
            "менежертэй ярья",
            "менежер",
        ]
    ):
        return (
            "😊 Манай борлуулалтын албатай "
            "9430-7017 дугаараар холбогдоорой."
        )

    return None


# =========================================================
# FACEBOOK MESSENGER
# =========================================================

def messenger_url():
    return (
        "https://graph.facebook.com/v20.0/me/messages"
        f"?access_token={META_PAGE_ACCESS_TOKEN}"
    )


def send_fb_message(
    recipient_id: str,
    text: str
):

    if not META_PAGE_ACCESS_TOKEN:
        print(
            "ERROR: META_PAGE_ACCESS_TOKEN байхгүй."
        )
        return

    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": text
        },
    }

    try:

        response = requests.post(
            messenger_url(),
            json=payload,
            headers={
                "Content-Type": "application/json"
            },
            timeout=30,
        )

        print(
            "FB TEXT:",
            response.status_code,
            response.text
        )

        response.raise_for_status()

    except Exception as e:

        print(
            "Error sending text to Facebook:",
            repr(e)
        )


def send_fb_image(
    recipient_id: str,
    image_url: str
):

    if not META_PAGE_ACCESS_TOKEN:
        print(
            "ERROR: META_PAGE_ACCESS_TOKEN байхгүй."
        )
        return

    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "attachment": {
                "type": "image",
                "payload": {
                    "url": image_url,
                    "is_reusable": True,
                },
            }
        },
    }

    try:

        response = requests.post(
            messenger_url(),
            json=payload,
            headers={
                "Content-Type": "application/json"
            },
            timeout=30,
        )

        print(
            "FB IMAGE:",
            response.status_code,
            response.text
        )

        response.raise_for_status()

    except Exception as e:

        print(
            "Error sending image to Facebook:",
            repr(e)
        )


def send_images_by_keys(
    recipient_id: str,
    image_keys
):

    if not image_keys:
        return

    seen = set()

    for key in image_keys:

        if key in seen:
            continue

        seen.add(key)

        if key not in IMAGE_LIBRARY:
            print(
                "BLOCKED unknown image key:",
                key
            )
            continue

        stem = IMAGE_LIBRARY[key]

        local_path = resolve_photo_file(
            stem
        )

        if (
            local_path is None
            or not local_path.is_file()
        ):
            print(
                "IMAGE FILE NOT FOUND FOR KEY:",
                key,
                "STEM:",
                stem
            )
            continue

        filename = local_path.name

        try:

            public_url = get_public_image_url(
                filename
            )

            print(
                "Sending image:",
                key,
                public_url
            )

            send_fb_image(
                recipient_id,
                public_url
            )

        except Exception as e:

            print(
                "Image send error:",
                repr(e)
            )


# =========================================================
# GEMINI
# =========================================================

def ask_gemini(
    sender_id: str,
    user_text: str
):

    """
    Gemini-г зөвхөн router-ууд танихгүй асуултад ашиглана.

    429 -> шууд quota fallback
    503 -> 3 хүртэл retry
    бусад алдаа -> fallback
    """

    if not client:
        raise RuntimeError(
            "GEMINI_API_KEY тохируулаагүй байна."
        )

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

ЧУХАЛ:

* JSON-оос өөр текст бүү бич.
* reply заавал бүтэн өгүүлбэр байна.
* image_keys зөвхөн зөвшөөрөгдсөн key байна.
* Filename, URL, Windows path бүү бич.
* Зураг шаардлагагүй бол image_keys = [] байна.
"""

    last_error = None

    # Зөвхөн түр зуурын server error үед retry.
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

            raw = (
                response.text or ""
            ).strip()

            print(
                f"GEMINI RAW (attempt {attempt + 1}):",
                raw
            )

            data = json.loads(
                raw
            )

            reply = str(
                data.get(
                    "reply",
                    ""
                )
            ).strip()

            image_keys = data.get(
                "image_keys",
                []
            )

            if not isinstance(
                image_keys,
                list
            ):
                image_keys = []

            valid_keys = [
                key
                for key in image_keys
                if (
                    isinstance(key, str)
                    and key in IMAGE_LIBRARY
                )
            ]

            if not reply:
                reply = UNKNOWN_TEXT

            return reply, valid_keys

        except Exception as e:

            last_error = e

            error_text = repr(e)

            print(
                f"GEMINI ERROR "
                f"(attempt {attempt + 1}/3):",
                error_text
            )

            # -------------------------------------------------
            # 429 quota
            # -------------------------------------------------

            if (
                "429" in error_text
                or "RESOURCE_EXHAUSTED" in error_text
                or "quota" in error_text.lower()
            ):
                print(
                    "GEMINI QUOTA EXCEEDED - "
                    "fallback ашиглана."
                )
                break

            # -------------------------------------------------
            # 503 temporary server error
            # -------------------------------------------------

            if (
                "503" in error_text
                or "UNAVAILABLE" in error_text
            ):
                if attempt < 2:
                    time.sleep(2)
                    continue

            # -------------------------------------------------
            # JSON parse error
            # -------------------------------------------------

            if isinstance(
                e,
                json.JSONDecodeError
            ):
                break

            # Бусад алдаанд дахин retry хийхгүй.
            break

    raise last_error


# =========================================================
# PROCESS RESPONSE
# =========================================================

def process_ai_response(
    sender_id: str,
    user_text: str
):

    try:

        print(
            "ROUTER CHECK:",
            user_text
        )

        # =====================================================
        # 1. ЗУРАГ ROUTER
        # =====================================================

        image_result = direct_image_router(
            user_text
        )

        if image_result is not None:

            print(
                "DIRECT IMAGE ROUTER:",
                image_result
            )

            if image_result:

                add_to_history(
                    sender_id,
                    "user",
                    user_text
                )

                reply = (
                    "Мэдээж 😊 Зургийг явууллаа."
                )

                add_to_history(
                    sender_id,
                    "assistant",
                    reply
                )

                send_fb_message(
                    sender_id,
                    reply
                )

                send_images_by_keys(
                    sender_id,
                    image_result
                )

                return

        # =====================================================
        # 2. LOCAL FAQ ROUTER
        # =====================================================

        direct_reply = direct_faq_router(
            user_text
        )

        if direct_reply is not None:

            print(
                "DIRECT FAQ REPLY:",
                direct_reply
            )

            add_to_history(
                sender_id,
                "user",
                user_text
            )

            add_to_history(
                sender_id,
                "assistant",
                direct_reply
            )

            send_fb_message(
                sender_id,
                direct_reply
            )

            return

        # =====================================================
        # 3. GEMINI
        # =====================================================

        print(
            "ROUTER: Gemini ашиглана"
        )

        try:

            reply, image_keys = ask_gemini(
                sender_id,
                user_text
            )

        except Exception as gemini_error:

            error_text = repr(
                gemini_error
            )

            print(
                "GEMINI FALLBACK:",
                error_text
            )

            reply = (
                "Энэ асуултад тохирох мэдээлэл байхгүй байна. Та манай ажилтантай холбогдож лавлаарай. "
                "манай борлуулалтын албатай 9430-7017 "
                "дугаараар холбогдоорой 😊"
            )

            image_keys = []

        print(
            "AI REPLY:",
            reply
        )

        print(
            "AI IMAGE KEYS:",
            image_keys
        )

        # =====================================================
        # HISTORY
        # =====================================================

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

        # =====================================================
        # FACEBOOK TEXT
        # =====================================================

        send_fb_message(
            sender_id,
            reply
        )

        # =====================================================
        # FACEBOOK IMAGE
        # =====================================================

        send_images_by_keys(
            sender_id,
            image_keys
        )

    except Exception as e:

        print(
            "Error processing AI response:",
            repr(e)
        )

        send_fb_message(
            sender_id,
            "Уучлаарай, түр зуурын техникийн алдаа гарлаа. "
            "Та түр хүлээгээрэй. 😊"
        )


# =========================================================
# META WEBHOOK VERIFICATION
# =========================================================

@app.get("/webhook")
async def verify_webhook(
    request: Request
):

    params = request.query_params

    mode = params.get(
        "hub.mode"
    )

    token = params.get(
        "hub.verify_token"
    )

    challenge = params.get(
        "hub.challenge"
    )

    if (
        mode == "subscribe"
        and token == VERIFY_TOKEN
    ):
        return Response(
            content=challenge or "",
            media_type="text/plain",
        )

    raise HTTPException(
        status_code=403,
        detail="Verification failed",
    )


# =========================================================
# META WEBHOOK RECEIVE MESSAGE
# =========================================================

@app.post("/webhook")
async def handle_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):

    try:

        data = await request.json()

    except Exception:

        return Response(
            content="INVALID_JSON",
            status_code=400,
        )

    if data.get("object") != "page":

        return Response(
            content="NOT_A_PAGE_EVENT",
            status_code=404,
        )

    for entry in data.get(
        "entry",
        []
    ):

        for messaging_event in entry.get(
            "messaging",
            []
        ):

            message = messaging_event.get(
                "message"
            )

            if not message:
                continue

            # Bot өөрийн echo message-ийг дахин боловсруулахгүй.
            if message.get("is_echo"):
                continue

            sender = messaging_event.get(
                "sender",
                {}
            )

            sender_id = sender.get(
                "id"
            )

            if not sender_id:
                continue

            user_text = message.get(
                "text",
                ""
            ).strip()

            if not user_text:
                continue

            print(
                "=" * 60
            )

            print(
                "USER:",
                sender_id
            )

            print(
                "MESSAGE:",
                user_text
            )

            print(
                "=" * 60
            )

            background_tasks.add_task(
                process_ai_response,
                sender_id,
                user_text,
            )

    return Response(
        content="EVENT_RECEIVED",
        status_code=200,
    )


# =========================================================
# ROOT
# =========================================================

@app.get("/")
async def root():

    return {
        "status": "Miners Villa bot is running",
        "photo_folder": str(PHOTO_FOLDER),
        "image_count": len(IMAGE_LIBRARY),
        "image_base_url_configured": bool(
            IMAGE_BASE_URL
        ),
        "gemini_model": GEMINI_MODEL,
    }