"""Battery Consumption sensors."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any, Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_ATTRIBUTE,
    CONF_SOURCE,
    CONF_UNIQUE_ID,
    CONF_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import slugify

from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_BATTERY_VOLTAGE,
    CONF_BATTERY_CONSUMPTION,
    CONF_CREATE_ACTIVITY_SENSOR,
    CONF_CREATE_CYCLE_SENSOR,
    CONF_CREATE_POWER_SENSOR,
    CONF_COMPANION_IS_CHARGING,
    CONF_COMPANION_BATTERY_STATE,
    CONF_COMPANION_CHARGER_TYPE,
    CONF_COMPANION_BATTERY_POWER,
    CONF_COMPANION_BATTERY_TEMPERATURE,
    CONF_COMPANION_BATTERY_HEALTH,
    CONF_COMPANION_BATTERY_CYCLE_COUNT,
    CONF_COMPANION_REMAINING_CHARGE_TIME,
    CONF_DEVICE_PROFILE,
    CONF_MINIMUM_CHANGE,
    CONF_PRECISION,
    CONF_SESSION_TIMEOUT,
    CONF_TRACKER_NAME,
    DATA_BATTERY_CONSUMPTION,
    DEFAULT_CREATE_ACTIVITY_SENSOR,
    DEFAULT_CREATE_CYCLE_SENSOR,
    DEFAULT_CREATE_POWER_SENSOR,
    DEFAULT_MINIMUM_CHANGE,
    DEFAULT_NAME,
    DEFAULT_SESSION_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

ATTR_SOURCE = "source"
ATTR_SOURCE_ATTRIBUTE = "source_attribute"
ATTR_PREVIOUS_MONITORED_VALUE = "previous_value"
ATTR_CURRENT_VARIATION = "variation"
ATTR_CURRENT_CHARGE = "battery_charge"
ATTR_CURRENT_DISCHARGE = "battery_discharge"
ATTR_CURRENT_VARIATION_ENERGY = "energy_variation"
ATTR_CURRENT_CHARGE_ENERGY = "energy_charge"
ATTR_CURRENT_DISCHARGE_ENERGY = "energy_discharge"
ATTR_TOTAL_CHARGE = "total_charge"
ATTR_TOTAL_DISCHARGE = "total_discharge"
ATTR_TOTAL_CHARGE_ENERGY = "total_energy_charge"
ATTR_TOTAL_DISCHARGE_ENERGY = "total_energy_discharge"
ATTR_CAPACITY_UNIT = "capacity_unit"
ATTR_CAPACITY = "capacity"
ATTR_ENERGY_LEVEL = "energy_level"
ATTR_LAST_UPDATED = "last_updated"
ATTR_PREVIOUS_LAST_UPDATED = "previous_last_updated"
ATTR_DELTA_LAST_UPDATED = "delta_last_updated_in_minutes"
ATTR_CURRENT_POWER = "instant_power"
ATTR_ACTIVITY = "activity"
ATTR_SESSION_STARTED = "session_started"
ATTR_SESSION_START_LEVEL = "session_start_level"
ATTR_SESSION_CHANGE = "session_change"
ATTR_SESSION_ENERGY = "session_energy"
ATTR_MINIMUM_CHANGE = "minimum_change"

ACTIVITY_IDLE = "idle"
ACTIVITY_CHARGING = "charging"
ACTIVITY_DISCHARGING = "discharging"


def _optional_value(value: Any) -> Any:
    return None if value in (None, STATE_UNKNOWN, STATE_UNAVAILABLE) else value


def _optional_float(value: Any) -> float | None:
    value = _optional_value(value)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _restored_datetime(value: Any) -> datetime | None:
    value = _optional_value(value)
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


_CALCULATION_KEYS = {
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
    CONF_COMPANION_IS_CHARGING,
    CONF_COMPANION_BATTERY_STATE,
    CONF_COMPANION_CHARGER_TYPE,
    CONF_COMPANION_BATTERY_POWER,
    CONF_COMPANION_BATTERY_TEMPERATURE,
    CONF_COMPANION_BATTERY_HEALTH,
    CONF_COMPANION_BATTERY_CYCLE_COUNT,
    CONF_COMPANION_REMAINING_CHARGE_TIME,
}


def _effective_entry_config(entry: ConfigEntry) -> dict[str, Any]:
    """Apply options as a complete calculation configuration."""
    conf = dict(entry.data)
    if entry.options:
        for key in _CALCULATION_KEYS:
            conf.pop(key, None)
        conf.update(entry.options)
    return conf


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: Callable,
) -> None:
    """Set up Battery Consumption from a config entry."""
    conf = _effective_entry_config(entry)
    tracker = BatteryConsumptionSensor(
        conf.get(CONF_UNIQUE_ID, entry.entry_id),
        _sensor_name(conf),
        conf[CONF_SOURCE],
        conf.get(CONF_ATTRIBUTE),
        conf[CONF_PRECISION],
        conf.get(CONF_BATTERY_CAPACITY),
        conf.get(CONF_UNIT_OF_MEASUREMENT),
        conf.get(CONF_MINIMUM_CHANGE, DEFAULT_MINIMUM_CHANGE),
        conf.get(CONF_SESSION_TIMEOUT, DEFAULT_SESSION_TIMEOUT),
        entry.entry_id,
        conf.get(CONF_TRACKER_NAME) or entry.title,
        conf.get(CONF_BATTERY_VOLTAGE),
        {key: conf.get(key) for key in (
            CONF_COMPANION_IS_CHARGING, CONF_COMPANION_BATTERY_STATE,
            CONF_COMPANION_CHARGER_TYPE, CONF_COMPANION_BATTERY_POWER,
            CONF_COMPANION_BATTERY_TEMPERATURE, CONF_COMPANION_BATTERY_HEALTH,
            CONF_COMPANION_BATTERY_CYCLE_COUNT, CONF_COMPANION_REMAINING_CHARGE_TIME,
        ) if conf.get(key)},
    )
    entities: list[SensorEntity] = [tracker]
    if conf.get(CONF_CREATE_ACTIVITY_SENSOR, DEFAULT_CREATE_ACTIVITY_SENSOR):
        entities.append(BatteryActivitySensor(tracker, entry.entry_id))
    if conf.get(CONF_CREATE_CYCLE_SENSOR, DEFAULT_CREATE_CYCLE_SENSOR):
        entities.append(BatteryCycleSensor(tracker, entry.entry_id))
    if conf.get(CONF_CREATE_POWER_SENSOR, DEFAULT_CREATE_POWER_SENSOR):
        if tracker.power_unit is not None:
            entities.append(BatteryPowerSensor(tracker, entry.entry_id))
        else:
            _LOGGER.warning(
                "Battery power sensor requires capacity and a supported unit: Wh, kWh, or MWh"
            )
    async_add_entities(entities)
    platform = entity_platform.async_get_current_platform()
    if not hass.data.setdefault(DOMAIN, {}).get("reset_totals_registered"):
        platform.async_register_entity_service(
            "reset_totals", {}, "async_reset_totals"
        )
        hass.data[DOMAIN]["reset_totals_registered"] = True


def _sensor_name(conf: dict[str, Any]) -> str:
    source = conf[CONF_SOURCE]
    attribute = conf.get(CONF_ATTRIBUTE)
    name = f"{DEFAULT_NAME}_{source}"
    return f"{name}_{attribute}" if attribute is not None else name


async def async_setup_platform(
    hass: HomeAssistant,
    config: dict[str, Any],
    async_add_entities: Callable,
    discovery_info: dict[str, Any] | None = None,
) -> None:
    """Set up a YAML Battery Consumption sensor."""
    if discovery_info is None:
        return
    key = discovery_info[CONF_BATTERY_CONSUMPTION]
    conf = hass.data[DATA_BATTERY_CONSUMPTION][key]
    async_add_entities(
        [
            BatteryConsumptionSensor(
                conf.get(CONF_UNIQUE_ID),
                _sensor_name(conf),
                conf[CONF_SOURCE],
                conf.get(CONF_ATTRIBUTE),
                conf[CONF_PRECISION],
                conf.get(CONF_BATTERY_CAPACITY),
                conf.get(CONF_UNIT_OF_MEASUREMENT),
                conf.get(CONF_MINIMUM_CHANGE, DEFAULT_MINIMUM_CHANGE),
                conf.get(CONF_SESSION_TIMEOUT, DEFAULT_SESSION_TIMEOUT),
                None,
                None,
            )
        ]
    )


class BatteryConsumptionSensor(RestoreEntity, SensorEntity):
    """Track battery changes using the original calculation path."""

    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.BATTERY

    def __init__(self, unique_id, name, source, attribute, precision,
                 battery_capacity, unit_of_measurement, minimum_change,
                 session_timeout, entry_id, tracker_name, battery_voltage=None,
                 companion_entities=None):
        self._attr_unique_id = unique_id
        self._source_entity_id = source
        self._source_attribute = attribute
        self._precision = precision
        self._configured_battery_capacity = battery_capacity
        self._configured_capacity_unit = unit_of_measurement
        self._battery_voltage = battery_voltage
        if battery_capacity is not None and unit_of_measurement == "mAh":
            if battery_voltage is None:
                raise ValueError("battery_voltage is required when capacity is in mAh")
            self._battery_capacity = battery_capacity * battery_voltage / 1000
            self._unit_of_measurement = "Wh"
        else:
            self._battery_capacity = battery_capacity
            self._unit_of_measurement = unit_of_measurement

        # Kept for configuration compatibility. Neither value changes accounting.
        self._minimum_change = float(minimum_change)
        self._session_timeout = int(session_timeout)
        self._entry_id = entry_id
        self._tracker_name = tracker_name
        self._tracker_slug = slugify(tracker_name) if tracker_name else None
        if entry_id is not None and tracker_name is not None:
            self._attr_has_entity_name = True
            self._attr_translation_key = "battery_level"
            self._attr_suggested_object_id = f"{DOMAIN}_{self._tracker_slug}_battery_level"
            self._attr_device_info = {
                "identifiers": {(DOMAIN, entry_id)},
                "name": f"Battery Consumption {tracker_name}",
                "manufacturer": "Battery Consumption",
                "model": "Battery Tracker",
                "sw_version": "2.10.5",
            }
        else:
            self._attr_name = name

        # Original state and accounting variables.
        self._state = None
        self._last_updated = None
        self._previous_state = None
        self._previous_last_updated = None
        self._delta = 0.0
        self._delta_last_updated = 0.0
        self._cumulative_charge = 0.0
        self._cumulative_discharge = 0.0

        # Observer-only state for optional entities.
        self._activity = ACTIVITY_IDLE
        self._activity_source_type = "battery_level"
        self._activity_source_entity = self._source_entity_id
        self._session_started = None
        self._session_start_level = None
        self._session_change = 0.0
        self._dependents = []
        self._companion_entities = companion_entities or {}

    def register_dependent(self, entity):
        self._dependents.append(entity)

    async def async_added_to_hass(self):
        """Restore state in the same order as the original component."""
        await super().async_added_to_hass()
        state_recorded = await self.async_get_last_state()
        if state_recorded:
            self._state = _optional_float(state_recorded.state)
            self._last_updated = state_recorded.last_updated
            self._previous_state = _optional_value(
                state_recorded.attributes.get(ATTR_PREVIOUS_MONITORED_VALUE)
            )
            self._previous_last_updated = _restored_datetime(
                state_recorded.attributes.get(ATTR_PREVIOUS_LAST_UPDATED)
            )
            self._compute_induced_data()
            self._cumulative_charge = _optional_float(
                state_recorded.attributes.get(ATTR_TOTAL_CHARGE)
            ) or 0.0
            self._cumulative_discharge = _optional_float(
                state_recorded.attributes.get(ATTR_TOTAL_DISCHARGE)
            ) or 0.0
        self.async_on_remove(async_track_state_change_event(
            self.hass, [self._source_entity_id], self._async_source_state_changed
        ))
        if self._companion_entities:
            self.async_on_remove(async_track_state_change_event(
                self.hass, list(self._companion_entities.values()),
                self._async_companion_state_changed
            ))
        if self._state is None:
            self._initialize_from_current_source()
        self._derive_optional_state()

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return "%"

    @property
    def extra_state_attributes(self):
        """Return the original attributes with original values and meanings."""
        ret = {ATTR_SOURCE: self._source_entity_id}
        if self._source_attribute:
            ret[ATTR_SOURCE_ATTRIBUTE] = self._source_attribute
        ret[ATTR_PREVIOUS_MONITORED_VALUE] = self._previous_state
        ret[ATTR_LAST_UPDATED] = self._last_updated
        ret[ATTR_PREVIOUS_LAST_UPDATED] = self._previous_last_updated
        ret[ATTR_DELTA_LAST_UPDATED] = self._delta_last_updated / 60
        ret[ATTR_CURRENT_VARIATION] = self._delta
        if self._delta < 0:
            ret[ATTR_CURRENT_CHARGE] = 0
            ret[ATTR_CURRENT_DISCHARGE] = -self._delta
        else:
            ret[ATTR_CURRENT_CHARGE] = self._delta
            ret[ATTR_CURRENT_DISCHARGE] = 0
        ret[ATTR_TOTAL_CHARGE] = self._cumulative_charge
        ret[ATTR_TOTAL_DISCHARGE] = self._cumulative_discharge
        if self._battery_capacity is not None:
            ret[ATTR_CAPACITY_UNIT] = self._unit_of_measurement
            ret[ATTR_CAPACITY] = self._battery_capacity
            ret[ATTR_ENERGY_LEVEL] = self._state * self._battery_capacity / 100
            ret[ATTR_CURRENT_VARIATION_ENERGY] = self._delta * self._battery_capacity / 100
            if self._delta < 0:
                ret[ATTR_CURRENT_CHARGE_ENERGY] = 0
                ret[ATTR_CURRENT_DISCHARGE_ENERGY] = -self._delta * self._battery_capacity / 100
            else:
                ret[ATTR_CURRENT_CHARGE_ENERGY] = self._delta * self._battery_capacity / 100
                ret[ATTR_CURRENT_DISCHARGE_ENERGY] = 0
            ret[ATTR_TOTAL_CHARGE_ENERGY] = self._cumulative_charge * self._battery_capacity / 100
            ret[ATTR_TOTAL_DISCHARGE_ENERGY] = self._cumulative_discharge * self._battery_capacity / 100
            ret[ATTR_CURRENT_POWER] = self._instant_power
        return ret

    @property
    def _instant_power(self):
        """Use the original power formula and original zero fallback."""
        if self._battery_capacity is None or self._delta_last_updated == 0:
            return 0.0
        return round(
            (self._delta * self._battery_capacity / 100)
            / (self._delta_last_updated / 3600), 2
        )

    @property
    def power_unit(self):
        unit = {"Wh": "W", "kWh": "kW", "MWh": "MW"}.get(self._unit_of_measurement)
        if unit is None and CONF_COMPANION_BATTERY_POWER in self._companion_entities:
            return "W"
        return unit

    async def async_reset_totals(self):
        self._cumulative_charge = 0.0
        self._cumulative_discharge = 0.0
        self.async_write_ha_state()
        self._write_dependents()

    @property
    def activity(self):
        return self._activity

    @property
    def session_attributes(self):
        attrs = {
            ATTR_SESSION_STARTED: self._session_started,
            ATTR_SESSION_START_LEVEL: self._session_start_level,
            ATTR_SESSION_CHANGE: self._session_change,
        }
        if self._battery_capacity is not None:
            attrs[ATTR_SESSION_ENERGY] = self._session_change * self._battery_capacity / 100
        return attrs

    @property
    def equivalent_full_cycles(self):
        return round(self._cumulative_discharge / 100, self._precision)

    def _compute_induced_data(self):
        """Original variation and timestamp calculation."""
        if (self._previous_state is not None and self._state is not None
                and self._previous_state != STATE_UNKNOWN and self._state != STATE_UNKNOWN):
            try:
                self._delta = self._state - self._previous_state
            except (TypeError, ValueError):
                self._delta = 0
                _LOGGER.warning("%s state or %s previous is not numerical",
                                self._state, self._previous_state)
            try:
                self._delta_last_updated = (
                    self._last_updated - self._previous_last_updated
                ).total_seconds()
            except (TypeError, ValueError):
                self._delta_last_updated = 0.0
                _LOGGER.warning("%s last_updated or %s previous_last_updated is not numerical",
                                self._last_updated, self._previous_last_updated)
        else:
            self._delta = 0
            self._delta_last_updated = 0.0

    def _compute_cumulative_data(self):
        """Original cumulative accounting with no threshold or filter."""
        if self._delta < 0:
            self._cumulative_discharge = self._cumulative_discharge - self._delta
        else:
            self._cumulative_charge = self._cumulative_charge + self._delta

    def _compute_new_state_and_attribute(self, value, last_updated):
        """Original update sequence."""
        self._previous_state = self._state
        self._previous_last_updated = self._last_updated
        self._state = round(value, self._precision)
        self._last_updated = last_updated
        self._compute_induced_data()
        self._compute_cumulative_data()

    def _companion_state(self, key):
        entity_id = self._companion_entities.get(key)
        if not entity_id or self.hass is None:
            return None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        return state

    @property
    def companion_telemetry_attributes(self):
        """Return optional telemetry owned by the activity sensor."""
        attrs = {}
        names = {
            CONF_COMPANION_CHARGER_TYPE: "charger_type",
            CONF_COMPANION_BATTERY_TEMPERATURE: "battery_temperature",
            CONF_COMPANION_BATTERY_HEALTH: "battery_health",
            CONF_COMPANION_REMAINING_CHARGE_TIME: "remaining_charge_time",
        }
        for key, name in names.items():
            state = self._companion_state(key)
            if state is not None:
                attrs[name] = state.state
                unit = state.attributes.get("unit_of_measurement")
                if unit:
                    attrs[f"{name}_unit"] = unit
        return attrs

    @property
    def hardware_cycle_count(self):
        state = self._companion_state(CONF_COMPANION_BATTERY_CYCLE_COUNT)
        if state is None:
            return None
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return None

    @property
    def output_power(self):
        state = self._companion_state(CONF_COMPANION_BATTERY_POWER)
        if state is None:
            return self._instant_power, "estimated", None
        try:
            value = float(state.state)
        except (TypeError, ValueError):
            return self._instant_power, "estimated", None
        source_unit = state.attributes.get("unit_of_measurement", "W")
        target = self.power_unit or "W"
        watts = value * {"W": 1, "kW": 1000, "MW": 1000000}.get(source_unit, 1)
        converted = watts / {"W": 1, "kW": 1000, "MW": 1000000}.get(target, 1)
        return round(converted, self._precision), "measured", state.entity_id

    @callback
    def _derive_optional_state(self, account_delta=False):
        charging = self._companion_state(CONF_COMPANION_IS_CHARGING)
        battery_state = self._companion_state(CONF_COMPANION_BATTERY_STATE)
        state_text = battery_state.state.lower().replace("_", " ") if battery_state else ""
        if charging is not None:
            self._activity_source_type = "is_charging"
            self._activity_source_entity = charging.entity_id
            if charging.state == "on":
                activity = ACTIVITY_CHARGING
            elif state_text == "full":
                activity = ACTIVITY_IDLE
            else:
                activity = ACTIVITY_DISCHARGING if self._delta < 0 else ACTIVITY_IDLE
        elif battery_state is not None:
            self._activity_source_type = "battery_state"
            self._activity_source_entity = battery_state.entity_id
            if state_text == "charging":
                activity = ACTIVITY_CHARGING
            elif state_text == "full":
                activity = ACTIVITY_IDLE
            elif state_text in ("discharging", "not charging"):
                activity = ACTIVITY_DISCHARGING if self._delta < 0 else ACTIVITY_IDLE
            elif self._delta > 0:
                activity = ACTIVITY_CHARGING
            elif self._delta < 0:
                activity = ACTIVITY_DISCHARGING
            else:
                activity = ACTIVITY_IDLE
        else:
            self._activity_source_type = "battery_level"
            self._activity_source_entity = self._source_entity_id
            if self._delta > 0:
                activity = ACTIVITY_CHARGING
            elif self._delta < 0:
                activity = ACTIVITY_DISCHARGING
            else:
                activity = ACTIVITY_IDLE
        if activity == ACTIVITY_IDLE:
            self._activity = activity
            return
        if activity != self._activity:
            self._session_started = self._last_updated
            self._session_start_level = self._previous_state
            self._session_change = self._delta if account_delta else 0.0
        elif account_delta and self._delta:
            self._session_change += self._delta
        self._activity = activity

    @callback
    def _async_companion_state_changed(self, _event):
        self._derive_optional_state()
        self._write_dependents()

    def _source_value(self, source_state):
        """Return a numeric value from the configured source or attribute."""
        if source_state is None:
            return None
        try:
            if self._source_attribute:
                return float(source_state.attributes.get(self._source_attribute))
            if source_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                return None
            return float(source_state.state)
        except (ValueError, TypeError):
            return None

    def _initialize_from_current_source(self):
        """Make a new tracker available immediately without creating usage totals."""
        source_state = self.hass.states.get(self._source_entity_id)
        value = self._source_value(source_state)
        if value is None:
            return
        self._state = round(value, self._precision)
        self._last_updated = source_state.last_updated
        self._previous_state = None
        self._previous_last_updated = None
        self._delta = 0
        self._delta_last_updated = 0.0
        self._instant_power = 0.0

    @callback
    def _async_source_state_changed(self, event):
        """Original source validation and update behavior."""
        new_state = event.data.get("new_state")
        if new_state is None:
            return
        value = self._source_value(new_state)
        if value is None and new_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            if self._source_attribute:
                _LOGGER.warning("%s attribute %s is not numerical",
                                self._source_entity_id, self._source_attribute)
            else:
                _LOGGER.warning("%s state is not numerical", self._source_entity_id)
        if value is not None:
            self._compute_new_state_and_attribute(value, new_state.last_updated)
            self._derive_optional_state(account_delta=True)
            self.async_write_ha_state()
            self._write_dependents()

    @callback
    def _write_dependents(self):
        for entity in self._dependents:
            if entity.hass is not None:
                entity.async_write_ha_state()


class BatteryActivitySensor(SensorEntity):
    """Represent current confirmed battery activity."""

    _attr_should_poll = False
    _attr_translation_key = "activity"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [ACTIVITY_IDLE, ACTIVITY_CHARGING, ACTIVITY_DISCHARGING]

    def __init__(self, tracker: BatteryConsumptionSensor, entry_id: str) -> None:
        self._tracker = tracker
        self._attr_unique_id = f"{entry_id}_activity"
        self._attr_suggested_object_id = (
            f"{DOMAIN}_{tracker._tracker_slug}_battery_activity"
        )
        self._attr_has_entity_name = True
        self._attr_device_info = tracker.device_info
        tracker.register_dependent(self)

    async def async_reset_totals(self) -> None:
        """Reset totals on the shared battery tracker."""
        await self._tracker.async_reset_totals()

    @property
    def state(self) -> str:
        return self._tracker.activity

    @property
    def icon(self) -> str:
        """Return an icon matching the current battery activity."""
        return {
            ACTIVITY_CHARGING: "mdi:battery-charging",
            ACTIVITY_DISCHARGING: "mdi:battery-minus",
            ACTIVITY_IDLE: "mdi:battery-outline",
        }[self._tracker.activity]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "value_meaning": "Current battery activity",
            "activity_source_type": self._tracker._activity_source_type,
            "activity_source_entity": self._tracker._activity_source_entity,
            **self._tracker.session_attributes,
            **self._tracker.companion_telemetry_attributes,
        }


class BatteryCycleSensor(SensorEntity):
    """Represent equivalent full discharge cycles."""

    _attr_should_poll = False
    _attr_translation_key = "equivalent_full_cycles"
    _attr_icon = "mdi:battery-sync"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = "cycles"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, tracker: BatteryConsumptionSensor, entry_id: str) -> None:
        self._tracker = tracker
        self._attr_unique_id = f"{entry_id}_equivalent_full_cycles"
        self._attr_suggested_object_id = (
            f"{DOMAIN}_{tracker._tracker_slug}_equivalent_full_cycles"
        )
        self._attr_has_entity_name = True
        self._attr_device_info = tracker.device_info
        tracker.register_dependent(self)

    async def async_reset_totals(self) -> None:
        """Reset totals on the shared battery tracker."""
        await self._tracker.async_reset_totals()

    @property
    def native_value(self) -> float:
        return self._tracker.equivalent_full_cycles

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        value = self._tracker.hardware_cycle_count
        attrs = {
            "value_meaning": "Equivalent full discharge cycles",
            "calculation": "total_discharge / 100",
        }
        if value is not None:
            attrs["hardware_cycle_count"] = value
            attrs["hardware_cycle_count_source"] = self._tracker._companion_entities.get(
                CONF_COMPANION_BATTERY_CYCLE_COUNT
            )
        return attrs


class BatteryPowerSensor(SensorEntity):
    """Represent confirmed average battery power over the last interval."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_translation_key = "battery_power"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, tracker: BatteryConsumptionSensor, entry_id: str) -> None:
        self._tracker = tracker
        self._attr_unique_id = f"{entry_id}_power"
        self._attr_suggested_object_id = (
            f"{DOMAIN}_{tracker._tracker_slug}_battery_power"
        )
        self._attr_native_unit_of_measurement = tracker.power_unit
        self._attr_device_info = tracker.device_info
        tracker.register_dependent(self)

    async def async_reset_totals(self) -> None:
        """Reset totals on the shared battery tracker."""
        await self._tracker.async_reset_totals()

    @property
    def native_value(self) -> float:
        return self._tracker.output_power[0]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        _, source_type, source_entity = self._tracker.output_power
        attrs = {
            "value_meaning": "Battery power over the latest interval",
            "source_type": source_type,
        }
        if source_entity:
            attrs["source_entity"] = source_entity
        return attrs

    @property
    def icon(self) -> str:
        return {
            ACTIVITY_CHARGING: "mdi:battery-charging",
            ACTIVITY_DISCHARGING: "mdi:battery-minus",
            ACTIVITY_IDLE: "mdi:battery-outline",
        }[self._tracker.activity]
