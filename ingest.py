# ingest.py
import os
import uuid
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
#from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

VECTOR_DB_DIR = "./data/vector_db"

def load_pdf(path):
    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages):
        txt = page.extract_text() or ""
        pages.append({"page": i+1, "text": txt})
    return pages

def chunk_pages(pages):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )
    chunks = []
    for p in pages:
        pieces = splitter.split_text(p["text"])
        for idx, pc in enumerate(pieces):
            chunks.append({
                "text": pc,
                "metadata": {
                    "page": p["page"],
                    "chunk_index": idx
                }
            })
    return chunks

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

DB_DIR = "data/vector_db"

from llm_agent import summarize_document
from sentence_transformers import SentenceTransformer

def ingest_pdf(path):
    pdf_name = os.path.splitext(os.path.basename(path))[0]
    save_dir = os.path.join(DB_DIR, pdf_name)

    pages = load_pdf(path)
    chunks = chunk_pages(pages)

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    # Full document text for summary and citation extraction
    full_text = "\n".join(texts)
    
    # Check document size
    from token_utils import check_pdf_size
    size_category, token_count, size_msg = check_pdf_size(full_text)
    print(f"📄 {pdf_name}: {size_msg} ({token_count} tokens)")

    # LLM summary of the whole document (with chunking if needed)
    print(f"🔄 Generating summary for {pdf_name}...")
    doc_summary = summarize_document(full_text)
    print(f"✅ Summary generated for {pdf_name}")
    
    # Generate document embedding for similarity search
    print(f"🔄 Generating embeddings for {pdf_name}...")
    embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    doc_embedding = embedding_model.encode(doc_summary)
    print(f"✅ Embeddings generated for {pdf_name}")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectordb = FAISS.from_texts(
        texts,
        embedding=embeddings,
        metadatas=metadatas
    )

    os.makedirs(save_dir, exist_ok=True)
    vectordb.save_local(save_dir)

    # Return additional data: embedding and full text
    return len(texts), len(pages), doc_summary, pdf_name
#, doc_embedding, full_text
