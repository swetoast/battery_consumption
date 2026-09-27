"""Config-flow tests for Battery Consumption."""

from homeassistant import config_entries
from homeassistant.const import CONF_SOURCE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.battery_consumption.const import DOMAIN

IDENTITY = {"tracker_name": "Pixel 9", CONF_SOURCE: "sensor.phone_battery"}
TRACKING = {
    "precision": 2,
    "minimum_change": 0,
    "session_timeout": 15,
    "create_activity_sensor": True,
    "create_cycle_sensor": True,
    "create_power_sensor": True,
}


async def _start(hass: HomeAssistant) -> dict:
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_manual_user_flow_is_separated(hass: HomeAssistant) -> None:
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert set(result["data_schema"].schema) == {
        "tracker_name", CONF_SOURCE, "attribute"
    }

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], IDENTITY
    )
    assert result["step_id"] == "mode"
    assert set(result["data_schema"].schema) == {"configuration_mode"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"configuration_mode": "manual"}
    )
    assert result["step_id"] == "manual"
    assert set(result["data_schema"].schema) == {
        "battery_capacity", "unit_of_measurement", "battery_voltage"
    }

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "battery_capacity": 5050,
            "unit_of_measurement": "mAh",
            "battery_voltage": 3.85,
        },
    )
    assert result["step_id"] == "tracking"
    assert "device_profile" not in result["data_schema"].schema
    assert "battery_capacity" not in result["data_schema"].schema
    assert "create_activity_sensor" in result["data_schema"].schema

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], TRACKING
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["device_profile"] == "manual"
    assert result["data"]["battery_capacity"] == 5050
    assert result["data"]["battery_voltage"] == 3.85


async def test_profile_user_flow_is_separated(hass: HomeAssistant) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], IDENTITY
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"configuration_mode": "profile"}
    )
    assert result["step_id"] == "profile"
    assert set(result["data_schema"].schema) == {"device_profile"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"device_profile": "google_pixel_8_pro"}
    )
    assert result["step_id"] == "tracking"
    assert "create_activity_sensor" in result["data_schema"].schema
    assert "battery_capacity" not in result["data_schema"].schema

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], TRACKING
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["device_profile"] == "google_pixel_8_pro"
    assert result["data"]["battery_capacity"] == 19.44
    assert result["data"]["unit_of_measurement"] == "Wh"


async def test_manual_mah_requires_voltage(hass: HomeAssistant) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], IDENTITY)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"configuration_mode": "manual"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"battery_capacity": 5050, "unit_of_measurement": "mAh"},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"
    assert result["errors"] == {"base": "voltage_required"}


async def test_duplicate_is_rejected_on_identity_step(hass: HomeAssistant) -> None:
    entry = config_entries.ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Phone",
        data={"tracker_name": "Phone", CONF_SOURCE: "sensor.phone_battery"},
        source=config_entries.SOURCE_USER,
        unique_id=None,
        discovery_keys={},
        options={},
        subentries_data={},
    )
    entry.add_to_hass(hass)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], IDENTITY
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "already_configured"}


async def test_options_manual_without_capacity_clears_profile_values(
    hass: HomeAssistant,
) -> None:
    """Switching to manual with no capacity must disable stored profile values."""
    entry = config_entries.ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Phone",
        data={
            "tracker_name": "Phone",
            CONF_SOURCE: "sensor.phone_battery",
            "device_profile": "google_pixel_8_pro",
            "battery_capacity": 5050,
            "unit_of_measurement": "mAh",
            "battery_voltage": 3.85,
        },
        source=config_entries.SOURCE_USER,
        unique_id="sensor.phone_battery:",
        discovery_keys={},
        options={},
        subentries_data={},
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"configuration_mode": "manual"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], TRACKING
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["device_profile"] == "manual"
    assert result["data"]["battery_capacity"] is None
    assert result["data"]["unit_of_measurement"] is None
    assert result["data"]["battery_voltage"] is None


async def test_options_manual_wh_clears_old_voltage(hass: HomeAssistant) -> None:
    """A manual Wh configuration must not inherit an old mAh voltage."""
    entry = config_entries.ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Phone",
        data={
            "tracker_name": "Phone",
            CONF_SOURCE: "sensor.phone_battery",
            "device_profile": "google_pixel_8_pro",
            "battery_capacity": 5050,
            "unit_of_measurement": "mAh",
            "battery_voltage": 3.85,
        },
        source=config_entries.SOURCE_USER,
        unique_id="sensor.phone_battery:",
        discovery_keys={},
        options={},
        subentries_data={},
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"configuration_mode": "manual"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"battery_capacity": 19.44, "unit_of_measurement": "Wh"},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], TRACKING
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["battery_capacity"] == 19.44
    assert result["data"]["unit_of_measurement"] == "Wh"
    assert result["data"]["battery_voltage"] is None


async def test_zero_precision_is_allowed(hass: HomeAssistant) -> None:
    """Allow whole-number output with zero decimal places."""
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], IDENTITY)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"configuration_mode": "manual"}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**TRACKING, "precision": 0}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["precision"] == 0
