# Battery Consumption Roadmap

## Purpose

This roadmap defines how Battery Consumption will grow from the current 2.10.5 baseline while preserving the existing integration contract and original battery calculations.

The integration will continue to turn an existing battery-level entity, or one of its attributes, into meaningful battery usage, activity, power, energy, and cycle information. Future work will improve profile reliability, device matching, Companion App support, diagnostics, repairs, and configuration quality without replacing existing entities or changing their established behavior.

## Baseline guarantees

All roadmap work must preserve the following unless a separate breaking-change plan is explicitly approved:

- Existing config entries and unique IDs
- Existing entity IDs
- Battery level sensor
- Battery activity sensor
- Battery power sensor
- Equivalent full cycles sensor
- Existing state types and units
- Existing device classes and state classes
- Existing device grouping
- Original variation calculations
- Original charge and discharge calculations
- Original cumulative totals
- Original timestamps and elapsed-time behavior
- Original energy calculations
- Original estimated-power formula
- Existing restore behavior
- Existing statistics compatibility
- Immediate initialization from any valid current numeric source level
- User-defined profile overrides
- Optional Companion App inputs

New functionality must be capability-driven. Missing optional sensors must never make the main battery tracker unavailable.

## Design rules

1. The configured battery-level source remains authoritative for the original calculations, totals, timestamps, and restore behavior.
2. Companion App entities are optional supporting inputs only.
3. Supporting inputs may improve activity classification, measured power, telemetry, and context, but must not rewrite the original accounting model.
4. Each sensor must have one meaningful state and only the attributes needed to explain that state.
5. Internal validation details, matching scores, raw discovery evidence, and debug information must not be exposed as normal sensor attributes.
6. Existing entities must be extended carefully instead of replaced.
7. New entities must only be added when the value has a clear independent purpose that cannot be represented appropriately by an existing entity.
8. User-facing text must be natural, concise, and translatable.
9. Profile matching must suggest, not silently assume.
10. Every release must include the complete release ZIP and a standalone Python recovery script containing that exact ZIP as Base64.

## Phase 1: Profile catalog integrity (completed in 2.11.0)

### Goal

Make the bundled and user-defined profile catalogs impossible to ship in a state where valid-looking entries silently disappear from the Home Assistant selector.

### Work

- Add a formal JSON Schema for `device_profiles.json`.
- Add a catalog version alongside the existing schema version.
- Validate the complete bundled catalog against the JSON Schema.
- Load every bundled profile through the real runtime profile loader during tests.
- Fail tests if any bundled profile is rejected.
- Build the real selector options during tests.
- Fail tests if a loaded profile is missing from the selector.
- Verify that profile IDs are unique.
- Verify that selector labels are unique.
- Verify manufacturer and model sorting.
- Verify that capacity is numeric and greater than zero.
- Verify that the capacity unit is supported.
- Require a valid nominal voltage for every `mAh` profile.
- Verify that source references and profile notes use the expected data types.
- Add explicit regression coverage for the complete Roborock catalog and the S8 Pro Ultra profile.
- Verify that invalid user profiles are skipped without removing valid bundled profiles.
- Verify that a valid user profile can add a new entry.
- Verify that a valid user profile can intentionally override a bundled entry.
- Record whether a loaded profile came from the bundled catalog or the user catalog internally.

### Acceptance criteria

- No bundled profile is silently skipped.
- Every bundled profile appears in the selector.
- Invalid bundled data fails CI.
- Invalid user data cannot break bundled data.
- Catalog version and profile origin are available to diagnostics.

## Phase 2: Device-aware profile suggestions (completed in 2.12.0)

### Goal

Reduce manual profile searching while keeping the user in control of capacity selection.

### Work

- Resolve the Home Assistant device associated with the selected battery-level source entity.
- Read available device registry information:
  - Manufacturer
  - Model
  - Model ID
  - Hardware version
  - Owning integration
- Extend the profile format with optional matching metadata:
  - `model_aliases`
  - `model_ids`
  - `hardware_versions`
  - `match_priority`
- Normalize manufacturer and model strings consistently.
- Implement deterministic matching priority:
  1. Exact manufacturer and exact model
  2. Exact manufacturer and exact model ID
  3. Exact manufacturer and exact configured alias
  4. Exact manufacturer and normalized model
  5. No suggestion
- Reject ambiguous matches instead of choosing the first result.
- Display the suggested profile during setup and reconfiguration.
- Require explicit user approval before applying the profile.
- Keep manual profile selection available.
- Keep manual capacity configuration available.
- Store the accepted profile ID in the config entry as today.
- Remember rejected suggestions for the same Home Assistant device.
- Do not repeatedly offer a previously rejected match unless the device identity or catalog version changes.

### Acceptance criteria

- Exact known devices receive the correct suggestion.
- Ambiguous model families do not receive an automatic selection.
- Different battery-capacity variants remain separate.
- Existing config entries are not automatically changed.
- Rejected suggestions stay dismissed.

## Phase 3: Companion App expansion (completed in 2.13.0)

### Goal

Use available Home Assistant Companion App battery sensors more completely while keeping battery-level accounting unchanged.

### Supported optional inputs

The integration will support these optional entities per the same Home Assistant device:

- `is_charging`
- `battery_state`
- `charger_type`
- `battery_power`
- `battery_temperature`
- `battery_health`
- `battery_cycle_count`
- `remaining_charge_time`

None of these fields may be required.

### Device matching

- Resolve the Home Assistant device belonging to the configured battery-level source.
- Suggest Companion App entities only when they belong to that same device.
- Do not match entities solely by entity ID prefix.
- Allow manual selection when automatic suggestions are unavailable.
- Validate selected Companion entities during setup and reconfiguration.
- Warn through repairs when a selected supporting entity belongs to another device.
- Continue operating when any supporting entity becomes unavailable.

### Activity priority

The activity sensor will determine its state using this priority:

1. Valid `is_charging`
2. Valid `battery_state`
3. Original battery-level variation

Expected states remain:

- `charging`
- `discharging`
- `idle`

Companion activity evidence may improve classification but must not alter original charge, discharge, energy, total, timestamp, or restore calculations.

### Power priority

The battery power sensor will use:

1. Valid measured Companion `battery_power`
2. Original estimated power

The power sensor will continue to explain its value using only direct provenance attributes:

- `value_meaning`
- `source_type`
- `source_entity` when measured power is used

Measured power must never be copied into the original main sensor accounting as a replacement for the original estimated-power calculation.

### Activity telemetry

The activity sensor may own optional telemetry needed to explain current battery behavior:

- Charger type
- Battery temperature
- Battery health
- Remaining charge time
- Activity source type
- Activity source entity
- Session start
- Session starting level
- Session percentage change
- Session energy

Telemetry must not be repeated on the power or equivalent-cycle sensors.

### Temperature handling

- Battery temperature is telemetry only.
- Preserve the source unit when provided.
- Do not infer a unit when Home Assistant does not provide one.
- Do not use temperature to alter original accounting.
- Do not create temperature-derived charge or discharge corrections.

### Battery health handling

- Preserve meaningful source states.
- Normalize only known equivalent values.
- Keep unknown vendor-specific states intact where safe.
- Do not convert battery health into an invented percentage.
- Do not use battery health to alter capacity automatically.

### Hardware cycle handling

- Equivalent full cycles remain calculated from total discharge divided by 100.
- Hardware cycle count remains optional comparison context.
- Hardware cycle count must not replace equivalent full cycles.
- Invalid or unavailable cycle values are omitted.
- The cycle sensor will continue to explain its calculation and optional hardware comparison without unrelated telemetry.

### Remaining charge time

- Treat remaining charge time as optional charging context.
- Preserve its source unit when available.
- Omit invalid, negative, unknown, or unavailable values.
- Do not estimate remaining charge time from battery percentage unless a separate approved design and validation plan is created.

### Initialization

- New trackers and trackers without a usable restored level must initialize immediately from any valid current numeric battery level.
- The initial level is a baseline only.
- Initializing must not create charge, discharge, energy, power, or cycle totals.
- When the source begins as unknown or unavailable, the first later numeric state becomes the baseline.
- Source attributes must follow the same behavior as direct source states.

### Acceptance criteria

- Phones and watches with complete Companion telemetry use all relevant optional inputs.
- Devices with only a battery percentage continue working normally.
- Robot vacuums, sensors, headsets, and other non-Companion devices remain fully supported.
- The original battery-level accounting is byte-for-byte behaviorally compatible in regression tests.
- Optional input loss does not make the main tracker unavailable.

## Phase 4: Diagnostics (completed in 2.14.0)

### Goal

Make profile, source, and Companion configuration problems visible without overloading normal entities with debug attributes.

### Diagnostic content

Provide a standard Home Assistant diagnostics export containing sanitized information such as:

- Integration version
- Profile catalog schema version
- Profile catalog version
- Selected profile ID
- Profile origin
- Profile manufacturer and model
- Capacity
- Capacity unit
- Nominal voltage
- Source entity domain
- Configured source attribute
- Whether the source entity currently exists
- Whether the current source value is numeric
- Whether initialization used restore or the current source
- Configured optional Companion input types
- Availability of configured optional inputs
- Count of bundled profiles loaded
- Count of user profiles loaded
- Count of rejected profiles
- Validation error categories

### Privacy and scope

- Do not include unrelated Home Assistant states.
- Do not include complete device registries.
- Do not include profile source URLs unless needed for profile diagnostics.
- Do not expose diagnostics as normal sensor attributes.
- Do not expose internal matching scores as telemetry.

### Acceptance criteria

- A missing profile or bad source can be diagnosed from one export.
- Sensitive and unrelated data are excluded.
- Diagnostics remain useful even when the tracker is unavailable.

## Phase 5: Home Assistant Repairs (completed in 2.16.0)

### Goal

Turn actionable failures into clear Home Assistant repair issues instead of silent omissions or log-only warnings.

### Repair conditions

Create repair issues for:

- Configured source entity no longer exists
- Configured source attribute no longer exists
- Selected profile no longer exists
- User profile file contains invalid JSON
- User profile fails validation
- Bundled profile fails validation
- `mAh` profile lacks valid nominal voltage
- Configured Companion entity belongs to another Home Assistant device
- Source continues reporting nonnumeric values
- Configured optional entity was removed

### Repair behavior

- Repairs must explain the exact problem.
- Repairs must identify the affected config entry.
- Repairs should route the user to reconfigure when appropriate.
- Optional Companion entity failures must not mark the main tracker unavailable.
- Repairs must be removed automatically when the issue is resolved.
- Temporary source unavailability must not immediately create a repair.
- Repeated nonnumeric source states should use a reasonable persistence threshold before creating a repair.

### Acceptance criteria

- Every repair represents something the user can act on.
- Repairs do not spam during short outages.
- Resolved problems remove their repair issue.

## Phase 6: Configuration flow improvements (completed in 2.17.0)

### Goal

Make setup and reconfiguration clear, device-aware, and resistant to invalid combinations.

### Work

- Keep the existing source entity and source attribute selection.
- Show the detected Home Assistant device when available.
- Show an exact profile suggestion when available.
- Explain why no suggestion is available when matching is ambiguous.
- Group optional Companion inputs by purpose:
  - Activity
  - Power
  - Telemetry
  - Cycle context
- Clearly mark every supporting entity as optional.
- Prevent selecting the main battery-level source as an incompatible supporting input.
- Validate that supporting entities belong to the same device when device registry data are available.
- Keep manual capacity and voltage configuration.
- Preserve existing stable unique IDs during reconfiguration.
- Do not modify existing totals when a profile or optional source is changed.
- Make profile catalog version visible in the configuration flow description or diagnostics, not as an entity attribute.

### Acceptance criteria

- A newly added phone can be configured without manually guessing every matching Companion entity.
- A generic battery sensor can be configured without seeing irrelevant required fields.
- Reconfiguration does not replace entities or reset totals.

## Phase 7: User profile safety and tooling (completed in 2.18.0)

### Goal

Keep custom profiles flexible without allowing malformed overrides to break valid bundled profiles.

### Work

- Validate user profiles against the same schema as bundled profiles.
- Validate user profiles through the same runtime normalization.
- Keep the bundled profile when a user override with the same ID is invalid.
- Log accepted and rejected overrides clearly.
- Report override results in diagnostics.
- Create a repair for a rejected override.
- Document the user profile file format.
- Provide complete examples for `Wh` and `mAh` profiles.
- Add a local validation command or script for maintainers.
- Keep user profiles across integration upgrades.

### Acceptance criteria

- Invalid custom data cannot remove a valid bundled profile.
- Valid custom profiles appear in the selector after integration reload.
- Override origin and outcome are traceable through diagnostics.

## Phase 8: Profile contribution workflow (completed in 2.19.0)

### Goal

Make profile additions evidence-based, reviewable, and automatically validated.

### Required profile evidence

Every profile contribution must include:

- Manufacturer
- Exact model
- Capacity
- Capacity unit
- Nominal voltage when capacity is in `mAh`
- Reliable source reference
- Known Home Assistant manufacturer string
- Known Home Assistant model string
- Regional or hardware variation notes
- Whether the capacity applies to one model or a verified series
- Known aliases, model IDs, or hardware versions

### Automated checks

- JSON Schema validation
- Runtime-loader validation
- Selector generation
- Duplicate ID detection
- Duplicate label detection
- Ambiguous alias detection
- Sorting validation
- Unit and voltage validation
- Evidence field validation
- Regression checks for existing profiles

### Acceptance criteria

- A new profile cannot merge unless it appears in the actual selector.
- Series profiles are only allowed when every listed model is verified to use the same battery specification.
- Unverified variants remain separate or are omitted.

## Phase 9: Documentation (completed in 2.20.0)

### Goal

Document the integration as users experience it without exposing unnecessary implementation detail.

### Documentation updates

- Explain the authoritative battery-level source.
- Explain optional Companion inputs and their priority.
- Explain measured versus estimated power.
- Explain equivalent full cycles versus hardware cycle count.
- Explain profile suggestions and manual approval.
- Explain bundled and user profile origins.
- Explain diagnostics and repairs.
- Document immediate initial-state behavior.
- Document that initial state does not create usage totals.
- Document user profile examples.
- Document profile contribution requirements.
- Keep all user-facing documentation free of debug terminology and unnecessary internal detail.

## Phase 10: Stronger typing and typed runtime data (in progress)

### Goal

Describe configuration, profiles, Companion inputs, result values, diagnostics, repairs, and runtime state precisely enough that type checking catches invalid combinations before release. This phase is internal quality work only and must not change Home Assistant entities, stored keys, calculations, totals, timestamps, restore behavior, or YAML compatibility.

### Stage 1: Safe annotations and shared contracts (completed in 2.23.0)

- Add explicit `Literal` types for capacity units, power units, activity states, activity sources, power sources, and profile origins.
- Add typed storage-boundary dictionaries for config-entry and Companion values.
- Add cohesive typed models for Companion entities, effective tracker configuration, device profiles, power results, and profile load reports.
- Replace the unnamed power tuple with `BatteryPowerResult` while preserving the same state and attributes.
- Add focused tests proving the typed result contract and accepted literal values.
- Start incremental mypy enforcement in CI.

### Stage 2: Typed profile and configuration normalization

- Convert validated profile dictionaries into immutable `DeviceProfile` objects after JSON validation.
- Add one normalization function from `ConfigEntry.data` and `ConfigEntry.options` to `EffectiveTrackerConfig`.
- Keep Home Assistant storage dictionaries and every existing key unchanged.
- Prove profile selector, suggestions, diagnostics, repairs, and sensor setup consume the same effective values as before.

### Stage 3: Typed runtime data

- Add `BatteryConsumptionRuntimeData` and a typed config-entry alias.
- Load reusable profile and effective configuration data once during entry setup.
- Supply the typed runtime data to sensors, diagnostics, and repairs.
- Keep the legacy YAML path separate and behaviorally unchanged.

### Stage 4: Full type-checking enforcement

- Expand mypy from the shared contracts to all integration modules.
- Enable stricter checks incrementally, including untyped definitions, implicit optional values, unreachable code, and unnecessary ignores.
- Run the checker in the GitHub validation workflow.
- Require type checks, regression tests, profile validation, HACS validation, and Hassfest before release.

### Acceptance criteria

- Type checking passes in the Home Assistant 2025.12.2 test environment.
- No generic cast is used to pretend unvalidated JSON is a trusted profile.
- Existing entity IDs, unique IDs, stored configuration, attributes, states, units, totals, timestamps, and restore behavior remain unchanged.
- Original accounting methods remain structurally unchanged unless a separately approved bug fix requires otherwise.
- Companion inputs remain optional and never alter the authoritative battery-level accounting.

## Test matrix

Every release affecting these areas must cover:

### Battery source

- Direct numeric source at 0%
- Direct numeric source at 1%
- Direct numeric source at 42%
- Direct numeric source at 99%
- Direct numeric source at 100%
- Numeric source attribute
- Initial unknown state followed by numeric state
- Initial unavailable state followed by numeric state
- Nonnumeric source
- Removed source entity
- Removed source attribute

### Restore and accounting

- Valid restored state
- Unusable restored state with valid current source
- Existing charge total restoration
- Existing discharge total restoration
- No total created by initial baseline
- No session movement created by initial baseline
- Original power calculation unchanged
- Original timestamps unchanged

### Companion support

- Battery level only
- `is_charging` only
- `battery_state` only
- Both activity inputs
- Measured power available
- Measured power unavailable
- Temperature with unit
- Temperature without unit
- Battery health
- Hardware cycle count
- Remaining charge time
- Supporting entity from a different device
- Supporting entity removed after setup

### Profiles

- Complete bundled catalog
- Complete selector output
- Exact profile suggestion
- Alias suggestion
- Model ID suggestion
- Hardware version distinction
- Ambiguous match
- Rejected suggestion
- User profile addition
- Valid user override
- Invalid user override
- Catalog version update

### Device classes

- Phone
- Watch
- VR headset
- Robot vacuum
- Rechargeable generic device
- Replaceable-battery sensor
- Device without Companion App entities

## Release requirements

Before any release is described as complete:

- Review this roadmap and the current baseline guarantees.
- Run all available automated tests.
- Run catalog validation through the real runtime loader.
- Confirm selector output contains every valid profile.
- Inspect the final manifest version.
- Confirm existing entity IDs and unique IDs remain unchanged.
- Confirm original calculation methods remain unchanged unless the release explicitly targets them.
- Inspect the final ZIP contents.
- Exclude cache files and compiled files.
- Verify the recovery script recreates the exact ZIP.
- Report any unverified Home Assistant runtime behavior clearly.

## Explicitly out of scope

The following are not planned for Battery Consumption:

- Battery replacement inventory
- Battery replacement dates
- Battery replacement buttons
- Disposable battery quantity tracking
- Duplicate enhanced battery entities
- General low-battery notification automation
- Remote profile-library downloading without a separate approved design
- Automatic capacity degradation based on battery health
- Automatic profile application from weak or ambiguous matches
- Changing original totals based on Companion power
- Publishing internal matching or validation evidence as sensor attributes

## Definition of success

Battery Consumption will be considered successfully expanded when it can reliably support phones, watches, VR headsets, robot vacuums, rechargeable devices, and ordinary battery-powered sensors while maintaining one stable calculation contract.

Users should receive immediate valid battery levels, accurate original accounting, useful optional Companion context, reliable device profiles, clear diagnostics, and actionable repairs without duplicated entities, repeated attributes, silent profile failures, or unexpected migrations.
