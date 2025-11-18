"""FastAPI Backend for Voice Assistant

Provides WebSocket endpoint for real-time ASR streaming
and REST endpoints for TTS synthesis and voice management.
"""

import os
import base64
import asyncio
from typing import Optional, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from loguru import logger
import sys
from dotenv import load_dotenv

# Add repository paths so that backend uses the LangGraph voice package
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANGGRAPH_DIR = os.path.join(ROOT_DIR, "agentic-shopping-voice-assistant")

def _ensure_path(path: str, *, priority: bool = False, label: str = ""):
    if os.path.isdir(path):
        if path in sys.path:
            sys.path.remove(path)
        if priority:
            sys.path.insert(0, path)
        else:
            sys.path.append(path)
        if label:
            logger.info(f"Added {label} to PYTHONPATH: {path}")
    else:
        logger.warning(f"Expected path missing ({label or path}); please verify repository checkout.")

# Always prioritize the LangGraph repo so `import voice` resolves there
_ensure_path(LANGGRAPH_DIR, priority=True, label="LangGraph repo")
# Keep monorepo root at the end for other shared modules
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# Load environment variables from .env file in parent directory
env_path = os.path.join(ROOT_DIR, '.env')
load_dotenv(dotenv_path=env_path)

try:
    from graph.graph import create_graph  # type: ignore
except ModuleNotFoundError:
    create_graph = None  # type: ignore
    logger.warning("LangGraph repository not found. Agent responses will be unavailable.")

from voice.pipeline import VoicePipeline

# Initialize FastAPI app
app = FastAPI(
    title="Voice Assistant API",
    description="Real-time voice assistant with ASR and TTS",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services containers
pipeline = VoicePipeline()
graph_app = None  # Lazy-initialized LangGraph workflow

# Configuration from environment variables
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# Initialize services on startup
@app.on_event("startup")
async def startup_event():
    """Initialize ASR and TTS services on startup."""
    logger.info("Initializing voice services...")
    
    # Initialize ASR
    try:
        pipeline.initialize_asr(
            model=WHISPER_MODEL,
            device=WHISPER_DEVICE,
            language="en"
        )
        logger.info("ASR service ready")
    except Exception as e:
        logger.error(f"Failed to initialize ASR: {e}")
    
    # Initialize TTS
    if ELEVENLABS_API_KEY:
        try:
            pipeline.initialize_tts(
                api_key=ELEVENLABS_API_KEY
            )
            logger.info("TTS service ready")
        except Exception as e:
            logger.error(f"Failed to initialize TTS: {e}")
    else:
        logger.warning("ELEVENLABS_API_KEY not set, TTS will not be available")

    # Initialize LangGraph workflow
    global graph_app
    if create_graph is None:
        logger.warning("Skipping LangGraph initialization (missing dependency)")
        return

    try:
        graph_app = create_graph()
        logger.info("LangGraph workflow initialized")
    except Exception as e:
        graph_app = None
        logger.error(f"Failed to initialize LangGraph workflow: {e}", exc_info=True)


# Pydantic models for API
class TTSRequest(BaseModel):
    """Request model for TTS synthesis."""
    text: str
    voice_id: Optional[str] = None
    language: Optional[str] = "en"
    stability: Optional[float] = None
    similarity_boost: Optional[float] = None


class TTSResponse(BaseModel):
    """Response model for TTS synthesis."""
    audio_base64: str
    duration: float
    format: str
    sample_rate: int


class VoiceInfo(BaseModel):
    """Model for voice information."""
    id: str
    name: str
    language: str
    gender: Optional[str] = ""
    accent: Optional[str] = ""


class AgentRequest(BaseModel):
    """Request body for LangGraph agent queries."""
    text: str
    language: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    """Response body for LangGraph agent output."""
    query: str
    answer: str
    citations: list[str]
    plan: Dict[str, Any]
    retrieved_docs: list[Dict[str, Any]]
    step_log: list[Dict[str, Any]]


# WebSocket endpoint for real-time ASR
@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    """WebSocket endpoint for streaming audio and receiving transcriptions.
    
    Protocol:
        Client -> Server:
            {"type": "audio", "data": "base64_audio_chunk", "language": "en"}
            {"type": "stop"}
        
        Server -> Client:
            {"type": "transcript", "text": "...", "is_final": true}
            {"type": "error", "message": "..."}
    """
    await websocket.accept()
    session_id = f"session_{id(websocket)}"
    pipeline.create_session(session_id)
    
    logger.info(f"WebSocket connection established: {session_id}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "audio":
                # Receive audio chunk
                audio_base64 = data.get("data", "")
                language = data.get("language", "en")
                
                try:
                    # Decode base64 audio
                    audio_bytes = base64.b64decode(audio_base64)
                    
                    # Add to session buffer
                    pipeline.add_audio_chunk(session_id, audio_bytes)
                    
                    logger.debug(f"Received audio chunk: {len(audio_bytes)} bytes")
                    
                    # Send acknowledgment (optional)
                    # await websocket.send_json({"type": "ack", "received": len(audio_bytes)})
                    
                except Exception as e:
                    logger.error(f"Error processing audio chunk: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Failed to process audio: {str(e)}"
                    })
            
            elif message_type == "stop":
                # Process accumulated audio
                language = data.get("language", "en")
                
                logger.info(f"Received stop signal, processing audio for session {session_id}")
                
                try:
                    # Transcribe accumulated audio
                    logger.info(f"Starting transcription for session {session_id}")
                    result = await pipeline.process_audio_stream(
                        session_id,
                        language=language
                    )
                    
                    logger.info(f"Transcription complete: {result.get('text', '')[:100]}")
                    
                    # Send final transcription
                    await websocket.send_json({
                        "type": "transcript",
                        "text": result.get("text", ""),
                        "is_final": True,
                        "language": result.get("language", language),
                        "segments": result.get("segments", [])
                    })
                    
                    logger.info(f"Sent transcript to client")
                    
                except Exception as e:
                    logger.error(f"Error transcribing audio: {e}", exc_info=True)
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Transcription failed: {str(e)}"
                    })
            
            elif message_type == "ping":
                # Keepalive
                await websocket.send_json({"type": "pong"})
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
        pipeline.delete_session(session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        pipeline.delete_session(session_id)


# REST endpoint for TTS synthesis
@app.post("/api/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    """Generate speech from text using ElevenLabs TTS.
    
    Args:
        request: TTS request with text, voice_id, language, and settings
        
    Returns:
        TTS response with audio_base64, duration, format, and sample_rate
    """
    if not pipeline.tts:
        raise HTTPException(
            status_code=503,
            detail="TTS service not available. Check ELEVENLABS_API_KEY."
        )
    
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty"
        )
    
    try:
        # Build voice settings
        voice_settings = {}
        if request.stability is not None:
            voice_settings["stability"] = request.stability
        if request.similarity_boost is not None:
            voice_settings["similarity_boost"] = request.similarity_boost
        
        # Synthesize speech
        result = await pipeline.synthesize_speech(
            text=request.text,
            voice_id=request.voice_id,
            language=request.language,
            **voice_settings
        )
        
        return TTSResponse(**result)
    
    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"TTS synthesis failed: {str(e)}"
        )


# REST endpoint to get available voices
@app.get("/api/voices", response_model=list[VoiceInfo])
async def get_voices():
    """Get list of available TTS voices.
    
    Returns:
        List of available voices with id, name, language, gender, and accent
    """
    if not pipeline.tts:
        raise HTTPException(
            status_code=503,
            detail="TTS service not available. Check ELEVENLABS_API_KEY."
        )
    
    try:
        voices = await pipeline.get_available_voices()
        return [VoiceInfo(**voice) for voice in voices]
    
    except Exception as e:
        logger.error(f"Failed to get voices: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get voices: {str(e)}"
        )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "asr_available": pipeline.asr is not None,
        "tts_available": pipeline.tts is not None,
        "agent_available": graph_app is not None
    }


def _ensure_langgraph_ready():
    if graph_app is None:
        raise HTTPException(
            status_code=503,
            detail="LangGraph workflow not initialized. Ensure the cloned repo exists and dependencies are installed."
        )


async def _invoke_langgraph(text: str) -> Dict[str, Any]:
    """Run the LangGraph workflow in a worker thread."""
    _ensure_langgraph_ready()

    query = text.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    def _run():
        return graph_app.invoke({  # type: ignore[union-attr]
            "query": query,
            "step_log": []
        })

    return await asyncio.to_thread(_run)


@app.post("/api/agent", response_model=AgentResponse)
async def agent_query(request: AgentRequest):
    """Invoke LangGraph to answer a natural-language shopping query."""
    try:
        result = await _invoke_langgraph(request.text)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent query failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent query failed: {str(e)}")

    return AgentResponse(
        query=result.get("query", request.text),
        answer=result.get("answer", ""),
        citations=result.get("citations", []),
        plan=result.get("plan", {}),
        retrieved_docs=result.get("retrieved_docs", []),
        step_log=result.get("step_log", [])
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Voice Assistant API",
        "version": "1.0.0",
        "endpoints": {
            "websocket": "/ws/voice",
            "tts": "/api/tts",
            "agent": "/api/agent",
            "voices": "/api/voices",
            "health": "/health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

