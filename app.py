# pyrefly: ignore [missing-import]
import streamlit as st
from llm.llm_chains import load_normal_chain, load_pdf_chat_chain
# pyrefly: ignore [missing-import]
from streamlit_mic_recorder import mic_recorder
from core.utils import get_timestamp, load_config
from handler.image_handler import handle_image
from handler.audio_handler import transcribe_audio
from handler.pdf_handler import add_documents_to_db
from html_templates import css
from db.database_operations import init_db, load_last_k_text_messages, save_text_message, save_image_message, save_audio_message, \
    load_messages, get_all_chat_history_ids, delete_chat_history
import sqlite3
import logging

logger = logging.getLogger(__name__)

config = load_config()

@st.cache_resource
def load_chain():
    """
    Load appropriate chat chain with error handling.

    Returns:
        Initialized chat chain or None if loading fails

    Raises:
        RuntimeError: If chain initialization fails
    """
    try:
        if st.session_state.pdf_chat:
            logger.info("Loading PDF chat chain...")
            return load_pdf_chat_chain()
        logger.info("Loading normal chat chain...")
        return load_normal_chain()
    except Exception as e:
        logger.error(f"Failed to load chat chain: {str(e)}")
        raise


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
    if st.session_state.session_key == "new_session" and st.session_state.new_session_key != None:
        st.session_state.session_index_tracker = st.session_state.new_session_key
        st.session_state.new_session_key = None

    st.sidebar.title("Chat Sessions")
    chat_sessions = ["new_session"] + get_all_chat_history_ids(st.session_state.db_conn)

    index = chat_sessions.index(st.session_state.session_index_tracker)
    st.sidebar.selectbox("Select a chat session", chat_sessions, key="session_key", index=index)
    pdf_toggle_col, voice_rec_col = st.sidebar.columns(2)
    pdf_toggle_col.toggle("PDF Chat", key="pdf_chat", value=False, on_change=clear_cache)
    with voice_rec_col:
        voice_recording = mic_recorder(start_prompt="Record Audio", stop_prompt="Stop recording", just_once=True)

    delete_chat_col, clear_cache_col = st.sidebar.columns(2)

    if st.session_state.get("confirm_delete", False):
        st.sidebar.warning("Are you sure?")
        yes_col, no_col = st.sidebar.columns(2)
        if yes_col.button("Yes", use_container_width=True):
            delete_chat_session_history()
            st.session_state.confirm_delete = False
            st.rerun()
        if no_col.button("No", use_container_width=True):
            st.session_state.confirm_delete = False
            st.rerun()
    else:
        if delete_chat_col.button("Delete Chat Session", use_container_width=True):
            st.session_state.confirm_delete = True
            st.rerun()

    clear_cache_col.button("Clear Cache", on_click=clear_cache, use_container_width=True)

    chat_container = st.container()
    user_input = st.chat_input("Type your message here", key="user_input")

    with st.sidebar.expander("📁 Media Uploads", expanded=False):
        uploaded_audio = st.file_uploader("Upload an audio file", type=["wav", "mp3", "ogg"],
                                                key=st.session_state.audio_uploader_key)
        uploaded_image = st.file_uploader("Upload an image file", type=["jpg", "jpeg", "png"])
        uploaded_pdf = st.file_uploader("Upload a pdf file", accept_multiple_files=True,
                                                key=st.session_state.pdf_uploader_key, type=["pdf"],
                                                on_change=toggle_pdf_chat)

    if uploaded_pdf:
        with st.spinner("Processing pdf..."):
            add_documents_to_db(uploaded_pdf)
            st.session_state.pdf_uploader_key += 2

    if uploaded_audio:
        with st.spinner("Processing audio..."):
            try:
                transcribed_audio = transcribe_audio(uploaded_audio.getvalue())
                logger.info(f"Audio transcribed: {len(transcribed_audio)} characters")
                llm_chain = load_chain()
                if llm_chain is None:
                    st.error("Failed to initialize chat chain. Please check logs for details.")
                else:
                    llm_answer = llm_chain.run(user_input="Summarize this text: " + transcribed_audio, chat_history=[])
                    save_audio_message(st.session_state.db_conn, get_session_key(), "human", uploaded_audio.getvalue())
                    save_text_message(st.session_state.db_conn, get_session_key(), "ai", llm_answer)
                    st.session_state.audio_uploader_key += 2
            except Exception as e:
                logger.error(f"Error processing audio: {str(e)}")
                st.error(f"Error processing audio: {str(e)}")

    if voice_recording:
        with st.spinner("Processing voice input..."):
            try:
                transcribed_audio = transcribe_audio(voice_recording["bytes"])
                logger.info(f"Voice transcribed: {len(transcribed_audio)} characters")
                llm_chain = load_chain()
                if llm_chain is None:
                    st.error("Failed to initialize chat chain. Please check logs for details.")
                else:
                    chat_history = load_last_k_text_messages(
                        st.session_state.db_conn,
                        get_session_key(),
                        config["chat_config"]["chat_memory_length"]
                    )
                    llm_answer = llm_chain.run(user_input=transcribed_audio, chat_history=chat_history)
                    save_audio_message(st.session_state.db_conn, get_session_key(), "human", voice_recording["bytes"])
                    save_text_message(st.session_state.db_conn, get_session_key(), "ai", llm_answer)
            except Exception as e:
                logger.error(f"Error processing voice: {str(e)}")
                st.error(f"Error processing voice: {str(e)}")

    if user_input:
        if uploaded_image:
            with st.spinner("Processing image..."):
                llm_answer = handle_image(uploaded_image.getvalue(), user_input)
                save_text_message(st.session_state.db_conn, get_session_key(), "human", user_input)
                save_image_message(st.session_state.db_conn, get_session_key(), "human", uploaded_image.getvalue())
                save_text_message(st.session_state.db_conn, get_session_key(), "ai", llm_answer)
                user_input = None

        if user_input:
            with st.spinner("Generating response..."):
                try:
                    llm_chain = load_chain()
                    if llm_chain is None:
                        st.error("Failed to initialize chat chain. Please refresh the page and try again.")
                    else:
                        chat_history = load_last_k_text_messages(
                            st.session_state.db_conn,
                            get_session_key(),
                            config["chat_config"]["chat_memory_length"]
                        )
                        llm_answer = llm_chain.run(user_input=user_input, chat_history=chat_history)
                        save_text_message(st.session_state.db_conn, get_session_key(), "human", user_input)
                        save_text_message(st.session_state.db_conn, get_session_key(), "ai", llm_answer)
                        user_input = None
                except RuntimeError as e:
                    logger.error(f"Chat chain error: {str(e)}")
                    st.error(f"Chat error: {str(e)}")
                except Exception as e:
                    logger.error(f"Unexpected error during chat: {str(e)}")
                    st.error(f"An unexpected error occurred: {str(e)}")

    if (st.session_state.session_key != "new_session") != (st.session_state.new_session_key != None):
        with chat_container:
            chat_history_messages = load_messages(st.session_state.db_conn, get_session_key())

            for message in chat_history_messages:
                with st.chat_message(name=message["sender_type"]):
                    if message["message_type"] == "text":
                        st.write(message["content"])
                    if message["message_type"] == "image":
                        st.image(message["content"])
                    if message["message_type"] == "audio":
                        st.audio(message["content"], format="audio/wav")

        if (st.session_state.session_key == "new_session") and (st.session_state.new_session_key != None):
            st.rerun()


if __name__ == "__main__":
    main()
