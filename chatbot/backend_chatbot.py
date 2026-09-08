from langgraph.graph import StateGraph,START,END
from typing import Annotated
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
import os
load_dotenv()

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class ChatState(BaseModel):
    user_input: Annotated[list[BaseMessage], add_messages]
    bot_response: Annotated[list[BaseMessage], add_messages]


model = ChatGroq(
    model_name="openai/gpt-oss-120b",
    api_key=os.environ.get("GROQ_API_KEY"),
    temperature=0.7,
    streaming=True,
    stop=None,
)

graph = StateGraph(ChatState)


def ChatGroq_llm(state: ChatState):
    conversation = []
    for index, user_message in enumerate(state.user_input):
        conversation.append(f"User: {user_message.content}")
        if index < len(state.bot_response):
            conversation.append(f"Assistant: {state.bot_response[index].content}")

    prompt = "You are a helpful assistant. Use the conversation history to answer the latest question.\n\n"
    prompt += "\n".join(conversation)
    bot_response = model.invoke(input=prompt)
    return {"bot_response": [bot_response]}

DB_PATH = os.path.join(os.path.dirname(__file__), "chat_history.sqlite")
db_connection = sqlite3.connect(DB_PATH, check_same_thread=False)
checkpoint = SqliteSaver(db_connection)
checkpoint.setup()

db_connection.execute(
    """
    CREATE TABLE IF NOT EXISTS conversations (
        thread_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """
)
db_connection.commit()

graph = StateGraph(ChatState)
graph.add_node("LLm_node", ChatGroq_llm)
graph.add_edge(START, "LLm_node")
graph.add_edge("LLm_node", END)
chatbot = graph.compile(checkpointer=checkpoint)


def create_conversation(thread_id: str, title: str = "New conversation") -> None:
    db_connection.execute(
        "INSERT OR IGNORE INTO conversations (thread_id, title) VALUES (?, ?)",
        (thread_id, title),
    )
    db_connection.commit()


def list_conversations() -> list[dict[str, str]]:
    rows = db_connection.execute(
        "SELECT thread_id, title, created_at, updated_at "
        "FROM conversations ORDER BY updated_at DESC"
    ).fetchall()
    return [
        {
            "thread_id": row[0],
            "title": row[1],
            "created_at": row[2],
            "updated_at": row[3],
        }
        for row in rows
    ]


def update_conversation(thread_id: str, title: str | None = None) -> None:
    if title is None:
        db_connection.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE thread_id = ?",
            (thread_id,),
        )
    else:
        db_connection.execute(
            "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE thread_id = ?",
            (title, thread_id),
        )
    db_connection.commit()


def delete_conversation(thread_id: str) -> None:
    db_connection.execute("DELETE FROM conversations WHERE thread_id = ?", (thread_id,))
    db_connection.commit()


def load_conversation(thread_id: str) -> list[dict[str, str]]:
    state = chatbot.get_state({"configurable": {"thread_id": thread_id}})
    values = state.values or {}
    user_messages = values.get("user_input", [])
    bot_messages = values.get("bot_response", [])
    messages = []
    for index, user_message in enumerate(user_messages):
        messages.append({"role": "user", "content": user_message.content})
        if index < len(bot_messages):
            messages.append({"role": "assistant", "content": bot_messages[index].content})
    return messages
