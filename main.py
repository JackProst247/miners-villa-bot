import os
import requests
from fastapi import FastAPI, Request, Response, BackgroundTasks
from langchain_core.prompts import ChatPromptTemplate

app = FastAPI()

# Тохиргооны хувьсагчид
PAGE_ACCESS_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "miners_villa_secret_123")

# --- 1. Webhook Баталгаажуулалт (GET) ---
@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, status_code=200)
    return Response(content="Verification failed", status_code=403)

# --- 2. Туслах функцүүд ---
def generate_ai_response(user_message: str) -> str:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", "{input}")
    ])
    chain = prompt | llm
    response = chain.invoke({"input": user_message})
    return response.content

def send_message(recipient_id: str, text: str):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    headers = {"Content-Type": "application/json"}
    requests.post(url, json=payload, headers=headers)

def process_ai_and_send(sender_id: str, user_text: str):
    try:
        ai_reply = generate_ai_response(user_text)
        send_message(sender_id, ai_reply)
    except Exception as e:
        print(f"Error processing AI message: {e}")

# --- 3. Ирж буй мессежийг хүлээн авах ба Хариулах (POST) ---
@app.post("/webhook")
async def handle_messages(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()

    if data.get("object") in ["page", "instagram"]:
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event.get("sender", {}).get("id")

                # Ирсэн текстеэр мессеж байгаа эсэхийг шалгах
                if "message" in messaging_event and "text" in messaging_event["message"]:
                    user_text = messaging_event["message"]["text"]
                    
                    # Meta-г хүлээлгэхгүйн тулд AI хариуг фон руу шилжүүлнэ
                    background_tasks.add_task(process_ai_and_send, sender_id, user_text)

    # Meta-д НЭН ДАРУЙ 200 OK хариу өгнө (Timeout-оос сэргийлнэ)
    return Response(content="EVENT_RECEIVED", status_code=200)