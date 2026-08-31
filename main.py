import os
import requests
from fastapi import FastAPI, Request, Response
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# .env файлаас нууц түлхүүрүүдийг унших
load_dotenv()

app = FastAPI()

# Баталгаажуулах Токен ба API түлхүүрүүд
VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "miners_villa_secret_123")
PAGE_ACCESS_TOKEN = os.getenv("META_PAGE_ACCESS_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# AI Загвар тохируулах
llm = ChatOpenAI(model="gpt-4o", temperature=0.3, api_key=OPENAI_API_KEY)

# Промпт ба зааварчилгаа
SYSTEM_PROMPT = """
Чи бол 'Miners Villa' орон сууцны төслийн борлуулалтын зөвлөх AI. 
Зорилго: Харилцагчийн сонирхсон өрөөний тоог мэдэж, 'Miners Villa'-ийн давуу талыг тайлбарлан, Загварын байр үзэх утасны дугаарыг нь авах.
Загварлаг, нөхөрсөг, монгол хэлний найруулга зүйг сайн баримталж хариулна уу. Хариулт бүрийнхээ төгсгөлд асуулт асууна уу.
"""

# 1. Meta Webhook Баталгаажуулалт (GET)
@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, status_code=200)
    return Response(content="Verification failed", status_code=403)

# 2. Ирж буй мессежийг хүлээн авах ба Хариулах (POST)
@app.post("/webhook")
async def handle_messages(request: Request):
    data = await request.json()

    if data.get("object") in ["page", "instagram"]:
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event["sender"]["id"]
                
                # Ирсэн текстоор мессеж байгаа эсэхийг шалгах
                if "message" in messaging_event and "text" in messaging_event["message"]:
                    user_text = messaging_event["message"]["text"]
                    
                    # AI-аас хариулт авах
                    ai_reply = generate_ai_response(user_text)
                    
                    # Хариултыг FB/IG руу буцааж илгээх
                    send_message(sender_id, ai_reply)

    return Response(content="EVENT_RECEIVED", status_code=200)

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