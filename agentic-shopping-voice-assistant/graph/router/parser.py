# graph/router/parser.py
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.exceptions import OutputParserException
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, List
import json
import re
import logging
logger = logging.getLogger(__name__)

# Valid safety flags for filtering
VALID_SAFETY_FLAGS = {"inappropriate_content", "medical_advice", "dangerous_product"}

class Constraints(BaseModel):
    # description: documentation for the LLM/parser
    product: Optional[str] = Field(None, description="Product type or category (e.g., 'shoes', 'laptop', 'cleaner')")
    min_price: Optional[float] = Field(None, description="Minimum price in USD")
    max_price: Optional[float] = Field(None, description="Maximum price in USD")
    material: Optional[str] = Field(None, description="Material preference (e.g., 'leather', 'stainless steel')")
    brand: Optional[List[str]] = Field(None, description="Brand name(s) as a list (e.g., ['Nike', 'Adidas'])")
    
    model_config = {"extra": "forbid"}  # Don't allow extra fields

class RouterOutput(BaseModel):
    task: Literal["product_search", "comparison", "recommendation", "availability_check"]
    constraints: Constraints
    safety_flags: List[str] = Field(default_factory=list)
    
    @field_validator('safety_flags')
    @classmethod
    def validate_safety_flags(cls, v):
        return [flag for flag in v if flag in VALID_SAFETY_FLAGS]

def extract_json_from_router_output(text: str) -> Optional[dict]:
    """Extract JSON from potentially messy output."""
    
    # Clean up common prefixes
    text = text.strip()
    text = re.sub(r'^(Output:|JSON:|Assistant:)\s*', '', text, flags=re.IGNORECASE)
    
    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    
    # Find JSON object
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try to fix common issues
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

# Create parser
parser = PydanticOutputParser(pydantic_object=RouterOutput)

def parse_router_output(text: str) -> RouterOutput:
    """Parse LLM output with fallback."""
    data = extract_json_from_router_output(text)
    logger.debug(f"🔍 Extracted JSON: {data}")
    
    if data is None:
        logger.warning("No JSON found in LLM output, using defaults")
        return RouterOutput(
            task="product_search",
            constraints=Constraints(),
            safety_flags=[]
        )
        
    # Validate and normalize
    task = data.get("task", "product_search")
    if task not in ["product_search", "comparison", "recommendation", "availability_check"]:
        task = "product_search"
    
    # Extract constraints with type coercion
    constraints_data = data.get("constraints", {})
    
    # Coerce prices to float
    min_price = constraints_data.get("min_price")
    if min_price is not None and min_price != "null" and min_price != "":
        try:
            min_price = float(min_price)
        except (ValueError, TypeError):
            min_price = None
    else:
        min_price = None
    
    max_price = constraints_data.get("max_price")
    if max_price is not None and max_price != "null" and max_price != "":
        try:
            max_price = float(max_price)
        except (ValueError, TypeError):
            max_price = None
    else:
        max_price = None
    
    # Ensure brand is array
    brand = constraints_data.get("brand")
    if brand is None:
        brand = []
    elif isinstance(brand, str):
        brand = [brand] if brand else []
    elif not isinstance(brand, list):
        brand = []
    
    # Create Constraints object
    constraints = Constraints(
        product=constraints_data.get("product"),
        min_price=min_price,
        max_price=max_price,
        material=constraints_data.get("material"),
        brand=brand
    )
    
    # Create RouterOutput object
    result = RouterOutput(
        task=task,
        constraints=constraints,
        safety_flags=data.get("safety_flags", [])
    )
    
    return result