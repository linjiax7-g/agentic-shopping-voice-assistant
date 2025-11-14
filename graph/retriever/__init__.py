# graph/retriever/__init__.py
"""
Unified retriever interface
Maintains backward compatibility with v1
"""

from graph.retriever.rag import retrieve_from_rag, get_vector_store
from graph.retriever.web import retrieve_from_web
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = ['retrieve_products', 'retrieve_from_rag', 'retrieve_from_web', 'get_vector_store']


def retrieve_products(
    query: str,
    filters: Dict,
    k: int = 5
) -> List[Dict]:
    """
    Original unified retriever (for v1 compatibility)
    Just calls RAG retriever
    
    Args:
        query: Search query text
        filters: Dict with category, min_price, max_price, brand, material
        k: Number of results
    
    Returns:
        List of product dicts
    """
    return retrieve_from_rag(query, filters, k)