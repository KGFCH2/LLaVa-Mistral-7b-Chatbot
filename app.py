import streamlit as st # pyrefly: ignore [missing-import]
import os
import sqlite3
from llm_chains import load_normal_chain, load_pdf_chat_chain # pyrefly: ignore [missing-import]
from streamlit_mic_recorder import mic_recorder # pyrefly: ignore [missing-import]
from utils import get_timestamp, load_config
from image_handler import handle_image
from audio_handler import transcribe_audio
from pdf_handler import add_documents_to_db
from html_templates import css
from database_operations import (
    init_db,
    load_last_k_text_messages,
    save_text_message,
    save_image_message,
    save_audio_message,
    load_messages,
    get_all_chat_history_ids,
    delete_chat_history,
    rename_chat_session,
)

config = load_config()

@st.cache_resource
def load_chain():
    if st.session_state.pdf_chat:
        print("loading pdf chat chain")
        return load_pdf_chat_chain()
    return load_normal_chain()


def toggle_pdf_chat():
    st.session_state.pdf_chat = True
    clear_cache()


def get_session_key():
    if st.session_state.session_key == "new_session":
        st.session_state.new_session_key = get_timestamp()
        return st.session_state.new_session_key
    return st.session_state.session_key


def delete_chat_session_history():
    delete_chat_history(st.session_state.db_conn, st.session_state.session_key)
    st.session_state.session_index_tracker = "new_session"


def clear_cache():
    st.cache_resource.clear()


def rename_current_session():
    if st.session_state.new_session_name and st.session_state.session_key != "new_session":
        old_id = st.session_state.session_key
        new_id = st.session_state.new_session_name
        rename_chat_session(st.session_state.db_conn, old_id, new_id)
        st.session_state.session_index_tracker = new_id
        st.session_state.session_key = new_id


def main():
    init_db()
    st.title("Converso")
    st.write(css, unsafe_allow_html=True)

    if "db_conn" not in st.session_state:
        st.session_state.session_key = "new_session"
        st.session_state.new_session_key = None
        st.session_state.session_index_tracker = "new_session"
        st.session_state.db_conn = sqlite3.connect(config["chat_sessions_database_path"], check_same_thread=False)
        st.session_state.audio_uploader_key = 0
        st.session_state.pdf_uploader_key = 1
    
    if st.session_state.session_key == "new_session" and st.session_state.new_session_key is not None:
        st.session_state.session_index_tracker = st.session_state.new_session_key
        st.session_state.new_session_key = None

    st.sidebar.title("🤖 Converso")
    
    # --- Enhanced System Status ---
    model_path = config["ctransformers"]["model_path"]["large"]
    with st.sidebar:
        if not os.path.exists(model_path):
            st.error("⚠️ **System Status: Mock Mode**")
            st.caption("Local GGUF models not found. Please check your `models/` directory.")
        else:
            st.success("✅ **System Status: Local LLM Active**")
            st.caption("Mistral 7B & LLaVa are ready to process your requests.")
    # ------------------------------

    conn = st.session_state.db_conn
    chat_sessions = ["new_session"] + get_all_chat_history_ids(conn)

    index = chat_sessions.index(st.session_state.session_index_tracker)
    st.sidebar.selectbox("📂 Chat History", chat_sessions, key="session_key", index=index, help="Select a previous conversation or start a new one.")

    with st.sidebar.expander("🛠️ Session Settings", expanded=False):
        delete_chat_col, clear_cache_col = st.columns(2)
        delete_chat_col.button("🗑️ Delete", on_click=delete_chat_session_history, help="Permanently delete this session.")
        clear_cache_col.button("🔄 Reset", on_click=clear_cache, help="Clear model cache and reinitialize.")

        if st.session_state.session_key != "new_session":
            st.divider()
            st.subheader("Rename Session")
            st.text_input("New Name", key="new_session_name", placeholder="Enter name...")
            st.button("Update Name", on_click=rename_current_session)

    st.sidebar.divider()
    st.sidebar.subheader("🧰 Multimodal Tools")
    
    tool_tabs = st.sidebar.tabs(["📄 PDF", "🖼️ Image", "🎙️ Audio"])

    with tool_tabs[0]:
        st.toggle("Enable PDF Context", key="pdf_chat", value=False, on_change=clear_cache, help="When enabled, the bot will search through uploaded PDFs.")
        uploaded_pdf = st.file_uploader(
            "Upload documents", accept_multiple_files=True,
            key=st.session_state.pdf_uploader_key, type=["pdf"],
            on_change=toggle_pdf_chat,
        )

    with tool_tabs[1]:
        uploaded_image = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"], help="Upload an image to ask questions about it.")

    with tool_tabs[2]:
        voice_recording = mic_recorder(
            start_prompt="Record Voice", stop_prompt="Stop Recording", just_once=True
        )
        st.divider()
        uploaded_audio = st.file_uploader(
            "Upload audio file", type=["wav", "mp3", "ogg"],
            key=st.session_state.audio_uploader_key,
        )

    chat_container = st.container()
    user_input = st.chat_input("Type your message here...", key="user_input")

    if uploaded_pdf:
        with st.spinner("Processing pdf..."):
            add_documents_to_db(uploaded_pdf)
            st.session_state.pdf_uploader_key += 2

    if uploaded_audio:
        transcribed_audio = transcribe_audio(uploaded_audio.getvalue())
        print(transcribed_audio)
        llm_chain = load_chain()
        llm_answer = llm_chain.run(user_input="Summarize this text: " + transcribed_audio, chat_history=[])
        save_audio_message(conn, get_session_key(), "human", uploaded_audio.getvalue())
        save_text_message(conn, get_session_key(), "ai", llm_answer)
        st.session_state.audio_uploader_key += 2

    if voice_recording:
        transcribed_audio = transcribe_audio(voice_recording["bytes"])
        print(transcribed_audio)
        llm_chain = load_chain()
        llm_answer = llm_chain.run(user_input=transcribed_audio,
                                   chat_history=load_last_k_text_messages(conn, get_session_key(),
                                                                          config["chat_config"]["chat_memory_length"]))
        save_audio_message(conn, get_session_key(), "human", voice_recording["bytes"])
        save_text_message(conn, get_session_key(), "ai", llm_answer)

    if user_input:
        if uploaded_image:
            with st.spinner("Processing image..."):
                llm_answer = handle_image(uploaded_image.getvalue(), user_input)
                save_text_message(conn, get_session_key(), "human", user_input)
                save_image_message(conn, get_session_key(), "human", uploaded_image.getvalue())
                save_text_message(conn, get_session_key(), "ai", llm_answer)
                user_input = None

        if user_input:
            llm_chain = load_chain()
            llm_answer = llm_chain.run(user_input=user_input,
                                       chat_history=load_last_k_text_messages(conn, get_session_key(), config["chat_config"][
                                           "chat_memory_length"]))
            save_text_message(conn, get_session_key(), "human", user_input)
            save_text_message(conn, get_session_key(), "ai", llm_answer)
            user_input = None

    if (st.session_state.session_key != "new_session") != (st.session_state.new_session_key is not None):
        with chat_container:
            chat_history_messages = load_messages(conn, get_session_key())

            for message in chat_history_messages:
                with st.chat_message(name=message["sender_type"]):
                    if message["message_type"] == "text":
                        st.write(message["content"])
                    if message["message_type"] == "image":
                        st.image(message["content"])
                    if message["message_type"] == "audio":
                        st.audio(message["content"], format="audio/wav")

        if (st.session_state.session_key == "new_session") and (st.session_state.new_session_key is not None):
            st.rerun()


if __name__ == "__main__":
    main()