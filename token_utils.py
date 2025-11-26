# token_utils.py - Utility functions for token management

def estimate_tokens(text):
    """
    Estimate number of tokens in text.
    Rule of thumb: 1 token ≈ 4 characters for English text.
    """
    return len(text) // 4


def truncate_to_tokens(text, max_tokens=5000):
    """
    Truncate text to approximately max_tokens.
    """
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def chunk_text_by_tokens(text, chunk_tokens=4000, overlap_tokens=200):
    """
    Split text into chunks by token count.
    """
    chunk_chars = chunk_tokens * 4
    overlap_chars = overlap_tokens * 4
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_chars
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap_chars
    
    return chunks


def check_pdf_size(full_text):
    """
    Check if PDF is too large and provide recommendations.
    """
    tokens = estimate_tokens(full_text)
    
    if tokens < 5000:
        return "small", tokens, "✅ Document size is optimal"
    elif tokens < 15000:
        return "medium", tokens, "⚠️ Document is large, will be chunked for processing"
    else:
        return "large", tokens, "⚠️ Very large document, processing may take longer"


if __name__ == "__main__":
    # Test
    sample_text = "This is a test document. " * 1000
    size, tokens, msg = check_pdf_size(sample_text)
    print(f"Size: {size}, Tokens: {tokens}")
    print(msg)