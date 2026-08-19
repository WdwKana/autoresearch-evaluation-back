#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "real_eval" / "registry"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_registry() -> tuple[dict[str, dict], dict[str, dict], list[dict]]:
    topics = {item["id"]: item for item in load_json(REGISTRY / "topics.json")["topics"]}
    frameworks = {item["id"]: item for item in load_json(REGISTRY / "frameworks.json")["frameworks"]}
    runs = load_json(REGISTRY / "runs.json")["runs"]
    return topics, frameworks, runs


def filter_runs(runs: list[dict], topic: str | None, mode: str | None) -> list[dict]:
    filtered = []
    for run in runs:
        if topic and run["topic_id"] != topic:
            continue
        if mode and run["mode"] != mode:
            continue
        filtered.append(run)
    return filtered


def render_markdown(topics: dict[str, dict], frameworks: dict[str, dict], runs: list[dict]) -> str:
    lines = [
        "| Topic | Mode | Framework | Wrapper | Validator |",
        "|---|---|---|---|---|",
    ]
    for run in runs:
        topic = topics[run["topic_id"]]
        framework = frameworks[run["framework_id"]]
        lines.append(
            "| {topic} | {mode} | {framework_id} {framework_name} | `{wrapper}` | `{validator}` |".format(
                topic=topic["label"],
                mode=run["mode"],
                framework_id=run["framework_id"],
                framework_name=framework["name"],
                wrapper=run["wrapper"],
                validator=run["validator"],
            )
        )
    return "\n".join(lines)


def render_json(topics: dict[str, dict], frameworks: dict[str, dict], runs: list[dict]) -> str:
    rows = []
    for run in runs:
        topic = topics[run["topic_id"]]
        framework = frameworks[run["framework_id"]]
        rows.append(
            {
                **run,
                "topic_label": topic["label"],
                "framework_name": framework["name"],
            }
        )
    return json.dumps({"rows": rows}, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Print the ResearchClawEval registry matrix.")
    parser.add_argument("--topic", choices=["babylm", "gave2_task2"])
    parser.add_argument("--mode", choices=["input_pack", "smoke", "fullrun"])
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()

    topics, frameworks, runs = load_registry()
    runs = filter_runs(runs, args.topic, args.mode)
    if args.format == "json":
        print(render_json(topics, frameworks, runs))
    else:
        print(render_markdown(topics, frameworks, runs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
