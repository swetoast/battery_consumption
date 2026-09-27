"""Tests for the editable battery device profile catalog."""

import json
from pathlib import Path

from custom_components.battery_consumption.device_profiles import load_device_profiles


def test_bundled_profiles_are_available(tmp_path: Path) -> None:
    profiles = load_device_profiles(str(tmp_path))
    assert profiles["google_pixel_8_pro"]["capacity"] == 5050
    assert profiles["google_pixel_watch_2"]["nominal_voltage"] == 3.87
    assert profiles["meta_quest_2"]["capacity"] == 14
    assert profiles["apple_iphone_15"]["capacity"] == 12.98
    assert profiles["samsung_galaxy_s24_ultra"]["capacity"] == 19.4
    assert profiles["panasonic_eneloop_aaa_bk_4mcc"]["nominal_voltage"] == 1.2
    assert profiles["varta_recharge_accu_power_9v_200"]["nominal_voltage"] == 8.4


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


def test_user_profile_override_logs_warning(tmp_path: Path, caplog) -> None:
    user_profiles = {
        "schema_version": 1,
        "devices": [
            {
                "id": "google_pixel_8_pro",
                "manufacturer": "Google",
                "model": "Pixel 8 Pro custom",
                "capacity": 20,
                "capacity_unit": "Wh",
            }
        ],
    }
    (tmp_path / "battery_consumption_device_profiles.json").write_text(
        json.dumps(user_profiles)
    )

    load_device_profiles(str(tmp_path))
    assert "User battery profile overrides bundled profile: google_pixel_8_pro" in caplog.text
