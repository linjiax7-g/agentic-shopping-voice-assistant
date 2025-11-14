# scripts/extract_metadata.py
"""
One-time script to extract structured metadata using LLM
Run this once to enrich your dataset before indexing

Output need to have at least these information:
- Uniq Id
- Product Name
- Selling Price
- Product Category
- Product Brand
- Product Material
- Product Description
- Product Review Score
"""

import sys
from pathlib import Path

# Add parent directory to path before importing local modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from datasets import load_dataset
from graph.models.llm import get_llm
from langchain_core.prompts import PromptTemplate
import json
import re
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Extraction prompt
EXTRACTION_TEMPLATE = """<|im_start|>system
You extract structured product metadata from text. Return ONLY valid JSON.<|im_end|>
<|im_start|>user
Extract metadata from this product listing. Return a JSON object with:
{{
  "category": string (e.g., "cleaner", "shampoo", "kettle", "shoes"),
  "brand": string or null (e.g., "Nike", "Dove"),
  "material": string or null (e.g., "organic", "stainless steel", "leather", "vegan")
}}

Rules:
- category: general product type (lowercase, singular)
- brand: company name if clearly stated
- material: key material/attribute if mentioned
- Use null if not found
- Return ONLY JSON, no explanation

Product Name: {product_name}
About: {about_product}
Specs: {product_spec}
<|im_end|>
<|im_start|>assistant
"""

extraction_prompt = PromptTemplate(
    input_variables=["product_name", "about_product", "product_spec"],
    template=EXTRACTION_TEMPLATE
)


def extract_json_from_llm(text: str) -> dict:
    """Extract JSON from LLM output"""
    text = text.strip()
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    
    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            json_str = json_str.replace("'", '"')
            json_str = re.sub(r',\s*}', '}', json_str)
            try:
                return json.loads(json_str)
            except:
                pass
    
    try:
        return json.loads(text)
    except:
        return {"category": None, "brand": None, "material": None}


def extract_metadata_batch(df: pd.DataFrame, batch_size: int = 50) -> pd.DataFrame:
    """
    Extract metadata for all products using LLM
    
    Args:
        df: DataFrame with product data
        batch_size: Process in batches to show progress
    
    Returns:
        DataFrame with added columns: category, brand, material
    """
    llm = get_llm()
    
    # Initialize result columns
    df['category'] = None
    df['brand'] = None
    df['material'] = None
    
    # Create chain
    chain = extraction_prompt | llm
    
    logger.info(f"Extracting metadata for {len(df)} products...")
    
    # Process in batches with progress bar
    for i in tqdm(range(0, len(df), batch_size), desc="Extracting metadata"):
        batch = df.iloc[i:i+batch_size]
        
        for idx, row in batch.iterrows():
            try:
                # Prepare input
                input_data = {
                    "product_name": str(row.get("Product Name", ""))[:200],
                    "about_product": str(row.get("About Product", ""))[:300],
                    "product_spec": str(row.get("Product Specification", ""))[:300]
                }
                
                # Call LLM
                result = chain.invoke(input_data)
                
                # Parse response
                metadata = extract_json_from_llm(result)
                
                # Update dataframe
                df.at[idx, 'category'] = metadata.get('category')
                df.at[idx, 'brand'] = metadata.get('brand')
                df.at[idx, 'material'] = metadata.get('material')
                
            except Exception as e:
                logger.warning(f"Failed to extract metadata for row {idx}: {e}")
                continue
    
    logger.info("Metadata extraction complete!")
    
    # Show statistics
    logger.info(f"Categories found: {df['category'].notna().sum()}")
    logger.info(f"Brands found: {df['brand'].notna().sum()}")
    logger.info(f"Materials found: {df['material'].notna().sum()}")
    
    return df


def main():
    """Main execution"""
    
    # Load data
    logger.info("Loading Amazon dataset...")
    df = load_dataset("calmgoose/amazon-product-data-2020", split="train")
    df = df.to_pandas()
    
    # Optional: Process subset for testing
    df = df.head(50)  # Uncomment to test on 50 products first
    
    # Extract metadata
    df_enriched = extract_metadata_batch(df)
    
    # Save enriched dataset
    output_path = Path("data/amazon_enriched.parquet")
    output_path.parent.mkdir(exist_ok=True)
    df_enriched.to_parquet(output_path, index=False)
    
    logger.info(f"Enriched dataset saved to {output_path}")
    
    # Show sample
    logger.info("\nSample of enriched data:")
    sample_cols = ["Product Name", "category", "brand", "material", "Selling Price"]
    print(df_enriched[sample_cols].head(10))


if __name__ == "__main__":
    main()