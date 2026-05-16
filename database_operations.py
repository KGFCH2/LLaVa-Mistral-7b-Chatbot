<<<<<<< HEAD
from utils import load_config
import streamlit as st
import sqlite3
config = load_config()

def get_db_connection():
    return st.session_state.db_conn

def get_db_cursor(db_connection):
    return db_connection.cursor()

def get_db_connection_and_cursor():
    conn = get_db_connection()
    return conn, conn.cursor()

def close_db_connection():
    if 'db_conn' in st.session_state and st.session_state.db_conn is not None:
        st.session_state.db_conn.close()
        st.session_state.db_conn = None


def save_text_message(chat_history_id, sender_type, text):
    conn, cursor = get_db_connection_and_cursor()

    cursor.execute('INSERT INTO messages (chat_history_id, sender_type, message_type, text_content) VALUES (?, ?, ?, ?)',
                   (chat_history_id, sender_type, 'text', text))

    conn.commit()

def save_image_message(chat_history_id, sender_type, image_bytes):
    conn, cursor = get_db_connection_and_cursor()

    cursor.execute('INSERT INTO messages (chat_history_id, sender_type, message_type, blob_content) VALUES (?, ?, ?, ?)',
                   (chat_history_id, sender_type, 'image', sqlite3.Binary(image_bytes)))

    conn.commit()

def save_audio_message(chat_history_id, sender_type, audio_bytes):
    conn, cursor = get_db_connection_and_cursor()

    cursor.execute('INSERT INTO messages (chat_history_id, sender_type, message_type, blob_content) VALUES (?, ?, ?, ?)',
                   (chat_history_id, sender_type, 'audio', sqlite3.Binary(audio_bytes)))

    conn.commit()

def load_messages(chat_history_id):
    conn, cursor = get_db_connection_and_cursor()

    query = "SELECT message_id, sender_type, message_type, text_content, blob_content FROM messages WHERE chat_history_id = ?"
    cursor.execute(query, (chat_history_id,))

    messages = cursor.fetchall()
    chat_history = []
    for message in messages:
        message_id, sender_type, message_type, text_content, blob_content = message

        if message_type == 'text':
            chat_history.append({'message_id': message_id, 'sender_type': sender_type, 'message_type': message_type, 'content': text_content})
        else:
            chat_history.append({'message_id': message_id, 'sender_type': sender_type, 'message_type': message_type, 'content': blob_content})


    return chat_history

def load_last_k_text_messages(chat_history_id, k):
    conn, cursor = get_db_connection_and_cursor()

    query = """
    SELECT message_id, sender_type, message_type, text_content
    FROM messages
    WHERE chat_history_id = ? AND message_type = 'text'
    ORDER BY message_id DESC
    LIMIT ?
    """
    cursor.execute(query, (chat_history_id, k))

    messages = cursor.fetchall()
    chat_history = []
    for message in reversed(messages):
        message_id, sender_type, message_type, text_content = message

        chat_history.append({
            'message_id': message_id,
            'sender_type': sender_type,
            'message_type': message_type,
            'content': text_content
        })


    return chat_history

def get_all_chat_history_ids():
    conn, cursor = get_db_connection_and_cursor()

    query = "SELECT DISTINCT chat_history_id FROM messages ORDER BY chat_history_id ASC"
    cursor.execute(query)

    chat_history_ids = cursor.fetchall()
    chat_history_id_list = [item[0] for item in chat_history_ids]

    return chat_history_id_list

def delete_chat_history(chat_history_id):
    conn, cursor = get_db_connection_and_cursor()

    query = "DELETE FROM messages WHERE chat_history_id = ?"
    cursor.execute(query, (chat_history_id,))
    conn.commit()

    print(f"All entries with chat_history_id {chat_history_id} have been deleted.")


def init_db():
    db_path = config["chat_sessions_database_path"]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    create_messages_table = """
    CREATE TABLE IF NOT EXISTS messages (
        message_id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_history_id TEXT NOT NULL,
        sender_type TEXT NOT NULL,
        message_type TEXT NOT NULL,
        text_content TEXT,
        blob_content BLOB
    );
    """

    cursor.execute(create_messages_table)
    conn.commit()
    conn.close()

if __name__ == "__main__":
=======
"""
database_operations.py  (refactored for FastAPI)

Changes from original:
- Removed `import streamlit as st`
- Removed get_db_connection() / get_db_cursor() which relied on st.session_state
- Every function now receives an explicit `conn: sqlite3.Connection` argument
- init_db() kept unchanged so app.py (Streamlit) still works
- get_db() added as a FastAPI dependency (used in api.py)
"""

import sqlite3
from typing import Generator
from utils import load_config

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
    conn.close()

def save_text_message(conn: sqlite3.Connection, chat_history_id: str,
                      sender_type: str, text: str) -> None:
    conn.execute(
        "INSERT INTO messages (chat_history_id, sender_type, message_type, text_content) "
        "VALUES (?, ?, 'text', ?)",
        (chat_history_id, sender_type, text),
    )
    conn.commit()


def save_image_message(conn: sqlite3.Connection, chat_history_id: str,
                       sender_type: str, image_bytes: bytes) -> None:
    conn.execute(
        "INSERT INTO messages (chat_history_id, sender_type, message_type, blob_content) "
        "VALUES (?, ?, 'image', ?)",
        (chat_history_id, sender_type, sqlite3.Binary(image_bytes)),
    )
    conn.commit()


def save_audio_message(conn: sqlite3.Connection, chat_history_id: str,
                       sender_type: str, audio_bytes: bytes) -> None:
    conn.execute(
        "INSERT INTO messages (chat_history_id, sender_type, message_type, blob_content) "
        "VALUES (?, ?, 'audio', ?)",
        (chat_history_id, sender_type, sqlite3.Binary(audio_bytes)),
    )
    conn.commit()

def load_messages(conn: sqlite3.Connection, chat_history_id: str) -> list:
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


def load_last_k_text_messages(conn: sqlite3.Connection,
                               chat_history_id: str, k: int) -> list:
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


def get_all_chat_history_ids(conn: sqlite3.Connection) -> list:
    rows = conn.execute(
        "SELECT DISTINCT chat_history_id FROM messages ORDER BY chat_history_id ASC"
    ).fetchall()
    return [row[0] for row in rows]

def delete_chat_history(conn: sqlite3.Connection, chat_history_id: str) -> None:
    conn.execute("DELETE FROM messages WHERE chat_history_id = ?", (chat_history_id,))
    conn.commit()
    print(f"All entries with chat_history_id '{chat_history_id}' have been deleted.")


def rename_chat_session(conn: sqlite3.Connection, old_id: str, new_id: str) -> None:
    conn.execute(
        "UPDATE messages SET chat_history_id = ? WHERE chat_history_id = ?",
        (new_id, old_id),
    )
    conn.commit()
    print(f"Chat session renamed from '{old_id}' to '{new_id}'.")


if __name__ == "__main__":
>>>>>>> cf049224449266d41007d6fac7ce8805e96a22cb
    init_db()