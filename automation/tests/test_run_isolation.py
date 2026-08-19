from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from run_isolation import (
    allocate_run_isolation,
    authoritative_host_path,
    authoritative_topic_runtime_mounts,
    ensure_authoritative_mount_targets,
    materialize_snapshot,
    prepare_attempt_runtime,
    render_project_command_for_run,
    repo_relative_path,
    snapshot_rsync_command,
    topic_scope_removals,
)
from topic_runtime import load_topic_config


def test_allocate_run_isolation_builds_unique_tmp_layout(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo-src"
    automation_dir = repo_root / "automation"
    (automation_dir / "state" / "projects").mkdir(parents=True)
    project = {"id": "04", "name": "AutoResearchClaw", "project_dir": str(repo_root / "AutoResearchClaw")}

    first = allocate_run_isolation(
        repo_root=repo_root,
        automation_dir=automation_dir,
        project=project,
        attempt=1,
        topic_label="GAVE2-Task2",
        base_tmp_root=tmp_path / "tmp-runs",
    )
    second = allocate_run_isolation(
        repo_root=repo_root,
        automation_dir=automation_dir,
        project=project,
        attempt=1,
        topic_label="GAVE2-Task2",
        base_tmp_root=tmp_path / "tmp-runs",
    )

    assert first.tmp_root != second.tmp_root
    assert first.repo_dir == first.tmp_root / "repo"
    assert first.codex_home_dir == first.tmp_root / "codex-home"
    assert first.state_dir == first.tmp_root / "state"
    assert first.authoritative_state_dir == automation_dir / "state"


def test_materialize_snapshot_excludes_runtime_residue_and_records_manifest(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo-src"
    (repo_root / "automation" / "state" / "projects").mkdir(parents=True)
    (repo_root / "automation" / "runs" / "04" / "attempt-001").mkdir(parents=True)
    (repo_root / "automation" / "todo_runtime.md").write_text("todo\n", encoding="utf-8")
    (repo_root / "automation" / "projects.yaml").write_text("{}\n", encoding="utf-8")
    (repo_root / "automation" / "runtime_topic.md").write_text("topic\n", encoding="utf-8")
    (repo_root / "AutoResearchClaw").mkdir(parents=True)
    (repo_root / "AutoResearchClaw" / "keep.txt").write_text("keep\n", encoding="utf-8")
    (repo_root / "automation" / "state" / "runtime_state.json").write_text("{}", encoding="utf-8")
    (repo_root / "automation" / "runs" / "04" / "attempt-001" / "old.log").write_text("old\n", encoding="utf-8")

    isolation = allocate_run_isolation(
        repo_root=repo_root,
        automation_dir=repo_root / "automation",
        project={"id": "04", "name": "AutoResearchClaw", "project_dir": str(repo_root / "AutoResearchClaw")},
        attempt=1,
        topic_label="GAVE2-Task2",
        base_tmp_root=tmp_path / "tmp-runs",
    )
    manifest = materialize_snapshot(isolation)

    assert (isolation.repo_dir / "AutoResearchClaw" / "keep.txt").exists()
    assert not (isolation.repo_dir / "automation" / "runs").exists()
    assert not (isolation.repo_dir / "automation" / "projects.yaml").exists()
    assert not (isolation.repo_dir / "automation" / "todo_runtime.md").exists()
    assert not (isolation.repo_dir / "automation" / "runtime_topic.md").exists()
    assert manifest["project_id"] == "04"
    assert manifest["snapshot_repo"] == str(isolation.repo_dir)
    assert manifest["authoritative_state_dir"] == str(repo_root / "automation" / "state")


def test_render_project_command_for_run_rewrites_only_host_side_mounts(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo-src"
    automation_dir = repo_root / "automation"
    automation_dir.mkdir(parents=True)
    project_root = repo_root / "AutoResearchClaw"
    project_root.mkdir(parents=True)
    isolation = allocate_run_isolation(
        repo_root=repo_root,
        automation_dir=automation_dir,
        project={"id": "04", "name": "AutoResearchClaw", "project_dir": str(project_root)},
        attempt=1,
        topic_label="GAVE2-Task2",
        base_tmp_root=tmp_path / "tmp-runs",
    )
    command = (
        "docker run --rm "
        "-v __HOST_AUTOMATION_DIR__:/automation-control:ro "
        "-v __HOST_REPO_ROOT__:/repo:ro "
        "__HOST_TOPIC_RUNTIME_MOUNTS__ "
        "-v __HOST_PROJECT_ROOT__:/workspace/AutoResearchClaw "
        "--env-file __HOST_PROJECT_ENV_FILE__ "
        "-e RESEARCHCLAWEVAL_AUTOMATION_DIR=/automation-control "
        "-e HOME=__RUN_HOME__ -e CODEX_HOME=__RUN_CODEX_HOME__ "
        "image bash -lc 'python3 /repo/automation/scripts/run_framework_babylm_proxy.py'"
    )

    rendered = render_project_command_for_run(
        command,
        {"project_dir": str(project_root), "env_file": str(project_root / "project4.env")},
        isolation,
        {
            "__HOST_TOPIC_RUNTIME_MOUNTS__": (
                "-v /host/data:/repo/data/gave2/task2:ro "
                "-v /host/provider.toml:/repo/api/codex_gpt54_shubiaobiao.toml:ro"
            )
        },
    )

    assert f"-v {automation_dir}:/automation-control:ro" in rendered
    assert f"-v {isolation.repo_dir}:/repo:ro" in rendered
    assert "-v /host/data:/repo/data/gave2/task2:ro" in rendered
    assert f"-v {isolation.repo_dir / 'AutoResearchClaw'}:/workspace/AutoResearchClaw" in rendered
    assert f"--env-file {project_root / 'project4.env'}" in rendered
    assert f"-e HOME={isolation.home_dir}" in rendered
    assert f"-e CODEX_HOME={isolation.codex_home_dir}" in rendered
    assert "/repo/automation/scripts/run_framework_babylm_proxy.py" in rendered


def test_prepare_attempt_runtime_keeps_repo_attempt_dir_and_tmp_snapshot_separate(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo-src"
    automation_dir = repo_root / "automation"
    (automation_dir / "state" / "projects").mkdir(parents=True)
    (repo_root / "AutoResearchClaw").mkdir(parents=True)
    project = {"id": "04", "name": "AutoResearchClaw", "project_dir": str(repo_root / "AutoResearchClaw")}

    isolation, manifest = prepare_attempt_runtime(
        repo_root=repo_root,
        automation_dir=automation_dir,
        project=project,
        attempt=3,
        topic_label="GAVE2-Task2",
        base_tmp_root=tmp_path / "tmp-runs",
        repo_attempt_dir=automation_dir / "runs" / "04" / "attempt-003",
    )

    assert isolation.tmp_root.parent.name == "04"
    assert isolation.tmp_root.parent.parent.name == "gave2-task2"
    assert (automation_dir / "runs" / "04" / "attempt-003" / "run_manifest.json").exists()
    assert manifest["repo_attempt_dir"] == str(automation_dir / "runs" / "04" / "attempt-003")


def test_second_attempt_does_not_see_first_attempt_sentinel(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo-src"
    automation_dir = repo_root / "automation"
    (automation_dir / "state" / "projects").mkdir(parents=True)
    (repo_root / "DeepScientist").mkdir(parents=True)
    project = {"id": "05", "name": "DeepScientist", "project_dir": str(repo_root / "DeepScientist")}

    first, _ = prepare_attempt_runtime(
        repo_root=repo_root,
        automation_dir=automation_dir,
        project=project,
        attempt=1,
        topic_label="GAVE2-Task2",
        base_tmp_root=tmp_path / "tmp-runs",
        repo_attempt_dir=automation_dir / "runs" / "05" / "attempt-001",
    )
    (first.repo_dir / "DeepScientist" / "sentinel.txt").write_text("leftover\n", encoding="utf-8")

    second, _ = prepare_attempt_runtime(
        repo_root=repo_root,
        automation_dir=automation_dir,
        project=project,
        attempt=2,
        topic_label="GAVE2-Task2",
        base_tmp_root=tmp_path / "tmp-runs",
        repo_attempt_dir=automation_dir / "runs" / "05" / "attempt-002",
    )

    assert not (second.repo_dir / "DeepScientist" / "sentinel.txt").exists()


def test_snapshot_rsync_command_drops_runtime_residue_and_group_preservation(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo-src"
    automation_dir = repo_root / "automation"
    project_root = repo_root / "AutoResearchClaw"
    project_root.mkdir(parents=True)
    isolation = allocate_run_isolation(
        repo_root=repo_root,
        automation_dir=automation_dir,
        project={"id": "04", "name": "AutoResearchClaw", "project_dir": str(project_root)},
        attempt=1,
        topic_label="GAVE2-Task2",
        base_tmp_root=tmp_path / "tmp-runs",
    )

    command = snapshot_rsync_command(isolation)

    assert "--no-owner" in command
    assert "--no-group" in command
    assert "real_eval/runs" in command
    assert "automation/state" in command


def test_repo_relative_path_maps_canonical_repo_prefix_to_current_repo_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "researchclaweval"
    host_path = Path("/legacy/researchclaweval/AutoResearchClaw/project4.env")

    relative = repo_relative_path(host_path, repo_root)

    assert relative == Path("AutoResearchClaw/project4.env")


def test_repo_relative_path_maps_canonical_repo_prefix_from_worktree_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "researchclaweval" / ".worktrees" / "strict-run-isolation"
    host_path = Path("/legacy/researchclaweval/AutoResearchClaw/project4.env")

    relative = repo_relative_path(host_path, repo_root)

    assert relative == Path("AutoResearchClaw/project4.env")


def test_authoritative_host_path_falls_back_to_parent_repo_for_worktree(tmp_path: Path) -> None:
    repo_root = tmp_path / "researchclaweval" / ".worktrees" / "strict-run-isolation"
    parent_repo = tmp_path / "researchclaweval"
    env_file = parent_repo / "AutoResearchClaw" / "project4.env"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text("env\n", encoding="utf-8")

    resolved = authoritative_host_path("/legacy/researchclaweval/AutoResearchClaw/project4.env", repo_root)

    assert resolved == env_file


def test_topic_scope_removals_excludes_other_topic_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo-src"
    automation_dir = repo_root / "automation"
    registry_dir = repo_root / "real_eval" / "registry"
    registry_dir.mkdir(parents=True)
    (registry_dir / "topics.json").write_text(
        json.dumps(
            {
                "topics": [
                    {
                        "id": "gave2_task2",
                        "label": "GAVE2-Task2",
                        "contract_file": "automation/gave2_task2_contract.md",
                        "dataset_root": "data/gave2/task2",
                        "summary_files": ["docs/gave2_task2_summary.md"],
                    },
                    {
                        "id": "arc_wbe_2026",
                        "label": "ARC-WBE-2026",
                        "contract_file": "automation/arc_white_box_estimation_2026_contract.md",
                        "dataset_root": "data/arc_white_box_estimation_2026",
                        "summary_files": ["docs/arc_wbe_2026_summary.md"],
                    },
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (repo_root / "automation").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs").mkdir(parents=True, exist_ok=True)
    (repo_root / "data" / "gave2" / "task2").mkdir(parents=True)
    (repo_root / "data" / "arc_white_box_estimation_2026").mkdir(parents=True)
    (repo_root / "AI-Scientist-v2" / "ai_scientist" / "ideas").mkdir(parents=True)
    (repo_root / "automation" / "gave2_task2_contract.md").write_text("gave2\n", encoding="utf-8")
    (repo_root / "automation" / "arc_white_box_estimation_2026_contract.md").write_text("arc\n", encoding="utf-8")
    (repo_root / "docs" / "gave2_task2_summary.md").write_text("gave2\n", encoding="utf-8")
    (repo_root / "docs" / "arc_wbe_2026_summary.md").write_text("arc\n", encoding="utf-8")
    (repo_root / "automation" / "arc_wbe_2026_manifest.json").write_text(
        json.dumps({"files": ["AI-Scientist-v2/ai_scientist/ideas/arc_wbe_2026_topic.md"]}) + "\n",
        encoding="utf-8",
    )
    (repo_root / "AI-Scientist-v2" / "ai_scientist" / "ideas" / "arc_wbe_2026_topic.md").write_text(
        "arc\n",
        encoding="utf-8",
    )
    (repo_root / "AutoResearchClaw").mkdir()
    project = {"id": "04", "name": "AutoResearchClaw", "project_dir": str(repo_root / "AutoResearchClaw")}

    isolation = allocate_run_isolation(
        repo_root=repo_root,
        automation_dir=automation_dir,
        project=project,
        attempt=1,
        topic_label="GAVE2-Task2",
        base_tmp_root=tmp_path / "tmp-runs",
        topic_contract_file=repo_root / "automation" / "gave2_task2_contract.md",
    )
    for path in (
        isolation.repo_dir / "automation",
        isolation.repo_dir / "docs",
        isolation.repo_dir / "data" / "arc_white_box_estimation_2026",
        isolation.repo_dir / "AI-Scientist-v2" / "ai_scientist" / "ideas",
    ):
        path.mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo_root / "automation" / "arc_white_box_estimation_2026_contract.md", isolation.repo_dir / "automation" / "arc_white_box_estimation_2026_contract.md")
    shutil.copy2(repo_root / "docs" / "arc_wbe_2026_summary.md", isolation.repo_dir / "docs" / "arc_wbe_2026_summary.md")
    shutil.copy2(repo_root / "automation" / "arc_wbe_2026_manifest.json", isolation.repo_dir / "automation" / "arc_wbe_2026_manifest.json")
    shutil.copy2(
        repo_root / "AI-Scientist-v2" / "ai_scientist" / "ideas" / "arc_wbe_2026_topic.md",
        isolation.repo_dir / "AI-Scientist-v2" / "ai_scientist" / "ideas" / "arc_wbe_2026_topic.md",
    )

    removals = topic_scope_removals(isolation)

    assert isolation.repo_dir / "automation" / "arc_white_box_estimation_2026_contract.md" in removals
    assert isolation.repo_dir / "docs" / "arc_wbe_2026_summary.md" in removals
    assert isolation.repo_dir / "automation" / "arc_wbe_2026_manifest.json" in removals
    assert isolation.repo_dir / "AI-Scientist-v2" / "ai_scientist" / "ideas" / "arc_wbe_2026_topic.md" in removals


def test_git_export_snapshot_uses_current_worktree_and_excludes_authoritative_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo-src"
    automation_dir = repo_root / "automation"
    subprocess.run(["git", "init", str(repo_root)], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "user.name", "Codex"], check=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "user.email", "codex@example.com"], check=True)

    (automation_dir / "state" / "projects").mkdir(parents=True, exist_ok=True)
    (repo_root / "dr-claw").mkdir(parents=True, exist_ok=True)
    (repo_root / "tracked.txt").write_text("tracked-before\n", encoding="utf-8")
    (automation_dir / "projects.yaml").write_text("projects: []\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo_root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo_root), "commit", "-m", "init"], check=True, capture_output=True, text=True)

    (repo_root / "tracked.txt").write_text("tracked-after\n", encoding="utf-8")
    harness = repo_root / "babylm_10m_harness" / "scripts" / "run_proxy_babylm_pipeline.py"
    harness.parent.mkdir(parents=True, exist_ok=True)
    harness.write_text("print('ok')\n", encoding="utf-8")
    (automation_dir / "todo_runtime.md").write_text("todo\n", encoding="utf-8")

    isolation = allocate_run_isolation(
        repo_root=repo_root,
        automation_dir=automation_dir,
        project={"id": "06", "name": "dr-claw", "project_dir": str(repo_root / "dr-claw")},
        attempt=1,
        topic_label="GAVE2-Task2",
        base_tmp_root=tmp_path / "tmp-runs",
    )
    materialize_snapshot(isolation)

    assert (isolation.repo_dir / "tracked.txt").read_text(encoding="utf-8") == "tracked-after\n"
    assert (isolation.repo_dir / "babylm_10m_harness" / "scripts" / "run_proxy_babylm_pipeline.py").exists()
    assert not (isolation.repo_dir / "automation" / "projects.yaml").exists()
    assert not (isolation.repo_dir / "automation" / "todo_runtime.md").exists()


def test_authoritative_topic_runtime_mounts_resolve_host_inputs(tmp_path: Path) -> None:
    repo_root = tmp_path / "researchclaweval" / ".worktrees" / "strict-run-isolation"
    parent_repo = tmp_path / "researchclaweval"
    (parent_repo / "data" / "gave2" / "task2").mkdir(parents=True)
    (parent_repo / "api").mkdir(parents=True)
    (parent_repo / "data" / "gave2" / "task2" / "sample.train.txt").write_text("data\n", encoding="utf-8")
    (parent_repo / "api" / "codex_gpt54_shubiaobiao.toml").write_text("model = 'gpt-5.4'\n", encoding="utf-8")
    (parent_repo / "api" / "_semantic_scholar_api_usage.md").write_text("semantic\n", encoding="utf-8")

    topic = type(
        "Topic",
        (),
        {
            "dataset_root": Path("/legacy/researchclaweval/data/gave2/task2"),
        },
    )()

    rendered = authoritative_topic_runtime_mounts(repo_root, topic)

    assert f"-v {parent_repo / 'data' / 'gave2' / 'task2'}:{repo_root / 'data' / 'gave2' / 'task2'}:ro" in rendered
    assert f"-v {parent_repo / 'api' / 'codex_gpt54_shubiaobiao.toml'}:{repo_root / 'api' / 'codex_gpt54_shubiaobiao.toml'}:ro" in rendered
    assert f"-v {parent_repo / 'api' / '_semantic_scholar_api_usage.md'}:{repo_root / 'api' / '_semantic_scholar_api_usage.md'}:ro" in rendered


def test_authoritative_host_path_honors_framework_specific_override(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "researchclaweval"
    framework_root = tmp_path / "frameworks" / "AutoResearchClaw"
    framework_root.mkdir(parents=True)
    monkeypatch.setenv("RESEARCHCLAWEVAL_AUTORESEARCHCLAW_ROOT", str(framework_root))

    resolved = authoritative_host_path(
        "/data/jianbiao/AutoResearchClaw/project4.env",
        repo_root,
    )

    assert resolved == framework_root / "project4.env"


def test_load_topic_config_canonicalizes_worktree_absolute_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "researchclaweval" / ".worktrees" / "strict-run-isolation"
    automation_dir = repo_root / "automation"
    automation_dir.mkdir(parents=True, exist_ok=True)
    (automation_dir / "runtime_topic.md").write_text(
        "\n".join(
            [
                "# Runtime Topic Contract",
                "",
                "## Topic",
                "",
                "- Topic label: `GAVE2 Task 2`",
                f"- Dataset root: `{repo_root / 'data' / 'gave2' / 'task2'}`",
                f"- Contract file: `{repo_root / 'automation' / 'gave2_task2_contract.md'}`",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    topic = load_topic_config(repo_root, automation_dir)

    assert topic.dataset_root == repo_root / "data" / "gave2" / "task2"
    assert topic.contract_file == repo_root / "automation" / "gave2_task2_contract.md"


def test_ensure_authoritative_mount_targets_creates_snapshot_mountpoints(tmp_path: Path) -> None:
    repo_root = tmp_path / "researchclaweval"
    automation_dir = repo_root / "automation"
    (automation_dir / "state" / "projects").mkdir(parents=True, exist_ok=True)
    (repo_root / "dr-claw").mkdir(parents=True, exist_ok=True)
    isolation = allocate_run_isolation(
        repo_root=repo_root,
        automation_dir=automation_dir,
        project={"id": "06", "name": "dr-claw", "project_dir": str(repo_root / "dr-claw")},
        attempt=1,
        topic_label="GAVE2-Task2",
        base_tmp_root=tmp_path / "tmp-runs",
    )
    isolation.repo_dir.mkdir(parents=True, exist_ok=True)
    topic = type("Topic", (), {"dataset_root": repo_root / "data" / "gave2" / "task2"})()

    ensure_authoritative_mount_targets(isolation, topic)

    assert (isolation.repo_dir / "data" / "gave2" / "task2").is_dir()
    assert (isolation.repo_dir / "api" / "codex_gpt54_shubiaobiao.toml").exists()
    assert (isolation.repo_dir / "api" / "_semantic_scholar_api_usage.md").exists()
