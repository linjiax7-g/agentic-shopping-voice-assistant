# graph/retriever/rag.py
"""
Private RAG retrieval logic
Extracted from original retriever/__init__.py
"""

try:
    from langchain_chroma import Chroma  # Preferred if available
except ModuleNotFoundError:
    from langchain_community.vectorstores import Chroma  # Fallback without extra dependency
from langchain_huggingface import HuggingFaceEmbeddings
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

_vector_store = None

def get_vector_store(persist_directory: str = "./chroma_db"):
    """Get or create vector store (singleton)"""
    global _vector_store
    
    if _vector_store is None:
        embedder = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        _vector_store = Chroma(
            persist_directory=persist_directory,
            embedding_function=embedder
        )
    
    return _vector_store


def retrieve_from_rag(
    query: str,
    filters: Dict,
    k: int = 5
) -> List[Dict]:
    """
    Retrieve products from private RAG
    
    Args:
        query: Search query text
        filters: Dict with category, min_price, max_price, brand, material
        k: Number of results
    
    Returns:
        List of product dicts with standard format
    """
    vector_store = get_vector_store()
    
    # Get more results for post-filtering
    results = vector_store.similarity_search_with_score(
        query=query,
        k=k * 3
    )
    
    logger.info(f"[RAG] Retrieved {len(results)} candidates before filtering")
    
    # Post-process filtering
    filtered_results = []
    for doc, score in results:
        metadata = doc.metadata
        
        if not _matches_filters(metadata, filters):
            continue
        
        # Build result dict
        result = {
            "doc_id": metadata.get("Uniq Id"),
            "title": metadata.get("Product Name"),
            "price": _parse_price(metadata.get("Selling Price")),
            "category": metadata.get("category", ""),
            "brand": metadata.get("brand", ""),
            "material": metadata.get("material", ""),
            "content": doc.page_content,
            "score": float(score),
            "source": "rag"  # 标记来源
        }
        
        filtered_results.append(result)
        
        if len(filtered_results) >= k:
            break
    
    logger.info(f"[RAG] Returned {len(filtered_results)} products after filtering")
    
    return filtered_results


def _parse_price(price_str) -> float:
    """Parse price string to float"""
    try:
        price_str = str(price_str).replace(',', '').replace('₹', '').replace('$', '')
        return float(price_str)
    except (ValueError, TypeError):
        return 0.0


def _matches_filters(metadata: Dict, filters: Dict) -> bool:
    """Check if document matches filter criteria"""
    
    # Category filter
    if "category" in filters and filters["category"]:
        doc_category = str(metadata.get("category", "")).lower()
        filter_category = str(filters["category"]).lower()
        if filter_category not in doc_category and doc_category != filter_category:
            return False
    
    # Price filtering
    price = _parse_price(metadata.get("Selling Price", 0))
    
    if "min_price" in filters:
        if price < filters["min_price"]:
            return False
    
    if "max_price" in filters:
        if price > filters["max_price"]:
            return False
    
    # Brand filtering
    if "brand" in filters and filters["brand"]:
        doc_brand = str(metadata.get("brand", "")).lower()
        filter_brands = [b.lower() for b in filters["brand"]]
        if not any(fb in doc_brand for fb in filter_brands):
            return False
    
    # Material filtering
    if "material" in filters and filters["material"]:
        doc_material = str(metadata.get("material", "")).lower()
        filter_material = str(filters["material"]).lower()
        if filter_material not in doc_material:
            return False
    
    return True