"""Diagnostics for Battery Consumption."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ATTRIBUTE,
    CONF_SOURCE,
    CONF_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant

from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_BATTERY_VOLTAGE,
    CONF_DEVICE_PROFILE,
)
from .device_profiles import async_load_device_profiles_with_report
from .entry_config import COMPANION_KEYS as _COMPANION_KEYS
from .entry_config import effective_entry_config


def _catalog_metadata() -> dict[str, Any]:
    """Return non-sensitive bundled catalog metadata."""
    component_path = Path(__file__).parent
    try:
        catalog = json.loads(
            (component_path / "device_profiles.json").read_text(encoding="utf-8")
        )
        manifest = json.loads(
            (component_path / "manifest.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return {
            "integration_version": None,
            "schema_version": None,
            "catalog_version": None,
        }
    return {
        "integration_version": manifest.get("version"),
        "schema_version": catalog.get("schema_version"),
        "catalog_version": catalog.get("catalog_version"),
    }


def _source_diagnostics(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Describe source validity without exposing its entity ID or value."""
    source_entity_id = data.get(CONF_SOURCE)
    source = hass.states.get(source_entity_id) if source_entity_id else None
    source_attribute = data.get(CONF_ATTRIBUTE)
    value: Any = source.attributes.get(source_attribute) if source and source_attribute else (
        source.state if source else None
    )
    numeric = False
    if source is not None and source.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        try:
            float(value)
            numeric = True
        except (TypeError, ValueError):
            pass
    return {
        "domain": source_entity_id.split(".", 1)[0] if source_entity_id and "." in source_entity_id else None,
        "attribute_configured": bool(source_attribute),
        "exists": source is not None,
        "available": source is not None and source.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE),
        "numeric": numeric,
    }


def _companion_diagnostics(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, Any]:
    """Describe configured optional inputs by type only."""
    configured = [key for key in _COMPANION_KEYS if data.get(key)]
    available = [
        key
        for key in configured
        if (state := hass.states.get(data[key])) is not None
        and state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE)
    ]
    return {
        "configured_types": configured,
        "available_types": available,
        "configured_count": len(configured),
        "available_count": len(available),
    }


def _profile_diagnostics(
    data: dict[str, Any], profiles: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Describe the selected profile without exposing catalog notes or sources."""
    profile_id = data.get(CONF_DEVICE_PROFILE)
    manual = profile_id in (None, "manual")
    profile = profiles.get(profile_id) if profile_id and not manual else None
    return {
        "selected_id": profile_id,
        "manual_configuration": manual,
        "exists": None if manual else profile is not None,
        "origin": profile.get("origin") if profile else None,
        "manufacturer": profile.get("manufacturer") if profile else None,
        "model": profile.get("model") if profile else None,
        "capacity": data.get(CONF_BATTERY_CAPACITY),
        "capacity_unit": data.get(CONF_UNIT_OF_MEASUREMENT),
        "nominal_voltage": data.get(CONF_BATTERY_VOLTAGE),
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return sanitized diagnostics for a config entry."""
    data = effective_entry_config(entry)
    profiles, report = await async_load_device_profiles_with_report(hass)
    origins = [profile.get("origin") for profile in profiles.values()]
    return {
        "integration": {
            "entry_version": entry.version,
            "entry_minor_version": entry.minor_version,
            **_catalog_metadata(),
        },
        "source": _source_diagnostics(hass, data),
        "profile": _profile_diagnostics(data, profiles),
        "companion_inputs": _companion_diagnostics(hass, data),
        "profile_catalog": {
            "loaded_total": len(profiles),
            "bundled_loaded": origins.count("bundled"),
            "user_loaded": origins.count("user"),
            "user_override_count": len(report.user_overrides),
            "rejected_user_entries": report.rejected_user_entries,
            "user_catalog_error": report.user_catalog_error,
        },
    }
