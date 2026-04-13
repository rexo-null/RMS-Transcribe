import json
import os
import queue
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False

from model_manager import ModelManager
from transcription_engine import TranscriptionEngine
from utils import ensure_dirs, export_result_files, format_time, is_supported_audio, make_logger, to_readable_text


QUALITY_PRESETS = {
    "Быстро": {"model_size": "small", "beam_size": 3},
    "Баланс": {"model_size": "medium", "beam_size": 5},
    "Максимум качества": {"model_size": "large-v3", "beam_size": 6},
}


class UIManager:
    def __init__(self, root, base_dir: Path, hf_token: str, app_version: str = "1.0.0"):
        self.root = root
        self.base_dir = base_dir
        self.hf_token = hf_token
        self.app_version = app_version

        self.paths = ensure_dirs(base_dir)
        self.event_queue: queue.Queue[Dict[str, Any]] = queue.Queue()
        self.log = make_logger(self._push_event, self.paths["results"] / "logs" / "app.log")

        self.model_manager = ModelManager(self.paths["models"], hf_token, self.log)
        self.engine: TranscriptionEngine | None = None

        self.file_queue: List[Path] = []
        self.results_by_file: Dict[str, Any] = {}
        self.file_state: Dict[str, Dict[str, Any]] = {}
        self.is_processing = False
        self._stop_requested = False

        self._build_ui()
        self._set_controls_idle()
        self._poll_events()
        self._refresh_model_status()

    def _build_ui(self):
        self.root.title("RMS Transcribe Desktop")
        self.root.geometry("1360x860")
        self.root.minsize(1180, 760)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        try:
            self.root.configure(bg="#171a1f")
        except Exception:
            pass

        self.root.grid_columnconfigure(0, weight=45)
        self.root.grid_columnconfigure(1, weight=55)
        self.root.grid_rowconfigure(1, weight=1)

        self.top_frame = ctk.CTkFrame(self.root, corner_radius=12)
        self.top_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=10, pady=(10, 8))
        self.top_frame.grid_columnconfigure(1, weight=1)
        self.top_frame.grid_columnconfigure(2, weight=0)

        self.models_status_label = ctk.CTkLabel(self.top_frame, text="Модели: статус неизвестен")
        self.models_status_label.grid(row=0, column=0, padx=12, pady=10, sticky="w")

        self.download_models_button = ctk.CTkButton(
            self.top_frame,
            text="Проверить/загрузить модели",
            command=self.on_check_models,
        )
        self.download_models_button.grid(row=0, column=1, padx=12, pady=10, sticky="e")
        self.version_label = ctk.CTkLabel(self.top_frame, text=f"v{self.app_version}", text_color="#9aa4b2")
        self.version_label.grid(row=0, column=2, padx=(0, 8), pady=10, sticky="e")

        self.instruction_button = ctk.CTkButton(
            self.top_frame,
            text="Инструкция",
            command=self._show_instructions,
            width=100,
        )
        self.instruction_button.grid(row=0, column=3, padx=(0, 12), pady=10, sticky="e")

        self.global_progress = ctk.CTkProgressBar(self.top_frame, progress_color="#3b82f6")
        self.global_progress.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 8))
        self.global_progress.set(0)

        self.global_progress_text = ctk.CTkLabel(self.top_frame, text="Прогресс: 0%")
        self.global_progress_text.grid(row=2, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 10))

        self.left_frame = ctk.CTkFrame(self.root, corner_radius=12)
        self.left_frame.grid(row=1, column=0, sticky="nsew", padx=(10, 6), pady=(0, 10))
        self.left_frame.grid_columnconfigure(0, weight=1)
        self.left_frame.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self.left_frame, text="Очередь файлов", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 8)
        )

        queue_buttons = ctk.CTkFrame(self.left_frame)
        queue_buttons.grid(row=1, column=0, sticky="ew", padx=12)
        queue_buttons.grid_columnconfigure((0, 1, 2), weight=1)

        self.add_files_button = ctk.CTkButton(queue_buttons, text="Добавить", command=self.on_add_files)
        self.add_files_button.grid(row=0, column=0, padx=4, pady=6, sticky="ew")

        self.remove_file_button = ctk.CTkButton(queue_buttons, text="Удалить", command=self.on_remove_selected)
        self.remove_file_button.grid(row=0, column=1, padx=4, pady=6, sticky="ew")

        self.clear_queue_button = ctk.CTkButton(queue_buttons, text="Очистить", command=self.on_clear_queue)
        self.clear_queue_button.grid(row=0, column=2, padx=4, pady=6, sticky="ew")

        table_frame = ctk.CTkFrame(self.left_frame)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(8, 6))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Queue.Treeview", background="#1f242d", fieldbackground="#1f242d", foreground="#e8eaed", rowheight=26)
        style.configure("Queue.Treeview.Heading", background="#2a313d", foreground="#f1f5f9")
        style.map("Queue.Treeview", background=[("selected", "#2d6cdf")], foreground=[("selected", "#ffffff")])

        self.queue_tree = ttk.Treeview(
            table_frame,
            columns=("file", "status", "progress", "remaining_time"),
            show="headings",
            style="Queue.Treeview",
            selectmode="browse",
        )
        self.queue_tree.heading("file", text="Файл")
        self.queue_tree.heading("status", text="Статус")
        self.queue_tree.heading("progress", text="Прогресс")
        self.queue_tree.heading("remaining_time", text="Осталось")
        self.queue_tree.column("file", width=280, anchor="w")
        self.queue_tree.column("status", width=110, anchor="center")
        self.queue_tree.column("progress", width=70, anchor="center")
        self.queue_tree.column("remaining_time", width=90, anchor="center")
        self.queue_tree.grid(row=0, column=0, sticky="nsew")

        tree_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.queue_tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.queue_tree.configure(yscrollcommand=tree_scroll.set)

        settings_frame = ctk.CTkFrame(self.left_frame)
        settings_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 12))
        settings_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(settings_frame, text="Профиль качества", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 4)
        )
        self.quality_var = ctk.StringVar(value="Максимум качества")
        self.quality_menu = ctk.CTkOptionMenu(
            settings_frame,
            variable=self.quality_var,
            values=list(QUALITY_PRESETS.keys()),
            command=lambda _: self._refresh_model_status(),
        )
        self.quality_menu.grid(row=0, column=1, sticky="ew", padx=10, pady=(10, 4))

        cpu_default = self._recommended_cpu_threads()
        self.cpu_info_label = ctk.CTkLabel(
            settings_frame,
            text=f"CPU потоки: авто ({cpu_default}) | VAD: всегда включен",
            text_color="#aeb8c5",
        )
        self.cpu_info_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))

        self.show_advanced = ctk.BooleanVar(value=False)
        self.advanced_toggle = ctk.CTkSwitch(
            settings_frame,
            text="Расширенные настройки",
            variable=self.show_advanced,
            command=self._toggle_advanced_settings,
        )
        self.advanced_toggle.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 8))

        self.advanced_frame = ctk.CTkFrame(settings_frame)
        self.advanced_frame.grid_columnconfigure(1, weight=1)

        self.manual_override_var = ctk.BooleanVar(value=False)
        self.manual_override_check = ctk.CTkCheckBox(
            self.advanced_frame,
            text="Использовать ручные параметры",
            variable=self.manual_override_var,
        )
        self.manual_override_check.grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 6))

        ctk.CTkLabel(self.advanced_frame, text="Модель Whisper").grid(row=1, column=0, sticky="w", padx=10, pady=4)
        self.manual_model_var = ctk.StringVar(value="large-v3")
        self.manual_model_menu = ctk.CTkOptionMenu(
            self.advanced_frame,
            variable=self.manual_model_var,
            values=["small", "medium", "large-v3"],
        )
        self.manual_model_menu.grid(row=1, column=1, sticky="ew", padx=10, pady=4)

        ctk.CTkLabel(self.advanced_frame, text="CPU потоки").grid(row=2, column=0, sticky="w", padx=10, pady=4)
        self.manual_cpu_var = ctk.IntVar(value=self._recommended_cpu_threads())
        self.manual_cpu_slider = ctk.CTkSlider(
            self.advanced_frame,
            from_=1,
            to=16,
            number_of_steps=15,
            command=self._on_manual_cpu_change,
        )
        self.manual_cpu_slider.set(self.manual_cpu_var.get())
        self.manual_cpu_slider.grid(row=2, column=1, sticky="ew", padx=10, pady=4)
        self.manual_cpu_label = ctk.CTkLabel(self.advanced_frame, text=str(self.manual_cpu_var.get()))
        self.manual_cpu_label.grid(row=2, column=2, sticky="w", padx=(0, 10))

        self.manual_vad_var = ctk.BooleanVar(value=True)
        self.manual_vad_check = ctk.CTkCheckBox(self.advanced_frame, text="VAD включен", variable=self.manual_vad_var)
        self.manual_vad_check.grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=(6, 10))

        if DND_AVAILABLE and hasattr(self.root, "drop_target_register"):
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>", self._on_drop_files)

        self.right_frame = ctk.CTkFrame(self.root, corner_radius=12)
        self.right_frame.grid(row=1, column=1, sticky="nsew", padx=(6, 10), pady=(0, 10))
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.right_frame, text="Транскрибация", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(12, 8)
        )

        self.transcript_box = ctk.CTkTextbox(self.right_frame, wrap="word")
        self.transcript_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self.transcript_box.configure(state="disabled")
        
        # Добавляем поддержку копирования выделенного текста
        self.transcript_box.bind("<Control-c>", self._copy_transcript_selection)
        self.transcript_box.bind("<Button-3>", self._show_transcript_context_menu)

        action_bar = ctk.CTkFrame(self.right_frame)
        action_bar.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        action_bar.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.start_button = ctk.CTkButton(action_bar, text="Старт", command=self.on_start_processing, fg_color="#2d7bf4")
        self.start_button.grid(row=0, column=0, padx=4, pady=6, sticky="ew")

        self.stop_button = ctk.CTkButton(action_bar, text="Стоп", command=self.on_stop_requested, fg_color="#9c2f45")
        self.stop_button.grid(row=0, column=1, padx=4, pady=6, sticky="ew")

        self.export_json_button = ctk.CTkButton(action_bar, text="Экспорт выбранного JSON", command=self.on_export_json)
        self.export_json_button.grid(row=0, column=2, padx=4, pady=6, sticky="ew")

        self.export_txt_button = ctk.CTkButton(action_bar, text="Экспорт выбранного TXT", command=self.on_export_txt)
        self.export_txt_button.grid(row=0, column=3, padx=4, pady=6, sticky="ew")

        self.save_transcript_button = ctk.CTkButton(action_bar, text="Сохранить транскрибацию", command=self.on_save_transcript)
        self.save_transcript_button.grid(row=0, column=4, padx=(4, 0), pady=6, sticky="ew")

        ctk.CTkLabel(self.right_frame, text="Логи", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=3, column=0, sticky="w", padx=12, pady=(2, 4)
        )

        self.log_box = ctk.CTkTextbox(self.right_frame, height=190)
        self.log_box.grid(row=4, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _recommended_cpu_threads(self) -> int:
        cpus = os.cpu_count() or 4
        return max(2, min(12, cpus - 1))

    def _on_manual_cpu_change(self, value):
        self.manual_cpu_var.set(int(round(value)))
        self.manual_cpu_label.configure(text=str(self.manual_cpu_var.get()))

    def _quality_config(self) -> Dict[str, Any]:
        return QUALITY_PRESETS[self.quality_var.get()]

    def _active_runtime_config(self) -> Dict[str, Any]:
        if self.show_advanced.get() and self.manual_override_var.get():
            return {
                "model_size": self.manual_model_var.get(),
                "beam_size": 6 if self.manual_model_var.get() == "large-v3" else 5,
                "cpu_threads": self.manual_cpu_var.get(),
                "vad_enabled": bool(self.manual_vad_var.get()),
                "profile": "Ручной",
            }
        cfg = self._quality_config()
        return {
            "model_size": cfg["model_size"],
            "beam_size": cfg["beam_size"],
            "cpu_threads": self._recommended_cpu_threads(),
            "vad_enabled": True,
            "profile": self.quality_var.get(),
        }

    def _toggle_advanced_settings(self):
        if self.show_advanced.get():
            self.advanced_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))
        else:
            self.advanced_frame.grid_forget()

    def _push_event(self, event: Dict[str, Any]):
        self.event_queue.put(event)

    def _poll_events(self):
        while not self.event_queue.empty():
            event = self.event_queue.get_nowait()
            etype = event.get("type")

            if etype == "log":
                self._append_log(event["timestamp"], event["message"])
            elif etype == "progress":
                self._set_progress(event.get("value", 0.0), event.get("text", ""))
            elif etype == "transcript_line":
                self._append_transcript_line(event["line"])
            elif etype == "file_status":
                self._update_file_status_view(
                    event["file_path"],
                    event["status"],
                    event["progress"],
                    event.get("remaining_time", "--:--"),
                )
            elif etype == "processing_done":
                self._on_processing_done(event.get("stopped", False))

        self.root.after(100, self._poll_events)

    def _append_log(self, ts: str, message: str):
        self.log_box.insert("end", f"[{ts}] {message}\n")
        self.log_box.see("end")

    def _append_transcript_line(self, line: str):
        self.transcript_box.configure(state="normal")
        self.transcript_box.insert("end", line + "\n")
        self.transcript_box.see("end")
        self.transcript_box.configure(state="disabled")

    def _insert_transcript_header(self, file_path: Path):
        title = f"\n{'=' * 18} {file_path.name} {'=' * 18}\n"
        self._append_transcript_line(title)

    def _set_progress(self, value: float, text: str):
        value = max(0.0, min(100.0, float(value)))
        self.global_progress.set(value / 100.0)
        label = text if text else f"Прогресс: {value:.1f}%"
        self.global_progress_text.configure(text=label)

    def _set_controls_idle(self):
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.add_files_button.configure(state="normal")
        self.remove_file_button.configure(state="normal")
        self.clear_queue_button.configure(state="normal")
        self.download_models_button.configure(state="normal")

    def _set_controls_processing(self):
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.add_files_button.configure(state="disabled")
        self.remove_file_button.configure(state="disabled")
        self.clear_queue_button.configure(state="disabled")
        self.download_models_button.configure(state="disabled")

    def _refresh_model_status(self):
        model_size = self._active_runtime_config()["model_size"]
        status = self.model_manager.check_status(model_size)
        if status["all_ready"]:
            self.models_status_label.configure(text=f"Модели: готовы ({model_size})")
        else:
            parts = []
            parts.append("Whisper OK" if status["whisper"] else "Whisper нет")
            parts.append("Pyannote OK" if status["pyannote"] else "Pyannote нет")
            self.models_status_label.configure(text=f"Модели: {', '.join(parts)} | профиль: {self._active_runtime_config()['profile']}")

    def _update_queue_view(self):
        self.queue_tree.delete(*self.queue_tree.get_children())
        for i, item in enumerate(self.file_queue, start=1):
            path_key = str(item)
            meta = self.file_state.get(path_key, {"status": "В очереди", "progress": 0, "remaining_time": "--:--"})
            iid = path_key
            remaining = meta.get("remaining_time", "--:--")
            self.queue_tree.insert(
                "",
                "end",
                iid=iid,
                values=(f"{i:02d}. {item.name}", meta["status"], f"{meta['progress']:>3d}%", remaining),
            )

    def _set_file_status(self, file_path: Path, status: str, progress: int, remaining_time: str = "--:--"):
        progress = max(0, min(100, int(progress)))
        self.file_state[str(file_path)] = {"status": status, "progress": progress, "remaining_time": remaining_time}
        self._push_event(
            {
                "type": "file_status",
                "file_path": str(file_path),
                "status": status,
                "progress": progress,
                "remaining_time": remaining_time,
            }
        )

    def _update_file_status_view(self, file_path: str, status: str, progress: int, remaining_time: str = "--:--"):
        if self.queue_tree.exists(file_path):
            values = list(self.queue_tree.item(file_path, "values"))
            if len(values) == 4:
                values[1] = status
                values[2] = f"{int(progress):>3d}%"
                values[3] = remaining_time
                self.queue_tree.item(file_path, values=values)
        else:
            self._update_queue_view()

    def on_add_files(self):
        paths = filedialog.askopenfilenames(
            title="Выберите аудиофайлы",
            filetypes=[("Audio", "*.mp3 *.wav *.ogg *.m4a *.flac")],
        )
        self._add_paths_to_queue([Path(p) for p in paths])

    def _on_drop_files(self, event):
        raw = self.root.tk.splitlist(event.data)
        self._add_paths_to_queue([Path(p) for p in raw])

    def _add_paths_to_queue(self, files: List[Path]):
        added = 0
        for file_path in files:
            if file_path.exists() and is_supported_audio(file_path) and file_path not in self.file_queue:
                self.file_queue.append(file_path)
                self.file_state[str(file_path)] = {"status": "В очереди", "progress": 0, "remaining_time": "--:--"}
                added += 1
        self._update_queue_view()
        self.log(f"Добавлено файлов в очередь: {added}")

    def on_remove_selected(self):
        selected = self.queue_tree.selection()
        if not selected:
            messagebox.showinfo("Информация", "Выберите файл в очереди для удаления")
            return

        path = Path(selected[0])
        if path in self.file_queue:
            self.file_queue.remove(path)
        self.file_state.pop(str(path), None)
        self.results_by_file.pop(str(path), None)
        self._update_queue_view()
        self.log(f"Удалён файл из очереди: {path.name}")

    def on_clear_queue(self):
        self.file_queue.clear()
        self.file_state.clear()
        self._update_queue_view()
        self.log("Очередь очищена")

    def on_check_models(self):
        self.download_models_button.configure(state="disabled")
        runtime_cfg = self._active_runtime_config()
        model_size = runtime_cfg["model_size"]

        def worker():
            try:
                self.log(f"Проверка моделей для профиля '{runtime_cfg['profile']}' ({model_size})")
                self.model_manager.ensure_models(
                    model_size=model_size,
                    progress_callback=lambda p, t: self._push_event({"type": "progress", "value": p, "text": t}),
                )
                self.root.after(0, self._refresh_model_status)
                self.log("Проверка/загрузка моделей завершена")
            except Exception as exc:
                self.log(f"Ошибка загрузки моделей: {exc}", "error")
                self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Не удалось загрузить модели:\n{exc}"))
            finally:
                self.root.after(0, lambda: self.download_models_button.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def _build_engine(self) -> TranscriptionEngine:
        cfg = self._active_runtime_config()
        return TranscriptionEngine(
            whisper_model_dir=self.model_manager.get_whisper_dir(cfg["model_size"]),
            diarization_model_dir=self.model_manager.get_pyannote_dir(),
            hf_token=self.hf_token,
            cpu_threads=cfg["cpu_threads"],
            model_size=cfg["model_size"],
            vad_enabled=cfg["vad_enabled"],
            logger=self.log,
            beam_size=cfg["beam_size"],
        )

    def on_start_processing(self):
        if self.is_processing:
            return

        if not self.file_queue:
            messagebox.showwarning("Внимание", "Добавьте файлы в очередь")
            return

        status = self.model_manager.check_status(self._active_runtime_config()["model_size"])
        if not status["all_ready"]:
            messagebox.showwarning("Модели не готовы", "Сначала проверьте/загрузите модели")
            return

        self.is_processing = True
        self._stop_requested = False
        self._set_controls_processing()

        self.transcript_box.configure(state="normal")
        self.transcript_box.delete("1.0", "end")
        self.transcript_box.configure(state="disabled")
        self.results_by_file.clear()
        self._set_progress(0, "Запуск пакетной обработки...")

        def worker():
            try:
                total_start = time.perf_counter()
                self.engine = self._build_engine()
                self.log("Инициализация моделей в памяти...")
                self.engine.load_models()
                self.log("Модели загружены, старт пакетной обработки")

                total = len(self.file_queue)
                for idx, file_path in enumerate(self.file_queue, start=1):
                    if self._stop_requested:
                        self.log("Остановка запрошена пользователем")
                        break

                    file_start = time.perf_counter()
                    self._insert_transcript_header(file_path)
                    self._set_file_status(file_path, "В работе", 0, "~01:00")

                    base = (idx - 1) / total
                    weight = 1 / total
                    self._push_event(
                        {
                            "type": "progress",
                            "value": base * 100,
                            "text": f"Файл {idx}/{total}: {file_path.name} (0%)",
                        }
                    )
                    self.log(f"Старт файла {idx}/{total}: {file_path.name}")

                    def time_callback(remaining_str: str):
                        self._set_file_status(file_path, "В работе", int((base + weight * 0.5) * 100), remaining_str)

                    def stage_progress(stage_text: str, stage_value: float):
                        stage_value = max(0.0, min(1.0, stage_value))
                        overall = (base + weight * stage_value) * 100
                        self._set_file_status(file_path, stage_text, int(stage_value * 100))
                        self._push_event(
                            {
                                "type": "progress",
                                "value": overall,
                                "text": f"Файл {idx}/{total}: {file_path.name} - {stage_text}",
                            }
                        )

                    try:
                        result = self.engine.transcribe_file_with_progress(file_path, stage_progress, time_callback)
                        self.results_by_file[str(file_path)] = result

                        total_items = len(result.items)
                        for line_idx, item in enumerate(result.items, start=1):
                            line = f"[{format_time(item.start)}-{format_time(item.end)}] {item.speaker}: {item.text}"
                            self._push_event({"type": "transcript_line", "line": line})
                            if line_idx % 20 == 0 or line_idx == total_items:
                                stage_emit = 0.96 + 0.03 * (line_idx / max(1, total_items))
                                self._set_file_status(file_path, "Формирование вывода", int(stage_emit * 100), "00:00")

                        saved = export_result_files(result, self.paths["results"])
                        elapsed = time.perf_counter() - file_start
                        self._set_file_status(file_path, "Готово", 100, "00:00")
                        self.log(
                            f"Готово {file_path.name} за {elapsed:.1f}с | "
                            f"JSON={saved['json'].name}, TXT={saved['txt'].name}, CSV={saved['csv'].name}"
                        )
                    except InterruptedError:
                        self._set_file_status(file_path, "Прервано", 0, "--:--")
                        self.log(f"Обработка файла {file_path.name} прервана")
                        self._push_event({"type": "processing_done", "stopped": True})
                        return

                    self._push_event(
                        {
                            "type": "progress",
                            "value": (idx / total) * 100,
                            "text": f"Обработано {idx}/{total} файлов",
                        }
                    )

                self._push_event({"type": "processing_done", "stopped": self._stop_requested})
                self.log(f"Общее время пакетной обработки: {time.perf_counter() - total_start:.1f}с")
            except Exception as exc:
                self.log(f"Критическая ошибка обработки: {exc}", "error")
                self._push_event({"type": "processing_done", "stopped": True})
                self.root.after(0, lambda err=str(exc): messagebox.showerror("Ошибка", err))

        threading.Thread(target=worker, daemon=True).start()

    def _on_processing_done(self, stopped: bool):
        self.is_processing = False
        self._set_controls_idle()
        if stopped:
            self._set_progress(0, "Обработка остановлена")
        else:
            self._set_progress(100, "Пакетная обработка завершена")
            self.log("Все файлы обработаны")

    def on_stop_requested(self):
        self._stop_requested = True
        self.stop_button.configure(state="disabled")
        self.log("Запрошена остановка... прерывание обработки")
        if self.engine:
            try:
                self.engine.request_stop()
            except Exception:
                pass

    def _get_selected_result(self):
        selected = self.queue_tree.selection()
        if not selected:
            messagebox.showinfo("Информация", "Выберите файл в очереди")
            return None, None

        key = selected[0]
        result = self.results_by_file.get(key)
        if result is None:
            messagebox.showinfo("Информация", "Для выбранного файла пока нет результата")
            return None, None
        return Path(key), result

    def on_export_json(self):
        file_path, result = self._get_selected_result()
        if result is None:
            return

        suggested = f"{file_path.stem}.json"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=suggested,
            filetypes=[("JSON", "*.json")],
        )
        if not save_path:
            return

        target = Path(save_path)
        json_payload = {
            "source_file": result.source_file,
            "created_at": result.created_at,
            "language": result.language,
            "model_size": result.model_size,
            "vad_enabled": result.vad_enabled,
            "items": [asdict(item) for item in result.items],
        }
        target.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self.log(f"JSON экспортирован для {file_path.name}: {target}")

    def on_export_txt(self):
        file_path, result = self._get_selected_result()
        if result is None:
            return

        suggested = f"{file_path.stem}.txt"
        save_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=suggested,
            filetypes=[("TXT", "*.txt")],
        )
        if not save_path:
            return

        target = Path(save_path)
        target.write_text(to_readable_text(result.items), encoding="utf-8")
        self.log(f"TXT экспортирован для {file_path.name}: {target}")
    
    def on_save_transcript(self):
        """Сохраняет всё содержимое окна транскрибации в txt файл"""
        self.transcript_box.configure(state="normal")
        transcript_content = self.transcript_box.get("1.0", "end").strip()
        self.transcript_box.configure(state="disabled")
        
        if not transcript_content:
            messagebox.showinfo("Информация", "Окно транскрибации пустое")
            return
        
        save_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile="transcript.txt",
            filetypes=[("TXT", "*.txt")],
        )
        if not save_path:
            return
        
        target = Path(save_path)
        target.write_text(transcript_content, encoding="utf-8")
        self.log(f"Транскрибация сохранена в файл: {target}")

    def _copy_transcript_selection(self, event=None):
        """Копирует выделенный текст из окна транскрибации"""
        try:
            selected_text = self.transcript_box.selection_get()
            if selected_text:
                self.root.clipboard_clear()
                self.root.clipboard_append(selected_text)
        except Exception:
            pass
        return "break"
    
    def _show_transcript_context_menu(self, event):
        """Показывает контекстное меню для окна транскрибации"""
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Копировать", command=self._copy_transcript_selection)
        context_menu.add_separator()
        context_menu.add_command(label="Выделить всё", command=self._select_all_transcript)
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def _select_all_transcript(self):
        """Выделяет весь текст в окне транскрибации"""
        self.transcript_box.configure(state="normal")
        self.transcript_box.tag_add("sel", "1.0", "end")
        self.transcript_box.configure(state="disabled")
    
    def _show_instructions(self):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Инструкция по использованию")
        dialog.geometry("700x550")
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=0)

        textbox = ctk.CTkTextbox(dialog, wrap="word", font=ctk.CTkFont(size=12))
        textbox.grid(row=0, column=0, sticky="nsew", padx=15, pady=(15, 10))

        instructions = """ИНСТРУКЦИЯ ПО ИСПОЛЬЗОВАНИЮ RMS Transcribe

1. ПОДГОТОВКА
   • Нажмите кнопку "Проверить/загрузить модели"
   • Дождитесь статуса "Модели: готовы" в верхней части окна
   • При первом запуске модели скачиваются автоматически (требуется интернет)

2. ДОБАВЛЕНИЕ АУДИОФАЙЛОВ
   • Нажмите "Добавить" или перетащите файлы мышью в окно приложения
   • Поддерживаемые форматы: MP3, WAV, OGG, M4A, FLAC
   • Файлы отображаются в очереди со статусом и прогрессом

3. ВЫБОР ПРОФИЛЯ КАЧЕСТВА
   • Быстро — высокая скорость, базовое качество
   • Баланс — оптимальное соотношение скорость/качество
   • Максимум качества — лучшее качество распознавания (медленнее)

4. РАСШИРЕННЫЕ НАСТРОЙКИ (опционально)
   • Включите переключатель "Расширенные настройки"
   • Можно задать модель вручную, количество CPU потоков, включить/выключить VAD

5. ЗАПУСК ОБРАБОТКИ
   • Нажмите кнопку "Старт"
   • В правом окне отображается транскрибация в реальном времени
   • Внизу показываются детальные логи процесса
   • В таблице очереди виден прогресс и оставшееся время по каждому файлу

6. УПРАВЛЕНИЕ ВО ВРЕМЯ РАБОТЫ
   • Кнопка "Стоп" — немедленно прерывает обработку текущего файла
   • При закрытии окна приложение корректно завершит текущий файл

7. ЭКСПОРТ РЕЗУЛЬТАТОВ
   • Выберите файл в таблице очереди (кликните на него)
   • Нажмите "Экспорт выбранного JSON" или "Экспорт выбранного TXT"
   • Результаты автоматически сохраняются в папку results/ в форматах JSON, TXT, CSV

8. СОВЕТЫ
   • Для длинных файлов используйте профиль "Быстро"
   • Для важных записей рекомендуется "Максимум качества"
   • VAD (Voice Activity Detection) автоматически пропускает тишину

По вопросам и проблемам обращайтесь к документации в папке docs/"""

        textbox.insert("1.0", instructions)
        textbox.configure(state="disabled")

        close_btn = ctk.CTkButton(dialog, text="Закрыть", command=dialog.destroy, width=120)
        close_btn.grid(row=1, column=0, pady=(0, 15))

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")



def create_root():
    if DND_AVAILABLE:
        return TkinterDnD.Tk()
    return ctk.CTk()
