# paper_search.py - Enhanced with embedding-based search and citation extraction
import requests
import re
from sentence_transformers import SentenceTransformer
import numpy as np

# Load embedding model (same as used in ingestion)
embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')


def extract_citations_from_text(full_text):
    """
    Extract citations/references from the PDF text.
    Looks for common patterns like [1], (Author, Year), etc.
    """
    citations = []
    
    # Pattern 1: References section
    ref_section = re.search(r'(?:references|bibliography|works cited)(.*?)(?:\n\n\n|\Z)', 
                           full_text.lower(), re.DOTALL | re.IGNORECASE)
    
    if ref_section:
        ref_text = ref_section.group(1)
        
        # Extract individual references (common patterns)
        # Pattern: Author et al. (Year). Title. Journal/Conference.
        pattern1 = r'([A-Z][a-z]+(?:,?\s+[A-Z]\.?\s*)+(?:et al\.)?\s*\(\d{4}\)\.?\s+[^.]+\.)'
        matches1 = re.findall(pattern1, ref_text)
        citations.extend(matches1)
        
        # Pattern: [1] Author, A., & Author, B. (Year).
        pattern2 = r'\[\d+\]\s+([A-Z][^.]+\.\s+\(\d{4}\)[^.]+\.)'
        matches2 = re.findall(pattern2, ref_text)
        citations.extend(matches2)
    
    # Pattern 2: In-text citations
    # (Author, Year) or (Author et al., Year)
    intext_pattern = r'\(([A-Z][a-z]+(?:\s+et al\.)?,?\s+\d{4})\)'
    intext_citations = re.findall(intext_pattern, full_text)
    
    # Deduplicate and clean
    citations = list(set(citations + intext_citations))
    citations = [c.strip() for c in citations if len(c.strip()) > 10]
    
    return citations[:15]  # Return top 15 citations


def extract_dois_from_text(full_text):
    """
    Extract DOIs (Digital Object Identifiers) from text.
    DOIs can be used to fetch paper metadata.
    """
    # DOI pattern: 10.xxxx/xxxxx
    doi_pattern = r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+'
    dois = re.findall(doi_pattern, full_text)
    return list(set(dois))[:10]  # Return top 10 unique DOIs


def search_arxiv_by_embedding(doc_embedding, doc_summary, max_results=5):
    """
    Search arXiv using document summary for better results.
    Use embeddings to re-rank results.
    """
    # Extract key terms from summary for search
    search_query = ' '.join(doc_summary.split()[:30])  # First 30 words
    
    url = f"http://export.arxiv.org/api/query?search_query=all:{search_query}&start=0&max_results={max_results*2}"
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return []

        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.text)

        results = []
        ns = {"arxiv": "http://www.w3.org/2005/Atom"}

        for entry in root.findall("arxiv:entry", ns):
            title_elem = entry.find("arxiv:title", ns)
            summary_elem = entry.find("arxiv:summary", ns)
            id_elem = entry.find("arxiv:id", ns)
            
            if title_elem is None or summary_elem is None:
                continue
                
            title = title_elem.text.strip()
            summary = summary_elem.text.strip()
            link = id_elem.text if id_elem is not None else ""
            
            # Calculate embedding similarity
            paper_text = f"{title} {summary}"
            paper_embedding = embedding_model.encode(paper_text)
            similarity = np.dot(doc_embedding, paper_embedding) / (
                np.linalg.norm(doc_embedding) * np.linalg.norm(paper_embedding)
            )

            results.append({
                "title": title,
                "summary": summary,
                "link": link,
                "similarity": float(similarity),
                "source": "arXiv"
            })

        # Sort by similarity and return top results
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:max_results]
    
    except Exception as e:
        print(f"Error searching arXiv: {e}")
        return []


def search_semantic_scholar_by_embedding(doc_embedding, doc_summary, max_results=5):
    """
    Search Semantic Scholar using document summary.
    Re-rank by embedding similarity.
    """
    search_query = ' '.join(doc_summary.split()[:30])
    
    url = f"https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": search_query,
        "limit": max_results * 2,
        "fields": "title,authors,year,url,abstract,citationCount"
    }
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code != 200:
            return []

        data = resp.json()
        results = []

        for p in data.get("data", []):
            title = p.get("title", "")
            abstract = p.get("abstract", "")
            
            if not title or not abstract:
                continue
            
            # Calculate embedding similarity
            paper_text = f"{title} {abstract}"
            paper_embedding = embedding_model.encode(paper_text)
            similarity = np.dot(doc_embedding, paper_embedding) / (
                np.linalg.norm(doc_embedding) * np.linalg.norm(paper_embedding)
            )
            
            authors = p.get("authors", [])
            author_names = ", ".join([a.get("name", "") for a in authors[:3]])
            
            results.append({
                "title": title,
                "summary": abstract,
                "link": p.get("url", ""),
                "authors": author_names,
                "year": p.get("year", "N/A"),
                "citations": p.get("citationCount", 0),
                "similarity": float(similarity),
                "source": "Semantic Scholar"
            })

        # Sort by similarity
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:max_results]
    
    except Exception as e:
        print(f"Error searching Semantic Scholar: {e}")
        return []


def search_papers_by_embedding(doc_summary, doc_embedding, full_text=None):
    """
    Main function: Search for similar papers using embeddings.
    Also extract citations from the document.
    
    Returns: {
        'similar_papers': [...],
        'extracted_citations': [...],
        'dois': [...]
    }
    """
    results = {
        'similar_papers': [],
        'extracted_citations': [],
        'dois': []
    }
    
    # 1. Search similar papers using embeddings
    arxiv_papers = search_arxiv_by_embedding(doc_embedding, doc_summary, max_results=4)
    semantic_papers = search_semantic_scholar_by_embedding(doc_embedding, doc_summary, max_results=4)
    
    # Combine and sort by similarity
    all_papers = arxiv_papers + semantic_papers
    all_papers.sort(key=lambda x: x['similarity'], reverse=True)
    
    # Remove duplicates based on title similarity
    seen_titles = set()
    unique_papers = []
    for paper in all_papers:
        title_normalized = paper['title'].lower().strip()
        if title_normalized not in seen_titles:
            seen_titles.add(title_normalized)
            unique_papers.append(paper)
    
    results['similar_papers'] = unique_papers[:7]
    
    # 2. Extract citations from the PDF text if provided
    if full_text:
        results['extracted_citations'] = extract_citations_from_text(full_text)
        results['dois'] = extract_dois_from_text(full_text)
    
    return results


def search_papers(doc_summary, doc_embedding=None, full_text=None):
    """
    Legacy function for backward compatibility.
    Now uses embedding-based search.
    """
    if doc_embedding is None:
        # Generate embedding from summary if not provided
        doc_embedding = embedding_model.encode(doc_summary)
    
    results = search_papers_by_embedding(doc_summary, doc_embedding, full_text)
    
    # Return in old format for compatibility
    return results['similar_papers']