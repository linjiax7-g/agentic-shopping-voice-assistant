"""CLI helper to run the LangGraph voice pipeline end-to-end."""

import argparse
import asyncio
import base64
import sys
from pathlib import Path

# Ensure project root is on sys.path so `graph` can be imported
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from voice.pipeline import load_default_voice_pipeline, voice_to_voice_query  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test the LangGraph voice pipeline using a prerecorded audio file."
    )
    parser.add_argument(
        "audio_path",
        type=Path,
        help="Path to an audio file (wav/mp3/webm) containing the user's query.",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Optional language code override for Whisper (default is env WHISPER_LANGUAGE).",
    )
    parser.add_argument(
        "--voice-id",
        default=None,
        help="Optional ElevenLabs voice_id override for TTS.",
    )
    parser.add_argument(
        "--graph-version",
        default="hybrid",
        help="LangGraph version registered in graph/graph.py (default: hybrid).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("response.mp3"),
        help="Where to save the synthesized response audio (default: response.mp3).",
    )
    return parser.parse_args()


async def _run(args: argparse.Namespace):
    pipeline = load_default_voice_pipeline()
    result = await voice_to_voice_query(
        str(args.audio_path),
        pipeline=pipeline,
        language=args.language,
        voice_id=args.voice_id,
        graph_version=args.graph_version,
    )

    print("\n=== Voice-to-Voice Test ===")
    print(f"Transcript: {result['query_text']}")
    print(f"Answer: {result['graph_result'].get('answer', '')}")
    print(f"Citations: {result['graph_result'].get('citations', [])}")
    print(f"Retrieved docs: {len(result['graph_result'].get('retrieved_docs', []))}")

    audio_b64 = result["tts"]["audio_base64"]
    args.output.write_bytes(base64.b64decode(audio_b64))
    print(f"\nSynthesized audio written to: {args.output.resolve()}")


def main():
    args = _parse_args()
    if not args.audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {args.audio_path}")
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()

