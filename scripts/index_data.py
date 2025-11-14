"""
Data indexing script for Amazon Product Dataset 2020
Uses pre-extracted metadata from extract_metadata.py
"""

import pandas as pd
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma


def load_enriched_data():
    """Load enriched dataset with metadata"""
    data_path = Path("data/amazon_enriched.parquet")
    
    if not data_path.exists():
        raise FileNotFoundError(
            "Enriched data not found. Run 'python scripts/extract_metadata.py' first!"
        )
    
    df = pd.read_parquet(data_path)
    return df


def index_products(df: pd.DataFrame = None, persist_directory: str = "./chroma_db"):
    """
    Index products into vector database with rich metadata
    """
    if df is None:
        df = load_enriched_data()
    
    # Select columns for embedding
    useful_columns = ["Product Name", "About Product", "Product Specification"]
    df_embed = df[['Uniq Id'] + useful_columns + ['Selling Price', 'category', 'brand', 'material']].copy()
    df_embed = df_embed.fillna("")
    
    # Create embedding text
    df_embed['embed_text'] = df_embed.apply(
        lambda x: f"Product Name: {x['Product Name']}. "
                  f"About Product: {x['About Product']}. "
                  f"Product Specification: {x['Product Specification']}",
        axis=1
    )
    
    # Prepare metadata with all filters
    metadatas = []
    for _, row in df_embed.iterrows():
        metadata = {
            "Uniq Id": row["Uniq Id"],
            "Product Name": row["Product Name"],
            "Selling Price": row["Selling Price"],
            "category": row["category"] if pd.notna(row["category"]) else "",
            "brand": row["brand"] if pd.notna(row["brand"]) else "",
            "material": row["material"] if pd.notna(row["material"]) else "",
        }
        metadatas.append(metadata)
    
    # Generate embeddings
    print(f"Creating embeddings for {len(df_embed)} products...")
    embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # Initialize Chroma vector store
    vector_store = Chroma.from_texts(
        texts=df_embed['embed_text'].tolist(),
        metadatas=metadatas,
        embedding=embedder,
        persist_directory=persist_directory
    )
    
    print(f"✓ Indexed {len(df_embed)} products to {persist_directory}")
    
    return vector_store


if __name__ == "__main__":
    df = load_enriched_data()
    print(f"Loaded {len(df)} enriched products")
    
    # Show metadata stats
    print(f"\nMetadata coverage:")
    print(f"  Categories: {df['category'].notna().sum()}/{len(df)}")
    print(f"  Brands: {df['brand'].notna().sum()}/{len(df)}")
    print(f"  Materials: {df['material'].notna().sum()}/{len(df)}")
    
    persist_dir = "./chroma_db"
    vector_store = index_products(df, persist_directory=persist_dir)
    print(f"\n✓ Vector store ready at {persist_dir}")