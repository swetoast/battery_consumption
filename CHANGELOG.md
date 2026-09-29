# Changelog

All notable changes to Battery Consumption are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and version numbers follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.23.0] - 2026-09-29

### Added

- A detailed stronger-typing phase in the project roadmap.
- Shared typed contracts for configuration, Companion inputs, profiles, activity, power, and profile-loading results.
- Incremental mypy validation in the repository workflow.

### Changed

- Replaced the optional power sensor's unnamed result tuple with a typed immutable result object.
- Moved the profile loading report to the shared typed models while preserving its runtime behavior.

### Compatibility

- No entity IDs, unique IDs, stored keys, sensor states, attributes, units, calculations, totals, timestamps, Companion priority, or restore behavior changed.

## [2.22.0] - 2026-09-29

### Added

- Home Assistant icon translations for Battery activity states.
- A dedicated icon for the Reset totals action.

### Changed

- Moved Battery activity and Equivalent full cycles icons from Python properties to `icons.json`.
- Battery power now uses the native Home Assistant power device-class icon instead of duplicating Battery activity icons.
- Battery level continues to use the native Home Assistant battery device-class icon.

## [2.21.0] - 2026-09-29

### Added

- Dedicated `CHANGELOG.md` with user-facing release history.
- HACS brand assets under `brand/`.
- Tag-driven GitHub Release workflow that verifies the tag against `manifest.json` and publishes the matching changelog section as release notes.
- Direct links from the README to installation, updates, support, the changelog, and the completed roadmap.

### Changed

- Rewrote the README around project overview, installation, configuration, behavior, entities, profiles, diagnostics, updating, troubleshooting, and contribution guidance.
- Replaced the old release-history block in the README with a link to this changelog.
- Rewrote `info.md` as a concise HACS information page.
- Consolidated repository validation into one workflow using current GitHub Actions.
- Moved the completed roadmap and release test matrix to `docs/ROADMAP.md`.
- Updated the HACS display name and declared Home Assistant `2025.12.2` as the minimum version.

### Removed

- Duplicate validation workflows.
- Redundant root `icon@2x.png`; HACS brand assets now live under `brand/`.

## [2.20.1] - 2026-09-29

### Fixed

- Made an explicit Companion battery state of `full` report `idle` even when `is_charging` remains on.
- Made movement-derived activity return to `idle` after the configured session timeout.
- Kept an initial `100%` reading as an idle baseline with no usage totals.
- Kept a generic rise from `99%` to `100%` temporarily `charging` before returning to `idle`.

## [2.20.0] - 2026-09-28

### Changed

- Completed the user documentation for source authority, startup baselines, profiles, Companion inputs, diagnostics, repairs, and contribution rules.
- Marked the original nine-phase roadmap complete.

## [2.19.0] - 2026-09-28

### Added

- Structured device-profile request form.
- Evidence, duplicate, ambiguity, ordering, selector, schema, and runtime-compatible profile validation.
- Updated profile validation workflow.

## [2.18.0] - 2026-09-28

### Added

- Safe user-profile loading reports in diagnostics.
- Repair issue for invalid custom profile catalogs.
- Standalone local profile validator.
- Complete `Wh` and `mAh` custom-profile examples.

### Fixed

- Invalid user overrides no longer displace valid bundled profiles.
- Malformed custom catalogs fall back to bundled profiles.

## [2.17.0] - 2026-09-28

### Changed

- Improved setup and options descriptions with detected Home Assistant device context.
- Clarified profile approval and the activity, power, telemetry, charging, and cycle purpose of optional Companion inputs.

## [2.16.0] - 2026-09-28

### Added

- Repair issues for removed battery-level sources, missing source attributes, and removed optional Companion entities.
- Automatic cleanup for resolved and deleted config-entry repair issues.

## [2.15.0] - 2026-09-28

### Added

- Home Assistant Repairs support.
- Repair issues for missing selected profiles and Companion entities registered to another device.

## [2.14.0] - 2026-09-28

### Added

- Sanitized config-entry diagnostics for source validity, selected profile, profile catalog, and optional Companion inputs.

## [2.13.0] - 2026-09-28

### Added

- Same-device validation for optional Companion entities during setup and reconfiguration.

## [2.12.0] - 2026-09-28

### Added

- Conservative device-aware profile suggestions using Home Assistant entity and device registries.
- Optional profile aliases, model IDs, and hardware-version matching metadata.

## [2.11.0] - 2026-09-28

### Changed

- Added catalog versioning, formal schema validation, profile-origin tracking, and selector coverage.
- Strengthened bundled profile validation without changing existing battery accounting.

## [2.10.5] - 2026-09-28

### Fixed

- Initialized a tracker from the current numeric source when no usable restored battery level exists.
- Preserved the first valid value as a baseline without creating totals.

## [2.10.4] - 2026-09-28

### Added

- Immediate initial battery-level availability from the configured source.

## [2.10.3] - 2026-09-28

### Fixed

- Added the required nominal voltage to bundled `mAh` Roborock profiles.

## [2.10.2] - 2026-09-28

### Changed

- Gave each optional sensor one clear state value and only the attributes needed to explain it.
- Added the project icon.

## [2.5.0]

### Added

- Config-entry device grouping and native entity naming.
- Reconfiguration, safer restoration, optional native power sensor, reset action, and expanded tests.

## [2.4.1]

### Changed

- Added entity categories and activity-aware icons.

## [2.4.0]

### Added

- Meaningful-change filtering, battery activity sessions, and equivalent full-cycle tracking.

[Unreleased]: https://github.com/swetoast/battery_consumption/compare/2.23.0...HEAD
[2.23.0]: https://github.com/swetoast/battery_consumption/compare/2.22.0...2.23.0
[2.22.0]: https://github.com/swetoast/battery_consumption/compare/2.21.0...2.22.0
[2.21.0]: https://github.com/swetoast/battery_consumption/compare/2.20.1...2.21.0
[2.20.1]: https://github.com/swetoast/battery_consumption/compare/2.20.0...2.20.1
[2.20.0]: https://github.com/swetoast/battery_consumption/compare/2.19.0...2.20.0
[2.19.0]: https://github.com/swetoast/battery_consumption/compare/2.18.0...2.19.0
[2.18.0]: https://github.com/swetoast/battery_consumption/compare/2.17.0...2.18.0
[2.17.0]: https://github.com/swetoast/battery_consumption/compare/2.16.0...2.17.0
[2.16.0]: https://github.com/swetoast/battery_consumption/compare/2.15.0...2.16.0
[2.15.0]: https://github.com/swetoast/battery_consumption/compare/2.14.0...2.15.0
[2.14.0]: https://github.com/swetoast/battery_consumption/compare/2.13.0...2.14.0
[2.13.0]: https://github.com/swetoast/battery_consumption/compare/2.12.0...2.13.0
[2.12.0]: https://github.com/swetoast/battery_consumption/compare/2.11.0...2.12.0
[2.11.0]: https://github.com/swetoast/battery_consumption/compare/2.10.5...2.11.0
[2.10.5]: https://github.com/swetoast/battery_consumption/compare/2.10.4...2.10.5
[2.10.4]: https://github.com/swetoast/battery_consumption/compare/2.10.3...2.10.4
[2.10.3]: https://github.com/swetoast/battery_consumption/compare/2.10.2...2.10.3
