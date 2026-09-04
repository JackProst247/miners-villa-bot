import os
import requests
from fastapi import FastAPI, Request, Response, BackgroundTasks, HTTPException
from google import genai
from google.genai import types

app = FastAPI()

# Орчны хувьсагчууд
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "miners_villa_secret_123")
META_PAGE_ACCESS_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Ботын зан төлөв: Маш товч бөгөөд тодорхой хариулах тушаал
SYSTEM_PROMPT = (
    "Та бол Miners Villa төслийн 23 настай эелдэг зөөлөн ааштай борлуулагч. "
    "Хэрэглэгчийн асуултад маш эелдэг бөгөөд ДЭЭД ТАЛ НЬ 1-2 ӨГҮҮЛБЭРТ багтаан товч тодорхой хариулна уу. "
    "Илүү дутуу урт тайлбар, нуршуу зүйл бичиж болохгүй, үргэлж сайн байна уу? өдрийн мэнд гэж эхэлж нэг удаа асууна. " \
    "Мэдээллийн үнэн бодит эх сурвалтай хариулна. " \
    "Хэрэглэгчийн асуултанд хариулахдаа зөвхөн Miners Villa төслийн талаар мэдээлэл өгнө. " \
    "хэрэглэгч уурлаж бухимдсан байвал тайвшруулах эелдэг үг хэллэг хэрэглэнэ. " \
    "дараах танилцуулга мэдээллийг ашиглан хариулна: Танилцуулга ерөнхий

Сайн байна уу?

Miners Villa төсөлтэй амжилттай холбогдлоо 🤗

Эрдэнэт үйлдвэртэй хамтран бүтээн байгуулж буй амины орон сууцны төсөлтэй танилцаж буйд баярлалаа.

😊 Мкв үнэ 5,500,000 - 5,800,000

📍Төлбөрийн нөхцөлийн мэдээлэл
Урьдчилгаа төлбөр - 30%
Явцын төлбөр - 40%
Явцын төлбөр - 20%
Түлхүүр гардуулах үед- 10%
Мөн явцын төлбөрт бартерийн санал нээлттэйгээр хүлээн авах болно. / Зөвхөн байр /

📍 Борлуулалтын оффис:
Эрдэнэт хот 1/16-р байрны зүүн урд буланд төв зам дагуу байрлалтай.

📞 Холбоо барих:
9430-7017

Хаус төрөл

Өдрийн мэнд.
Зах зээл дээр борлуулагдаж буй Таун хаус болон Мульт хаус-ын мкв-ыг илгээж байна

Манай Таун хаус маань 213.33 мкв болон 267.48мкв гэсэн сонголттойгоор борлуулагдаж байна.

Одоо худалдаалагдаж байгаа Мульт хаус-ын сонготууд

A- 126 мкв
B- 125,21мкв
C- 192,25мкв
D- 189,64мкв
F- 136,42мкв
G- 178,39мкв
H- 198,52мкв
I- 189,52 мкв
G- 178,39мкв
гэсэн сонголтууд байна.



Ашиглалтад орох?

Miners Villa төсөл шинэ шатандаа орж, төлөвлөсөн ажлууд үе шаттайгаар хэрэгжиж байгаа бөгөөд 2026 оны өвөл гэхэд дотоод заслын ажлыг эхлүүлэхээр шаргуу ажиллаж байна. Та бүхнийг удаан хүлээлгэх бус, итгэл хүлээлгэсэн сонголтынхоо үнэ цэнийг мэдрэх боломжийг бүрдүүлэхээр бид ажиллаж байна.



Төслийн хаяг
📍 Манай төслийн хаяг Баян-Өндөр уулын зүүн энгэрт буюу Бүсийн оношилгооны төв, Медипас эмнэлгийн ард 30,8 га талбайд бүтээн байгуулалтын ажил үргэлжилж байна.

📍 Борлуулалтын оффис:
Эрдэнэт хот 1/16-р байрны зүүн урд буланд төв зам дагуу байрлалтай.

Төлбөр төлөлт

Гэрээн дээрх хаан банкны дансны дугаарлуу төлбөрөө шилжүүлнэ.
Гүйлгээний утга
Гэрээний дугаар
Байрныхаа тоот
Овог нэр
Регистер

Барилгын явц

🏗️ 7 хоног бүрийн 1 дэх өдөр FACEBOOK PAGE болон INSTAGRAM хаяг дээр REEL хэлбэрээр мэдээлэл шинэчлэгдэн орох болно. Та манай FACEBOOK PAGE болон INSTAGRAM хаягтай нэгдэж тухай бүрт мэдээлэлтэй танилцах боломжтой.



"
)

# Албан ёсны шинэ Gemini Client үүсгэх
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
        # Хариултын уртыг чанга хязгаарлах болон системийн тушаал тохируулах
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=100  # Хариултын текстыг урт гарахаас сэргийлж 100 токеноор хязгаарлав
        )
        
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=user_text,
            config=config
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