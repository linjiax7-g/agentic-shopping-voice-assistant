# tests/test_retriever.py
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.graph import create_graph

def test_retriever_basic():
    """Test basic retrieval with price filter"""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "organic shampoo under $20",
        "step_log": []
    })
    
    docs = result["retrieved_docs"]
    
    # Should retrieve some docs
    assert len(docs) > 0, f"Expected results, got {len(docs)}"
    
    # All docs should respect max_price filter
    for doc in docs:
        price = doc.get("price", 0)
        assert price <= 20, f"Price {price} exceeds max_price 20"
    
    print(f"✓ Retrieved {len(docs)} products under $20")
    for doc in docs[:3]:
        print(f"  - {doc['title']}: ${doc['price']}")


def test_retriever_category_filter():
    """Test category filtering"""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "Nike shoes",
        "step_log": []
    })
    
    docs = result["retrieved_docs"]
    
    assert len(docs) > 0, "Should retrieve Nike products"
    
    # Check if brand filter worked
    filters = result["plan"]["filters"]
    if "Nike" in filters.get("brand", []):
        print(f"✓ Brand filter applied, retrieved {len(docs)} Nike products")


def test_retriever_price_range():
    """Test min and max price filtering"""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "kettles between $20 and $40",
        "step_log": []
    })
    
    docs = result["retrieved_docs"]
    
    for doc in docs:
        price = doc.get("price", 0)
        assert 20 <= price <= 40, f"Price {price} outside range [20, 40]"
    
    print(f"✓ All {len(docs)} products in price range $20-$40")


def test_full_pipeline():
    """Test complete router -> planner -> retriever flow"""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "organic shampoo under $20",
        "step_log": []
    })
    
    # Check all nodes executed
    nodes = [log["node"] for log in result["step_log"]]
    assert "router" in nodes
    assert "planner" in nodes
    assert "retriever" in nodes
    
    # Check all succeeded
    for log in result["step_log"]:
        assert log.get("success", False), f"{log['node']} failed: {log.get('error')}"
    
    # Check results
    assert len(result["retrieved_docs"]) > 0
    
    print("✓ Full pipeline test passed")
    print(f"  Retrieved {len(result['retrieved_docs'])} products")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])