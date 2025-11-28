import os
from langchain_groq import ChatGroq

MODEL = "llama-3.1-8b-instant"

def answer_with_context(question, chunks):
    llm = ChatGroq(
        model=MODEL,
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.0
    )

    context_text = ""

    # Handle both string chunks and object chunks
    for i, c in enumerate(chunks):
        if isinstance(c, str):
            # If it's already a string, use it directly
            label = f"[Chunk {i+1}]"
            context_text += f"{label}\n{c}\n\n"
        else:
            # If it's an object with metadata and page_content
            try:
                meta = c.metadata if hasattr(c, 'metadata') else {}
                content = c.page_content if hasattr(c, 'page_content') else str(c)
                label = f"[Chunk {i+1} from {meta.get('source', 'document')} page={meta.get('page', 'N/A')}]"
                context_text += f"{label}\n{content}\n\n"
            except AttributeError:
                # Fallback for dictionary-like objects
                meta = c.get('metadata', {}) if isinstance(c, dict) else {}
                content = c.get('text', str(c)) if isinstance(c, dict) else str(c)
                label = f"[Chunk {i+1} from {meta.get('source', 'document')} page={meta.get('page', 'N/A')}]"
                context_text += f"{label}\n{content}\n\n"

    prompt = f"""
Answer the question using ONLY these chunks:

{context_text}

Question: {question}

Format:
1) Final answer
2) Citations (which chunk labels you used)
"""

    try:
        resp = llm.invoke(prompt)
        return resp.content
    except Exception as e:
        return f"I apologize, but I encountered an error while processing your question: {str(e)}"

def summarize_document(full_text):
    """
    Summarize document with chunking for large documents.
    Handles documents that exceed token limits.
    """
    llm = ChatGroq(
        model=MODEL,
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.0
    )
    
    # Estimate tokens (rough: 1 token ≈ 4 characters)
    estimated_tokens = len(full_text) // 4
    max_chars = 20000  # ~5000 tokens, safe limit
    
    # If document is too large, chunk it and summarize each chunk
    if len(full_text) > max_chars:
        print(f"⚠️ Document too large ({estimated_tokens} tokens), chunking...")
        
        # Split into chunks
        chunk_size = max_chars
        chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
        
        summaries = []
        for i, chunk in enumerate(chunks[:3]):  # Only first 3 chunks to save tokens
            prompt = f"""
Summarize the key topics and methods in this section of a research document:

{chunk}

Provide a brief 2-3 sentence summary focusing on the main topic.
"""
            try:
                resp = llm.invoke(prompt)
                summaries.append(resp.content.strip())
                print(f"✅ Summarized chunk {i+1}/{min(len(chunks), 3)}")
            except Exception as e:
                print(f"❌ Error summarizing chunk {i+1}: {e}")
                continue
        
        if not summaries:
            return "Unable to generate summary due to processing errors."
            
        # Combine chunk summaries into final summary
        combined = " ".join(summaries)
        
        final_prompt = f"""
Based on these section summaries of a research paper, provide a comprehensive 3-4 sentence summary of the overall document:

{combined}

Focus on: main topic, research field, and key methodology.
Return only the summary, no preamble.
"""
        try:
            resp = llm.invoke(final_prompt)
            return resp.content.strip()
        except Exception as e:
            return f"Summary generation failed: {str(e)}"
    
    # If document is small enough, summarize directly
    prompt = f"""
You are an expert in analyzing academic documents.

Summarize the core topic, field, and methods described in the following document text.
The summary must be 3-4 sentences and strictly about the topic.

Document:
{full_text}

Return only the topic summary.
"""

    try:
        resp = llm.invoke(prompt)
        return resp.content.strip()
    except Exception as e:
        return f"Summary generation failed: {str(e)}"
