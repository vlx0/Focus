"""
app.py
======
GUI для Focus — планировщика системной громкости.

В заданное время устанавливает master volume (или mute) на
уровне сценария. По окончании — возвращает к 100%.
"""

import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from datetime import datetime
from typing import Callable

from audio import AudioFilter
from scheduler import Scheduler
from config import Config, Scenario, config_path
from logger import setup as setup_logging

log = setup_logging()

# Палитра
BG = "#1e1e2e"
BG_SURFACE = "#313244"
BG_SURFACE_2 = "#3a3a52"
BG_INPUT = "#45475a"
FG = "#cdd6f4"
FG_DIM = "#a6adc8"
ACCENT = "#89b4fa"
SUCCESS = "#a6e3a1"
DANGER = "#f38ba8"


class ScenarioRow:
    """Одна строка сценария в UI."""

    def __init__(
        self,
        parent,
        scenario: Scenario,
        on_change: Callable,
        on_delete: Callable,
    ) -> None:
        self.scenario = scenario
        self._on_change = on_change
        self._on_delete = on_delete

        self.frame = tk.Frame(parent, bg=BG_SURFACE_2, bd=0, highlightthickness=0)
        content = tk.Frame(self.frame, bg=BG_SURFACE_2)
        content.pack(fill="x", padx=10, pady=8)

        # Верх: чекбокс + название + удалить
        top = tk.Frame(content, bg=BG_SURFACE_2)
        top.pack(fill="x", pady=(0, 6))
        self.var_enabled = tk.BooleanVar(value=scenario.enabled)
        tk.Checkbutton(
            top, variable=self.var_enabled,
            bg=BG_SURFACE_2, fg=FG, selectcolor=BG_INPUT,
            activebackground=BG_SURFACE_2, activeforeground=FG,
            command=self._notify_change,
        ).pack(side="left")
        self.title_label = tk.Label(
            top, text="", bg=BG_SURFACE_2, fg=FG_DIM,
            font=("Segoe UI", 9, "bold"),
        )
        self.title_label.pack(side="left", padx=4)
        tk.Button(
            top, text="🗑", command=self._on_delete_click,
            bg=BG_SURFACE_2, fg=DANGER,
            activebackground=BG_SURFACE_2, activeforeground=DANGER,
            font=("Segoe UI", 11, "bold"),
            bd=0, relief="flat", padx=8, pady=0, cursor="hand2",
        ).pack(side="right")

        # Низ: время + громкость
        bottom = tk.Frame(content, bg=BG_SURFACE_2)
        bottom.pack(fill="x")

        self.var_sh = tk.StringVar(value=f"{scenario.start_hour:02d}")
        self.var_sm = tk.StringVar(value=f"{scenario.start_minute:02d}")
        self.var_eh = tk.StringVar(value=f"{scenario.end_hour:02d}")
        self.var_em = tk.StringVar(value=f"{scenario.end_minute:02d}")
        for var in (self.var_sh, self.var_eh):
            var.trace_add("write", self._notify_change)

        self._spinbox(bottom, self.var_sh, 0, 23).pack(side="left")
        tk.Label(bottom, text=":", bg=BG_SURFACE_2, fg=FG,
                 font=("Segoe UI", 12, "bold")).pack(side="left", padx=1)
        self._spinbox(bottom, self.var_sm, 0, 59).pack(side="left")
        tk.Label(bottom, text="→", bg=BG_SURFACE_2, fg=FG_DIM,
                 font=("Segoe UI", 12, "bold"), padx=8).pack(side="left")
        self._spinbox(bottom, self.var_eh, 0, 23).pack(side="left")
        tk.Label(bottom, text=":", bg=BG_SURFACE_2, fg=FG,
                 font=("Segoe UI", 12, "bold")).pack(side="left", padx=1)
        self._spinbox(bottom, self.var_em, 0, 59).pack(side="left")

        tk.Label(bottom, text="🔊", bg=BG_SURFACE_2, fg=FG_DIM,
                 font=("Segoe UI", 11), padx=12).pack(side="left")
        self.var_volume = tk.IntVar(value=scenario.intensity)
        self.volume_label = tk.Label(
            bottom, text=f"{scenario.intensity}%",
            bg=BG_SURFACE_2, fg=ACCENT,
            font=("Segoe UI", 9, "bold"), width=4,
        )
        self.scale = tk.Scale(
            bottom, from_=0, to=100,
            orient="horizontal", variable=self.var_volume,
            bg=BG_SURFACE_2, fg=FG, troughcolor=BG_INPUT,
            highlightthickness=0, sliderrelief="flat",
            font=("Segoe UI", 8), length=80, showvalue=False,
        )
        self.scale.pack(side="left")
        self.volume_label.pack(side="left", padx=4)
        self.var_volume.trace_add("write", self._on_volume_change)
        self.var_enabled.trace_add("write", self._notify_change)

    def _spinbox(self, parent, var, mn, mx) -> tk.Spinbox:
        return tk.Spinbox(
            parent, textvariable=var, from_=mn, to=mx, width=2,
            format="%02.0f", bg=BG_INPUT, fg=FG,
            buttonbackground=BG_INPUT, relief="flat", bd=0,
            font=("Segoe UI", 10, "bold"), justify="center",
        )

    def _on_volume_change(self, *_args) -> None:
        self.volume_label.config(text=f"{self.var_volume.get()}%")
        self._notify_change()

    def _on_delete_click(self) -> None:
        self._on_delete(self)

    def _notify_change(self, *_args) -> None:
        try:
            self.scenario.start_hour = max(0, min(23, int(self.var_sh.get())))
            self.scenario.start_minute = max(0, min(59, int(self.var_sm.get())))
            self.scenario.end_hour = max(0, min(23, int(self.var_eh.get())))
            self.scenario.end_minute = max(0, min(59, int(self.var_em.get())))
            self.scenario.intensity = max(0, min(100, int(self.var_volume.get())))
            self.scenario.enabled = bool(self.var_enabled.get())
        except (ValueError, tk.TclError):
            return
        self._on_change()

    def set_index(self, idx: int) -> None:
        self.title_label.config(text=f"СЦЕНАРИЙ #{idx}")

    def destroy(self) -> None:
        self.frame.destroy()


class FocusApp:
    WINDOW_W = 540
    WINDOW_H = 600

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Focus — планировщик громкости")
        self.root.geometry(f"{self.WINDOW_W}x{self.WINDOW_H}")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.after(400, lambda: self.root.attributes("-topmost", False))

        self._cfg_path: Path = config_path()
        self.config: Config = Config.load(self._cfg_path)
        self.audio = AudioFilter()
        self.scheduler = Scheduler(
            self.config, self.audio,
            on_state_change=self._on_scheduler_state,
        )

        self.var_auto = tk.BooleanVar(value=self.config.auto_start)
        self.var_status = tk.StringVar(value="Планировщик остановлен")
        self._rows: list[ScenarioRow] = []

        self._build_ui()
        self._render_scenarios()

        if self.config.auto_start:
            self.scheduler.start()
            self._refresh_status()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        tk.Label(
            self.root, text="🎯  Focus",
            font=("Segoe UI", 18, "bold"),
            bg=BG, fg=FG,
        ).pack(pady=(20, 2))
        tk.Label(
            self.root,
            text="Планировщик системной громкости и mute",
            font=("Segoe UI", 9), bg=BG, fg=FG_DIM,
        ).pack(pady=(0, 14))

        # Список сценариев со скроллом
        scroll_wrap = tk.Frame(self.root, bg=BG)
        scroll_wrap.pack(fill="both", expand=True, padx=20, pady=4)
        self.scenarios_canvas = tk.Canvas(
            scroll_wrap, bg=BG, highlightthickness=0, bd=0,
        )
        self.scenarios_canvas.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(
            scroll_wrap, orient="vertical",
            command=self.scenarios_canvas.yview,
            bg=BG, troughcolor=BG_SURFACE, bd=0, highlightthickness=0,
        )
        sb.pack(side="right", fill="y")
        self.scenarios_canvas.configure(yscrollcommand=sb.set)
        self.scenarios_container = tk.Frame(self.scenarios_canvas, bg=BG)
        self._scenarios_window = self.scenarios_canvas.create_window(
            (0, 0), window=self.scenarios_container, anchor="nw"
        )
        self.scenarios_container.bind(
            "<Configure>",
            lambda e: self.scenarios_canvas.configure(
                scrollregion=self.scenarios_canvas.bbox("all")
            ),
        )
        self.scenarios_canvas.bind(
            "<Configure>",
            lambda e: self.scenarios_canvas.itemconfigure(
                self._scenarios_window, width=e.width
            ),
        )
        self.scenarios_canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.scenarios_canvas.yview_scroll(
                int(-1 * (e.delta / 120)), "units"
            ),
        )

        # Кнопка «+ Сценарий»
        tk.Button(
            self.root, text="➕  Добавить сценарий",
            command=self._add_scenario,
            bg=ACCENT, fg="#1e1e2e",
            activebackground=ACCENT, activeforeground="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            bd=0, relief="flat", padx=14, pady=8, cursor="hand2",
        ).pack(fill="x", padx=20, pady=4)

        # Кнопка «Focus Now» / «Выключить»
        self.btn_toggle = tk.Button(
            self.root, text="🔇  Включить Focus",
            command=self._on_toggle_click,
            bg=ACCENT, fg="#1e1e2e",
            activebackground=ACCENT, activeforeground="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            bd=0, relief="flat", padx=14, pady=8, cursor="hand2",
        )
        self.btn_toggle.pack(fill="x", padx=20, pady=4)

        # Сохранить
        tk.Button(
            self.root, text="💾  Сохранить и запустить планировщик",
            command=self._on_save_click,
            bg=SUCCESS, fg="#1e1e2e",
            activebackground=SUCCESS, activeforeground="#1e1e2e",
            font=("Segoe UI", 10, "bold"),
            bd=0, relief="flat", padx=14, pady=8, cursor="hand2",
        ).pack(fill="x", padx=20, pady=4)

        tk.Checkbutton(
            self.root, text="Автозапуск планировщика при открытии",
            variable=self.var_auto,
            bg=BG, fg=FG_DIM, selectcolor=BG_INPUT,
            activebackground=BG, activeforeground=FG,
            font=("Segoe UI", 9),
        ).pack(padx=20, pady=(0, 8), anchor="w")

        # Статус
        status_bar = tk.Frame(self.root, bg=BG_SURFACE)
        status_bar.pack(side="bottom", fill="x")
        self.status_label = tk.Label(
            status_bar, textvariable=self.var_status,
            bg=BG_SURFACE, fg=FG_DIM, font=("Segoe UI", 9),
            anchor="w", wraplength=460, justify="left",
        )
        self.status_label.pack(side="left", fill="x", expand=True, padx=14, pady=4)

    def _render_scenarios(self) -> None:
        for row in self._rows:
            row.destroy()
        self._rows.clear()
        for idx, sc in enumerate(self.config.scenarios):
            row = ScenarioRow(
                self.scenarios_container, sc,
                on_change=self._on_scenario_change,
                on_delete=self._delete_scenario,
            )
            row.frame.pack(fill="x", pady=4)
            row.set_index(idx + 1)
            self._rows.append(row)

    def _on_scenario_change(self) -> None:
        for idx, row in enumerate(self._rows):
            row.set_index(idx + 1)

    def _add_scenario(self) -> None:
        try:
            self.config.add_scenario()
            self._render_scenarios()
        except Exception:
            log.exception("Add scenario failed")

    def _delete_scenario(self, row: ScenarioRow) -> None:
        if row.scenario in self.config.scenarios:
            self.config.scenarios.remove(row.scenario)
        self._render_scenarios()

    def _update_toggle_button(self) -> None:
        if self.audio.is_active:
            self.btn_toggle.config(
                text="🔊  Выключить Focus",
                bg=DANGER, activebackground=DANGER,
            )
        else:
            self.btn_toggle.config(
                text="🔇  Включить Focus",
                bg=ACCENT, activebackground=ACCENT,
            )

    def _on_toggle_click(self) -> None:
        try:
            if self.audio.is_active:
                if self.audio.disable():
                    self._set_status("Focus выключен — звук восстановлен")
                else:
                    self._set_status("Не удалось снять mute")
            else:
                # Берём минимальную громкость среди активных сценариев
                active = self.config.active_scenarios()
                vol = min((s.intensity for s in active), default=0)
                if self.audio.apply(vol / 100.0):
                    self._set_status(f"Focus вкл · громкость {vol}%")
                else:
                    self._set_status("Не удалось применить mute")
            self._update_toggle_button()
        except Exception:
            log.exception("toggle failed")
            try:
                messagebox.showerror("Ошибка", "Смотри nightlight.log")
            except Exception:
                pass

    def _on_save_click(self) -> None:
        try:
            for idx, row in enumerate(self._rows):
                try:
                    _ = int(row.var_sh.get())
                    _ = int(row.var_sm.get())
                    _ = int(row.var_eh.get())
                    _ = int(row.var_em.get())
                except ValueError:
                    messagebox.showerror(
                        "Некорректные значения",
                        f"Сценарий #{idx + 1}: проверьте часы и минуты.",
                    )
                    return
            self.config.scenarios = [r.scenario for r in self._rows]
            self.config.auto_start = bool(self.var_auto.get())
            self.config.save(self._cfg_path)
            self.scheduler.update_config(self.config)
            self.scheduler.start()
            self._refresh_status()
            self._set_status(
                f"Сохранено · сценариев: {len(self.config.scenarios)}"
            )
            log.info("Config saved: %d scenarios", len(self.config.scenarios))
        except Exception:
            log.exception("Save failed")
            try:
                messagebox.showerror("Ошибка", "Смотри nightlight.log")
            except Exception:
                pass

    def _on_scheduler_state(self, in_window: bool, intensity: int, label: str) -> None:
        def _update() -> None:
            now = datetime.now().strftime("%H:%M")
            if in_window:
                self._set_status(f"🟢 {label} · {intensity}% · {now}")
            else:
                self._set_status(f"⚪ Все сценарии неактивны · {now}")
            self._update_toggle_button()
        self.root.after(0, _update)

    def _set_status(self, text: str) -> None:
        MAX = 60
        if len(text) > MAX:
            text = text[:MAX - 1] + "…"
        self.var_status.set(text)

    def _refresh_status(self) -> None:
        now = datetime.now().strftime("%H:%M")
        self._set_status(f"🟡 Планировщик запущен · {now}")

    def _on_close(self) -> None:
        try:
            self.scheduler.stop()
        finally:
            self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
