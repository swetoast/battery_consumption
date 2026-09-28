<p align="center">
  <img src="logo.png" alt="Battery Consumption logo" width="420">
</p>

# battery_consumption
## Description

Battery Consumption is a custom integration for [Home Assistant](https://www.home-assistant.io/) that calculates battery charge, discharge, accumulated changes, energy values, and estimated power from an existing battery-level entity.

![GitHub release](https://img.shields.io/github/release/swetoast/battery_consumption)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)

The integration keeps the battery level as the sensor state and updates whenever its source entity changes. It can expose current variation, charge and discharge percentages, accumulated values, energy values, and estimated instantaneous power.

Version 2.10.2 gives every optional sensor one clear value and only the attributes needed to explain that value, and includes the new project icon. Version 2.10.4 makes a new tracker available immediately from its source entity without creating false usage totals. Version 2.10.5 also replaces an unusable restored state with the source entity current numeric level. This fork targets Home Assistant 2025.12.2. Version 2.5.0 adds device grouping, native naming, improved selectors, safe recovery and restoration, an optional native power sensor, a reset action, tests, and modern validation workflows. Version 2.4.0 adds optional noise filtering, battery activity sessions, and equivalent full-cycle tracking. Version 2.4.1 adds polished entity categories and dynamic icons. The new entities and filtering are disabled by default.

## Configuration

Add Battery Consumption from **Settings → Devices & services → Add integration**. Configure the source entity, optional source attribute, precision, optional battery capacity, and optional capacity unit.

After setup, use **Configure** for precision, battery capacity, capacity unit, minimum meaningful change, session timeout, and the optional activity and equivalent full-cycle sensors. Use **Reconfigure** for the source entity or source attribute. The existing sensor keeps its stable unique ID and entity-registry identity. Existing YAML configuration remains supported but is not imported automatically into the user interface.

For HACS, add `https://github.com/swetoast/battery_consumption` as a custom **Integration** repository, install Battery Consumption, restart Home Assistant, and then add the integration from **Settings → Devices & services**.

## Other information

Full installation, removal, troubleshooting, action, YAML, attribute, upgrade, and release information are available in the [Battery Consumption repository](https://github.com/swetoast/battery_consumption).

This is a fork of the original Battery Consumption project by `jugla`. The project remains distributed under the included MIT License, and the original copyright and permission notice are retained in `LICENSE`.
