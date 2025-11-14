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
    """Load Qwen3-4B-Instruct (July 2025 release)."""
    
    model_id = "Qwen/Qwen3-4B-Instruct-2507"
    device = "mps" if torch.backends.mps.is_available() else "cpu"

    logger.info(f"Loading model {model_id}...")
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    
    try:
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            trust_remote_code=True,
            dtype=torch.float16,
            low_cpu_mem_usage=True
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
            max_new_tokens=512,
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