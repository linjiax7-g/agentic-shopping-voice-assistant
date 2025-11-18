"""Voice Assistant Module

Provides ASR (Automatic Speech Recognition), TTS (Text-to-Speech),
and pipeline orchestration for voice interactions.
"""

from .asr import WhisperASR
from .tts import ElevenLabsTTS
from .pipeline import (
    VoicePipeline,
    load_default_voice_pipeline,
    transcribe_audio_file,
    voice_to_voice_query,
)

__all__ = [
    "WhisperASR",
    "ElevenLabsTTS",
    "VoicePipeline",
    "load_default_voice_pipeline",
    "transcribe_audio_file",
    "voice_to_voice_query",
]

