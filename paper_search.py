# paper_search.py - Memory-optimized version
import requests
import re
import numpy as np

def get_embedding_model():
    """Use cached model from app.py"""
    try:
        from app import get_embedding_model as get_cached_model
        return get_cached_model()
    except:
        # Fallback if import fails
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

def extract_citations_from_text(full_text):
    """Extract citations/references from the PDF text."""
    citations = []
    
    # Pattern 1: References section
    ref_section = re.search(r'(?:references|bibliography|works cited)(.*?)(?:\n\n\n|\Z)', 
                           full_text.lower(), re.DOTALL | re.IGNORECASE)
    
    if ref_section:
        ref_text = ref_section.group(1)
        
        # Extract individual references
        pattern1 = r'([A-Z][a-z]+(?:,?\s+[A-Z]\.?\s*)+(?:et al\.)?\s*\(\d{4}\)\.?\s+[^.]+\.)'
        matches1 = re.findall(pattern1, ref_text)
        citations.extend(matches1)
        
        pattern2 = r'\[\d+\]\s+([A-Z][^.]+\.\s+\(\d{4}\)[^.]+\.)'
        matches2 = re.findall(pattern2, ref_text)
        citations.extend(matches2)
    
    # Pattern 2: In-text citations
    intext_pattern = r'\(([A-Z][a-z]+(?:\s+et al\.)?,?\s+\d{4})\)'
    intext_citations = re.findall(intext_pattern, full_text)
    
    # Deduplicate and clean
    citations = list(set(citations + intext_citations))
    citations = [c.strip() for c in citations if len(c.strip()) > 10]
    
    return citations[:15]

def extract_dois_from_text(full_text):
    """Extract DOIs from text."""
    doi_pattern = r'10\.\d{4,9}/[-._;()/:A-Za-z0-9]+'
    dois = re.findall(doi_pattern, full_text)
    return list(set(dois))[:10]

def search_arxiv_simple(query, max_results=5):
    """Simplified arXiv search without embeddings"""
    url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={max_results}"
    
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

            results.append({
                "title": title,
                "summary": summary,
                "link": link,
                "source": "arXiv"
            })

        return results[:max_results]
    
    except Exception as e:
        print(f"Error searching arXiv: {e}")
        return []

def search_semantic_scholar_simple(query, max_results=5):
    """Simplified Semantic Scholar search"""
    url = f"https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": max_results,
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
            abstract = p.get("abstract", "No abstract available")
            
            if not title:
                continue
            
            authors = p.get("authors", [])
            author_names = ", ".join([a.get("name", "") for a in authors[:3]])
            
            results.append({
                "title": title,
                "summary": abstract if abstract else "No abstract available",
                "link": p.get("url", ""),
                "authors": author_names,
                "year": p.get("year", "N/A"),
                "citations": p.get("citationCount", 0),
                "source": "Semantic Scholar"
            })

        return results[:max_results]
    
    except Exception as e:
        print(f"Error searching Semantic Scholar: {e}")
        return []

def search_papers(doc_summary, doc_embedding=None, full_text=None):
    """
    Main function: Search for similar papers.
    Optimized to avoid loading models unnecessarily.
    """
    # Extract key terms from summary for search
    search_query = ' '.join(doc_summary.split()[:30])  # First 30 words
    
    print(f"🔍 Searching for: {search_query[:100]}...")
    
    # Search both sources
    arxiv_papers = search_arxiv_simple(search_query, max_results=4)
    semantic_papers = search_semantic_scholar_simple(search_query, max_results=4)
    
    # Combine results
    all_papers = arxiv_papers + semantic_papers
    
    # Remove duplicates based on title similarity
    seen_titles = set()
    unique_papers = []
    for paper in all_papers:
        title_normalized = paper['title'].lower().strip()
        if title_normalized not in seen_titles:
            seen_titles.add(title_normalized)
            unique_papers.append(paper)
    
    print(f"✅ Found {len(unique_papers)} unique papers")
    
    return unique_papers[:7]
