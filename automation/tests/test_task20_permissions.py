from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LIB = REPO_ROOT / "real_eval/scripts/lib_real_eval.sh"
PREPARE_RELAY = REPO_ROOT / "real_eval/scripts/prepare_tdc_admet_tox_gpt_relay.py"


def mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


def test_source_provider_config_is_owner_only() -> None:
    provider = REPO_ROOT / "api/codex_gpt54_shubiaobiao.toml"
    assert mode(provider) == 0o600


def test_workspace_credential_copy_gate_rejects_only_credential_named_files(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(mode=0o700)
    (workspace / "safe.txt").write_text("fixture\n", encoding="utf-8")
    subprocess.run(
        ["bash", "-c", f"source {LIB!s}; real_eval_assert_no_credential_copies {workspace!s}"],
        check=True,
    )

    (workspace / "provider.env").write_text("OPENAI_API_KEY=fixture\n", encoding="utf-8")
    result = subprocess.run(
        ["bash", "-c", f"source {LIB!s}; real_eval_assert_no_credential_copies {workspace!s}"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "fixture" not in result.stderr


def test_tdc_relay_fixture_writes_secret_files_with_owner_only_modes(tmp_path: Path) -> None:
    provider = tmp_path / "provider.toml"
    provider.write_text(
        'model = "fixture-model"\n'
        'model_provider = "fixture"\n\n'
        '[model_providers.fixture]\n'
        'base_url = "https://fixture.invalid/v1"\n'
        'wire_api = "responses"\n'
        'experimental_bearer_token = "fixture-token"\n',
        encoding="utf-8",
    )
    upstream = tmp_path / "upstream_relay.env"
    client = tmp_path / "provider.env"
    config = tmp_path / "codex_home" / "config.toml"
    evidence = tmp_path / "evidence.json"
    subprocess.run(
        [
            "python3",
            str(PREPARE_RELAY),
            "--provider-config",
            str(provider),
            "--client-base-url",
            "http://fixture-relay:8787/v1",
            "--client-key",
            "fixture-client-key",
            "--upstream-env",
            str(upstream),
            "--client-env",
            str(client),
            "--codex-config",
            str(config),
            "--evidence",
            str(evidence),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert mode(upstream) == 0o600
    assert mode(client) == 0o600
    assert mode(config) == 0o600


def test_tdc_shell_paths_have_permission_hardening_and_bash_syntax() -> None:
    scripts = [
        REPO_ROOT / "real_eval/scripts/lib_real_eval.sh",
        REPO_ROOT / "real_eval/scripts/tdc_admet_tox_framework_smoke.sh",
        REPO_ROOT / "real_eval/scripts/tdc_admet_tox_framework_fullrun.sh",
    ]
    for script in scripts:
        subprocess.run(["bash", "-n", str(script)], check=True)
    for script in scripts[1:]:
        text = script.read_text(encoding="utf-8")
        assert 'chmod 700 "$CODEX_HOME_DIR"' in text
        assert 'chmod 600 "$CODEX_HOME_DIR/config.toml"' in text
        assert "real_eval_assert_no_credential_copies \"$WORKSPACE\"" in text
