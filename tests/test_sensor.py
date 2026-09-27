"""Regression tests for Battery Consumption calculations."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from custom_components.battery_consumption.sensor import BatteryConsumptionSensor


def _tracker(minimum_change: float = 0) -> BatteryConsumptionSensor:
    return BatteryConsumptionSensor(
        "test", "Test battery", "sensor.test_battery", None, 2, 50, "kWh",
        minimum_change, 15, "entry-id", "Pixel 9"
    )


def _event(value: object, minute: int = 0) -> Mock:
    state = Mock()
    state.state = str(value)
    state.attributes = {}
    state.last_updated = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=minute)
    event = Mock()
    event.data = {"new_state": state}
    return event


def test_original_accounting_behavior() -> None:
    tracker = _tracker()
    for minute, value in enumerate((50, 51, 50)):
        tracker._async_source_state_changed(_event(value, minute))
    assert tracker._cumulative_charge == 1
    assert tracker._cumulative_discharge == 1


def test_noise_threshold_accumulates_net_movement() -> None:
    tracker = _tracker(2)
    for minute, value in enumerate((50, 51, 50, 51, 52)):
        tracker._async_source_state_changed(_event(value, minute))
    assert tracker._cumulative_charge == 2
    assert tracker._cumulative_discharge == 0


def test_invalid_level_is_rejected() -> None:
    tracker = _tracker()
    tracker._async_source_state_changed(_event(50))
    tracker._async_source_state_changed(_event(101, 1))
    assert tracker.state == 50
    assert tracker.available is False


def test_power_unit_and_equivalent_cycles() -> None:
    tracker = _tracker()
    tracker._cumulative_discharge = 125
    assert tracker.power_unit == "kW"
    assert tracker.equivalent_full_cycles == 1.25


def test_namespaced_suggested_object_ids() -> None:
    tracker = _tracker()
    assert tracker._attr_suggested_object_id == (
        "battery_consumption_pixel_9_battery_level"
    )
    assert tracker.device_info["name"] == "Battery Consumption Pixel 9"


def test_mah_capacity_is_converted_to_wh() -> None:
    tracker = BatteryConsumptionSensor(
        "test-mah", "Phone battery", "sensor.phone_battery", None,
        2, 5050, "mAh", 0, 15, "entry-mah", "Pixel 8 Pro", 3.85
    )
    assert tracker._battery_capacity == 19.4425
    assert tracker._unit_of_measurement == "Wh"
    assert tracker.power_unit == "W"


def test_wh_capacity_remains_unchanged() -> None:
    tracker = BatteryConsumptionSensor(
        "test-wh", "Phone battery", "sensor.phone_battery", None,
        2, 19.5, "Wh", 0, 15, "entry-wh", "Pixel 8 Pro", None
    )
    assert tracker._battery_capacity == 19.5
    assert tracker._unit_of_measurement == "Wh"
