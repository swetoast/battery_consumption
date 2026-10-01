"""Effective configuration shared by every part of the integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_UNIT_OF_MEASUREMENT

from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_BATTERY_VOLTAGE,
    CONF_COMPANION_BATTERY_CYCLE_COUNT,
    CONF_COMPANION_BATTERY_HEALTH,
    CONF_COMPANION_BATTERY_POWER,
    CONF_COMPANION_BATTERY_STATE,
    CONF_COMPANION_BATTERY_TEMPERATURE,
    CONF_COMPANION_CHARGER_TYPE,
    CONF_COMPANION_IS_CHARGING,
    CONF_COMPANION_REMAINING_CHARGE_TIME,
    CONF_CREATE_ACTIVITY_SENSOR,
    CONF_CREATE_CYCLE_SENSOR,
    CONF_CREATE_POWER_SENSOR,
    CONF_DEVICE_PROFILE,
    CONF_MINIMUM_CHANGE,
    CONF_PRECISION,
    CONF_SESSION_TIMEOUT,
)

COMPANION_KEYS: tuple[str, ...] = (
    CONF_COMPANION_IS_CHARGING,
    CONF_COMPANION_BATTERY_STATE,
    CONF_COMPANION_CHARGER_TYPE,
    CONF_COMPANION_BATTERY_POWER,
    CONF_COMPANION_BATTERY_TEMPERATURE,
    CONF_COMPANION_BATTERY_HEALTH,
    CONF_COMPANION_BATTERY_CYCLE_COUNT,
    CONF_COMPANION_REMAINING_CHARGE_TIME,
)

# Keys owned by the options flow. Once options exist they replace these keys
# from the original entry data as a complete set, so a value the user cleared
# in options can never fall back to the value stored at setup time.
CALCULATION_KEYS: frozenset[str] = frozenset(
    {
        CONF_DEVICE_PROFILE,
        CONF_PRECISION,
        CONF_BATTERY_CAPACITY,
        CONF_UNIT_OF_MEASUREMENT,
        CONF_BATTERY_VOLTAGE,
        CONF_MINIMUM_CHANGE,
        CONF_SESSION_TIMEOUT,
        CONF_CREATE_ACTIVITY_SENSOR,
        CONF_CREATE_CYCLE_SENSOR,
        CONF_CREATE_POWER_SENSOR,
        *COMPANION_KEYS,
    }
)


def effective_config(data: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    """Return entry data with options applied as a complete calculation set."""
    conf = dict(data)
    if options:
        for key in CALCULATION_KEYS:
            conf.pop(key, None)
        conf.update(options)
    return conf


def effective_entry_config(entry: ConfigEntry) -> dict[str, Any]:
    """Return the configuration a config entry is actually running with."""
    return effective_config(dict(entry.data), dict(entry.options))
