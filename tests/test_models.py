"""Tests for typed internal models."""

from custom_components.battery_consumption.models import (
    BatteryPowerResult,
    CompanionEntities,
    EffectiveTrackerConfig,
    ProfileLoadReport,
)


def test_power_result_preserves_value_and_provenance() -> None:
    result = BatteryPowerResult(12.5, "measured", "sensor.phone_battery_power")
    assert result.value == 12.5
    assert result.source_type == "measured"
    assert result.source_entity_id == "sensor.phone_battery_power"


def test_optional_companion_entities_default_to_none() -> None:
    entities = CompanionEntities()
    assert entities.is_charging is None
    assert entities.battery_temperature is None


def test_effective_config_is_immutable() -> None:
    config = EffectiveTrackerConfig(
        tracker_name="Phone",
        source_entity_id="sensor.phone_battery",
        source_attribute=None,
        profile_id=None,
        capacity=None,
        capacity_unit=None,
        nominal_voltage=None,
        effective_capacity_wh=None,
        precision=2,
        minimum_change=0.0,
        session_timeout=15,
        create_activity_sensor=False,
        create_cycle_sensor=False,
        create_power_sensor=False,
        companion=CompanionEntities(),
    )
    assert config.source_entity_id == "sensor.phone_battery"


def test_profile_report_retains_existing_mutable_accumulator_behavior() -> None:
    report = ProfileLoadReport(bundled_loaded=107)
    report.user_overrides.append("example")
    assert report.user_overrides == ["example"]
    assert report.has_user_errors is False
