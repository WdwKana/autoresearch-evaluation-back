#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass
class ValidationResult:
    status: str
    summary: str
    evidence: dict
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return self.status in {
            "finished",
            "finished_degraded",
            "unsupported_native_entrypoint",
            "blocked_benchmark_authorization",
        }


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except Exception:
        return str(path)


def glob_any(root: Path, patterns: Iterable[str]) -> list[Path]:
    hits: list[Path] = []
    for pattern in patterns:
        hits.extend(sorted(root.glob(pattern)))
    seen = set()
    uniq = []
    for path in hits:
        if path not in seen and path.exists():
            seen.add(path)
            uniq.append(path)
    return uniq


def pick_latest(paths: Iterable[Path]) -> Path | None:
    paths = [p for p in paths if p.exists()]
    if not paths:
        return None
    return max(paths, key=lambda p: p.stat().st_mtime)


def file_contains(path: Path, needles: Iterable[str]) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    return all(needle in text for needle in needles)


GAVE2_METRIC_KEYS = ("vessel_dice", "av_macro_f1", "official_composite_score")


def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def metric_triplet(data: object) -> dict | None:
    if not isinstance(data, dict):
        return None
    if not all(is_number(data.get(key)) for key in GAVE2_METRIC_KEYS):
        return None
    return {key: float(data[key]) for key in GAVE2_METRIC_KEYS}


def find_gave2_models(data: object) -> dict[str, dict]:
    models: dict[str, dict] = {}

    if isinstance(data, dict):
        direct_metrics = metric_triplet(data.get("best_val")) or metric_triplet(data)
        if direct_metrics is not None and isinstance(data.get("name"), str):
            models[data["name"]] = direct_metrics
            return models

        captured_model_ids: set[int] = set()
        for fallback_name, value in data.items():
            if not isinstance(value, dict):
                continue
            metrics = metric_triplet(value.get("best_val"))
            if metrics is None and isinstance(value.get("name"), str):
                metrics = metric_triplet(value)
            if metrics is None:
                continue
            model_name = (
                value.get("name") if isinstance(value.get("name"), str) else str(fallback_name)
            )
            models[model_name] = metrics
            captured_model_ids.add(id(value))

        for value in data.values():
            if id(value) in captured_model_ids:
                continue
            if isinstance(value, (dict, list)):
                for name, metrics in find_gave2_models(value).items():
                    models.setdefault(name, metrics)
    elif isinstance(data, list):
        for idx, value in enumerate(data):
            if not isinstance(value, (dict, list)):
                continue
            for name, metrics in find_gave2_models(value).items():
                models.setdefault(name if name else f"model_{idx}", metrics)

    return models


def gave2_metric_json_candidates(root: Path) -> list[Path]:
    workspace = root / "workspace"
    if not workspace.exists():
        return []

    candidates: list[Path] = []
    skip_dirs = {
        ".git",
        ".nv",
        "__pycache__",
        ".pytest_cache",
        "node_modules",
        "site-packages",
        "dist-packages",
    }
    for dirpath, dirnames, filenames in os.walk(workspace, topdown=True, onerror=lambda _exc: None):
        dirnames[:] = [
            name for name in dirnames if name not in skip_dirs and not name.startswith(".")
        ]
        path = Path(dirpath)
        for filename in filenames:
            if not filename.endswith(".json"):
                continue
            lower = filename.lower()
            if not (
                lower.startswith("results")
                or lower.endswith("summary.json")
                or lower in {"metrics.json", "pipeline_summary.json"}
            ):
                continue
            candidates.append(path / filename)
    return sorted(candidates, key=lambda p: (p.stat().st_mtime, str(p)), reverse=True)


def extract_gave2_metrics(root: Path) -> dict | None:
    for path in gave2_metric_json_candidates(root):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        models = find_gave2_models(data)
        if not models:
            continue
        best_model = max(
            models,
            key=lambda name: models[name].get("official_composite_score", float("-inf")),
        )
        return {
            "source": rel(path, root),
            "best_model": best_model,
            "best_official_composite_score": models[best_model]["official_composite_score"],
            "models": models,
        }
    return None


def json_device_values(root: Path) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for path in root.rglob("*.json"):
        try:
            parts = path.relative_to(root).parts
        except Exception:
            parts = path.parts
        if any(part.startswith(".") for part in parts):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        stack = [data]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                for key, value in item.items():
                    if key.lower() == "device" and isinstance(value, str):
                        pairs.append((rel(path, root), value.lower()))
                    elif isinstance(value, (dict, list)):
                        stack.append(value)
            elif isinstance(item, list):
                stack.extend(v for v in item if isinstance(v, (dict, list)))
    return pairs


def has_cuda_evidence(root: Path) -> tuple[bool, list[tuple[str, str]]]:
    pairs = json_device_values(root)
    if any(value.startswith("cuda") for _, value in pairs):
        return True, pairs
    txt_hits = []
    for name in [
        "artifacts/logs/ngc_preflight.txt",
        "artifacts/logs/env_check.txt",
        "artifacts/logs/completed.txt",
        "logs/e2e.log",
    ]:
        p = root / name
        if p.exists():
            txt_hits.append(p)
    for path in txt_hits:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").lower()
        except Exception:
            continue
        if "device=cuda" in text or "device: cuda" in text or "cuda_available: true" in text:
            return True, pairs
    return False, pairs


def first_rel(paths: list[Path], root: Path) -> str | None:
    return rel(paths[0], root) if paths else None


def validate_ai_researcher_resume(root: Path) -> ValidationResult:
    paper_dir = root / "repo/research_agent/babylm/target_sections/babylm_10m"
    eval_json = glob_any(root, ["repo/**/pace_eval.json", "repo/**/*eval*.json"])
    report_md = glob_any(
        root, ["repo/**/main.md", "repo/**/final_report.md", "repo/**/*report*.md"]
    )
    evidence = {
        "paper_dir": rel(paper_dir, root) if paper_dir.exists() else None,
        "eval_json": first_rel(eval_json, root),
        "report": first_rel(report_md, root),
    }
    ok = paper_dir.exists() and bool(eval_json)
    if ok:
        return ValidationResult(
            "finished",
            "AI-Researcher resume produced paper sections and evaluation JSON.",
            evidence,
            [],
        )
    return ValidationResult(
        "failed_no_artifacts", "AI-Researcher resume evidence is incomplete.", evidence, []
    )


def validate_ai_researcher_real(root: Path) -> ValidationResult:
    result = validate_ai_researcher_resume(root)
    return ValidationResult(
        result.status,
        result.summary.replace("resume", "real"),
        result.evidence,
        result.warnings,
    )


def validate_ai_scientist_v2(root: Path) -> ValidationResult:
    repo = root / "repo"
    idea = repo / "ai_scientist/ideas/babylm_10m_strict_small_topic.json"
    exps = sorted([p for p in (repo / "experiments").glob("*_attempt_*") if p.is_dir()])
    exp = pick_latest(exps)
    summaries = []
    pdfs = []
    figures = []
    review_text = None
    review_json = None
    if exp is not None:
        summaries = glob_any(
            exp,
            [
                "logs/0-run/baseline_summary.json",
                "logs/0-run/ablation_summary.json",
                "logs/0-run/research_summary.json",
                "logs/0-run/draft_summary.json",
            ],
        )
        pdfs = glob_any(exp, ["*.pdf"])
        figures = glob_any(exp, ["figures/*.png", "figures/*.jpg"])
        rt = exp / "review_text.txt"
        rj = exp / "review_img_cap_ref.json"
        review_text = rt if rt.exists() else None
        review_json = rj if rj.exists() else None
    evidence = {
        "idea_json": rel(idea, root) if idea.exists() else None,
        "experiment_dir": rel(exp, root) if exp else None,
        "summary_files": [rel(p, root) for p in summaries],
        "pdf": first_rel(pdfs, root),
        "figure_count": len(figures),
        "review_text": rel(review_text, root) if review_text else None,
        "review_json": rel(review_json, root) if review_json else None,
    }
    if idea.exists() and exp and len(summaries) >= 2 and (pdfs or review_text):
        return ValidationResult(
            "finished",
            "AI-Scientist-v2 ideation, BFTS, and writeup/review artifacts are present.",
            evidence,
            [],
        )
    if idea.exists() and exp and len(summaries) >= 2:
        return ValidationResult(
            "finished_degraded",
            "AI-Scientist-v2 completed ideation and experiment summaries, but writeup/review artifacts are incomplete.",
            evidence,
            [],
        )
    return ValidationResult(
        "failed_no_artifacts",
        "AI-Scientist-v2 did not leave the expected idea and experiment evidence.",
        evidence,
        [],
    )


def validate_aris(root: Path) -> ValidationResult:
    final_report = glob_any(root, ["workspace/babylm_10m_harness/reports/final_report.md"])
    checkpoints = glob_any(
        root,
        [
            "workspace/babylm_10m_harness/outputs/models/**/*.safetensors",
            "workspace/babylm_10m_harness/outputs/models/**/*.bin",
        ],
    )
    eval_json = glob_any(root, ["workspace/**/*eval*.json"])
    evidence = {
        "final_report": first_rel(final_report, root),
        "checkpoint": first_rel(checkpoints, root),
        "eval_json": first_rel(eval_json, root),
    }
    if final_report and checkpoints and eval_json:
        return ValidationResult(
            "finished",
            "ARIS produced the harness report, model checkpoint, and evaluation JSON.",
            evidence,
            [],
        )
    return ValidationResult("failed_no_artifacts", "ARIS evidence is incomplete.", evidence, [])


def validate_autoresearchclaw_resume(root: Path) -> ValidationResult:
    artifact_dirs = sorted(
        [p for p in (root / "repo/artifacts").glob("babylm-real-*") if p.is_dir()]
    )
    artifact_dir = pick_latest(artifact_dirs)
    deliverables = artifact_dir / "deliverables" if artifact_dir else None
    topic_eval = artifact_dir / "stage-02/topic_evaluation.json" if artifact_dir else None
    checkpoints = (
        glob_any(artifact_dir, ["**/*.pt", "**/*.pth", "**/*.safetensors", "**/pytorch_model.bin"])
        if artifact_dir
        else []
    )
    evidence = {
        "artifact_dir": rel(artifact_dir, root) if artifact_dir else None,
        "deliverables": rel(deliverables, root) if deliverables and deliverables.exists() else None,
        "topic_evaluation": rel(topic_eval, root) if topic_eval and topic_eval.exists() else None,
        "checkpoint": first_rel(checkpoints, root),
    }
    if (
        artifact_dir
        and deliverables
        and deliverables.exists()
        and topic_eval
        and topic_eval.exists()
    ):
        status = "finished" if checkpoints else "finished_degraded"
        summary = "AutoResearchClaw packaged deliverables and evaluation artifacts."
        if status == "finished_degraded":
            summary = "AutoResearchClaw packaged deliverables and evaluation artifacts, but no checkpoint file was found under the artifact bundle."
        return ValidationResult(status, summary, evidence, [])
    return ValidationResult(
        "failed_no_artifacts", "AutoResearchClaw resume artifacts are incomplete.", evidence, []
    )


def validate_deepscientist(root: Path) -> ValidationResult:
    report_md = glob_any(root, ["workspace/final_report.md"])
    checkpoints = glob_any(
        root,
        [
            "workspace/artifacts/checkpoints/**/*.pt",
            "workspace/artifacts/checkpoints/**/*.pth",
            "workspace/artifacts/checkpoints/**/*.safetensors",
        ],
    )
    eval_json = glob_any(
        root, ["workspace/artifacts/eval/*.json", "workspace/artifacts/eval/**/*.json"]
    )
    evidence = {
        "final_report": first_rel(report_md, root),
        "checkpoint": first_rel(checkpoints, root),
        "eval_json": first_rel(eval_json, root),
    }
    if report_md and checkpoints and eval_json:
        return ValidationResult(
            "finished",
            "DeepScientist produced checkpoints, eval JSON, and final report.",
            evidence,
            [],
        )
    return ValidationResult(
        "failed_no_artifacts", "DeepScientist evidence is incomplete.", evidence, []
    )


def validate_drclaw(root: Path) -> ValidationResult:
    checkpoints = glob_any(
        root,
        [
            "home/dr-claw/**/outputs/checkpoints/**/*.safetensors",
            "home/dr-claw/**/outputs/checkpoints/**/*.pt",
            "home/dr-claw/**/outputs/checkpoints/**/*.bin",
        ],
    )
    eval_json = glob_any(root, ["home/dr-claw/**/outputs/eval/*.json"])
    train_history = glob_any(root, ["home/dr-claw/**/outputs/logs/train_history.jsonl"])
    report_md = glob_any(root, ["home/dr-claw/**/*final_report*.md", "home/dr-claw/**/*report*.md"])
    evidence = {
        "checkpoint": first_rel(checkpoints, root),
        "eval_json": first_rel(eval_json, root),
        "train_history": first_rel(train_history, root),
        "report": first_rel(report_md, root),
    }
    if checkpoints and eval_json and train_history:
        status = "finished" if report_md else "finished_degraded"
        summary = "Dr. Claw produced real training checkpoints, eval JSON, and training history."
        if status == "finished_degraded":
            summary = "Dr. Claw produced real training checkpoints, eval JSON, and training history, but no final publication report was found."
        return ValidationResult(status, summary, evidence, [])
    return ValidationResult("failed_no_artifacts", "Dr. Claw evidence is incomplete.", evidence, [])


def validate_evoscientist(root: Path) -> ValidationResult:
    candidate_roots = []
    for sub in [
        root / "phase2/workspace",
        root / "workspace",
        root / "07_evoscientist_real_babylm_ngc_current_acceleratefix/workspace",
    ]:
        if sub.exists():
            candidate_roots.append(sub)
    candidate = candidate_roots[0] if candidate_roots else root
    report_md = glob_any(candidate, ["final_report.md"])
    checkpoints = glob_any(
        candidate,
        [
            "artifacts/checkpoints/**/*.safetensors",
            "artifacts/checkpoints/**/*.pt",
            "artifacts/checkpoints/**/*.bin",
        ],
    )
    eval_json = glob_any(
        candidate, ["artifacts/eval/*.json", "artifacts/eval/**/*.json", "artifacts/*eval*.json"]
    )
    model_stats = glob_any(candidate, ["artifacts/logs/model_stats.json"])
    cuda_ok, device_pairs = has_cuda_evidence(candidate)
    evidence = {
        "candidate_root": rel(candidate, root),
        "final_report": first_rel(report_md, root),
        "checkpoint": first_rel(checkpoints, root),
        "eval_json": first_rel(eval_json, root),
        "model_stats": first_rel(model_stats, root),
        "device_values": [{"path": p, "device": d} for p, d in device_pairs],
    }
    if report_md and checkpoints and eval_json and model_stats and cuda_ok:
        return ValidationResult(
            "finished",
            "EvoScientist produced CUDA-backed checkpoints, eval JSON, model stats, and final report.",
            evidence,
            [],
        )
    if report_md and checkpoints and eval_json and model_stats:
        return ValidationResult(
            "failed_no_artifacts",
            "EvoScientist produced files but CUDA device evidence is missing, so the run is invalid for this task.",
            evidence,
            [],
        )
    return ValidationResult(
        "failed_no_artifacts", "EvoScientist evidence is incomplete.", evidence, []
    )


def validate_gave2_input_pack(root: Path) -> ValidationResult:
    manifest_path = root / "native_pack_manifest.json"
    evidence = {
        "manifest": rel(manifest_path, root) if manifest_path.exists() else None,
        "copied_inputs": [],
        "framework": None,
    }
    if not manifest_path.exists():
        return ValidationResult(
            "failed_no_artifacts", "GAVE2 native input pack manifest is missing.", evidence, []
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        evidence["parse_error"] = str(exc)
        return ValidationResult(
            "failed_no_artifacts", "GAVE2 native input pack manifest is unreadable.", evidence, []
        )

    copied = manifest.get("copied_inputs", [])
    missing = [rel_path for rel_path in copied if not (root / rel_path).exists()]
    evidence["copied_inputs"] = copied
    evidence["framework"] = manifest.get("framework")
    evidence["dataset_root"] = manifest.get("dataset_root")
    evidence["contract_file"] = manifest.get("contract_file")
    if missing:
        evidence["missing_inputs"] = missing
        return ValidationResult(
            "failed_no_artifacts",
            "GAVE2 native input pack is missing copied input files.",
            evidence,
            [],
        )
    if not copied:
        return ValidationResult(
            "failed_no_artifacts",
            "GAVE2 native input pack did not record any copied inputs.",
            evidence,
            [],
        )
    return ValidationResult(
        "finished", "GAVE2 native input pack is prepared and validated.", evidence, []
    )


def validate_gave2_smoke(root: Path) -> ValidationResult:
    manifest_path = root / "smoke_manifest.json"
    log_path = root / "logs/smoke.log"
    evidence = {
        "manifest": rel(manifest_path, root) if manifest_path.exists() else None,
        "log": rel(log_path, root) if log_path.exists() else None,
        "checks": {},
    }
    if not manifest_path.exists():
        return ValidationResult(
            "failed_no_artifacts", "GAVE2 smoke manifest is missing.", evidence, []
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        evidence["parse_error"] = str(exc)
        return ValidationResult(
            "failed_no_artifacts", "GAVE2 smoke manifest is unreadable.", evidence, []
        )

    checks = manifest.get("checks", {})
    evidence["framework"] = manifest.get("framework")
    evidence["image"] = manifest.get("image")
    evidence["checks"] = checks
    if not checks:
        return ValidationResult(
            "failed_no_artifacts", "GAVE2 smoke manifest did not record checks.", evidence, []
        )
    if not manifest.get("all_passed"):
        return ValidationResult(
            "failed_no_artifacts", "GAVE2 smoke checks did not all pass.", evidence, []
        )
    if not log_path.exists():
        return ValidationResult("failed_no_artifacts", "GAVE2 smoke log is missing.", evidence, [])
    return ValidationResult("finished", "GAVE2 smoke checks passed.", evidence, [])


def validate_arc_wbe_2026_smoke(root: Path) -> ValidationResult:
    manifest_path = root / "smoke_manifest.json"
    log_path = root / "logs/smoke.log"
    evidence = {
        "manifest": rel(manifest_path, root) if manifest_path.exists() else None,
        "log": rel(log_path, root) if log_path.exists() else None,
        "topic_evidence": None,
        "checks": {},
    }

    if not manifest_path.exists():
        return ValidationResult(
            "failed_no_artifacts", "ARC smoke manifest is missing.", evidence, []
        )
    if not log_path.exists():
        return ValidationResult("failed_no_artifacts", "ARC smoke log is missing.", evidence, [])

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        evidence["parse_error"] = str(exc)
        return ValidationResult(
            "failed_no_artifacts", "ARC smoke manifest is unreadable.", evidence, []
        )

    evidence["checks"] = manifest.get("checks", {})
    evidence["framework"] = manifest.get("framework")
    evidence["dataset_root"] = manifest.get("dataset_root")
    evidence["contract_file"] = manifest.get("contract_file")
    evidence["manifest_topic_evidence"] = manifest.get("topic_evidence")
    if not evidence["checks"]:
        return ValidationResult(
            "failed_no_artifacts", "ARC smoke manifest did not record checks.", evidence, []
        )
    if not manifest.get("all_passed"):
        return ValidationResult(
            "failed_validation", "ARC smoke checks did not all pass.", evidence, []
        )

    topic_candidates = glob_any(
        root,
        [
            "repo/**/*ARC_WBE_2026*.md",
            "repo/**/*arc_wbe_2026*.json",
            "repo/**/topic.txt",
            "repo/**/config.arc.yaml",
            "workspace/**/*ARC_WBE_2026*.md",
            "workspace/**/*arc_wbe_2026*.json",
            "workspace/**/topic.txt",
            "workspace/**/config.arc.yaml",
            "inputs/**/*ARC_WBE_2026*.md",
            "inputs/**/*arc_wbe_2026*.json",
            "inputs/**/topic.txt",
            "inputs/**/config.arc.yaml",
        ],
    )

    accepted: list[Path] = []
    for path in topic_candidates:
        name = path.name.lower()
        if "arc_wbe_2026" in name:
            accepted.append(path)
            continue
        if name == "topic.txt" and file_contains(path, ["ARC-WBE-2026"]):
            accepted.append(path)
            continue
        if name == "config.arc.yaml" and file_contains(path, ["arc_wbe_2026", "ARC-WBE-2026"]):
            accepted.append(path)

    topic_evidence = pick_latest(accepted)
    if topic_evidence is None:
        return ValidationResult(
            "failed_validation",
            "ARC smoke did not leave topic-specific evidence.",
            evidence,
            ["missing_topic_evidence"],
        )

    evidence["topic_evidence"] = rel(topic_evidence, root)

    return ValidationResult("finished", "ARC smoke consumed the topic contract.", evidence, [])


def validate_gave2_fullrun(root: Path) -> ValidationResult:
    manifest_path = root / "fullrun_manifest.json"
    state_path = root / "state.json"
    log_path = root / "logs/e2e.log"
    evidence = {
        "manifest": rel(manifest_path, root) if manifest_path.exists() else None,
        "state": rel(state_path, root) if state_path.exists() else None,
        "log": rel(log_path, root) if log_path.exists() else None,
    }
    if not manifest_path.exists() or not state_path.exists() or not log_path.exists():
        return ValidationResult(
            "failed_no_artifacts",
            "GAVE2 full-run wrapper did not leave manifest/state/log evidence.",
            evidence,
            [],
        )
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as exc:
        evidence["parse_error"] = str(exc)
        return ValidationResult(
            "failed_no_artifacts", "GAVE2 full-run state is unreadable.", evidence, []
        )
    status = state.get("status", "unknown")
    evidence["status"] = status
    evidence["summary"] = state.get("summary")
    metrics = extract_gave2_metrics(root)
    if metrics is not None:
        evidence["gave2_metrics"] = metrics
    if status in {"finished", "finished_degraded"}:
        return ValidationResult(
            status, "GAVE2 full-run wrapper finished and left state/log evidence.", evidence, []
        )
    if status == "blocked":
        return ValidationResult(
            "failed_no_artifacts",
            f"GAVE2 full-run wrapper is blocked: {state.get('summary', 'unknown blocker')}",
            evidence,
            [],
        )
    return ValidationResult(
        "failed_no_artifacts",
        f"GAVE2 full-run wrapper did not finish successfully (status={status}).",
        evidence,
        [],
    )


def read_json(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def extract_arc_score(root: Path) -> tuple[Path | None, dict | None]:
    candidates = [
        root / "workspace/score.json",
        root / "artifacts/score.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        if not is_number(data.get("score")) or not isinstance(data.get("score_source"), str):
            continue
        return path, data
    return None, None


OFFICIAL_ARC_SCORE_SOURCES = {
    "official_adapter_whest_run",
}


def has_arc_native_execution_log_evidence(log_path: Path, manifest: dict | None = None) -> bool:
    try:
        text = log_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    if "arc_wbe_2026" not in text:
        return False
    if not isinstance(manifest, dict):
        return False
    if manifest.get("framework_orchestration") is not True:
        return False
    for key in ("native_entrypoint", "kimi_injection", "native_log_marker"):
        value = manifest.get(key)
        if not isinstance(value, str) or not value.strip():
            return False
    return manifest["native_log_marker"] in text and manifest["native_entrypoint"] in text


def arc_report_looks_on_topic(report_path: Path) -> bool:
    try:
        text = report_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    lower = text.lower()
    if "arc-wbe-2026" in lower or "arc_wbe_2026" in lower:
        if "babylm proxy report" in lower:
            return False
        return True
    if "babylm" in lower or "gave2" in lower or "retinal" in lower:
        return False
    return True


def validate_arc_wbe_2026_fullrun(root: Path) -> ValidationResult:
    manifest_path = root / "fullrun_manifest.json"
    state_path = root / "state.json"
    log_path = root / "logs/e2e.log"
    evidence = {
        "manifest": rel(manifest_path, root) if manifest_path.exists() else None,
        "state": rel(state_path, root) if state_path.exists() else None,
        "log": rel(log_path, root) if log_path.exists() else None,
        "final_report": None,
        "score": None,
        "score_source": None,
        "score_artifact": None,
        "official_comparable": None,
        "submission_artifact": None,
    }
    if not manifest_path.exists() or not state_path.exists() or not log_path.exists():
        return ValidationResult(
            "failed_no_artifacts",
            "ARC full-run wrapper did not leave manifest/state/log evidence.",
            evidence,
            [],
        )

    state = read_json(state_path)
    if not isinstance(state, dict):
        return ValidationResult(
            "failed_no_artifacts", "ARC full-run state is unreadable.", evidence, []
        )
    evidence["status"] = state.get("status", "unknown")
    evidence["summary"] = state.get("summary")
    fullrun_manifest = read_json(manifest_path)
    if not isinstance(fullrun_manifest, dict):
        return ValidationResult(
            "failed_no_artifacts", "ARC full-run manifest is unreadable.", evidence, []
        )
    evidence["native_entrypoint"] = fullrun_manifest.get("native_entrypoint")
    evidence["kimi_injection"] = fullrun_manifest.get("kimi_injection")

    if state.get("status") == "unsupported_native_entrypoint":
        reason = state.get(
            "summary", "Framework has no supported native noninteractive entrypoint."
        )
        return ValidationResult("unsupported_native_entrypoint", reason, evidence, [])
    final_report = pick_latest(
        [
            root / "workspace/final_report.md",
            root / "artifacts/final_report.md",
        ]
    )
    submission_artifact = pick_latest(
        [
            root / "workspace/submission.json",
            root / "artifacts/submission.json",
        ]
    )
    score_path, score_payload = extract_arc_score(root)

    if final_report is not None:
        evidence["final_report"] = rel(final_report, root)
    if submission_artifact is not None:
        evidence["submission_artifact"] = rel(submission_artifact, root)
    if score_path is not None and isinstance(score_payload, dict):
        evidence["score"] = float(score_payload["score"])
        evidence["score_source"] = score_payload["score_source"]
        evidence["score_artifact"] = rel(score_path, root)
        evidence["official_comparable"] = (
            score_payload["score_source"] in OFFICIAL_ARC_SCORE_SOURCES
        )
        if isinstance(score_payload.get("score_artifact"), str):
            evidence["score_artifact_source"] = score_payload["score_artifact"]

    submission_payload = read_json(submission_artifact) if submission_artifact is not None else None
    if isinstance(submission_payload, dict):
        evidence["submission_payload"] = submission_payload

    if final_report is not None and not arc_report_looks_on_topic(final_report):
        return ValidationResult(
            "failed_validation",
            "ARC full-run final report is polluted by another topic.",
            evidence,
            ["cross_topic_report_pollution"],
        )

    if state.get("status") == "blocked":
        return ValidationResult(
            "failed_validation",
            f"ARC full-run wrapper is blocked: {state.get('summary', 'unknown blocker')}",
            evidence,
            [],
        )

    if not has_arc_native_execution_log_evidence(log_path, fullrun_manifest):
        return ValidationResult(
            "failed_validation",
            "ARC full-run lacks declared framework-native entrypoint or Kimi-injection evidence.",
            evidence,
            ["missing_native_entrypoint_manifest_or_log"],
        )

    if (
        final_report is not None
        and submission_artifact is not None
        and score_path is not None
        and evidence.get("official_comparable")
    ):
        return ValidationResult(
            "finished",
            "ARC full-run produced official-comparable score evidence.",
            evidence,
            [],
        )
    if final_report is not None and submission_artifact is not None:
        native_execution = (
            isinstance(submission_payload, dict)
            and submission_payload.get("framework_native_execution") is True
        )
        consumed_topic_input = (
            isinstance(submission_payload, dict)
            and submission_payload.get("consumed_topic_input") is True
        )
        workspace_trace_root = (
            submission_payload.get("workspace_trace_root")
            if isinstance(submission_payload, dict)
            else None
        )
        log_has_native_entrypoint = has_arc_native_execution_log_evidence(
            log_path, fullrun_manifest
        )
        if (
            state.get("status") == "finished_degraded"
            and native_execution
            and consumed_topic_input
            and workspace_trace_root
            and log_has_native_entrypoint
        ):
            return ValidationResult(
                "finished_degraded",
                "ARC full-run completed framework-native execution without local official scoring.",
                evidence,
                [],
            )
        return ValidationResult(
            "failed_validation",
            "ARC full-run left a submission package, but native execution evidence is incomplete.",
            evidence,
            ["missing_native_execution_evidence"],
        )
    return ValidationResult(
        "failed_validation",
        "ARC full-run did not produce sufficient score or submission evidence.",
        evidence,
        ["missing_submission_or_score"],
    )


def psydefdetect_report_looks_on_topic(report_path: Path) -> bool:
    try:
        text = report_path.read_text(encoding="utf-8", errors="ignore").lower()
    except Exception:
        return False
    if "psydefdetect" in text or "psychological defense" in text or "defense mechanism" in text:
        severe_pollution = (
            "babylm proxy report",
            "gave2 task 2",
            "arc-wbe-2026 runtime contract",
            "arc_wbe_2026 runtime contract",
        )
        return not any(marker in text for marker in severe_pollution)
    return False


def has_psydefdetect_native_execution_log_evidence(
    log_path: Path, manifest: dict | None = None
) -> bool:
    try:
        text = log_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    if not isinstance(manifest, dict) or manifest.get("framework_orchestration") is not True:
        return False
    for key in ("native_entrypoint", "provider_injection", "native_log_marker", "executor_kind"):
        value = manifest.get(key)
        if not isinstance(value, str) or not value.strip():
            return False
    return manifest["native_log_marker"] in text and manifest["native_entrypoint"] in text


def psydefdetect_metric_candidates(root: Path) -> list[Path]:
    candidates = [
        root / "workspace/score.json",
        root / "workspace/score_metrics.json",
        root / "workspace/psydefdetect_metrics.json",
        root / "workspace/psydefdetect_scores.json",
        root / "workspace/metrics.json",
        root / "workspace/psydefdetect_run/metrics.json",
        root / "artifacts/score.json",
        root / "artifacts/score_metrics.json",
        root / "artifacts/psydefdetect_metrics.json",
        root / "artifacts/psydefdetect_scores.json",
        root / "artifacts/metrics.json",
    ]
    workspace = root / "workspace"
    if workspace.exists():
        candidates.extend(sorted(workspace.glob("psydefdetect*/metrics.json")))
        candidates.extend(sorted(workspace.glob("*/psydefdetect*/metrics.json")))
    return candidates


def extract_psydefdetect_score(root: Path) -> tuple[Path | None, dict | None]:
    score_keys = (
        ("psydefdetect_score",),
        ("score",),
        ("macro_f1_positive",),
        ("macro_f1_positive_1_8",),
        ("macro_f1_positive_labels_1_8",),
        ("official_macro_f1_positive_1_8",),
        ("official_positive_macro_f1_oof",),
        ("best_positive_macro_f1",),
        ("selected_scores", "official_macro_f1_positive_1_8"),
        ("test_metrics", "macro_f1_positive_1_8"),
        ("eval_metrics", "macro_f1_positive_1_8"),
        ("heldout_metrics", "macro_f1_positive_labels_1_8"),
        ("eval", "official_macro_f1_positive_1_8"),
    )
    for path in psydefdetect_metric_candidates(root):
        if not path.exists():
            continue
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        for key_path in score_keys:
            value = data
            for key in key_path:
                if not isinstance(value, dict) or key not in value:
                    value = None
                    break
                value = value[key]
            if is_number(value):
                return path, {
                    "psydefdetect_score": float(value),
                    "score_key": ".".join(key_path),
                }
    return None, None


def validate_psydefdetect_smoke(root: Path) -> ValidationResult:
    manifest_path = root / "smoke_manifest.json"
    log_path = root / "logs/smoke.log"
    evidence = {
        "manifest": rel(manifest_path, root) if manifest_path.exists() else None,
        "log": rel(log_path, root) if log_path.exists() else None,
        "checks": {},
    }
    if not manifest_path.exists():
        return ValidationResult(
            "failed_no_artifacts", "PsyDefDetect smoke manifest is missing.", evidence, []
        )
    if not log_path.exists():
        return ValidationResult(
            "failed_no_artifacts", "PsyDefDetect smoke log is missing.", evidence, []
        )
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict):
        return ValidationResult(
            "failed_no_artifacts", "PsyDefDetect smoke manifest is unreadable.", evidence, []
        )
    checks = manifest.get("checks", {})
    evidence["checks"] = checks
    evidence["framework"] = manifest.get("framework")
    evidence["dataset_root"] = manifest.get("dataset_root")
    evidence["contract_file"] = manifest.get("contract_file")
    if not checks:
        return ValidationResult(
            "failed_no_artifacts",
            "PsyDefDetect smoke manifest did not record checks.",
            evidence,
            [],
        )
    if not manifest.get("all_passed"):
        return ValidationResult(
            "failed_validation", "PsyDefDetect smoke checks did not all pass.", evidence, []
        )
    return ValidationResult("finished", "PsyDefDetect smoke checks passed.", evidence, [])


def validate_tdc_admet_tox_smoke(root: Path) -> ValidationResult:
    manifest_path = root / "smoke_manifest.json"
    state_path = root / "state.json"
    log_path = root / "logs/smoke.log"
    evidence = {
        "manifest": rel(manifest_path, root) if manifest_path.exists() else None,
        "state": rel(state_path, root) if state_path.exists() else None,
        "log": rel(log_path, root) if log_path.exists() else None,
        "checks": {},
    }
    if not manifest_path.exists() or not state_path.exists() or not log_path.exists():
        return ValidationResult(
            "failed_no_artifacts",
            "TDC-ADMET-Tox smoke manifest/state/log evidence is incomplete.",
            evidence,
            [],
        )
    manifest = read_json(manifest_path)
    state = read_json(state_path)
    if not isinstance(manifest, dict) or not isinstance(state, dict):
        return ValidationResult(
            "failed_no_artifacts", "TDC-ADMET-Tox smoke evidence is unreadable.", evidence, []
        )
    evidence["checks"] = manifest.get("checks", {})
    evidence["framework"] = manifest.get("framework")
    evidence["native_entrypoint"] = manifest.get("native_entrypoint")
    evidence["dataset_root"] = manifest.get("dataset_root")
    evidence["evidence_artifact"] = manifest.get("evidence_artifact")
    if manifest.get("topic_id") != "tdc_admet_tox":
        return ValidationResult(
            "failed_validation", "TDC-ADMET-Tox smoke manifest has the wrong topic.", evidence, []
        )
    if state.get("status") != "finished" or not manifest.get("all_passed"):
        return ValidationResult(
            "failed_validation", "TDC-ADMET-Tox smoke checks did not all pass.", evidence, []
        )
    required_checks = {
        "codex_exit_zero",
        "native_entrypoint_present",
        "public_file_set_exact",
        "labeled_schema",
        "test_schema_unlabeled",
        "endpoint_sets_exact",
        "agent_evidence",
        "no_final_outputs",
    }
    checks = manifest.get("checks")
    if not isinstance(checks, dict) or any(checks.get(key) is not True for key in required_checks):
        return ValidationResult(
            "failed_validation", "TDC-ADMET-Tox smoke required checks are incomplete.", evidence, []
        )
    return ValidationResult(
        "finished", "TDC-ADMET-Tox blocking Codex smoke checks passed.", evidence, []
    )


def validate_psydefdetect_fullrun(root: Path) -> ValidationResult:
    manifest_path = root / "fullrun_manifest.json"
    state_path = root / "state.json"
    log_path = root / "logs/e2e.log"
    evidence = {
        "manifest": rel(manifest_path, root) if manifest_path.exists() else None,
        "state": rel(state_path, root) if state_path.exists() else None,
        "log": rel(log_path, root) if log_path.exists() else None,
        "final_report": None,
        "prediction_artifact": None,
        "score_artifact": None,
        "experiment_trace": None,
    }
    if not manifest_path.exists() or not state_path.exists() or not log_path.exists():
        return ValidationResult(
            "failed_no_artifacts",
            "PsyDefDetect full-run wrapper did not leave manifest/state/log evidence.",
            evidence,
            [],
        )
    state = read_json(state_path)
    if not isinstance(state, dict):
        return ValidationResult(
            "failed_no_artifacts", "PsyDefDetect full-run state is unreadable.", evidence, []
        )
    fullrun_manifest = read_json(manifest_path)
    if not isinstance(fullrun_manifest, dict):
        return ValidationResult(
            "failed_no_artifacts", "PsyDefDetect full-run manifest is unreadable.", evidence, []
        )
    evidence["status"] = state.get("status", "unknown")
    evidence["summary"] = state.get("summary")
    evidence["native_entrypoint"] = fullrun_manifest.get("native_entrypoint")
    evidence["provider_injection"] = fullrun_manifest.get("provider_injection")
    evidence["executor_kind"] = fullrun_manifest.get("executor_kind")
    if state.get("status") == "unsupported_native_entrypoint":
        reason = state.get(
            "summary", "Framework has no supported native noninteractive entrypoint."
        )
        return ValidationResult("unsupported_native_entrypoint", reason, evidence, [])
    if state.get("status") == "blocked_benchmark_authorization":
        reason = state.get(
            "summary", "Framework benchmark authorization has not been supplied."
        )
        return ValidationResult("blocked_benchmark_authorization", reason, evidence, [])
    final_report = pick_latest(
        [root / "workspace/final_report.md", root / "artifacts/final_report.md"]
    )
    prediction_artifact = pick_latest(
        [
            root / "workspace/predictions.jsonl",
            root / "workspace/submission.csv",
            root / "artifacts/predictions.jsonl",
            root / "artifacts/submission.csv",
        ]
    )
    experiment_trace = pick_latest(
        [
            root / "workspace/experiment_trace.json",
            root / "artifacts/experiment_trace.json",
        ]
    )
    score_artifact, score_payload = extract_psydefdetect_score(root)
    if final_report is not None:
        evidence["final_report"] = rel(final_report, root)
    if prediction_artifact is not None:
        evidence["prediction_artifact"] = rel(prediction_artifact, root)
    trace_payload = read_json(experiment_trace) if experiment_trace is not None else None
    if experiment_trace is not None and isinstance(trace_payload, dict):
        evidence["experiment_trace"] = rel(experiment_trace, root)
        evidence["framework_native_execution"] = trace_payload.get("framework_native_execution")
        evidence["consumed_topic_input"] = trace_payload.get("consumed_topic_input")
        evidence["workspace_trace_root"] = trace_payload.get("workspace_trace_root")
        evidence["experiment_count"] = (
            len(trace_payload.get("experiments", []))
            if isinstance(trace_payload.get("experiments"), list)
            else 0
        )
        evidence["selected_experiment_id"] = trace_payload.get("selected_experiment_id")
        evidence["framework_internal_model"] = trace_payload.get("framework_internal_model")
        evidence["framework_internal_api_base_url"] = trace_payload.get(
            "framework_internal_api_base_url"
        )
    if score_artifact is not None and isinstance(score_payload, dict):
        evidence["score_artifact"] = rel(score_artifact, root)
        evidence["psydefdetect_score"] = score_payload["psydefdetect_score"]
        evidence["score_key"] = score_payload["score_key"]
    if final_report is not None and not psydefdetect_report_looks_on_topic(final_report):
        return ValidationResult(
            "failed_validation",
            "PsyDefDetect full-run final report is polluted by another topic.",
            evidence,
            ["cross_topic_report_pollution"],
        )
    if state.get("status") == "blocked":
        return ValidationResult(
            "failed_validation",
            f"PsyDefDetect full-run wrapper is blocked: {state.get('summary', 'unknown blocker')}",
            evidence,
            [],
        )
    native_execution = (
        isinstance(trace_payload, dict) and trace_payload.get("framework_native_execution") is True
    )
    consumed_topic_input = (
        isinstance(trace_payload, dict) and trace_payload.get("consumed_topic_input") is True
    )
    workspace_trace_root = (
        trace_payload.get("workspace_trace_root") if isinstance(trace_payload, dict) else None
    )
    selected_experiment_id = (
        trace_payload.get("selected_experiment_id") if isinstance(trace_payload, dict) else None
    )
    experiments = trace_payload.get("experiments") if isinstance(trace_payload, dict) else None
    native_log_evidence = has_psydefdetect_native_execution_log_evidence(log_path, fullrun_manifest)
    expected_model = fullrun_manifest.get("evaluation_model")
    expected_base_url = fullrun_manifest.get("provider_base_url")
    provider_model_ok = (
        isinstance(trace_payload, dict)
        and isinstance(expected_model, str)
        and expected_model.strip()
        and trace_payload.get("framework_internal_model") == expected_model
        and isinstance(trace_payload.get("framework_internal_api_base_url"), str)
        and trace_payload["framework_internal_api_base_url"].strip()
        and isinstance(expected_base_url, str)
        and expected_base_url.strip()
        and trace_payload["framework_internal_api_base_url"].rstrip("/")
        == expected_base_url.rstrip("/")
    )

    if (
        state.get("status") in {"finished", "finished_degraded"}
        and final_report is not None
        and prediction_artifact is not None
        and score_artifact is not None
        and native_execution
        and consumed_topic_input
        and isinstance(workspace_trace_root, str)
        and workspace_trace_root.strip()
        and isinstance(selected_experiment_id, str)
        and selected_experiment_id.strip()
        and isinstance(experiments, list)
        and len(experiments) >= 2
        and len(experiments) <= 4
        and native_log_evidence
        and provider_model_ok
    ):
        return ValidationResult(
            "finished",
            "PsyDefDetect full-run produced score evidence and native experiment trace.",
            evidence,
            [],
        )

    if final_report is not None and prediction_artifact is not None:
        return ValidationResult(
            "failed_validation",
            "PsyDefDetect full-run left predictions/report artifacts, but native-entrypoint, provider, score, or experiment-trace evidence is incomplete.",
            evidence,
            ["missing_native_provider_score_or_experiment_trace"],
        )
    return ValidationResult(
        "failed_validation",
        "PsyDefDetect full-run did not produce sufficient prediction/report/score evidence.",
        evidence,
        ["missing_prediction_report_or_score"],
    )


def validate(framework: str, root: Path) -> ValidationResult:
    mapping = {
        "ai_researcher_real": validate_ai_researcher_real,
        "ai_researcher_resume": validate_ai_researcher_resume,
        "ai_scientist_v2": validate_ai_scientist_v2,
        "aris": validate_aris,
        "autoresearchclaw_resume": validate_autoresearchclaw_resume,
        "deepscientist": validate_deepscientist,
        "drclaw": validate_drclaw,
        "evoscientist_auto": validate_evoscientist,
        "evoscientist_continue": validate_evoscientist,
        "gave2_input_pack": validate_gave2_input_pack,
        "gave2_smoke": validate_gave2_smoke,
        "gave2_fullrun": validate_gave2_fullrun,
        "arc_wbe_2026_smoke": validate_arc_wbe_2026_smoke,
        "arc_wbe_2026_fullrun": validate_arc_wbe_2026_fullrun,
        "psydefdetect_smoke": validate_psydefdetect_smoke,
        "psydefdetect_fullrun": validate_psydefdetect_fullrun,
        "tdc_admet_tox_smoke": validate_tdc_admet_tox_smoke,
    }
    if framework not in mapping:
        raise SystemExit(f"Unknown framework validator: {framework}")
    return mapping[framework](root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--framework", required=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--state-file")
    parser.add_argument("--manifest-path")
    args = parser.parse_args()

    root = Path(args.run_root).resolve()
    state_file = Path(args.state_file).resolve() if args.state_file else root / "state.json"
    manifest_path = (
        Path(args.manifest_path).resolve()
        if args.manifest_path
        else root / "artifact_manifest.json"
    )

    state = {}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            state = {}

    result = validate(args.framework, root)
    manifest = {
        "framework": args.framework,
        "run_root": str(root),
        "validated_at": now_iso(),
        "status": result.status,
        "summary": result.summary,
        "warnings": result.warnings,
        "evidence": result.evidence,
        "prior_state": state,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    if state_file.parent.exists():
        merged = dict(state)
        merged["status"] = result.status
        merged["summary"] = result.summary
        merged["updated_at"] = now_iso()
        merged["validator_summary"] = result.summary
        merged["artifact_manifest"] = str(manifest_path)
        if "gave2_metrics" in result.evidence:
            merged["gave2_metrics"] = result.evidence["gave2_metrics"]
        if result.status == "finished_degraded":
            merged["degraded_reason"] = result.summary
        else:
            merged.pop("degraded_reason", None)
        state_file.write_text(json.dumps(merged, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if result.ok else 13


if __name__ == "__main__":
    raise SystemExit(main())
