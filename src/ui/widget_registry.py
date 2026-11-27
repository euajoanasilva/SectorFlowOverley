from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class WidgetDefinition:
    widget_id: str
    title: str
    category: str
    editable: bool = True
    implemented: bool = False


WIDGET_DEFINITIONS: list[WidgetDefinition] = [
    WidgetDefinition("standings", "Standings", "Corrida", True, True),
    WidgetDefinition("delta", "Delta", "Corrida", True, True),
    WidgetDefinition("driver_panel", "Telemetry", "Corrida", True, True),
    WidgetDefinition("fuel_time", "Fuel Time", "Corrida", True, True),
    WidgetDefinition("tires", "Tyres", "Carro", True, True),
    WidgetDefinition("url", "URL", "Carro", True, True),
    WidgetDefinition("flags", "Flags", "Carro", True, True),
    WidgetDefinition("relative", "Relative", "Carro", True, True),
    WidgetDefinition("map", "Mapa", "Estratégia", True, True),
    WidgetDefinition("battery", "Battery", "Estratégia", True, True),
    WidgetDefinition("lap_timer", "Lap Timer", "Estratégia", True, True),
    WidgetDefinition("damage", "Damage", "Estratégia", True, True),
    WidgetDefinition("weather", "Weather", "Sistema", True, True),
    WidgetDefinition("radar", "Radar", "Sistema", True, True),
]
