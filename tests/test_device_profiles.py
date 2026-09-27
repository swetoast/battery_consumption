"""Tests for the editable battery device profile catalog."""

import json
from pathlib import Path

from custom_components.battery_consumption.device_profiles import load_device_profiles


def test_bundled_profiles_are_available(tmp_path: Path) -> None:
    profiles = load_device_profiles(str(tmp_path))
    assert profiles["google_pixel_8_pro"]["capacity"] == 5050
    assert profiles["google_pixel_watch_2"]["nominal_voltage"] == 3.87
    assert profiles["meta_quest_2"]["capacity"] == 3640


def test_user_profiles_add_and_override_entries(tmp_path: Path) -> None:
    user_profiles = {
        "schema_version": 1,
        "devices": [
            {
                "id": "google_pixel_8_pro",
                "manufacturer": "Google",
                "model": "Pixel 8 Pro custom",
                "capacity": 5000,
                "capacity_unit": "mAh",
                "nominal_voltage": 3.85,
            },
            {
                "id": "my_custom_device",
                "manufacturer": "Example",
                "model": "Custom device",
                "capacity": 20,
                "capacity_unit": "Wh",
            },
        ],
    }
    (tmp_path / "battery_consumption_device_profiles.json").write_text(
        json.dumps(user_profiles)
    )

    profiles = load_device_profiles(str(tmp_path))
    assert profiles["google_pixel_8_pro"]["capacity"] == 5000
    assert profiles["my_custom_device"]["capacity_unit"] == "Wh"


def test_invalid_user_profiles_are_skipped(tmp_path: Path) -> None:
    user_profiles = {
        "schema_version": 1,
        "devices": [
            {
                "id": "invalid profile id",
                "manufacturer": "Example",
                "model": "Invalid",
                "capacity": 1000,
                "capacity_unit": "mAh",
                "nominal_voltage": 3.85,
            },
            {
                "id": "missing_voltage",
                "manufacturer": "Example",
                "model": "Invalid",
                "capacity": 1000,
                "capacity_unit": "mAh",
            },
        ],
    }
    (tmp_path / "battery_consumption_device_profiles.json").write_text(
        json.dumps(user_profiles)
    )

    profiles = load_device_profiles(str(tmp_path))
    assert "invalid profile id" not in profiles
    assert "missing_voltage" not in profiles
