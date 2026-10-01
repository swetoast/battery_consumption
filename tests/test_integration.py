"""End-to-end regression tests against a running Home Assistant instance."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_SOURCE
from homeassistant.core import HomeAssistant, State
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    mock_restore_cache,
)

from custom_components.battery_consumption.const import DOMAIN

BASE: dict[str, Any] = {
    "tracker_name": "Phone",
    CONF_SOURCE: "sensor.phone_battery",
    "device_profile": "manual",
    "precision": 2,
    "session_timeout": 15,
    "create_activity_sensor": True,
    "create_cycle_sensor": True,
    "create_power_sensor": True,
}
WH: dict[str, Any] = {"battery_capacity": 20.0, "unit_of_measurement": "Wh"}
LEVEL = "sensor.battery_consumption_phone_battery_level"
ACTIVITY = "sensor.battery_consumption_phone_battery_activity"
POWER = "sensor.battery_consumption_phone_battery_power"
CYCLES = "sensor.battery_consumption_phone_equivalent_full_cycles"


async def _setup(
    hass: HomeAssistant,
    data: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN, data=data, options=options or {}, title=data["tracker_name"]
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _issues(hass: HomeAssistant) -> set[str]:
    return {issue_id for domain, issue_id in ir.async_get(hass).issues if domain == DOMAIN}


async def test_new_tracker_with_live_source_adds_level_sensor(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.phone_battery", "80")
    entry = await _setup(hass, {**BASE, **WH})

    assert entry.state is ConfigEntryState.LOADED
    state = hass.states.get(LEVEL)
    assert state is not None
    assert float(state.state) == 80
    assert state.attributes["unit_of_measurement"] == "%"
    assert state.attributes["state_class"] == "measurement"
    assert state.attributes["energy_level"] == 16


async def test_unavailable_source_with_capacity_adds_level_sensor(
    hass: HomeAssistant,
) -> None:
    hass.states.async_set("sensor.phone_battery", "unavailable")
    await _setup(hass, {**BASE, **WH})

    state = hass.states.get(LEVEL)
    assert state is not None
    assert state.state == "unknown"
    assert state.attributes["energy_level"] is None

    hass.states.async_set("sensor.phone_battery", "55")
    await hass.async_block_till_done()
    assert float(hass.states.get(LEVEL).state) == 55


async def test_missing_source_loads_and_raises_then_clears_issue(
    hass: HomeAssistant,
) -> None:
    entry = await _setup(hass, BASE)

    assert entry.state is ConfigEntryState.LOADED
    assert f"source_missing_{entry.entry_id}" in _issues(hass)

    hass.states.async_set("sensor.phone_battery", "70")
    await hass.async_block_till_done()
    assert f"source_missing_{entry.entry_id}" not in _issues(hass)


async def test_cleared_companion_in_options_is_not_flagged_or_resuggested(
    hass: HomeAssistant,
) -> None:
    hass.states.async_set("sensor.phone_battery", "80")
    options = {k: v for k, v in BASE.items() if k not in ("tracker_name", CONF_SOURCE)}
    entry = await _setup(
        hass, {**BASE, "companion_battery_state": "sensor.removed_state"}, options
    )

    assert f"companion_entity_missing_{entry.entry_id}" not in _issues(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"configuration_mode": "manual"}
    )
    result = await hass.config_entries.options.async_configure(result["flow_id"], {})
    suggested = {
        str(key): key.description.get("suggested_value")
        for key in result["data_schema"].schema
        if key.description
    }
    assert suggested.get("companion_battery_state") is None


async def test_companion_session_starts_at_current_level(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    hass.states.async_set("sensor.phone_battery", "80")
    hass.states.async_set("binary_sensor.phone_is_charging", "off")
    await _setup(
        hass, {**BASE, **WH, "companion_is_charging": "binary_sensor.phone_is_charging"}
    )
    for level in ("79", "78"):
        freezer.tick(timedelta(minutes=1))
        hass.states.async_set("sensor.phone_battery", level)
        await hass.async_block_till_done()

    freezer.tick(timedelta(minutes=30))
    plugged_in = dt_util.utcnow()
    hass.states.async_set("binary_sensor.phone_is_charging", "on")
    await hass.async_block_till_done()

    state = hass.states.get(ACTIVITY)
    assert state.state == "charging"
    assert state.attributes["session_start_level"] == 78
    assert state.attributes["session_started"] == plugged_in


async def test_estimated_power_returns_to_zero_after_timeout(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    hass.states.async_set("sensor.phone_battery", "80")
    await _setup(hass, {**BASE, **WH})
    freezer.tick(timedelta(minutes=1))
    hass.states.async_set("sensor.phone_battery", "79")
    await hass.async_block_till_done()

    assert float(hass.states.get(POWER).state) == -12.0

    freezer.tick(timedelta(minutes=16))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert float(hass.states.get(POWER).state) == 0.0
    # The original attribute on the level sensor is unchanged.
    assert hass.states.get(LEVEL).attributes["instant_power"] == -12.0


async def test_reset_totals_across_entries_and_resets_session(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    hass.states.async_set("sensor.phone_battery", "80")
    hass.states.async_set("sensor.tablet_battery", "50")
    await _setup(hass, {**BASE, **WH})
    await _setup(
        hass, {**BASE, "tracker_name": "Tablet", CONF_SOURCE: "sensor.tablet_battery"}
    )
    for level in ("79", "78"):
        freezer.tick(timedelta(minutes=1))
        hass.states.async_set("sensor.phone_battery", level)
        await hass.async_block_till_done()
    assert hass.states.get(LEVEL).attributes["total_discharge"] == 2
    assert hass.states.get(ACTIVITY).attributes["session_change"] == -2

    await hass.services.async_call(
        DOMAIN,
        "reset_totals",
        {"entity_id": [CYCLES, "sensor.battery_consumption_tablet_battery_level"]},
        blocking=True,
    )

    assert hass.states.get(LEVEL).attributes["total_discharge"] == 0
    assert hass.states.get(ACTIVITY).attributes["session_change"] == 0
    assert hass.states.get(ACTIVITY).attributes["session_start_level"] == 78


async def test_restore_uses_source_timestamp_attribute(hass: HomeAssistant) -> None:
    source_time = dt_util.utcnow() - timedelta(minutes=5)
    mock_restore_cache(
        hass,
        [
            State(
                LEVEL,
                "60",
                {
                    "source": "sensor.phone_battery",
                    "previous_value": 61,
                    "last_updated": source_time.isoformat(),
                    "previous_last_updated": (
                        source_time - timedelta(minutes=1)
                    ).isoformat(),
                    "total_charge": 3,
                    "total_discharge": 7,
                },
            )
        ],
    )
    hass.states.async_set("sensor.phone_battery", "60")
    await _setup(hass, {**BASE, **WH})
    state = hass.states.get(LEVEL)

    assert state.attributes["last_updated"] == source_time
    assert state.attributes["total_discharge"] == 7
    assert state.attributes["delta_last_updated_in_minutes"] == 1


async def test_reconfigured_source_keeps_totals_with_new_baseline(
    hass: HomeAssistant,
) -> None:
    mock_restore_cache(
        hass,
        [
            State(
                LEVEL,
                "90",
                {
                    "source": "sensor.old_battery",
                    "previous_value": 91,
                    "total_charge": 3,
                    "total_discharge": 7,
                },
            )
        ],
    )
    hass.states.async_set("sensor.phone_battery", "40")
    await _setup(hass, {**BASE, **WH})
    state = hass.states.get(LEVEL)

    assert float(state.state) == 40
    assert state.attributes["previous_value"] is None
    assert state.attributes["total_discharge"] == 7

    hass.states.async_set("sensor.phone_battery", "39")
    await hass.async_block_till_done()
    assert hass.states.get(LEVEL).attributes["total_discharge"] == 8


async def test_reconfigure_can_clear_attribute(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.phone_battery", "80", {"level": 80})
    entry = await _setup(hass, {**BASE, "attribute": "level"})

    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"tracker_name": "Phone", CONF_SOURCE: "sensor.phone_battery", "attribute": ""},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert "attribute" not in entry.data


async def test_custom_catalog_issue_is_global_and_removed_with_last_entry(
    hass: HomeAssistant, tmp_path: Path
) -> None:
    hass.config.config_dir = str(tmp_path)
    catalog = tmp_path / "battery_consumption_device_profiles.json"
    await hass.async_add_executor_job(
        catalog.write_text,
        json.dumps({"schema_version": 1, "devices": [{"id": "Bad Id"}]}),
    )
    hass.states.async_set("sensor.phone_battery", "80")
    hass.states.async_set("sensor.tablet_battery", "50")
    first = await _setup(hass, BASE)
    second = await _setup(
        hass, {**BASE, "tracker_name": "Tablet", CONF_SOURCE: "sensor.tablet_battery"}
    )

    catalog_issues = {i for i in _issues(hass) if i.startswith("user_profile")}
    assert catalog_issues == {"user_profile_catalog_invalid"}

    await hass.config_entries.async_remove(first.entry_id)
    assert "user_profile_catalog_invalid" in _issues(hass)
    await hass.config_entries.async_remove(second.entry_id)
    assert "user_profile_catalog_invalid" not in _issues(hass)


async def test_manual_capacity_must_be_positive(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"tracker_name": "Phone", CONF_SOURCE: "sensor.phone_battery"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"configuration_mode": "manual"}
    )
    try:
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {"battery_capacity": 0, "unit_of_measurement": "Wh"}
        )
    except Exception as err:  # noqa: BLE001
        assert "battery_capacity" in str(err)
    else:
        raise AssertionError("capacity 0 was accepted")


async def test_non_numeric_source_warns_once(hass: HomeAssistant, caplog) -> None:
    hass.states.async_set("sensor.phone_battery", "80")
    await _setup(hass, BASE)
    for value in ("bad", "worse", "still bad"):
        hass.states.async_set("sensor.phone_battery", value)
        await hass.async_block_till_done()

    assert caplog.text.count("state is not numerical") == 1


async def test_yaml_tracker_and_reset_action(hass: HomeAssistant) -> None:
    hass.states.async_set("sensor.yaml_battery", "64")
    assert await async_setup_component(
        hass, DOMAIN, {DOMAIN: {"yaml_phone": {"source": "sensor.yaml_battery"}}}
    )
    await hass.async_block_till_done()
    entity_id = "sensor.battery_consumption_sensor_yaml_battery"

    assert float(hass.states.get(entity_id).state) == 64
    assert hass.services.has_service(DOMAIN, "reset_totals")
    await hass.services.async_call(
        DOMAIN, "reset_totals", {"entity_id": entity_id}, blocking=True
    )
