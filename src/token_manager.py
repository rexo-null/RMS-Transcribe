import os
import webbrowser
from pathlib import Path
from typing import Optional, Callable

import customtkinter as ctk


class TokenManager:
    def __init__(self, install_dir: Path):
        self.install_dir = install_dir
        self.env_file = install_dir / ".env"
    
    def load_token(self) -> str:
        """Загружает токен из .env файла"""
        from dotenv import load_dotenv
        load_dotenv(self.env_file)
        return os.getenv("HUGGING_FACE_TOKEN", "").strip()
    
    def save_token(self, token: str) -> bool:
        """Сохраняет токен в .env файл"""
        try:
            token = token.strip()
            if not token:
                return False
            
            # Читаем текущий файл
            lines = []
            if self.env_file.exists():
                lines = self.env_file.read_text(encoding="utf-8").splitlines()
            
            # Находим и заменяем строку с токеном
            token_found = False
            for i, line in enumerate(lines):
                if line.strip().startswith("HUGGING_FACE_TOKEN="):
                    lines[i] = f"HUGGING_FACE_TOKEN={token}"
                    token_found = True
                    break
            
            # Если токен не найден, добавляем его
            if not token_found:
                lines.append(f"HUGGING_FACE_TOKEN={token}")
            
            # Записываем обратно
            self.env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return True
        except Exception:
            return False
    
    def has_token(self) -> bool:
        """Проверяет наличие токена"""
        token = self.load_token()
        return bool(token and len(token) > 10)  # Базовая проверка длины токена


class TokenInputDialog:
    def __init__(self, parent, on_token_saved: Optional[Callable[[str], None]] = None):
        self.parent = parent
        self.on_token_saved = on_token_saved
        self.token_var = ctk.StringVar()
        self.result = None
        
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Требуется токен Hugging Face")
        self.dialog.geometry("550x500")
        self.dialog.resizable(False, False)  # Фиксированный размер
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Центрирование окна
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (550 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (500 // 2)
        self.dialog.geometry(f"550x500+{x}+{y}")
        
        self._build_ui()
    
    def _build_ui(self):
        self.dialog.grid_columnconfigure(0, weight=1)
        self.dialog.grid_rowconfigure(3, weight=1)
        
        # Заголовок
        title_frame = ctk.CTkFrame(self.dialog)
        title_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        title_frame.grid_columnconfigure(0, weight=1)
        
        title_label = ctk.CTkLabel(
            title_frame,
            text="🔑 Требуется токен Hugging Face",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.grid(row=0, column=0, pady=15)
        
        # Информационный текст
        info_frame = ctk.CTkFrame(self.dialog)
        info_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        info_frame.grid_columnconfigure(0, weight=1)
        
        info_text = """Для работы с моделями диаризации (разделения по дикторам) требуется токен доступа к Hugging Face.

Пожалуйста, получите токен и введите его в поле ниже."""
        
        info_label = ctk.CTkLabel(
            info_frame,
            text=info_text,
            font=ctk.CTkFont(size=12),
            wraplength=480
        )
        info_label.grid(row=0, column=0, padx=15, pady=12)
        
        # Ссылки
        links_frame = ctk.CTkFrame(self.dialog)
        links_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        links_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Ссылка на Hugging Face
        hf_link = ctk.CTkButton(
            links_frame,
            text="🌐 Hugging Face",
            command=lambda: webbrowser.open("https://huggingface.co"),
            fg_color="#1f2937",
            hover_color="#374151",
            text_color="#60a5fa"
        )
        hf_link.grid(row=0, column=0, padx=(15, 5), pady=12, sticky="ew")
        
        # Ссылка на инструкцию
        instruction_link = ctk.CTkButton(
            links_frame,
            text="📖 Инструкция по созданию токена",
            command=self._show_instruction,
            fg_color="#1f2937",
            hover_color="#374151",
            text_color="#60a5fa"
        )
        instruction_link.grid(row=0, column=1, padx=(5, 15), pady=12, sticky="ew")
        
        # Поле ввода токена
        input_frame = ctk.CTkFrame(self.dialog)
        input_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 10))
        input_frame.grid_columnconfigure(0, weight=1)
        
        token_label = ctk.CTkLabel(
            input_frame,
            text="Введите ваш токен Hugging Face:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        token_label.grid(row=0, column=0, padx=15, pady=(12, 5), sticky="w")
        
        self.token_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.token_var,
            placeholder_text="hf_...",
            show="*",
            font=ctk.CTkFont(size=11),
            height=35
        )
        self.token_entry.grid(row=1, column=0, padx=15, pady=(0, 5), sticky="ew")
        
        # Кнопка показать/скрыть токен
        self.show_token_var = ctk.BooleanVar(value=False)
        show_token_check = ctk.CTkCheckBox(
            input_frame,
            text="Показать токен",
            variable=self.show_token_var,
            command=self._toggle_token_visibility
        )
        show_token_check.grid(row=2, column=0, padx=15, pady=(0, 12), sticky="w")
        
        # Кнопки действий
        buttons_frame = ctk.CTkFrame(self.dialog)
        buttons_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 20))
        buttons_frame.grid_columnconfigure((0, 1), weight=1)
        
        save_button = ctk.CTkButton(
            buttons_frame,
            text="💾 Сохранить токен",
            command=self._save_token,
            fg_color="#10b981",
            hover_color="#059669",
            height=40
        )
        save_button.grid(row=0, column=0, padx=(15, 5), pady=12, sticky="ew")
        
        skip_button = ctk.CTkButton(
            buttons_frame,
            text="⏭️ Пропустить",
            command=self._skip,
            fg_color="#6b7280",
            hover_color="#4b5563",
            height=40
        )
        skip_button.grid(row=0, column=1, padx=(5, 15), pady=12, sticky="ew")
        
        # Фокус на поле ввода
        self.token_entry.focus()
        self.token_entry.bind("<Return>", lambda e: self._save_token())
    
    def _toggle_token_visibility(self):
        if self.show_token_var.get():
            self.token_entry.configure(show="")
        else:
            self.token_entry.configure(show="*")
    
    def _save_token(self):
        from tkinter import messagebox
        token = self.token_var.get().strip()
        if not token:
            messagebox.showwarning("Внимание", "Пожалуйста, введите токен")
            return
        
        if len(token) < 10:
            messagebox.showwarning("Внимание", "Токен кажется слишком коротким")
            return
        
        self.result = token
        if self.on_token_saved:
            self.on_token_saved(token)
        self.dialog.destroy()
    
    def _skip(self):
        self.result = None
        self.dialog.destroy()
    
    def _show_instruction(self):
        self._show_instruction_dialog()
    
    def _show_instruction_dialog(self):
        instruction_dialog = ctk.CTkToplevel(self.dialog)
        instruction_dialog.title("Инструкция по созданию токена")
        instruction_dialog.geometry("600x650")
        instruction_dialog.resizable(False, False)  # Фиксированный размер
        instruction_dialog.transient(self.dialog)
        instruction_dialog.grab_set()
        
        # Центрирование окна
        instruction_dialog.update_idletasks()
        x = (instruction_dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (instruction_dialog.winfo_screenheight() // 2) - (650 // 2)
        instruction_dialog.geometry(f"600x650+{x}+{y}")
        
        instruction_dialog.grid_columnconfigure(0, weight=1)
        instruction_dialog.grid_rowconfigure(0, weight=1)
        instruction_dialog.grid_rowconfigure(1, weight=0)
        
        # Текст инструкции
        textbox = ctk.CTkTextbox(instruction_dialog, wrap="word", font=ctk.CTkFont(size=11))
        textbox.grid(row=0, column=0, sticky="nsew", padx=15, pady=(15, 10))
        
        instruction_text = """ИНСТРУКЦИЯ ПО СОЗДАНИЮ ТОКЕНА HUGGING FACE

1. 🌐 РЕГИСТРАЦИЯ НА HUGGING FACE
   • Перейдите на сайт https://huggingface.co
   • Нажмите "Sign Up" для регистрации или "Sign In" для входа
   • Подтвердите email, если требуется

2. 🔑 СОЗДАНИЕ ТОКЕНА
   • После входа нажмите на свой профиль в правом верхнем углу
   • Выберите "Settings" (Настройки)
   • В меню слева выберите "Access Tokens" (Токены доступа)
   • Нажмите "New token" (Создать токен)

3. ⚙️ НАСТРОЙКА ТОКЕНА
   • Имя: введите любое имя (например, "RMS-Transcribe")
   • Тип: выберите "Read" (Чтение)
   • Оставьте другие настройки по умолчанию
   • Нажмите "Generate a token"

4. 📋 КОПИРОВАНИЕ ТОКЕНА
   • Сразу скопируйте сгенерированный токен
   • Токен начинается с "hf_"
   • Сохраните его в надежном месте
   • ⚠️ ВНИМАНИЕ: токен будет показан только один раз!

5. 🔄 ИСПОЛЬЗОВАНИЕ ТОКЕНА
   • Вернитесь в приложение RMS-Transcribe
   • Вставьте токен в поле ввода
   • Нажмите "Сохранить токен"

6. ✅ ПРОВЕРКА
   • После сохранения токена приложение сможет скачивать модели
   • Токен сохраняется в файле .env в директории программы
   • Повторный ввод не потребуется при следующих запусках

📝 ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ:
• Токен с правами "Read" позволяет скачивать публичные модели
• Для pyannote требуются права доступа к приватным репозиториям
• Если возникнут проблемы, можно создать новый токен с правами "Write"
• Никогда не делитесь своим токеном с другими пользователями

🔗 ПОЛЕЗНЫЕ ССЫЛКИ:
• Hugging Face: https://huggingface.co
• Управление токенами: https://huggingface.co/settings/tokens
• Документация по токенам: https://huggingface.co/docs/hub/security-tokens"""
        
        textbox.insert("1.0", instruction_text)
        textbox.configure(state="disabled")
        
        # Кнопка закрытия
        close_button = ctk.CTkButton(
            instruction_dialog,
            text="Закрыть",
            command=instruction_dialog.destroy,
            height=40
        )
        close_button.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="ew")
    
    def get_result(self) -> Optional[str]:
        """Возвращает введенный токен или None если пользователь пропустил"""
        return self.result


def request_token_if_needed(parent, token_manager: TokenManager) -> Optional[str]:
    """Проверяет наличие токена и запрашивает его если необходимо"""
    if token_manager.has_token():
        return token_manager.load_token()
    
    # Скрываем главное окно перед показом диалога
    parent.withdraw()
    
    # Показываем диалог ввода токена
    dialog = TokenInputDialog(parent, on_token_saved=token_manager.save_token)
    parent.wait_window(dialog.dialog)
    
    # Показываем главное окно снова после закрытия диалога
    parent.deiconify()
    
    return dialog.get_result()
