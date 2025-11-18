# Project Handoff: Agentic Orchestration Pipeline

## 🎯 What's Complete

✅ **Core LangGraph Pipeline** (Router → Planner → Retriever → Answerer)  
✅ **Router** - Intent classification & constraint extraction  
✅ **Planner** - Retrieval strategy planning  
✅ **Retriever** - Vector search with metadata filtering  
✅ **Answerer** - Answer generation with citations  
✅ **Tests** - Comprehensive test suite  
✅ **Documentation** - Integration guide & examples

## 📋 What Each Team Needs to Do

### 1. Private RAG Team 🗄️
**Goal:** Improve retrieval quality and metadata

**Files to modify:**
- `graph/retriever/__init__.py` - Optimize search & filtering
- `scripts/extract_metadata.py` - Better metadata extraction

**Read:**
- `INTEGRATION_GUIDE.md` - Section 1
- `examples/integration_examples.py rag`

**Test:**
```bash
python tests/test_retriever.py
```

---

### 2. Web Search Team 🌐
**Goal:** Add live price/availability via MCP

**Files to create:**
- `graph/tools/web_search.py` - Web search function
- `mcp_server/` - MCP server implementation

**Files to modify:**
- `graph/nodes.py` - Add web search to retriever_node

**Read:**
- `INTEGRATION_GUIDE.md` - Section 2
- `examples/integration_examples.py web`

**Test:**
```bash
# Query with "now" should trigger web search
python -c "
from graph.graph import create_graph
result = create_graph().invoke({'query': 'is shampoo available now?', 'step_log': []})
assert 'web_search' in result['plan']['sources']
print('✓ Web search triggered')
"
```

---

### 3. Voice Team 🎤
**Goal:** Add ASR (Whisper) and TTS (OpenAI)

**Files to create:**
- `voice/asr.py` - Speech-to-text
- `voice/tts.py` - Text-to-speech
- `voice/pipeline.py` - Complete voice pipeline

**Read:**
- `INTEGRATION_GUIDE.md` - Section 3
- `examples/integration_examples.py voice`

**Test:**
```bash
python voice/test_pipeline.py
```

---

### 4. UI Team 🖥️
**Goal:** Build Streamlit interface

**Files to create:**
- `app.py` - Main Streamlit app
- `ui/components.py` - Reusable UI components (optional)

**Read:**
- `INTEGRATION_GUIDE.md` - Section 4
- `examples/integration_examples.py ui`

**Run:**
```bash
streamlit run app.py
```

---

## 🚀 Quick Start for All Teams

### 1. Setup Environment
```bash
# Clone the repo
git clone <repo-url>
cd project

# Install dependencies
pip install -r requirements.txt

# Verify setup
python tests/test_router.py
python tests/test_planner.py
python tests/test_retriever.py
python tests/test_answerer.py
```

### 2. Understand the Pipeline
```bash
# See how it all works
python demo.py

# See integration examples for your team
python examples/integration_examples.py [rag|web|voice|ui]
```

### 3. Read Your Documentation
```bash
# Open the integration guide
cat INTEGRATION_GUIDE.md | less

# Search for your team's section
grep -A 50 "Private RAG Team" INTEGRATION_GUIDE.md
```

---

## 📝 How to Use the Graph

### Basic Usage
```python
from graph.graph import create_graph

# Create graph once
graph = create_graph()

# Run a query
result = graph.invoke({
    "query": "organic shampoo under $20",
    "step_log": []
})

# Access outputs
print(result["answer"])       # Final answer
print(result["citations"])    # Sources cited
print(result["retrieved_docs"])  # All products found
```

### Input Format
```python
{
    "query": str,      # User's natural language query
    "step_log": []     # Always pass empty list
}
```

### Output Format
```python
{
    "answer": str,              # Final answer (what user sees)
    "citations": List[str],     # ["DOC 1", "DOC 2", ...]
    "retrieved_docs": List[dict],  # All retrieved products
    "task": str,                # "product_search" | "comparison" | ...
    "constraints": dict,        # Extracted filters
    "plan": dict,               # Retrieval strategy
    "safety_flags": List[str],  # Safety warnings
    "step_log": List[dict]      # Execution log
}
```

---

## 🧪 Testing Your Changes

### Run All Tests
```bash
# Test your changes don't break existing functionality
python -m pytest tests/ -v
```

### Test Specific Component
```bash
# Router
python tests/test_router.py

# Planner
python tests/test_planner.py

# Retriever (RAG team)
python tests/test_retriever.py

# Answerer
python tests/test_answerer.py
```

### Test Complete Pipeline
```python
# test_your_integration.py
from graph.graph import create_graph

def test_integration():
    graph = create_graph()
    
    result = graph.invoke({
        "query": "organic shampoo under $20",
        "step_log": []
    })
    
    # Verify all nodes succeeded
    for log in result["step_log"]:
        assert log.get("success"), f"{log['node']} failed!"
    
    # Verify output
    assert result["answer"]
    assert result["citations"]
    assert result["retrieved_docs"]
    
    print("✓ Integration test passed!")

test_integration()
```

---

## 📁 File Structure

```
project/
├── INTEGRATION_GUIDE.md        ← 📖 READ THIS FIRST
├── HANDOFF_README.md            ← 📖 You are here
├── examples/
│   └── integration_examples.py  ← 💡 Code examples for each team
│
├── graph/                       ← ✅ COMPLETE (don't modify unless needed)
│   ├── router/                  
│   ├── planner/                 
│   ├── retriever/               ← 🗄️ RAG team modifies
│   ├── answerer/                
│   ├── tools/                   ← 🌐 Web team creates
│   ├── models/                  
│   ├── nodes.py                 ← 🌐 Web team modifies
│   ├── state.py                 
│   └── graph.py                 
│
├── voice/                       ← 🎤 Voice team creates
│   ├── asr.py                   
│   ├── tts.py                   
│   └── pipeline.py              
│
├── ui/                          ← 🖥️ UI team creates
│   └── app.py                   
│
├── scripts/
│   └── extract_metadata.py      ← 🗄️ RAG team improves
│
├── tests/                       ← ✅ COMPLETE (add more as needed)
│   ├── test_router.py
│   ├── test_planner.py
│   ├── test_retriever.py
│   └── test_answerer.py
│
└── demo.py                      ← 💡 See it in action
```

---

## 🐛 Common Issues

### "Graph is slow"
**Cause:** LLM running on CPU  
**Solution:** Use GPU or switch to API-based LLM (OpenAI/Anthropic)

### "No products found"
**Cause:** Vector DB not indexed or filters too strict  
**Solution:** Check `chroma_db/` exists, verify metadata in `data/amazon_enriched.parquet`

### "Duplicate logs in step_log"
**Cause:** Not passing fresh `step_log: []`  
**Solution:** Always use `graph.invoke({"query": q, "step_log": []})`

### "Import errors"
**Cause:** Missing dependencies  
**Solution:** `pip install -r requirements.txt`

---

## 📞 Who to Ask

- **Graph structure, state, orchestration** → Original developer (you)
- **Retrieval, metadata, indexing** → RAG team
- **Web search, MCP, live data** → Web search team
- **ASR, TTS, voice pipeline** → Voice team
- **UI, Streamlit, user experience** → UI team

---

## ✅ Final Checklist

Before considering your integration complete:

- [ ] Read `INTEGRATION_GUIDE.md` section for your team
- [ ] Run `python examples/integration_examples.py [your-team]`
- [ ] Implement your component
- [ ] Write tests for your component
- [ ] Run `pytest tests/ -v` - all tests pass
- [ ] Test integration with `demo.py`
- [ ] Update this README with any new requirements
- [ ] Document any new dependencies in `requirements.txt`

---

## 🎉 Final Integration

Once all teams complete their work:

```bash
# 1. Test everything
pytest tests/ -v

# 2. Run demo
python demo.py

# 3. Launch UI
streamlit run app.py

# 4. Test voice-to-voice
# Record audio → Upload → Get spoken answer with citations
```

**Expected Demo Flow:**
1. User speaks: "I need organic shampoo under $20"
2. ASR transcribes to text
3. Graph processes: Router → Planner → Retriever (private + web) → Answerer
4. TTS speaks answer: "I found 3 options. Brand X at $14.99..."
5. UI shows products, prices, citations

Good luck! 🚀
