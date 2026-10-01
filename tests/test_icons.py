"""Tests for Home Assistant icon translations."""

import json
from pathlib import Path


def test_icon_translations_cover_dynamic_and_service_icons() -> None:
    root = Path(__file__).parents[1] / "custom_components" / "battery_consumption"
    icons = json.loads((root / "icons.json").read_text())
    sensors = icons["entity"]["sensor"]
    assert sensors["activity"]["state"] == {
        "charging": "mdi:battery-charging",
        "discharging": "mdi:battery-minus",
        "idle": "mdi:battery-outline",
    }
    assert sensors["equivalent_full_cycles"]["default"] == "mdi:battery-sync"
    assert icons["services"]["reset_totals"] == "mdi:battery-sync-outline"


def test_python_does_not_override_native_or_translated_icons() -> None:
    root = Path(__file__).parents[1] / "custom_components" / "battery_consumption"
    source = (root / "sensor.py").read_text()
    assert "def icon(" not in source
    assert "_attr_icon" not in source
