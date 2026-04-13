import gc
import os
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Callable, Dict, List, Any

import torch
import torchaudio
import pyannote.audio.core.io as pyannote_io
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline

from utils import TranscriptLine, FileTranscriptionResult, timestamp_now


class _TorchaudioDecoder:
    def __init__(self, file_path):
        info = torchaudio.info(str(file_path))
        self.metadata = type(
            "AudioMeta",
            (),
            {
                "duration": info.num_frames / float(info.sample_rate or 1),
                "sample_rate": info.sample_rate,
                "num_channels": info.num_channels,
                "bits_per_sample": 16,
            },
        )()


# Критический патч совместимости pyannote + torchaudio (без av)
pyannote_io.AudioDecoder = _TorchaudioDecoder


class TranscriptionEngine:
    def __init__(
        self,
        whisper_model_dir: Path,
        diarization_model_dir: Path,
        hf_token: str,
        cpu_threads: int,
        model_size: str,
        vad_enabled: bool,
        logger: Callable[[str, str], None],
        beam_size: int = 5,
    ) -> None:
        self.whisper_model_dir = whisper_model_dir
        self.diarization_model_dir = diarization_model_dir
        self.hf_token = hf_token
        self.cpu_threads = max(1, int(cpu_threads))
        self.model_size = model_size
        self.vad_enabled = vad_enabled
        self.beam_size = max(1, int(beam_size))
        self.logger = logger

        self.whisper_model: WhisperModel | None = None
        self.diarization_pipeline: Pipeline | None = None
        self._stop_requested = threading.Event()

    def request_stop(self) -> None:
        self._stop_requested.set()
        self.logger("Получен сигнал остановки...")

    def load_models(self) -> None:
        self.logger("Загрузка faster-whisper в память...")
        self.whisper_model = WhisperModel(
            str(self.whisper_model_dir),
            device="cpu",
            compute_type="int8",
            cpu_threads=self.cpu_threads,
        )
        self.logger("Whisper успешно инициализирован.")

        self.logger("Загрузка pyannote diarization в память...")
        config_path = self.diarization_model_dir / "config.yaml"
        if not config_path.exists():
            raise FileNotFoundError(
                f"Не найден локальный конфиг pyannote: {config_path}"
            )
        # В Windows передаем POSIX-вид пути до config.yaml, чтобы pyannote
        # однозначно воспринимал источник как локальный файл, а не repo_id.
        model_ref = config_path.as_posix()
        token = self.hf_token.strip() if self.hf_token else ""
        # Совместимость с разными версиями pyannote:
        # где-то поддерживается `token`, где-то `use_auth_token`, а где-то ни один.
        if token:
            try:
                self.diarization_pipeline = Pipeline.from_pretrained(
                    model_ref,
                    token=token,
                )
            except TypeError:
                try:
                    self.diarization_pipeline = Pipeline.from_pretrained(
                        model_ref,
                        use_auth_token=token,
                    )
                except TypeError:
                    self.diarization_pipeline = Pipeline.from_pretrained(model_ref)
        else:
            self.diarization_pipeline = Pipeline.from_pretrained(model_ref)
        self.diarization_pipeline.to(torch.device("cpu"))
        self.logger("Pyannote успешно инициализирован.")

    def transcribe_file(self, file_path: Path) -> FileTranscriptionResult:
        return self.transcribe_file_with_progress(file_path, None, None)

    def transcribe_file_with_progress(
        self,
        file_path: Path,
        progress_callback: Callable[[str, float], None] | None,
        time_callback: Callable[[str], None] | None,
    ) -> FileTranscriptionResult:
        self._stop_requested.clear()

        if self.whisper_model is None or self.diarization_pipeline is None:
            raise RuntimeError("Модели не загружены. Вызовите load_models().")

        self.logger(f"Обработка файла: {file_path.name}")
        file_start_time = time.perf_counter()
        processing_input = self._prepare_audio_for_processing(file_path)

        if self._stop_requested.is_set():
            raise InterruptedError("Обработка прервана пользователем")

        if progress_callback:
            progress_callback("Подготовка аудио", 0.1)

        # Получаем длительность аудио для оценки времени
        audio_duration = 0
        try:
            info = torchaudio.info(str(processing_input))
            audio_duration = info.num_frames / float(info.sample_rate or 1)
        except Exception:
            pass

        # Эмпирическая оценка: ~0.3x реального времени для faster-whisper на CPU
        estimated_total_seconds = audio_duration * 0.3 + 10  # +10s overhead

        segments_iter, info = self.whisper_model.transcribe(
            str(processing_input),
            language="ru",
            beam_size=self.beam_size,
            vad_filter=self.vad_enabled,
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=True,
        )

        if self._stop_requested.is_set():
            raise InterruptedError("Обработка прервана пользователем")

        segments = list(segments_iter)

        if self._stop_requested.is_set():
            raise InterruptedError("Обработка прервана пользователем")

        elapsed_whisper = time.perf_counter() - file_start_time
        if progress_callback:
            progress_callback("ASR завершен", 0.55)

        # Обновляем оценку оставшегося времени
        if time_callback:
            diarization_estimate = estimated_total_seconds * 0.4 - elapsed_whisper
            remaining = max(0, int(diarization_estimate))
            time_callback(self._format_seconds(remaining))

        diarization_start = time.perf_counter()
        diarization = self.diarization_pipeline(str(processing_input))
        elapsed_diarization = time.perf_counter() - diarization_start

        if self._stop_requested.is_set():
            raise InterruptedError("Обработка прервана пользователем")

        if progress_callback:
            progress_callback("Диаризация завершена", 0.85)

        if time_callback:
            merge_estimate = estimated_total_seconds * 0.05
            remaining = max(0, int(merge_estimate))
            time_callback(self._format_seconds(remaining))

        merged = self._merge_diarization(segments, diarization)

        if self._stop_requested.is_set():
            raise InterruptedError("Обработка прервана пользователем")

        if progress_callback:
            progress_callback("Сегменты объединены", 0.95)

        if time_callback:
            time_callback("00:00")

        result = FileTranscriptionResult(
            source_file=str(file_path),
            created_at=timestamp_now(),
            language=info.language if info and info.language else "ru",
            model_size=self.model_size,
            vad_enabled=self.vad_enabled,
            items=merged,
        )

        self._cleanup_memory()
        if progress_callback:
            progress_callback("Файл обработан", 1.0)
        if processing_input != file_path:
            try:
                processing_input.unlink(missing_ok=True)
            except Exception:
                self.logger(f"Не удалось удалить временный файл: {processing_input}", "warning")
        return result

    def _format_seconds(self, seconds: int) -> str:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes:02d}:{secs:02d}"

    def _prepare_audio_for_processing(self, file_path: Path) -> Path:
        # Для проблемных MP3/M4A на Windows принудительно переводим в PCM WAV,
        # чтобы исключить ошибки декодера mpg123 в pyannote/torchaudio.
        if file_path.suffix.lower() not in {".mp3", ".m4a"}:
            return file_path

        ffmpeg_bin = self._resolve_ffmpeg_executable()
        if not ffmpeg_bin:
            raise RuntimeError(
                "ffmpeg не найден. В C:\\ffmpeg-8.1 обнаружены исходники, но нет ffmpeg.exe. "
                "Установите бинарную сборку ffmpeg (где есть ffmpeg.exe) или выполните "
                "'pip install imageio-ffmpeg' и перезапустите приложение."
            )
            return file_path

        tmp_dir = Path(tempfile.gettempdir())
        tmp_wav = tmp_dir / f"{file_path.stem}_diar_{uuid.uuid4().hex[:8]}.wav"
        command = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(file_path),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(tmp_wav),
        ]
        try:
            subprocess.run(
                command,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            self.logger(f"Подготовлен WAV для обработки: {tmp_wav.name}")
            return tmp_wav
        except subprocess.CalledProcessError as exc:
            stderr_text = (exc.stderr or b"").decode("utf-8", errors="ignore").strip()
            raise RuntimeError(
                "Ошибка ffmpeg при конвертации аудио в WAV. "
                f"Файл: {file_path.name}. Детали: {stderr_text[:500]}"
            ) from exc

    def _resolve_ffmpeg_executable(self) -> str | None:
        # 1) системный PATH
        ffmpeg_bin = shutil.which("ffmpeg")
        if ffmpeg_bin:
            return ffmpeg_bin

        # 2) явно заданный путь от пользователя
        env_raw = os.environ.get("FFMPEG_PATH", "")
        env_path = Path(env_raw).expanduser() if env_raw else None
        if env_path:
            if env_path.is_file():
                return str(env_path)
            candidate = env_path / "ffmpeg.exe"
            if candidate.exists():
                return str(candidate)
            candidate = env_path / "bin" / "ffmpeg.exe"
            if candidate.exists():
                return str(candidate)

        # 3) попытка через пакет imageio-ffmpeg (скачивает/хранит бинарник)
        try:
            from imageio_ffmpeg import get_ffmpeg_exe

            exe = get_ffmpeg_exe()
            if exe and Path(exe).exists():
                return exe
        except Exception:
            return None

        return None

    def _merge_diarization(self, segments, diarization) -> List[TranscriptLine]:
        merged: List[TranscriptLine] = []

        speaker_map: Dict[str, str] = {}
        next_letter = 0

        for segment in segments:
            text = (segment.text or "").strip()
            if not text:
                continue
            text = self._postprocess_text(text)

            seg_start = float(segment.start)
            seg_end = float(segment.end)

            overlaps: Dict[str, float] = {}
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                overlap = min(seg_end, turn.end) - max(seg_start, turn.start)
                if overlap > 0:
                    overlaps[speaker] = overlaps.get(speaker, 0.0) + float(overlap)

            if overlaps:
                best_speaker = max(overlaps, key=overlaps.get)
            else:
                best_speaker = "UNKNOWN"

            if best_speaker not in speaker_map and best_speaker != "UNKNOWN":
                letter = chr(ord("A") + next_letter)
                speaker_map[best_speaker] = f"Спикер {letter}"
                next_letter += 1

            merged.append(
                TranscriptLine(
                    start=round(seg_start, 2),
                    end=round(seg_end, 2),
                    speaker=speaker_map.get(best_speaker, "Спикер ?"),
                    text=text,
                )
            )

        return merged

    def _cleanup_memory(self) -> None:
        gc.collect()

    def _postprocess_text(self, text: str) -> str:
        # Легкая доменная коррекция для типичных ошибок в сантехнических звонках.
        replacements = {
            "эс мес": "смес",
            "смесетиль": "смеситель",
            "смиситель": "смеситель",
            "мой ка": "мойка",
            "раковен": "раковин",
            "сифонн": "сифон",
            "резиба": "резьба",
            "протечк": "протечк",
            "р м с": "РМС",
        }
        normalized = text
        low = normalized.lower()
        for src, target in replacements.items():
            if src in low:
                low = low.replace(src, target)
        if "рмс" in low:
            low = low.replace("рмс", "РМС")
        # Возвращаем мягко нормализованный вариант без агрессивной пунктуации.
        return low[0].upper() + low[1:] if low else text
