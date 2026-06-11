from langchain_core.documents import Document # pyrefly: ignore [missing-import]
from llm.llm_chains import load_vectordb, create_embeddings
from core.utils import load_config
import pypdfium2 # pyrefly: ignore [missing-import]
from langchain_text_splitters import RecursiveCharacterTextSplitter # pyrefly: ignore [missing-import]
import re

config = load_config()

def get_pdf_texts(pdfs_bytes_list):
    return [extract_text_from_pdf(pdf_bytes.getvalue()) for pdf_bytes in pdfs_bytes_list]

def extract_text_from_pdf(pdf_bytes):
    if not pdf_bytes:
        return ""
    try:
        pdf_file = pypdfium2.PdfDocument(pdf_bytes)
        text = "\n".join(
            pdf_file.get_page(page_number).get_textpage().get_text_range() for page_number in range(len(pdf_file)))
        
        # Clean text: remove duplicate whitespaces and normalise newlines
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n+', '\n', text)
        return text.strip()
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def get_text_chunks(text):
    splitter = RecursiveCharacterTextSplitter(chunk_size=config["pdf_text_splitter"]["chunk_size"],
                                              chunk_overlap=config["pdf_text_splitter"]["overlap"],
                                              separators=config["pdf_text_splitter"]["separators"])
    return splitter.split_text(text)

def get_document_chunks(text_list):
    documents = []
    for text in text_list:
        for chunk in get_text_chunks(text):
            documents.append(Document(page_content=chunk))
    return documents

def add_documents_to_db(pdfs_bytes):
    texts = get_pdf_texts(pdfs_bytes)
    documents = get_document_chunks(texts)
    vector_db = load_vectordb(create_embeddings())
    vector_db.add_documents(documents)
    print("Documents added to db.")

