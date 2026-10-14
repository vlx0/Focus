"""
audio.py
========
Управление системной громкостью и mute в Windows (stdlib only).

Два уровня:
  1) Mute toggle — через keybd_event(VK_VOLUME_MUTE), 100% надёжно.
  2) Уровень громкости — через подсчёт шагов VK_VOLUME_UP/DOWN.
     Каждое нажатие = 2% (стандарт Windows 10/11).

Совместим по API с NightFilter / UIAFilter (apply / disable / is_active).
Параметр `level`: 0.0..1.0, где 0.0 = mute, 1.0 = максимальная громкость.
"""

import ctypes
import sys
import time
from typing import Optional

from logger import get as get_log

log = get_log()

# Virtual-Key codes
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF

# Шаг громкости в Windows 10/11 — 2% на нажатие
VOLUME_STEP_PCT = 2


class AudioFilter:
    """Бэкенд управления системной громкостью (mute + уровень)."""

    def __init__(self) -> None:
        self._muted: bool = False
        self._volume: float = 1.0
        self._last_error: Optional[str] = None
        self._available: bool = self._check_available()

    def _check_available(self) -> bool:
        return sys.platform == "win32"

    @property
    def is_available(self) -> bool:
        return self._available

    # ------------------------------------------------------------------ #
    def apply(self, level: float) -> bool:
        """
        Применяет уровень 0..1. 0 = mute, 1 = максимум.
        """
        if not self._available:
            return False
        level = max(0.0, min(1.0, float(level)))
        try:
            if level == 0.0:
                if not self._muted:
                    self._send_mute_key()
                    self._muted = True
                self._volume = 0.0
            else:
                # Снимаем mute если был
                if self._muted:
                    self._send_mute_key()
                    self._muted = False
                # Устанавливаем уровень через счёт шагов.
                # Сначала сбрасываем в 0, потом поднимаем до нужного.
                target_pct = int(round(level * 100))
                self._set_volume_to(target_pct)
                self._volume = level
            self._last_error = None
            return True
        except Exception as e:
            self._last_error = f"apply: {e!r}"
            log.exception("Audio apply failed")
            return False

    def disable(self) -> bool:
        """Восстанавливает: unmute + 100%."""
        try:
            if self._muted:
                self._send_mute_key()
                self._muted = False
            self._set_volume_to(100)
            self._volume = 1.0
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    def _send_mute_key(self) -> None:
        """Шлёт VK_VOLUME_MUTE через keybd_event."""
        u = ctypes.windll.user32
        KEYEVENTF_EXTENDEDKEY = 0x0001
        KEYEVENTF_KEYUP = 0x0002
        u.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY, 0)
        u.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        time.sleep(0.05)  # даём системе время обработать

    def _send_volume_key(self, up: bool) -> None:
        """Шлёт VK_VOLUME_UP или VK_VOLUME_DOWN."""
        u = ctypes.windll.user32
        vk = VK_VOLUME_UP if up else VK_VOLUME_DOWN
        KEYEVENTF_EXTENDEDKEY = 0x0001
        KEYEVENTF_KEYUP = 0x0002
        u.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY, 0)
        u.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
        time.sleep(0.02)

    def _set_volume_to(self, target_pct: int) -> None:
        """
        Устанавливает громкость в target_pct процентов через шаги.
        Сначала опускаем в 0 (50 нажатий DOWN), потом поднимаем до цели.
        """
        target_pct = max(0, min(100, int(target_pct)))
        # 100 / 2 = 50 шагов до нуля
        for _ in range(50):
            self._send_volume_key(up=False)
        # Поднимаем до цели
        steps = target_pct // VOLUME_STEP_PCT
        for _ in range(steps):
            self._send_volume_key(up=True)

    # ------------------------------------------------------------------ #
    @property
    def is_active(self) -> bool:
        return self._muted or self._volume < 1.0

    @property
    def current_warmth(self) -> float:  # API compat
        return self._volume

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error
