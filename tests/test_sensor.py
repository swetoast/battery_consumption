"""Regression tests for the original calculation behavior."""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from custom_components.battery_consumption.sensor import (
    ACTIVITY_CHARGING,
    ACTIVITY_DISCHARGING,
    ACTIVITY_IDLE,
    ATTR_CURRENT_POWER,
    BatteryConsumptionSensor,
)


def tracker(minimum=0):
    item = BatteryConsumptionSensor("id", "Pixel", "sensor.pixel", None, 2,
        19.4425, "Wh", minimum, 15, "id", "Pixel Pro 8")
    # Unit tests drive the tracker directly, without an entity platform.
    item.async_write_ha_state = Mock()
    return item

def event(value, seconds):
    state=Mock(); state.state=str(value); state.attributes={}
    state.last_updated=datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=seconds)
    result=Mock(); result.data={"new_state":state}; return result

def test_original_accounting_and_unchanged_updates():
    item=tracker(99)
    for value, seconds in ((77,0),(78,60),(78,120),(77,180)):
        item._async_source_state_changed(event(value,seconds))
    assert item._cumulative_charge == 1
    assert item._cumulative_discharge == 1
    item._async_source_state_changed(event(77,240))
    assert item._delta == 0
    assert item.activity == ACTIVITY_IDLE
    assert item.extra_state_attributes[ATTR_CURRENT_POWER] == 0.0

def test_original_power_formula():
    item=tracker(); item._async_source_state_changed(event(84,0))
    item._async_source_state_changed(event(85,3.71667))
    assert item._instant_power == 188.32

def test_activity_only_observes_original_delta():
    item=tracker(); item._async_source_state_changed(event(77,0))
    assert item.activity == ACTIVITY_IDLE
    item._async_source_state_changed(event(78,60)); assert item.activity == ACTIVITY_CHARGING
    item._async_source_state_changed(event(77,120)); assert item.activity == ACTIVITY_DISCHARGING
    item._async_source_state_changed(event(77,180)); assert item.activity == ACTIVITY_IDLE

def test_modern_main_entity_naming_is_not_combined_with_legacy_name():
    item=tracker()
    assert item._attr_translation_key == "battery_level"
    assert item._attr_suggested_object_id == "battery_consumption_pixel_pro_8_battery_level"
    assert not hasattr(item, "_attr_name")


def test_initial_source_sample_is_available_without_accounting():
    item = tracker()
    source = Mock()
    source.state = "100"
    source.attributes = {}
    source.last_updated = datetime(2026, 1, 1, tzinfo=timezone.utc)
    item.hass = Mock()
    item.hass.states.get.return_value = source

    item._initialize_from_current_source()

    assert item.native_value == 100
    assert item._previous_state is None
    assert item._delta == 0
    assert item._cumulative_charge == 0
    assert item._cumulative_discharge == 0
    assert item._instant_power == 0
    assert item.estimated_power == 0


def test_initial_source_attribute_is_available_without_accounting():
    item = BatteryConsumptionSensor("id", "Battery", "sensor.device", "level", 2,
        20, "Wh", 0, 15, "id", "Device")
    source = Mock()
    source.state = "online"
    source.attributes = {"level": 73}
    source.last_updated = datetime(2026, 1, 1, tzinfo=timezone.utc)
    item.hass = Mock()
    item.hass.states.get.return_value = source

    item._initialize_from_current_source()

    assert item.native_value == 73
    assert item._cumulative_charge == 0
    assert item._cumulative_discharge == 0


def test_unusable_restored_level_falls_back_to_current_source():
    item = tracker()
    item._state = None
    source = Mock()
    source.state = "42"
    source.attributes = {}
    source.last_updated = datetime(2026, 1, 1, tzinfo=timezone.utc)
    item.hass = Mock()
    item.hass.states.get.return_value = source

    if item._state is None:
        item._initialize_from_current_source()

    assert item.native_value == 42
    assert item._cumulative_charge == 0
    assert item._cumulative_discharge == 0


def _companion_state(entity_id: str, value: str):
    state = Mock()
    state.entity_id = entity_id
    state.state = value
    state.attributes = {}
    return state


def test_initial_100_percent_is_idle():
    item = tracker()
    item._state = 100
    item._delta = 0
    item._derive_optional_state()
    assert item.activity == ACTIVITY_IDLE


def test_non_companion_rise_to_100_is_temporarily_charging():
    item = tracker()
    item._previous_state = 99
    item._state = 100
    item._delta = 1
    item.hass = Mock()
    with patch(
        "custom_components.battery_consumption.sensor.async_call_later",
        return_value=Mock(),
    ):
        item._derive_optional_state(account_delta=True)
    assert item.activity == ACTIVITY_CHARGING
    item._async_activity_idle(None)
    assert item.activity == ACTIVITY_IDLE


def test_explicit_full_overrides_is_charging_on():
    item = tracker()
    item._companion_entities = {
        "companion_is_charging": "binary_sensor.phone_is_charging",
        "companion_battery_state": "sensor.phone_battery_state",
    }
    item.hass = Mock()
    states = {
        "binary_sensor.phone_is_charging": _companion_state(
            "binary_sensor.phone_is_charging", "on"
        ),
        "sensor.phone_battery_state": _companion_state(
            "sensor.phone_battery_state", "full"
        ),
    }
    item.hass.states.get.side_effect = states.get
    item._derive_optional_state()
    assert item.activity == ACTIVITY_IDLE
    assert item._activity_source_type == "battery_state"


def test_explicit_charging_remains_charging_without_movement_timeout():
    item = tracker()
    item._companion_entities = {
        "companion_is_charging": "binary_sensor.phone_is_charging"
    }
    item.hass = Mock()
    item.hass.states.get.return_value = _companion_state(
        "binary_sensor.phone_is_charging", "on"
    )
    item._derive_optional_state()
    assert item.activity == ACTIVITY_CHARGING
    assert item._activity_idle_cancel is None
