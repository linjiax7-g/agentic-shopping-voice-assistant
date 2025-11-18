# tests/test_planner.py
import pytest
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
logging.basicConfig(level=logging.WARNING, format='%(name)s - %(levelname)s - %(message)s')

from graph.graph import create_graph
import json

# ============================================================================
# BASIC FUNCTIONALITY TESTS
# ============================================================================

def test_planner_basic_product_search():
    """Test basic product search with single constraint."""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "organic shampoo under $20",
        "step_log": []
    })
    
    plan = result["plan"]
    
    # Validate sources
    assert plan["sources"] == ["private_rag"], f"Expected ['private_rag'], got {plan['sources']}"
    
    # Validate retrieval fields
    expected_fields = ["title", "brand", "price", "rating", "material"]
    for field in expected_fields:
        assert field in plan["retrieval_fields"], f"Missing field: {field}"
    
    # Validate filters (constraint mapping)
    assert plan["filters"]["max_price"] == 20, f"Expected max_price=20, got {plan['filters'].get('max_price')}"
    assert plan["filters"]["material"] == "organic", f"Expected material='organic', got {plan['filters'].get('material')}"
    assert plan["filters"]["category"] == "shampoo", f"Expected category='shampoo', got {plan['filters'].get('category')}"
    
    # Validate comparison criteria
    assert "price" in plan["comparison_criteria"]
    assert "rating" in plan["comparison_criteria"]
    
    print(f"✓ Basic product search test passed")


def test_planner_price_range():
    """Test product search with BOTH min and max price."""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "stainless steel kettles between $20 and $40",
        "step_log": []
    })
    
    plan = result["plan"]
    
    # Should have BOTH min_price and max_price
    assert plan["filters"]["min_price"] == 20, f"Expected min_price=20, got {plan['filters'].get('min_price')}"
    assert plan["filters"]["max_price"] == 40, f"Expected max_price=40, got {plan['filters'].get('max_price')}"
    assert plan["filters"]["material"] == "stainless steel"
    assert plan["filters"]["category"] == "kettle"
    
    print(f"✓ price range test passed")


def test_planner_min_price_only():
    """Test product search with only minimum price."""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "premium organic coffee above $30",
        "step_log": []
    })
    
    plan = result["plan"]
    
    # Should have min_price but NOT max_price
    assert int(plan["filters"]["min_price"]) == 30
    assert "max_price" not in plan["filters"], f"Should not have max_price, but got {plan['filters']}"
    assert plan["filters"]["material"] == "organic"
    
    print(f"✓ Min price only test passed")


# ============================================================================
# TASK-SPECIFIC TESTS
# ============================================================================

def test_planner_comparison_task():
    """Test comparison task with multiple brands."""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "compare Dove vs Pantene conditioner",
        "step_log": []
    })
    
    plan = result["plan"]
    
    # Validate task-specific fields
    assert "features" in plan["retrieval_fields"], "Comparison should include 'features'"
    assert "ingredients" in plan["retrieval_fields"], "Comparison should include 'ingredients'"
    assert "review_count" in plan["retrieval_fields"], "Comparison should include 'review_count'"
    
    # Validate comparison criteria
    assert "features" in plan["comparison_criteria"], "Comparison should compare 'features'"
    
    # Validate BOTH brands are in filters
    brands = plan["filters"].get("brand", [])
    assert "Dove" in brands, f"Expected 'Dove' in brands, got {brands}"
    assert "Pantene" in brands, f"Expected 'Pantene' in brands, got {brands}"
    assert len(brands) == 2, f"Expected exactly 2 brands, got {len(brands)}"
    
    print(f"✓ Comparison task test passed")


def test_planner_recommendation_task():
    """Test recommendation task (should prioritize quality)."""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "recommend the best vegan soap",
        "step_log": []
    })
    
    plan = result["plan"]
    
    # Should prioritize quality metrics
    assert "rating" in plan["comparison_criteria"], "Recommendation should prioritize 'rating'"
    assert "review_count" in plan["comparison_criteria"], "Recommendation should prioritize 'review_count'"
    
    # Should NOT prioritize price (unless query mentions price)
    # Allow price, but rating/review_count should be present
    
    # Validate material filter
    assert plan["filters"]["material"] == "vegan"
    
    print(f"✓ Recommendation task test passed")


def test_planner_availability_check():
    """Test availability_check task (should add web_search and in_stock field)."""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "is organic shampoo available now?",
        "step_log": []
    })
    
    plan = result["plan"]
    
    # Should include web search for live data
    assert "web_search" in plan["sources"], f"Expected web_search in sources, got {plan['sources']}"
    assert "private_rag" in plan["sources"], "Should still include private_rag"
    
    # Should have in_stock field
    assert "in_stock" in plan["retrieval_fields"], "Availability check should include 'in_stock'"
    
    # Should have NO comparison criteria (just checking availability)
    assert len(plan["comparison_criteria"]) == 0, f"Availability check should have no criteria, got {plan['comparison_criteria']}"
    
    # Should have filters
    assert plan["filters"]["material"] == "organic"
    assert plan["filters"]["category"] == "shampoo"
    
    print(f"✓ Availability check test passed")


# ============================================================================
# KEYWORD-TRIGGERED TESTS
# ============================================================================

def test_planner_cheap_keyword():
    """Test 'cheap' keyword affects criteria and price."""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "cheap Nike shoes",
        "step_log": []
    })
    
    plan = result["plan"]
    
    # Should have low max_price (router infers ~15 for "cheap")
    assert plan["filters"].get("max_price", 999) <= 20, f"'cheap' should set low max_price, got {plan['filters'].get('max_price')}"
    
    # Should prioritize price in comparison
    assert "price" in plan["comparison_criteria"], "Cheap query should prioritize 'price'"
    
    # May also have value_for_money
    # assert "value_for_money" in plan["comparison_criteria"]  # Optional
    
    # Should have brand filter
    assert "Nike" in plan["filters"].get("brand", [])
    
    print(f"✓ Cheap keyword test passed")


def test_planner_live_keywords():
    """Test various live data keywords trigger web_search."""
    
    graph = create_graph()
    
    live_keywords = [
        "is notebook available now?",
        "current price of Nike shoes",
        "latest sales of leather coat",
        "in stock vegan products",
        "can I buy shampoo today?"
    ]
    
    for query in live_keywords:
        result = graph.invoke({"query": query, "step_log": []})
        plan = result["plan"]
        
        assert "web_search" in plan["sources"], f"Query '{query}' should trigger web_search, got {plan['sources']}"
    
    print(f"✓ Live keywords test passed ({len(live_keywords)} queries)")


# ============================================================================
# CONSTRAINT MAPPING TESTS
# ============================================================================

def test_constraint_to_filter_mapping():
    """Test that router constraints correctly map to planner filters."""
    
    graph = create_graph()
    
    # Query with all constraint types
    result = graph.invoke({
        "query": "organic Nike shampoo between $10 and $30",
        "step_log": []
    })
    
    plan = result["plan"]
    constraints = result["constraints"]
    
    # Verify mappings
    if constraints.get("min_price"):
        assert plan["filters"]["min_price"] == constraints["min_price"], f"min_price should map to min_price, expected {constraints['min_price']}, got {plan['filters']['min_price']}"
    
    if constraints.get("max_price"):
        assert plan["filters"]["max_price"] == constraints["max_price"], f"max_price should map to max_price, expected {constraints['max_price']}, got {plan['filters']['max_price']}"
    
    if constraints.get("material"):
        assert plan["filters"]["material"] == constraints["material"], f"material should map to material, expected {constraints['material']}, got {plan['filters']['material']}"
    
    if constraints.get("brand"):
        assert plan["filters"]["brand"] == constraints["brand"], f"brand should map to brand, expected {constraints['brand']}, got {plan['filters']['brand']}"    
    
    if constraints.get("product"):
        assert plan["filters"]["category"] == constraints["product"], f"product should map to category, expected {constraints['product']}, got {plan['filters']['category']}"
    
    print(f"✓ Constraint mapping test passed")


def test_empty_constraints():
    """Test planner handles queries with no constraints."""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "show me some products",
        "step_log": []
    })
    
    plan = result["plan"]
    
    # Should still have valid plan structure
    assert "sources" in plan
    assert "retrieval_fields" in plan
    assert "filters" in plan
    
    # Filters might be empty or minimal
    assert isinstance(plan["filters"], dict)
    
    print(f"✓ Empty constraints test passed")


def test_partial_constraints():
    """Test planner handles partial constraints (some null values)."""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "Nike products",
        "step_log": []
    })
    
    plan = result["plan"]
    
    # Should have brand filter
    assert "Nike" in plan["filters"].get("brand", [])
    
    # Should NOT have price filters if not mentioned
    # (Optional: can be lenient here)
    
    print(f"✓ Partial constraints test passed")


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

def test_planner_fallback():
    """Test planner has sensible fallback when it fails."""
    
    graph = create_graph()
    
    # Use a nonsensical query that might break the planner
    result = graph.invoke({
        "query": "asdfghjkl zxcvbnm qwerty",
        "step_log": []
    })
    
    plan = result.get("plan", {})
    
    # Should have fallback plan
    assert "sources" in plan, "Should have fallback sources"
    assert "retrieval_fields" in plan, "Should have fallback fields"
    assert "filters" in plan, "Should have fallback filters"
    
    # Fallback should include at least private_rag
    assert "private_rag" in plan.get("sources", [])
    
    print(f"✓ Planner fallback test passed")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

def test_router_planner_integration():
    """Test that router output correctly flows into planner."""
    
    graph = create_graph()
    
    result = graph.invoke({
        "query": "organic shampoo under $20",
        "step_log": []
    })
    
    # Check router succeeded
    router_log = [log for log in result["step_log"] if log["node"] == "router"]
    assert len(router_log) > 0, "Router should have logged"
    assert router_log[0].get("success", False), "Router should succeed"
    
    # Check planner succeeded
    planner_log = [log for log in result["step_log"] if log["node"] == "planner"]
    assert len(planner_log) > 0, "Planner should have logged"
    assert planner_log[0].get("success", False), "Planner should succeed"
    
    # Check data flow
    assert result["task"] is not None, "Task should be set by router"
    assert result["constraints"] is not None, "Constraints should be set by router"
    assert result["plan"] is not None, "Plan should be set by planner"
    
    print(f"✓ Router-Planner integration test passed")


# ============================================================================
# STRESS TESTS
# ============================================================================

def test_planner_consistency():
    """Test that same query produces consistent plans."""
    
    graph = create_graph()
    
    query = "organic shampoo under $20"
    
    # Run same query 3 times
    results = []
    for _ in range(3):
        result = graph.invoke({"query": query, "step_log": []})
        results.append(result["plan"])
    
    # Plans should be identical (or very similar)
    # Check sources are consistent
    sources = [set(r["sources"]) for r in results]
    assert all(s == sources[0] for s in sources), f"Sources should be consistent: {sources}"
    
    # Check filters are consistent
    filters = [r["filters"] for r in results]
    assert all(f == filters[0] for f in filters), f"Filters should be consistent: {filters}"
    
    print(f"✓ Planner consistency test passed")


# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])