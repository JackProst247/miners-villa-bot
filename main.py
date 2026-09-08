import os
import json
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

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "miners_villa_secret_123")
META_PAGE_ACCESS_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Messenger зураг авахад ашиглах PUBLIC HTTPS URL.
# Жишээ:
# IMAGE_BASE_URL=https://xxxx.trycloudflare.com/photo
IMAGE_BASE_URL = os.getenv("IMAGE_BASE_URL", "").rstrip("/")

# Gemini model. Google-ийн одоогийн жишээнүүдтэй нийцүүлж env-ээр сольж болдог.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")

# =========================================================
# APP + PHOTO FOLDER
# =========================================================
app = FastAPI(title="Miners Villa Messenger Bot")

BASE_DIR = Path(__file__).resolve().parent
PHOTO_FOLDER = BASE_DIR / "photo"
PHOTO_FOLDER.mkdir(parents=True, exist_ok=True)

# D:\Miners Villa bot\photo\ файлуудыг
# https://PUBLIC_URL/photo/filename хэлбэрээр нээх боломжтой болгоно.
app.mount(
    "/photo",
    StaticFiles(directory=str(PHOTO_FOLDER)),
    name="photo",
)

# =========================================================
# IMAGE LIBRARY
# Зургийн жинхэнэ filename-уудыг screenshot дээрхтэй тааруулсан.
# Файлын нэрийг дахин солих шаардлагагүй.
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

    # Мульт хаус зогсоолын зураг
    # Файлын нэр Windows Explorer дээр таслагдаж харагдаж байгаа тул
    # яг бүтэн нэрийг дараа нь нягталж болно.

    # Таун хаус
    "TOWNHOUSE_212": "townhouse_212",
    "TOWNHOUSE_212_1": "townhouse_212_1",
    "TOWNHOUSE_266": "townhouse_266",
    "TOWNHOUSE_266_1": "townhouse_266_1",
}


# Gemini зөвхөн эдгээр KEY-ээс сонгоно.
IMAGE_KEYS = list(IMAGE_LIBRARY.keys())

# =========================================================
# SIMPLE CONVERSATION MEMORY
# "267?" гэх мэт богино follow-up асуултад тусална.
# Server restart хийхэд memory цэвэрлэгдэнэ.
# =========================================================
CONVERSATIONS: Dict[str, List[Dict[str, str]]] = {}
MAX_HISTORY = 8

# =========================================================
# MINERS VILLA SYSTEM PROMPT
# =========================================================
SYSTEM_PROMPT = """
ТА БОЛ "МИНА" — MINERS VILLA ТӨСЛИЙН 23 НАСТАЙ, ЭЕЛДЭГ,
ЗӨӨЛӨН, ТУСЧ БОРЛУУЛАГЧ.

ЗОРИЛГО:
- Хэрэглэгчид Miners Villa-ийн талаар үнэн зөв мэдээлэл өгөх
- Асуултад яг тохирсон, богино хариулт өгөх
- Хэт робот шиг, хэт албан ёсны бичихгүй
- Хэрэглэгчийг дарамтлахгүйгээр шаардлагатай үед борлуулалтын багтай холбох

ХЭЛ, ӨНГӨ:
- Монгол хэлээр хариул.
- Дулаан, эелдэг, хүнтэй ярилцаж байгаа мэт бич.
- Ихэнх хариулт 1-3 өгүүлбэр байна.
- Шаардлагатай үед emoji ашиглаж болно.
- Бүх хариултын төгсгөлд CTA хийх шаардлагагүй.
- Хэрэглэгч мэндэлбэл мэндэлж хариул.
- Хэрэглэгчийн асуултыг уртаар давтахгүй.

МЭДЭЭЛЛИЙН ҮНДСЭН САН:
- Төслийн нэр: Miners Villa
- М² үнэ: 5,500,000 - 5,800,000 ₮
- Борлуулалтын утас: 9430-7017
- Борлуулалтын оффис: Эрдэнэт хот, 1/16-р байрны зүүн урд буланд, төв зам дагуу.

ТӨЛБӨРИЙН НӨХЦӨЛ:
- Урьдчилгаа: 30%
- Явцын төлбөр: 40%
- Явцын төлбөр: 20%
- Түлхүүр гардуулахад: 10%
- Явцын төлбөрт зөвхөн байрны бартер сонсоно.
- Машин, газар, бизнесийн бартер зөвшөөрсөн гэж хэлж болохгүй.

ТАУН ХАУС:
- 213.33 м²
- 267.48 м²

МУЛЬТ ХАУС:
- A — 126 м²
- B — 125.21 м²
- C — 192.25 м²
- D — 189.64 м²
- F — 136.42 м²
- G — 178.39 м²
- H — 198.52 м²
- I — 189.52 м²

БАЙРШИЛ:
- Баян-Өндөр уулын зүүн энгэрт
- Бүсийн оношилгооны төвийн ард
- Медипас эмнэлгийн ард
- 30.8 га талбайд.

БАРИЛГЫН АЖИЛ:
- 2026 оны өвөл гэхэд дотоод заслын ажлыг эхлүүлэхээр ажиллаж байна.
- Үүнийг баталгаатай ашиглалтад орох огноо мэтээр хэлж болохгүй.

ТӨЛБӨР ТӨЛӨХ:
- Гэрээн дээрх Хаан банкны данс руу шилжүүлнэ.
- Гүйлгээний утгад гэрээний дугаар, байрны тоот, овог нэр, регистр зэргийг бичнэ.
- Дансны дугаарыг prompt-д өгөөгүй тул зохиож болохгүй.
- Данс асуувал: "Дансны дугаар нь гэрээнд заасан Хаан банкны данс байна. Тодруулах шаардлагатай бол 9430-7017 дугаарт холбогдоорой 😊"

БАРИЛГЫН ЯВЦ:
- 7 хоног бүрийн 1 дэх өдөр Facebook Page болон Instagram дээр Reel хэлбэрээр шинэчилж хүргэдэг.

МЭДЭЭЛЭЛ БАЙХГҮЙ БОЛ:
"Энэ мэдээллийг одоогоор надад өгөөгүй байна. Дэлгэрэнгүй мэдээллийг 9430-7017 дугаараас лавлаарай 😊"
гэж хариул.

ХҮНТЭЙ ЯРИХ ХҮСЭЛТ:
"😊 Манай борлуулалтын албатай 9430-7017 дугаараар холбогдоорой."

ҮНЭ:
- "Үнэ хэд вэ?" гэвэл м² үнэ 5,500,000–5,800,000 ₮ гэж хэл.
- Мэдээллийн санд байхгүй м²-ийн нийт үнийг өөрөө тооцоолж баталгаатай үнэ мэтээр хэлэхгүй.

МЭДЭЭЛЭЛ ЗОХИОХГҮЙ:
Үнэ, талбай, байрны тоо, хугацаа, хөнгөлөлт, урамшуулал,
материал, зогсоол, сургууль, цэцэрлэг, үйлчилгээ болон бусад
өгөөгүй нөхцөлийг өөрөө зохиож болохгүй.

ЗУРГИЙН ГОЛ ДҮРЭМ:
Gemini зураг файлыг өөрөө сонгохгүй.
Зөвхөн доорх тогтмол IMAGE KEY-үүдээс сонгоно.
URL, filename, file path зохиож болохгүй.

IMAGE KEY-ҮҮД:
""" + "\n".join(f"- {k}" for k in IMAGE_KEYS) + """

ЗУРГИЙН СОНГОЛТЫН ЖИШЭЭ:
- "267 м² зураг" / "267 зураг" -> TOWNHOUSE_266
- "212/213 м² зураг" / "213 зураг" -> TOWNHOUSE_212
- "126 м² мульт" -> MULT_126
- "125.21 м² мульт" -> MULT_125
- "192.25 м² мульт" -> MULT_192
- "189.64 м² мульт" -> MULT_189_64
- "136.42 м² мульт" -> MULT_136
- "178.39 м² мульт" -> MULT_178
- "198.52 м² мульт" -> MULT_198
- "126.32 м² мульт" -> MULT_126_32
- "100.77 м² мульт" -> MULT_100
- "120.85 м² мульт" -> MULT_120
- "116 м² мульт" -> MULT_116
- "ерөнхий төлөвлөгөө" -> GENERAL_PLAN
- "ногоон байгууламж" / "ногоон цэцэрлэг" -> GREEN_GARDEN
- "тохижилт" -> LANDSCAPING
- "амрах талбай" -> RELAXATION_AREA
- "0-5 насны тоглоомын талбай" -> SPORTS_AREA_0_5
- "9-13 насны тоглоомын талбай" -> SPORTS_AREA_9_13
- "13-16 насны тоглоомын талбай" -> SPORTS_AREA_13_16
- "спортын талбайн төлөвлөгөө" -> SPORTS_AREA_PLAN
- "мульт хаусын ерөнхий зураг" -> MULT
- "таун хаусын зураг" -> TOWNHOUSE_266 болон TOWNHOUSE_212 хоёуланг явуулж болно.
- "мульт хаусын зураг" гэж ерөнхий асуулт бол MULT_126, MULT_125 зэрэг 2-3 тохирох загварын key сонгож болно.
- "план", "төлөвлөлт" гэж зураг хүсвэл тохирох зураг байгаа үед image_key сонго.
- Зөвхөн зураг байхгүй төрлийн талаар image key зохиож болохгүй.

ЧУХАЛ:
- Хэрэглэгч зураг хүсээгүй бол image_keys хоосон байна.
- Нэг хүсэлтэд шаардлагагүй олон зураг бүү явуул.
- Зөвхөн IMAGE KEY-ээр сонго.
- Хэрэв эргэлзээтэй бол image_keys=[].
"""

# =========================================================
# VALIDATION
# =========================================================
def check_environment():
    missing = []

    if not META_PAGE_ACCESS_TOKEN:
        missing.append("META_PAGE_ACCESS_TOKEN")

    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")

    if not IMAGE_BASE_URL:
        print("WARNING: IMAGE_BASE_URL тохируулаагүй байна.")
        print("Messenger зураг авахын тулд PUBLIC HTTPS URL шаардлагатай.")

    if missing:
        print("WARNING: .env дотор дутуу хувьсагч:", ", ".join(missing))


check_environment()

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# =========================================================
# HELPERS
# =========================================================
def resolve_photo_file(stem: str) -> Path | None:
    """photo хавтаснаас өгсөн filename stem-тэй файлыг extension-оос үл хамааран олно."""
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

    return "\n".join(
        f"{item['role']}: {item['text']}"
        for item in history
    )


# =========================================================
# FACEBOOK MESSENGER
# =========================================================
def messenger_url():
    return (
        "https://graph.facebook.com/v20.0/me/messages"
        f"?access_token={META_PAGE_ACCESS_TOKEN}"
    )


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
        print("Error sending text to Facebook:", e)


def send_fb_image(recipient_id: str, image_url: str):
    if not META_PAGE_ACCESS_TOKEN:
        print("ERROR: META_PAGE_ACCESS_TOKEN байхгүй.")
        return

    payload = {
        "recipient": {"id": recipient_id},
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
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        print("FB IMAGE:", response.status_code, response.text)
        response.raise_for_status()

    except Exception as e:
        print("Error sending image to Facebook:", e)


def send_images_by_keys(recipient_id: str, image_keys):
    if not image_keys:
        return

    # Давхардсан key-ийг арилгана.
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
            print("Image send error:", e)


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

Ийм бүтэцтэй байна:

{{
  "reply": "Хэрэглэгчид илгээх Монгол хэл дээрх богино хариулт",
  "image_keys": ["IMAGE_KEY"]
}}

Зураг шаардлагагүй бол:

{{
  "reply": "Хэрэглэгчид илгээх хариулт",
  "image_keys": []
}}

image_keys дотор ЗӨВХӨН prompt-д зөвшөөрсөн IMAGE KEY ашигла.
Filename, URL, Windows path бүү бич.
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
            max_output_tokens=500,
        ),
    )

    raw = (response.text or "").strip()

    print("GEMINI RAW:", raw)

    data = json.loads(raw)

    reply = str(data.get("reply", "")).strip()
    image_keys = data.get("image_keys", [])

    if not isinstance(image_keys, list):
        image_keys = []

    # Security/accuracy: Gemini зөвшөөрөгдөөгүй key өгсөн бол шууд хасна.
    valid_keys = [
        key for key in image_keys
        if isinstance(key, str) and key in IMAGE_LIBRARY
    ]

    if not reply:
        reply = (
            "Энэ мэдээллийг одоогоор надад өгөөгүй байна. "
            "Дэлгэрэнгүй мэдээллийг 9430-7017 дугаараас лавлаарай 😊"
        )

    return reply, valid_keys


def process_ai_response(sender_id: str, user_text: str):
    try:
        reply, image_keys = ask_gemini(sender_id, user_text)

        print("AI REPLY:", reply)
        print("AI IMAGE KEYS:", image_keys)

        # History-д AI хариуг хадгална.
        add_to_history(sender_id, "user", user_text)
        add_to_history(sender_id, "assistant", reply)

        # Эхлээд текст
        send_fb_message(sender_id, reply)

        # Дараа нь зураг
        send_images_by_keys(sender_id, image_keys)

    except json.JSONDecodeError as e:
        print("Gemini JSON parse error:", e)

        # JSON буруу ирсэн үед хэрэглэгчид raw JSON явуулахгүй.
        send_fb_message(
            sender_id,
            "Уучлаарай, түр зуур техникийн алдаа гарлаа. "
            "Дахин нэг асуугаад үзээрэй 😊"
        )

    except Exception as e:
        print("Error processing AI response:", repr(e))

        send_fb_message(
            sender_id,
            "Уучлаарай, түр зуур техникийн алдаа гарлаа. "
            "Дахин нэг асуугаад үзээрэй 😊"
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

    for entry in data.get("entry", []):
        for messaging_event in entry.get("messaging", []):

            # Bot өөрийн echo message-ийг дахин боловсруулахгүй.
            message = messaging_event.get("message")

            if not message:
                continue

            if message.get("is_echo"):
                continue

            sender = messaging_event.get("sender", {})
            sender_id = sender.get("id")

            if not sender_id:
                continue

            user_text = message.get("text", "").strip()

            if not user_text:
                # Одоогоор зөвхөн text message боловсруулах хувилбар.
                continue

            print("=" * 60)
            print("USER:", sender_id)
            print("MESSAGE:", user_text)
            print("=" * 60)

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
        "image_base_url_configured": bool(IMAGE_BASE_URL),
        "gemini_model": GEMINI_MODEL,
    }
