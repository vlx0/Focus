"""
logger.py
=========
Простой логгер в файл `nightlight.log` рядом со скриптом.

Используется и для sys.excepthook (необработанные исключения),
и для ручных логов из критичных мест (UI-колбэки, ctypes-API).
"""

import logging
import sys
from pathlib import Path


_LOGGER_NAME = "nightlight"
_LOGGER: logging.Logger | None = None


def setup() -> logging.Logger:
    """
    Инициализирует логгер один раз. Возвращает его.
    """
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    log_path = Path(__file__).parent / "nightlight.log"
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False  # не дублировать в root

    # Если хэндлер уже есть (повторный вызов setup), не плодим
    if not logger.handlers:
        fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

        sh = logging.StreamHandler(stream=sys.stderr)
        sh.setFormatter(fmt)
        logger.addHandler(sh)

    # Ловим всё, что не поймали
    def _hook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.error(
            "UNCAUGHT: %s", "".join(
                __import__("traceback").format_exception(
                    exc_type, exc_value, exc_tb
                )
            )
        )
    sys.excepthook = _hook

    _LOGGER = logger
    return logger


def get() -> logging.Logger:
    """Возвращает уже инициализированный логгер (или создаёт)."""
    return _LOGGER or setup()
