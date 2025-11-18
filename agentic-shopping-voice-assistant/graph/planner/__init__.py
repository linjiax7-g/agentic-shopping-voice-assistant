# graph/planner/__init__.py
from graph.models.llm import get_llm
from graph.planner.prompts import planner_prompt
from graph.planner.parser import parse_planner_output
from langchain_core.runnables import RunnableLambda
import json

def format_planner_input(state_dict: dict) -> dict:
    """Format state for planner prompt."""
    return {
        "query": state_dict["query"],
        "task": state_dict["task"],
        "constraints": json.dumps(state_dict["constraints"], indent=2)
    }

def create_planner_chain():
    """Create the planner LCEL chain."""
    llm = get_llm()
    
    chain = (
        RunnableLambda(format_planner_input)
        | planner_prompt
        | llm
        | parse_planner_output
    )
    
    return chain

# Singleton pattern
_planner_chain = None

def get_planner_chain():
    """Get or create planner chain (lazy loading)."""
    global _planner_chain
    if _planner_chain is None:
        _planner_chain = create_planner_chain()
    return _planner_chain