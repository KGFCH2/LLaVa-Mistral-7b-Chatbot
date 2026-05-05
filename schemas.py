from typing import List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique session identifier")
    message:    str = Field(..., min_length=1, description="User's text message")


class ChatResponse(BaseModel):
    session_id: str
    reply:      str


class SessionListResponse(BaseModel):
    sessions: List[str]


class MessageOut(BaseModel):
    message_id:   Optional[int] = None
    sender_type:  str
    message_type: str
    content:      str


class SessionHistoryResponse(BaseModel):
    session_id: str
    messages:   List[MessageOut]


class DeleteSessionResponse(BaseModel):
    session_id: str
    deleted:    bool


class ImageChatResponse(BaseModel):
    session_id: str
    reply:      str


class PDFUploadResponse(BaseModel):
    session_id:   str
    chunks_added: int
    message:      str = "PDF processed and added to vector store."


class AudioTranscribeResponse(BaseModel):
    session_id:    str
    transcription: str
    reply:         str