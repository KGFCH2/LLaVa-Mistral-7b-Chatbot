"""
database_operations.py  (refactored for FastAPI & Streamlit compatibility)

Every function receives an explicit `conn: sqlite3.Connection` argument.
Added safety validations and database exception handling (rollback on error).
"""

import sqlite3
from typing import Generator
from core.utils import load_config

config = load_config()


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
    if not chat_history_id or not sender_type:
        raise ValueError("chat_history_id and sender_type cannot be empty")
    try:
        conn.execute(
            "INSERT INTO messages (chat_history_id, sender_type, message_type, text_content) "
            "VALUES (?, ?, 'text', ?)",
            (chat_history_id, sender_type, text),
        )
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error saving text message: {e}")
        raise e


def save_image_message(conn: sqlite3.Connection, chat_history_id: str,
                       sender_type: str, image_bytes: bytes) -> None:
    if not chat_history_id or not sender_type:
        raise ValueError("chat_history_id and sender_type cannot be empty")
    try:
        conn.execute(
            "INSERT INTO messages (chat_history_id, sender_type, message_type, blob_content) "
            "VALUES (?, ?, 'image', ?)",
            (chat_history_id, sender_type, sqlite3.Binary(image_bytes)),
        )
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error saving image message: {e}")
        raise e


def save_audio_message(conn: sqlite3.Connection, chat_history_id: str,
                       sender_type: str, audio_bytes: bytes) -> None:
    if not chat_history_id or not sender_type:
        raise ValueError("chat_history_id and sender_type cannot be empty")
    try:
        conn.execute(
            "INSERT INTO messages (chat_history_id, sender_type, message_type, blob_content) "
            "VALUES (?, ?, 'audio', ?)",
            (chat_history_id, sender_type, sqlite3.Binary(audio_bytes)),
        )
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error saving audio message: {e}")
        raise e


def load_messages(conn: sqlite3.Connection, chat_history_id: str) -> list:
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
            content = text_content if message_type == "text" else blob_content
            result.append({
                "message_id":   message_id,
                "sender_type":  sender_type,
                "message_type": message_type,
                "content":      content,
            })
        return result
    except sqlite3.Error as e:
        print(f"Error loading messages: {e}")
        raise e


def load_last_k_text_messages(conn: sqlite3.Connection,
                               chat_history_id: str, k: int) -> list:
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

        return [
            {
                "message_id":   row[0],
                "sender_type":  row[1],
                "message_type": row[2],
                "content":      row[3],
            }
            for row in reversed(rows)
        ]
    except sqlite3.Error as e:
        print(f"Error loading last k text messages: {e}")
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