"""Regression tests for the original calculation behavior."""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from custom_components.battery_consumption.sensor import (
    ACTIVITY_CHARGING, ACTIVITY_DISCHARGING, ACTIVITY_IDLE,
    ATTR_CURRENT_POWER, BatteryConsumptionSensor,
)

def tracker(minimum=0):
    return BatteryConsumptionSensor("id", "Pixel", "sensor.pixel", None, 2,
        19.4425, "Wh", minimum, 15, "id", "Pixel Pro 8")

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

    assert item.state == 100
    assert item._previous_state is None
    assert item._delta == 0
    assert item._cumulative_charge == 0
    assert item._cumulative_discharge == 0
    assert item._instant_power == 0


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

    assert item.state == 73
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

    assert item.state == 42
    assert item._cumulative_charge == 0
    assert item._cumulative_discharge == 0
