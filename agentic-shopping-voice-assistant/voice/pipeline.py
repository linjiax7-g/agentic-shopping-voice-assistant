"""Voice Pipeline Orchestration

Based on pipecat/pipeline/pipeline.py
Coordinates ASR and TTS services for voice interactions.
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from uuid import uuid4
from dotenv import load_dotenv
from loguru import logger

from .asr import WhisperASR
from .tts import ElevenLabsTTS


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class VoicePipeline:
    """Voice Pipeline for coordinating ASR and TTS services
    
    Manages the lifecycle of voice interactions including:
    - Audio stream processing for ASR
    - Text-to-speech generation
    - Session state management
    """
    
    def __init__(
        self,
        asr_config: Optional[Dict[str, Any]] = None,
        tts_config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the voice pipeline.
        
        Args:
            asr_config: Configuration for ASR service
            tts_config: Configuration for TTS service
        """
        self.asr_config = asr_config or {}
        self.tts_config = tts_config or {}
        
        self.asr: Optional[WhisperASR] = None
        self.tts: Optional[ElevenLabsTTS] = None
        
        # Session state
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        logger.info("VoicePipeline initialized")
    
    def initialize_asr(self, **config):
        """Initialize the ASR service.
        
        Args:
            **config: Configuration overrides for ASR
        """
        merged_config = {**self.asr_config, **config}
        self.asr = WhisperASR(**merged_config)
        logger.info("ASR service initialized")
    
    def initialize_tts(self, **config):
        """Initialize the TTS service.
        
        Args:
            **config: Configuration overrides for TTS
        """
        merged_config = {**self.tts_config, **config}
        self.tts = ElevenLabsTTS(**merged_config)
        logger.info("TTS service initialized")
    
    def create_session(self, session_id: str, metadata: Optional[Dict] = None):
        """Create a new session.
        
        Args:
            session_id: Unique session identifier
            metadata: Optional session metadata
        """
        self.sessions[session_id] = {
            "metadata": metadata or {},
            "audio_chunks": [],
            "transcripts": [],
            "created_at": None  # Could add timestamp
        }
        logger.info(f"Session created: {session_id}")
    
    def delete_session(self, session_id: str):
        """Delete a session.
        
        Args:
            session_id: Session identifier to delete
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Session deleted: {session_id}")
    
    def add_audio_chunk(self, session_id: str, audio_chunk: bytes):
        """Add audio chunk to session buffer.
        
        Args:
            session_id: Session identifier
            audio_chunk: Audio data chunk
        """
        if session_id not in self.sessions:
            self.create_session(session_id)
        
        self.sessions[session_id]["audio_chunks"].append(audio_chunk)
    
    def get_audio_chunks(self, session_id: str) -> list:
        """Get audio chunks for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of audio chunks
        """
        if session_id not in self.sessions:
            return []
        
        return self.sessions[session_id]["audio_chunks"]
    
    def clear_audio_chunks(self, session_id: str):
        """Clear audio chunks for a session.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.sessions:
            self.sessions[session_id]["audio_chunks"] = []
    
    async def process_audio(
        self,
        session_id: str,
        audio_data: bytes,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process audio through ASR.
        
        Args:
            session_id: Session identifier
            audio_data: Audio bytes to transcribe
            language: Language code for transcription
            
        Returns:
            Transcription result dictionary
        """
        if not self.asr:
            raise RuntimeError("ASR service not initialized")
        
        result = await self.asr.transcribe(audio_data, language)
        
        # Store transcript in session
        if session_id in self.sessions:
            self.sessions[session_id]["transcripts"].append(result)
        
        return result
    
    async def process_audio_stream(
        self,
        session_id: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process accumulated audio chunks from session.
        
        Args:
            session_id: Session identifier
            language: Language code for transcription
            
        Returns:
            Transcription result dictionary
        """
        if not self.asr:
            raise RuntimeError("ASR service not initialized")
        
        chunks = self.get_audio_chunks(session_id)
        logger.info(f"Processing {len(chunks)} audio chunks for session {session_id}")
        
        if not chunks:
            logger.warning(f"No audio chunks found for session {session_id}")
            return {"text": "", "language": language or "en", "segments": []}
        
        # Concatenate all PCM chunks (frontend sends raw PCM directly)
        try:
            logger.info(f"Concatenating {len(chunks)} PCM audio chunks...")
            pcm_audio = b"".join(chunks)
            logger.info(f"Total PCM audio: {len(pcm_audio)} bytes, transcribing...")
            result = await self.asr.transcribe(pcm_audio, language)
            logger.info(f"Transcription complete: '{result.get('text', '')[:100]}'")
        except Exception as e:
            logger.error(f"Audio processing failed: {e}", exc_info=True)
            raise
        
        # Store transcript and clear chunks
        if session_id in self.sessions:
            self.sessions[session_id]["transcripts"].append(result)
            self.clear_audio_chunks(session_id)
        
        return result
    
    async def synthesize_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        language: Optional[str] = None,
        **voice_settings
    ) -> Dict[str, Any]:
        """Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            voice_id: Voice ID to use
            language: Language code
            **voice_settings: Voice customization settings
            
        Returns:
            Audio synthesis result dictionary
        """
        if not self.tts:
            raise RuntimeError("TTS service not initialized")
        
        return await self.tts.synthesize(
            text,
            voice_id=voice_id,
            language=language,
            **voice_settings
        )
    
    async def get_available_voices(self) -> list:
        """Get available TTS voices.
        
        Returns:
            List of available voices
        """
        if not self.tts:
            raise RuntimeError("TTS service not initialized")
        
        return await self.tts.get_voices()
    
    async def _convert_to_pcm(self, audio_chunks: list) -> bytes:
        """Convert WebM/Opus audio chunks to 16-bit PCM.
        
        Args:
            audio_chunks: List of audio byte chunks (WebM format)
            
        Returns:
            PCM audio bytes (16-bit, 16kHz, mono)
        """
        try:
            import ffmpeg
            import tempfile
            
            # Concatenate all chunks into a single blob
            combined_audio = b"".join(audio_chunks)
            
            # Create temporary files for input and output
            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as input_file:
                input_file.write(combined_audio)
                input_path = input_file.name
            
            try:
                # Use ffmpeg to convert WebM to raw PCM
                # Output format: 16-bit PCM, 16kHz sample rate, mono
                output_path = input_path + '.pcm'
                
                # Ensure ffmpeg is in PATH for Windows
                if os.name == 'nt':  # Windows
                    ffmpeg_bin_path = os.path.join(
                        os.environ.get('LOCALAPPDATA', ''), 
                        'Microsoft', 'WinGet', 'Packages', 
                        'Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe',
                        'ffmpeg-8.0-full_build', 'bin'
                    )
                    if os.path.exists(ffmpeg_bin_path) and ffmpeg_bin_path not in os.environ.get('PATH', ''):
                        os.environ['PATH'] = ffmpeg_bin_path + os.pathsep + os.environ.get('PATH', '')
                        logger.info(f"Added ffmpeg to PATH: {ffmpeg_bin_path}")
                
                await asyncio.to_thread(
                    lambda: (
                        ffmpeg
                        .input(input_path)
                        .output(
                            output_path,
                            format='s16le',  # signed 16-bit little-endian PCM
                            acodec='pcm_s16le',  # PCM codec
                            ac=1,  # mono (1 channel)
                            ar=16000  # 16kHz sample rate
                        )
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True, quiet=True)
                    )
                )
                
                # Read the converted PCM data
                with open(output_path, 'rb') as f:
                    pcm_bytes = f.read()
                
                logger.info(f"Converted {len(combined_audio)} bytes WebM to {len(pcm_bytes)} bytes PCM")
                
                return pcm_bytes
                
            finally:
                # Clean up temporary files
                if os.path.exists(input_path):
                    os.unlink(input_path)
                if os.path.exists(output_path):
                    os.unlink(output_path)
            
        except ImportError:
            logger.error("ffmpeg-python not installed. Install with: pip install ffmpeg-python")
            logger.error("Also install ffmpeg system binary: https://ffmpeg.org/download.html")
            raise RuntimeError("Audio conversion requires ffmpeg-python and ffmpeg")
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
            raise RuntimeError(f"Audio conversion failed: {e}")
        except Exception as e:
            logger.error(f"Audio conversion failed: {e}")
            raise


def _lazy_import_create_graph():
    """Import graph factory without creating circular deps."""
    try:
        from graph.graph import create_graph  # type: ignore
        return create_graph
    except ModuleNotFoundError:
        # When running scripts like `python voice/test_pipeline.py`,
        # ensure project root is on sys.path so `graph` can be found.
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        from graph.graph import create_graph  # type: ignore
        return create_graph


def load_default_voice_pipeline(
    asr_overrides: Optional[Dict[str, Any]] = None,
    tts_overrides: Optional[Dict[str, Any]] = None,
    load_env: bool = True
) -> VoicePipeline:
    """Create and initialize VoicePipeline using environment defaults."""
    if load_env:
        load_dotenv()

    asr_overrides = asr_overrides or {}
    tts_overrides = tts_overrides or {}

    pipeline = VoicePipeline()

    asr_config = {
        "model": os.getenv("WHISPER_MODEL", "base"),
        "device": os.getenv("WHISPER_DEVICE", "cpu"),
        "compute_type": os.getenv("WHISPER_COMPUTE_TYPE", "default"),
        "language": os.getenv("WHISPER_LANGUAGE", "en")
    }
    asr_config.update(asr_overrides)
    pipeline.initialize_asr(**asr_config)

    tts_api_key = tts_overrides.get("api_key") or os.getenv("ELEVENLABS_API_KEY")
    if not tts_api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is required for TTS synthesis")

    tts_config = {
        "api_key": tts_api_key,
        "default_voice_id": os.getenv("ELEVENLABS_VOICE_ID"),
        "default_model": os.getenv("ELEVENLABS_MODEL", "eleven_turbo_v2_5"),
        "sample_rate": int(os.getenv("ELEVENLABS_SAMPLE_RATE", "44100"))
    }
    tts_config.update(tts_overrides)
    pipeline.initialize_tts(**tts_config)

    return pipeline


async def _convert_file_to_pcm(audio_file_path: str) -> bytes:
    """Convert arbitrary audio file to raw PCM suitable for Whisper."""
    try:
        import ffmpeg
    except ImportError as exc:
        raise RuntimeError("ffmpeg-python is required to read audio files") from exc

    def _run_ffmpeg():
        kwargs = dict(
            format="s16le",
            acodec="pcm_s16le",
            ac=1,
            ar=16000,
        )
        process = (
            ffmpeg
            .input(audio_file_path)
            .output("pipe:", **kwargs)
            .run(capture_stdout=True, capture_stderr=True)
        )
        return process

    try:
        stdout, _ = await asyncio.to_thread(_run_ffmpeg)
        return stdout
    except ffmpeg.Error as e:  # type: ignore[name-defined]
        logger.error(f"FFmpeg conversion failed: {e.stderr.decode() if e.stderr else e}")
        raise RuntimeError("Failed to convert audio file to PCM") from e


async def transcribe_audio_file(
    audio_file_path: str,
    pipeline: Optional[VoicePipeline] = None,
    *,
    language: Optional[str] = None
) -> Dict[str, Any]:
    """Transcribe an audio file using the voice pipeline."""
    if not pipeline:
        pipeline = load_default_voice_pipeline()

    pcm_audio = await _convert_file_to_pcm(audio_file_path)
    session_id = f"file_{uuid4().hex}"
    pipeline.create_session(session_id)
    pipeline.add_audio_chunk(session_id, pcm_audio)
    result = await pipeline.process_audio_stream(session_id, language=language)
    pipeline.delete_session(session_id)
    return result


async def voice_to_voice_query(
    audio_input_path: str,
    pipeline: Optional[VoicePipeline] = None,
    *,
    language: Optional[str] = None,
    voice_id: Optional[str] = None,
    graph_version: str = "hybrid",
    graph_input: Optional[Dict[str, Any]] = None,
    **voice_settings
) -> Dict[str, Any]:
    """Complete voice-to-voice pipeline integrating LangGraph."""
    pipeline = pipeline or load_default_voice_pipeline()

    transcription = await transcribe_audio_file(
        audio_input_path,
        pipeline=pipeline,
        language=language
    )
    query_text = (transcription.get("text") or "").strip()
    if not query_text:
        raise RuntimeError("No speech detected in the provided audio input")

    create_graph = _lazy_import_create_graph()
    graph = create_graph(version=graph_version)
    state = graph_input.copy() if graph_input else {"step_log": []}
    state["query"] = query_text

    graph_result = graph.invoke(state)

    tts_payload = await pipeline.synthesize_speech(
        graph_result.get("answer", ""),
        voice_id=voice_id,
        language=language or transcription.get("language"),
        **voice_settings
    )

    return {
        "query_text": query_text,
        "transcription": transcription,
        "graph_result": graph_result,
        "tts": tts_payload
    }

