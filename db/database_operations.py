"""
database_operations.py  (refactored for FastAPI & Streamlit compatibility)

Every function receives an explicit `conn: sqlite3.Connection` argument.
Added safety validations and database exception handling (rollback on error).
Includes encryption support for sensitive chat data.
"""

import sqlite3
from typing import Generator
import logging
from core.utils import load_config
from core.encryption import encrypt_text, decrypt_text, encrypt_binary, decrypt_binary, is_encryption_available, EncryptionError

config = load_config()
logger = logging.getLogger(__name__)


def get_db() -> Generator[sqlite3.Connection, None, None]:
    db_path = config["chat_sessions_database_path"]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    db_path = config["chat_sessions_database_path"]
    conn = sqlite3.connect(db_path)
    try:
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
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error initializing database: {e}")
        raise e
    finally:
        conn.close()


def save_text_message(conn: sqlite3.Connection, chat_history_id: str,
                      sender_type: str, text: str) -> None:
    """
    Save encrypted text message to database.

    Args:
        conn: Database connection
        chat_history_id: Session ID
        sender_type: "human" or "ai"
        text: Message text to encrypt and store

    Raises:
        ValueError: If chat_history_id or sender_type is empty
        EncryptionError: If encryption fails
        sqlite3.Error: If database operation fails
    """
    if not chat_history_id or not sender_type:
        raise ValueError("chat_history_id and sender_type cannot be empty")
    try:
        # Encrypt text before storing
        encrypted_text = encrypt_text(text)
        logger.debug(f"Encrypted text message ({len(text)} chars -> {len(encrypted_text)} bytes)")

        conn.execute(
            "INSERT INTO messages (chat_history_id, sender_type, message_type, text_content) "
            "VALUES (?, ?, 'text', ?)",
            (chat_history_id, sender_type, sqlite3.Binary(encrypted_text)),
        )
        conn.commit()
        logger.info(f"Text message saved: {chat_history_id}/{sender_type}")
    except EncryptionError as e:
        conn.rollback()
        logger.error(f"Encryption error saving text message: {e}")
        raise
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error saving text message: {e}")
        raise e


def save_image_message(conn: sqlite3.Connection, chat_history_id: str,
                       sender_type: str, image_bytes: bytes) -> None:
    """
    Save encrypted image message to database.

    Args:
        conn: Database connection
        chat_history_id: Session ID
        sender_type: "human" or "ai"
        image_bytes: Image data to encrypt and store

    Raises:
        ValueError: If chat_history_id or sender_type is empty
        EncryptionError: If encryption fails
        sqlite3.Error: If database operation fails
    """
    if not chat_history_id or not sender_type:
        raise ValueError("chat_history_id and sender_type cannot be empty")
    try:
        # Encrypt image before storing
        encrypted_image = encrypt_binary(image_bytes)
        logger.debug(f"Encrypted image ({len(image_bytes)} bytes -> {len(encrypted_image)} bytes)")

        conn.execute(
            "INSERT INTO messages (chat_history_id, sender_type, message_type, blob_content) "
            "VALUES (?, ?, 'image', ?)",
            (chat_history_id, sender_type, sqlite3.Binary(encrypted_image)),
        )
        conn.commit()
        logger.info(f"Image message saved: {chat_history_id}/{sender_type}")
    except EncryptionError as e:
        conn.rollback()
        logger.error(f"Encryption error saving image message: {e}")
        raise
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error saving image message: {e}")
        raise e


def save_audio_message(conn: sqlite3.Connection, chat_history_id: str,
                       sender_type: str, audio_bytes: bytes) -> None:
    """
    Save encrypted audio message to database.

    Args:
        conn: Database connection
        chat_history_id: Session ID
        sender_type: "human" or "ai"
        audio_bytes: Audio data to encrypt and store

    Raises:
        ValueError: If chat_history_id or sender_type is empty
        EncryptionError: If encryption fails
        sqlite3.Error: If database operation fails
    """
    if not chat_history_id or not sender_type:
        raise ValueError("chat_history_id and sender_type cannot be empty")
    try:
        # Encrypt audio before storing
        encrypted_audio = encrypt_binary(audio_bytes)
        logger.debug(f"Encrypted audio ({len(audio_bytes)} bytes -> {len(encrypted_audio)} bytes)")

        conn.execute(
            "INSERT INTO messages (chat_history_id, sender_type, message_type, blob_content) "
            "VALUES (?, ?, 'audio', ?)",
            (chat_history_id, sender_type, sqlite3.Binary(encrypted_audio)),
        )
        conn.commit()
        logger.info(f"Audio message saved: {chat_history_id}/{sender_type}")
    except EncryptionError as e:
        conn.rollback()
        logger.error(f"Encryption error saving audio message: {e}")
        raise
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error saving audio message: {e}")
        raise e


def load_messages(conn: sqlite3.Connection, chat_history_id: str) -> list:
    """
    Load and decrypt messages from database.

    Args:
        conn: Database connection
        chat_history_id: Session ID

    Returns:
        List of decrypted messages

    Raises:
        ValueError: If chat_history_id is empty
        EncryptionError: If decryption fails
        sqlite3.Error: If database operation fails
    """
    if not chat_history_id:
        raise ValueError("chat_history_id cannot be empty")
    try:
        rows = conn.execute(
            "SELECT message_id, sender_type, message_type, text_content, blob_content "
            "FROM messages WHERE chat_history_id = ?",
            (chat_history_id,),
        ).fetchall()

        result = []
        for row in rows:
            message_id, sender_type, message_type, text_content, blob_content = row

            try:
                if message_type == "text":
                    # Decrypt text content
                    content = decrypt_text(text_content) if text_content else ""
                else:
                    # Decrypt binary content (image/audio)
                    content = decrypt_binary(blob_content) if blob_content else b""

                result.append({
                    "message_id":   message_id,
                    "sender_type":  sender_type,
                    "message_type": message_type,
                    "content":      content,
                })
                logger.debug(f"Message {message_id} decrypted successfully")
            except EncryptionError as e:
                logger.error(f"Failed to decrypt message {message_id}: {str(e)}")
                raise

        logger.info(f"Loaded {len(result)} decrypted messages for {chat_history_id}")
        return result
    except EncryptionError as e:
        logger.error(f"Decryption error loading messages: {e}")
        raise
    except sqlite3.Error as e:
        logger.error(f"Database error loading messages: {e}")
        raise e


def load_last_k_text_messages(conn: sqlite3.Connection,
                               chat_history_id: str, k: int) -> list:
    """
    Load and decrypt last k text messages from database.

    Args:
        conn: Database connection
        chat_history_id: Session ID
        k: Number of messages to load

    Returns:
        List of decrypted text messages in chronological order

    Raises:
        ValueError: If chat_history_id is empty
        EncryptionError: If decryption fails
        sqlite3.Error: If database operation fails
    """
    if not chat_history_id:
        raise ValueError("chat_history_id cannot be empty")
    try:
        rows = conn.execute(
            """
            SELECT message_id, sender_type, message_type, text_content
            FROM   messages
            WHERE  chat_history_id = ? AND message_type = 'text'
            ORDER  BY message_id DESC
            LIMIT  ?
            """,
            (chat_history_id, k),
        ).fetchall()

        result = []
        for row in reversed(rows):
            try:
                message_id, sender_type, message_type, text_content = row
                # Decrypt text content
                decrypted_content = decrypt_text(text_content) if text_content else ""

                result.append({
                    "message_id":   message_id,
                    "sender_type":  sender_type,
                    "message_type": message_type,
                    "content":      decrypted_content,
                })
                logger.debug(f"Message {message_id} decrypted successfully")
            except EncryptionError as e:
                logger.error(f"Failed to decrypt message {message_id}: {str(e)}")
                raise

        logger.info(f"Loaded {len(result)} decrypted text messages for {chat_history_id}")
        return result
    except EncryptionError as e:
        logger.error(f"Decryption error loading text messages: {e}")
        raise
    except sqlite3.Error as e:
        logger.error(f"Database error loading last k text messages: {e}")
        raise e


def get_all_chat_history_ids(conn: sqlite3.Connection) -> list:
    try:
        rows = conn.execute(
            "SELECT DISTINCT chat_history_id FROM messages ORDER BY chat_history_id ASC"
        ).fetchall()
        return [row[0] for row in rows]
    except sqlite3.Error as e:
        print(f"Error getting chat history IDs: {e}")
        raise e


def delete_chat_history(conn: sqlite3.Connection, chat_history_id: str) -> None:
    if not chat_history_id:
        raise ValueError("chat_history_id cannot be empty")
    try:
        conn.execute("DELETE FROM messages WHERE chat_history_id = ?", (chat_history_id,))
        conn.commit()
        print(f"All entries with chat_history_id '{chat_history_id}' have been deleted.")
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error deleting chat history: {e}")
        raise e


def rename_chat_session(conn: sqlite3.Connection, old_id: str, new_id: str) -> None:
    if not old_id or not new_id:
        raise ValueError("old_id and new_id cannot be empty")
    try:
        conn.execute(
            "UPDATE messages SET chat_history_id = ? WHERE chat_history_id = ?",
            (new_id, old_id),
        )
        conn.commit()
        print(f"Chat session renamed from '{old_id}' to '{new_id}'.")
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error renaming chat session: {e}")
        raise e


if __name__ == "__main__":
    init_db()