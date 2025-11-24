"""
Text-to-Speech (TTS) module using OpenAI TTS API

This module provides functions to convert text to speech using OpenAI's TTS models.
Supports multiple voice options and high-quality audio output.
"""

from pathlib import Path
from typing import Literal
import os

VoiceType = Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]


def synthesize_speech(
    text: str,
    output_path: str,
    voice: VoiceType = "alloy",
    model: str = "tts-1"
) -> str:
    """
    Convert text to speech using OpenAI TTS

    Args:
        text: Answer text to speak (max ~4096 characters)
        output_path: Where to save audio file (e.g., "output.mp3")
        voice: Voice selection - options:
            - "alloy": Neutral, balanced voice
            - "echo": Male, clear voice
            - "fable": British accent, expressive
            - "onyx": Deep male voice
            - "nova": Female, energetic
            - "shimmer": Female, warm and soft
        model: TTS model to use:
            - "tts-1": Standard quality, faster
            - "tts-1-hd": Higher quality, slower

    Returns:
        Path to generated audio file (same as output_path)

    Raises:
        ValueError: If OpenAI API key is not set
        Exception: If TTS generation fails

    Examples:
        >>> synthesize_speech("Hello world", "greeting.mp3")
        'greeting.mp3'

        >>> synthesize_speech(
        ...     "Welcome to our store",
        ...     "welcome.mp3",
        ...     voice="nova",
        ...     model="tts-1-hd"
        ... )
        'welcome.mp3'
    """
    # Import here to avoid import errors if openai not installed
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError(
            "OpenAI library not installed. Install with: pip install openai>=1.0.0"
        )

    # Validate API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable not set. "
            "Please set it with: export OPENAI_API_KEY='your-key-here'"
        )

    # Validate text length (OpenAI has ~4096 character limit)
    if len(text) > 4096:
        raise ValueError(
            f"Text too long ({len(text)} characters). "
            "OpenAI TTS supports up to 4096 characters. "
            "Consider splitting into multiple chunks."
        )

    # Initialize client
    client = OpenAI(api_key=api_key)

    # Ensure output directory exists
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Generate speech
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text,
            response_format="mp3"  # Can also use "opus", "aac", "flac"
        )

        # Save to file
        response.stream_to_file(output_path)

        return output_path

    except Exception as e:
        raise Exception(f"TTS generation failed: {str(e)}")


def synthesize_speech_chunked(
    text: str,
    output_dir: str,
    voice: VoiceType = "alloy",
    model: str = "tts-1",
    chunk_size: int = 4000
) -> list[str]:
    """
    Synthesize long text by splitting into chunks

    Useful for text longer than 4096 characters.
    Splits on sentence boundaries when possible.

    Args:
        text: Long text to convert to speech
        output_dir: Directory to save audio chunks
        voice: Voice selection
        model: TTS model
        chunk_size: Max characters per chunk (default 4000)

    Returns:
        List of paths to generated audio files

    Examples:
        >>> long_text = "..." * 5000
        >>> chunks = synthesize_speech_chunked(long_text, "output/")
        >>> print(f"Generated {len(chunks)} audio files")
    """
    import re

    # Simple sentence splitter
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current_chunk = ""
    chunk_paths = []
    chunk_num = 0

    for sentence in sentences:
        if len(current_chunk) + len(sentence) < chunk_size:
            current_chunk += sentence + " "
        else:
            if current_chunk:
                # Save current chunk
                chunk_num += 1
                output_path = f"{output_dir}/chunk_{chunk_num:03d}.mp3"
                synthesize_speech(current_chunk.strip(), output_path, voice, model)
                chunk_paths.append(output_path)
            current_chunk = sentence + " "

    # Save final chunk
    if current_chunk:
        chunk_num += 1
        output_path = f"{output_dir}/chunk_{chunk_num:03d}.mp3"
        synthesize_speech(current_chunk.strip(), output_path, voice, model)
        chunk_paths.append(output_path)

    return chunk_paths


# Estimate duration (rough approximation)
def estimate_audio_duration(text: str, words_per_minute: int = 150) -> float:
    """
    Estimate audio duration in seconds

    Args:
        text: Text to estimate
        words_per_minute: Speaking rate (default 150 wpm)

    Returns:
        Estimated duration in seconds

    Examples:
        >>> estimate_audio_duration("Hello world")
        0.8
    """
    words = len(text.split())
    return (words / words_per_minute) * 60


if __name__ == "__main__":
    # Demo usage
    print("TTS Module Demo")
    print("=" * 50)

    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
    else:
        print("✅ OPENAI_API_KEY is set")

        # Test synthesis
        test_text = "Welcome to our voice shopping assistant. How can I help you today?"
        output_path = "test_output.mp3"

        try:
            result = synthesize_speech(test_text, output_path, voice="nova")
            duration = estimate_audio_duration(test_text)
            print(f"✅ Generated: {result}")
            print(f"📊 Estimated duration: {duration:.1f} seconds")
        except Exception as e:
            print(f"❌ Error: {e}")
