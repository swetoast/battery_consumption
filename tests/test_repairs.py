"""Repair issue tests for Battery Consumption."""

from unittest.mock import Mock, patch

from custom_components.battery_consumption.repairs import (
    _companion_mismatches,
    _entry_data,
    _issue_id,
    _missing_companion_types,
    _source_attribute_missing,
    _source_missing,
)


def test_issue_id_is_scoped_to_entry():
    assert _issue_id("profile_missing", "entry-1") == "profile_missing_entry-1"


def test_entry_options_override_entry_data():
    entry = Mock()
    entry.data = {"device_profile": "old", "source": "sensor.battery"}
    entry.options = {"device_profile": "new"}
    assert _entry_data(entry)["device_profile"] == "new"


def test_companion_mismatch_is_empty_without_registered_source():
    hass = Mock()
    hass.data = {}
    assert _companion_mismatches(hass, {"source": "sensor.unregistered"}) == []


def test_source_missing_requires_registry_and_state_absence():
    hass = Mock()
    registry = Mock()
    registry.async_get.return_value = None
    hass.states.get.return_value = None
    with patch(
        "custom_components.battery_consumption.repairs.er.async_get",
        return_value=registry,
    ):
        assert _source_missing(hass, {"source": "sensor.removed"}) is True


def test_source_attribute_repair_ignores_unavailable_source():
    hass = Mock()
    state = Mock()
    state.state = "unavailable"
    state.attributes = {}
    hass.states.get.return_value = state
    assert _source_attribute_missing(
        hass, {"source": "sensor.battery", "attribute": "level"}
    ) is False


def test_source_attribute_repair_detects_missing_attribute():
    hass = Mock()
    state = Mock()
    state.state = "online"
    state.attributes = {"other": 1}
    hass.states.get.return_value = state
    assert _source_attribute_missing(
        hass, {"source": "sensor.battery", "attribute": "level"}
    ) is True


def test_missing_companion_types_reports_only_removed_entities():
    hass = Mock()
    registry = Mock()
    registry.async_get.return_value = None
    hass.states.get.return_value = None
    with patch(
        "custom_components.battery_consumption.repairs.er.async_get",
        return_value=registry,
    ):
        assert _missing_companion_types(
            hass,
            {"companion_battery_state": "sensor.removed_battery_state"},
        ) == ["companion_battery_state"]
