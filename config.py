"""
config.py
=========
Загрузка и сохранение пользовательских настроек в JSON.

С версии 0.2 настроено под список сценариев. Старые конфиги
(с одним start_hour/start_minute/...) автоматически мигрируют
в один сценарий.
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict


DEFAULT_SCENARIO_DAY = (10, 0, 12, 30, 50)    # 10:00 → 12:30, 50%
DEFAULT_SCENARIO_NIGHT = (21, 0, 7, 0, 70)    # 21:00 → 07:00, 70%


@dataclass
class Scenario:
    """
    Один сценарий: «с какого по какое время держать фильтр
    с такой-то интенсивностью».
    """
    start_hour: int
    start_minute: int
    end_hour: int
    end_minute: int
    intensity: int
    enabled: bool = True

    def __post_init__(self) -> None:
        # Жёсткая защита: всё, что прилетает из UI или из config.json
        # (даже руками поправленного) — клэмпится в допустимые диапазоны.
        # Без этого datetime.replace(hour=25) крашит планировщик.
        self.start_hour = max(0, min(23, int(self.start_hour)))
        self.start_minute = max(0, min(59, int(self.start_minute)))
        self.end_hour = max(0, min(23, int(self.end_hour)))
        self.end_minute = max(0, min(59, int(self.end_minute)))
        self.intensity = max(0, min(100, int(self.intensity)))
        self.enabled = bool(self.enabled)

    def crosses_midnight(self) -> bool:
        """True, если окно переходит через полночь (конец ≤ начало)."""
        return (self.end_hour, self.end_minute) <= (self.start_hour, self.start_minute)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Scenario":
        known = set(cls.__dataclass_fields__.keys())
        # Значения по умолчанию — защита от мусора в config.json
        defaults = {f: 0 for f in cls.__dataclass_fields__ if f != "intensity"}
        defaults["intensity"] = 50
        defaults["enabled"] = True
        return cls(**{**defaults,
                      **{k: v for k, v in d.items() if k in known}})


@dataclass
class Config:
    scenarios: list[Scenario] = field(default_factory=list)
    auto_start: bool = True

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def active_scenarios(self) -> list[Scenario]:
        return [s for s in self.scenarios if s.enabled]

    def add_scenario(self, scenario: Scenario | None = None) -> Scenario:
        if scenario is None:
            scenario = Scenario(*DEFAULT_SCENARIO_DAY, enabled=True)
        self.scenarios.append(scenario)
        return scenario

    def remove_scenario(self, index: int) -> None:
        if 0 <= index < len(self.scenarios):
            del self.scenarios[index]

    # ------------------------------------------------------------------ #
    # Сериализация
    # ------------------------------------------------------------------ #
    @classmethod
    def create_default(cls) -> "Config":
        return cls(
            scenarios=[
                Scenario(*DEFAULT_SCENARIO_NIGHT, enabled=True),
                Scenario(*DEFAULT_SCENARIO_DAY, enabled=True),
            ],
            auto_start=True,
        )

    @classmethod
    def load(cls, path: Path) -> "Config":
        if not path.exists():
            return cls.create_default()
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            # --- Обратная совместимость: одиночный сценарий из v0.1 ---
            if "scenarios" not in raw:
                scenario = Scenario(
                    start_hour=int(raw.get("start_hour", 21)),
                    start_minute=int(raw.get("start_minute", 0)),
                    end_hour=int(raw.get("end_hour", 7)),
                    end_minute=int(raw.get("end_minute", 0)),
                    intensity=int(raw.get("intensity", 60)),
                    enabled=True,
                )
                return cls(
                    scenarios=[scenario],
                    auto_start=bool(raw.get("auto_start", True)),
                )

            scenarios = [Scenario.from_dict(s) for s in raw["scenarios"]]
            if not scenarios:
                return cls.create_default()
            return cls(
                scenarios=scenarios,
                auto_start=bool(raw.get("auto_start", True)),
            )
        except (json.JSONDecodeError, TypeError, ValueError, KeyError):
            return cls.create_default()

    def save(self, path: Path) -> None:
        data = {
            "scenarios": [s.to_dict() for s in self.scenarios],
            "auto_start": self.auto_start,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def config_path() -> Path:
    base = Path(os.path.dirname(os.path.abspath(__file__)))
    return base / "config.json"
