# Goalslice

Choose the deliverables you need, then keep every declared prerequisite and
omit unrelated work before scheduling. This is an offline Python standard-library
tool. It executes no task labels and reads no network, environment, wallet or key.

From the repository root, one command shows it working:

```sh
python3 -B line-1/tools/goalslice/goalslice.py --demo --explain
```

Observed: choosing `deliver` keeps brief, build, test and deliver, totaling
**11 estimated work minutes**. It omits optional-chart and optional-polish,
totaling **12 work minutes**. Each retained task lists the requested targets
that require it. This makes omitted work explicit for human review. Ten tests
passed, including 200 seeded graphs checked by independent fixed-point closure,
numeric boundary round-trips and an integration with Workplan and Plancheck.
The selected demo schedules in 11 minutes on two workers under a 12-minute budget.

For your own graph, repeat `--target` for each required deliverable:

```sh
python3 -B line-1/tools/goalslice/goalslice.py --tasks line-1/tools/plancheck/tasks.json --target b
```

Without `--explain`, stdout contains **only a planner-compatible `tasks` object**,
with JSON numeric durations preserved exactly. `--explain` instead returns a
review report: durations and effort totals are exact decimal strings, not
planner input. Default demo output can feed the existing planner offline:

```sh
python3 -B line-1/tools/goalslice/goalslice.py --demo > line-1/tools/goalslice/selected.json
python3 -B line-1/tools/workplan/workplan.py --input line-1/tools/goalslice/selected.json --workers 2 --budget 12
```

The first command creates a local output file only because the caller redirects
stdout; the tool itself writes no files. Workplan uses floating point for
fractional estimates; exact emission by Goalslice does not change Workplan's
numeric limitations. Use Plancheck to validate a complete resulting schedule.

## Contract and limits

Input is the same strict task graph used by Plancheck: exactly one `tasks`
array of 1–500 rows with unique nonempty `id` (at most 100 characters), positive
numeric `minutes` and optional distinct prerequisite IDs in `after`. The
**entire** graph must be valid, including omitted branches. Cycles, unknown
dependencies, invalid numbers, duplicate JSON keys and unknown fields refuse
the operation before output. Targets must be 1–500 distinct known IDs. Shared
prerequisites appear once; selecting an ancestor and descendant is allowed.

The unchanged sibling `../plancheck/plancheck.py` supplies graph validation,
exact number parsing and the bounded ordinary workspace-local file reader.
Keep both directories together. Each input and the emitted planner graph is
limited to 100,000 bytes. Numeric inputs have at most 100 coefficient digits
and exponent magnitude 100; no decimal context rounding occurs. Output is
deterministic by task and target ID and retains all edges between selected
tasks. Python API: `select(data, targets)` returns the explanation;
`tasks_json(report)` serializes its selected graph.

Exit **0** means a valid selection, **1** means invalid input or an exceeded
limit (stderr, no partial stdout); argument syntax errors use argparse exit 2.
No deadline is inferred. Removed work may contain obligations absent from the
declared dependency graph: the caller must select all mandatory deliverables.
Prerequisite closure is minimal for the supplied targets, not a proof that
these targets satisfy the real job. Effort totals are not elapsed time, a
schedule, saved wall-clock time or a completion guarantee. No graph, task or
existing schedule is modified in place.

Run the checks:

```sh
python3 -B line-1/tools/goalslice/selftest.py
```

Tests cover shared prerequisites, ancestor targets, disconnected branches,
invalid omitted work, invalid targets, immutable and permuted inputs, a
500-task chain, exact decimals through 100-digit and exponent boundaries,
escaped IDs, CLI exits, duplicate keys, overlarge files, 200 seeded closure
oracles and the planner/checker integration. Fixtures stay in
`test/scratch/goalslice/`. These are local observations, not independent certification.
