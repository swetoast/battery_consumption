"""Tests for the standalone profile contribution validator."""

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "validate_device_profiles.py"
SPEC = importlib.util.spec_from_file_location("profile_validator", SCRIPT)
VALIDATOR = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(VALIDATOR)


def _write(tmp_path: Path, devices: list[dict]) -> Path:
    path = tmp_path / "profiles.json"
    path.write_text(json.dumps({"schema_version": 1, "devices": devices}))
    return path


def _profile(profile_id: str, model: str) -> dict:
    return {
        "id": profile_id,
        "manufacturer": "Example",
        "model": model,
        "capacity": 20,
        "capacity_unit": "Wh",
        "source": "https://example.com/evidence",
        "notes": "Verified 20 Wh capacity",
    }


def test_validator_accepts_complete_profile(tmp_path: Path) -> None:
    assert VALIDATOR.validate(_write(tmp_path, [_profile("example", "Device")])) == []


def test_validator_rejects_ambiguous_alias(tmp_path: Path) -> None:
    first = _profile("first", "Device A")
    first["model_aliases"] = ["Shared"]
    second = _profile("second", "Device B")
    second["model_aliases"] = ["Shared"]
    errors = VALIDATOR.validate(_write(tmp_path, [first, second]))
    assert any("conflicts" in error for error in errors)


def test_validator_requires_evidence(tmp_path: Path) -> None:
    profile = _profile("example", "Device")
    profile.pop("source")
    profile.pop("notes")
    errors = VALIDATOR.validate(_write(tmp_path, [profile]))
    assert any("source" in error for error in errors)
    assert any("notes" in error for error in errors)


def test_validator_requires_stable_sorting(tmp_path: Path) -> None:
    errors = VALIDATOR.validate(
        _write(tmp_path, [_profile("z", "Zed"), _profile("a", "Alpha")])
    )
    assert "devices must be sorted by manufacturer and model" in errors
