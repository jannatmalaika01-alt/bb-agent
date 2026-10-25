import os
from typing import List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-3.5-flash-lite"

app = FastAPI(title="Big Brains AI Support Agent")

FAQ = [
    "Refunds: items can be returned within 30 days for a full refund.",
    "Shipping: standard shipping takes 3-5 business days; express takes 1-2.",
    "Support hours: Monday to Friday, 9am to 6pm.",
    "Password reset: click 'Forgot password' on the login page and check your email.",
    "Payments: we accept credit cards, PayPal and bank transfer.",
]

SYSTEM_PROMPT = (
    "You are the Big Brains AI Support Agent, a friendly customer support assistant. "
    "Answer using only the company info provided. If the answer isn't there, say "
    "you'll escalate to a human agent. Keep replies short and clear."
)


class Turn(BaseModel):
    role: str  # "user" or "agent"
    text: str


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Turn]] = []


def find_context(question: str, top_k: int = 2):
    words = set(question.lower().split())
    scored = sorted(FAQ, key=lambda f: len(words & set(f.lower().split())), reverse=True)
    return scored[:top_k]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest):
    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY missing in .env")
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message is empty")

    context = "\n".join(find_context(req.message))
    past = "\n".join(
        f"{'Customer' if t.role == 'user' else 'Agent'}: {t.text}"
        for t in (req.history or [])[-6:]
    )
    prompt = (
        f"{SYSTEM_PROMPT}\n\nCompany info:\n{context}\n\n"
        f"Conversation so far:\n{past}\n\nCustomer: {req.message}\nAgent:"
    )
    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        return {"reply": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))