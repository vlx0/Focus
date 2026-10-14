"""
scheduler.py
============
Фоновый поток, который раз в 30 секунд проверяет все активные сценарии
и применяет/снимает фильтр.

При нескольких активных сценариях берётся МИНИМАЛЬНЫЙ уровень
(наибольшее затемнение) — для звука и яркости это безопаснее.
"""

import threading
import time
from datetime import datetime
from typing import Callable, Optional

from config import Config, Scenario
from logger import get as get_log

log = get_log()

# Раз в сколько секунд планировщик сверяется с часами
TICK_SECONDS = 30


def _scenario_in_window(s: Scenario, now: datetime) -> bool:
    """Проверяет, попадает ли `now` в окно сценария `s`."""
    start = now.replace(
        hour=s.start_hour, minute=s.start_minute, second=0, microsecond=0
    )
    end = now.replace(
        hour=s.end_hour, minute=s.end_minute, second=0, microsecond=0
    )
    if s.crosses_midnight():
        return now >= start or now < end
    return start <= now < end


class Scheduler:
    def __init__(
        self,
        config: Config,
        filter_: NightFilter,
        on_state_change: Optional[Callable[[bool, int, str], None]] = None,
    ) -> None:
        """
        on_state_change(in_window, intensity, label) — UI-колбэк
        срабатывает при реальной смене состояния фильтра.
        """
        self._config = config
        self._filter = filter_
        self._on_state_change = on_state_change

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------ #
    # Публичный API
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop, name="NightLight-Scheduler", daemon=True
        )
        self._thread.start()
        log.info("Scheduler started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        try:
            self._filter.disable()
        except Exception:
            pass

    def update_config(self, new_config: Config) -> None:
        self._config = new_config

    # ------------------------------------------------------------------ #
    # Цикл
    # ------------------------------------------------------------------ #
    def _active_match(self, now: datetime) -> tuple[int, str] | None:
        """
        Возвращает (intensity, label) для активного сценария.
        «Intensity» теперь = яркость экрана в % (0..100). При
        нескольких активных сценариях берём МИНИМАЛЬНУЮ яркость
        (= максимальное затемнение, безопаснее для сна).
        """
        best: tuple[int, str] | None = None
        for idx, s in enumerate(self._config.scenarios):
            if not s.enabled:
                continue
            try:
                if _scenario_in_window(s, now):
                    label = (f"#{idx + 1} "
                             f"{s.start_hour:02d}:{s.start_minute:02d}"
                             f"→"
                             f"{s.end_hour:02d}:{s.end_minute:02d}")
                    # Берём МИНИМУМ яркости (максимум затемнения)
                    if best is None or s.intensity < best[0]:
                        best = (s.intensity, label)
            except (ValueError, TypeError, AttributeError) as exc:
                log.warning("Scenario #%d skipped: %s", idx + 1, exc)
                continue
        return best

    def _loop(self) -> None:
        last_state: Optional[tuple[int, str]] = None  # последнее применённое

        while not self._stop_event.is_set():
            try:
                now = datetime.now()
                current = self._active_match(now)

                if current != last_state:
                    if current is not None:
                        # intensity = яркость экрана в % (0..100)
                        # warmth = "сколько затемнить" (0..1), инвертировано
                        intensity = current[0]
                        warmth = max(0.0, min(1.0, (100 - intensity) / 100.0))
                        ok = self._filter.apply(warmth)
                        backend = getattr(self._filter, "active_backend", "?")
                        log.info(
                            "Auto: filter ON (intensity=%d%%, warmth=%.2f, "
                            "scenario=%s, backend=%s, ok=%s)",
                            intensity, warmth, current[1], backend, ok,
                        )
                    else:
                        # UIA-бэкенду нужно явное выключение (он не
                        # умеет «выключить по отсутствию окна»)
                        ok = self._filter.disable()
                        log.info("Auto: filter OFF (ok=%s)", ok)
                    last_state = current
                    if self._on_state_change:
                        in_window = current is not None
                        intensity = current[0] if current else 0
                        label = current[1] if current else ""
                        self._on_state_change(in_window, intensity, label)
            except Exception:
                log.exception("Scheduler tick failed")

            for _ in range(TICK_SECONDS):
                if self._stop_event.is_set():
                    break
                time.sleep(1)
