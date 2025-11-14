# graph/strategies.py
"""
Routing strategies for different graph versions
All conditional logic in one place
"""

from graph.state import GraphState
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Hybrid ConditionalRetrieval Router
# ============================================================================

def retrieval_router_hybrid(state: GraphState) -> str:
    """
    Decide which retriever to use based on planner's sources
    
    Returns:
        "rag_only" | "web_only" | "hybrid"
    """
    sources = state["plan"].get("sources", ["private_rag"])
    
    has_rag = "private_rag" in sources
    has_web = "web_search" in sources
    
    if has_rag and has_web:
        logger.info("📊 Routing: Using HYBRID retrieval (RAG + Web)")
        return "hybrid"
    elif has_web:
        logger.info("🌐 Routing: Using WEB retrieval only")
        return "web_only"
    else:
        logger.info("🗄️ Routing: Using RAG retrieval only")
        return "rag_only"


# ============================================================================
# Add Reflection Loop
# ============================================================================

def retrieval_router_reflection(state: GraphState) -> str:
    """
    Decide whether to refine or finish
    
    Returns:
        "refine" | "done"
    """
    num_docs = len(state.get("retrieved_docs", []))
    
    if num_docs < 3:
        logger.info("🔄 Reflection: Too few results, refining query...")
        return "refine"
    else:
        logger.info("✅ Reflection: Results sufficient, proceeding to answer")
        return "done"


# ============================================================================
# Transform into Autonomous Agent
# ============================================================================

def retrieval_router_autonomous(state: GraphState) -> str:
    """
    Agent decides next action autonomously
    
    Returns:
        "search_rag" | "search_web" | "answer" | "ask_user" | "done"
    """
    # TODO: Implement with LLM-based decision making
    # This would be similar to ReAct pattern
    
    # For now, simple heuristic
    if not state.get("retrieved_docs"):
        return "search_rag"
    elif len(state["retrieved_docs"]) < 3:
        return "search_web"
    elif not state.get("answer"):
        return "answer"
    else:
        return "done"