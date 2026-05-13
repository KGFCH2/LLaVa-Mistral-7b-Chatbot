from langchain_core.documents import Document # pyrefly: ignore [missing-import]
import os
from utils import load_config
import pypdfium2 # pyrefly: ignore [missing-import]
from langchain_text_splitters import RecursiveCharacterTextSplitter # pyrefly: ignore [missing-import]
from llm_chains import load_vectordb, create_embeddings

config = load_config()


def get_pdf_texts(pdf_list):
    documents = []
    for pdf in pdf_list:
        pdf_reader = pypdfium2.PdfDocument(pdf)
        pdf_text = ""
        for i in range(len(pdf_reader)):
            page = pdf_reader.get_page(i)
            text_page = page.get_textpage()
            pdf_text += text_page.get_text_range()
        
        # Create a Document object for each PDF
        documents.append(Document(page_content=pdf_text, metadata={"source": pdf.name}))
    
    return documents


def get_text_chunks(documents):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=config["pdf_text_splitter"]["chunk_size"],
        chunk_overlap=config["pdf_text_splitter"]["chunk_overlap"],
        separators=config["pdf_text_splitter"]["separators"]
    )
    
    # Split the documents into chunks
    chunks = text_splitter.split_documents(documents)
    return chunks


def add_documents_to_db(pdf_list):
    # Step 1: Extract text from PDFs
    documents = get_pdf_texts(pdf_list)
    
    # Step 2: Split text into chunks
    chunks = get_text_chunks(documents)
    
    # Step 3: Load vector database
    vector_db = load_vectordb(create_embeddings())
    
    # Step 4: Add chunks to the vector database
    vector_db.add_documents(chunks)
    print("Documents added to vector database.")
