# Battery Consumption

Battery Consumption is a custom integration for [Home Assistant](https://www.home-assistant.io/) that calculates battery charge, discharge, accumulated changes, energy values, and estimated power from an existing battery-level entity.

![GitHub release](https://img.shields.io/github/release/swetoast/battery_consumption)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)

<p align="center">
  <img src="https://github.com/home-assistant/brands/blob/master/custom_integrations/battery_consumption/icon%402x.png" alt="Battery Consumption icon" width="400">
</p>

The integration keeps the battery level as the sensor state and updates whenever its source entity changes. It provides attributes for:

- Current battery variation
- Charge and discharge percentages
- Accumulated charge and discharge percentages
- Battery capacity and current energy level when capacity is configured
- Charge, discharge, and accumulated energy values when capacity is configured
- Estimated instantaneous power when capacity and a valid update interval are available

This fork targets Home Assistant 2025.12.2 and supports both user-interface configuration and the existing YAML configuration format.

## Configuration

### User interface

1. Open **Settings → Devices & services**.
2. Select **Add integration**.
3. Search for **Battery Consumption**.
4. Configure the source entity and the required calculation settings.

The following fields are available:

- **Source entity**: Entity containing the battery level to monitor.
- **Source attribute**: Optional attribute containing the battery level. Leave this empty to use the source entity state.
- **Precision**: Number of decimal places used for calculated values. The default is `2`.
- **Battery capacity**: Optional full battery capacity used to calculate energy and power values.
- **Capacity unit**: Optional unit associated with the configured battery capacity, such as `Wh` or `kWh`.
- **Minimum meaningful change**: Optional noise threshold in percentage points. The default `0` preserves the original behavior.
- **Session timeout**: Minutes without confirmed movement before activity returns to `idle`. The default is `15`.
- **Create battery activity sensor**: Adds an optional `charging`, `discharging`, or `idle` sensor. Disabled by default.
- **Create equivalent full cycles sensor**: Adds an optional accumulated discharge-cycle sensor. Disabled by default.

After setup, use **Configure** to change calculation options such as precision, battery capacity, and capacity unit. Use **Reconfigure** to change the source entity or source attribute. Both operations reload the existing config entry, while the sensor keeps the same stable unique ID and Home Assistant entity-registry identity.

Each source entity and source attribute combination can be configured once through the user interface. Existing YAML configurations are not imported automatically and continue to run as YAML configurations.

## Installation

Install the integration through HACS as a custom repository or install it manually.

### [HACS](https://hacs.xyz/) (Home Assistant Community Store)

This fork is installed as a custom HACS repository unless it has separately been accepted into the HACS default repository list.

1. Open HACS in Home Assistant.
2. Open the menu and select **Custom repositories**.
3. Add `https://github.com/swetoast/battery_consumption`.
4. Select **Integration** as the repository category.
5. Select **Battery Consumption** and install it.
6. Restart Home Assistant.
7. Add the integration from **Settings → Devices & services → Add integration**.

### Manual

<details>
<summary>Manual procedure</summary>

1. Download the `battery_consumption` folder from the latest release of this repository.
2. Copy it to `<config>/custom_components/battery_consumption` in your Home Assistant configuration directory.
3. Restart Home Assistant.
4. Add the integration from **Settings → Devices & services → Add integration**.

</details>

## Breaking change

Version 2.2.0 added config-entry setup, a config flow, and an options flow for Home Assistant 2025.12.2. Existing YAML configuration remains supported and keeps its existing sensor calculations and attributes.

YAML configurations are not automatically migrated into the user interface. To move an existing YAML sensor to the user interface, first record its settings, remove that YAML entry, restart Home Assistant, and then add the equivalent entry from **Settings → Devices & services**. Avoid running an equivalent YAML and UI entry at the same time because both would monitor the same source independently.

Version 2.2.1 updated repository ownership, links, and Home Assistant metadata for the `swetoast/battery_consumption` fork. Version 2.2.2 completed the documentation update without changing sensor behavior. Version 2.3.0 adds full config-entry lifecycle handling: create and delete through Home Assistant, dedicated reconfiguration for source fields, calculation options, duplicate-source protection, automatic reloads, and a stable entity unique ID based on the config-entry ID.

This project is a fork of the original Battery Consumption project by `jugla`. The included MIT License permits use, copying, modification, merging, publication, distribution, sublicensing, and sale, provided that the original copyright notice and permission notice remain included. The original `Copyright (c) 2021 jugla` notice has therefore been retained in `LICENSE`.

## Using the component

The user interface is the recommended configuration method for new installations. The original YAML format remains available for existing installations.

```yaml
battery_consumption:
  zoe_battery_consumption:
    source: sensor.zoe_battery_level
    attribute: battery_level
    unique_id: zoe_battery_consumption
    precision: 2
    battery_capacity: 52
    unit_of_measurement: kWh
```

Configuration keys:

- `source`: Required source entity containing the battery level.
- `attribute`: Optional source attribute containing the battery level. If omitted, the entity state is used.
- `unique_id`: Optional unique ID for YAML-created sensors.
- `precision`: Optional number of decimal places. The default is `2`.
- `battery_capacity`: Optional full battery capacity. Energy and power attributes are only calculated when this is configured.
- `unit_of_measurement`: Optional unit used for the configured battery capacity and calculated energy attributes.

The created sensor name retains the existing format:

- Without a source attribute: `battery_consumption_<source entity>`
- With a source attribute: `battery_consumption_<source entity>_<attribute>`

## Sensor and attribute

The sensor state is the current monitored battery value rounded to the configured precision.

The integration exposes the following attributes:

| Attribute | Availability | Unit | Description |
| --- | --- | --- | --- |
| `source` | Always | None | Source entity monitored by the integration |
| `source_attribute` | When configured | None | Source attribute monitored instead of the entity state |
| `previous_value` | Always | Source value unit | Previously recorded battery value |
| `last_updated` | Always | Timestamp | Update time of the current monitored value |
| `previous_last_updated` | Always | Timestamp | Update time of the previous monitored value |
| `delta_last_updated_in_minutes` | Always | Minutes | Time between the current and previous value |
| `variation` | Always | `%` | Difference between the current and previous battery values |
| `battery_charge` | Always | `%` | Positive battery variation; otherwise `0` |
| `battery_discharge` | Always | `%` | Absolute value of a negative battery variation; otherwise `0` |
| `total_charge` | Always | `%` | Accumulated positive battery variations |
| `total_discharge` | Always | `%` | Accumulated absolute negative battery variations |
| `capacity_unit` | With battery capacity | Configured capacity unit | Unit configured for battery capacity |
| `capacity` | With battery capacity | Configured capacity unit | Configured full battery capacity |
| `energy_level` | With battery capacity | Configured capacity unit | Energy represented by the current battery level |
| `energy_variation` | With battery capacity | Configured capacity unit | Energy represented by the current battery variation |
| `energy_charge` | With battery capacity | Configured capacity unit | Energy represented by the current charge variation |
| `energy_discharge` | With battery capacity | Configured capacity unit | Energy represented by the current discharge variation |
| `total_energy_charge` | With battery capacity | Configured capacity unit | Energy represented by accumulated charge variations |
| `total_energy_discharge` | With battery capacity | Configured capacity unit | Energy represented by accumulated discharge variations |
| `instant_power` | With battery capacity and valid update interval | Capacity unit per hour | Estimated power calculated from energy variation and elapsed time |

Accumulated values are restored from the previous Home Assistant state after a restart.

## Typical use

Template sensors can expose the accumulated energy attributes as dedicated energy entities for use with utility meters.

```yaml
template:
  - sensor:
      - name: Zoe battery total charge
        state: >-
          {{ state_attr(
            'sensor.battery_consumption_sensor_zoe_battery_level',
            'total_energy_charge'
          ) }}
        unit_of_measurement: kWh
        device_class: energy
        state_class: total

      - name: Zoe battery total discharge
        state: >-
          {{ state_attr(
            'sensor.battery_consumption_sensor_zoe_battery_level',
            'total_energy_discharge'
          ) }}
        unit_of_measurement: kWh
        device_class: energy
        state_class: total

utility_meter:
  zoe_battery_total_charge_daily:
    source: sensor.zoe_battery_total_charge
    cycle: daily
  zoe_battery_total_charge_weekly:
    source: sensor.zoe_battery_total_charge
    cycle: weekly
  zoe_battery_total_charge_monthly:
    source: sensor.zoe_battery_total_charge
    cycle: monthly
  zoe_battery_total_discharge_daily:
    source: sensor.zoe_battery_total_discharge
    cycle: daily
  zoe_battery_total_discharge_weekly:
    source: sensor.zoe_battery_total_discharge
    cycle: weekly
  zoe_battery_total_discharge_monthly:
    source: sensor.zoe_battery_total_discharge
    cycle: monthly
```

A template sensor can also expose the current battery variation for statistics and graph cards.

```yaml
template:
  - sensor:
      - name: Zoe battery variation
        state: >-
          {{ state_attr(
            'sensor.battery_consumption_sensor_zoe_battery_level',
            'variation'
          ) }}
        unit_of_measurement: "%"
        device_class: battery
        state_class: measurement
```

Replace the example entity IDs with the entities created in your Home Assistant installation.

## Noise-resistant tracking and battery sessions

Version 2.4.0 adds optional noise-resistant accounting and two optional entities. All new features are disabled by default, so upgrading retains the existing behavior until they are enabled from **Configure**.

### Minimum meaningful change

`Minimum meaningful change` controls how far the battery level must move from the last accounted level before the integration records charge or discharge. A value of `0` preserves the original behavior and records every numeric change.

With a threshold of `2`, changes such as `50 → 51 → 50 → 51` are treated as unconfirmed movement. A later value of `52` confirms a 2 percentage-point charge from the last accounted level of `50`. This prevents small source fluctuations from inflating accumulated charge and discharge totals.

### Battery activity sensor

When enabled, the activity sensor reports one of these states:

- `charging`
- `discharging`
- `idle`

A confirmed change starts or continues a session in the relevant direction. A change in direction starts a new session. The configured session timeout changes the activity to `idle` after no confirmed movement has occurred for that number of minutes.

The activity sensor includes the session start time, session starting level, confirmed session change, and session energy when battery capacity is configured.

### Equivalent full cycles sensor

When enabled, the equivalent full cycles sensor calculates:

```text
total accumulated discharge percentage / 100
```

For example, five separate 20% discharges equal one equivalent full cycle. This is an accounting measure based on observed battery-level movement. It is not a battery-health estimate and does not claim to represent the hardware battery-management system's internal cycle count.

### Data validation and continuity

Battery source values outside `0` to `100`, non-numeric values, and unavailable source states are rejected instead of being included in the calculations. The Battery Consumption entities follow source availability.

Changing calculation options preserves accumulated totals. Reconfiguring the source entity or source attribute keeps the Home Assistant entity identity but starts accounting from the new source without restoring totals that belonged to the previous source.
