import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from brain import load_skills, route_command
from auto_router import auto_route, looks_like_pdf_question  # use your auto_router's function
from memory_store import get_memories

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

from rag_pdf import index_pdf, get_active_pdf, ask_pdf
from web_search import web_search


# Trigger keywords
TIME_TRIGGERS = [
    "time", "current time", "time right now", "what time is it", "what is the time",
    "time now", "date", "today's date", "current date"
]

WEB_TRIGGERS = [
    "current", "latest", "today", "now", "news", "price", "rate", "exchange",
    "usd", "pkr", "who is the current", "president", "prime minister",
    "cm of", "chief minister", "updated", "2024", "2025", "2026"
]

def needs_time(text: str) -> bool:
    t = (text or "").lower().strip()
    return any(k in t for k in TIME_TRIGGERS)

def needs_web(text: str) -> bool:
    t = (text or "").lower().strip()
    return any(k in t for k in WEB_TRIGGERS)

def get_now_string() -> str:
    # change this timezone to your preference:
    
    tz_name = os.getenv("JARVIS_TZ", "Asia/Karachi")
    now = datetime.now(ZoneInfo(tz_name))
    return now.strftime("%Y-%m-%d %H:%M:%S %Z")

# App
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup 
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise EnvironmentError("Missing OPENROUTER_API_KEY in .env")

skills = load_skills("skills")
print(" Loaded skills:", list(skills.keys()))

llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    temperature=0.3,
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are Jarvis. Be helpful, accurate, and concise."),
    ("system", "User memory (use this if relevant):\n{memory_context}"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

chain = prompt | llm

_store = {}

def get_history(session_id: str) -> ChatMessageHistory:
    if session_id not in _store:
        _store[session_id] = ChatMessageHistory()
    return _store[session_id]

jarvis = RunnableWithMessageHistory(
    chain,
    get_history,
    input_messages_key="input",
    history_messages_key="history",
)

class ChatRequest(BaseModel):
    session_id: str = "default"
    text: str

class ChatResponse(BaseModel):
    session_id: str
    route: str
    output: str

@app.get("/")
def root():
    return {"status": "ok", "message": "Jarvis API running", "endpoints": ["/chat", "/upload_pdf", "/docs"]}

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    session_id = req.session_id
    text = (req.text or "").strip()
    low = text.lower()

    memory_items = get_memories(session_id)
    memory_context = "\n".join(f"- {m}" for m in memory_items) if memory_items else "No saved memory yet."

    # 0) Real time (Python-side)
    if needs_time(text):
        return ChatResponse(
            session_id=session_id,
            route="time",
            output=f"Current time: {get_now_string()}"
        )

    # 1) Slash commands (/pdf etc.)
    cmd_result = route_command(text, skills, session_id, llm=llm)
    if cmd_result == "__CLEAR_CHAT__":
        _store.pop(session_id, None)
        return ChatResponse(session_id=session_id, route="clear", output="✅ Chat history cleared.")
    if cmd_result is not None:
        return ChatResponse(session_id=session_id, route="command", output=str(cmd_result))

    # 2) PDF auto-route ONLY if active pdf exists AND looks like a PDF question
    active_pdf = get_active_pdf(session_id)
    if active_pdf and looks_like_pdf_question(text):
        # Improve "summary" behavior: ask for summary explicitly
        if "summary" in low or "summarize" in low:
            q = "Give a concise summary of this PDF. Include key sections and bullet points."
        else:
            q = text
        answer = ask_pdf(session_id=session_id, question=q, llm=llm, k=8)
        return ChatResponse(session_id=session_id, route="pdf", output=answer)

    # 3) Skills auto-router (for non-pdf skills)
    
    auto_result = auto_route(text, llm, skills, session_id)
    if auto_result is not None:
        return ChatResponse(session_id=session_id, route="skill", output=str(auto_result))

    # 4) Web search mode (for latest/current questions)
    if needs_web(text):
        try:
            sources = web_search(text, max_results=5)
        except Exception as e:
            return ChatResponse(session_id=session_id, route="web_error", output=f"❌ Web search failed: {e}")

        if sources.strip():
            prompt_with_sources = (
                "Answer using these web results. If the results don't contain the answer, say you're not sure.\n\n"
                f"Web Results:\n{sources}\n\n"
                f"User Question:\n{text}\n\n"
                "Answer:"
            )
            ans = llm.invoke(prompt_with_sources)
            out = ans.content if hasattr(ans, "content") else str(ans)
            return ChatResponse(session_id=session_id, route="web", output=out)

    # 5) Normal chat
    cfg = {"configurable": {"session_id": session_id}}
    res = jarvis.invoke({"input": text, "memory_context": memory_context}, config=cfg)
    return ChatResponse(session_id=session_id, route="chat", output=res.content)


# PDF upload
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.post("/upload_pdf")
async def upload_pdf(session_id: str = "default", file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        return {"ok": False, "error": "Only PDF files are supported."}

    save_path = UPLOAD_DIR / file.filename
    data = await file.read()
    save_path.write_bytes(data)

    chunks = index_pdf(session_id=session_id, file_path=str(save_path), source_id=file.filename)
    return {"ok": True, "filename": file.filename, "chunks_indexed": chunks, "active_pdf": file.filename}
