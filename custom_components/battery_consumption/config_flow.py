"""Config flow for Battery Consumption."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_ATTRIBUTE, CONF_SOURCE, CONF_UNIT_OF_MEASUREMENT
from homeassistant.helpers import config_validation as cv, selector
from homeassistant.util import slugify

from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_BATTERY_VOLTAGE,
    CONF_CREATE_ACTIVITY_SENSOR,
    CONF_CREATE_CYCLE_SENSOR,
    CONF_CREATE_POWER_SENSOR,
    CONF_DEVICE_PROFILE,
    CONF_MINIMUM_CHANGE,
    CONF_PRECISION,
    CONF_SESSION_TIMEOUT,
    CONF_TRACKER_NAME,
    DEFAULT_CREATE_ACTIVITY_SENSOR,
    DEFAULT_CREATE_CYCLE_SENSOR,
    DEFAULT_CREATE_POWER_SENSOR,
    DEFAULT_MINIMUM_CHANGE,
    DEFAULT_PRECISION,
    DEFAULT_SESSION_TIMEOUT,
    DEVICE_PROFILE_MANUAL,
    DOMAIN,
)
from .device_profiles import async_load_device_profiles

CONF_CONFIGURATION_MODE = "configuration_mode"
CONFIGURATION_MODE_PROFILE = "profile"
CONFIGURATION_MODE_MANUAL = "manual"


def _identity_schema() -> vol.Schema:
    """Build the schema for fields that identify the tracker."""
    return vol.Schema(
        {
            vol.Required(CONF_TRACKER_NAME): vol.All(cv.string, vol.Length(min=1)),
            vol.Required(CONF_SOURCE): selector.EntitySelector(),
            vol.Optional(CONF_ATTRIBUTE): cv.string,
        }
    )


def _configuration_mode_schema(default: str) -> vol.Schema:
    """Build the schema that chooses profile or manual capacity configuration."""
    return vol.Schema(
        {
            vol.Required(CONF_CONFIGURATION_MODE, default=default): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": CONFIGURATION_MODE_PROFILE, "label": "Device profile"},
                        {"value": CONFIGURATION_MODE_MANUAL, "label": "Manual configuration"},
                    ],
                    mode=selector.SelectSelectorMode.LIST,
                )
            )
        }
    )


def _profile_selector(profiles: dict[str, dict[str, Any]]) -> selector.SelectSelector:
    """Build a searchable device profile selector."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                {
                    "value": profile_id,
                    "label": f"{profile['manufacturer']} · {profile['model']}",
                }
                for profile_id, profile in profiles.items()
            ],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _common_options_schema() -> vol.Schema:
    """Build calculation options shared by profile and manual modes."""
    return vol.Schema(
        {
            vol.Required(CONF_PRECISION, default=DEFAULT_PRECISION): vol.All(
                vol.Coerce(int), vol.Range(min=1)
            ),
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
            vol.Required(
                CONF_CREATE_POWER_SENSOR,
                default=DEFAULT_CREATE_POWER_SENSOR,
            ): cv.boolean,
        }
    )


def _profile_options_schema(profiles: dict[str, dict[str, Any]]) -> vol.Schema:
    """Build options for a known device profile."""
    return vol.Schema(
        {vol.Required(CONF_DEVICE_PROFILE): _profile_selector(profiles)}
    ).extend(_common_options_schema().schema)


def _manual_options_schema() -> vol.Schema:
    """Build options for manually entered battery specifications."""
    return vol.Schema(
        {
            vol.Optional(CONF_BATTERY_CAPACITY): vol.All(
                vol.Coerce(float), vol.Range(min=0)
            ),
            vol.Optional(CONF_UNIT_OF_MEASUREMENT): vol.In(
                ["mAh", "Wh", "kWh", "MWh"]
            ),
            vol.Optional(CONF_BATTERY_VOLTAGE, default=3.85): vol.All(
                vol.Coerce(float), vol.Range(min=0.1)
            ),
        }
    ).extend(_common_options_schema().schema)


def _clean_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Convert empty optional text fields to missing values."""
    cleaned = dict(user_input)
    if not cleaned.get(CONF_ATTRIBUTE):
        cleaned.pop(CONF_ATTRIBUTE, None)
    return cleaned


def _apply_device_profile(
    data: dict[str, Any], profiles: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Resolve the selected device profile into battery calculation settings."""
    result = dict(data)
    profile_id = result.get(CONF_DEVICE_PROFILE, DEVICE_PROFILE_MANUAL)
    if profile_id == DEVICE_PROFILE_MANUAL:
        result[CONF_DEVICE_PROFILE] = DEVICE_PROFILE_MANUAL
        if not result.get(CONF_BATTERY_CAPACITY):
            result.pop(CONF_BATTERY_CAPACITY, None)
            result.pop(CONF_UNIT_OF_MEASUREMENT, None)
            result.pop(CONF_BATTERY_VOLTAGE, None)
        elif result.get(CONF_UNIT_OF_MEASUREMENT) == "mAh":
            result.setdefault(CONF_BATTERY_VOLTAGE, 3.85)
        else:
            result.pop(CONF_BATTERY_VOLTAGE, None)
        return result

    profile = profiles.get(profile_id)
    if profile is None:
        result[CONF_DEVICE_PROFILE] = DEVICE_PROFILE_MANUAL
        return result
    result[CONF_BATTERY_CAPACITY] = profile["capacity"]
    result[CONF_UNIT_OF_MEASUREMENT] = profile["capacity_unit"]
    if profile["capacity_unit"] == "mAh":
        result[CONF_BATTERY_VOLTAGE] = profile["nominal_voltage"]
    else:
        result.pop(CONF_BATTERY_VOLTAGE, None)
    return result


def _source_key(data: dict[str, Any]) -> tuple[str, str]:
    """Return the source and attribute pair used for duplicate detection."""
    return data[CONF_SOURCE], data.get(CONF_ATTRIBUTE, "")


class BatteryConsumptionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Battery Consumption."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the multi-step flow."""
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect tracker identity before choosing capacity configuration."""
        if user_input is not None:
            self._data = _clean_input(user_input)
            return await self.async_step_capacity_source()
        return self.async_show_form(step_id="user", data_schema=_identity_schema())

    async def async_step_capacity_source(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose device-profile or manual capacity configuration."""
        if user_input is not None:
            if user_input[CONF_CONFIGURATION_MODE] == CONFIGURATION_MODE_PROFILE:
                return await self.async_step_profile()
            return await self.async_step_manual()
        return self.async_show_form(
            step_id="capacity_source",
            data_schema=_configuration_mode_schema(CONFIGURATION_MODE_PROFILE),
        )

    async def async_step_profile(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure capacity from a known device profile."""
        profiles = await async_load_device_profiles(self.hass)
        if user_input is not None:
            return await self._async_finish({**user_input}, profiles)
        return self.async_show_form(
            step_id="profile", data_schema=_profile_options_schema(profiles)
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure battery specifications manually."""
        if user_input is not None:
            user_input[CONF_DEVICE_PROFILE] = DEVICE_PROFILE_MANUAL
            return await self._async_finish(user_input, {})
        return self.async_show_form(
            step_id="manual", data_schema=_manual_options_schema()
        )

    async def _async_finish(
        self, options: dict[str, Any], profiles: dict[str, dict[str, Any]]
    ) -> ConfigFlowResult:
        """Validate uniqueness and create the config entry."""
        data = _apply_device_profile(_clean_input({**self._data, **options}), profiles)
        wanted_slug = slugify(data[CONF_TRACKER_NAME])
        if any(
            slugify(entry.data.get(CONF_TRACKER_NAME, entry.title)) == wanted_slug
            for entry in self._async_current_entries()
        ):
            return self.async_abort(reason="name_already_configured")
        source, attribute = _source_key(data)
        await self.async_set_unique_id(f"{source}:{attribute}")
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=data[CONF_TRACKER_NAME], data=data)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change tracker name or monitored source."""
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            identity = _clean_input(user_input)
            wanted_slug = slugify(identity[CONF_TRACKER_NAME])
            if any(
                other.entry_id != entry.entry_id
                and slugify(other.data.get(CONF_TRACKER_NAME, other.title))
                == wanted_slug
                for other in self._async_current_entries()
            ):
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=self.add_suggested_values_to_schema(
                        _identity_schema(), identity
                    ),
                    errors={"base": "name_already_configured"},
                )
            source, attribute = _source_key(identity)
            await self.async_set_unique_id(f"{source}:{attribute}")
            self._abort_if_unique_id_mismatch(reason="wrong_entry")
            data = dict(entry.data)
            for key in (CONF_TRACKER_NAME, CONF_SOURCE, CONF_ATTRIBUTE):
                data.pop(key, None)
            data.update(identity)
            self.hass.config_entries.async_update_entry(
                entry, title=identity[CONF_TRACKER_NAME]
            )
            return self.async_update_reload_and_abort(entry, data_updates=data)

        current = {
            CONF_TRACKER_NAME: entry.data.get(CONF_TRACKER_NAME, entry.title),
            CONF_SOURCE: entry.data[CONF_SOURCE],
            CONF_ATTRIBUTE: entry.data.get(CONF_ATTRIBUTE, ""),
        }
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(_identity_schema(), current),
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
        """Choose profile or manual options without mixing their fields."""
        if user_input is not None:
            if user_input[CONF_CONFIGURATION_MODE] == CONFIGURATION_MODE_PROFILE:
                return await self.async_step_profile()
            return await self.async_step_manual()
        values = {**self.config_entry.data, **self.config_entry.options}
        default = (
            CONFIGURATION_MODE_MANUAL
            if values.get(CONF_DEVICE_PROFILE, DEVICE_PROFILE_MANUAL)
            == DEVICE_PROFILE_MANUAL
            else CONFIGURATION_MODE_PROFILE
        )
        return self.async_show_form(
            step_id="init", data_schema=_configuration_mode_schema(default)
        )

    async def async_step_profile(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage options using a known device profile."""
        profiles = await async_load_device_profiles(self.hass)
        if user_input is not None:
            data = _apply_device_profile(_clean_input(user_input), profiles)
            return self.async_create_entry(data=data)
        values = {**self.config_entry.data, **self.config_entry.options}
        selected = values.get(CONF_DEVICE_PROFILE)
        if selected not in profiles:
            values.pop(CONF_DEVICE_PROFILE, None)
        return self.async_show_form(
            step_id="profile",
            data_schema=self.add_suggested_values_to_schema(
                _profile_options_schema(profiles), values
            ),
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage manually entered battery options."""
        if user_input is not None:
            data = _clean_input(user_input)
            data[CONF_DEVICE_PROFILE] = DEVICE_PROFILE_MANUAL
            data = _apply_device_profile(data, {})
            return self.async_create_entry(data=data)
        values = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="manual",
            data_schema=self.add_suggested_values_to_schema(
                _manual_options_schema(), values
            ),
        )
