<p align="center">
  <img src="logo.png" alt="Battery Consumption logo" width="320">
</p>

# Battery Consumption

Battery Consumption is a Home Assistant custom integration that tracks battery movement, accumulated charge and discharge, energy, activity, equivalent full cycles, and optional power from an existing battery-level entity.

## Main capabilities

- UI-based setup and reconfiguration.
- Immediate battery-level availability without false startup totals.
- Persistent accumulated values across Home Assistant restarts.
- Verified bundled and user-defined device profiles.
- Optional Companion App activity, measured power, cycle context, and telemetry.
- Sanitized diagnostics and actionable repairs.

The battery-level source remains authoritative for the original calculations, totals, timestamps, and restore behavior. Companion App inputs are optional and never replace that accounting contract.

## Requirements

- Home Assistant 2025.12.2 or newer.
- A numeric battery percentage entity or attribute from 0 through 100.

Install the integration, restart Home Assistant, then add Battery Consumption from **Settings > Devices & services**.

See the repository README for complete installation, configuration, profile, troubleshooting, and contribution documentation. Read the GitHub Release notes before updating.
