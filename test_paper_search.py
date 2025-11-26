# test_paper_search.py - Test embedding-based search
from paper_search import search_papers_by_embedding, extract_citations_from_text
from sentence_transformers import SentenceTransformer
import numpy as np

print("=" * 60)
print("🧪 TESTING ENHANCED PAPER SEARCH")
print("=" * 60)

# Test 1: Embedding generation
print("\n1. Testing embedding generation...")
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
test_summary = "This paper discusses machine learning approaches for natural language processing"
embedding = model.encode(test_summary)
print(f"✅ Embedding generated: shape {embedding.shape}, type {type(embedding)}")

# Test 2: Citation extraction
print("\n2. Testing citation extraction...")
sample_text = """
References:
[1] Smith, J., & Johnson, A. (2020). Deep learning for NLP. Conference on AI.
[2] Brown, M. et al. (2019). Neural networks in practice. Journal of ML.

As discussed by (Williams, 2021), the methodology shows promising results.
"""
citations = extract_citations_from_text(sample_text)
print(f"✅ Extracted {len(citations)} citations")
for c in citations:
    print(f"   - {c[:80]}...")

# Test 3: Search papers by embedding
print("\n3. Testing embedding-based paper search...")
try:
    results = search_papers_by_embedding(test_summary, embedding, sample_text)
    
    print(f"✅ Found {len(results['similar_papers'])} similar papers")
    print(f"✅ Extracted {len(results['extracted_citations'])} citations")
    print(f"✅ Found {len(results['dois'])} DOIs")
    
    if results['similar_papers']:
        print("\n📄 Top similar paper:")
        top_paper = results['similar_papers'][0]
        print(f"   Title: {top_paper['title'][:60]}...")
        print(f"   Similarity: {top_paper['similarity']*100:.1f}%")
        print(f"   Source: {top_paper['source']}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ ALL TESTS COMPLETED")
print("=" * 60)