#!/usr/bin/env python3
"""Entry point for the bounded zero-dollar compute job.

Fail-closed manifest gate first: every input listed in MANIFEST.json is
re-hashed and compared BEFORE any check or workload executes. Any missing
or mismatched input aborts with a non-zero exit — the manifest constrains
execution, it does not merely describe it.

Then runs the self-checks in test_workload.py (no test framework needed),
executes the deterministic workload, and writes results.json plus the
verified input manifest into out/. Stdlib only. Exits non-zero if any
check fails.

Trust anchor: MANIFEST.json itself is not self-verifying. The operator
holds the hardened manifest hashes out-of-band (see HARDENING.md); a
tampered manifest is an operator-visible event, not a silent one.

Usage: python3 run_job.py [--job-id ID]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent          # zero_dollar_run_bundle/
REPO_ROOT = HERE.parent                          # repository root
MANIFEST = HERE / "MANIFEST.json"
OUT = HERE / "out"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_manifest() -> dict[str, str]:
    """Fail closed: every manifest-listed input must exist and match.

    Returns the verified {relative_path: sha256} mapping. Raises
    SystemExit(non-zero) on any problem, before any workload code runs.
    """
    if not MANIFEST.is_file():
        print(f"MANIFEST GATE FAILED: {MANIFEST} not found; refusing to run",
              file=sys.stderr)
        raise SystemExit(2)
    try:
        manifest = json.loads(MANIFEST.read_text())
        expected = manifest["inputs"]
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"MANIFEST GATE FAILED: {MANIFEST} unreadable ({exc}); "
              f"refusing to run", file=sys.stderr)
        raise SystemExit(2)

    verified: dict[str, str] = {}
    failures: list[str] = []
    for rel, want in expected.items():
        path = REPO_ROOT / rel
        if not path.is_file():
            failures.append(f"{rel}: MISSING")
            continue
        got = sha256_file(path)
        if got != want:
            failures.append(f"{rel}: MISMATCH\n  expected {want}\n  got      {got}")
            continue
        verified[rel] = got
    if failures:
        print("MANIFEST GATE FAILED — refusing to run:", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        raise SystemExit(2)
    return verified


def run_checks() -> tuple[int, int, list[str]]:
    sys.path.insert(0, str(HERE))
    import test_workload

    passed, failed, failures = 0, 0, []
    for name in sorted(dir(test_workload)):
        if not name.startswith("test_"):
            continue
        fn = getattr(test_workload, name)
        if not callable(fn):
            continue
        try:
            fn()
            passed += 1
        except Exception:
            failed += 1
            failures.append(f"{name}:\n{traceback.format_exc()}")
    return passed, failed, failures


def main() -> int:
    # Gate first: no checks, no workload, no output until inputs verify.
    manifest = verify_manifest()

    ap = argparse.ArgumentParser()
    ap.add_argument("--job-id", default="manual")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()

    passed, failed, failures = run_checks()

    sys.path.insert(0, str(HERE))
    import workload

    payload = workload.run() if failed == 0 else None

    results = {
        "job_id": args.job_id,
        "lane": "github-actions/public/standard-linux (validatable locally)",
        "started_at": started,
        "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "checks_passed": passed,
        "checks_failed": failed,
        "check_failures": failures,
        "workload_payload": payload,
        "input_manifest_sha256": manifest,
        "manifest_verified": True,
        "execution_binding": {
            # Binds this result to the immutable execution that produced it.
            # Present under GitHub Actions; null for local runs.
            "github_sha": os.environ.get("GITHUB_SHA"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_repository": os.environ.get("GITHUB_REPOSITORY"),
            "github_ref": os.environ.get("GITHUB_REF"),
        },
        "python": sys.version,
    }
    (OUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(f"manifest gate: {len(manifest)} inputs verified; "
          f"checks: {passed} passed, {failed} failed; "
          f"results -> {OUT / 'results.json'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
