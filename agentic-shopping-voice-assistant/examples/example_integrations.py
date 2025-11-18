"""
Integration Examples for Each Team
Run specific examples: python examples/integration_examples.py [rag|web|voice|ui]
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# EXAMPLE 1: Private RAG Team
# ============================================================================
def example_rag_integration():
    """
    Example showing how RAG team should integrate their improved retriever
    """
    print("\n" + "="*70)
    print("EXAMPLE 1: Private RAG Integration")
    print("="*70)
    
    from graph.graph import create_graph
    
    # Your improved retrieval function should work the same way
    graph = create_graph()
    
    result = graph.invoke({
        "query": "organic shampoo under $20",
        "step_log": []
    })
    
    # Show what the retriever returned
    print("\nRetriever returned:")
    for i, doc in enumerate(result["retrieved_docs"][:3], 1):
        print(f"\n[{i}] {doc['title']}")
        print(f"    Price: ${doc['price']:.2f}")
        print(f"    Brand: {doc.get('brand', 'N/A')}")
        print(f"    Material: {doc.get('material', 'N/A')}")
        print(f"    Score: {doc['score']:.3f}")
    
    print("\n✓ RAG integration test passed!")
    print("\nTo improve retrieval, modify:")
    print("  - graph/retriever/__init__.py (retrieval logic)")
    print("  - scripts/extract_metadata.py (metadata extraction)")


# ============================================================================
# EXAMPLE 2: Web Search Team
# ============================================================================
def example_web_search_integration():
    """
    Example showing how web search team should integrate MCP
    """
    print("\n" + "="*70)
    print("EXAMPLE 2: Web Search Integration")
    print("="*70)
    
    # Mock implementation (your team will implement real version)
    def mock_web_search(query: str, filters: dict):
        """This is what your web_search function should look like"""
        return [
            {
                "doc_id": "https://example.com/product1",
                "title": "Example Product from Web",
                "price": 15.99,
                "brand": "WebBrand",
                "material": "organic",
                "category": "shampoo",
                "content": "Found via web search API...",
                "score": 0.95,
                "source": "web",  # Important: mark as web source
                "url": "https://example.com/product1"
            }
        ]
    
    print("\nYour web search function should:")
    print("1. Accept query and filters (same as retriever)")
    print("2. Call web search API (Brave/Serper/Bing)")
    print("3. Return same format as private retriever")
    print("4. Add 'source': 'web' and 'url' fields")
    
    # Show how to integrate
    print("\nIntegration point in graph/nodes.py:")
    print("""
    def retriever_node(state: GraphState) -> GraphState:
        plan = state["plan"]
        sources = plan.get("sources", ["private_rag"])
        
        docs = []
        
        # Private RAG
        if "private_rag" in sources:
            docs += retrieve_products(...)
        
        # YOUR CODE HERE
        if "web_search" in sources:
            from graph.tools.web_search import web_search_products
            web_docs = web_search_products(
                query=state["query"],
                filters=plan["filters"]
            )
            docs += web_docs
        
        state["retrieved_docs"] = docs
        return state
    """)
    
    print("\n✓ See INTEGRATION_GUIDE.md section 2 for full details")


# ============================================================================
# EXAMPLE 3: Voice Team
# ============================================================================
def example_voice_integration():
    """
    Example showing how voice team should integrate ASR + TTS
    """
    print("\n" + "="*70)
    print("EXAMPLE 3: Voice Integration")
    print("="*70)
    
    # Mock implementations
    def mock_transcribe(audio_path: str) -> str:
        """Mock ASR - your team will use Whisper"""
        return "organic shampoo under $20"
    
    def mock_synthesize(text: str, output_path: str) -> str:
        """Mock TTS - your team will use OpenAI TTS"""
        print(f"  [TTS] Would save audio to: {output_path}")
        return output_path
    
    print("\n1. Create voice/asr.py:")
    print("""
    import whisper
    
    def transcribe_audio(audio_file_path: str) -> str:
        model = whisper.load_model("base")
        result = model.transcribe(audio_file_path)
        return result["text"]
    """)
    
    print("\n2. Create voice/tts.py:")
    print("""
    from openai import OpenAI
    
    def synthesize_speech(text: str, output_path: str) -> str:
        client = OpenAI()
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text
        )
        response.stream_to_file(output_path)
        return output_path
    """)
    
    print("\n3. Create voice/pipeline.py:")
    print("""
    from voice.asr import transcribe_audio
    from voice.tts import synthesize_speech
    from graph.graph import create_graph
    
    def voice_to_voice_query(audio_input_path: str):
        # ASR
        query = transcribe_audio(audio_input_path)
        
        # Graph
        graph = create_graph()
        result = graph.invoke({"query": query, "step_log": []})
        
        # TTS
        audio_path = synthesize_speech(result["answer"], "output.mp3")
        
        return {
            "query": query,
            "answer": result["answer"],
            "audio_path": audio_path
        }
    """)
    
    # Demo the flow
    print("\n--- Demo Flow ---")
    from graph.graph import create_graph
    
    print("\n[ASR] Transcribing audio...")
    query = mock_transcribe("user_audio.wav")
    print(f"  Transcribed: '{query}'")
    
    print("\n[Graph] Processing query...")
    graph = create_graph()
    result = graph.invoke({"query": query, "step_log": []})
    print(f"  Answer: {result['answer'][:100]}...")
    
    print("\n[TTS] Synthesizing speech...")
    audio_path = mock_synthesize(result["answer"], "response.mp3")
    
    print("\n✓ Voice integration complete!")


# ============================================================================
# EXAMPLE 4: UI Team
# ============================================================================
def example_ui_integration():
    """
    Example showing how UI team should integrate Streamlit
    """
    print("\n" + "="*70)
    print("EXAMPLE 4: UI Integration (Streamlit)")
    print("="*70)
    
    print("\nBasic Streamlit App (app.py):")
    print("""
import streamlit as st
from graph.graph import create_graph

st.title("🛍️ AI Shopping Assistant")

# Initialize graph (singleton)
if 'graph' not in st.session_state:
    st.session_state.graph = create_graph()

# Text input
query = st.text_input("What are you looking for?", 
                      placeholder="e.g., organic shampoo under $20")

if st.button("Search") and query:
    with st.spinner("Searching..."):
        result = st.session_state.graph.invoke({
            "query": query,
            "step_log": []
        })
    
    # Display answer
    st.success(result["answer"])
    
    # Display citations
    st.caption(f"📚 Sources: {', '.join(result['citations'])}")
    
    # Display products
    st.subheader("Products Found")
    for doc in result["retrieved_docs"]:
        with st.expander(f"{doc['title']} - ${doc['price']:.2f}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Brand:** {doc['brand']}")
                st.write(f"**Material:** {doc['material']}")
            with col2:
                st.write(f"**Category:** {doc['category']}")
                st.write(f"**Score:** {doc['score']:.3f}")
            st.write(doc['content'][:200] + "...")
    """)
    
    print("\n\nWith Voice Support:")
    print("""
import streamlit as st
from graph.graph import create_graph
from voice.asr import transcribe_audio
from voice.tts import synthesize_speech
import tempfile

st.title("🎤 Voice Shopping Assistant")

# Audio input
audio_file = st.file_uploader("Record or upload audio", 
                               type=["wav", "mp3"])

if audio_file and st.button("Process Voice"):
    # Save audio
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(audio_file.read())
        audio_path = tmp.name
    
    # Transcribe
    with st.spinner("Transcribing..."):
        query = transcribe_audio(audio_path)
    st.info(f"You said: {query}")
    
    # Process
    with st.spinner("Searching..."):
        graph = create_graph()
        result = graph.invoke({"query": query, "step_log": []})
    
    # Display answer
    st.success(result["answer"])
    
    # TTS
    with st.spinner("Generating speech..."):
        response_audio = synthesize_speech(result["answer"], "response.mp3")
    st.audio(response_audio)
    
    # Show products...
    """)
    
    print("\n\nRun your app:")
    print("  streamlit run app.py")
    
    print("\n✓ UI integration examples complete!")


# ============================================================================
# Main
# ============================================================================
def main():
    examples = {
        "rag": example_rag_integration,
        "web": example_web_search_integration,
        "voice": example_voice_integration,
        "ui": example_ui_integration
    }
    
    if len(sys.argv) > 1 and sys.argv[1] in examples:
        examples[sys.argv[1]]()
    else:
        print("\nRunning all integration examples...\n")
        for name, func in examples.items():
            func()
            print("\n" + "-"*70 + "\n")
        
        print("\n" + "="*70)
        print("All integration examples complete!")
        print("="*70)
        print("\nNext steps:")
        print("  1. Read INTEGRATION_GUIDE.md")
        print("  2. Each team modifies their section")
        print("  3. Test with: python test_integration.py")
        print("  4. Final demo: streamlit run app.py")


if __name__ == "__main__":
    main()
