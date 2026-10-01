"""Self-checks for the zero-dollar bundle workload. Stdlib only.

Each test_* function takes no arguments and raises AssertionError on failure.
run_job.py discovers and executes them without any test framework.
"""

from __future__ import annotations

import workload


def test_sha256_chain_deterministic() -> None:
    a = workload.sha256_chain("life-episode-001", 20000)
    b = workload.sha256_chain("life-episode-001", 20000)
    assert a == b, "chain must be deterministic"
    assert len(a) == 64 and all(c in "0123456789abcdef" for c in a)


def test_sha256_chain_seed_sensitive() -> None:
    a = workload.sha256_chain("seed-a", 100)
    b = workload.sha256_chain("seed-b", 100)
    assert a != b, "different seeds must diverge"


def test_merkle_root_deterministic_and_ordered() -> None:
    leaves = [workload.sha256_chain(f"leaf:{i}", 10) for i in range(16)]
    r1 = workload.merkle_root(leaves)
    r2 = workload.merkle_root(leaves)
    assert r1 == r2, "merkle root must be deterministic"
    assert workload.merkle_root(list(reversed(leaves))) != r1, "root must be order-sensitive"


def test_merkle_root_empty() -> None:
    # empty tree is defined as sha256 of empty input
    import hashlib

    assert workload.merkle_root([]) == hashlib.sha256(b"").hexdigest()


def test_canonical_json_digest_stable() -> None:
    obj = {"b": [3, 2, 1], "a": {"z": 1, "y": 2}}
    assert workload.canonical_json_digest(obj) == workload.canonical_json_digest(obj)
    # key order must not matter
    assert workload.canonical_json_digest({"a": 1, "b": 2}) == workload.canonical_json_digest(
        {"b": 2, "a": 1}
    )


def test_run_payload_self_consistent() -> None:
    payload = workload.run(seed="life-episode-001", rounds=20000)
    recomputed = workload.canonical_json_digest(
        {k: v for k, v in payload.items() if k != "payload_digest"}
    )
    assert payload["payload_digest"] == recomputed, "payload digest must verify"
    assert payload["seed"] == "life-episode-001"
