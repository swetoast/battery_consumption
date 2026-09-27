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
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import slugify

from .const import (
    CONF_BATTERY_CAPACITY,
    CONF_BATTERY_CONSUMPTION,
    CONF_CREATE_ACTIVITY_SENSOR,
    CONF_CREATE_CYCLE_SENSOR,
    CONF_CREATE_POWER_SENSOR,
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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: Callable,
) -> None:
    """Set up Battery Consumption from a config entry."""
    conf = {**entry.data, **entry.options}
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
    )
    entities: list[SensorEntity] = [tracker]
    if conf.get(CONF_CREATE_ACTIVITY_SENSOR, DEFAULT_CREATE_ACTIVITY_SENSOR):
        entities.append(BatteryActivitySensor(tracker, entry.entry_id))
    if conf.get(CONF_CREATE_CYCLE_SENSOR, DEFAULT_CREATE_CYCLE_SENSOR):
        entities.append(BatteryCycleSensor(tracker, entry.entry_id))
    if conf.get(CONF_CREATE_POWER_SENSOR, DEFAULT_CREATE_POWER_SENSOR):
        if tracker.power_unit is not None and tracker._battery_capacity is not None:
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
    """Track battery changes and accumulated charge and discharge."""

    _attr_should_poll = False
    _attr_device_class = SensorDeviceClass.BATTERY

    def __init__(
        self,
        unique_id: str | None,
        name: str,
        source: str,
        attribute: str | None,
        precision: int,
        battery_capacity: float | None,
        unit_of_measurement: str | None,
        minimum_change: float,
        session_timeout: int,
        entry_id: str | None,
        tracker_name: str | None,
    ) -> None:
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._source_entity_id = source
        self._source_attribute = attribute
        self._precision = precision
        self._battery_capacity = battery_capacity
        self._unit_of_measurement = unit_of_measurement
        self._minimum_change = float(minimum_change)
        self._session_timeout = int(session_timeout)
        self._entry_id = entry_id
        self._tracker_name = tracker_name
        self._tracker_slug = slugify(tracker_name) if tracker_name else None
        self._attr_has_entity_name = entry_id is not None
        if entry_id is not None and tracker_name is not None:
            self._attr_translation_key = "battery_level"
            self._attr_suggested_object_id = (
                f"{DOMAIN}_{self._tracker_slug}_battery_level"
            )
            self._attr_device_info = {
                "identifiers": {(DOMAIN, entry_id)},
                "name": f"Battery Consumption {tracker_name}",
                "manufacturer": "Battery Consumption",
                "model": "Battery Tracker",
                "sw_version": "2.6.0",
            }

        self._state: float | None = None
        self._last_updated: datetime | None = None
        self._previous_state: float | None = None
        self._previous_last_updated: datetime | None = None
        self._accounted_state: float | None = None
        self._accounted_last_updated: datetime | None = None
        self._delta = 0.0
        self._delta_last_updated = 0.0
        self._cumulative_charge = 0.0
        self._cumulative_discharge = 0.0
        self._source_available = True

        self._activity = ACTIVITY_IDLE
        self._session_started: datetime | None = None
        self._session_start_level: float | None = None
        self._session_change = 0.0
        self._cancel_idle: Callable[[], None] | None = None
        self._dependents: list[SensorEntity] = []

    def register_dependent(self, entity: SensorEntity) -> None:
        """Register an entity which mirrors tracker state."""
        self._dependents.append(entity)

    async def async_added_to_hass(self) -> None:
        """Restore state and subscribe to source changes."""
        await super().async_added_to_hass()
        restored = await self.async_get_last_state()
        if restored and (
            restored.attributes.get(ATTR_SOURCE) == self._source_entity_id
            and restored.attributes.get(ATTR_SOURCE_ATTRIBUTE)
            == self._source_attribute
        ):
            self._state = _optional_float(restored.state)
            self._last_updated = restored.last_updated
            self._previous_state = _optional_float(
                restored.attributes.get(ATTR_PREVIOUS_MONITORED_VALUE)
            )
            self._previous_last_updated = _restored_datetime(
                restored.attributes.get(ATTR_PREVIOUS_LAST_UPDATED)
            )
            self._accounted_state = self._state
            self._accounted_last_updated = self._last_updated
            self._cumulative_charge = _optional_float(
                restored.attributes.get(ATTR_TOTAL_CHARGE)
            ) or 0.0
            self._cumulative_discharge = _optional_float(
                restored.attributes.get(ATTR_TOTAL_DISCHARGE)
            ) or 0.0
            restored_activity = restored.attributes.get(ATTR_ACTIVITY, ACTIVITY_IDLE)
            restored_started = _restored_datetime(
                restored.attributes.get(ATTR_SESSION_STARTED)
            )
            if (
                restored_activity in (ACTIVITY_CHARGING, ACTIVITY_DISCHARGING)
                and restored_started is not None
                and (datetime.now(restored_started.tzinfo) - restored_started).total_seconds()
                < self._session_timeout * 60
            ):
                self._activity = restored_activity
                self._session_started = restored_started
                self._session_start_level = _optional_float(
                    restored.attributes.get(ATTR_SESSION_START_LEVEL)
                )
                self._session_change = _optional_float(
                    restored.attributes.get(ATTR_SESSION_CHANGE)
                ) or 0.0
                remaining = self._session_timeout * 60 - (
                    datetime.now(restored_started.tzinfo) - restored_started
                ).total_seconds()
                self._cancel_idle = async_call_later(
                    self.hass, remaining, self._async_mark_idle
                )

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._source_entity_id],
                self._async_source_state_changed,
            )
        )

    @property
    def available(self) -> bool:
        return self._source_available

    @property
    def state(self) -> float | None:
        return None if self._state is None else round(self._state, self._precision)

    @property
    def unit_of_measurement(self) -> str:
        return "%"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        def r(value: float) -> float:
            return round(value, self._precision)

        attrs: dict[str, Any] = {
            ATTR_SOURCE: self._source_entity_id,
            ATTR_PREVIOUS_MONITORED_VALUE: None if self._previous_state is None else r(self._previous_state),
            ATTR_LAST_UPDATED: self._last_updated,
            ATTR_PREVIOUS_LAST_UPDATED: self._previous_last_updated,
            ATTR_DELTA_LAST_UPDATED: self._delta_last_updated / 60,
            ATTR_CURRENT_VARIATION: r(self._delta),
            ATTR_CURRENT_CHARGE: r(max(self._delta, 0)),
            ATTR_CURRENT_DISCHARGE: r(max(-self._delta, 0)),
            ATTR_TOTAL_CHARGE: r(self._cumulative_charge),
            ATTR_TOTAL_DISCHARGE: r(self._cumulative_discharge),
            ATTR_ACTIVITY: self._activity,
            ATTR_SESSION_STARTED: self._session_started,
            ATTR_SESSION_START_LEVEL: self._session_start_level,
            ATTR_SESSION_CHANGE: r(self._session_change),
        }
        if self._source_attribute:
            attrs[ATTR_SOURCE_ATTRIBUTE] = self._source_attribute
        if self._minimum_change > 0:
            attrs[ATTR_MINIMUM_CHANGE] = self._minimum_change
        if self._battery_capacity is not None:
            variation_energy = self._delta * self._battery_capacity / 100
            attrs.update(
                {
                    ATTR_CAPACITY_UNIT: self._unit_of_measurement,
                    ATTR_CAPACITY: self._battery_capacity,
                    ATTR_ENERGY_LEVEL: (
                        None
                        if self._state is None
                        else r(self._state * self._battery_capacity / 100)
                    ),
                    ATTR_CURRENT_VARIATION_ENERGY: r(variation_energy),
                    ATTR_CURRENT_CHARGE_ENERGY: r(max(variation_energy, 0)),
                    ATTR_CURRENT_DISCHARGE_ENERGY: r(max(-variation_energy, 0)),
                    ATTR_TOTAL_CHARGE_ENERGY: (
                        r(self._cumulative_charge * self._battery_capacity / 100)
                    ),
                    ATTR_TOTAL_DISCHARGE_ENERGY: (
                        r(self._cumulative_discharge * self._battery_capacity / 100)
                    ),
                    ATTR_CURRENT_POWER: self._instant_power,
                }
            )
        return attrs

    @property
    def _instant_power(self) -> float | None:
        if self._battery_capacity is None or self._delta_last_updated <= 0:
            return None
        return round(
            (self._delta * self._battery_capacity / 100)
            / (self._delta_last_updated / 3600),
            2,
        )

    @property
    def power_unit(self) -> str | None:
        return {"Wh": "W", "kWh": "kW", "MWh": "MW"}.get(
            self._unit_of_measurement
        )

    async def async_reset_totals(self) -> None:
        """Reset accumulated charge, discharge, cycles, and session state."""
        self._cumulative_charge = 0.0
        self._cumulative_discharge = 0.0
        self._activity = ACTIVITY_IDLE
        self._session_started = None
        self._session_start_level = None
        self._session_change = 0.0
        if self._cancel_idle is not None:
            self._cancel_idle()
            self._cancel_idle = None
        self.async_write_ha_state()
        self._write_dependents()

    @property
    def activity(self) -> str:
        return self._activity

    @property
    def session_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {
            ATTR_SESSION_STARTED: self._session_started,
            ATTR_SESSION_START_LEVEL: self._session_start_level,
            ATTR_SESSION_CHANGE: self._session_change,
        }
        if self._battery_capacity is not None:
            attrs[ATTR_SESSION_ENERGY] = (
                self._session_change * self._battery_capacity / 100
            )
            attrs[ATTR_CAPACITY_UNIT] = self._unit_of_measurement
        return attrs

    @property
    def equivalent_full_cycles(self) -> float:
        return round(self._cumulative_discharge / 100, self._precision)

    @callback
    def _async_source_state_changed(self, event: Event) -> None:
        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            self._source_available = False
            self._accounted_state = None
            self._accounted_last_updated = None
            self._activity = ACTIVITY_IDLE
            if self._cancel_idle is not None:
                self._cancel_idle()
                self._cancel_idle = None
            self.async_write_ha_state()
            self._write_dependents()
            return

        raw_value = (
            new_state.attributes.get(self._source_attribute)
            if self._source_attribute
            else new_state.state
        )
        value = _optional_float(raw_value)
        if value is None or not 0 <= value <= 100:
            self._source_available = False
            self._accounted_state = None
            self._accounted_last_updated = None
            self._activity = ACTIVITY_IDLE
            if self._cancel_idle is not None:
                self._cancel_idle()
                self._cancel_idle = None
            _LOGGER.warning(
                "%s%s must provide a numerical battery level from 0 to 100",
                self._source_entity_id,
                f" attribute {self._source_attribute}" if self._source_attribute else "",
            )
            self.async_write_ha_state()
            self._write_dependents()
            return

        self._source_available = True
        self._previous_state = self._state
        self._previous_last_updated = self._last_updated
        self._state = value
        self._last_updated = new_state.last_updated

        if self._accounted_state is None:
            self._accounted_state = self._state
            self._accounted_last_updated = self._last_updated
            self._delta = 0.0
            self._delta_last_updated = 0.0
        else:
            pending_delta = self._state - self._accounted_state
            threshold = self._minimum_change
            if pending_delta != 0 and (threshold == 0 or abs(pending_delta) >= threshold):
                previous_accounted_level = self._accounted_state
                previous_accounted_time = self._accounted_last_updated
                self._delta = round(pending_delta, self._precision)
                self._delta_last_updated = (
                    (self._last_updated - previous_accounted_time).total_seconds()
                    if previous_accounted_time is not None
                    else 0.0
                )
                self._accounted_state = self._state
                self._accounted_last_updated = self._last_updated
                if self._delta > 0:
                    self._cumulative_charge += self._delta
                    activity = ACTIVITY_CHARGING
                else:
                    self._cumulative_discharge -= self._delta
                    activity = ACTIVITY_DISCHARGING
                self._update_session(activity, previous_accounted_level)
            else:
                self._delta = 0.0
                self._delta_last_updated = 0.0

        self.async_write_ha_state()
        self._write_dependents()

    @callback
    def _update_session(
        self, activity: str, previous_accounted_level: float
    ) -> None:
        if activity != self._activity:
            self._activity = activity
            self._session_started = self._last_updated
            self._session_start_level = previous_accounted_level
            self._session_change = self._delta
        else:
            self._session_change += self._delta

        if self._cancel_idle is not None:
            self._cancel_idle()
        self._cancel_idle = async_call_later(
            self.hass,
            self._session_timeout * 60,
            self._async_mark_idle,
        )

    @callback
    def _async_mark_idle(self, _now: datetime) -> None:
        self._cancel_idle = None
        self._activity = ACTIVITY_IDLE
        self._write_dependents()

    @callback
    def _write_dependents(self) -> None:
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
    def available(self) -> bool:
        return self._tracker.available

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
        return self._tracker.session_attributes


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
    def available(self) -> bool:
        return self._tracker.available

    @property
    def native_value(self) -> float:
        return self._tracker.equivalent_full_cycles


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
    def available(self) -> bool:
        return self._tracker.available and self._tracker._instant_power is not None

    @property
    def native_value(self) -> float | None:
        return self._tracker._instant_power

    @property
    def icon(self) -> str:
        return {
            ACTIVITY_CHARGING: "mdi:battery-charging",
            ACTIVITY_DISCHARGING: "mdi:battery-minus",
            ACTIVITY_IDLE: "mdi:battery-outline",
        }[self._tracker.activity]
