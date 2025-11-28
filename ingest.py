# ingest.py - LLM-only PDF ingestion (no embeddings)
import os
from pypdf import PdfReader
from llm_agent import summarize_document

def load_pdf(path):
    """Extract text from PDF pages"""
    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages):
        txt = page.extract_text() or ""
        if txt.strip():  # Only add non-empty pages
            pages.append({"page": i+1, "text": txt})
    return pages

def extract_document_text(pages):
    """Combine all pages into a single document text"""
    full_text = ""
    for page in pages:
        full_text += f"Page {page['page']}:\n{page['text']}\n\n"
    return full_text.strip()

def chunk_text_for_llm(text, max_chunk_size=4000):
    """
    Simple text chunking for LLM processing
    Splits by paragraphs to maintain context
    """
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        # If adding this paragraph would exceed max size, save current chunk
        if len(current_chunk) + len(paragraph) > max_chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            current_chunk = paragraph
        else:
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph
    
    # Add the last chunk if it exists
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks

def ingest_pdf(path):
    """
    PDF ingestion using only LLM for processing
    No vector embeddings - focuses on content extraction and summarization
    """
    pdf_name = os.path.splitext(os.path.basename(path))[0]
    
    print(f"📄 Processing {pdf_name}...")
    
    # Step 1: Extract text from PDF
    pages = load_pdf(path)
    if not pages:
        raise ValueError(f"No text could be extracted from {pdf_name}")
    
    print(f"✅ Extracted text from {len(pages)} pages")
    
    # Step 2: Combine into full document text
    full_text = extract_document_text(pages)
    
    # Step 3: Generate document summary using LLM
    print(f"🔄 Generating summary using LLM...")
    try:
        doc_summary = summarize_document(full_text)
        print(f"✅ Summary generated successfully")
    except Exception as e:
        print(f"❌ Error generating summary: {e}")
        # Fallback: create a basic summary from first few pages
        first_page_text = pages[0]['text'][:500] if pages else "No content"
        doc_summary = f"Document: {pdf_name}. First page preview: {first_page_text}..."
    
    # Step 4: Create chunks for future Q&A (without embeddings)
    chunks = []
    for page in pages:
        # Simple chunking by page
        if page['text'].strip():
            chunks.append({
                "text": page['text'],
                "metadata": {
                    "page": page['page'],
                    "source": pdf_name
                }
            })
    
    print(f"✅ Created {len(chunks)} text chunks")
    
    return len(chunks), len(pages), doc_summary, pdf_name

def get_document_chunks(pdf_name):
    """
    Retrieve chunks for a specific document
    In a real implementation, you might store this in a database
    """
    # This is a simplified version - in production, you'd retrieve from storage
    return []

def estimate_token_count(text):
    """Simple token estimation (roughly 4 characters per token)"""
    return len(text) // 4

def check_document_size(full_text):
    """Check if document is within reasonable size limits"""
    token_count = estimate_token_count(full_text)
    
    if token_count > 8000:
        category = "large"
        message = f"Large document ({token_count} tokens - may take longer to process)"
    elif token_count > 4000:
        category = "medium" 
        message = f"Medium document ({token_count} tokens)"
    else:
        category = "small"
        message = f"Small document ({token_count} tokens)"
    
    return category, token_count, message
