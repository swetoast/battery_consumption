"""Load and validate editable battery device profiles."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

_MATCH_SEPARATORS = " -_./()[]"

from .const import USER_DEVICE_PROFILES_FILE

_LOGGER = logging.getLogger(__name__)
_SUPPORTED_UNITS = {"mAh", "Wh", "kWh", "MWh"}
PROFILE_ORIGIN_BUNDLED = "bundled"
PROFILE_ORIGIN_USER = "user"


@dataclass
class ProfileLoadReport:
    """Summarize profile loading without exposing profile contents."""

    bundled_loaded: int = 0
    user_loaded: int = 0
    user_overrides: list[str] = field(default_factory=list)
    rejected_user_entries: int = 0
    user_catalog_error: str | None = None

    @property
    def has_user_errors(self) -> bool:
        """Return whether the user catalog requires attention."""
        return self.user_catalog_error is not None or self.rejected_user_entries > 0


def _validated_profile(raw: Any, source_name: str) -> dict[str, Any] | None:
    """Return a normalized profile or skip an invalid entry."""
    if not isinstance(raw, dict):
        _LOGGER.warning("Skipping non-object battery profile in %s", source_name)
        return None

    profile_id = raw.get("id")
    manufacturer = raw.get("manufacturer")
    model = raw.get("model")
    unit = raw.get("capacity_unit")
    try:
        capacity = float(raw.get("capacity"))
    except (TypeError, ValueError):
        capacity = 0

    if (
        not isinstance(profile_id, str)
        or not profile_id
        or slugify(profile_id) != profile_id
        or not isinstance(manufacturer, str)
        or not manufacturer.strip()
        or not isinstance(model, str)
        or not model.strip()
        or capacity <= 0
        or unit not in _SUPPORTED_UNITS
    ):
        _LOGGER.warning("Skipping invalid battery profile %s in %s", profile_id, source_name)
        return None

    voltage = raw.get("nominal_voltage")
    if unit == "mAh":
        try:
            voltage = float(voltage)
        except (TypeError, ValueError):
            voltage = 0
        if voltage <= 0:
            _LOGGER.warning(
                "Skipping mAh battery profile %s without nominal voltage in %s",
                profile_id,
                source_name,
            )
            return None
    else:
        voltage = None

    profile = {
        "id": profile_id,
        "manufacturer": manufacturer.strip(),
        "model": model.strip(),
        "capacity": capacity,
        "capacity_unit": unit,
        "nominal_voltage": voltage,
    }
    if isinstance(raw.get("source"), str):
        profile["source"] = raw["source"]
    if isinstance(raw.get("notes"), str):
        profile["notes"] = raw["notes"]
    for key in ("model_aliases", "model_ids", "hardware_versions"):
        values = raw.get(key)
        if isinstance(values, list) and all(
            isinstance(value, str) and value.strip() for value in values
        ):
            profile[key] = [value.strip() for value in values]
    return profile


def _load_file_with_report(
    path: Path, required: bool, origin: str
) -> tuple[dict[str, dict[str, Any]], int, str | None]:
    """Load one profile file and return profiles, rejection count, and error."""
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return {}, 0, None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        if required:
            raise
        _LOGGER.error("Could not load user battery profiles from %s: %s", path, err)
        return {}, 0, "invalid_json"

    if not isinstance(data, dict) or data.get("schema_version") != 1:
        if required:
            raise ValueError(f"Invalid bundled battery profile catalog: {path}")
        _LOGGER.error("Ignoring %s because schema_version is not 1", path)
        return {}, 0, "unsupported_schema"

    devices = data.get("devices")
    if not isinstance(devices, list):
        if required:
            raise ValueError(f"Invalid bundled battery profile devices: {path}")
        _LOGGER.error("Ignoring %s because devices is not a list", path)
        return {}, 0, "invalid_devices"

    profiles: dict[str, dict[str, Any]] = {}
    rejected = 0
    for raw in devices:
        profile = _validated_profile(raw, str(path))
        if profile is None:
            rejected += 1
            continue
        profile_id = profile["id"]
        if profile_id in profiles:
            message = f"Duplicate battery profile id {profile_id} in {path}"
            if required:
                raise ValueError(message)
            _LOGGER.error(message)
            rejected += 1
            continue
        profile["origin"] = origin
        profiles[profile_id] = profile
    return profiles, rejected, None


def _load_file(
    path: Path, required: bool, origin: str
) -> dict[str, dict[str, Any]]:
    """Load one profile file and retain its origin internally."""
    profiles, _, _ = _load_file_with_report(path, required, origin)
    return profiles


def load_device_profiles_with_report(
    config_dir: str,
) -> tuple[dict[str, dict[str, Any]], ProfileLoadReport]:
    """Load profiles and return a sanitized outcome report."""
    bundled_path = Path(__file__).with_name("device_profiles.json")
    profiles, bundled_rejected, _ = _load_file_with_report(
        bundled_path, required=True, origin=PROFILE_ORIGIN_BUNDLED
    )
    if bundled_rejected:
        raise ValueError("Bundled battery profile catalog contains rejected entries")

    report = ProfileLoadReport(bundled_loaded=len(profiles))
    user_path = Path(config_dir) / USER_DEVICE_PROFILES_FILE
    user_profiles, rejected, user_error = _load_file_with_report(
        user_path, required=False, origin=PROFILE_ORIGIN_USER
    )
    report.rejected_user_entries = rejected
    report.user_catalog_error = user_error
    report.user_loaded = len(user_profiles)
    report.user_overrides = sorted(profiles.keys() & user_profiles.keys())
    for profile_id in report.user_overrides:
        _LOGGER.warning(
            "User battery profile overrides bundled profile: %s", profile_id
        )
    profiles.update(user_profiles)
    return (
        dict(
            sorted(
                profiles.items(),
                key=lambda item: (
                    item[1]["manufacturer"].casefold(),
                    item[1]["model"].casefold(),
                ),
            )
        ),
        report,
    )


def load_device_profiles(config_dir: str) -> dict[str, dict[str, Any]]:
    """Load bundled profiles and apply valid user additions or overrides."""
    profiles, _ = load_device_profiles_with_report(config_dir)
    return profiles


def _normalized_match_value(value: str | None) -> str:
    """Normalize device metadata for conservative profile matching."""
    if not value:
        return ""
    normalized = value.casefold().strip()
    for separator in _MATCH_SEPARATORS:
        normalized = normalized.replace(separator, "")
    return normalized


def suggest_device_profile(
    profiles: dict[str, dict[str, Any]],
    manufacturer: str | None,
    model: str | None,
    model_id: str | None = None,
    hardware_version: str | None = None,
) -> str | None:
    """Return one unambiguous profile suggestion from device metadata."""
    wanted_manufacturer = _normalized_match_value(manufacturer)
    wanted_model = _normalized_match_value(model)
    wanted_model_id = _normalized_match_value(model_id)
    wanted_hardware = _normalized_match_value(hardware_version)
    if not wanted_manufacturer:
        return None

    ranked: dict[int, list[str]] = {1: [], 2: [], 3: [], 4: []}
    for profile_id, profile in profiles.items():
        if _normalized_match_value(profile["manufacturer"]) != wanted_manufacturer:
            continue
        exact_model = profile["model"].casefold().strip() == (model or "").casefold().strip()
        normalized_model = _normalized_match_value(profile["model"]) == wanted_model
        aliases = {_normalized_match_value(value) for value in profile.get("model_aliases", [])}
        model_ids = {_normalized_match_value(value) for value in profile.get("model_ids", [])}
        hardware_versions = {
            _normalized_match_value(value)
            for value in profile.get("hardware_versions", [])
        }
        if wanted_hardware and hardware_versions and wanted_hardware not in hardware_versions:
            continue
        if exact_model and wanted_model:
            ranked[1].append(profile_id)
        elif wanted_model_id and wanted_model_id in model_ids:
            ranked[2].append(profile_id)
        elif wanted_model and wanted_model in aliases:
            ranked[3].append(profile_id)
        elif wanted_model and normalized_model:
            ranked[4].append(profile_id)

    for rank in (1, 2, 3, 4):
        if len(ranked[rank]) == 1:
            return ranked[rank][0]
        if ranked[rank]:
            return None
    return None


def profile_selector_options(
    profiles: dict[str, dict[str, Any]],
) -> list[dict[str, str]]:
    """Return the exact options used by the Home Assistant selector."""
    return [
        {
            "value": profile_id,
            "label": f"{profile['manufacturer']} · {profile['model']}",
        }
        for profile_id, profile in profiles.items()
    ]


async def async_load_device_profiles(
    hass: HomeAssistant,
) -> dict[str, dict[str, Any]]:
    """Load profiles outside the Home Assistant event loop."""
    return await hass.async_add_executor_job(load_device_profiles, hass.config.config_dir)


async def async_load_device_profiles_with_report(
    hass: HomeAssistant,
) -> tuple[dict[str, dict[str, Any]], ProfileLoadReport]:
    """Load profiles and report outside the Home Assistant event loop."""
    return await hass.async_add_executor_job(
        load_device_profiles_with_report, hass.config.config_dir
    )
