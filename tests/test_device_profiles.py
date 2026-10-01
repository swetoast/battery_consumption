"""Tests for the editable battery device profile catalog."""

import json
from pathlib import Path

from custom_components.battery_consumption.device_profiles import (
    PROFILE_ORIGIN_BUNDLED,
    PROFILE_ORIGIN_USER,
    _load_file,
    load_device_profiles,
    load_device_profiles_with_report,
    profile_selector_options,
    suggest_device_profile,
)


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


def test_bundled_roborock_profiles_are_valid_and_visible(tmp_path: Path) -> None:
    profiles = load_device_profiles(str(tmp_path))
    roborock = [profile for profile in profiles.values() if profile["manufacturer"] == "Roborock"]

    assert len(roborock) == 14
    assert profiles["roborock_s8_pro_ultra"]["capacity"] == 5200
    assert profiles["roborock_s8_pro_ultra"]["nominal_voltage"] == 14.4
    assert all(profile["nominal_voltage"] == 14.4 for profile in roborock)

    labels = [f'{profile["manufacturer"]} · {profile["model"]}' for profile in profiles.values()]
    assert "Roborock · S8 Pro Ultra" in labels
    assert labels.index("Ring · Video Doorbell 4") < labels.index("Roborock · S8 Pro Ultra")
    assert labels.index("Roborock · S8 Pro Ultra") < labels.index("Saft · LS 14250 1/2 AA")


def test_complete_bundled_catalog_survives_runtime_loader(tmp_path: Path) -> None:
    catalog_path = Path(__file__).parents[1] / "custom_components" / "battery_consumption" / "device_profiles.json"
    catalog = json.loads(catalog_path.read_text())
    profiles = load_device_profiles(str(tmp_path))

    assert catalog["catalog_version"]
    assert len(profiles) == len(catalog["devices"])
    assert set(profiles) == {profile["id"] for profile in catalog["devices"]}
    assert all(profile["origin"] == PROFILE_ORIGIN_BUNDLED for profile in profiles.values())


def test_selector_contains_every_loaded_profile_once(tmp_path: Path) -> None:
    profiles = load_device_profiles(str(tmp_path))
    options = profile_selector_options(profiles)
    values = [option["value"] for option in options]
    labels = [option["label"] for option in options]

    assert values == list(profiles)
    assert len(values) == len(set(values))
    assert len(labels) == len(set(labels))
    assert labels == sorted(labels, key=str.casefold)


def test_profile_origin_tracks_user_additions_and_overrides(tmp_path: Path) -> None:
    user_profiles = {
        "schema_version": 1,
        "devices": [
            {
                "id": "google_pixel_8_pro",
                "manufacturer": "Google",
                "model": "Pixel 8 Pro override",
                "capacity": 20,
                "capacity_unit": "Wh",
            },
            {
                "id": "user_device",
                "manufacturer": "User",
                "model": "Device",
                "capacity": 10,
                "capacity_unit": "Wh",
            },
        ],
    }
    (tmp_path / "battery_consumption_device_profiles.json").write_text(json.dumps(user_profiles))

    profiles = load_device_profiles(str(tmp_path))
    assert profiles["google_pixel_8_pro"]["origin"] == PROFILE_ORIGIN_USER
    assert profiles["user_device"]["origin"] == PROFILE_ORIGIN_USER
    assert profiles["meta_quest_2"]["origin"] == PROFILE_ORIGIN_BUNDLED


def test_duplicate_bundled_id_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "profiles.json"
    profile = {
        "id": "duplicate",
        "manufacturer": "Example",
        "model": "Device",
        "capacity": 10,
        "capacity_unit": "Wh",
    }
    path.write_text(json.dumps({"schema_version": 1, "devices": [profile, profile]}))

    import pytest
    with pytest.raises(ValueError, match="Duplicate battery profile id duplicate"):
        _load_file(path, required=True, origin=PROFILE_ORIGIN_BUNDLED)


def test_device_profile_suggestion_priority_and_ambiguity(tmp_path: Path) -> None:
    profiles = load_device_profiles(str(tmp_path))
    assert suggest_device_profile(profiles, "Roborock", "S8 Pro Ultra") == "roborock_s8_pro_ultra"
    assert suggest_device_profile(profiles, "Roborock", "Roborock S8 Pro Ultra") == "roborock_s8_pro_ultra"
    assert suggest_device_profile(profiles, "Google", "Google Pixel 8 Pro") == "google_pixel_8_pro"
    assert suggest_device_profile(profiles, "Unknown", "Device") is None


def test_device_profile_suggestion_does_not_guess_ambiguous_match() -> None:
    profiles = {
        "first": {"manufacturer": "Example", "model": "Battery A", "model_aliases": ["Shared"]},
        "second": {"manufacturer": "Example", "model": "Battery B", "model_aliases": ["Shared"]},
    }
    assert suggest_device_profile(profiles, "Example", "Shared") is None


def test_hardware_version_must_match_when_profile_restricts_it() -> None:
    profiles = {
        "device_v1": {
            "manufacturer": "Example",
            "model": "Device",
            "hardware_versions": ["v1"],
        }
    }
    assert suggest_device_profile(profiles, "Example", "Device", hardware_version="v1") == "device_v1"
    assert suggest_device_profile(profiles, "Example", "Device", hardware_version="v2") is None


def test_invalid_user_override_keeps_bundled_profile_and_reports_rejection(
    tmp_path: Path,
) -> None:
    user_profiles = {
        "schema_version": 1,
        "devices": [
            {
                "id": "google_pixel_8_pro",
                "manufacturer": "Google",
                "model": "Broken override",
                "capacity": 0,
                "capacity_unit": "Wh",
            }
        ],
    }
    (tmp_path / "battery_consumption_device_profiles.json").write_text(
        json.dumps(user_profiles)
    )

    profiles, report = load_device_profiles_with_report(str(tmp_path))

    assert profiles["google_pixel_8_pro"]["origin"] == PROFILE_ORIGIN_BUNDLED
    assert profiles["google_pixel_8_pro"]["model"] == "Pixel 8 Pro"
    assert report.rejected_user_entries == 1
    assert report.has_user_errors is True


def test_invalid_user_json_reports_error_without_breaking_bundled_profiles(
    tmp_path: Path,
) -> None:
    (tmp_path / "battery_consumption_device_profiles.json").write_text("not json")
    profiles, report = load_device_profiles_with_report(str(tmp_path))
    assert "google_pixel_8_pro" in profiles
    assert report.user_catalog_error == "invalid_json"
    assert report.has_user_errors is True
