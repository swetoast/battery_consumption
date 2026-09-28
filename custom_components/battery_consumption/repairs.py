"""Actionable repair issues for Battery Consumption."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ATTRIBUTE,
    CONF_SOURCE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir

from .const import (
    CONF_COMPANION_BATTERY_CYCLE_COUNT,
    CONF_COMPANION_BATTERY_HEALTH,
    CONF_COMPANION_BATTERY_POWER,
    CONF_COMPANION_BATTERY_STATE,
    CONF_COMPANION_BATTERY_TEMPERATURE,
    CONF_COMPANION_CHARGER_TYPE,
    CONF_COMPANION_IS_CHARGING,
    CONF_COMPANION_REMAINING_CHARGE_TIME,
    CONF_DEVICE_PROFILE,
    CONF_TRACKER_NAME,
    DEVICE_PROFILE_MANUAL,
    DOMAIN,
)
from .device_profiles import async_load_device_profiles_with_report

_COMPANION_KEYS = (
    CONF_COMPANION_IS_CHARGING,
    CONF_COMPANION_BATTERY_STATE,
    CONF_COMPANION_CHARGER_TYPE,
    CONF_COMPANION_BATTERY_POWER,
    CONF_COMPANION_BATTERY_TEMPERATURE,
    CONF_COMPANION_BATTERY_HEALTH,
    CONF_COMPANION_BATTERY_CYCLE_COUNT,
    CONF_COMPANION_REMAINING_CHARGE_TIME,
)


def _issue_id(kind: str, entry_id: str) -> str:
    """Return an issue ID scoped to one config entry."""
    return f"{kind}_{entry_id}"


def _entry_data(entry: ConfigEntry) -> dict[str, Any]:
    """Return effective config-entry data."""
    return {**entry.data, **entry.options}


def _companion_mismatches(
    hass: HomeAssistant, data: dict[str, Any]
) -> list[str]:
    """Return configured supporting entities owned by another device."""
    source_entity_id = data.get(CONF_SOURCE)
    if not source_entity_id:
        return []
    registry = er.async_get(hass)
    source = registry.async_get(source_entity_id)
    if source is None or source.device_id is None:
        return []

    mismatches = []
    for key in _COMPANION_KEYS:
        entity_id = data.get(key)
        if not entity_id:
            continue
        companion = registry.async_get(entity_id)
        if (
            companion is not None
            and companion.device_id is not None
            and companion.device_id != source.device_id
        ):
            mismatches.append(key)
    return mismatches


def _source_missing(hass: HomeAssistant, data: dict[str, Any]) -> bool:
    """Return whether the configured source no longer exists anywhere."""
    entity_id = data.get(CONF_SOURCE)
    if not entity_id:
        return True
    return (
        er.async_get(hass).async_get(entity_id) is None
        and hass.states.get(entity_id) is None
    )


def _source_attribute_missing(
    hass: HomeAssistant, data: dict[str, Any]
) -> bool:
    """Return whether an available source lacks its configured attribute."""
    attribute = data.get(CONF_ATTRIBUTE)
    entity_id = data.get(CONF_SOURCE)
    if not attribute or not entity_id:
        return False
    state = hass.states.get(entity_id)
    if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        return False
    return attribute not in state.attributes


def _missing_companion_types(
    hass: HomeAssistant, data: dict[str, Any]
) -> list[str]:
    """Return configured supporting input types whose entities were removed."""
    registry = er.async_get(hass)
    missing = []
    for key in _COMPANION_KEYS:
        entity_id = data.get(key)
        if not entity_id:
            continue
        if registry.async_get(entity_id) is None and hass.states.get(entity_id) is None:
            missing.append(key)
    return missing


def _create_issue(
    hass: HomeAssistant,
    entry: ConfigEntry,
    kind: str,
    placeholders: dict[str, str],
) -> None:
    """Create one actionable repair issue."""
    ir.async_create_issue(
        hass,
        DOMAIN,
        _issue_id(kind, entry.entry_id),
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.ERROR,
        translation_key=kind,
        translation_placeholders=placeholders,
    )


def _delete_issue(hass: HomeAssistant, entry: ConfigEntry, kind: str) -> None:
    """Delete a resolved repair issue."""
    ir.async_delete_issue(hass, DOMAIN, _issue_id(kind, entry.entry_id))


async def async_update_entry_repairs(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Create or clear repair issues for one config entry."""
    data = _entry_data(entry)
    tracker_name = str(data.get(CONF_TRACKER_NAME, entry.title))
    profiles, profile_report = await async_load_device_profiles_with_report(hass)
    profile_id = data.get(CONF_DEVICE_PROFILE, DEVICE_PROFILE_MANUAL)

    if profile_report.has_user_errors:
        _create_issue(
            hass,
            entry,
            "user_profile_catalog_invalid",
            {
                "tracker_name": tracker_name,
                "rejected_count": str(profile_report.rejected_user_entries),
            },
        )
    else:
        _delete_issue(hass, entry, "user_profile_catalog_invalid")

    if _source_missing(hass, data):
        _create_issue(
            hass,
            entry,
            "user_profile_catalog_invalid",
        "source_missing",
            {"tracker_name": tracker_name},
        )
    else:
        _delete_issue(hass, entry, "source_missing")

    if _source_attribute_missing(hass, data):
        _create_issue(
            hass,
            entry,
            "source_attribute_missing",
            {
                "tracker_name": tracker_name,
                "attribute": str(data.get(CONF_ATTRIBUTE)),
            },
        )
    else:
        _delete_issue(hass, entry, "source_attribute_missing")

    missing_companions = _missing_companion_types(hass, data)
    if missing_companions:
        _create_issue(
            hass,
            entry,
            "companion_entity_missing",
            {
                "tracker_name": tracker_name,
                "count": str(len(missing_companions)),
            },
        )
    else:
        _delete_issue(hass, entry, "companion_entity_missing")

    if profile_id != DEVICE_PROFILE_MANUAL and profile_id not in profiles:
        _create_issue(
            hass,
            entry,
            "profile_missing",
            {"tracker_name": tracker_name, "profile_id": str(profile_id)},
        )
    else:
        _delete_issue(hass, entry, "profile_missing")

    mismatches = _companion_mismatches(hass, data)
    if mismatches:
        _create_issue(
            hass,
            entry,
            "companion_device_mismatch",
            {
                "tracker_name": tracker_name,
                "count": str(len(mismatches)),
            },
        )
    else:
        _delete_issue(hass, entry, "companion_device_mismatch")


async def async_delete_entry_repairs(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Delete repair issues when a config entry is removed."""
    for kind in (
        "source_missing",
        "source_attribute_missing",
        "companion_entity_missing",
        "profile_missing",
        "companion_device_mismatch",
    ):
        _delete_issue(hass, entry, kind)
