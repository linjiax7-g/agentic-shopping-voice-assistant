# graph/nodes.py
from graph.state import GraphState
from graph.router import get_router_chain
from graph.planner import get_planner_chain
import json
import logging
logger = logging.getLogger(__name__)

def router_node(state: GraphState) -> GraphState:
    """Extract task, constraints, and safety flags using LangChain + HuggingFace."""
    
    query = state["query"]
    try:
        # Use the chain
        router_chain = get_router_chain()
        result = router_chain.invoke(query)
        
        # Update state
        state["task"] = result.task
        state["constraints"] = result.constraints.model_dump(exclude_none=True)
        state["safety_flags"] = result.safety_flags
        
        # Log
        state["step_log"].append({
            "node": "router",
            "input": query,
            "output": {
                "task": result.task,
                "constraints": state["constraints"],
                "safety_flags": result.safety_flags
            },
            "success": True
        })
        
    except Exception as e:
        # Fallback on error
        logger.error(f"Router error: {e}", exc_info=True)
        
        state["task"] = "product_search"
        state["constraints"] = {}
        state["safety_flags"] = []
        state["step_log"].append({
            "node": "router",
            "error": str(e),
            "success": False
        })
    
    return state

def planner_node(state: GraphState) -> GraphState:
    """
    Create a retrieval plan based on task and constraints.
    Uses rule-based logic for speed and reliability.
    """
    
    task = state["task"]
    constraints = state["constraints"]
    query = state["query"]
    
    try:
        # Use the chain
        planner_chain = get_planner_chain()
        
        # Prepare input for chain
        chain_input = {
            "query": state["query"],
            "task": state["task"],
            "constraints": state["constraints"]
        }
        
        # Invoke chain
        plan = planner_chain.invoke(chain_input)
        
        # Update state
        state["plan"] = plan
        
        # Log
        state["step_log"].append({
            "node": "planner",
            "input": {
                "task": task,
                "constraints": constraints
            },
            "output": plan,
            "success": True
        })
        
    except Exception as e:
        # Fallback plan
        state["plan"] = {
            "sources": ["private_rag"],
            "retrieval_fields": ["title", "price", "rating"],
            "comparison_criteria": ["price"],
            "filters": {}
        }
        state["step_log"].append({
            "node": "planner",
            "error": str(e),
            "success": False
        })
    
    return state