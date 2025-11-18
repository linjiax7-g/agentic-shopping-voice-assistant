# graph/router/model.py
from langchain_huggingface import HuggingFacePipeline
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, BitsAndBytesConfig
import torch
import gc
import logging
logger = logging.getLogger(__name__)

# Global instance
_llm = None

def load_llm_qwen_model():
    """Load Qwen Model"""
    
    # model_id = "Qwen/Qwen3-4B-Instruct-2507"
    model_id = "Qwen/Qwen2.5-1.5B-Instruct"
    
    # Use MPS on M4 Pro - much faster than CPU
    # Use float32 for MPS to avoid NaN/inf in sampling operations!!!!!!!!
    # This is a known issue: MPS on Apple Silicon has incomplete float16 support.
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    dtype = torch.float32  # Must use float32 to avoid NaN/inf

    logger.info(f"Loading model {model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    
    try:
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            trust_remote_code=True,
            dtype=dtype,
            low_cpu_mem_usage=True,
        )
        model = model.to(device)
    except Exception as e:
        logger.error(f"Model loading failed: {e}")
        raise
    
    try:
        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=128,  # Reduced for faster generation
            temperature=0.1,
            do_sample=True,
            return_full_text=False,
            pad_token_id=tokenizer.eos_token_id
        )
    except Exception as e:
        logger.error(f"Pipeline creation failed: {e}")
        raise
    
    llm = HuggingFacePipeline(pipeline=pipe)
    logger.info("Model loaded successfully")
    
    return llm

def get_llm():
    """
    Get the LLM instance (lazy loading singleton).
    Same model is reused across all nodes.
    
    Args:
        model_id: HuggingFace model identifier (only used on first call)
    
    Returns:
        HuggingFacePipeline instance
    """
    global _llm
    
    if _llm is None:
        _llm = load_llm_qwen_model()
    
    return _llm

def reset_llm():
    """Reset the LLM instance (useful for testing or switching models)."""
    global _llm
    _llm = None
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()