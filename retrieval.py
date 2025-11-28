# retrieval.py - Memory-optimized version
import os
from langchain_community.vectorstores import FAISS

DB_DIR = "data/vector_db"

def retrieve_chunks(query, pdf_name, top_k=5):
    """
    Retrieve chunks using cached embeddings model
    """
    # Import cached model
    from app import get_langchain_embeddings
    
    load_path = os.path.join(DB_DIR, pdf_name)

    # Use cached embeddings
    embeddings = get_langchain_embeddings()

    vectordb = FAISS.load_local(
        load_path,
        embeddings,
        allow_dangerous_deserialization=True
    )

    docs = vectordb.similarity_search(query, k=top_k)
    
    return docs
