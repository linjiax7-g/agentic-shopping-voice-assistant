# Agentic Voice-to-Voice AI Assistant for Product Discovery

A multi-agent voice assistant for e-commerce product discovery using LangGraph, MCP tools, and RAG.

## Project Structure

```project/
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

## Voice Pipeline (ASR + TTS)

- `voice/asr.py` wraps Whisper (via `faster-whisper`) for high-quality speech-to-text.
- `voice/tts.py` streams ElevenLabs TTS responses and returns base64 MP3 payloads.
- `voice/pipeline.py` now exposes helpers to bootstrap the ASR/TTS stack and run the LangGraph workflow end-to-end from an audio file.

### Environment

Create a `.env` file (or export vars) with at least:

```
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
WHISPER_LANGUAGE=en
ELEVENLABS_API_KEY=your_elevenlabs_key
# Optional overrides:
# ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
# ELEVENLABS_MODEL=eleven_turbo_v2_5
```

### Voice-to-Voice Test

1. Install deps from `requirements.txt` (ensures `faster-whisper`, `ffmpeg-python`, `aiohttp`, etc.).
2. Provide an audio file (wav/mp3/webm) with a spoken shopping query.
3. Run:

```
python voice/test_pipeline.py path/to/audio.wav --output response.mp3
```

The script will:

- Transcribe the audio via Whisper (`voice.transcribe_audio_file`)
- Invoke the LangGraph workflow to get the product answer
- Synthesize the final response to `response.mp3`

You can also import the helpers directly:

```python
from voice import load_default_voice_pipeline, voice_to_voice_query

pipeline = load_default_voice_pipeline()
result = await voice_to_voice_query("sample.wav", pipeline=pipeline)
print(result["graph_result"]["answer"])
```