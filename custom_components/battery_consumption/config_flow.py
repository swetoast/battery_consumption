"""Config flow for Battery Consumption."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ATTRIBUTE, CONF_SOURCE, CONF_UNIT_OF_MEASUREMENT
from homeassistant.data_entry_flow import ConfigFlowResult
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_CREATE_ACTIVITY_SENSOR,
    CONF_CREATE_CYCLE_SENSOR,
    CONF_MINIMUM_CHANGE,
    CONF_PRECISION,
    CONF_SESSION_TIMEOUT,
    DEFAULT_CREATE_ACTIVITY_SENSOR,
    DEFAULT_CREATE_CYCLE_SENSOR,
    DEFAULT_MINIMUM_CHANGE,
    DEFAULT_PRECISION,
    DEFAULT_SESSION_TIMEOUT,
    DOMAIN,
)


def _identity_schema() -> vol.Schema:
    """Build the schema for fields that identify the monitored value."""
    return vol.Schema(
        {
            vol.Required(CONF_SOURCE): cv.entity_id,
            vol.Optional(CONF_ATTRIBUTE): cv.string,
        }
    )


def _options_schema() -> vol.Schema:
    """Build the schema for calculation options."""
    return vol.Schema(
        {
            vol.Required(CONF_PRECISION, default=DEFAULT_PRECISION): vol.All(
                vol.Coerce(int), vol.Range(min=1)
            ),
            vol.Optional(
                CONF_BATTERY_CAPACITY, default=DEFAULT_PRECISION
            ): vol.All(vol.Coerce(float), vol.Range(min=0)),
            vol.Optional(CONF_UNIT_OF_MEASUREMENT): cv.string,
            vol.Required(
                CONF_MINIMUM_CHANGE, default=DEFAULT_MINIMUM_CHANGE
            ): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
            vol.Required(
                CONF_SESSION_TIMEOUT, default=DEFAULT_SESSION_TIMEOUT
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440)),
            vol.Required(
                CONF_CREATE_ACTIVITY_SENSOR,
                default=DEFAULT_CREATE_ACTIVITY_SENSOR,
            ): cv.boolean,
            vol.Required(
                CONF_CREATE_CYCLE_SENSOR,
                default=DEFAULT_CREATE_CYCLE_SENSOR,
            ): cv.boolean,
        }
    )


def _user_schema() -> vol.Schema:
    """Build the complete schema used when creating an entry."""
    return _identity_schema().extend(_options_schema().schema)


def _clean_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Convert empty optional text fields to missing values."""
    cleaned = dict(user_input)
    for key in (CONF_ATTRIBUTE, CONF_UNIT_OF_MEASUREMENT):
        if not cleaned.get(key):
            cleaned.pop(key, None)
    return cleaned


def _source_key(data: dict[str, Any]) -> tuple[str, str]:
    """Return the source and attribute pair used for duplicate detection."""
    return data[CONF_SOURCE], data.get(CONF_ATTRIBUTE, "")


class BatteryConsumptionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Battery Consumption."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create a Battery Consumption sensor."""
        if user_input is not None:
            data = _clean_input(user_input)
            source, attribute = _source_key(data)
            await self.async_set_unique_id(f"{source}:{attribute}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=source, data=data)

        return self.async_show_form(step_id="user", data_schema=_user_schema())

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the monitored source without changing entity identity."""
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            identity = _clean_input(user_input)
            wanted_key = _source_key(identity)
            for other_entry in self._async_current_entries():
                if other_entry.entry_id == entry.entry_id:
                    continue
                other_data = {**other_entry.data, **other_entry.options}
                if _source_key(other_data) == wanted_key:
                    return self.async_show_form(
                        step_id="reconfigure",
                        data_schema=self.add_suggested_values_to_schema(
                            _identity_schema(), identity
                        ),
                        errors={"base": "already_configured"},
                    )

            data = dict(entry.data)
            data.pop(CONF_SOURCE, None)
            data.pop(CONF_ATTRIBUTE, None)
            data.update(identity)
            return self.async_update_reload_and_abort(
                entry,
                data_updates=data,
            )

        current = {
            CONF_SOURCE: entry.data[CONF_SOURCE],
            CONF_ATTRIBUTE: entry.data.get(CONF_ATTRIBUTE, ""),
        }
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                _identity_schema(), current
            ),
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> BatteryConsumptionOptionsFlow:
        """Return the options flow handler."""
        return BatteryConsumptionOptionsFlow()


class BatteryConsumptionOptionsFlow(config_entries.OptionsFlow):
    """Handle Battery Consumption calculation options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage calculation options without changing sensor identity."""
        if user_input is not None:
            return self.async_create_entry(data=_clean_input(user_input))

        values = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _options_schema(), values
            ),
        )
