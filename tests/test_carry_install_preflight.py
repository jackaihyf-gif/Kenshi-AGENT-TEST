"""Prevent recurrence of the real startup -31 installation regression."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

path = Path(__file__).parents[1] / "experiments/carry_phase/preflight_install.py"
spec = importlib.util.spec_from_file_location("carry_install_preflight", path)
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)

GATE = "ecccbfebb61a689a8cd870d68e0fe913513ea04a9c2926c59b37e46a37702e9a"
ORIGINAL = "37246540fc1c985f6b95041595688463acc82bca23d0b05e248e5e9ead711609"
CARRY_CANDIDATE = "9cf7ab197fe155b38fdb4d0e20d49527784d4cfc0fa9b79c97ba11f1a38b0589"


def test_previously_verified_original_pair_is_accepted():
    preflight.validate_hashes(ORIGINAL, GATE)


def test_real_carry_candidate_is_refused_with_the_deployed_gate():
    with pytest.raises(ValueError, match="native startup would reject"):
        preflight.validate_hashes(CARRY_CANDIDATE, GATE)


@pytest.mark.parametrize("asset", [ORIGINAL, CARRY_CANDIDATE])
def test_unknown_gate_never_accepts_an_asset_by_default(asset):
    with pytest.raises(ValueError, match="Unreviewed cache-gate"):
        preflight.validate_hashes(asset, "0" * 64)


def test_cli_rejection_keeps_both_inputs_unchanged(tmp_path):
    skeleton, gate = tmp_path / "synthetic.skeleton", tmp_path / "synthetic.dll"
    skeleton.write_bytes(b"synthetic skeleton; no game data")
    gate.write_bytes(b"synthetic gate; not a native library")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    result = subprocess.run(
        [sys.executable, str(path), "--candidate-skeleton", str(skeleton),
         "--cache-gate", str(gate)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert "Unreviewed cache-gate" in result.stderr
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before
