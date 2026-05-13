from typing import List, Optional
from pydantic import BaseModel # pyrefly: ignore [missing-import]
import uvicorn # pyrefly: ignore [missing-import]
from llm_chains import load_normal_chain
from schemas import ChatMessage, ChatResponse
import sqlite3
from fastapi import FastAPI, UploadFile, File, Form # pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware # pyrefly: ignore [missing-import]
from database_operations import save_text_message, load_last_k_text_messages, init_db
from utils import load_config, get_timestamp

config = load_config()
app = FastAPI()

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


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(message: ChatMessage):
    # Load the LLM chain
    llm_chain = load_normal_chain()

    # Create a database connection
    db_path = config["chat_sessions_database_path"]
    conn = sqlite3.connect(db_path)

    # Get chat history
    chat_history = load_last_k_text_messages(
        conn, message.chat_history_id, config["chat_config"]["chat_memory_length"]
    )

    # Run the chain
    llm_answer = llm_chain.run(user_input=message.content, chat_history=chat_history)

    # Save messages to database
    save_text_message(conn, message.chat_history_id, "human", message.content)
    save_text_message(conn, message.chat_history_id, "ai", llm_answer)

    conn.close()

    return ChatResponse(content=llm_answer, chat_history_id=message.chat_history_id)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)