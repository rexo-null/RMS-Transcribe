import csv
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}


@dataclass
class TranscriptLine:
    start: float
    end: float
    speaker: str
    text: str


@dataclass
class FileTranscriptionResult:
    source_file: str
    created_at: str
    language: str
    model_size: str
    vad_enabled: bool
    items: List[TranscriptLine]


def timestamp_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_dirs(base_dir: Path) -> Dict[str, Path]:
    models_dir = base_dir / "models"
    results_dir = base_dir / "results"
    whisper_dir = models_dir / "whisper"
    pyannote_dir = models_dir / "pyannote"

    models_dir.mkdir(parents=True, exist_ok=True)
    whisper_dir.mkdir(parents=True, exist_ok=True)
    pyannote_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    return {
        "models": models_dir,
        "results": results_dir,
        "whisper": whisper_dir,
        "pyannote": pyannote_dir,
    }


def is_supported_audio(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS


def _safe_stem(path: Path) -> str:
    return "".join(ch for ch in path.stem if ch.isalnum() or ch in "-_ ").strip() or "audio"


def format_time(seconds: float) -> str:
    total = max(0.0, float(seconds))
    mm = int(total // 60)
    ss = total - mm * 60
    return f"{mm:02d}:{ss:04.1f}"


def to_readable_text(items: List[TranscriptLine]) -> str:
    lines = []
    for item in items:
        lines.append(
            f"[{format_time(item.start)}-{format_time(item.end)}] {item.speaker}: {item.text}"
        )
    return "\n".join(lines)


def export_result_files(result: FileTranscriptionResult, results_dir: Path) -> Dict[str, Path]:
    source_path = Path(result.source_file)
    file_name = _safe_stem(source_path)
    date_part = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = results_dir / f"{file_name}_{date_part}.json"
    txt_path = results_dir / f"{file_name}_{date_part}.txt"
    csv_path = results_dir / f"{file_name}_{date_part}.csv"

    json_payload: Dict[str, Any] = {
        "source_file": result.source_file,
        "created_at": result.created_at,
        "language": result.language,
        "model_size": result.model_size,
        "vad_enabled": result.vad_enabled,
        "items": [asdict(item) for item in result.items],
    }

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(json_payload, f, ensure_ascii=False, indent=2)

    with txt_path.open("w", encoding="utf-8") as f:
        f.write(to_readable_text(result.items))

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["start", "end", "speaker", "text"])
        writer.writeheader()
        for item in result.items:
            writer.writerow(asdict(item))

    return {"json": json_path, "txt": txt_path, "csv": csv_path}


def make_logger(push_event, log_file: Path | None = None):
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)

    def _log(message: str, level: str = "info") -> None:
        ts = timestamp_now()
        push_event(
            {
                "type": "log",
                "level": level,
                "timestamp": ts,
                "message": message,
            }
        )
        if log_file is not None:
            with log_file.open("a", encoding="utf-8") as f:
                f.write(f"[{ts}] [{level.upper()}] {message}\n")

    return _log
