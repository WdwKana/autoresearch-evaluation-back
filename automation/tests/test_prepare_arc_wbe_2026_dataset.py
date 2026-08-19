from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "automation" / "scripts"))

from prepare_arc_wbe_2026_dataset import (
    DATASET_ID,
    DATASET_REVISION,
    DEFAULT_HF_HOME,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_SPLITS,
    MANIFEST_NAME,
    baked_split_dir,
    build_materialization_manifest,
    materialize_split,
)


def test_prepare_script_defaults_match_topic_registry_contract() -> None:
    assert DATASET_ID == "aicrowd/arc-whestbench-public-2026"
    assert DATASET_REVISION == "v1-phase1"
    assert DEFAULT_OUTPUT_ROOT == ROOT / "data" / "arc_white_box_estimation_2026"
    assert DEFAULT_HF_HOME == ROOT / "data" / ".cache" / "arc_wbe_2026_hf"
    assert DEFAULT_SPLITS == ("mini",)


def test_build_materialization_manifest_records_split_dirs(tmp_path: Path) -> None:
    output_root = tmp_path / "arc"
    hf_home = tmp_path / "hf-cache"

    manifest = build_materialization_manifest(output_root=output_root, hf_home=hf_home, splits=("mini", "full"))

    assert manifest["dataset_id"] == DATASET_ID
    assert manifest["dataset_revision"] == DATASET_REVISION
    assert manifest["output_root"] == str(output_root)
    assert manifest["hf_home"] == str(hf_home)
    assert manifest["splits"]["mini"]["raw_path"] == str(output_root / "mini")
    assert manifest["splits"]["mini"]["baked_path"] == str(baked_split_dir(output_root, "mini"))
    assert manifest["splits"]["full"]["raw_path"] == str(output_root / "arc-whestbench-full")
    assert manifest["splits"]["full"]["baked_path"] == str(baked_split_dir(output_root, "full"))


def test_baked_split_dir_uses_split_specific_directory(tmp_path: Path) -> None:
    output_root = tmp_path / "arc"

    assert baked_split_dir(output_root, "mini") == output_root / "baked" / "mini"
    assert baked_split_dir(output_root, "full") == output_root / "baked" / "full"


def test_materialize_split_skips_import_when_raw_split_already_exists(tmp_path: Path) -> None:
    output_root = tmp_path / "arc"
    hf_home = tmp_path / "hf"
    existing = output_root / "arc-whestbench-full"
    existing.mkdir(parents=True)

    materialize_split(output_root=output_root, hf_home=hf_home, split="full")


def test_cli_supports_dry_run_manifest_generation(tmp_path: Path) -> None:
    script = ROOT / "automation" / "scripts" / "prepare_arc_wbe_2026_dataset.py"
    output_root = tmp_path / "arc"
    hf_home = tmp_path / "hf"

    proc = subprocess.run(
        [
            "python3",
            str(script),
            "--output-root",
            str(output_root),
            "--hf-home",
            str(hf_home),
            "--splits",
            "mini,full",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(proc.stdout)
    assert payload["output_root"] == str(output_root)
    assert payload["hf_home"] == str(hf_home)
    assert payload["splits"] == ["mini", "full"]
    manifest_path = output_root / "materialization_manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["splits"]["mini"]["raw_materialized"] is False
    assert manifest["splits"]["mini"]["baked_materialized"] is False
    assert manifest["splits"]["full"]["raw_materialized"] is False
    assert manifest["splits"]["full"]["baked_materialized"] is False


def test_cli_dry_run_can_request_baked_manifest_rows(tmp_path: Path) -> None:
    script = ROOT / "automation" / "scripts" / "prepare_arc_wbe_2026_dataset.py"
    output_root = tmp_path / "arc"
    hf_home = tmp_path / "hf"

    proc = subprocess.run(
        [
            "python3",
            str(script),
            "--output-root",
            str(output_root),
            "--hf-home",
            str(hf_home),
            "--splits",
            "mini",
            "--bake-splits",
            "mini",
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(proc.stdout)
    assert payload["manifest"] == str(output_root / MANIFEST_NAME)
    manifest = json.loads((output_root / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["splits"]["mini"]["requested_bake"] is True
