# Battery Consumption

<p align="center">
  <img src="logo.png" alt="Battery Consumption logo" width="220">
</p>

<p align="center">
  A Home Assistant custom integration for tracking battery movement, energy, activity, cycles, and optional device telemetry from an existing battery-level entity.
</p>

<p align="center">
  <a href="https://github.com/swetoast/battery_consumption/actions/workflows/validate.yaml"><img src="https://github.com/swetoast/battery_consumption/actions/workflows/validate.yaml/badge.svg" alt="Validation"></a>
  <img src="https://img.shields.io/badge/Home%20Assistant-2025.12.2%2B-blue" alt="Home Assistant 2025.12.2 or newer">
  <a href="https://hacs.xyz/"><img src="https://img.shields.io/badge/HACS-Custom-orange" alt="HACS custom repository"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License"></a>
</p>

## Overview

Battery Consumption turns an existing battery percentage entity, or a numeric attribute on an entity, into a persistent Home Assistant battery tracker. The battery level remains the main sensor state while the integration calculates charge, discharge, accumulated movement, energy, estimated power, battery activity, and equivalent full cycles.

The configured battery-level source is authoritative. Optional Home Assistant Companion App entities can improve activity, measured power, cycle context, and telemetry, but never alter the original battery accounting, totals, timestamps, or restore behavior.

## Key features

- UI-based setup, options, and reconfiguration.
- Immediate battery-level availability from the current source state.
- Persistent charge and discharge totals across Home Assistant restarts.
- Optional battery capacity from a verified profile or manual configuration.
- Energy calculations for `Wh`, `kWh`, and `MWh` capacities.
- Conversion of `mAh` capacity to `Wh` using nominal voltage.
- Optional activity, power, and equivalent-full-cycle sensors.
- Conservative device-profile suggestions that require user approval.
- Optional same-device Companion App support for phones and watches.
- Config-entry diagnostics and actionable Home Assistant repairs.
- Validated bundled and user-defined battery profiles.

## Requirements

- Home Assistant `2025.12.2` or newer.
- A source entity or attribute containing a numeric battery percentage from `0` through `100`.
- Battery capacity only when energy, power, or cycle-related output is wanted.
- Nominal voltage when capacity is entered in `mAh`.

Home Assistant `2025.12.2` is the compatibility target. Static validation is included in the repository. Exact runtime compatibility must still be confirmed in the target Home Assistant installation before treating a new release as production-verified.

## Installation

### HACS custom repository

1. Open HACS in Home Assistant.
2. Open the menu and select **Custom repositories**.
3. Add `https://github.com/swetoast/battery_consumption` as an **Integration** repository.
4. Search for **Battery Consumption** and install it.
5. Restart Home Assistant.
6. Open **Settings > Devices & services > Add integration**.
7. Search for **Battery Consumption**.

HACS updates are published through GitHub Releases. A release tag and the integration version in `manifest.json` must match for an update to be published correctly.

### Manual installation

1. Copy `custom_components/battery_consumption` into the Home Assistant `custom_components` directory.
2. Restart Home Assistant.
3. Add **Battery Consumption** from **Settings > Devices & services**.

The resulting path must be:

```text
/config/custom_components/battery_consumption/
```

## Quick start

1. Enter a short tracker name.
2. Select the battery-level source entity.
3. Enter a source attribute only when the percentage is stored in an attribute instead of the entity state.
4. Choose a verified device profile or enter capacity manually.
5. Keep optional Companion App fields empty unless matching entities exist on the same Home Assistant device.
6. Choose which optional sensors should be created.
7. Submit the form.

The first valid source value becomes the baseline. It does not create charge, discharge, energy, power, cycle totals, or session movement.

## How battery activity works

Battery activity has three states:

- `charging`
- `discharging`
- `idle`

For a device without Companion App charging data:

- A rising battery level reports `charging`.
- A falling battery level reports `discharging`.
- No movement reports `idle`.
- Movement-derived activity returns to `idle` after the configured session timeout.
- An initial value, including `100%`, is an idle baseline.
- A rise from `99%` to `100%` is temporarily `charging`, then returns to `idle`.

For a Companion App device, the integration uses this activity priority:

1. `battery_state: full` reports `idle`.
2. `is_charging: on` reports `charging`.
3. Other recognized battery-state values provide charging or discharging context.
4. Battery-level movement is the fallback.

A separate `charged` state is intentionally not created. A generic `100%` reading does not prove that a device is connected to power or has finished its charging process.

## Optional Companion App inputs

The integration can use these optional entities when they belong to the same Home Assistant device as the battery-level source:

- Is charging
- Battery state
- Charger type
- Battery power
- Battery temperature
- Battery health
- Hardware battery cycle count
- Remaining charge time

Every field is optional. Devices without Companion App sensors continue to use battery-level movement only.

Companion inputs affect only optional output and context:

- **Activity:** charging, discharging, full, and charger context.
- **Power:** measured battery power when available, otherwise the original estimate.
- **Cycles:** hardware cycle count as comparison context.
- **Telemetry:** battery temperature, health, charger type, and remaining charge time.

They do not change the original battery-level calculations, accumulated totals, timestamps, or restore behavior.

## Device profiles

A device profile supplies verified battery capacity and, when required, nominal voltage. The setup flow can suggest a profile from the Home Assistant device linked to the selected source entity. The suggestion is never applied until it is selected and submitted. Ambiguous matches are not guessed.

Profiles have two origins:

- **Bundled:** Included with the integration and validated during release checks.
- **User:** Loaded from `battery_consumption_device_profiles.json` in the Home Assistant configuration directory.

A valid user profile with the same ID overrides the bundled profile. An invalid override is rejected and the bundled profile remains active.

### Custom profile using watt-hours

```json
{
  "schema_version": 1,
  "devices": [
    {
      "id": "example_device_20wh",
      "manufacturer": "Example",
      "model": "Device 20 Wh",
      "capacity": 20,
      "capacity_unit": "Wh",
      "source": "https://example.com/device-specification",
      "notes": "Verified 20 Wh battery capacity"
    }
  ]
}
```

### Custom profile using milliamp-hours

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
      "nominal_voltage": 3.85,
      "source": "https://example.com/device-specification",
      "notes": "Verified 5000 mAh capacity at 3.85 V nominal voltage"
    }
  ]
}
```

Validate a profile catalog locally:

```bash
python3 scripts/validate_device_profiles.py battery_consumption_device_profiles.json
```

Reload the integration after changing the user profile file.

## Entities

### Battery level

The main sensor keeps the monitored percentage as its state and retains the original accounting attributes, including:

- Current variation
- Current charge and discharge
- Accumulated charge and discharge
- Capacity and energy values when configured
- Current and previous timestamps
- Estimated instantaneous power

### Battery activity

Optional enum sensor with `charging`, `discharging`, and `idle` states. It owns session context and optional Companion telemetry.

### Equivalent full cycles

Optional diagnostic sensor calculated from accumulated discharge. A total of 100 percentage points of discharge equals one equivalent full cycle, even when accumulated across several partial sessions.

A Companion App hardware cycle count is comparison context only. It does not replace the calculated equivalent-full-cycle value.

### Battery power

Optional power sensor. A valid Companion battery-power entity provides measured power. Otherwise, the integration uses the original estimate based on confirmed battery movement, configured capacity, and elapsed time. The sensor attributes identify whether the current value is measured or estimated.

## Iconography

Battery level and Battery power use their native Home Assistant device-class icons for consistent dashboard behavior. Battery activity changes icon with its state: charging, discharging, or idle. Equivalent full cycles uses a battery-cycle icon, and the Reset totals action has its own reset icon.

State-based icons are defined through Home Assistant icon translations rather than runtime entity properties.

## Resetting totals

Call the `battery_consumption.reset_totals` action and target one Battery Consumption entity.

The action resets:

- Accumulated charge
- Accumulated discharge
- Equivalent full cycles
- Current activity session

The tracker configuration, entities, and current battery level are not removed. Resetting totals cannot be undone.

## Diagnostics and repairs

Download diagnostics from the Battery Consumption config-entry menu. Diagnostics include integration and catalog versions, selected profile details, source validity, configured Companion input types, availability, and sanitized profile-loading outcomes. Diagnostics do not dump unrelated Home Assistant entities or complete registries.

Battery Consumption creates repair issues for actionable configuration problems:

- The battery-level source was removed.
- An available source no longer provides the configured attribute.
- A selected profile no longer exists.
- A custom profile catalog is invalid.
- A configured optional Companion entity was removed.
- A Companion entity belongs to another Home Assistant device.

Temporary `unknown` or `unavailable` source states do not create a missing-attribute repair. Correcting the configuration and reloading the entry removes resolved issues.

## Updating

HACS checks published GitHub Releases for newer versions. When an update is available:

1. Open **Settings > Updates** or HACS.
2. Read the release notes.
3. Install the update.
4. Restart Home Assistant.

Before updating an established installation, create a Home Assistant backup. Existing entity IDs, unique IDs, totals, timestamps, and restore behavior are intended to remain stable across upgrades.

See [CHANGELOG.md](CHANGELOG.md) for release history.

## Troubleshooting

### The source is unavailable

The Battery Consumption entities follow source availability. When the source returns, its first valid value establishes a fresh accounting baseline. Movement during the unavailable period is not counted as one large event.

### The source value is rejected

The source must provide a numeric value from `0` through `100`. Unknown, unavailable, nonnumeric, negative, and above-100 values are excluded from accounting.

### A source attribute produces no value

Confirm that the configured attribute exists and contains a numeric percentage. Leave the source attribute empty when the entity state already contains the percentage.

### Energy or power is missing

Energy values require battery capacity. `mAh` capacity also requires nominal voltage. Estimated power requires confirmed movement and elapsed time.

### Activity remains charging or discharging

Movement-derived activity returns to `idle` after the configured session timeout. Companion-derived charging remains active while its explicit charging input remains active, except that an explicit `full` battery state reports `idle`.

### A profile does not appear

Run the profile validator, correct every reported error, reload the integration, and check Home Assistant Repairs. Invalid user additions and overrides are rejected without replacing valid bundled profiles.

## Support and contributing

Use the repository issue tracker for reproducible bug reports and feature requests. Include the Home Assistant version, Battery Consumption version, relevant diagnostics, expected behavior, and observed behavior.

Device-profile contributions must use the repository's **Device battery profile** issue form. Each contribution requires an exact manufacturer and model, capacity, unit, nominal voltage for `mAh`, a reliable public source, and known regional or hardware variations. Series-wide profiles require evidence that every listed model uses the same battery specification.

The repository includes validation for JSON Schema, runtime profile loading, selector output, duplicate IDs and labels, ambiguous matching metadata, evidence fields, units, voltage, sorting, HACS, and Hassfest.

## Project documentation

- [Changelog](CHANGELOG.md)
- [Completed roadmap and release test matrix](docs/ROADMAP.md)
- [HACS information page](info.md)

## License and acknowledgements

Battery Consumption is distributed under the MIT License. See [LICENSE](LICENSE).

This repository is a fork of the original [Battery Consumption project by `jugla`](https://github.com/jugla/battery_consumption). The original copyright and permission notice remain in the license file.
