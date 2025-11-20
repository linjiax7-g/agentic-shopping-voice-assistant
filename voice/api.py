"""
FastAPI REST API for Voice Shopping Assistant

Provides endpoints for:
- TTS (Text-to-Speech) generation
- Complete query pipeline (Query → LangGraph → TTS)
- Audio file serving

Usage:
    uvicorn voice.api:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pathlib import Path
import os
import uuid
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Voice Shopping Assistant API",
    description="REST API for TTS and agentic product discovery",
    version="1.0.0"
)

# CORS configuration for React frontend
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Output directory for TTS files
OUTPUT_DIR = Path("./tts_output")
OUTPUT_DIR.mkdir(exist_ok=True)

# ============================================================================
# Request/Response Models
# ============================================================================

class TTSRequest(BaseModel):
    """Request model for TTS generation"""
    text: str = Field(..., description="Text to convert to speech", max_length=4096)
    voice: str = Field(
        default="alloy",
        description="Voice selection: alloy, echo, fable, onyx, nova, shimmer"
    )
    model: str = Field(
        default="tts-1",
        description="TTS model: tts-1 (fast) or tts-1-hd (high quality)"
    )

    class Config:
        schema_extra = {
            "example": {
                "text": "I found 3 organic shampoos under $20. The best option is Brand X.",
                "voice": "alloy",
                "model": "tts-1"
            }
        }


class TTSResponse(BaseModel):
    """Response model for TTS generation"""
    success: bool
    audio_id: str
    audio_url: str
    duration_estimate: float
    message: Optional[str] = None


class QueryRequest(BaseModel):
    """Request model for product query"""
    query: str = Field(..., description="Natural language product search query")

    class Config:
        schema_extra = {
            "example": {
                "query": "organic shampoo under $20"
            }
        }


class QueryResponse(BaseModel):
    """Response model for product query with TTS"""
    success: bool
    query: str
    answer: str
    citations: List[str]
    products: List[Dict[str, Any]]
    task: Optional[str] = None
    constraints: Optional[Dict[str, Any]] = None
    audio_id: str
    audio_url: str
    step_log: Optional[List[Dict[str, Any]]] = None


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint

    Returns API status and configuration
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "output_dir": str(OUTPUT_DIR),
        "cors_origins": CORS_ORIGINS
    }


# ============================================================================
# TTS Endpoints
# ============================================================================

@app.post("/api/tts", response_model=TTSResponse, tags=["TTS"])
async def generate_tts(request: TTSRequest):
    """
    Generate TTS audio from text

    **Integration Point:** voice_shopping_assistant_ui.tsx:193 (playTTS function)

    **Process:**
    1. Receives text and voice preference
    2. Generates speech using OpenAI TTS
    3. Saves audio file with unique ID
    4. Returns audio URL and metadata

    **Example:**
    ```bash
    curl -X POST http://localhost:8000/api/tts \\
      -H "Content-Type: application/json" \\
      -d '{"text": "Hello world", "voice": "alloy"}'
    ```
    """
    try:
        logger.info(f"TTS request: {len(request.text)} characters, voice={request.voice}")

        # Import TTS module
        from voice.tts import synthesize_speech, estimate_audio_duration

        # Generate unique filename
        audio_id = str(uuid.uuid4())
        output_path = OUTPUT_DIR / f"{audio_id}.mp3"

        # Synthesize speech
        synthesize_speech(
            text=request.text,
            output_path=str(output_path),
            voice=request.voice,
            model=request.model
        )

        # Estimate duration
        duration = estimate_audio_duration(request.text)

        logger.info(f"TTS generated: {audio_id}.mp3 ({duration:.1f}s)")

        return TTSResponse(
            success=True,
            audio_id=audio_id,
            audio_url=f"/api/tts/audio/{audio_id}",
            duration_estimate=duration,
            message="TTS generated successfully"
        )

    except ValueError as e:
        logger.error(f"TTS validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"TTS generation error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


@app.get("/api/tts/audio/{audio_id}", tags=["TTS"])
async def get_tts_audio(audio_id: str):
    """
    Serve generated TTS audio file

    **Integration Point:** Frontend audio player

    Returns MP3 audio file for playback in browser
    """
    # Validate audio_id format (prevent path traversal)
    try:
        uuid.UUID(audio_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid audio ID format")

    audio_path = OUTPUT_DIR / f"{audio_id}.mp3"

    if not audio_path.exists():
        logger.warning(f"Audio file not found: {audio_id}")
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f"inline; filename={audio_id}.mp3",
            "Cache-Control": "public, max-age=3600"
        }
    )


@app.delete("/api/tts/audio/{audio_id}", tags=["TTS"])
async def delete_tts_audio(audio_id: str):
    """
    Delete TTS audio file (cleanup)
    """
    try:
        uuid.UUID(audio_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid audio ID format")

    audio_path = OUTPUT_DIR / f"{audio_id}.mp3"

    if audio_path.exists():
        audio_path.unlink()
        logger.info(f"Deleted audio: {audio_id}")
        return {"success": True, "message": "Audio deleted"}
    else:
        raise HTTPException(status_code=404, detail="Audio file not found")


# ============================================================================
# Query Pipeline Endpoint
# ============================================================================

@app.post("/api/query", response_model=QueryResponse, tags=["Query"])
async def process_query(request: QueryRequest):
    """
    Process text query through complete pipeline

    **Pipeline:**
    1. Query → LangGraph (Router → Planner → Retriever → Answerer)
    2. Answer → TTS generation
    3. Return structured response with audio

    **Integration Point:** voice_shopping_assistant_ui.tsx (complete flow)

    **Example:**
    ```bash
    curl -X POST http://localhost:8000/api/query \\
      -H "Content-Type: application/json" \\
      -d '{"query": "organic shampoo under $20"}'
    ```
    """
    try:
        logger.info(f"Query request: {request.query}")

        # Import graph and TTS
        from graph.graph import create_graph
        from voice.tts import synthesize_speech

        # Run LangGraph pipeline
        logger.info("Running LangGraph pipeline...")
        graph = create_graph()
        result = graph.invoke({
            "query": request.query,
            "step_log": []
        })

        logger.info(f"Graph completed: task={result.get('task')}, "
                   f"docs={len(result.get('retrieved_docs', []))}")

        # Generate TTS for answer
        logger.info("Generating TTS for answer...")
        audio_id = str(uuid.uuid4())
        output_path = OUTPUT_DIR / f"{audio_id}.mp3"

        synthesize_speech(
            text=result["answer"],
            output_path=str(output_path),
            voice="alloy"
        )

        logger.info(f"Query completed successfully: {audio_id}")

        return QueryResponse(
            success=True,
            query=request.query,
            answer=result["answer"],
            citations=result.get("citations", []),
            products=result.get("retrieved_docs", []),
            task=result.get("task"),
            constraints=result.get("constraints"),
            audio_id=audio_id,
            audio_url=f"/api/tts/audio/{audio_id}",
            step_log=result.get("step_log", [])
        )

    except Exception as e:
        logger.error(f"Query processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
        )


# ============================================================================
# ASR Endpoint (Future Enhancement)
# ============================================================================

@app.post("/api/asr", tags=["ASR"])
async def transcribe_audio(audio_file: UploadFile = File(...)):
    """
    Transcribe audio to text using Whisper ASR

    **Status:** Placeholder for future implementation

    **Future Integration:**
    - Receive audio from frontend (recorded or uploaded)
    - Use Whisper to transcribe
    - Return text query
    - Pass to /api/query endpoint
    """
    # Placeholder for ASR implementation
    raise HTTPException(
        status_code=501,
        detail="ASR endpoint not yet implemented. Use Whisper library for implementation."
    )


# ============================================================================
# Cleanup Endpoint
# ============================================================================

@app.post("/api/cleanup", tags=["Admin"])
async def cleanup_old_audio_files(max_age_hours: int = 24):
    """
    Clean up audio files older than specified hours

    Useful for preventing disk space issues
    """
    import time

    deleted_count = 0
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600

    for audio_file in OUTPUT_DIR.glob("*.mp3"):
        file_age = current_time - audio_file.stat().st_mtime
        if file_age > max_age_seconds:
            audio_file.unlink()
            deleted_count += 1

    logger.info(f"Cleanup: deleted {deleted_count} files older than {max_age_hours}h")

    return {
        "success": True,
        "deleted_count": deleted_count,
        "message": f"Cleaned up {deleted_count} files"
    }


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors"""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )


# ============================================================================
# Startup Event
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("=" * 70)
    logger.info("Voice Shopping Assistant API Starting...")
    logger.info("=" * 70)
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"CORS origins: {CORS_ORIGINS}")
    logger.info(f"OpenAI API configured: {bool(os.getenv('OPENAI_API_KEY'))}")
    logger.info("=" * 70)

    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("⚠️  OPENAI_API_KEY not set! TTS will fail.")
        logger.warning("   Set it with: export OPENAI_API_KEY='your-key-here'")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "voice.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
