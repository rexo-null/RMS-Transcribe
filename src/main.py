import os
import sys
import warnings
from pathlib import Path

# Hide console window on Windows when running as GUI app
if sys.platform == "win32" and sys.stdout and not sys.stdout.isatty():
    try:
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    except Exception:
        pass

from dotenv import load_dotenv

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings(
    "ignore",
    message=".*torchaudio\\._backend\\.set_audio_backend has been deprecated.*",
    category=UserWarning,
)
warnings.filterwarnings(
    "ignore",
    message=".*torchaudio\\._backend\\.get_audio_backend has been deprecated.*",
    category=UserWarning,
)
warnings.filterwarnings(
    "ignore",
    message=".*speechbrain\\.pretrained.*deprecated.*",
    category=UserWarning,
)
warnings.filterwarnings(
    "ignore",
    message=".*AudioMetaData.*has been moved to.*torchaudio\\.AudioMetaData.*",
    category=UserWarning,
)
warnings.filterwarnings(
    "ignore",
    message=".*MPEG_LAYER_III subtype is unknown to TorchAudio.*",
    category=UserWarning,
)
warnings.filterwarnings(
    "ignore",
    message=".*std\\(\\): degrees of freedom is <= 0.*",
    category=UserWarning,
)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("PYTHONUTF8", "1")
# Workaround for Windows OpenMP runtime collision (torch/onnx/numba deps).
# Позволяет приложению продолжать работу при дублировании libiomp5md.dll.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
# Явно добавляем ffmpeg в PATH для стабильной конвертации MP3 -> WAV.
ffmpeg_root = Path(r"C:\ffmpeg-8.1")
ffmpeg_bin = ffmpeg_root / "bin"
if ffmpeg_bin.exists():
    os.environ["PATH"] = f"{ffmpeg_bin};{os.environ.get('PATH', '')}"
elif ffmpeg_root.exists():
    os.environ["PATH"] = f"{ffmpeg_root};{os.environ.get('PATH', '')}"

from ui_manager import UIManager, create_root
from token_manager import TokenManager, request_token_if_needed

APP_VERSION = "1.0.2"

def main():
    # Use user data directory for models/results (not Program Files)
    base_dir = Path(os.getenv("APPDATA", os.path.expanduser("~"))) / "RMS-Transcribe"
    base_dir.mkdir(parents=True, exist_ok=True)

    # Load .env from installation directory (read-only)
    install_dir = Path(__file__).resolve().parent
    load_dotenv(install_dir / ".env")

    # Создаем менеджер токенов и проверяем его наличие
    token_manager = TokenManager(install_dir)
    
    root = create_root()
    
    # Проверяем наличие токена и запрашиваем если нужно
    hf_token = request_token_if_needed(root, token_manager)
    
    app = UIManager(root=root, base_dir=base_dir, hf_token=hf_token or "", app_version=APP_VERSION)

    if not hf_token:
        app.log("HF токен не указан. Некоторые функции (pyannote) могут быть недоступны.", "warning")
    else:
        app.log("HF токен успешно загружен.")

    close_wait_logged = {"value": False}

    def wait_and_close():
        if app.is_processing:
            root.after(500, wait_and_close)
            return
        root.destroy()

    def on_close():
        if app.is_processing:
            app.on_stop_requested()
            if not close_wait_logged["value"]:
                app.log("Ожидание завершения обработки аудио перед выходом...")
                close_wait_logged["value"] = True
            root.after(500, wait_and_close)
            return
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
