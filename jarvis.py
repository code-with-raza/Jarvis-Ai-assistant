import os
from dotenv import load_dotenv

from brain import load_skills, route_command
from auto_router import auto_route
from memory_store import get_memories

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

# Setup
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise EnvironmentError("Missing OPENROUTER_API_KEY in .env")

skills = load_skills("skills")

# LLM

llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    temperature=0.3,
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are Jarvis. Be helpful and concise."),
    ("system", "User memory (use this if relevant):\n{memory_context}"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

chain = prompt | llm

# Memory 

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

SESSION_ID = "Malik"
CFG = {"configurable": {"session_id": SESSION_ID}}

# Main Loop

def main():
    print(" Jarvis Core (Plugin Skills Enabled + Auto Router + Memory Context)")
    print("Type /help for commands.\n")
    print("Loaded skills:", list(skills.keys()))

    while True:
        user_text = input("You: ").strip()
        if not user_text:
            continue

        #  Core exit commands
        if user_text.lower() in {"exit", "quit", "/exit", "/quit"}:
            print("Jarvis: Goodbye.")
            break

        # 1) Slash command router
        cmd_result = route_command(user_text, skills, SESSION_ID)

        if cmd_result == "__CLEAR_CHAT__":
            _store.pop(SESSION_ID, None)
            print("Jarvis:  Chat history cleared.\n")
            continue

        if cmd_result is not None:
            print(f"Jarvis: {cmd_result}\n")
            continue

        # 2) Auto router (LLM chooses skill)
        auto_result = auto_route(user_text, llm, skills, SESSION_ID)
        if auto_result is not None:
            print(f"Jarvis: {auto_result}\n")
            continue

        # 3) Normal chat (inject saved memory into prompt)
        memory_items = get_memories(SESSION_ID)
        memory_context = "\n".join(f"- {m}" for m in memory_items) if memory_items else "No saved memory yet."

        res = jarvis.invoke(
            {"input": user_text, "memory_context": memory_context},
            config=CFG
        )
        print(f"Jarvis: {res.content}\n")


if __name__ == "__main__":
    main()
    