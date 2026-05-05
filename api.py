import asyncio
import sqlite3
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import List

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from database_operations import (
    delete_chat_history, get_all_chat_history_ids, get_db, init_db,
    load_last_k_text_messages, load_messages,
    save_audio_message, save_image_message, save_text_message,
)
from schemas import (
    AudioTranscribeResponse, ChatRequest, ChatResponse,
    DeleteSessionResponse, ImageChatResponse, MessageOut,
    PDFUploadResponse, SessionHistoryResponse, SessionListResponse,
)
from utils import load_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="LLaVa-Mistral-7b Chatbot API",
    description="Multi-modal chatbot API powered by LLaVA + Mistral-7B",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_config() -> dict:
    return load_config()


@lru_cache(maxsize=1)
def _normal_chain():
    from llm_chains import load_normal_chain
    return load_normal_chain()


@lru_cache(maxsize=1)
def _pdf_chain():
    from llm_chains import load_pdf_chat_chain
    return load_pdf_chat_chain()


@lru_cache(maxsize=1)
def _llava_model():
    from image_handler import load_llava
    return load_llava()

@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "LLaVa-Mistral-7b Chatbot API is running."}

@app.post("/api/chat/message", response_model=ChatResponse, tags=["Chat"])
async def send_message(
    body:   ChatRequest,
    conn:   sqlite3.Connection = Depends(get_db),
    config: dict               = Depends(get_config),
):
    memory_length = config["chat_config"]["chat_memory_length"]
    history = load_last_k_text_messages(conn, body.session_id, memory_length)
    try:
        reply = await asyncio.to_thread(
            _normal_chain().run, user_input=body.message, chat_history=history
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"LLM error: {exc}")
    save_text_message(conn, body.session_id, "human", body.message)
    save_text_message(conn, body.session_id, "ai", reply)
    return ChatResponse(session_id=body.session_id, reply=reply)


@app.get("/api/chat/sessions", response_model=SessionListResponse, tags=["Chat"])
async def list_sessions(conn: sqlite3.Connection = Depends(get_db)):
    return SessionListResponse(sessions=get_all_chat_history_ids(conn))


@app.get("/api/chat/sessions/{session_id}", response_model=SessionHistoryResponse, tags=["Chat"])
async def get_session_history(session_id: str, conn: sqlite3.Connection = Depends(get_db)):
    raw = load_messages(conn, session_id)
    return SessionHistoryResponse(session_id=session_id, messages=[MessageOut(**m) for m in raw])


@app.delete("/api/chat/sessions/{session_id}", response_model=DeleteSessionResponse, tags=["Chat"])
async def delete_session(session_id: str, conn: sqlite3.Connection = Depends(get_db)):
    delete_chat_history(conn, session_id)
    return DeleteSessionResponse(session_id=session_id, deleted=True)

@app.post("/api/image/chat", response_model=ImageChatResponse, tags=["Image"])
async def image_chat(
    session_id: str        = Form(...),
    prompt:     str        = Form(..., min_length=1),
    image:      UploadFile = File(...),
    conn:       sqlite3.Connection = Depends(get_db),
):
    if image.content_type not in ("image/jpeg", "image/jpg", "image/png"):
        raise HTTPException(status_code=400, detail="Only jpg and png images are supported.")
    image_bytes = await image.read()

    def _run_llava():
        from image_handler import convert_bytes_to_base64
        llava = _llava_model()
        output = llava.create_chat_completion(messages=[
            {"role": "system", "content": "You are an assistant who perfectly describes images."},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": convert_bytes_to_base64(image_bytes)}},
                {"type": "text", "text": prompt},
            ]},
        ])
        return output["choices"][0]["message"]["content"]

    try:
        reply = await asyncio.to_thread(_run_llava)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Image model error: {exc}")

    save_text_message(conn, session_id, "human", prompt)
    save_image_message(conn, session_id, "human", image_bytes)
    save_text_message(conn, session_id, "ai", reply)
    return ImageChatResponse(session_id=session_id, reply=reply)

@app.post("/api/files/pdf", response_model=PDFUploadResponse, tags=["Files"])
async def upload_pdf(
    session_id: str              = Form(...),
    pdfs:       List[UploadFile] = File(...),
    conn:       sqlite3.Connection = Depends(get_db),
):
    for pdf in pdfs:
        if pdf.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail=f"{pdf.filename} is not a PDF.")
    pdf_bytes_list = [await pdf.read() for pdf in pdfs]

    def _ingest():
        from pdf_handler import extract_text_from_pdf, get_document_chunks
        from llm_chains import load_vectordb, create_embeddings
        documents = get_document_chunks([extract_text_from_pdf(b) for b in pdf_bytes_list])
        load_vectordb(create_embeddings()).add_documents(documents)
        return len(documents)

    try:
        chunks_added = await asyncio.to_thread(_ingest)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF processing error: {exc}")
    return PDFUploadResponse(session_id=session_id, chunks_added=chunks_added)


@app.post("/api/files/audio", response_model=AudioTranscribeResponse, tags=["Files"])
async def upload_audio(
    session_id: str        = Form(...),
    audio:      UploadFile = File(...),
    conn:       sqlite3.Connection = Depends(get_db),
    config:     dict               = Depends(get_config),
):
    if audio.content_type not in ("audio/wav", "audio/mpeg", "audio/ogg", "audio/x-wav"):
        raise HTTPException(status_code=400, detail="Use wav, mp3, or ogg.")
    audio_bytes = await audio.read()

    try:
        from audio_handler import transcribe_audio
        transcription = await asyncio.to_thread(transcribe_audio, audio_bytes)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transcription error: {exc}")

    history = load_last_k_text_messages(conn, session_id, config["chat_config"]["chat_memory_length"])
    try:
        reply = await asyncio.to_thread(
            _normal_chain().run,
            user_input=f"Summarize this text: {transcription}",
            chat_history=history,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"LLM error: {exc}")

    save_audio_message(conn, session_id, "human", audio_bytes)
    save_text_message(conn, session_id, "ai", reply)
    return AudioTranscribeResponse(session_id=session_id, transcription=transcription, reply=reply)