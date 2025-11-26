# retrieval.py
import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

DB_DIR = "data/vector_db"

def retrieve_chunks(query, pdf_name, top_k=5):

    load_path = os.path.join(DB_DIR, pdf_name)

    # *** USE LOCAL HUGGINGFACE EMBEDDINGS — NO OPENAI ***
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectordb = FAISS.load_local(
        load_path,
        embeddings,
        allow_dangerous_deserialization=True
    )

    docs = vectordb.similarity_search(query, k=top_k)
    
    return docs
