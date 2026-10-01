"""Typed internal models for Battery Consumption."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypedDict

CapacityUnit = Literal["mAh", "Wh", "kWh", "MWh"]
EnergyUnit = Literal["Wh", "kWh", "MWh"]
PowerUnit = Literal["W", "kW", "MW"]
BatteryActivity = Literal["charging", "discharging", "idle"]
ActivitySourceType = Literal["battery_level", "is_charging", "battery_state"]
PowerSourceType = Literal["measured", "estimated"]
ProfileOrigin = Literal["bundled", "user"]
ProfileCatalogError = Literal["invalid_json", "unsupported_schema", "invalid_devices"]


class CompanionEntityConfig(TypedDict, total=False):
    """Stored optional Companion App entity IDs."""

    companion_is_charging: str
    companion_battery_state: str
    companion_charger_type: str
    companion_battery_power: str
    companion_battery_temperature: str
    companion_battery_health: str
    companion_battery_cycle_count: str
    companion_remaining_charge_time: str


class TrackerConfig(CompanionEntityConfig, total=False):
    """Stored config-entry or YAML values before normalization."""

    tracker_name: str
    source: str
    attribute: str
    device_profile: str
    battery_capacity: float
    battery_voltage: float
    unit_of_measurement: CapacityUnit
    precision: int
    minimum_change: float
    session_timeout: int
    create_activity_sensor: bool
    create_cycle_sensor: bool
    create_power_sensor: bool


@dataclass(frozen=True, slots=True)
class CompanionEntities:
    """Normalized optional Companion App entity IDs."""

    is_charging: str | None = None
    battery_state: str | None = None
    charger_type: str | None = None
    battery_power: str | None = None
    battery_temperature: str | None = None
    battery_health: str | None = None
    battery_cycle_count: str | None = None
    remaining_charge_time: str | None = None


@dataclass(frozen=True, slots=True)
class BatteryPowerResult:
    """Power value and provenance exposed by the optional power sensor."""

    value: float
    source_type: PowerSourceType
    source_entity_id: str | None = None


@dataclass(frozen=True, slots=True)
class DeviceProfile:
    """Validated immutable battery profile."""

    profile_id: str
    manufacturer: str
    model: str
    capacity: float
    capacity_unit: CapacityUnit
    nominal_voltage: float | None
    origin: ProfileOrigin
    source: str | None = None
    notes: str | None = None
    model_aliases: tuple[str, ...] = field(default_factory=tuple)
    model_ids: tuple[str, ...] = field(default_factory=tuple)
    hardware_versions: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class EffectiveTrackerConfig:
    """Validated effective configuration used after storage normalization."""

    tracker_name: str
    source_entity_id: str
    source_attribute: str | None
    profile_id: str | None
    capacity: float | None
    capacity_unit: CapacityUnit | None
    nominal_voltage: float | None
    effective_capacity_wh: float | None
    precision: int
    minimum_change: float
    session_timeout: int
    create_activity_sensor: bool
    create_cycle_sensor: bool
    create_power_sensor: bool
    companion: CompanionEntities


@dataclass(slots=True)
class ProfileLoadReport:
    """Sanitized profile-loading result shared by diagnostics and repairs."""

    bundled_loaded: int = 0
    user_loaded: int = 0
    user_overrides: list[str] = field(default_factory=list)
    rejected_user_entries: int = 0
    user_catalog_error: ProfileCatalogError | None = None

    @property
    def has_user_errors(self) -> bool:
        """Return whether the user catalog requires attention."""
        return self.user_catalog_error is not None or self.rejected_user_entries > 0
