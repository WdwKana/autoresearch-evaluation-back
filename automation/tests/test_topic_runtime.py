from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from topic_runtime import (
    TopicConfig,
    _default_repo_root,
    default_topic_config,
    load_topic_config,
    render_topic_command,
)


def test_render_topic_command_replaces_generic_topic_placeholders() -> None:
    topic = TopicConfig(
        label="ARC-WBE-2026",
        dataset_root=Path("/tmp/arc-data"),
        contract_file=Path("/tmp/arc-contract.md"),
    )

    rendered = render_topic_command(
        "run --topic __TOPIC_LABEL__ --data __TOPIC_DATASET_ROOT__ --contract __TOPIC_CONTRACT_FILE__",
        topic,
    )

    assert rendered == "run --topic ARC-WBE-2026 --data /tmp/arc-data --contract /tmp/arc-contract.md"


def test_default_topic_config_is_topic_neutral(tmp_path: Path) -> None:
    cfg = default_topic_config(repo_root=tmp_path)

    assert cfg.label == "Default-Topic"
    assert cfg.dataset_root == tmp_path / "data" / "unset-topic"
    assert cfg.contract_file == tmp_path / "automation" / "runtime_topic.md"


def test_default_repo_root_uses_current_source_tree(monkeypatch) -> None:
    monkeypatch.delenv("RESEARCHCLAWEVAL_ROOT", raising=False)

    assert _default_repo_root() == Path(__file__).resolve().parents[2]


def test_default_topic_config_can_be_overridden_by_runtime_markdown(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime_topic.md"
    runtime.write_text(
        "# Runtime Topic Contract\n\n- Topic label: `ARC-WBE-2026`\n- Dataset root: `/tmp/arc-data`\n- Contract file: `/tmp/arc-contract.md`\n",
        encoding="utf-8",
    )

    cfg = load_topic_config(repo_root=tmp_path, automation_dir=tmp_path)

    assert cfg.label == "ARC-WBE-2026"
    assert cfg.dataset_root == Path("/tmp/arc-data")
    assert cfg.contract_file == Path("/tmp/arc-contract.md")


def test_load_topic_config_accepts_legacy_runtime_topic_format(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime_topic.md"
    runtime.write_text(
        "# Runtime Topic\n\n"
        "Current active topic: **ARC White-Box Estimation Challenge 2026**\n\n"
        "## Canonical references\n"
        "- `/tmp/arc-contract.md`\n"
        "- `/tmp/arc-summary.md`\n\n"
        "## Dataset root\n"
        "`/tmp/arc-data`\n",
        encoding="utf-8",
    )

    cfg = load_topic_config(repo_root=tmp_path, automation_dir=tmp_path)

    assert cfg.label == "ARC White-Box Estimation Challenge 2026"
    assert cfg.dataset_root == Path("/tmp/arc-data")
    assert cfg.contract_file == Path("/tmp/arc-contract.md")


def test_load_topic_config_maps_absolute_values_to_explicit_repo_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "researchclaweval"
    automation_dir = repo_root / "automation"
    automation_dir.mkdir(parents=True)
    runtime = automation_dir / "runtime_topic.md"
    runtime.write_text(
        "# Runtime Topic Contract\n\n"
        "- Topic label: `ARC-WBE-2026`\n"
        "- Dataset root: `/legacy/researchclaweval/data/arc`\n"
        "- Contract file: `/legacy/researchclaweval/automation/arc.md`\n",
        encoding="utf-8",
    )

    cfg = load_topic_config(repo_root=repo_root, automation_dir=automation_dir)

    assert cfg.dataset_root == repo_root / "data" / "arc"
    assert cfg.contract_file == repo_root / "automation" / "arc.md"


def test_load_topic_config_preserves_explicit_repo_root_through_symlink(tmp_path: Path) -> None:
    physical_root = tmp_path / "physical" / "researchclaweval"
    linked_root = tmp_path / "data" / "researchclaweval"
    automation_dir = physical_root / "automation"
    automation_dir.mkdir(parents=True)
    linked_root.parent.mkdir()
    linked_root.symlink_to(physical_root, target_is_directory=True)
    (automation_dir / "runtime_topic.md").write_text(
        "# Runtime Topic Contract\n\n"
        "- Topic label: `ARC-WBE-2026`\n"
        f"- Dataset root: `{physical_root / 'data' / 'arc'}`\n"
        f"- Contract file: `{physical_root / 'automation' / 'arc.md'}`\n",
        encoding="utf-8",
    )

    cfg = load_topic_config(repo_root=linked_root, automation_dir=linked_root / "automation")

    assert cfg.dataset_root == linked_root / "data" / "arc"
    assert cfg.contract_file == linked_root / "automation" / "arc.md"
