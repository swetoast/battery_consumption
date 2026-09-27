"""Tests for the Battery Consumption config flow."""

from homeassistant import config_entries
from homeassistant.const import CONF_SOURCE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.battery_consumption.const import DOMAIN


async def _advance_identity(hass: HomeAssistant, source: str = "sensor.phone_battery"):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    return await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"tracker_name": "Pixel 9", CONF_SOURCE: source},
    )


async def test_manual_user_flow(hass: HomeAssistant) -> None:
    result = await _advance_identity(hass)
    assert result["step_id"] == "capacity_source"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"configuration_mode": "manual"}
    )
    assert result["step_id"] == "manual"
    schema_keys = {str(key) for key in result["data_schema"].schema}
    assert "device_profile" not in schema_keys
    assert "battery_capacity" in schema_keys
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "precision": 2,
            "battery_capacity": 5,
            "unit_of_measurement": "kWh",
            "minimum_change": 0,
            "session_timeout": 15,
            "create_activity_sensor": False,
            "create_cycle_sensor": False,
            "create_power_sensor": False,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["device_profile"] == "manual"
    assert result["data"]["battery_capacity"] == 5


async def test_profile_user_flow(hass: HomeAssistant) -> None:
    result = await _advance_identity(hass, "sensor.watch_battery")
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"configuration_mode": "profile"}
    )
    assert result["step_id"] == "profile"
    schema_keys = {str(key) for key in result["data_schema"].schema}
    assert "device_profile" in schema_keys
    assert "battery_capacity" not in schema_keys
    assert "battery_voltage" not in schema_keys


async def test_duplicate_is_rejected(hass: HomeAssistant) -> None:
    entry = config_entries.ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Existing",
        data={"tracker_name": "Existing", CONF_SOURCE: "sensor.phone_battery"},
        source=config_entries.SOURCE_USER,
        unique_id="sensor.phone_battery:",
        discovery_keys={},
        options={},
        subentries_data={},
    )
    entry.add_to_hass(hass)
    result = await _advance_identity(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"configuration_mode": "manual"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "precision": 2,
            "battery_capacity": 5,
            "unit_of_measurement": "kWh",
            "minimum_change": 0,
            "session_timeout": 15,
            "create_activity_sensor": False,
            "create_cycle_sensor": False,
            "create_power_sensor": False,
        },
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
