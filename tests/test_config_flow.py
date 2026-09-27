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


def test_profile_schema_omits_manual_capacity_fields() -> None:
    from custom_components.battery_consumption.config_flow import _options_schema

    profiles = {
        "google_pixel_8_pro": {
            "manufacturer": "Google",
            "model": "Pixel 8 Pro",
            "capacity": 19.44,
            "capacity_unit": "Wh",
            "nominal_voltage": None,
        }
    }
    keys = {str(key) for key in _options_schema(profiles, "google_pixel_8_pro").schema}
    assert "device_profile" in keys
    assert "precision" in keys
    assert "minimum_change" in keys
    assert "session_timeout" in keys
    assert "create_activity_sensor" in keys
    assert "battery_capacity" not in keys
    assert "unit_of_measurement" not in keys
    assert "battery_voltage" not in keys


def test_manual_schema_includes_manual_capacity_fields() -> None:
    from custom_components.battery_consumption.config_flow import _options_schema

    keys = {str(key) for key in _options_schema({}, "manual").schema}
    assert "battery_capacity" in keys
    assert "unit_of_measurement" in keys
    assert "battery_voltage" in keys
