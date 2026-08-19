# ResearchClawEval

[中文说明](README.zh-CN.md)

ResearchClawEval is a public evaluation control plane for research-agent
frameworks. It defines task contracts, pins upstream framework versions,
records adapter patches, validates run evidence, and renders sanitized result
tables without distributing private datasets or framework checkouts.

## Support matrix

| Topic | Maturity | Public modes |
|---|---|---|
| GAVE2-Task2 | stable | input pack, smoke, full run |
| ARC-WBE-2026 | stable | input pack, smoke, full run |
| PsyDefDetect | beta | smoke, full run |
| BabyLM-10M | legacy | full run |
| TDC-ADMET-Tox | experimental | smoke pilot |

The registry contains seven framework adapters and 64 topic/framework/mode
mappings. A mapping is not proof of a valid native result. Full-run rows remain
`candidate_requires_runtime_evidence` until launch, provider, trace, and output
evidence pass validation. Generic host `codex exec` mappings are explicitly
`unsupported_non_native`.

## Quick start

Requirements: Linux, Python 3.10-3.12, and `uv`. Docker is required only for
real framework runs.

### One-click setup (for collaborators)

```bash
# Clone this repository
git clone https://github.com/YOUR_USERNAME/researchclaweval-public.git
cd researchclaweval-public

# Run the setup script — clones 3 frameworks, applies patches, installs deps
bash setup.sh

# Set up your LLM API key
export OPENAI_API_KEY=your_key_here
export OPENAI_BASE_URL=https://your-provider-url/v1
export OPENAI_MODEL=your-model-name

# Verify the setup
uv run rceval validate registry
uv run rceval registry list
uv run rceval registry matrix --topic gave2_task2 --mode fullrun
uv run rceval dry-run --topic arc_wbe_2026 --mode smoke --output-dir /tmp/rceval-plan
uv run rceval leaderboard render
```

See [SETUP.md](SETUP.md) for detailed collaboration instructions.

### Minimal validation (no frameworks needed)

These commands do not launch a framework or require datasets. Framework and
dataset locations are supplied later through registry environment overrides.

```bash
uv sync --extra dev
uv run rceval validate registry
uv run rceval registry list
uv run rceval registry matrix --topic gave2_task2 --mode fullrun
uv run rceval dry-run --topic arc_wbe_2026 --mode smoke --output-dir /tmp/rceval-plan
uv run rceval leaderboard render
```

## Repository boundary

This repository contains contracts, registry data, validators, wrappers,
adapter manifests, minimal patches, tests, and public documentation. It does
not contain API credentials, hidden labels, datasets, raw run directories,
local automation state, or full upstream framework sources.

See [CONTRIBUTING.md](CONTRIBUTING.md) for Topic, adapter, and result submission
requirements. `framework_evaluator` is experimental in v0.1 and is not yet a
stable Python API.

