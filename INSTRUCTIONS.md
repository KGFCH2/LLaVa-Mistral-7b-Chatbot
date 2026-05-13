# 📖 Converso Project Instructions & Architecture

Welcome to the internal documentation for **Converso**. This guide explains the project structure, the purpose of each file, and how the multimodal system works.

---

## 🏗️ Core Architecture Overview

Converso is built with a modular architecture that separates the **UI (Streamlit)**, **Orchestration (LangChain)**, and **Specialized Multimodal Handlers**.

### 📂 File-by-File Breakdown

| File Name | Working Principle | Emoji |
| :--- | :--- | :---: |
| **`app.py`** | The main entry point. Orchestrates the Streamlit UI, manages session state, and coordinates between the different handlers. It implements the new tabbed layout for tools. | 🏠 |
| **`llm_chains.py`** | The brain of the app. Built using LangChain, it constructs the conversation chains, initializes the LLMs, and manages the Vector DB. Includes a `MockLLM` fallback. | ⛓️ |
| **`database_operations.py`** | Handles persistent storage of chat histories using SQLite. Manages session creation, message logging, deletion, and renaming. | 💾 |
| **`pdf_handler.py`** | Logic for processing PDF documents. It handles text extraction, chunking, and indexing into ChromaDB for Retrieval-Augmented Generation (RAG). | 📄 |
| **`image_handler.py`** | Interface for the LLaVA (Large Language-and-Vision Assistant). Processes image bytes and runs them through the multimodal GGUF model for visual understanding. | 🖼️ |
| **`audio_handler.py`** | Audio processing module. Utilizes the Whisper model (via Transformers) to transcribe audio uploads or mic recordings into text for the LLM. | 🎙️ |
| **`html_templates.py`** | Contains the custom CSS system. Injects premium glassmorphism styles, hover effects, and chat bubble aesthetics into the Streamlit app. | 🎨 |
| **`prompt_templates.py`** | Central repository for instruction-tuned prompts. Ensures the LLM receives the correct context format for both general chat and PDF-specific RAG. | 📝 |
| **`utils.py`** | Shared utility functions, primarily used for loading the `config.yaml` and generating unique timestamps for chat sessions. | 🛠️ |
| **`config.yaml`** | The single source of truth for all configurations, including model paths, hardware settings (GPU/CPU), and UI parameters. | ⚙️ |

---

## 🛠️ Key Workflows

### 1. Multimodal Interaction 🌈
Users can interact via three main "Tool Tabs" in the sidebar:
- **📄 PDF**: Uploaded files are chunked and stored in a local `chroma_db` folder. The bot then uses RAG to answer questions based *only* on that context.
- **🖼️ Image**: When an image is uploaded, the LLaVA model is triggered to provide a description or answer questions about the visual content.
- **🎙️ Audio**: Voice input is transcribed to text instantly and sent as a prompt to the main LLM.

### 2. Session Management 📂
Every conversation is assigned a unique ID. 
- **Persistence**: Messages are saved to `chat_sessions/chat_sessions.db`.
- **Renaming**: Users can customize session names in the "Session Settings" expander.
- **Cleanup**: Sessions can be deleted individually, or the model cache can be reset via the UI.

### 3. Resilience & Debugging 🛡️
- **System Status**: The sidebar shows a live status indicator.
- **Mock Mode**: If local GGUF models (Mistral/LLaVA) are not found, the app automatically switches to `MockLLM`. This allows developers to test the UI, database, and flow without needing 10GB+ of model files.

---

> [!NOTE]
> All models are run **locally**. No data leaves your machine. ensure you have the appropriate GGUF files in the `models/` directory as specified in `config.yaml`.
