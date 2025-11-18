"""Speech-to-Text (ASR) Module using Whisper

Based on pipecat/services/whisper/stt.py
Implements streaming audio processing with Whisper for real-time transcription.
"""

import asyncio
from typing import Optional, Dict, Any
import numpy as np
from loguru import logger


class WhisperASR:
    """Whisper-based Speech Recognition Service
    
    Provides real-time transcription of audio streams using faster-whisper.
    Supports multiple languages and streaming audio processing.
    """
    
    def __init__(
        self,
        model: str = "base",
        device: str = "auto",
        compute_type: str = "default",
        no_speech_prob: float = 0.4,
        language: str = "en"
    ):
        """Initialize the Whisper ASR service.
        
        Args:
            model: Whisper model size ('tiny', 'base', 'small', 'medium', 'large-v3')
            device: Device to run inference on ('cpu', 'cuda', or 'auto')
            compute_type: Compute type for inference ('default', 'int8', 'float16')
            no_speech_prob: Probability threshold for filtering out non-speech
            language: Default language code for transcription
        """
        self.model_name = model
        self.device = device
        self.compute_type = compute_type
        self.no_speech_prob = no_speech_prob
        self.language = language
        self._model = None
        
        self._load_model()
    
    def _load_model(self):
        """Load the Whisper model.
        
        Downloads from Hugging Face on first run if not cached.
        """
        try:
            from faster_whisper import WhisperModel
            
            logger.info(f"Loading Whisper model: {self.model_name}")
            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type
            )
            logger.info("Whisper model loaded successfully")
        except ModuleNotFoundError as e:
            logger.error(f"Missing dependency: {e}")
            logger.error("Install with: pip install faster-whisper")
            raise
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    async def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transcribe audio data to text.
        
        Args:
            audio_data: Raw audio bytes in 16-bit PCM format
            language: Language code for transcription (overrides default)
            
        Returns:
            Dictionary with 'text', 'language', and 'segments' keys
        """
        if not self._model:
            raise RuntimeError("Whisper model not loaded")
        
        logger.info(f"Starting transcription: {len(audio_data)} bytes of audio data")
        
        # Convert audio bytes to float32 array
        # Divide by 32768 because we have signed 16-bit data
        try:
            audio_float = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            logger.info(f"Converted to float32 array: {len(audio_float)} samples ({len(audio_float)/16000:.2f} seconds)")
        except Exception as e:
            logger.error(f"Failed to convert audio data: {e}")
            raise
        
        # Use provided language or default
        lang = language or self.language
        
        # Run transcription in thread pool to avoid blocking
        logger.info(f"Running Whisper transcription (language: {lang})...")
        segments, info = await asyncio.to_thread(
            self._model.transcribe,
            audio_float,
            language=lang
        )
        logger.info(f"Whisper transcription completed")
        
        # Collect transcription text and filter by speech probability
        text_parts = []
        segment_list = []
        
        try:
            logger.info("Processing transcription segments...")
            segment_count = 0
            
            # Convert generator to list to avoid iteration issues
            try:
                segments_list = list(segments)
                logger.info(f"Converted segments generator to list: {len(segments_list)} segments")
            except Exception as e:
                logger.error(f"Failed to convert segments to list: {e}", exc_info=True)
                # Return empty result if we can't process segments
                return {
                    "text": "",
                    "language": lang,
                    "segments": [],
                    "language_probability": 1.0
                }
            
            for segment in segments_list:
                segment_count += 1
                logger.debug(f"Segment {segment_count}: text='{segment.text}', no_speech_prob={segment.no_speech_prob}")
                if segment.no_speech_prob < self.no_speech_prob:
                    text_parts.append(segment.text)
                    segment_list.append({
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text,
                        "no_speech_prob": segment.no_speech_prob
                    })
                else:
                    logger.debug(f"Segment {segment_count} filtered out (high no_speech_prob)")
            
            logger.info(f"Processed {segment_count} segments, {len(text_parts)} passed filter")
        except Exception as e:
            logger.error(f"Error processing segments: {e}", exc_info=True)
            raise
        
        full_text = " ".join(text_parts).strip()
        logger.info(f"Final transcription text: '{full_text}'")
        
        result = {
            "text": full_text,
            "language": info.language if hasattr(info, 'language') else lang,
            "segments": segment_list,
            "language_probability": info.language_probability if hasattr(info, 'language_probability') else 1.0
        }
        logger.info(f"Returning transcription result: {len(full_text)} characters")
        return result
    
    async def transcribe_stream(
        self,
        audio_chunks: list,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Transcribe streaming audio chunks.
        
        Args:
            audio_chunks: List of audio byte chunks in 16-bit PCM format
            language: Language code for transcription
            
        Returns:
            Dictionary with transcription results
        """
        # Concatenate all chunks
        combined_audio = b"".join(audio_chunks)
        
        # Process the combined audio
        return await self.transcribe(combined_audio, language)
    
    def set_language(self, language: str):
        """Set the default language for transcription.
        
        Args:
            language: Language code (e.g., 'en', 'zh', 'es')
        """
        self.language = language
        logger.info(f"ASR language set to: {language}")

