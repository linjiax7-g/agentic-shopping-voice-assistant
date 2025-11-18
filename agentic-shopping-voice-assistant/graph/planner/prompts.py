# graph/planner/prompts.py
from langchain_core.prompts import PromptTemplate

PLANNER_TEMPLATE = """<|im_start|>system
You are a retrieval planner for a product search system. Create an optimal plan for retrieving and comparing products.<|im_end|>
<|im_start|>user
Create a retrieval plan based on the user's request.

User Query: {query}
Task Type: {task}
Router Constraints: {constraints}

Return a JSON object with this structure:
{{
  "sources": ["private_rag"] or ["private_rag", "web_search"],
  "retrieval_fields": array of field names,
  "comparison_criteria": array of criteria,
  "filters": object with filter conditions
}}

DECISION RULES:

1. SOURCES - Which data sources to query:
   
   DEFAULT: ["private_rag"]
   
   ADD "web_search" if:
   - Query contains: "now", "current", "latest", "today", "available", "in stock"
   - Task is "availability_check"
   
   Examples:
   - "organic shampoo" → ["private_rag"]
   - "is shampoo available NOW?" → ["private_rag", "web_search"]

2. RETRIEVAL_FIELDS - Which product attributes to fetch:
   
   Available fields: title, brand, price, rating, category, material, features, ingredients, in_stock, review_count
   
   Based on task:
   - product_search: ["title", "brand", "price", "rating", "material"]
   - comparison: ["title", "brand", "price", "rating", "features", "ingredients", "review_count"]
   - recommendation: ["title", "brand", "price", "rating", "features", "review_count"]
   - availability_check: ["title", "brand", "price", "in_stock"]

3. COMPARISON_CRITERIA - How to rank/evaluate products:
   
   Available criteria: price, rating, review_count, features, value_for_money
   
   Rules:
   - Default: ["price", "rating"]
   - If query has "cheap", "affordable": ["price", "value_for_money"]
   - If query has "best", "top", "recommend": ["rating", "review_count"]
   - For comparison task: ["price", "rating", "features"]
   - For availability_check: [] (no comparison needed)

4. FILTERS - Convert router constraints to database filters:
   
   CRITICAL: Map constraint field names to filter field names:
   
   Router constraint → Database filter:
   - min_price → min_price
   - max_price → max_price
   - material → material
   - brand → brand (keep as array)
   - product → category
   
   ALWAYS include ALL non-null constraints in filters!

EXAMPLES (Follow these EXACTLY):

Example 1 - Basic product search:
Input:
  Query: "organic shampoo under $20"
  Task: "product_search"
  Constraints: {{"product": "shampoo", "max_price": 20, "material": "organic", "brand": []}}

Output:
{{"sources": ["private_rag"], "retrieval_fields": ["title", "brand", "price", "rating", "material"], "comparison_criteria": ["price", "rating"], "filters": {{"category": "shampoo", "max_price": 20, "material": "organic"}}}}

Explanation: max_price→max_price, product→category, brand is empty so not in filters

Example 2 - Comparison with brands:
Input:
  Query: "compare Dove vs Pantene conditioner"
  Task: "comparison"
  Constraints: {{"product": "conditioner", "brand": ["Dove", "Pantene"], "min_price": null, "max_price": null, "material": null}}

Output:
{{"sources": ["private_rag"], "retrieval_fields": ["title", "brand", "price", "rating", "features", "ingredients", "review_count"], "comparison_criteria": ["price", "rating", "features"], "filters": {{"category": "conditioner", "brand": ["Dove", "Pantene"]}}}}

Explanation: product→category, brand array copied as-is, null values omitted from filters

Example 3 - Availability check with live data:
Input:
  Query: "is organic shampoo available now?"
  Task: "availability_check"
  Constraints: {{"product": "shampoo", "material": "organic", "brand": [], "min_price": null, "max_price": null}}

Output:
{{"sources": ["private_rag", "web_search"], "retrieval_fields": ["title", "brand", "price", "in_stock"], "comparison_criteria": [], "filters": {{"category": "shampoo", "material": "organic"}}}}

Explanation: "available now" triggers web_search, material included in filters, empty brand omitted

Example 4 - Recommendation with quality focus:
Input:
  Query: "recommend the best vegan soap"
  Task: "recommendation"
  Constraints: {{"product": "soap", "material": "vegan", "brand": [], "min_price": null, "max_price": null}}

Output:
{{"sources": ["private_rag"], "retrieval_fields": ["title", "brand", "price", "rating", "features", "review_count"], "comparison_criteria": ["rating", "review_count"], "filters": {{"category": "soap", "material": "vegan"}}}}

Explanation: "best" keyword → prioritize rating/review_count

Example 5 - price range query:
Input:
  Query: "stainless steel kettles between $20 and $40"
  Task: "product_search"
  Constraints: {{"product": "kettle", "min_price": 20, "max_price": 40, "material": "stainless steel", "brand": []}}

Output:
{{"sources": ["private_rag"], "retrieval_fields": ["title", "brand", "price", "rating", "material"], "comparison_criteria": ["price", "rating"], "filters": {{"category": "kettle", "min_price": 20, "max_price": 40, "material": "stainless steel"}}}}

Explanation: BOTH min_price→min_price AND max_price→max_price in filters

Example 6 - Cheap products (inferred price):
Input:
  Query: "cheap Nike shoes"
  Task: "product_search"
  Constraints: {{"product": "shoes", "brand": ["Nike"], "max_price": 15, "min_price": null, "material": null}}

Output:
{{"sources": ["private_rag"], "retrieval_fields": ["title", "brand", "price", "rating"], "comparison_criteria": ["price", "value_for_money"], "filters": {{"category": "shoes", "brand": ["Nike"], "max_price": 15}}}}

Explanation: "cheap" → max_price in router, affects comparison_criteria too

Example 7 - Premium products:
Input:
  Query: "premium organic coffee above $30"
  Task: "product_search"
  Constraints: {{"product": "coffee", "min_price": 30, "material": "organic", "brand": [], "max_price": null}}

Output:
{{"sources": ["private_rag"], "retrieval_fields": ["title", "brand", "price", "rating", "material"], "comparison_criteria": ["price", "rating"], "filters": {{"category": "coffee", "min_price": 30, "material": "organic"}}}}

Explanation: min_price→min_price (note: no max_price)

Example 8 - Latest live price check with live data:
Input:
  Query: "latest price of organic soap?"
  Task: "availability_check"
  Constraints: {{"product": "soap", "material": "organic", "brand": [], "min_price": null, "max_price": null}}

Output:
{{"sources": ["private_rag", "web_search"], "retrieval_fields": ["title", "brand", "price", "in_stock"], "comparison_criteria": [], "filters": {{"category": "soap", "material": "organic"}}}}

Explanation: "latest" triggers web_search, material included in filters, empty brand omitted

Now create a plan for this query:
Query: {query}
Task: {task}
Constraints: {constraints}<|im_end|>
<|im_start|>assistant
"""

planner_prompt = PromptTemplate(
    input_variables=["query", "task", "constraints"],
    template=PLANNER_TEMPLATE
)