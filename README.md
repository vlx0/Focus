# 🎯 Focus

Планировщик системной громкости для Windows. По расписанию
**приглушает звук** (mute или заданный уровень) на время «фокусировки»
и возвращает обратно по окончании.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078d4?logo=windows)
![License](https://img.shields.io/badge/License-MIT-green)
![Dependencies](https://img.shields.io/badge/Dependencies-zero-brightgreen)

---

## ✨ Что делает

- ⏰ Несколько **сценариев** с временем начала/конца и уровнем громкости
- 🔇 По сценарию: mute (0%) или конкретный уровень (10%, 30%, 50%...)
- 🌅 Окна через полночь работают автоматически (22:00 → 07:00)
- 🔄 Возврат к 100% по окончании
- 💾 Настройки в `config.json` (1.5 КБ)
- 🪶 **Без зависимостей** — только стандартная библиотека Python

---

## 🚀 Запуск

```powershell
git clone https://github.com/<your-username>/Focus.git
cd Focus
python main.py
```

> Только Windows 10/11 (использует `keybd_event` с `VK_VOLUME_MUTE`).
> `requirements.txt` пустой — никакого `pip install`.

При первом запуске откроется окно с двумя сценариями по умолчанию.
Нажми **«💾 Сохранить и запустить планировщик»** — громкость начнёт
снижаться по расписанию.

---

## 🖱 Как это работает

Когда по сценарию приходит время:

1. Планировщик вычисляет нужный уровень (берётся **минимум** среди активных
   сценариев — самое «глубокое» приглушение)
2. `audio.py` отправляет системе `keybd_event`:
   - `VK_VOLUME_MUTE` (0xAD) — toggle mute
   - `VK_VOLUME_UP` / `VK_VOLUME_DOWN` — шаги по 2% (стандарт Windows)

Системная громкость — **настоящая**, не виртуальный слой.

---

## 📁 Структура

```
Focus/
├── main.py              # Точка входа
├── app.py               # Tkinter GUI
├── audio.py             # keybd_event для mute/volume
├── scheduler.py         # Фоновый поток-планировщик
├── config.py            # JSON-конфиг + Scenario dataclass
├── logger.py            # Логи в nightlight.log
├── config.json          # Создаётся при первом «Сохранить»
├── requirements.txt     # Пустой (только stdlib)
├── LICENSE              # MIT
└── README.md
```

## 🎛 Настройки `config.json`

```json
{
  "scenarios": [
    {
      "start_hour": 21, "start_minute": 0,
      "end_hour": 7,    "end_minute": 0,
      "intensity": 30,
      "enabled": true
    }
  ],
  "auto_start": true
}
```

| Поле | Тип | Что значит |
|---|---|---|
| `start_hour` / `start_minute` | 0..23 / 0..59 | Когда приглушать |
| `end_hour` / `end_minute` | 0..23 / 0..59 | Когда восстановить 100% |
| `intensity` | 0..100 | Целевой уровень громкости (0 = mute) |
| `enabled` | bool | Сценарий активен |
| `auto_start` | bool | Запускать планировщик сразу |

---

## 🪟 Сборка в .exe

```powershell
pip install pyinstaller
pyinstaller --onefile --noconsole --name Focus main.py
```

---

## 🐛 Известные ограничения

- Только Windows 10/11 (использует `keybd_event`).
- Смена уровня громкости происходит **шагами** (по 2%), поэтому при
  первом переключении слышно серию щелчков. На современных
  аудио-драйверах это занимает ~1 секунду.
- Состояние mute трекается **внутри программы** (Windows не даёт
  простого способа прочитать «сейчас mute или нет» без COM).
  Если что-то ещё меняет mute, пока программа не работает,
  внутренний флаг может разойтись с реальностью — лечится
  перезапуском.

## 📝 Лицензия

MIT — делай что хочешь, только копирайт сохрани.
