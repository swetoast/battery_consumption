# Battery Consumption

<p align="center">
  <img src="logo.png" alt="Battery Consumption icon" width="220">
</p>

<p align="center">
  Track battery movement, accumulated charge and discharge, energy, activity sessions, equivalent full cycles, and estimated power in Home Assistant.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-2.20.0-blue" alt="Version 2.20.0">
  <img src="https://img.shields.io/badge/Home%20Assistant-2025.12.2-blue" alt="Home Assistant 2025.12.2">
  <a href="https://hacs.xyz/"><img src="https://img.shields.io/badge/HACS-Custom-orange.svg" alt="HACS Custom"></a>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
</p>

Battery Consumption turns an existing percentage entity, or one of its attributes, into a detailed battery tracker. The integration updates when the source changes and keeps its accumulated values across Home Assistant restarts.

## Battery-level source and startup behavior

The configured battery-level entity, or its selected attribute, is the authoritative source for battery percentage. It is the only source used for the original variation, charge, discharge, energy, accumulated totals, timestamps, and restore behavior.

A tracker starts from whatever valid numeric percentage the source currently reports, including `0`, `1`, `42`, `99`, or `100`. The first valid value is a baseline only. It does not create charge, discharge, energy, power, cycle totals, or session movement.

If the source initially reports `unknown` or `unavailable`, the tracker waits for the first valid numeric value and uses that value as the baseline. When a usable restored battery level exists, normal restore behavior is preserved.

## Optional Companion App battery inputs

For phones and watches running the Home Assistant Companion App, a tracker can use optional supporting entities from the same Home Assistant device: is charging, battery state, charger type, measured battery power, battery temperature, battery health, hardware battery cycle count, and remaining charge time.

The setup flow suggests matching enabled entities from the same device. Every field remains optional, so ordinary battery-powered smart devices continue to work without Companion App sensors.

The battery-level source remains the only input used by the original variation, charge, discharge, energy, timestamp, total, and restore calculations. Companion inputs only improve optional activity, power, cycle context, and telemetry outputs.


### Optional sensor attribute ownership

Each optional entity has one primary value and only the attributes needed to explain that value:

- Battery activity owns session context and optional Companion telemetry.
- Battery power owns measured or estimated source provenance.
- Equivalent full cycles owns its calculation and optional hardware cycle comparison.
- The main battery-level sensor retains the original accounting attributes unchanged.


## Version 2.20.0

Completes the user documentation for the stable calculation contract, startup baseline, device profiles, Companion App input priority, measured and estimated power, cycle meanings, diagnostics, repairs, and profile contributions. Existing configuration, sensors, totals, timestamps, and calculations are unchanged.

## Version 2.19.0

Completes the profile contribution workflow. The repository now includes a structured device-profile request form, evidence requirements, duplicate and ambiguous matching checks, stable ordering validation, JSON Schema validation, runtime-compatible contribution validation, and an updated CI workflow. Existing sensors and calculations remain unchanged.

## Version 2.18.0

Completes user-profile safety and tooling. Invalid custom additions or overrides can no longer displace valid bundled profiles, diagnostics report sanitized loading outcomes, Home Assistant creates an actionable repair for invalid custom catalog data, and a standalone local catalog validator is included.

## Version 2.17.0

Completes the configuration-flow improvement phase. Profile and supporting-input steps now show the detected Home Assistant device, explain profile approval, organize optional inputs by activity, power, telemetry, and cycle purpose, and clearly state that all supporting inputs are optional and must belong to the same device. Stored configuration, entities, totals, and calculations are unchanged.

## Version 2.16.0

Completes the static configuration repair set with actionable issues for a removed battery-level source, a configured source attribute that is no longer provided, and optional Companion entities that were removed. Unknown or temporarily unavailable source states do not trigger an attribute repair. Existing sensors and calculations remain unchanged.

## Version 2.15.0

Adds actionable Home Assistant repair issues for missing selected profiles and Companion entities registered to another device. Issues are created per tracker, removed automatically when the configuration is corrected, and deleted when the config entry is removed. Temporary source unavailability does not create a repair. Existing sensors and calculations remain unchanged.

## Version 2.14.0

Adds Home Assistant config-entry diagnostics for profile, source, catalog, and optional Companion input troubleshooting. Diagnostics deliberately omit entity IDs, current battery values, profile evidence URLs, and unrelated Home Assistant data. Existing sensors and calculations remain unchanged.

## Version 2.13.0

Completes same-device Companion App handling. Optional Companion entities are suggested only from the Home Assistant device that owns the battery-level source, and setup or reconfiguration now rejects registered supporting entities that belong to another device. Missing optional entities remain allowed and never affect the original battery calculations.

## Version 2.12.0

Adds conservative device-aware profile suggestions using the Home Assistant entity and device registries. Exact manufacturer/model matches and explicit aliases are suggested in the existing profile selector, but the user must still approve the selection. Ambiguous matches are never guessed. Existing entries, sensors, calculations, totals, timestamps, and restore behavior remain unchanged.

## Version 2.11.0

Adds formal profile-catalog validation, catalog versioning, runtime origin tracking, duplicate-ID protection, and shared selector generation. Every bundled profile is now tested through the same loader and selector path used by Home Assistant. Existing sensors, calculations, totals, timestamps, and restore behavior are unchanged.

## Version 2.10.5

Fixes the bundled Roborock profiles so they pass profile validation and appear in the Home Assistant device-profile selector. The fix adds the required 14.4 V nominal battery-pack voltage to every bundled Roborock profile, including the S8 Pro Ultra.


New trackers now read the current source state when added to Home Assistant, so Battery level is available immediately even when the source remains unchanged. The initial sample establishes the displayed level without adding charge, discharge, energy, cycle, or power totals. Restored trackers keep the existing restore path unchanged.


A tracker now initializes from the source entity whenever no usable restored battery level exists. This covers every valid initial numeric level, including trackers whose previous restored state was unavailable or unknown. The initial reading remains a baseline only and does not create charge, discharge, energy, power, or cycle totals.

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
4. Enter the tracker name and select the battery source.
5. Choose **Device profile** or **Manual configuration**.
6. Select the exact profile, or enter the manual battery specification.
7. Configure tracking behavior and optional entities.

Each source entity and source attribute combination can be configured once.

### Naming standard

The tracker name is combined with the integration namespace and entity purpose. For a tracker named `Pixel 9`, new entities use these initial entity IDs:

```text
sensor.battery_consumption_pixel_9_battery_level
sensor.battery_consumption_pixel_9_battery_activity
sensor.battery_consumption_pixel_9_battery_power
sensor.battery_consumption_pixel_9_equivalent_full_cycles
```

The virtual device is displayed as `Battery Consumption Pixel 9`. Entity names inside the device remain natural and translated: **Battery level**, **Battery activity**, **Battery power**, and **Equivalent full cycles**.

Entity IDs already registered by Home Assistant are not forcibly renamed. The namespaced format applies to new trackers and newly created optional entities. Stable unique IDs remain based on the config-entry ID, so changing the tracker name does not replace existing entities.

### Available options

| Option | Purpose | Default |
| --- | --- | --- |
| Tracker name | Short device name used in displayed names and namespaced entity IDs | Required |
| Source entity | Entity that provides the battery percentage | Required |
| Source attribute | Optional attribute containing the percentage | Entity state |
| Device profile | Known device battery profile or manual setup | Manual configuration |
| Precision | Decimal places shown for calculated values | `2` |
| Battery capacity | Capacity printed on the battery, such as `5050` | Optional |
| Capacity unit | `mAh`, `Wh`, `kWh`, or `MWh`; mAh is converted automatically | Optional |
| Battery nominal voltage | Required when manual capacity is entered in `mAh` | Required for manual `mAh` |
| Minimum meaningful change | Percentage-point movement required before accounting confirms a change | `0` |
| Session timeout | Minutes without confirmed movement before activity becomes idle | `15` |
| Create battery activity sensor | Adds the charging, discharging, and idle sensor | Disabled |
| Create equivalent full cycles sensor | Adds the derived cycle-count sensor | Disabled |
| Create battery power sensor | Adds a native signed power sensor | Disabled |

Use **Configure** to change calculation options. Use **Reconfigure** to change the source entity or source attribute. Reconfiguration keeps the existing Home Assistant entity identity while starting accounting from the new source.

## Device profiles

Select a known device during setup to fill battery capacity, unit, and nominal voltage automatically. The bundled catalog contains sourced profiles for popular Apple, Google, Samsung, Meta, and Valve devices, plus exact rechargeable AA, AAA, C, D, and 9V products from ANSMANN, Duracell, Panasonic, and VARTA. It also includes an Energizer CR2032 profile whose capacity is explicitly marked as load-dependent. Generic alkaline AA, AAA, C, D, and 9V profiles are intentionally excluded because their delivered capacity changes materially with load, cutoff voltage, temperature, and usage pattern.

The built-in catalog is stored in `custom_components/battery_consumption/device_profiles.json`. To add devices without modifying integration files, create:

```text
/config/battery_consumption_device_profiles.json
```

Use this format:

```json
{
  "schema_version": 1,
  "devices": [
    {
      "id": "manufacturer_device_model",
      "manufacturer": "Manufacturer",
      "model": "Device model",
      "capacity": 4000,
      "capacity_unit": "mAh",
      "nominal_voltage": 3.85,
      "source": "https://example.com/device-specification"
    }
  ]
}
```

Restart Home Assistant after editing the user profile file. User profiles are added to the bundled catalog. A user profile with the same `id` replaces the bundled entry. Invalid profiles are skipped and logged without preventing the integration from loading.

The selected profile values are copied into the config entry, so an existing tracker keeps working if its profile is later removed or changed.

## Profile selection and origin

A device profile supplies verified capacity and, when required, nominal voltage. The setup flow may suggest a profile from the source entity's registered Home Assistant device, but a suggestion is never applied until it is selected and submitted. Ambiguous matches are not guessed.

Profiles have one of two origins:

- **Bundled:** Included with the integration and validated during release checks.
- **User:** Loaded from `battery_consumption_device_profiles.json` in the Home Assistant configuration directory.

A valid user profile with the same ID intentionally overrides the bundled profile. An invalid override is rejected and the valid bundled profile remains active.

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

## Power and cycle meanings

### Measured and estimated power

When a valid Companion App battery-power entity is configured and available, the Battery power sensor uses that measured value. Otherwise, the sensor falls back to the original estimate calculated from confirmed battery movement, configured capacity, and elapsed time.

Measured Companion power improves the optional power output only. It does not replace or rewrite the original charge, discharge, energy, total, timestamp, or restore calculations. The power sensor attributes identify whether the current value is measured or estimated.

### Equivalent full cycles and hardware cycles

Equivalent full cycles are calculated from accumulated discharge. A total of 100 percentage points of discharge equals one equivalent full cycle, even when the discharge occurs across several partial sessions.

A Companion App hardware cycle count is optional comparison context. It does not replace equivalent full cycles because the device manufacturer may count hardware cycles differently.

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

## Diagnostics and repairs

Home Assistant can download diagnostics from the Battery Consumption config-entry menu. The report includes integration and catalog versions, selected profile details, source validity, optional Companion input availability, and sanitized profile-loading outcomes. It does not dump unrelated Home Assistant entities or complete registries.

Battery Consumption creates repair issues for actionable configuration problems:

- The battery-level source was removed.
- An available source no longer provides the configured attribute.
- A selected profile no longer exists.
- A custom profile catalog is invalid.
- A configured optional Companion entity was removed.
- A Companion entity belongs to another Home Assistant device.

Temporary `unknown` or `unavailable` source states do not create a missing-attribute repair. Correcting the configuration and reloading the entry removes resolved issues.

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

## Custom device profiles

Place `battery_consumption_device_profiles.json` in the Home Assistant configuration directory. Valid custom IDs override bundled profiles with the same ID; invalid overrides are rejected and the bundled profile remains active. Reload the integration after editing the file.

Example using watt-hours:

```json
{
  "schema_version": 1,
  "devices": [
    {
      "id": "example_device_20wh",
      "manufacturer": "Example",
      "model": "Device 20 Wh",
      "capacity": 20,
      "capacity_unit": "Wh"
    }
  ]
}
```

Example using milliamp-hours:

```json
{
  "schema_version": 1,
  "devices": [
    {
      "id": "example_device_5000mah",
      "manufacturer": "Example",
      "model": "Device 5000 mAh",
      "capacity": 5000,
      "capacity_unit": "mAh",
      "nominal_voltage": 3.85
    }
  ]
}
```

Validate a catalog locally with:

```bash
python3 scripts/validate_device_profiles.py battery_consumption_device_profiles.json
```


## Contributing device profiles

Use the repository's **Device battery profile** issue form. Every contribution must provide an exact manufacturer and model, capacity, unit, nominal voltage for `mAh`, a reliable public evidence URL, and known regional or hardware variations. Home Assistant manufacturer, model, aliases, model IDs, and hardware versions should be included when observed.

A series-wide profile is accepted only when the evidence shows that every listed model uses the same battery specification. Unverified variants must remain separate or be omitted. Contributions are checked for schema validity, runtime compatibility, selector visibility, duplicate IDs and labels, ambiguous matching metadata, evidence fields, units, voltage, and stable ordering.

