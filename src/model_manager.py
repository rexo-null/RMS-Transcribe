from pathlib import Path
from typing import Callable, Dict

from huggingface_hub import snapshot_download


class ModelManager:
    def __init__(
        self,
        models_dir: Path,
        hf_token: str,
        logger: Callable[[str, str], None],
    ) -> None:
        self.models_dir = models_dir
        self.hf_token = hf_token
        self.logger = logger

        self.whisper_root = self.models_dir / "whisper"
        self.pyannote_root = self.models_dir / "pyannote"
        self.whisper_root.mkdir(parents=True, exist_ok=True)
        self.pyannote_root.mkdir(parents=True, exist_ok=True)

    def get_whisper_dir(self, model_size: str) -> Path:
        return self.whisper_root / f"faster-whisper-{model_size}"

    def get_pyannote_dir(self) -> Path:
        return self.pyannote_root / "speaker-diarization-3.1"

    def check_status(self, model_size: str) -> Dict[str, bool]:
        whisper_dir = self.get_whisper_dir(model_size)
        pyannote_dir = self.get_pyannote_dir()

        whisper_ok = (whisper_dir / "model.bin").exists()
        pyannote_ok = (pyannote_dir / "config.yaml").exists()

        return {
            "whisper": whisper_ok,
            "pyannote": pyannote_ok,
            "all_ready": whisper_ok and pyannote_ok,
        }

    def ensure_models(
        self,
        model_size: str,
        progress_callback: Callable[[float, str], None],
    ) -> Dict[str, Path]:
        whisper_dir = self.get_whisper_dir(model_size)
        pyannote_dir = self.get_pyannote_dir()

        progress_callback(2, "Проверка локальных моделей...")

        if not (whisper_dir / "model.bin").exists():
            self.logger(f"Whisper {model_size} не найден, запускаю загрузку...", "warning")
            progress_callback(10, f"Скачивание Whisper ({model_size})...")
            snapshot_download(
                repo_id=f"Systran/faster-whisper-{model_size}",
                local_dir=str(whisper_dir),
                local_dir_use_symlinks=False,
                token=self.hf_token or None,
                resume_download=True,
            )
        else:
            self.logger(f"Whisper {model_size} найден локально.")

        progress_callback(55, "Проверка pyannote...")

        if not (pyannote_dir / "config.yaml").exists():
            self.logger("Модель pyannote не найдена, запускаю загрузку...", "warning")
            progress_callback(65, "Скачивание pyannote diarization...")
            snapshot_download(
                repo_id="pyannote/speaker-diarization-3.1",
                local_dir=str(pyannote_dir),
                local_dir_use_symlinks=False,
                token=self.hf_token or None,
                resume_download=True,
            )
        else:
            self.logger("pyannote найдена локально.")

        progress_callback(100, "Модели готовы")
        return {
            "whisper_dir": whisper_dir,
            "pyannote_dir": pyannote_dir,
        }
