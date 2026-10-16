# MountainCar re-adjudication of 2026-09-28 (frozen evidence)

On 2026-09-28 the MountainCar delivery floor changed by user ruling: 01's gate now requires
experiment_trace.json to record at least 1 experiment (upstream: 2-4), and 02's assembly floor
became >=1 stage selection (was 2). Retained runs that had been rejected only by the old floor were
re-judged WITHOUT re-running them: their deliverables were copied into a separate directory and the
then-current gate and official scorer were replayed there.

Outputs, never modified since:
- real_eval/runs/adjudication_mcar01_ge1_20260928/<tag>/verdict.json  (5 tags; 01 runs)
- real_eval/runs/adjudication_mcar02_ge1_20260928/<tag>/verdict.json  (3 tags; 02 runs, all assembly rc=4: no stage
  produced an official evaluation plus a full submission, so no score)
Each verdict records the source run, the model, every step's return code, the score and the repository
commit of the code that judged it. The source run directories were read-only inputs.

Scripts:
- adjudicate_mountaincar_ge1.sh   01: copies the deliverables, src/ and checkpoints/ of a retained run into the
  adjudication workspace, extracts the delivery gate verbatim from the overlay-rendered shared runner
  (shared runner + 01's shared-layer patch), runs it with the run's actual model/base URL, then the official
  frozen scorer inside the ai-researcher-exec:mountaincar-jax image with --network none.
- adjudicate_mountaincar02_ge1.sh 02: replays the ladder's assemble -> host-validate -> official-score chain on
  the retained run's BFTS artifacts, with the helpers pinned in helpers/.
- helpers/: assemble_mountaincar.py, mountaincar_host_validate.py, mc_python.sh -- the text of
  debug/dawei/ladder/staged/mountaincar/ at commit 08e8ae8, the commit every 02 verdict records
  (adjudicated 11:45-12:07 UTC). The ladder's assemble_mountaincar.py was changed right after, at 12:08
  (8ecb5a5, second-floor alignment), so the current ladder copy differs from the pinned one; the other
  two files are identical in both. In the pinned text the second floor still reads "contract needs 2";
  all three runs had 0 scored replays, so the verdicts do not depend on that floor.
  The 01 verdicts each record their own commit (ea6f433, 7354bba, a252bb2, 2557b84): the gate text was
  extracted from the runner as it was at each adjudication; the script's current form (overlay-rendered
  runner) dates from 2026-10-04.

Relocated here on 2026-10-16 from real_eval/scripts/ (real_eval/run_checks/ is gitignored, so this lives
under debug/dawei/ with the campaign records): these are records of a past ruling, not pipeline
tools. Only the path variables were changed (repo root and helper directory are now derived from the
file location); provider base URL defaults are left as they were, since each verdict records the values
used. Re-running is not intended: a verdict already on disk is skipped, and replaying against a newer
gate or patch version would not reproduce the recorded verdicts.
