# graph/planner/parser.py
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Literal, Any
import json
import re

class PlannerOutput(BaseModel):
    sources: List[Literal["private_rag", "web_search"]] = Field(
        description="Which data sources to query"
    )
    retrieval_fields: List[str] = Field(
        description="Which product fields to retrieve"
    )
    comparison_criteria: List[str] = Field(
        default_factory=list,
        description="How to compare/rank products"
    )
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Filters to apply during retrieval"
    )
    
    @field_validator('sources')
    @classmethod
    def validate_sources(cls, v):
        """Ensure at least one source."""
        if not v or len(v) == 0:
            return ["private_rag"]
        return v
    
    @field_validator('retrieval_fields')
    @classmethod
    def validate_fields(cls, v):
        """Ensure we have at least basic fields."""
        if not v or len(v) == 0:
            return ["title", "price", "rating"]
        return v

def extract_json_from_planner_output(text: str) -> Optional[dict]:
    """Extract JSON from LLM output."""
    
    # Clean up
    text = text.strip()
    text = re.sub(r'^(Output:|JSON:|Plan:)\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    
    # Find JSON
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try fixes
            json_str = json_str.replace("'", '"')
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            try:
                return json.loads(json_str)
            except:
                pass
    
    # Last resort
    try:
        return json.loads(text)
    except:
        return None

def parse_planner_output(text: str) -> dict:
    """Parse LLM planner output with fallback."""
    
    data = extract_json_from_planner_output(text)
    
    if data is None:
        # Fallback plan
        return {
            "sources": ["private_rag"],
            "retrieval_fields": ["title", "price", "rating"],
            "comparison_criteria": ["price"],
            "filters": {}
        }
    
    # Validate and normalize
    result = {
        "sources": data.get("sources", ["private_rag"]),
        "retrieval_fields": data.get("retrieval_fields", ["title", "price", "rating"]),
        "comparison_criteria": data.get("comparison_criteria", []),
        "filters": data.get("filters", {})
    }
    
    # Ensure sources are valid
    valid_sources = {"private_rag", "web_search"}
    result["sources"] = [s for s in result["sources"] if s in valid_sources]
    if not result["sources"]:
        result["sources"] = ["private_rag"]
    
    return result