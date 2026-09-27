"""Load and validate editable battery device profiles."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import slugify

from .const import USER_DEVICE_PROFILES_FILE

_LOGGER = logging.getLogger(__name__)
_SUPPORTED_UNITS = {"mAh", "Wh", "kWh", "MWh"}


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
    return profile


def _load_file(path: Path, required: bool) -> dict[str, dict[str, Any]]:
    """Load one profile file."""
    if not path.exists():
        if required:
            raise FileNotFoundError(path)
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        if required:
            raise
        _LOGGER.error("Could not load user battery profiles from %s: %s", path, err)
        return {}

    if not isinstance(data, dict) or data.get("schema_version") != 1:
        if required:
            raise ValueError(f"Invalid bundled battery profile catalog: {path}")
        _LOGGER.error("Ignoring %s because schema_version is not 1", path)
        return {}

    profiles: dict[str, dict[str, Any]] = {}
    devices = data.get("devices", [])
    if not isinstance(devices, list):
        devices = []
    for raw in devices:
        profile = _validated_profile(raw, str(path))
        if profile is not None:
            profiles[profile["id"]] = profile
    return profiles


def load_device_profiles(config_dir: str) -> dict[str, dict[str, Any]]:
    """Load bundled profiles and apply user additions or overrides."""
    bundled_path = Path(__file__).with_name("device_profiles.json")
    profiles = _load_file(bundled_path, required=True)
    user_path = Path(config_dir) / USER_DEVICE_PROFILES_FILE
    profiles.update(_load_file(user_path, required=False))
    return dict(
        sorted(
            profiles.items(),
            key=lambda item: (
                item[1]["manufacturer"].casefold(),
                item[1]["model"].casefold(),
            ),
        )
    )


async def async_load_device_profiles(
    hass: HomeAssistant,
) -> dict[str, dict[str, Any]]:
    """Load profiles outside the Home Assistant event loop."""
    return await hass.async_add_executor_job(load_device_profiles, hass.config.config_dir)
