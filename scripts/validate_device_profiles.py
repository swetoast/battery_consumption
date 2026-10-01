#!/usr/bin/env python3
"""Validate a Battery Consumption profile catalog with the runtime rules."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

SUPPORTED_UNITS = {"mAh", "Wh", "kWh", "MWh"}
ID_PATTERN = re.compile(r"^[a-z0-9_]+$")
URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
MATCH_SEPARATORS = " -_./()[]"


def normalize(value: str) -> str:
    """Normalize model matching metadata like the runtime matcher."""
    normalized = value.casefold().strip()
    for separator in MATCH_SEPARATORS:
        normalized = normalized.replace(separator, "")
    return normalized


def validate(path: Path) -> list[str]:
    errors = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as err:
        return [f"Cannot read valid JSON: {err}"]
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        return ["schema_version must be 1"]
    devices = data.get("devices")
    if not isinstance(devices, list):
        return ["devices must be a list"]
    seen = set()
    labels = set()
    exact_models = set()
    matching_values: dict[tuple[str, str], tuple[str, str]] = {}
    ordered_labels = []
    for index, profile in enumerate(devices):
        where = f"devices[{index}]"
        if not isinstance(profile, dict):
            errors.append(f"{where} must be an object")
            continue
        profile_id = profile.get("id")
        if not isinstance(profile_id, str) or not ID_PATTERN.fullmatch(profile_id):
            errors.append(f"{where}.id must contain lowercase letters, digits, or underscores")
        elif profile_id in seen:
            errors.append(f"{where}.id duplicates {profile_id}")
        else:
            seen.add(profile_id)
        manufacturer = profile.get("manufacturer")
        model = profile.get("model")
        if not isinstance(manufacturer, str) or not manufacturer.strip():
            errors.append(f"{where}.manufacturer is required")
        if not isinstance(model, str) or not model.strip():
            errors.append(f"{where}.model is required")
        if isinstance(manufacturer, str) and isinstance(model, str):
            label = f"{manufacturer.strip()} · {model.strip()}".casefold()
            if label in labels:
                errors.append(f"{where} duplicates selector label {manufacturer} · {model}")
            labels.add(label)
            ordered_labels.append((manufacturer.strip().casefold(), model.strip().casefold()))
            manufacturer_key = normalize(manufacturer)
            model_key = normalize(model)
            exact_models.add((manufacturer_key, model_key))
            for field in ("model_aliases", "model_ids"):
                values = profile.get(field, [])
                if not isinstance(values, list) or not all(
                    isinstance(value, str) and value.strip() for value in values
                ):
                    errors.append(f"{where}.{field} must be a list of non-empty strings")
                    continue
                if len(values) != len(set(values)):
                    errors.append(f"{where}.{field} contains duplicate values")
                for value in values:
                    key = (manufacturer_key, normalize(value))
                    previous = matching_values.get(key)
                    if previous and previous[0] != profile_id:
                        errors.append(
                            f"{where}.{field} value {value} conflicts with {previous[1]}"
                        )
                    else:
                        matching_values[key] = (str(profile_id), f"{where}.{field}")
            hardware = profile.get("hardware_versions", [])
            if not isinstance(hardware, list) or not all(
                isinstance(value, str) and value.strip() for value in hardware
            ):
                errors.append(f"{where}.hardware_versions must be a list of non-empty strings")
            elif len(hardware) != len(set(hardware)):
                errors.append(f"{where}.hardware_versions contains duplicate values")
        source = profile.get("source")
        if not isinstance(source, str) or not URL_PATTERN.match(source):
            errors.append(f"{where}.source must be an http or https evidence URL")
        notes = profile.get("notes")
        if not isinstance(notes, str) or not notes.strip():
            errors.append(f"{where}.notes must describe the verified specification")
        try:
            capacity = float(profile.get("capacity"))
        except (TypeError, ValueError):
            capacity = 0
        if capacity <= 0:
            errors.append(f"{where}.capacity must be greater than zero")
        unit = profile.get("capacity_unit")
        if unit not in SUPPORTED_UNITS:
            errors.append(f"{where}.capacity_unit is unsupported")
        if unit == "mAh":
            try:
                voltage = float(profile.get("nominal_voltage"))
            except (TypeError, ValueError):
                voltage = 0
            if voltage <= 0:
                errors.append(f"{where}.nominal_voltage is required for mAh")
    if ordered_labels != sorted(ordered_labels):
        errors.append("devices must be sorted by manufacturer and model")
    for manufacturer_key, model_key in exact_models:
        conflict = matching_values.get((manufacturer_key, model_key))
        if conflict:
            errors.append(
                f"matching metadata in {conflict[1]} conflicts with an exact model"
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    errors = validate(args.path)
    if errors:
        print("Profile catalog validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Profile catalog is valid: {args.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
