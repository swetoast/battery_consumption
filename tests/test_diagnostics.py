"""Diagnostics tests for Battery Consumption."""

from unittest.mock import Mock

from custom_components.battery_consumption.diagnostics import (
    _companion_diagnostics,
    _profile_diagnostics,
    _source_diagnostics,
)


def test_source_diagnostics_is_sanitized_and_numeric():
    hass = Mock()
    state = Mock()
    state.state = "42"
    state.attributes = {}
    hass.states.get.return_value = state

    result = _source_diagnostics(hass, {"source": "sensor.private_name"})

    assert result == {
        "domain": "sensor",
        "attribute_configured": False,
        "exists": True,
        "available": True,
        "numeric": True,
    }
    assert "private_name" not in str(result)


def test_companion_diagnostics_lists_types_not_entity_ids():
    hass = Mock()
    state = Mock()
    state.state = "charging"
    hass.states.get.return_value = state
    result = _companion_diagnostics(
        hass, {"companion_battery_state": "sensor.private_battery_state"}
    )
    assert result["configured_types"] == ["companion_battery_state"]
    assert result["available_types"] == ["companion_battery_state"]
    assert "private_battery_state" not in str(result)


def test_profile_diagnostics_uses_internal_origin():
    result = _profile_diagnostics(
        {
            "device_profile": "example",
            "battery_capacity": 20,
            "unit_of_measurement": "Wh",
        },
        {
            "example": {
                "origin": "bundled",
                "manufacturer": "Example",
                "model": "Device",
            }
        },
    )
    assert result["exists"] is True
    assert result["origin"] == "bundled"
    assert result["capacity"] == 20
