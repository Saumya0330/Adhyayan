# retrieval.py - Simple text-based retrieval (no embeddings)
import os
from llm_agent import answer_with_context

def retrieve_chunks(question, pdf_name):
    """
    Simple retrieval that returns all chunks for basic context
    In a production system, you'd implement proper retrieval logic
    """
    # For now, return a message about the retrieval method
    # In a real implementation, you'd retrieve relevant chunks from storage
    return [
        f"You are analyzing the research paper titled: {pdf_name}",
        f"User question: {question}",
        "Provide a clear, accurate, and well-structured answer based on the paper's content."
    ]
def simple_text_search(question, chunks):
    """
    Basic keyword-based search through chunks
    """
    question_lower = question.lower()
    relevant_chunks = []
    
    for chunk in chunks:
        text_lower = chunk['text'].lower()
        # Simple keyword matching
        if any(keyword in text_lower for keyword in question_lower.split()):
            relevant_chunks.append(chunk)
    
    # If no keyword matches, return first few chunks as context
    if not relevant_chunks and chunks:
        relevant_chunks = chunks[:3]  # First 3 chunks as fallback
    
    return relevant_chunks
