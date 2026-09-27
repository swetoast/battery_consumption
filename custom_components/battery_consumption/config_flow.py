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
MODE_PROFILE = "profile"


def _identity_schema() -> vol.Schema:
    """Build tracker identity schema."""
    return vol.Schema(
        {
            vol.Required(CONF_TRACKER_NAME): vol.All(cv.string, vol.Length(min=1)),
            vol.Required(CONF_SOURCE): selector.EntitySelector(),
            vol.Optional(CONF_ATTRIBUTE): cv.string,
        }
    )


def _mode_schema(default: str = DEVICE_PROFILE_MANUAL) -> vol.Schema:
    """Build capacity configuration mode schema."""
    return vol.Schema(
        {
            vol.Required(CONF_CONFIGURATION_MODE, default=default): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": DEVICE_PROFILE_MANUAL, "label": "Manual configuration"},
                        {"value": MODE_PROFILE, "label": "Device profile"},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        }
    )


def _profile_selector(profiles: dict[str, dict[str, Any]]) -> selector.SelectSelector:
    """Build a searchable device profile selector."""
    options = [
        {
            "value": profile_id,
            "label": f"{profile['manufacturer']} · {profile['model']}",
        }
        for profile_id, profile in profiles.items()
    ]
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _profile_schema(profiles: dict[str, dict[str, Any]]) -> vol.Schema:
    """Build profile selection schema."""
    return vol.Schema({vol.Required(CONF_DEVICE_PROFILE): _profile_selector(profiles)})


def _manual_schema() -> vol.Schema:
    """Build manual battery specification schema."""
    return vol.Schema(
        {
            vol.Optional(CONF_BATTERY_CAPACITY): vol.All(
                vol.Coerce(float), vol.Range(min=0)
            ),
            vol.Optional(CONF_UNIT_OF_MEASUREMENT): vol.In(
                ["mAh", "Wh", "kWh", "MWh"]
            ),
            vol.Optional(CONF_BATTERY_VOLTAGE): vol.All(
                vol.Coerce(float), vol.Range(min=0.1)
            ),
        }
    )


def _tracking_schema() -> vol.Schema:
    """Build tracking and optional entity schema shared by both modes."""
    return vol.Schema(
        {
            vol.Required(CONF_PRECISION, default=DEFAULT_PRECISION): vol.All(
                vol.Coerce(int), vol.Range(min=0)
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


def _clean_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Remove empty optional values."""
    cleaned = dict(user_input)
    for key in (
        CONF_ATTRIBUTE,
        CONF_BATTERY_CAPACITY,
        CONF_UNIT_OF_MEASUREMENT,
        CONF_BATTERY_VOLTAGE,
    ):
        if cleaned.get(key) in (None, ""):
            cleaned.pop(key, None)
    return cleaned


def _apply_device_profile(
    data: dict[str, Any], profiles: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Copy selected profile values into stored configuration."""
    result = dict(data)
    profile_id = result.get(CONF_DEVICE_PROFILE, DEVICE_PROFILE_MANUAL)
    if profile_id == DEVICE_PROFILE_MANUAL:
        result[CONF_DEVICE_PROFILE] = DEVICE_PROFILE_MANUAL
        if CONF_BATTERY_CAPACITY not in result:
            result.pop(CONF_UNIT_OF_MEASUREMENT, None)
            result.pop(CONF_BATTERY_VOLTAGE, None)
        elif result.get(CONF_UNIT_OF_MEASUREMENT) != "mAh":
            result.pop(CONF_BATTERY_VOLTAGE, None)
        return result

    profile = profiles.get(profile_id)
    if profile is None:
        raise ValueError(f"Unknown device profile: {profile_id}")
    result[CONF_BATTERY_CAPACITY] = profile["capacity"]
    result[CONF_UNIT_OF_MEASUREMENT] = profile["capacity_unit"]
    if profile["capacity_unit"] == "mAh":
        result[CONF_BATTERY_VOLTAGE] = profile["nominal_voltage"]
    else:
        result.pop(CONF_BATTERY_VOLTAGE, None)
    return result


def _capacity_error(data: dict[str, Any]) -> str | None:
    """Validate manual capacity fields."""
    capacity = data.get(CONF_BATTERY_CAPACITY)
    unit = data.get(CONF_UNIT_OF_MEASUREMENT)
    if capacity is None:
        return None
    if unit is None:
        return "unit_required"
    if unit == "mAh" and data.get(CONF_BATTERY_VOLTAGE) is None:
        return "voltage_required"
    return None


def _source_key(data: dict[str, Any]) -> tuple[str, str]:
    """Return source and attribute pair for duplicate detection."""
    return data[CONF_SOURCE], data.get(CONF_ATTRIBUTE, "")


class BatteryConsumptionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle Battery Consumption config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow state."""
        self._data: dict[str, Any] = {}
        self._profiles: dict[str, dict[str, Any]] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect tracker name and source."""
        errors: dict[str, str] = {}
        if user_input is not None:
            identity = _clean_input(user_input)
            wanted_slug = slugify(identity[CONF_TRACKER_NAME])
            if any(
                slugify(entry.data.get(CONF_TRACKER_NAME, entry.title)) == wanted_slug
                for entry in self._async_current_entries()
            ):
                errors["base"] = "name_already_configured"
            else:
                wanted_key = _source_key(identity)
                if any(
                    _source_key({**entry.data, **entry.options}) == wanted_key
                    for entry in self._async_current_entries()
                ):
                    errors["base"] = "already_configured"

            if not errors:
                self._data = identity
                return await self.async_step_mode()

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                _identity_schema(), user_input or {}
            ),
            errors=errors,
        )

    async def async_step_mode(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose manual or profile configuration."""
        if user_input is not None:
            if user_input[CONF_CONFIGURATION_MODE] == MODE_PROFILE:
                return await self.async_step_profile()
            self._data[CONF_DEVICE_PROFILE] = DEVICE_PROFILE_MANUAL
            return await self.async_step_manual()
        return self.async_show_form(step_id="mode", data_schema=_mode_schema())

    async def async_step_profile(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select a device profile."""
        self._profiles = await async_load_device_profiles(self.hass)
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_tracking()
        return self.async_show_form(
            step_id="profile", data_schema=_profile_schema(self._profiles)
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect manual battery specification."""
        if user_input is not None:
            manual = _clean_input(user_input)
            if error := _capacity_error(manual):
                return self.async_show_form(
                    step_id="manual",
                    data_schema=self.add_suggested_values_to_schema(
                        _manual_schema(), user_input
                    ),
                    errors={"base": error},
                )
            self._data.update(manual)
            return await self.async_step_tracking()
        return self.async_show_form(step_id="manual", data_schema=_manual_schema())

    async def async_step_tracking(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect shared tracking and optional entity settings."""
        if user_input is not None:
            self._data.update(user_input)
            if not self._profiles:
                self._profiles = await async_load_device_profiles(self.hass)
            data = _apply_device_profile(self._data, self._profiles)
            return self.async_create_entry(title=data[CONF_TRACKER_NAME], data=data)
        return self.async_show_form(step_id="tracking", data_schema=_tracking_schema())

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Update tracker identity without replacing its entity identity."""
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            identity = _clean_input(user_input)
            wanted_slug = slugify(identity[CONF_TRACKER_NAME])
            wanted_key = _source_key(identity)
            for other in self._async_current_entries():
                if other.entry_id == entry.entry_id:
                    continue
                other_data = {**other.data, **other.options}
                if slugify(other.data.get(CONF_TRACKER_NAME, other.title)) == wanted_slug:
                    return self.async_show_form(
                        step_id="reconfigure",
                        data_schema=self.add_suggested_values_to_schema(
                            _identity_schema(), identity
                        ),
                        errors={"base": "name_already_configured"},
                    )
                if _source_key(other_data) == wanted_key:
                    return self.async_show_form(
                        step_id="reconfigure",
                        data_schema=self.add_suggested_values_to_schema(
                            _identity_schema(), identity
                        ),
                        errors={"base": "already_configured"},
                    )

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
            data_schema=self.add_suggested_values_to_schema(
                _identity_schema(), current
            ),
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> BatteryConsumptionOptionsFlow:
        """Return options flow handler."""
        return BatteryConsumptionOptionsFlow()


class BatteryConsumptionOptionsFlow(config_entries.OptionsFlow):
    """Handle calculation options with the same separated mode flow."""

    def __init__(self) -> None:
        """Initialize options flow state."""
        self._data: dict[str, Any] = {}
        self._profiles: dict[str, dict[str, Any]] = {}

    def _current(self) -> dict[str, Any]:
        """Return effective current configuration."""
        return {**self.config_entry.data, **self.config_entry.options}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose manual or profile configuration."""
        current = self._current()
        current_profile = current.get(CONF_DEVICE_PROFILE, DEVICE_PROFILE_MANUAL)
        default_mode = (
            DEVICE_PROFILE_MANUAL
            if current_profile == DEVICE_PROFILE_MANUAL
            else MODE_PROFILE
        )
        if user_input is not None:
            if user_input[CONF_CONFIGURATION_MODE] == MODE_PROFILE:
                return await self.async_step_profile()
            self._data[CONF_DEVICE_PROFILE] = DEVICE_PROFILE_MANUAL
            return await self.async_step_manual()
        return self.async_show_form(
            step_id="init", data_schema=_mode_schema(default_mode)
        )

    async def async_step_profile(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select device profile."""
        self._profiles = await async_load_device_profiles(self.hass)
        current = self._current()
        current_profile = current.get(CONF_DEVICE_PROFILE)
        suggested = (
            {CONF_DEVICE_PROFILE: current_profile}
            if current_profile in self._profiles
            else {}
        )
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_tracking()
        return self.async_show_form(
            step_id="profile",
            data_schema=self.add_suggested_values_to_schema(
                _profile_schema(self._profiles), suggested
            ),
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect manual battery specification."""
        current = self._current()
        suggested = {
            key: current[key]
            for key in (
                CONF_BATTERY_CAPACITY,
                CONF_UNIT_OF_MEASUREMENT,
                CONF_BATTERY_VOLTAGE,
            )
            if key in current
        }
        if user_input is not None:
            manual = _clean_input(user_input)
            if error := _capacity_error(manual):
                return self.async_show_form(
                    step_id="manual",
                    data_schema=self.add_suggested_values_to_schema(
                        _manual_schema(), user_input
                    ),
                    errors={"base": error},
                )
            self._data.update(manual)
            return await self.async_step_tracking()
        return self.async_show_form(
            step_id="manual",
            data_schema=self.add_suggested_values_to_schema(
                _manual_schema(), suggested
            ),
        )

    async def async_step_tracking(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect shared tracking and optional entity settings."""
        current = self._current()
        suggested = {
            key: current[key]
            for key in (
                CONF_PRECISION,
                CONF_MINIMUM_CHANGE,
                CONF_SESSION_TIMEOUT,
                CONF_CREATE_ACTIVITY_SENSOR,
                CONF_CREATE_CYCLE_SENSOR,
                CONF_CREATE_POWER_SENSOR,
            )
            if key in current
        }
        if user_input is not None:
            self._data.update(user_input)
            if not self._profiles:
                self._profiles = await async_load_device_profiles(self.hass)
            data = _apply_device_profile(self._data, self._profiles)
            # Options are merged over entry data at runtime. Explicitly store nulls
            # for inactive capacity fields so values from the original config entry
            # cannot leak back in after switching profile/manual modes.
            if data.get(CONF_DEVICE_PROFILE) == DEVICE_PROFILE_MANUAL:
                if CONF_BATTERY_CAPACITY not in data:
                    data[CONF_BATTERY_CAPACITY] = None
                    data[CONF_UNIT_OF_MEASUREMENT] = None
                    data[CONF_BATTERY_VOLTAGE] = None
                elif data.get(CONF_UNIT_OF_MEASUREMENT) != "mAh":
                    data[CONF_BATTERY_VOLTAGE] = None
            elif data.get(CONF_UNIT_OF_MEASUREMENT) != "mAh":
                data[CONF_BATTERY_VOLTAGE] = None
            return self.async_create_entry(data=data)
        return self.async_show_form(
            step_id="tracking",
            data_schema=self.add_suggested_values_to_schema(
                _tracking_schema(), suggested
            ),
        )
