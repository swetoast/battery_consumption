"""Config-flow tests for Battery Consumption."""

from homeassistant import config_entries
from homeassistant.const import CONF_SOURCE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.data_entry_flow import FlowResultType

from custom_components.battery_consumption.config_flow import (
    _companion_device_mismatches,
    _companion_suggestions,
    _source_device_placeholders,
)
from custom_components.battery_consumption.const import (
    CONF_COMPANION_BATTERY_STATE,
    CONF_COMPANION_IS_CHARGING,
    DOMAIN,
)

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


def _registered_entity(hass, unique_id, object_id, device_id):
    return er.async_get(hass).async_get_or_create(
        domain="sensor",
        platform="test",
        unique_id=unique_id,
        suggested_object_id=object_id,
        device_id=device_id,
    )


def test_companion_suggestions_are_limited_to_source_device(hass: HomeAssistant) -> None:
    devices = dr.async_get(hass)
    source_device = devices.async_get_or_create(
        config_entry_id="source_config",
        identifiers={("test", "source_device")},
    )
    other_device = devices.async_get_or_create(
        config_entry_id="other_config",
        identifiers={("test", "other_device")},
    )
    source = _registered_entity(hass, "source", "phone_battery", source_device.id)
    charging = _registered_entity(
        hass, "charging", "phone_is_charging", source_device.id
    )
    _registered_entity(hass, "other", "watch_battery_state", other_device.id)

    suggestions = _companion_suggestions(hass, source.entity_id)

    assert suggestions == {CONF_COMPANION_IS_CHARGING: charging.entity_id}


def test_companion_device_mismatch_detects_only_other_devices(
    hass: HomeAssistant,
) -> None:
    devices = dr.async_get(hass)
    source_device = devices.async_get_or_create(
        config_entry_id="source_config",
        identifiers={("test", "source_device")},
    )
    other_device = devices.async_get_or_create(
        config_entry_id="other_config",
        identifiers={("test", "other_device")},
    )
    source = _registered_entity(hass, "source", "phone_battery", source_device.id)
    same = _registered_entity(hass, "same", "phone_battery_state", source_device.id)
    other = _registered_entity(hass, "other", "watch_battery_state", other_device.id)

    assert _companion_device_mismatches(
        hass,
        source.entity_id,
        {CONF_COMPANION_BATTERY_STATE: same.entity_id},
    ) == []
    assert _companion_device_mismatches(
        hass,
        source.entity_id,
        {CONF_COMPANION_BATTERY_STATE: other.entity_id},
    ) == [other.entity_id]


def test_source_device_placeholders_show_registered_device(hass: HomeAssistant) -> None:
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id="source_config",
        identifiers={("test", "device")},
        name="Pixel phone",
        manufacturer="Google",
        model="Pixel 8 Pro",
    )
    source = _registered_entity(hass, "source_context", "phone_battery", device.id)

    assert _source_device_placeholders(hass, source.entity_id) == {
        "device_name": "Pixel phone",
        "manufacturer": "Google",
        "model": "Pixel 8 Pro",
    }


def test_source_device_placeholders_have_safe_fallback(hass: HomeAssistant) -> None:
    assert _source_device_placeholders(hass, "sensor.not_registered") == {
        "device_name": "No registered device",
        "manufacturer": "Unknown manufacturer",
        "model": "Unknown model",
    }
