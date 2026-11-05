# Topic 2 Summary

## Topic
- Topic id: topic2
- Topic label: Topic 2
- Topic root: /data/mountaincar_continuous
- Contract file: /data/daweiwang/claude-home/researchclaweval-public/automation/topic2_contract.md
- Upstream: facebookresearch/MLGym @ 9d40c1b5035202018cd7091fb4e83a9c68b377c0

## Goal
Improve the official Average Reward of the MountainCarContinuous-v0
reinforcement-learning task as much as possible under the available resource
budget.

## Task description
- A runnable PPO Actor-Critic baseline and a frozen evaluation protocol are
  provided.
- You may inspect and modify the permitted training code (src/train.py,
  src/policy.py, src/networks.py, src/helpers.py, src/config.yaml) and add
  new research code under src/.
- You must run real training experiments and deliver exactly five valid
  trained checkpoints under checkpoints/.
- The frozen evaluator (evaluate.py) is read-only. It evaluates 256 parallel
  environments across 5 seeds, each rollout capped at 200 frames, and
  requires exactly 5 checkpoints.

## CRITICAL: Checkpoint Location Requirement
Checkpoints MUST be saved directly to:
  checkpoints/config-42-0.pkl
  checkpoints/config-42-1.pkl
  checkpoints/config-42-2.pkl
  checkpoints/config-42-3.pkl
  checkpoints/config-42-4.pkl
Do NOT put checkpoints in subdirectories (exp1_checkpoints/, etc.).

## Required normalized result fields
- score (Reward Mean, higher is better)
- reward_std
- score_source
- score_artifact

## Expected deliverables
- root-level research_idea.json, experiment_trace.json, and final_report.md
- exactly five checkpoints under checkpoints/ plus config.yaml and src/
- host-produced official score evidence after the native framework exits
- logs and preserved workspace traces

## Checkpoint / config contract
- The evaluator globs checkpoints/<config_stem>*.pkl and asserts exactly 5.
- Keep the Model class name in networks.py unchanged.
- config.yaml + networks.py + checkpoints must stay mutually compatible.
