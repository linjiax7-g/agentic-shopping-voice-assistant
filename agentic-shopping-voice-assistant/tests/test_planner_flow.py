# test_router_flow.py
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graph.graph import create_graph
import json

graph = create_graph()

test_cases = [
    "organic shampoo under $20",
    "compare Dove vs Pantene conditioner",
    "is vegan soap available now?",
    "recommend the best Nike shoes",
    "cheap stainless steel kettle"
]

print("Testing LLM-Based Planner\n")

for query in test_cases:
    print(f"{'='*70}")
    print(f"Query: {query}")
    print(f"{'='*70}\n")
    
    result = graph.invoke({
        "query": query,
        "step_log": []
    })
    
    # Router output
    print("ROUTER:")
    print(f"  Task: {result['task']}")
    print(f"  Constraints: {json.dumps(result['constraints'], indent=4)}")
    
    # Planner output
    print("\nPLANNER:")
    print(f"  Sources: {result['plan']['sources']}")
    print(f"  Fields: {result['plan']['retrieval_fields']}")
    print(f"  Criteria: {result['plan']['comparison_criteria']}")
    print(f"  Filters: {json.dumps(result['plan']['filters'], indent=4)}")
    
    # Success check
    planner_log = [log for log in result['step_log'] if log['node'] == 'planner'][0]
    print(f"\nStatus: {'✓ Success' if planner_log.get('success') else '✗ Failed'}")
    
    if not planner_log.get('success'):
        print(f"Error: {planner_log.get('error')}")
    
    print()

print("Testing complete!")