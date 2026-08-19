# BabyLM-10M Legacy Evaluation Contract

## Status

This lane is retained as a legacy compatibility contract. New integrations
should target a stable or beta topic from the registry.

## Inputs

- Dataset location is supplied through `BABYLM_DATASET_ROOT`.
- Framework source location is resolved from the framework registry.
- Datasets and framework checkouts are external assets and are not distributed
  by ResearchClawEval.

## Execution

- Run the framework through its documented native entrypoint.
- Keep all generated files inside a fresh per-run workspace.
- Do not use generic host-agent output as framework-native evidence.

## Required evidence

- A framework-authored final report.
- Experiment or training logs sufficient to identify the selected approach.
- Evaluation output and model/checkpoint evidence when the framework supports
  those artifacts.
- Runtime metadata identifying the framework version, model/provider, and
  native launch command.

Missing official score evidence is reported as `N/A`, never as zero.
