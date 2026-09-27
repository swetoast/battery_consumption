# Battery Consumption

<p align="center">
  <img src="https://github.com/home-assistant/brands/blob/master/custom_integrations/battery_consumption/icon%402x.png" alt="Battery Consumption icon" width="220">
</p>

<p align="center">
  Track battery movement, accumulated charge and discharge, energy, activity sessions, equivalent full cycles, and estimated power in Home Assistant.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-2.5.0-blue" alt="Version 2.5.0">
  <img src="https://img.shields.io/badge/Home%20Assistant-2025.12.2-blue" alt="Home Assistant 2025.12.2">
  <a href="https://hacs.xyz/"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg" alt="HACS Custom"></a>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
</p>

Battery Consumption turns an existing percentage entity, or one of its attributes, into a detailed battery tracker. The integration updates when the source changes and keeps its accumulated values across Home Assistant restarts.

## Highlights

- Configure and manage trackers from the Home Assistant user interface.
- Track charge, discharge, accumulated movement, energy, and signed power.
- Filter small source fluctuations with an optional meaningful-change threshold.
- Track charging, discharging, and idle sessions.
- Calculate equivalent full discharge cycles.
- Group UI-created entities under one Battery Consumption device.
- Preserve stable entity identities across reloads and reconfiguration.

## Requirements

- Home Assistant `2025.12.2` or newer
- A source entity or attribute that reports a numeric battery level from `0` through `100`
- Battery capacity and a supported capacity unit only when energy or power calculations are required

## Installation

### HACS custom repository

1. Open HACS in Home Assistant.
2. Open the menu and select **Custom repositories**.
3. Add `https://github.com/swetoast/battery_consumption`.
4. Select **Integration** as the repository category.
5. Install **Battery Consumption**.
6. Restart Home Assistant.
7. Open **Settings → Devices & services → Add integration**.
8. Search for **Battery Consumption**.

### Manual installation

1. Clone or download the source repository.
2. Copy `custom_components/battery_consumption` into `<config>/custom_components/battery_consumption`.
3. Restart Home Assistant.
4. Open **Settings → Devices & services → Add integration**.
5. Search for **Battery Consumption**.

## Configuration

### Add a tracker

1. Open **Settings → Devices & services**.
2. Select **Add integration**.
3. Search for **Battery Consumption**.
4. Select the source entity.
5. Configure the calculation options and optional entities.

Each source entity and source attribute combination can be configured once.

### Available options

| Option | Purpose | Default |
| --- | --- | --- |
| Source entity | Entity that provides the battery percentage | Required |
| Source attribute | Optional attribute containing the percentage | Entity state |
| Precision | Decimal places shown for calculated values | `2` |
| Battery capacity | Full battery capacity used for energy and power calculations | Optional |
| Capacity unit | Capacity unit such as `Wh`, `kWh`, or `MWh` | Optional |
| Minimum meaningful change | Percentage-point movement required before accounting confirms a change | `0` |
| Session timeout | Minutes without confirmed movement before activity becomes idle | `15` |
| Create battery activity sensor | Adds the charging, discharging, and idle sensor | Disabled |
| Create equivalent full cycles sensor | Adds the derived cycle-count sensor | Disabled |
| Create battery power sensor | Adds a native signed power sensor | Disabled |

Use **Configure** to change calculation options. Use **Reconfigure** to change the source entity or source attribute. Reconfiguration keeps the existing Home Assistant entity identity while starting accounting from the new source.

## Entities

UI-created entities are grouped under one Battery Consumption device.

### Battery level

The primary sensor shows the current source percentage and uses the Home Assistant battery device class. It is always created.

Its attributes include:

- Previous monitored value
- Current variation
- Current charge and discharge
- Accumulated charge and discharge
- Current and previous update times
- Time between confirmed updates
- Capacity and energy values when capacity is configured
- Signed estimated power when a valid interval is available

### Battery activity

Optional regular sensor with these states:

- `charging`
- `discharging`
- `idle`

The icon changes with the current activity. Session attributes include the start time, starting level, confirmed change, and session energy when capacity is configured.

### Equivalent full cycles

Optional diagnostic sensor calculated from accumulated discharge:

```text
equivalent full cycles = total accumulated discharge percentage / 100
```

Five separate 20% discharges therefore equal one equivalent full cycle. This is an accounting metric based on observed battery movement, not a battery-health estimate or the hardware battery-management system's internal cycle count.

### Battery power

Optional power sensor created when battery capacity uses one of these supported units:

| Capacity unit | Power unit |
| --- | --- |
| `Wh` | `W` |
| `kWh` | `kW` |
| `MWh` | `MW` |

Power is calculated across the latest confirmed battery movement interval:

- Positive values indicate charging.
- Negative values indicate discharging.
- The sensor remains unavailable until a confirmed movement has a valid positive time interval.

## Noise-resistant accounting

Set **Minimum meaningful change** above `0` to reduce false totals caused by a noisy battery source.

With a threshold of `2`, this sequence is not recorded as charge or discharge:

```text
50 → 51 → 50 → 51
```

A later value of `52` confirms a two percentage-point charge from the last accounted level of `50`.

The displayed battery level still follows the source. Only the accumulated accounting waits for confirmed movement.

## Attribute reference

| Attribute | Availability | Description |
| --- | --- | --- |
| `source` | Always | Monitored source entity |
| `source_attribute` | When configured | Monitored source attribute |
| `previous_value` | Always | Previous source value |
| `last_updated` | Always | Time of the current source update |
| `previous_last_updated` | Always | Time of the previous source update |
| `delta_last_updated_in_minutes` | Always | Minutes between confirmed values |
| `variation` | Always | Confirmed difference between current and accounted values |
| `battery_charge` | Always | Positive confirmed movement, otherwise `0` |
| `battery_discharge` | Always | Absolute negative confirmed movement, otherwise `0` |
| `total_charge` | Always | Accumulated positive movement |
| `total_discharge` | Always | Accumulated negative movement |
| `capacity_unit` | With capacity | Configured battery-capacity unit |
| `capacity` | With capacity | Configured full battery capacity |
| `energy_level` | With capacity | Energy represented by the current battery level |
| `energy_variation` | With capacity | Energy represented by the confirmed change |
| `energy_charge` | With capacity | Energy represented by confirmed charging |
| `energy_discharge` | With capacity | Energy represented by confirmed discharging |
| `total_energy_charge` | With capacity | Energy represented by accumulated charging |
| `total_energy_discharge` | With capacity | Energy represented by accumulated discharging |
| `instant_power` | With capacity and valid interval | Signed estimated power over the latest confirmed interval |

## Reset accumulated totals

Use **Developer tools → Actions** and run **Battery Consumption: Reset totals** against any entity belonging to the tracker.

The action resets:

- Accumulated charge
- Accumulated discharge
- Equivalent full cycles
- Current activity session

Configuration, entities, and current battery level are not removed. Resetting totals cannot be undone.

## Troubleshooting

### Source entity is unavailable

The Battery Consumption entities follow source availability. When the source returns, its first valid value establishes a fresh accounting baseline. Movement during the unavailable period is not counted as one large event.

### Source value is rejected

The source must provide a numeric value from `0` through `100`. Unknown, unavailable, nonnumeric, negative, and above-100 values are excluded from accounting.

### Source attribute produces no value

Confirm that the attribute exists and contains a numeric percentage. Leave **Source attribute** empty when the entity state already contains the percentage.

### Energy or power is missing

Energy values require battery capacity. The native power sensor also requires the capacity unit to be exactly `Wh`, `kWh`, or `MWh`.

### Activity remains idle

Activity changes only after movement reaches **Minimum meaningful change**. Set the threshold to `0` to confirm every numeric change. Activity returns to idle after the configured session timeout.

## Removal

1. Open **Settings → Devices & services**.
2. Open **Battery Consumption**.
3. Open the menu for the tracker.
4. Select **Delete**.

Remove the custom repository through HACS only when no Battery Consumption trackers remain.

## Development

The repository includes:

- Pytest regression tests for calculations and config-flow behavior
- Ruff configuration
- HACS validation
- Hassfest validation
- A consolidated GitHub Actions workflow

## License

Battery Consumption is distributed under the MIT License.

This repository is a fork of the original [Battery Consumption project by `jugla`](https://github.com/jugla/battery_consumption). The original copyright and permission notice remain in [`LICENSE`](LICENSE).
