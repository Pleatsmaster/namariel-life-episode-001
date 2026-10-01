# zero_dollar_run_bundle (hardened descendant)

Self-contained execution bundle for **LIFE-EPISODE-001 — Zero-Dollar Compute Lane**.

Lane: **GitHub Actions, public repository, standard Linux runners** — $0, no
payment method required, no billing enabled. See
`../ZERO_DOLLAR_EXECUTION_DECISION.json` for the selection record and
`../ZERO_DOLLAR_EXECUTION_PLAN.md` for the full plan.
See `../HARDENING.md` for what changed relative to the reviewed candidate
and why.

## Repository layout (the workflow MUST live at the repo root)

```
.github/workflows/zero-dollar-compute.yml   <- GitHub discovers workflows ONLY here
zero_dollar_run_bundle/
    run_job.py
    workload.py
    test_workload.py
    MANIFEST.json
    README.md
```

## Contents

- `.github/workflows/zero-dollar-compute.yml` — the CI workflow, at the
  repository root where GitHub discovers it. Pinned to the `ubuntu-22.04`
  runner image label and Python 3.12. **Manual `workflow_dispatch` only** —
  no push trigger, so no push can launch external compute on its own
  (prepared code ≠ authorized execution). Least authority:
  `permissions: contents: read`, checkout with `persist-credentials: false`.
  All three actions pinned to full commit SHAs (resolved 2026-10-01), not
  movable major tags. Larger runners are always billed even on public repos,
  so they are excluded.
- `run_job.py` — job entry point: **fail-closed manifest gate first** (every
  input in MANIFEST.json is re-hashed and compared before any check or
  workload runs; any missing/mismatched input aborts with exit 2), then runs
  self-checks, executes the deterministic workload, writes `out/results.json`
  + verified input hashes, and records the GitHub execution binding
  (`GITHUB_SHA` / `GITHUB_RUN_ID` / `GITHUB_REPOSITORY` / `GITHUB_REF`) so the
  archived result names the immutable commit and run that produced it.
  Stdlib only.
- `workload.py` — deterministic CPU-bound sample workload (SHA-256 chains,
  toy Merkle root, canonical-JSON digest). No application-level network
  calls, no secrets.
  `sha256_chain(seed, rounds)` performs exactly `rounds` transformations.
- `test_workload.py` — self-checks, runnable with no test framework.
- `MANIFEST.json` — SHA-256 of every bundle input (repo-relative paths),
  excluding the workflow itself. Regenerate after any edit. Trust chain:
  the reviewed workflow carries `EXPECTED_MANIFEST_SHA256` and verifies this
  file plus every listed input *before* `run_job.py` executes — because
  `run_job.py` cannot securely verify itself. The workflow's own identity is
  anchored by the immutable Git commit of the run plus the out-of-band
  workflow SHA held by the operator.
- `out/` — created by local validation runs; not part of the shipped bundle.

## Operator actions still required (not performed in this episode)

1. Create (or choose) a GitHub account — no payment method needed for this lane.
2. Create a **public** repository (public visibility is what makes standard
   runners free; a private repo would draw on the 2,000 min/month quota).
3. Push this layout so that `.github/workflows/zero-dollar-compute.yml` is at
   the repo root and `zero_dollar_run_bundle/` sits beside it.
4. Trigger the workflow manually (**Actions → zero-dollar-compute → Run
   workflow**). There is no push trigger by design.
5. Inspect the `job-results` artifact; verify `payload_digest` recomputes.

## Local validation (performed 2026-10-01, hardened descendant)

```
python3 -m py_compile zero_dollar_run_bundle/run_job.py \
    zero_dollar_run_bundle/workload.py zero_dollar_run_bundle/test_workload.py
python3 zero_dollar_run_bundle/run_job.py --job-id local-validation
```

Optional operator-side YAML sanity check (requires PyYAML — an
operator-machine dependency, NOT part of the bundle; the bundle itself and
its validation are stdlib-only):

```
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/zero-dollar-compute.yml'))"
```

All checks passed; `out/results.json` written. No external execution occurred.
