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
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir

from .const import (
    CONF_DEVICE_PROFILE,
    CONF_TRACKER_NAME,
    DEVICE_PROFILE_MANUAL,
    DOMAIN,
)
from .device_profiles import async_load_device_profiles_with_report
from .entry_config import COMPANION_KEYS as _COMPANION_KEYS
from .entry_config import effective_entry_config

# One custom profile file serves every tracker, so its issue is global.
USER_CATALOG_ISSUE_ID = "user_profile_catalog_invalid"

_ENTRY_ISSUE_KINDS = (
    "source_missing",
    "source_attribute_missing",
    "companion_entity_missing",
    "profile_missing",
    "companion_device_mismatch",
)
_SOURCE_ISSUE_KINDS = ("source_missing", "source_attribute_missing")


def _issue_id(kind: str, entry_id: str) -> str:
    """Return an issue ID scoped to one config entry."""
    return f"{kind}_{entry_id}"


def _entry_data(entry: ConfigEntry) -> dict[str, Any]:
    """Return the configuration the entry is actually running with."""
    return effective_entry_config(entry)


def has_source_issue(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Return whether a source-related issue is open for this entry."""
    registry = ir.async_get(hass)
    return any(
        registry.async_get_issue(DOMAIN, _issue_id(kind, entry.entry_id)) is not None
        for kind in _SOURCE_ISSUE_KINDS
    )


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

    # Earlier versions created this issue once per entry.
    _delete_issue(hass, entry, USER_CATALOG_ISSUE_ID)
    if profile_report.has_user_errors:
        ir.async_create_issue(
            hass,
            DOMAIN,
            USER_CATALOG_ISSUE_ID,
            is_fixable=False,
            is_persistent=True,
            severity=ir.IssueSeverity.ERROR,
            translation_key=USER_CATALOG_ISSUE_ID,
            translation_placeholders={
                "rejected_count": str(profile_report.rejected_user_entries),
            },
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, USER_CATALOG_ISSUE_ID)

    if _source_missing(hass, data):
        _create_issue(
            hass,
            entry,
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
    for kind in (*_ENTRY_ISSUE_KINDS, USER_CATALOG_ISSUE_ID):
        _delete_issue(hass, entry, kind)
    remaining = [
        other
        for other in hass.config_entries.async_entries(DOMAIN)
        if other.entry_id != entry.entry_id
    ]
    if not remaining:
        ir.async_delete_issue(hass, DOMAIN, USER_CATALOG_ISSUE_ID)
