import os
import json
import time
import re
import requests
from pathlib import Path
from urllib.parse import quote
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from groq import Groq

import requests, json
import mimetypes


# =========================================================
# .env Тохиргоо
# =========================================================

load_dotenv()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "miners_villa_secret_123")
META_PAGE_ACCESS_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")


# =========================================================
# APP + PHOTO ROUTE (Case-Insensitive & Reliable)
# =========================================================

app = FastAPI(title="Miners Villa Messenger Bot")

BASE_DIR = Path(__file__).resolve().parent
PHOTO_FOLDER = BASE_DIR / "photo"
PHOTO_FOLDER.mkdir(parents=True, exist_ok=True)

@app.get("/photo/{filename}")
async def get_photo(filename: str):
    # 1. Шууд хайх
    file_path = PHOTO_FOLDER / filename
    if file_path.is_file():
        media_type, _ = mimetypes.guess_type(str(file_path))
        return FileResponse(
            file_path, 
            media_type=media_type or "image/png",
            headers={"Cache-Control": "public, max-age=31536000"}
        )

    # 2. Том жижиг үсэг харгалзахгүй
    target = filename.lower()
    for f in PHOTO_FOLDER.iterdir():
        if f.is_file() and f.name.lower() == target:
            media_type, _ = mimetypes.guess_type(str(f))
            return FileResponse(f, media_type=media_type or "image/png", headers={"Cache-Control": "public, max-age=31536000"})

    # 3. Өргөтгөлгүй хайх
    target_stem = Path(filename).stem.lower()
    for f in PHOTO_FOLDER.iterdir():
        if f.is_file() and f.stem.lower() == target_stem:
            media_type, _ = mimetypes.guess_type(str(f))
            return FileResponse(f, media_type=media_type or "image/png", headers={"Cache-Control": "public, max-age=31536000"})

    raise HTTPException(status_code=404, detail="Photo not found")


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

IMAGE_KEYS = list(IMAGE_LIBRARY.keys())


# =========================================================
# CONVERSATION MEMORY
# =========================================================

CONVERSATIONS: Dict[str, List[Dict[str, str]]] = {}
MAX_HISTORY = 8


# =========================================================
# MINERS VILLA DATA
# =========================================================

PRICE_MIN = 5_500_000
PRICE_MAX = 5_800_000
SALES_PHONE = "9430-7017"

SALES_OFFICE = "Эрдэнэт хот, 1/16-р байрны зүүн урд буланд, төв зам дагуу"
LOCATION_TEXT = "Баян-Өндөр уулын зүүн энгэрт, Бүсийн оношилгооны төвийн ард, Медипас эмнэлгийн ард, 30.8 га талбайд байрладаг."
PAYMENT_TEXT = "30% урьдчилгаа, 40% явцын төлбөр, 20% явцын төлбөр, 10% түлхүүр гардуулах үед. Явцын төлбөрт зөвхөн байрны бартер сонсоно."
PARKING_TEXT = "Мульт хаусын Б1 болон 1-р давхарт нэгдсэн дулаан зогсоол байрлана. Зогсоолын үнэ 50,000,000 ₮."
UNKNOWN_TEXT = "Уучлаарай, би энэ асуултыг сайн ойлгосонгүй. Та асуултаа арай дэлгэрэнгүй бичнэ үү, эсвэл манай борлуулалтын албатай 9430-7017 дугаараар холбогдон лавлах боломжтой 😊"


# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
ТА БОЛ "МИНА" — MINERS VILLA ТӨСЛИЙН 23 НАСТАЙ, ЭЕЛДЭГ, ЗӨӨЛӨН, ТУСЧ БОРЛУУЛАГЧ.

ЗОРИЛГО БОЛОН ҮҮРЭГ:
1. Автомат түлхүүр үгэнд таараагүй үед зөвөөр ойлгож тайлбарлах.
2. Худал мэдээлэл зохиохгүй, мэдэхгүй зүйл байвал 9430-7017 дугаар руу холбогдохыг эелдгээр зөвлөх.

ҮНДСЭН МЭДЭЭЛЭЛ:
* М² үнэ: 5,500,000 - 5,800,000 ₮
* Борлуулалтын утас: 9430-7017
* Төлбөр: 30% урьдчилгаа, 40%, 20% явцын төлбөр, 10% үлдэгдэл. Бартер зөвхөн байраар.
* Загвар: Таун хаус (213.33-267.48 м²), Мульт хаус (125.21-198.52 м²). Сингл, Твин дууссан.
* Ашиглалтад орох: 2026 оны өвөл дотоод засал эхэлнэ. Яг таг хугацаа зохиож болохгүй.
"""


# =========================================================
# HELPERS
# =========================================================

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s\.,]", " ", text)
    
    replacements = {"ё": "е", "өү": "оу", "ү": "у", "ө": "о", "v": "u", "w": "v"}
    for old, new in replacements.items():
        text = text.replace(old, new)
        
    word_replacements = {
        "mdll": "medeelel", "mdlel": "medeelel", "mdeelel": "medeelel", 
        "brshil": "bairshil", "tlbur": "tulbur", "zgsol": "zogsool", 
        "uts": "utas", "mkv": "m2", "мкв": "м2"
    }
    words = text.split()
    normalized_words = [word_replacements.get(w, w) for w in words]
    return " ".join(normalized_words).strip()

def match_any(keywords: List[str], normalized_text: str) -> bool:
    return any(normalize_text(kw) in normalized_text for kw in keywords)

def resolve_photo_file(stem: str) -> Optional[Path]:
    if not PHOTO_FOLDER.exists():
        return None
    for file in PHOTO_FOLDER.iterdir():
        if file.is_file() and file.stem.lower() == stem.lower():
            return file
    return None

def get_public_image_url(filename: str) -> str:
    # Энд байгаа хаягийг Render дээр өгсөн өөрийнхөө бодит хаягаар солино
    base_url = "https://miners-villa-bot.onrender.com/photo"
    return f"{base_url}/{quote(filename, safe='')}"

def add_to_history(sender_id: str, role: str, text: str):
    history = CONVERSATIONS.setdefault(sender_id, [])
    history.append({"role": role, "text": text})
    if len(history) > MAX_HISTORY:
        del history[:-MAX_HISTORY]

def history_text(sender_id: str) -> str:
    history = CONVERSATIONS.get(sender_id, [])
    if not history: return "Өмнөх яриа байхгүй."
    return "\n".join(f"{item['role']}: {item['text']}" for item in history)


# =========================================================
# DIRECT IMAGE ROUTER
# =========================================================

def direct_image_router(user_text: str, sender_id: str = "") -> Optional[List[str]]:
    t = normalize_text(user_text)

    mult_image_map = {
        "126.32": "MULT_126_32", "126": "MULT_126",
        "125.21": "MULT_125", "125": "MULT_125",
        "120.85": "MULT_120", "120": "MULT_120",
        "116": "MULT_116", "100.77": "MULT_100", "100": "MULT_100",
        "136.42": "MULT_136", "136": "MULT_136",
        "178.39": "MULT_178", "178": "MULT_178",
        "189.64": "MULT_189_64", "189.52": "MULT_189", "189": "MULT_189",
        "192.25": "MULT_192", "192": "MULT_192",
        "198.52": "MULT_198", "198": "MULT_198",
    }
    
    for size in sorted(mult_image_map.keys(), key=len, reverse=True):
        pattern = r"\b" + size.replace(".", r"\.").replace(",", r"\,") + r"\b"
        if re.search(pattern, t):
            return ["MULT", mult_image_map[size]]

    if re.search(r"\b(212|213)\b", t): return ["TOWNHOUSE_212", "TOWNHOUSE_212_1", "GENERAL_PLAN"]
    if re.search(r"\b(266|267)\b", t): return ["TOWNHOUSE_266", "TOWNHOUSE_266_1", "GENERAL_PLAN"]

    if match_any(["таун хаус", "таунхаус", "таун", "taun", "townhouse"], t): 
        return ["TOWNHOUSE_212", "TOWNHOUSE_266", "GENERAL_PLAN"]

    if match_any(["мульт хаус", "мультхаус", "мульт", "mult", "мулт"], t): 
        return ["MULT", "MULT_125", "MULT_126"]

    parking_kws = ["зогсоол", "гараж", "гараш", "гарааш", "zogsool", "garaash", "garaj"]
    if match_any(parking_kws, t): return ["MULT_PARKING_SPACE", "MULT_PARKING_SPACE_1"]

    photo_only_kws = ["зураг", "зураг үзье", "zurag", "photo"]
    if match_any(photo_only_kws, t):
        hist_text = normalize_text(history_text(sender_id))
        if match_any(["таун", "townhouse"], hist_text): return ["TOWNHOUSE_212", "TOWNHOUSE_266"]
        if match_any(["мульт", "mult"], hist_text): return ["MULT", "MULT_125"]
        return ["GENERAL_PLAN"]

    return None


# =========================================================
# DIRECT FAQ ROUTER (Returns text, show_carousel, custom_quick_replies)
# =========================================================

def direct_faq_router(user_text: str, sender_id: str = "") -> Optional[Tuple[str, bool, Optional[List[Dict]]]]:
    t = normalize_text(user_text)

    default_buttons = [
        {"content_type": "text", "title": "🏡 Таун хаус", "payload": "PAYLOAD_TOWN"},
        {"content_type": "text", "title": "🏢 Мульт хаус", "payload": "PAYLOAD_MULT"},
        {"content_type": "text", "title": "💰 Үнэ", "payload": "PAYLOAD_PRICE"}
    ]

    model_buttons = [
        {"content_type": "text", "title": "🏡 Таун хаус", "payload": "PAYLOAD_TOWN"},
        {"content_type": "text", "title": "🏢 Мульт хаус", "payload": "PAYLOAD_MULT"},
        {"content_type": "text", "title": "☎️ Холбоо барих", "payload": "PAYLOAD_CONTACT"}
    ]

    # 1. Мэндчилгээ болон Эхлэл
    greetings = ["сайн уу", "сайн байна уу", "hello", "hi", "мэнд", "get started", "start", "эхлэх"]
    if match_any(greetings, t) and len(t.split()) <= 4:
        reply = (
            "Сайн байна уу? Тав тух, үнэ цэнийн илэрхийлэл болсон 'Miners Villa' төслийн "
            "албан ёсны чатботод тавтай морил! \n\n"
            "Урьд нь 'Уурхайчин-3' нэртэй байсан манай төсөл илүү өргөжиж, хүн бүхэнд нээлттэй "
            "амины орон сууцны цогцолбор хотхон болсныг дуулгахад таатай байна. Би танд ямар мэдээлэл өгч туслах вэ? 👇"
        )
        return (reply, True, None)

    # 2. Таун хаус сонгох үед
    if match_any(["таун хаус", "таунхаус", "таун", "taun", "townhouse"], t):
        reply = (
            "🏡 **Таун хаус (Townhouse)**\n\n"
            "• Сонголт: 213.33 м², 267.48 м²\n"
            "• Үнэ: м² нь 5,500,000 – 5,800,000 ₮\n"
            "• Онцлог: Дээд зэрэглэлийн тав тухтай амины орон сууц.\n\n"
            "Дэлгэрэнгүй зургуудыг доор харууллаа 👇"
        )
        return (reply, False, model_buttons)

    # 3. Мульт хаус сонгох үед
    if match_any(["мульт хаус", "мультхаус", "мульт", "mult", "мулт"], t):
        reply = (
            "🏢 **Мульт хаус (Multi-family house)**\n\n"
            "• Сонголт: 125.21 м², 126 м², 136.42 м², 178.39 м², 189.52 м², 189.64 м², 192.25 м², 198.52 м²\n"
            "• Үнэ: м² нь 5,500,000 – 5,800,000 ₮\n\n"
            "Сонирхож буй м²-ээ бичиж (жишээ нь: 126 эсвэл 178) дэлгэрэнгүй зураг авах боломжтой 😊"
        )
        return (reply, False, model_buttons)

    # 4. Загварын сонголт / мкв / хэмжээ
    model_keywords = ["сонголт", "загвар", "хэмжээ", "мкв", "м2", "квадрат", "songolt", "zagvar", "mkv"]
    if match_any(model_keywords, t):
        reply = (
            "Манай төслийн загварын сонголтууд:\n\n"
            "🏡 Таун хаус: 213.33 м², 267.48 м²\n"
            "🏢 Мульт хаус: 125.21 м², 126 м², 136.42 м², 178.39 м², 189.52 м², 189.64 м², 192.25 м², 198.52 м²\n\n"
            "(Сингл болон Твин хаусны борлуулалт дууссан). Доорх товчлуураар загвараа сонгоно уу 👇"
        )
        return (reply, False, model_buttons)

    # 5. Үнэ
    price_keywords = ["үнэ", "үнийн", "үнэтэй", "м2 үнэ", "une", "vne", "xed", "hed"]
    if match_any(price_keywords, t):
        reply = (
            "Одоогийн м² үнэ 5,500,000–5,800,000 ₮ байна. "
            "Дэлгэрэнгүй үнийн саналыг борлуулалтын албаны "
            f"{SALES_PHONE} дугаараас лавлаарай 😊"
        )
        return (reply, False, default_buttons)

    # 6. Байршил
    location_keywords = ["байршил", "хаана байдаг", "хаана вэ", "bairshil", "haana"]
    if match_any(location_keywords, t):
        return (f"Miners Villa нь {LOCATION_TEXT} Дэлгэрэнгүйг: {SALES_PHONE} 😊", False, default_buttons)

    # 7. Утас
    phone_keywords = ["утас", "дугаар", "холбоо барих", "залгах", "utas", "dugaar"]
    if match_any(phone_keywords, t) and not match_any(["оффис"], t):
        return (f"Манай борлуулалтын утас: {SALES_PHONE} 😊", False, default_buttons)

    # 8. Мэдээлэл
    info_keywords = ["мэдээлэл", "дэлгэрэнгүй", "танилцуулга", "medeelel", "taniltsuulga"]
    if match_any(info_keywords, t) and len(t.split()) <= 4:
        reply = (
            "\"Miners Villa\" төсөл:\n"
            "✨ Байршил: Баян-Өндөр хайрхны зүүн энгэрт.\n"
            "✨ Дэд бүтэц: Төвийн дулаан, цахилгаан, цэвэр, бохирт холбогдсон.\n"
            "✨ Эко орчин: 30.8 га талбайн 60% нь ногоон байгууламж.\n"
            "✨ Сонголт: Таун (Town) болон Мульт (Multi) хаусууд.\n\n"
            f"Дэлгэрэнгүй мэдээлэл авахыг хүсвэл {SALES_PHONE} дугаартай холбогдоорой! ✨"
        )
        return (reply, False, default_buttons)
        
    # 9. Онцлог
    features_keywords = ["онцлог", "давуу тал", "ялгаа", "ontslog", "davuu tal"]
    if match_any(features_keywords, t):
        reply = (
            "Төслийн онцлог, давуу талууд:\n"
            "✅ Найдвартай дэд бүтэц (Төвийн бүрэн холболт)\n"
            "✅ 24 цагийн харуул хамгаалалт, 2.2км хүрээлсэн хашаа\n"
            "✅ Автомашингүй ногоон бүс, байгалийн гэрэлтүүлэг сайтай\n"
            "✅ Насны онцлогт тохирсон 4 төрлийн тоглоомын талбай\n"
            "✅ 400 орчим автомашины нэгдсэн дулаан зогсоол"
        )
        return (reply, False, default_buttons)

    # 10. Төлбөрийн нөхцөл
    payment_keywords = ["төлбөр", "төлбөрийн нөхцөл", "урьдчилгаа", "tulbur", "urdchilgaa"]
    if match_any(payment_keywords, t):
        return (PAYMENT_TEXT, False, default_buttons)
        
    # 11. Зогсоол
    parking_keywords = ["зогсоол", "гарааш", "б1", "zogsool", "garaash"]
    if match_any(parking_keywords, t):
        return (PARKING_TEXT, False, default_buttons)
        
    # 12. Ашиглалтад орох
    completion_keywords = ["ашиглалт", "хэзээ орох", "ashiglalt", "hezee oroh"]
    if match_any(completion_keywords, t):
        return ("2026 оны өвөл гэхэд дотоод заслын ажлыг эхлүүлэхээр ажиллаж байна. Дэлгэрэнгүйг 9430-7017 дугаараас лавлана уу 😊", False, default_buttons)

    return None


# =========================================================
# FACEBOOK MESSENGER (API)
# =========================================================

def messenger_url():
    return f"https://graph.facebook.com/v20.0/me/messages?access_token={META_PAGE_ACCESS_TOKEN}"

def send_fb_message(recipient_id: str, text: str, quick_replies: Optional[List[Dict]] = None):
    if not META_PAGE_ACCESS_TOKEN: return
    
    message_data = {"text": text}
    if quick_replies:
        message_data["quick_replies"] = quick_replies
        
    payload = {"recipient": {"id": recipient_id}, "message": message_data}
    try:
        requests.post(messenger_url(), json=payload, headers={"Content-Type": "application/json"}, timeout=10)
    except Exception as e:
        print("Error sending text:", repr(e))

def send_carousel_menu(recipient_id: str):
    if not META_PAGE_ACCESS_TOKEN: return
    
    # 1. Эхний картын зураг (Таны саяын оруулсан линк)
    card1_url = "https://miners-villa-bot.onrender.com/photo/general.png"
    
    # 2. Хоёр дахь картын зураг (Хэрэв 2 дахь зургаа бас жижгэрүүлээд .png болгосон бол ингэж тавина)
    # Жич: Хэрэв 2 дахь зураг чинь .jpg хэвээрээ байгаа бол Green_garden.jpg гэж бичээрэй
    card2_url = "https://miners-villa-bot.onrender.com/photo/Green_garden.png" 
    
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": [
                        {
                            "title": "MINERS VILLA ТӨСӨЛ",
                            "subtitle": "Тав тух, үнэ цэнийн илэрхийлэл болсон хотхон",
                            "image_url": card1_url,
                            "buttons": [
                                {"type": "postback", "title": "💰 Үнийн мэдээлэл", "payload": "PAYLOAD_PRICE"},
                                {"type": "postback", "title": "ℹ️ Ерөнхий танилцуулга", "payload": "PAYLOAD_INFO"},
                                {"type": "postback", "title": "🏠 Загварын сонголт", "payload": "PAYLOAD_MODEL"}
                            ]
                        },
                        {
                            "title": "MINERS VILLA ТӨСӨЛ",
                            "subtitle": "Хүн бүхэнд нээлттэй амины орон сууцны цогцолбор",
                            "image_url": card2_url,
                            "buttons": [
                                {"type": "postback", "title": "📍 Төслийн байршил", "payload": "PAYLOAD_LOCATION"},
                                {"type": "postback", "title": "🌳 Төслийн онцлог", "payload": "PAYLOAD_FEATURES"},
                                {"type": "postback", "title": "☎️ Холбоо барих", "payload": "PAYLOAD_CONTACT"}
                            ]
                        }
                    ]
                }
            }
        }
    }
    
    try:
        requests.post(messenger_url(), json=payload, headers={"Content-Type": "application/json"}, timeout=10)
    except Exception as e:
        print("Error sending Carousel:", repr(e))

def send_images_by_keys(recipient_id: str, image_keys: List[str]):
    if not image_keys or not META_PAGE_ACCESS_TOKEN: return

    elements = []
    seen = set()
    for key in image_keys[:4]:
        if key in seen or key not in IMAGE_LIBRARY: continue
        seen.add(key)
        stem = IMAGE_LIBRARY[key]
        local_path = resolve_photo_file(stem)

        if local_path and local_path.is_file():
            public_url = get_public_image_url(local_path.name)
            if public_url:
                elements.append({
                    "title": f"Miners Villa - {key.replace('_', ' ')}",
                    "image_url": public_url,
                    "buttons": [{"type": "web_url", "url": public_url, "title": "🔍 Томруулж харах"}]
                })

    if not elements: return

    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {"template_type": "generic", "elements": elements}
            }
        }
    }

    try:
        requests.post(messenger_url(), json=payload, headers={"Content-Type": "application/json"}, timeout=10)
    except Exception as e:
        print("Error sending images:", repr(e))


# =========================================================
# GROQ AI (META LLAMA 3)
# =========================================================

def ask_groq(sender_id: str, user_text: str):
    if not client: return UNKNOWN_TEXT, []
    
    prompt = f"""
{SYSTEM_PROMPT}

ӨМНӨХ ЯРИА: {history_text(sender_id)}
ШИНЭ МЕССЕЖ: {user_text}

JSON буцаах формат:
{{ "reply": "Эелдэг, богино хариулт", "image_keys": [] }}
"""
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful assistant designed to output only JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3, max_tokens=500,
        )
        data = json.loads(response.choices[0].message.content.strip())
        reply = str(data.get("reply", UNKNOWN_TEXT)).strip()
        keys = [k for k in data.get("image_keys", []) if k in IMAGE_LIBRARY]
        return reply, keys[:4]
    except Exception as e:
        print("GROQ Error:", e)
        return UNKNOWN_TEXT, []


# =========================================================
# PROCESS RESPONSE
# =========================================================

def process_ai_response(sender_id: str, user_text: str):
    try:
        faq_result = direct_faq_router(user_text, sender_id)
        image_result = direct_image_router(user_text, sender_id)

        default_buttons = [
            {"content_type": "text", "title": "🏡 Таун хаус", "payload": "PAYLOAD_TOWN"},
            {"content_type": "text", "title": "🏢 Мульт хаус", "payload": "PAYLOAD_MULT"},
            {"content_type": "text", "title": "💰 Үнэ", "payload": "PAYLOAD_PRICE"}
        ]

        if faq_result or image_result:
            if faq_result:
                reply, show_carousel, custom_buttons = faq_result
            else:
                reply = "Мэдээж 😊 Дэлгэрэнгүй зургийг явууллаа."
                show_carousel = False
                custom_buttons = default_buttons

            add_to_history(sender_id, "user", user_text)
            add_to_history(sender_id, "assistant", reply)

            if show_carousel:
                send_fb_message(sender_id, reply)
                send_carousel_menu(sender_id)
            else:
                send_fb_message(sender_id, reply, quick_replies=custom_buttons or default_buttons)
                
            if image_result:
                send_images_by_keys(sender_id, image_result[:4])
            return

        reply, image_keys = ask_groq(sender_id, user_text)
        add_to_history(sender_id, "user", user_text)
        add_to_history(sender_id, "assistant", reply)

        send_fb_message(sender_id, reply, quick_replies=default_buttons)
        if image_keys:
            send_images_by_keys(sender_id, image_keys[:4])

    except Exception as e:
        print("Response Process Error:", repr(e))
        send_fb_message(sender_id, "Уучлаарай, түр зуурын алдаа гарлаа. 9430-7017 дугаараар холбогдоорой 😊")


# =========================================================
# META WEBHOOKS
# =========================================================

@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
    except Exception:
        return Response(content="INVALID_JSON", status_code=400)

    if data.get("object") != "page":
        return Response(content="NOT_A_PAGE_EVENT", status_code=404)

    payload_map = {
        "GET_STARTED": "сайн уу",
        "PAYLOAD_PRICE": "үнэ",
        "PAYLOAD_INFO": "танилцуулга",
        "PAYLOAD_MODEL": "сонголт",
        "PAYLOAD_LOCATION": "байршил",
        "PAYLOAD_FEATURES": "онцлог",
        "PAYLOAD_CONTACT": "утас",
        "PAYLOAD_TOWN": "таун хаус",
        "PAYLOAD_MULT": "мульт хаус"
    }

    for entry in data.get("entry", []):
        for messaging_event in entry.get("messaging", []):
            sender_id = messaging_event.get("sender", {}).get("id")
            
            message = messaging_event.get("message")
            postback = messaging_event.get("postback")
            
            user_text = ""
            if message and not message.get("is_echo"):
                if "quick_reply" in message:
                    raw_payload = message["quick_reply"].get("payload", "").strip()
                    user_text = payload_map.get(raw_payload, raw_payload)
                else:
                    user_text = message.get("text", "").strip()
            elif postback:
                raw_payload = postback.get("payload", "").strip()
                user_text = payload_map.get(raw_payload, raw_payload)

            if sender_id and user_text:
                background_tasks.add_task(process_ai_response, sender_id, user_text)

    return Response(content="EVENT_RECEIVED", status_code=200)

@app.get("/")
async def root():
    return {"status": "Miners Villa bot is running reliably"}