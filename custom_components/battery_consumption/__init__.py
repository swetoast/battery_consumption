"""The Battery Consumption integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ATTRIBUTE,
    CONF_SOURCE,
    CONF_UNIQUE_ID,
    CONF_UNIT_OF_MEASUREMENT,
    Platform,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import service
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.event import (
    async_track_entity_registry_updated_event,
    async_track_state_change_event,
)
from homeassistant.helpers.start import async_at_started

from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_BATTERY_CONSUMPTION,
    CONF_BATTERY_VOLTAGE,
    CONF_MINIMUM_CHANGE,
    CONF_PRECISION,
    CONF_SESSION_TIMEOUT,
    DATA_BATTERY_CONSUMPTION,
    DEFAULT_MINIMUM_CHANGE,
    DEFAULT_PRECISION,
    DEFAULT_SESSION_TIMEOUT,
    DOMAIN,
)
from .entry_config import COMPANION_KEYS, effective_entry_config
from .repairs import (
    async_delete_entry_repairs,
    async_update_entry_repairs,
    has_source_issue,
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
    """Set up Battery Consumption from YAML and register shared actions."""
    hass.data.setdefault(DATA_BATTERY_CONSUMPTION, {})

    # Registered once for every tracker, whether set up from YAML or the UI.
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        "reset_totals",
        entity_domain=Platform.SENSOR,
        schema=None,
        func="async_reset_totals",
    )

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
    _async_setup_entry_repairs(hass, entry)
    return True


@callback
def _async_setup_entry_repairs(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Check repairs once Home Assistant has started, then on relevant changes."""
    conf = effective_entry_config(entry)
    source = conf.get(CONF_SOURCE)
    watched = [entity_id for entity_id in (source, *(conf.get(key) for key in COMPANION_KEYS)) if entity_id]

    async def _async_check(_hass: HomeAssistant | None = None) -> None:
        await async_update_entry_repairs(hass, entry)

    @callback
    def _registry_updated(_event: Event[Any]) -> None:
        entry.async_create_task(hass, _async_check(), f"{DOMAIN} repairs")

    @callback
    def _source_changed(_event: Event[Any]) -> None:
        # Cheap guard: only re-check while a source issue is open, so normal
        # battery updates never reload the profile catalog.
        if has_source_issue(hass, entry):
            _registry_updated(_event)

    # Waiting for startup avoids false "source missing" issues for entities
    # whose integrations load after this one.
    entry.async_on_unload(async_at_started(hass, _async_check))
    if watched:
        entry.async_on_unload(
            async_track_entity_registry_updated_event(hass, watched, _registry_updated)
        )
    if source:
        entry.async_on_unload(
            async_track_state_change_event(hass, [source], _source_changed)
        )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Battery Consumption config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove repair issues belonging to a deleted config entry."""
    await async_delete_entry_repairs(hass, entry)


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload a config entry after its options change."""
    await hass.config_entries.async_reload(entry.entry_id)
