import os
import sqlite3
import pytest
from core.utils import load_config, get_timestamp
from core.encryption import encrypt_text, decrypt_text, encrypt_binary, decrypt_binary
from core.image_cache import image_cache, get_cached_image, cache_image, clear_image_cache
from db.database_operations import (
    save_text_message,
    save_image_message,
    save_audio_message,
    load_messages,
    load_last_k_text_messages,
    get_all_chat_history_ids,
    delete_chat_history,
    rename_chat_session
)
from llm.llm_chains import MockLLM


def test_mock_llm():
    llm = MockLLM()
    response = llm.invoke("Hello chatbot")
    assert "[MOCK MODE]" in response
    assert llm._llm_type == "mock"


def test_encryption_decryption():
    test_text = "Hello sensitive chat data!"
    encrypted = encrypt_text(test_text)
    decrypted = decrypt_text(encrypted)
    assert decrypted == test_text

    test_bytes = b"image_binary_data_here"
    encrypted_bytes = encrypt_binary(test_bytes)
    decrypted_bytes = decrypt_binary(encrypted_bytes)
    assert decrypted_bytes == test_bytes


def test_image_cache():
    clear_image_cache()
    assert image_cache.size() == 0

    img_data = b"fake_jpeg_image_bytes"
    cached_info = {"resized_bytes": img_data, "base64": "ZmFrZV9qcGVnX2ltYWdlX2J5dGVz"}

    cache_image(img_data, cached_info)
    assert image_cache.size() == 1

    retrieved = get_cached_image(img_data)
    assert retrieved == cached_info

    clear_image_cache()
    assert image_cache.size() == 0


def test_database_operations(tmp_path):
    # Setup temporary database
    db_file = tmp_path / "test_chat_sessions.db"
    conn = sqlite3.connect(db_file)
    
    # Create the table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_history_id TEXT NOT NULL,
            sender_type     TEXT NOT NULL,
            message_type    TEXT NOT NULL,
            text_content    TEXT,
            blob_content    BLOB
        )
    """)
    conn.commit()

    session_id = "test-session-123"

    # Test saving text message
    save_text_message(conn, session_id, "human", "Hello AI!")
    save_text_message(conn, session_id, "ai", "Hello Human!")

    # Test loading messages
    messages = load_messages(conn, session_id)
    assert len(messages) == 2
    assert messages[0]["sender_type"] == "human"
    assert messages[0]["content"] == "Hello AI!"
    assert messages[1]["sender_type"] == "ai"
    assert messages[1]["content"] == "Hello Human!"

    # Test loading last k messages
    last_msg = load_last_k_text_messages(conn, session_id, 1)
    assert len(last_msg) == 1
    assert last_msg[0]["content"] == "Hello Human!"

    # Test saving image & audio message
    save_image_message(conn, session_id, "human", b"test_image_data")
    save_audio_message(conn, session_id, "human", b"test_audio_data")

    all_messages = load_messages(conn, session_id)
    assert len(all_messages) == 4
    assert all_messages[2]["message_type"] == "image"
    assert all_messages[2]["content"] == b"test_image_data"
    assert all_messages[3]["message_type"] == "audio"
    assert all_messages[3]["content"] == b"test_audio_data"

    # Test listing sessions
    sessions = get_all_chat_history_ids(conn)
    assert session_id in sessions

    # Test renaming session
    new_session_id = "renamed-session-123"
    rename_chat_session(conn, session_id, new_session_id)
    sessions = get_all_chat_history_ids(conn)
    assert new_session_id in sessions
    assert session_id not in sessions

    # Test deleting session
    delete_chat_history(conn, new_session_id)
    sessions = get_all_chat_history_ids(conn)
    assert new_session_id not in sessions

    conn.close()


def test_load_config():
    config = load_config()
    assert config is not None
    assert "ctransformers" in config
    assert "chat_config" in config
