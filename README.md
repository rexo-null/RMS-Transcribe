# RMS Transcribe Desktop

[![Latest Release](https://img.shields.io/github/v/release/rexo-null/RMS-Transcribe?include_prereleases&label=release)](https://github.com/rexo-null/RMS-Transcribe/releases)

Локальное desktop-приложение для пакетной транскрибации аудио звонков с диаризацией спикеров.

**⚠️ Только Windows:** Приложение разработано для Windows 10/11

## 📥 Скачать

[⬇️ Скачать последнюю версию](https://github.com/rexo-null/RMS-Transcribe/releases/latest)

### Файлы релиза

Каждый релиз содержит следующие файлы (где `vX.X.X` — номер версии):

| Платформа | Архив | Установщик | Описание |
|-----------|-------|------------|----------|
| **Windows** | `RMS-Transcribe-Windows-vX.X.X.zip` | `RMS-Transcribe-Setup-vX.X.X.exe` | ZIP-архив или EXE-установщик |

### Быстрая установка

**Windows (рекомендуется EXE-установщик):**
1. На странице [Releases](https://github.com/rexo-null/RMS-Transcribe/releases) скачайте файл `RMS-Transcribe-Setup-vX.X.X.exe`
2. Запустите установщик и следуйте инструкциям
3. После установки ярлык появится в меню Пуск

**Windows (портативная версия):**
1. Скачайте `RMS-Transcribe-Windows-vX.X.X.zip`
2. Распакуйте архив
3. Запустите `app\RMS-Transcribe.exe`

**Готово к работе!** См. подробную инструкцию в [docs/USER_GUIDE.md](docs/USER_GUIDE.md) или [docs/INSTALL.md](docs/INSTALL.md)

---

## 📁 Структура проекта

```
rms-transcribe/
├── src/              # Исходный код приложения
├── tests/            # Unit и integration тесты
├── docs/             # Расширенная документация
├── examples/         # Примеры использования
├── assets/           # Логотипы, иконки
├── config/           # Конфигурационные файлы
├── requirements.txt  # Зависимости
└── README.md         # Этот файл
```

## 🚀 Быстрый старт для разработчика (Windows)

### 1. Настройка окружения

```powershell
# Создать виртуальное окружение
python -m venv .venv
.venv\Scripts\activate

# Установить зависимости
pip install -r requirements.txt
```

### 2. Конфигурация

```powershell
# При первом запуске приложение автоматически запросит токен
# Или создайте .env файл вручную:
echo HUGGING_FACE_TOKEN=your_token_here > .env
```

Получить токен: https://huggingface.co/settings/tokens

### 3. Запуск из исходников

```powershell
cd src
python main.py
```

## Сборка релиза

### Требования

- Python 3.10+
- PyInstaller: `pip install pyinstaller`
- (Опционально) Inno Setup 6.2+ для создания .exe установщика

### Сборка

Скрипты сборки находятся в `dev/infrastructure/`:

```powershell
# Сборка через PyInstaller
cd dev/infrastructure
.\build_windows.ps1

# Создание установщика Inno Setup
.\build_installer.ps1
```

### Результат локальной сборки

После выполнения скриптов в папке `dev/output/` создаются:

- `RMS-Transcribe-Windows-v{версия}.zip` — портативная версия
- `RMS-Transcribe-Setup-v{версия}.exe` — установщик Windows

## Системные требования

| Компонент | Требование |
|-----------|------------|
| **ОС** | Windows 10/11 (64-bit) |
| **Python** | 3.10+ |
| **RAM** | 4GB (8GB+ рекомендуется) |
| **Диск** | 2GB + ML-модели (~2-5 GB) |
| **Интернет** | Для загрузки моделей |

**ML-модели** (~2-5 GB) загружаются автоматически при первом запуске.

## Лицензия

RMS Internal Use Only

## Контакты

- Разработка: Dev Team
- Поддержка: support@rms.com
