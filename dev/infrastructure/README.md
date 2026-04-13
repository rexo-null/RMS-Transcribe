# RMS Transcribe - Build Scripts

Скрипты для сборки релиза под Windows.

## 📦 Готовые файлы

| Файл | Размер | Описание |
|------|--------|----------|
| `RMS-Transcribe-Setup-v1.0.0.exe` | ~76 MB | Windows установщик |
| `RMS-Transcribe-Windows-v1.0.0.zip` | ~76 MB | Портативная версия |

## 🪟 Сборка Windows

```powershell
cd releases
.\build_windows.ps1 -Version "1.0.0"
```

Требования:
- Windows 10/11 x64
- Python 3.10+
- Inno Setup (опционально, для создания установщика)

## 🚀 Загрузка в GitHub Release

1. Открой: https://github.com/rexo-null/transcribe/releases/new?tag=v1.0.0
2. Заголовок: **RMS Transcribe v1.0.0**
3. Загрузи файлы:
   - `RMS-Transcribe-Setup-v1.0.0.exe`
   - `RMS-Transcribe-Windows-v1.0.0.zip`
4. Нажми **Publish release**

## 📝 Примечания

- Эта папка (`releases/`) добавлена в `.gitignore` — собранные файлы не попадают в репозиторий
- Для автоматической сборки можно настроить GitHub Actions
