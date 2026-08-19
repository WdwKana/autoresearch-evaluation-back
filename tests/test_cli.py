from __future__ import annotations

import json
from pathlib import Path

from researchclaweval.cli import main


def test_registry_list_is_dynamic(capsys) -> None:
    assert main(["registry", "list", "--kind", "topics", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [row["id"] for row in payload["topics"]] == [
        "babylm",
        "gave2_task2",
        "arc_wbe_2026",
        "psydefdetect",
        "tdc_admet_tox",
    ]


def test_matrix_renders_current_topic_not_a_hardcoded_subset(capsys) -> None:
    assert (
        main(
            [
                "registry",
                "matrix",
                "--topic",
                "psydefdetect",
                "--mode",
                "fullrun",
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["rows"]) == 7
    assert {row["topic_id"] for row in payload["rows"]} == {"psydefdetect"}


def test_registry_export_rejects_an_unmapped_mode(capsys) -> None:
    assert main(["registry", "export", "--topic", "tdc_admet_tox", "--mode", "fullrun"]) == 2
    assert "no run rows" in capsys.readouterr().err


def test_dry_run_writes_plan_without_launching_framework(tmp_path: Path, capsys) -> None:
    output = tmp_path / "plan"
    assert (
        main(
            [
                "dry-run",
                "--topic",
                "arc_wbe_2026",
                "--mode",
                "smoke",
                "--output-dir",
                str(output),
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "dry_run"
    assert payload["framework_count"] == 7
    assert (output / "dry_run.json").is_file()
    assert (output / "dry_run.md").is_file()


def test_validate_run_rejects_non_native_mapping(tmp_path: Path, capsys) -> None:
    assert (
        main(
            [
                "validate",
                "run",
                "--topic",
                "gave2_task2",
                "--framework",
                "03",
                "--mode",
                "fullrun",
                "--run-dir",
                str(tmp_path),
            ]
        )
        == 2
    )
    assert "unsupported_non_native" in capsys.readouterr().err

