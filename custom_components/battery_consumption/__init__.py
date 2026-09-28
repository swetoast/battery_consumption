"""The Battery Consumption integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ATTRIBUTE,
    CONF_SOURCE,
    CONF_UNIQUE_ID,
    CONF_UNIT_OF_MEASUREMENT,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.discovery import async_load_platform

from .repairs import async_delete_entry_repairs, async_update_entry_repairs

from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_BATTERY_VOLTAGE,
    CONF_BATTERY_CONSUMPTION,
    CONF_MINIMUM_CHANGE,
    CONF_PRECISION,
    CONF_SESSION_TIMEOUT,
    DATA_BATTERY_CONSUMPTION,
    DEFAULT_MINIMUM_CHANGE,
    DEFAULT_PRECISION,
    DEFAULT_SESSION_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


def _validate_battery_configuration(config: dict) -> dict:
    """Require an explicit nominal voltage for mAh capacity."""
    if (
        config.get(CONF_BATTERY_CAPACITY) is not None
        and config.get(CONF_UNIT_OF_MEASUREMENT) == "mAh"
        and config.get(CONF_BATTERY_VOLTAGE) is None
    ):
        raise vol.Invalid("battery_voltage is required when capacity is in mAh")
    return config


BATTERY_CONSUMPTION_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required(CONF_SOURCE): cv.entity_id,
            vol.Optional(CONF_UNIQUE_ID): cv.string,
            vol.Optional(CONF_ATTRIBUTE): cv.string,
            vol.Optional(CONF_PRECISION, default=DEFAULT_PRECISION): cv.positive_int,
            vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
            vol.Optional(CONF_BATTERY_CAPACITY): cv.positive_float,
            vol.Optional(CONF_BATTERY_VOLTAGE): cv.positive_float,
            vol.Optional(
                CONF_MINIMUM_CHANGE, default=DEFAULT_MINIMUM_CHANGE
            ): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
            vol.Optional(
                CONF_SESSION_TIMEOUT, default=DEFAULT_SESSION_TIMEOUT
            ): vol.All(vol.Coerce(int), vol.Range(min=1)),
        }
    ),
    _validate_battery_configuration,
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({cv.slug: BATTERY_CONSUMPTION_SCHEMA})},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Battery Consumption from YAML."""
    hass.data.setdefault(DATA_BATTERY_CONSUMPTION, {})

    for battery_consumption, conf in config.get(DOMAIN, {}).items():
        _LOGGER.debug("Set up %s.%s", DOMAIN, battery_consumption)
        hass.data[DATA_BATTERY_CONSUMPTION][battery_consumption] = dict(conf)
        hass.async_create_task(
            async_load_platform(
                hass,
                Platform.SENSOR,
                DOMAIN,
                {CONF_BATTERY_CONSUMPTION: battery_consumption},
                config,
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Battery Consumption from a config entry."""
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_update_entry_repairs(hass, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Battery Consumption config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove repair issues belonging to a deleted config entry."""
    await async_delete_entry_repairs(hass, entry)


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload a config entry after its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
