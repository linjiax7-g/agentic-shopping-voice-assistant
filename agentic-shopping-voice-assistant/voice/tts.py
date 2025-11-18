"""Text-to-Speech (TTS) Module using ElevenLabs

Based on pipecat/services/elevenlabs/tts.py
Implements fragment-based speech synthesis with voice customization.
"""

import base64
from typing import Optional, Dict, Any
import aiohttp
from loguru import logger


class ElevenLabsTTS:
    """ElevenLabs Text-to-Speech Service
    
    Provides high-quality speech synthesis with multiple voices and languages.
    Uses ElevenLabs HTTP API for fragment-based audio generation.
    """
    
    # Default ElevenLabs voices (examples - actual voice IDs needed)
    DEFAULT_VOICES = {
        "rachel": "21m00Tcm4TlvDq8ikWAM",  # English female
        "adam": "pNInz6obpgDQGcFmaJgB",     # English male
        "bella": "EXAVITQu4vr4xnSDxMaL",    # English female
        "antoni": "ErXwobaYiN019PkySvjV",   # English male
    }
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.elevenlabs.io",
        default_voice_id: Optional[str] = None,
        default_model: str = "eleven_turbo_v2_5",
        sample_rate: int = 44100
    ):
        """Initialize the ElevenLabs TTS service.
        
        Args:
            api_key: ElevenLabs API key
            base_url: Base URL for ElevenLabs API
            default_voice_id: Default voice ID to use
            default_model: TTS model to use
            sample_rate: Output audio sample rate
        """
        self.api_key = api_key
        self.base_url = base_url
        self.default_voice_id = default_voice_id or self.DEFAULT_VOICES["rachel"]
        self.model = default_model
        self.sample_rate = sample_rate
        
        # Voice settings
        self.voice_settings = {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True
        }
    
    def _get_output_format(self) -> str:
        """Get the appropriate output format for the sample rate.
        
        Returns MP3 format for browser compatibility.
        PCM formats are not playable in browsers without conversion.
        """
        # Use MP3 format for browser compatibility
        format_map = {
            8000: "mp3_22050_32",
            16000: "mp3_22050_32",
            22050: "mp3_22050_32",
            24000: "mp3_44100_64",
            44100: "mp3_44100_128"
        }
        return format_map.get(self.sample_rate, "mp3_44100_128")
    
    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None,
        language: Optional[str] = None,
        **voice_settings
    ) -> Dict[str, Any]:
        """Synthesize speech from text.
        
        Args:
            text: Text to convert to speech
            voice_id: Voice ID to use (overrides default)
            language: Language code (e.g., 'en', 'zh', 'es')
            **voice_settings: Optional voice settings (stability, similarity_boost, etc.)
            
        Returns:
            Dictionary with 'audio_base64', 'duration', and 'format' keys
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Use provided voice or default
        vid = voice_id or self.default_voice_id
        
        # Build the URL
        url = f"{self.base_url}/v1/text-to-speech/{vid}"
        
        # Merge voice settings
        settings = {**self.voice_settings, **voice_settings}
        
        # Build payload
        payload = {
            "text": text,
            "model_id": self.model,
            "voice_settings": settings
        }
        
        # Add language if supported by model
        if language and self.model in ["eleven_turbo_v2_5", "eleven_flash_v2_5"]:
            payload["language_code"] = language
        
        # Build headers
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        }
        
        # Build query parameters
        params = {
            "output_format": self._get_output_format()
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    params=params
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"ElevenLabs API error: {error_text}")
                        raise Exception(f"ElevenLabs API error: {error_text}")
                    
                    # Read audio data
                    audio_data = await response.read()
                    
                    # Convert to base64
                    audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                    
                    # Estimate duration (rough estimate)
                    # For MP3, roughly 1 second per 16KB at 128kbps
                    duration = len(audio_data) / 16000.0
                    
                    return {
                        "audio_base64": audio_base64,
                        "duration": duration,
                        "format": "mp3" if "mp3" in self._get_output_format() else "pcm",
                        "sample_rate": self.sample_rate
                    }
        
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            raise
    
    async def get_voices(self) -> list:
        """Get available voices from ElevenLabs.
        
        Returns:
            List of voice dictionaries with 'id', 'name', and 'language' keys
        """
        url = f"{self.base_url}/v1/voices"
        headers = {"xi-api-key": self.api_key}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch voices: {response.status}")
                        # Return default voices as fallback
                        return [
                            {"id": vid, "name": name.capitalize(), "language": "en"}
                            for name, vid in self.DEFAULT_VOICES.items()
                        ]
                    
                    data = await response.json()
                    voices = []
                    
                    for voice in data.get("voices", []):
                        voices.append({
                            "id": voice.get("voice_id"),
                            "name": voice.get("name"),
                            "language": voice.get("labels", {}).get("language", "en"),
                            "gender": voice.get("labels", {}).get("gender", ""),
                            "accent": voice.get("labels", {}).get("accent", "")
                        })
                    
                    return voices
        
        except Exception as e:
            logger.error(f"Failed to get voices: {e}")
            # Return default voices as fallback
            return [
                {"id": vid, "name": name.capitalize(), "language": "en"}
                for name, vid in self.DEFAULT_VOICES.items()
            ]
    
    def set_voice_settings(
        self,
        stability: Optional[float] = None,
        similarity_boost: Optional[float] = None,
        style: Optional[float] = None,
        use_speaker_boost: Optional[bool] = None
    ):
        """Update default voice settings.
        
        Args:
            stability: Voice stability (0.0-1.0)
            similarity_boost: Similarity boost (0.0-1.0)
            style: Style control (0.0-1.0)
            use_speaker_boost: Whether to use speaker boost
        """
        if stability is not None:
            self.voice_settings["stability"] = stability
        if similarity_boost is not None:
            self.voice_settings["similarity_boost"] = similarity_boost
        if style is not None:
            self.voice_settings["style"] = style
        if use_speaker_boost is not None:
            self.voice_settings["use_speaker_boost"] = use_speaker_boost

