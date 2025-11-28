# ingest.py - Simplified version for LLM-only approach
import os
from pypdf import PdfReader

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

def ingest_pdf(path):
    """
    Simple PDF ingestion - extract text and prepare for LLM processing
    """
    pdf_name = os.path.splitext(os.path.basename(path))[0]
    
    print(f"📄 Processing {pdf_name}...")
    
    # Step 1: Extract text from PDF
    pages = load_pdf(path)
    if not pages:
        raise ValueError(f"No text could be extracted from {pdf_name}")
    
    print(f"✅ Extracted text from {len(pages)} pages")
    
    # Step 2: Combine into full document text for summarization
    full_text = extract_document_text(pages)
    
    # Step 3: Generate document summary using LLM
    from llm_agent import summarize_document
    print(f"🔄 Generating summary using LLM...")
    try:
        doc_summary = summarize_document(full_text)
        print(f"✅ Summary generated successfully")
    except Exception as e:
        print(f"❌ Error generating summary: {e}")
        # Fallback summary
        first_page_text = pages[0]['text'][:500] if pages else "No content"
        doc_summary = f"Document: {pdf_name}. Content preview: {first_page_text}..."
    
    # Step 4: Create simple chunks (just page texts)
    chunks = []
    for page in pages:
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
