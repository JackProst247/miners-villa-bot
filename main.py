import os
import requests
from fastapi import FastAPI, Request, Response, BackgroundTasks, HTTPException
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

app = FastAPI()

# Орчны хувьсагчуудыг унших
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "miners_villa_secret_123")
META_PAGE_ACCESS_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Google Gemini загварыг тохируулах
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=GEMINI_API_KEY
)

def send_fb_message(recipient_id: str, text: str):
    """Facebook Messenger API руу хариу мессеж илгээх функц"""
    url = f"https://graph.facebook.com/v20.0/me/messages?access_token={META_PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    headers = {"Content-Type": "application/json"}
    
    try:
        res = requests.post(url, json=payload, headers=headers)
        res.raise_for_status()
    except Exception as e:
        print(f"Error sending message to Facebook: {e}")

def process_ai_response(sender_id: str, user_text: str):
    """Background Task: Gemini-ээс хариу аваад Facebook руу илгээх"""
    try:
        # Gemini AI-аас хариу авах
        response = llm.invoke([HumanMessage(content=user_text)])
        ai_text = response.content
        
        # Facebook Messenger рүү хариу илгээх
        send_fb_message(sender_id, ai_text)
    except Exception as e:
        print(f"Error processing AI response: {e}")

@app.get("/webhook")
async def verify_webhook(request: Request):
    """Facebook Webhook баталгаажуулах GET хүсэлт"""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    
    raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    """Facebook-ээс ирсэн мессежийг хүлээн авах POST хүсэлт"""
    data = await request.json()

    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                # Хэрэглэгчийн бичсэн шинэ мессеж мөн эсэхийг шалгах
                if messaging_event.get("message") and not messaging_event["message"].get("is_echo"):
                    sender_id = messaging_event["sender"]["id"]
                    user_text = messaging_event["message"].get("text", "")

                    if user_text:
                        # AI хариуг арын горимд боловсруулж, Webhook Timeout-аас сэргийлнэ
                        background_tasks.add_task(process_ai_response, sender_id, user_text)

        return Response(content="EVENT_RECEIVED", status_code=200)

    return Response(content="NOT_A_PAGE_EVENT", status_code=404)

@app.get("/")
async def root():
    return {"status": "Bot server is running successfully with Google Gemini!"}
# SYSTEM_PROMPT хувьсагчийг функцынхээ дээр эсвэл эхэнд нь зарлаж өгнө
SYSTEM_PROMPT = "Та бол Miners Villa төслийн борлуулагч бөгөөд төслийн танилцуулга болон мэдээллийг эелдэг бөгөөд товч тодорхой хариулах үүрэгтэй юм."

# Жишээ нь Gemini код дотор чинь SYSTEM_PROMPT ашиглагдаж байгаа бол одоо алдаа гарахгүй

