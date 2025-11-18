# LangGraph Integration Guide

## Overview
This document explains how to integrate with the **Agentic Orchestration Pipeline** built with LangGraph.

**What This Pipeline Does:**
- Takes a text query as input
- Routes it through 4 agents: Router → Planner → Retriever → Answerer
- Returns a structured answer with citations

**Your Team's Responsibilities:**
1. **Private RAG Team**: Improve retrieval quality and metadata
2. **Web Search Team**: Add live price/availability checking via MCP
3. **Voice Team**: Add ASR (speech-to-text) and TTS (text-to-speech)
4. **UI Team**: Build Streamlit interface to tie everything together

---

## Quick Start

```python
from graph.graph import create_graph

# Initialize the graph once
graph = create_graph()

# Run a query
result = graph.invoke({
    "query": "organic shampoo under $20",
    "step_log": []
})

# Access the output
print(result["answer"])        # Final answer text
print(result["citations"])     # List of cited sources
print(result["retrieved_docs"])  # Full retrieved documents
```

---

## Input Schema

### Required Input
```python
{
    "query": str,           # User's natural language query
    "step_log": []          # Always pass empty list []
}
```

### Example Inputs
```python
# Basic product search
{"query": "organic shampoo under $20", "step_log": []}

# Comparison
{"query": "compare Nike vs Adidas shoes", "step_log": []}

# Recommendation
{"query": "recommend the best stainless steel cleaner", "step_log": []}

# Availability check (triggers web search if implemented)
{"query": "is organic shampoo available now?", "step_log": []}
```

---

## Output Schema

### Complete Output Structure
```python
{
    # Final outputs (what users see)
    "answer": str,              # Natural language answer
    "citations": List[str],      # ["DOC 1", "DOC 2", ...]
    
    # Intermediate outputs (for debugging/UI)
    "task": str,                 # "product_search" | "comparison" | "recommendation" | "availability_check"
    "constraints": dict,         # Extracted filters
    "plan": dict,                # Retrieval plan
    "retrieved_docs": List[dict],  # Retrieved products
    
    # Execution log
    "step_log": List[dict],      # Logs from each node
    
    # Safety
    "safety_flags": List[str]    # ["medical_advice", ...]
}
```

### Example Output
```python
{
    "answer": "I found 3 organic shampoos under $20. The best option is Brand X...",
    "citations": ["DOC 1", "DOC 2"],
    "task": "product_search",
    "constraints": {
        "product": "shampoo",
        "max_price": 20,
        "material": "organic",
        "brand": []
    },
    "plan": {
        "sources": ["private_rag"],
        "retrieval_fields": ["title", "brand", "price", "rating", "material"],
        "comparison_criteria": ["price", "rating"],
        "filters": {
            "category": "shampoo",
            "max_price": 20,
            "material": "organic"
        }
    },
    "retrieved_docs": [
        {
            "doc_id": "B07XYZ123",
            "title": "Brand X Organic Shampoo",
            "price": 14.99,
            "brand": "Brand X",
            "material": "organic",
            "category": "shampoo",
            "content": "Sulfate-free organic shampoo...",
            "score": 0.89
        },
        # ... more docs
    ],
    "safety_flags": [],
    "step_log": [
        {"node": "router", "success": True, ...},
        {"node": "planner", "success": True, ...},
        {"node": "retriever", "success": True, ...},
        {"node": "answerer", "success": True, ...}
    ]
}
```

---

## Integration Points by Team

### 1. Private RAG Team

**What You Need to Do:**
- Improve `graph/retriever/__init__.py`
- Enhance metadata extraction in `scripts/extract_metadata.py`
- Optimize vector search and filtering

**Interface Contract:**
```python
# Input (from Planner)
filters = {
    "category": "shampoo",
    "min_price": 10.0,
    "max_price": 20.0,
    "material": "organic",
    "brand": ["Dove", "Pantene"]  # Can be empty list
}

# Your function should accept these
def retrieve_products(
    query: str,              # Search query
    filters: Dict,           # Filters above
    retrieval_fields: List[str],  # Fields to retrieve
    k: int = 5              # Number of results
) -> List[Dict]:
    # Your implementation here
    pass

# Output format (MUST return this structure)
[
    {
        "doc_id": str,       # Unique product ID
        "title": str,        # Product name
        "price": float,      # Price as number
        "brand": str,        # Brand name (can be empty)
        "material": str,     # Material/attribute (can be empty)
        "category": str,     # Product category (can be empty)
        "content": str,      # Full text content
        "score": float       # Relevance score
    },
    # ... more docs
]
```

**Testing Your Changes:**
```bash
python tests/test_retriever.py
```

---

### 2. Web Search Team (MCP)

**What You Need to Do:**
- Create `graph/tools/web_search.py`
- Build MCP server with `web.search` tool
- Modify planner to conditionally call web search

**Interface Contract:**
```python
# Add this function to graph/tools/web_search.py
def web_search_products(
    query: str,
    filters: Dict
) -> List[Dict]:
    """
    Search live web for product info
    
    Returns same format as retrieve_products():
    [
        {
            "doc_id": str,      # URL or unique ID
            "title": str,
            "price": float,
            "brand": str,
            "material": str,
            "category": str,
            "content": str,
            "score": float,
            "source": "web",    # Add this to distinguish from private RAG
            "url": str          # Add source URL
        }
    ]
    """
    pass
```

**Integration with Retriever:**
Modify `graph/nodes.py` retriever_node:
```python
def retriever_node(state: GraphState) -> GraphState:
    plan = state["plan"]
    sources = plan.get("sources", ["private_rag"])
    
    docs = []
    
    # Private RAG
    if "private_rag" in sources:
        docs += retrieve_products(...)
    
    # Web search (YOUR CODE HERE)
    if "web_search" in sources:
        from graph.tools.web_search import web_search_products
        web_docs = web_search_products(...)
        docs += web_docs
    
    state["retrieved_docs"] = docs
    return state
```

**Testing:**
```python
# Test query that should trigger web search
result = graph.invoke({
    "query": "is organic shampoo available now?",
    "step_log": []
})

# Should have "web_search" in sources
assert "web_search" in result["plan"]["sources"]
```

---

### 3. Voice Team (ASR + TTS)

**What You Need to Do:**
- Add Whisper for speech-to-text
- Add OpenAI TTS / ElevenLabs for text-to-speech
- Create wrapper functions

**Interface Contract:**

**ASR (Speech-to-Text):**
```python
# Create: voice/asr.py
def transcribe_audio(audio_file_path: str) -> str:
    """
    Convert audio to text using Whisper
    
    Args:
        audio_file_path: Path to audio file (WAV/MP3)
    
    Returns:
        Transcribed text string
    """
    import whisper
    model = whisper.load_model("base")
    result = model.transcribe(audio_file_path)
    return result["text"]
```

**TTS (Text-to-Speech):**
```python
# Create: voice/tts.py
def synthesize_speech(text: str, output_path: str) -> str:
    """
    Convert text to speech
    
    Args:
        text: Answer text to speak
        output_path: Where to save audio file
    
    Returns:
        Path to generated audio file
    """
    from openai import OpenAI
    client = OpenAI()
    
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text
    )
    
    response.stream_to_file(output_path)
    return output_path
```

**Integration:**
```python
# voice/pipeline.py
from voice.asr import transcribe_audio
from voice.tts import synthesize_speech
from graph.graph import create_graph

def voice_to_voice_query(audio_input_path: str) -> dict:
    """Complete voice-to-voice pipeline"""
    
    # 1. Speech to text
    query = transcribe_audio(audio_input_path)
    
    # 2. Run graph
    graph = create_graph()
    result = graph.invoke({"query": query, "step_log": []})
    
    # 3. Text to speech
    audio_output_path = "output.mp3"
    synthesize_speech(result["answer"], audio_output_path)
    
    return {
        "query": query,
        "answer": result["answer"],
        "citations": result["citations"],
        "audio_path": audio_output_path
    }
```

**Testing:**
```bash
python voice/test_pipeline.py
```

---

### 4. UI Team (Streamlit)

**What You Need to Do:**
- Build Streamlit app
- Integrate voice pipeline
- Display results and citations

**Interface Contract:**

**Basic Integration:**
```python
# app.py
import streamlit as st
from graph.graph import create_graph

st.title("🛍️ AI Shopping Assistant")

# Text input
query = st.text_input("What are you looking for?")

if st.button("Search"):
    graph = create_graph()
    result = graph.invoke({"query": query, "step_log": []})
    
    # Display answer
    st.success(result["answer"])
    
    # Display citations
    st.caption(f"Sources: {', '.join(result['citations'])}")
    
    # Display retrieved products
    for doc in result["retrieved_docs"]:
        with st.expander(f"{doc['title']} - ${doc['price']:.2f}"):
            st.write(f"**Brand:** {doc['brand']}")
            st.write(f"**Material:** {doc['material']}")
            st.write(doc['content'][:200] + "...")
```

**With Voice:**
```python
# app.py with voice
import streamlit as st
from graph.graph import create_graph
from voice.asr import transcribe_audio
from voice.tts import synthesize_speech
import tempfile

st.title("🎤 Voice Shopping Assistant")

# Audio input
audio_file = st.file_uploader("Upload audio or record", type=["wav", "mp3"])

if audio_file and st.button("Process"):
    # Save uploaded audio
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_file.read())
        tmp_path = tmp.name
    
    # Transcribe
    query = transcribe_audio(tmp_path)
    st.info(f"You said: {query}")
    
    # Run graph
    graph = create_graph()
    result = graph.invoke({"query": query, "step_log": []})
    
    # Display answer
    st.success(result["answer"])
    
    # Generate speech
    output_audio = synthesize_speech(result["answer"], "response.mp3")
    st.audio(output_audio)
    
    # Show products
    for doc in result["retrieved_docs"][:3]:
        st.write(f"**{doc['title']}** - ${doc['price']:.2f}")
```

**Run the app:**
```bash
streamlit run app.py
```

---

## Testing the Full Integration

### Test Script for All Teams
```python
# test_integration.py
from graph.graph import create_graph

def test_full_pipeline():
    """Test complete pipeline"""
    
    graph = create_graph()
    
    queries = [
        "organic shampoo under $20",
        "compare Nike vs Adidas shoes",
        "is stainless steel cleaner available now?"
    ]
    
    for query in queries:
        print(f"\nTesting: {query}")
        result = graph.invoke({"query": query, "step_log": []})
        
        # Verify output
        assert result["answer"], "No answer generated"
        assert result["citations"], "No citations"
        assert result["retrieved_docs"], "No docs retrieved"
        
        print(f"✓ Answer: {result['answer'][:100]}...")
        print(f"✓ Citations: {result['citations']}")
        print(f"✓ Retrieved: {len(result['retrieved_docs'])} docs")

if __name__ == "__main__":
    test_full_pipeline()
```

---

## Common Issues & Solutions

### Issue 1: Graph takes too long
**Solution:** The LLM is slow on CPU. Consider:
- Using GPU if available
- Switching to API-based LLM (OpenAI, Anthropic)
- Reducing `max_new_tokens` in `graph/models/llm.py`

### Issue 2: No results from retriever
**Solution:** Check if:
- Vector DB is indexed: `ls chroma_db/`
- Filters are too strict
- Metadata extraction worked: check `data/amazon_enriched.parquet`

### Issue 3: Citations missing
**Solution:** Parser might be failing. Check:
- LLM is outputting `[DOC X]` format
- Parser regex in `graph/answerer/parser.py`

### Issue 4: step_log accumulating duplicates
**Solution:** Always pass fresh `step_log: []` in each invoke:
```python
result = graph.invoke({"query": query, "step_log": []})
```

---

## File Structure Reference

```
project/
├── graph/                      # CORE PIPELINE (Your work)
│   ├── router/                 # Intent extraction
│   ├── planner/                # Retrieval planning
│   ├── retriever/              # RAG Team modifies this
│   ├── answerer/               # Answer generation
│   ├── tools/                  # Web Search Team adds this
│   ├── models/                 # LLM management
│   ├── nodes.py                # Node implementations
│   ├── state.py                # State schema
│   └── graph.py                # Graph definition
│
├── voice/                      # Voice Team creates this
│   ├── asr.py                  # Speech-to-text
│   ├── tts.py                  # Text-to-speech
│   └── pipeline.py             # Voice pipeline
│
├── ui/                         # UI Team creates this
│   └── app.py                  # Streamlit app
│
├── scripts/                    # Data processing
│   └── extract_metadata.py    # RAG Team improves this
│
├── data/                       # Data storage
│   └── amazon_enriched.parquet
│
├── chroma_db/                  # Vector database
│
└── tests/                      # Test files
    ├── test_router.py
    ├── test_planner.py
    ├── test_retriever.py
    └── test_answerer.py
```

---

## Getting Help

**Questions about:**
- Graph structure, state, nodes → Contact orchestration team (you)
- Retrieval, metadata, indexing → Contact RAG team
- Web search, MCP, live data → Contact web search team
- ASR, TTS, voice pipeline → Contact voice team
- UI, Streamlit, user experience → Contact UI team

**Resources:**
- LangGraph docs: https://langchain-ai.github.io/langgraph/
- Current tests: `tests/test_*.py`
- Example usage: `demo.py`
