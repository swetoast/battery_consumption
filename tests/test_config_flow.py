"""Config-flow tests for Battery Consumption."""

from homeassistant import config_entries
from homeassistant.const import CONF_SOURCE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.battery_consumption.const import DOMAIN


async def test_user_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "tracker_name": "Pixel 9",
            "device_profile": "manual",
            CONF_SOURCE: "sensor.phone_battery",
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


async def test_duplicate_is_rejected(hass: HomeAssistant) -> None:
    entry = config_entries.ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="sensor.phone_battery",
        data={CONF_SOURCE: "sensor.phone_battery"},
        source=config_entries.SOURCE_USER,
        unique_id="sensor.phone_battery:",
        discovery_keys={},
        options={},
        subentries_data={},
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "tracker_name": "Pixel 9",
            "device_profile": "manual",
            CONF_SOURCE: "sensor.phone_battery",
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
