import os
import requests
from fastapi import FastAPI, Request, Response, BackgroundTasks, HTTPException
from google import genai

app = FastAPI()

# Орчны хувьсагчууд
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "miners_villa_secret_123")
META_PAGE_ACCESS_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Ботын зан төлөв ба мэдээллийн бааз
SYSTEM_PROMPT = """
Та бол Miners Villa төслийн 23 настай, эелдэг зөөлөн ааштай борлуулагч юм.
Хэрэглэгчийн асуултад маш эелдэг бөгөөд 2-3 ӨГҮҮЛБЭРТ багтаан тодорхой, гүйцэд хариулна уу.
Урт нуршуу бичихгүй. Мэдээллийн үнэн бодит эх сурвалжтай хариулна.
Зөвхөн Miners Villa төслийн талаар мэдээлэл өгнө.

Дараах мэдээллийг ашиглан хариулна:

1. Ерөнхий мэдээлэл ба Үнэ:
- Мкв үнэ: 5,500,000 - 5,800,000 ₮
- Төлбөрийн нөхцөл: Урьдчилгаа 30%, Явцын төлбөр 40%, Явцын төлбөр 20%, Түлхүүр гардуулахад 10%.
- Явцын төлбөрт зөвхөн байрны бартер сонсоно.
- Борлуулалтын оффис: Эрдэнэт хот 1/16-р байрны зүүн урд буланд төв зам дагуу.
- Утас: 9430-7017

2. Хаус төрөл & Мкв:
- Таун хаус: 213.33 мкв болон 267.48 мкв.
- Мульт хаус: A-126мкв, B-125.21мкв, C-192.25мкв, D-189.64мкв, F-136.42мкв, G-178.39мкв, H-198.52мкв, I-189.52мкв.

3. Ашиглалтад орох хугацаа:
- 2026 оны өвөл гэхэд дотоод заслын ажлыг эхлүүлэхээр шаргуу ажиллаж байна.

4. Төслийн байршил:
- Баян-Өндөр уулын зүүн энгэрт, Бүсийн оношилгооны төв, Медипас эмнэлгийн ард 30.8 га талбайд.

5. Төлбөр төлөлт:
- Гэрээн дээрх Хаан банкны данс руу шилжүүлнэ. Гүйлгээний утгад: Гэрээний дугаар, Байрны тоот, Овог нэр, Регистр.

6. Барилгын явц:
- 7 хоног бүрийн 1 дэх өдөр Facebook Page болон Instagram хаяг дээр Reel хэлбэрээр мэдээлэл шинэчлэгдэн орно.
"""

# Client үүсгэх
client = genai.Client(api_key=GEMINI_API_KEY)

def send_fb_message(recipient_id: str, text: str):
    """Facebook Messenger API руу хариу мессеж илгээх"""
    url = f"https://graph.facebook.com/v20.0/me/messages?access_token={META_PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        res = requests.post(url, json=payload, headers=headers)
        print(f"FB Send API Status Code: {res.status_code}")
        print(f"FB Send API Response Body: {res.text}")
        res.raise_for_status()
    except Exception as e:
        print(f"Error sending message to Facebook: {e}")

def process_ai_response(sender_id: str, user_text: str):
    """Gemini-ээс хариу аваад FB руу илгээх"""
    try:
        # Prompt болон хэрэглэгчийн асуултыг нэгтгэж илгээнэ (AFC алдаанаас бүрэн сэргийлнэ)
        full_prompt = f"{SYSTEM_PROMPT}\n\nХэрэглэгчийн мессеж: {user_text}\nХариулт:"
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=full_prompt
        )
        
        ai_text = response.text
        print(f"Generated AI Response: {ai_text}")
        send_fb_message(sender_id, ai_text)
        
    except Exception as e:
        print(f"Error processing AI response: {e}")

@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    
    raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()

    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                if messaging_event.get("message") and not messaging_event["message"].get("is_echo"):
                    sender_id = messaging_event["sender"]["id"]
                    user_text = messaging_event["message"].get("text", "")

                    if user_text:
                        print(f"Received message from {sender_id}: {user_text}")
                        background_tasks.add_task(process_ai_response, sender_id, user_text)

        return Response(content="EVENT_RECEIVED", status_code=200)

    return Response(content="NOT_A_PAGE_EVENT", status_code=404)

@app.get("/")
async def root():
    return {"status": "Bot server is running successfully!"}