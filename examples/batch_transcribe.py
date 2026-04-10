"""
Example: Batch transcription of multiple audio files.

Usage:
    python examples/batch_transcribe.py /path/to/audio/files
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import os
from transcription_engine import TranscriptionEngine


def batch_transcribe(directory: str, output_dir: str = "./results"):
    """Transcribe all audio files in directory."""
    
    # Supported formats
    audio_exts = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}
    
    # Find all audio files
    audio_files = [
        f for f in Path(directory).iterdir()
        if f.suffix.lower() in audio_exts
    ]
    
    if not audio_files:
        print(f"No audio files found in {directory}")
        return
    
    print(f"Found {len(audio_files)} audio files")
    
    # Initialize engine
    engine = TranscriptionEngine(
        model_size="base",
        num_speakers=2,
        cpu_threads=2
    )
    
    # Process each file
    for i, audio_file in enumerate(audio_files, 1):
        print(f"\n[{i}/{len(audio_files)}] Processing: {audio_file.name}")
        
        try:
            result = engine.transcribe(
                str(audio_file),
                output_dir=output_dir
            )
            
            print(f"  ✓ Completed: {result['output_file']}")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print(f"\n{'='*50}")
    print(f"Batch processing complete!")
    print(f"Results saved to: {output_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python batch_transcribe.py <directory>")
        print("Example: python batch_transcribe.py ./audio_files")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "./results"
    
    batch_transcribe(input_dir, output_dir)
