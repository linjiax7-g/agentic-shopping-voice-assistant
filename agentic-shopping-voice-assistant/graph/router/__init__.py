# graph/router/__init__.py
from graph.models.llm import get_llm
from graph.router.prompts import router_prompt
from graph.router.parser import parse_router_output
from langchain_core.runnables import RunnablePassthrough

def create_router_chain():
    """Create the router LCEL chain."""
    llm = get_llm()
    
    chain = (
        {"query": RunnablePassthrough()}
        | router_prompt
        | llm
        | parse_router_output
    )
    
    return chain

# Singleton pattern
_router_chain = None

def get_router_chain():
    """Get or create router chain (lazy loading)."""
    global _router_chain
    if _router_chain is None:
        _router_chain = create_router_chain()
    return _router_chain