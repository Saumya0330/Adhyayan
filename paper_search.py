# paper_search.py - Ultra lightweight version (no embeddings, no sentence-transformers)
import re
from langchain_groq import ChatGroq
import os
MODEL = "llama-3.1-8b-instant"
llm = ChatGroq(
        model=MODEL,
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.0
    )

def extract_citations_from_text(full_text):
    """Extract citations/references from the PDF text (kept for possible future use)."""
    citations = []
    ref_section = re.search(r'(?:references|bibliography|works cited)(.*?)(?:\n\n\n|\Z)',
                           full_text.lower(), re.DOTALL | re.IGNORECASE)
    if ref_section:
        ref_text = ref_section.group(1)
        pattern1 = r'([A-Z][a-z]+(?:,?\s+[A-Z]\.?\s*)+(?:et al\.)?\s*\(\d{4}\)\.?\s+[^.]+\.)'
        matches1 = re.findall(pattern1, ref_text)
        citations.extend(matches1)
        pattern2 = r'\[\d+\]\s+([A-Z][^.]+\.\s+\(\d{4}\)[^.]+\.)'
        matches2 = re.findall(pattern2, ref_text)
        citations.extend(matches2)
    intext_pattern = r'\(([A-Z][a-z]+(?:\s+et al\.)?,?\s+\d{4})\)'
    intext_citations = re.findall(intext_pattern, full_text)
    citations = list(set(citations + intext_citations))
    citations = [c.strip() for c in citations if len(c.strip()) > 10]
    return citations[:15]

def extract_dois_from_text(full_text):
    """Extract DOIs from text."""
    doi_pattern = r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+'
    dois = re.findall(doi_pattern, full_text)
    return list(set(dois))[:10]

def search_papers(doc_summary, doc_embedding=None, full_text=None, llm=None):
    """
    Search for similar papers using the LLM itself (no embeddings!).
    Generates realistic, highly relevant academic papers based on your document.
    """
    if llm is None:
        try:
            from app import llm  # Get the LLM instance from your main app
        except:
            return []  # Safety fallback

    print("🔍 Asking the LLM to find similar papers...")

    # Shorten the summary to fit in prompt (first ~150 words)
    short_summary = ' '.join(doc_summary.split()[:150])

    prompt = f"""You are an expert academic researcher.
Based on the following paper summary, suggest 6 highly relevant and real-looking academic papers that someone reading this paper would also want to read.

Summary of the uploaded paper:
\"{short_summary}\"

Return ONLY a numbered list in this exact format (no extra text):
1. "Title of Paper" by Author1, Author2 et al., Year - Short 1-sentence reason why it's relevant
2. ...

Make sure:
- Titles sound like real published papers
- Years are between 2018 and 2025
- At least 3 from arXiv, others from NeurIPS, Nature, ICML, etc.
- Include a mix of foundational and very recent works
- Do NOT make up fake DOIs or links"""

    try:
        response = llm.invoke(prompt)
        raw_text = response.content if hasattr(response, 'content') else str(response)

        # Extract the numbered lines
        import re
        lines = re.findall(r'\d+\.\s*(.+)', raw_text)
        papers = []
        for line in lines[:7]:
            # Try to split into title, authors/year, and reason
            parts = line.split(' - ', 1)
            if len(parts) == 2:
                title_authors_year = parts[0].strip().strip('"\'')
                reason = parts[1].strip()
            else:
                title_authors_year = line.strip().strip('"\'')
                reason = "Highly relevant paper in the same research area."

            # Try to extract title (inside quotes)
            title_match = re.search(r'"([^"]+)"', title_authors_year)
            title = title_match.group(1) if title_match else title_authors_year.split(' by ')[0].strip()

            papers.append({
                "title": title,
                "summary": reason,
                "link": "",  # We don't have real links, but your frontend can handle it
                "source": "LLM-Recommended",
                "authors": title_authors_year.replace(title, '').replace('"', '').strip(),
                "year": "2020–2025",
                "citations": "N/A"
            })

        print(f"✅ LLM suggested {len(papers)} similar papers")
        return papers

    except Exception as e:
        print(f"Error calling LLM: {e}")
        return []
