# graph/retriever/web.py
"""
Web search retrieval logic (MCP integration point)
This is a MOCK implementation - Web Search Team will replace this
"""

from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


def retrieve_from_web(
    query: str,
    filters: Dict,
    k: int = 5
) -> List[Dict]:
    """
    Retrieve products from live web search
    
    Args:
        query: Search query text
        filters: Dict with category, min_price, max_price, brand, material
        k: Number of results
    
    Returns:
        List of product dicts with standard format
    
    NOTE: This is a MOCK implementation!
    Web Search Team should replace this with real MCP integration.
    """
    
    logger.warning("[WEB] Using MOCK web search (not implemented yet)")
    
    # TODO: Web Search Team - Replace with real implementation
    # Example integration:
    # from mcp_client import search_products
    # results = search_products(query, filters)
    
    # Mock results for testing
    mock_results = [
        {
            "doc_id": "web_001",
            "title": f"[WEB MOCK] Product matching '{query}'",
            "price": 15.99,
            "category": filters.get("category", "unknown"),
            "brand": filters.get("brand", ["Unknown"])[0] if filters.get("brand") else "Unknown",
            "material": filters.get("material", "unknown"),
            "content": f"This is a mock web search result for '{query}'. Real implementation needed.",
            "score": 0.95,
            "source": "web",  # 标记来源
            "url": "https://example.com/product"  # Web 独有字段
        }
    ]
    
    logger.info(f"[WEB] Returned {len(mock_results)} mock results")
    
    return mock_results[:k]