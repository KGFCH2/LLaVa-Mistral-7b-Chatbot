from typing import List, Optional
from pydantic import BaseModel # pyrefly: ignore [missing-import]
import uvicorn # pyrefly: ignore [missing-import]
from llm.llm_chains import load_normal_chain
from endpoint.schemas import (
    ChatMessage, ChatResponse, SessionListResponse,
    SessionHistoryResponse, DeleteSessionResponse, MessageOut
)
import sqlite3
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends # pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware # pyrefly: ignore [missing-import]
from db.database_operations import (
    save_text_message, load_last_k_text_messages, init_db,
    get_all_chat_history_ids, load_messages, delete_chat_history, rename_chat_session
)
from core.utils import load_config, get_timestamp

config = load_config()
app = FastAPI(title="Converso API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()


def get_db_connection():
    db_path = config["chat_sessions_database_path"]
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    try:
        yield conn
    finally:
        conn.close()


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(message: ChatMessage, conn: sqlite3.Connection = Depends(get_db_connection)):
    # Load the LLM chain
    llm_chain = load_normal_chain()

    # Get chat history
    chat_history = load_last_k_text_messages(
        conn, message.chat_history_id, config["chat_config"]["chat_memory_length"]
    )

    # Run the chain
    llm_answer = llm_chain.run(user_input=message.content, chat_history=chat_history)

    # Save messages to database
    save_text_message(conn, message.chat_history_id, "human", message.content)
    save_text_message(conn, message.chat_history_id, "ai", llm_answer)

    return ChatResponse(content=llm_answer, chat_history_id=message.chat_history_id)


@app.get("/sessions", response_model=SessionListResponse)
async def list_sessions(conn: sqlite3.Connection = Depends(get_db_connection)):
    try:
        sessions = get_all_chat_history_ids(conn)
        return SessionListResponse(sessions=sessions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@app.get("/sessions/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(session_id: str, conn: sqlite3.Connection = Depends(get_db_connection)):
    try:
        messages = load_messages(conn, session_id)
        formatted_messages = []
        for msg in messages:
            content_str = msg["content"]
            if isinstance(content_str, bytes):
                content_str = "[Binary Content]"
            formatted_messages.append(MessageOut(
                message_id=msg["message_id"],
                sender_type=msg["sender_type"],
                message_type=msg["message_type"],
                content=content_str
            ))
        return SessionHistoryResponse(session_id=session_id, messages=formatted_messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve session history: {str(e)}")


@app.delete("/sessions/{session_id}", response_model=DeleteSessionResponse)
async def delete_session(session_id: str, conn: sqlite3.Connection = Depends(get_db_connection)):
    try:
        delete_chat_history(conn, session_id)
        return DeleteSessionResponse(session_id=session_id, deleted=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


@app.put("/sessions/{session_id}/rename")
async def rename_session(session_id: str, new_name: str, conn: sqlite3.Connection = Depends(get_db_connection)):
    try:
        rename_chat_session(conn, session_id, new_name)
        return {"session_id": session_id, "new_name": new_name, "renamed": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rename session: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)