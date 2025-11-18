# tests/test_router.py
import pytest
import sys
import logging
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set up logging (only show warnings and errors)
logging.basicConfig(level=logging.WARNING, format='%(name)s - %(levelname)s - %(message)s')

from graph.graph import create_graph
from graph.state import GraphState

def test_router_basic():
    """Test basic router functionality."""
    
    graph = create_graph()
    
    initial_state = GraphState(
        query="organic shampoo under $20",
        step_log=[]
    )
    
    # Run only the router node for testing
    result = graph.invoke(initial_state)
    
    # Assertions
    assert result["task"] == "product_search", f"Expected 'product_search', got '{result.get('task')}'"
    assert result["constraints"].get("max_price") in [20, 20.0], f"Expected max_price=20, got {result['constraints'].get('max_price')}"
    assert result["constraints"].get("material") == "organic", f"Expected material='organic', got '{result['constraints'].get('material')}'"
    assert len(result["safety_flags"]) == 0, f"Expected no safety flags, got {result['safety_flags']}"
    
def test_router_comparison():
    """Test comparison query."""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "compare Nike vs Adidas running shoes",
        "step_log": []
    })
    
    assert result["task"] == "comparison", f"Expected 'comparison', got '{result.get('task')}'"
    assert "Nike" in result["constraints"].get("brand", []) or "Adidas" in result["constraints"].get("brand", []), f"Expected brand with Nike/Adidas, got {result['constraints'].get('brand')}"

def test_router_safety():
    """Test safety flag detection."""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "medicine to cure my disease",
        "step_log": []
    })
    
    assert "medical_advice" in result["safety_flags"], f"Expected 'medical_advice' in safety_flags, got {result.get('safety_flags')}"

def test_router_max_price_only():
    """Test router extracts max_price from 'under $X'."""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "organic shampoo under $20",
        "step_log": []
    })
    
    constraints = result["constraints"]
    
    # Router should extract max_price only
    assert constraints.get("max_price") - 20 <= 0.1, f"Expected max_price=20, got {constraints.get('max_price')}"
    assert constraints.get("min_price") is None, f"Should not have min_price, got {constraints.get('min_price')}"
    assert constraints.get("material") == "organic"


def test_router_min_price_only():
    """Test router extracts min_price from 'above $X'."""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "premium organic coffee above $30",
        "step_log": []
    })
    
    constraints = result["constraints"]
    
    # Router should extract min_price only
    assert constraints.get("min_price") - 30 <= 0.1, f"Expected min_price=30, got {constraints.get('min_price')}"
    assert constraints.get("max_price") is None, f"Should not have max_price, got {constraints.get('max_price')}"
    assert constraints.get("material") == "organic"


def test_router_price_range():
    """Test router extracts BOTH min and max price from 'between $X and $Y'."""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "stainless steel kettles between $20 and $40",
        "step_log": []
    })
    
    constraints = result["constraints"]
    
    # Router should extract BOTH
    assert constraints.get("min_price") - 20 <= 0.1, f"Expected min_price=20, got {constraints.get('min_price')}"
    assert constraints.get("max_price") - 40 <= 0.1, f"Expected max_price=40, got {constraints.get('max_price')}"
    assert constraints.get("material") == "stainless steel"


def test_router_around_price():
    """Test router extracts range from 'around $X'."""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "leather Nike shoes around $80",
        "step_log": []
    })
    
    constraints = result["constraints"]
    
    # Router should create a range (e.g., 80*0.8 to 80*1.2 = 64 to 96)
    assert constraints.get("min_price") is not None, "Should have min_price for 'around'"
    assert constraints.get("max_price") is not None, "Should have max_price for 'around'"
    
    # Allow some tolerance in the calculation
    assert 70 <= constraints.get("min_price") <= 75, f"min_price should be ~72, got {constraints.get('min_price')}"
    assert 85 <= constraints.get("max_price") <= 90, f"max_price should be ~88, got {constraints.get('max_price')}"


def test_router_cheap_keyword():
    """Test router infers price from 'cheap' keyword."""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "cheap vegan soap",
        "step_log": []
    })
    
    constraints = result["constraints"]
    
    # Router should infer max_price ~15 for "cheap"
    assert constraints.get("max_price") is not None, "Should infer max_price for 'cheap'"
    assert constraints.get("max_price") <= 20, f"'cheap' should be ≤20, got {constraints.get('max_price')}"


def test_router_premium_keyword():
    """Test router infers price from 'premium/expensive' keyword."""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "expensive luxury shampoo",
        "step_log": []
    })
    
    constraints = result["constraints"]
    
    # Router should infer min_price ~100 for "expensive"
    assert constraints.get("min_price") is not None, "Should infer min_price for 'expensive'"
    assert constraints.get("min_price") >= 80, f"'expensive' should be ≥100, got {constraints.get('min_price')}"
    

if __name__ == "__main__":
    pytest.main([__file__, "-v"])