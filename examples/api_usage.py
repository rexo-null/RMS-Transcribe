"""
Example: Using RMS Transcribe as a library.

Demonstrates programmatic API usage without GUI.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from transcription_engine import TranscriptionEngine


def transcribe_single_file(audio_path: str):
    """Transcribe a single audio file with full options."""
    
    # Initialize engine with custom settings
    engine = TranscriptionEngine(
        model_size="small",      # better quality than base
        num_speakers=2,
        cpu_threads=4,           # more threads for faster processing
        language="ru",           # Russian language
        vad_filter=True          # skip silent parts
    )
    
    # Process file
    print(f"Transcribing: {audio_path}")
    
    result = engine.transcribe(
        audio_path=audio_path,
        output_dir="./results",
        export_format="json"     # or "txt" or "both"
    )
    
    # Display results
    print(f"\nTranscription complete!")
    print(f"Duration: {result['duration']:.2f} seconds")
    print(f"Output: {result['output_file']}")
    
    # Print segments
    if "segments" in result:
        print(f"\nSegments ({len(result['segments'])} total):")
        for seg in result["segments"][:5]:  # Show first 5
            speaker = seg.get("speaker", "Unknown")
            text = seg.get("text", "")
            print(f"  [{speaker}] {text[:60]}...")
    
    return result


if __name__ == "__main__":
    # Example usage
    # Replace with your audio file path
    audio_file = "./test_audio.mp3"
    
    try:
        transcribe_single_file(audio_file)
    except FileNotFoundError:
        print(f"File not found: {audio_file}")
        print("Please provide a valid audio file path")
