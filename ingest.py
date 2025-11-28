# ingest.py - Memory-optimized version
import os
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
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

from llm_agent import summarize_document

def ingest_pdf(path):
    """
    Memory-optimized PDF ingestion.
    Uses cached embedding model from app.py
    """
    # Import here to use cached model
    from app import get_langchain_embeddings, get_embedding_model
    
    pdf_name = os.path.splitext(os.path.basename(path))[0]
    save_dir = os.path.join(VECTOR_DB_DIR, pdf_name)

    print(f"📄 Processing {pdf_name}...")
    
    pages = load_pdf(path)
    chunks = chunk_pages(pages)

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    # Full document text for summary
    full_text = "\n".join(texts)
    
    # Check document size
    from token_utils import check_pdf_size
    size_category, token_count, size_msg = check_pdf_size(full_text)
    print(f"📊 {pdf_name}: {size_msg} ({token_count} tokens)")

    # LLM summary of the whole document
    print(f"🔄 Generating summary...")
    doc_summary = summarize_document(full_text)
    print(f"✅ Summary generated")
    
    # Use cached embedding model
    print(f"🔄 Generating embeddings...")
    embedding_model = get_embedding_model()
    doc_embedding = embedding_model.encode(doc_summary)
    print(f"✅ Embeddings generated")

    # Use cached LangChain embeddings
    embeddings = get_langchain_embeddings()

    # Create vector store
    print(f"🔄 Creating vector store...")
    vectordb = FAISS.from_texts(
        texts,
        embedding=embeddings,
        metadatas=metadatas
    )

    os.makedirs(save_dir, exist_ok=True)
    vectordb.save_local(save_dir)
    print(f"✅ Vector store saved to {save_dir}")

    return len(texts), len(pages), doc_summary, pdf_name
