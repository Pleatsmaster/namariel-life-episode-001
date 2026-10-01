"""Deterministic sample workload for the zero-dollar compute lane.

Pure stdlib, no network, no secrets, no side effects outside the bundle's
out/ directory. CPU-bound and fully deterministic: the same inputs always
produce the same outputs, so a run can be verified by recomputation.
"""

from __future__ import annotations

import hashlib
import json


def sha256_chain(seed: str, rounds: int) -> str:
    """Iterated SHA-256 chain. Deterministic for a fixed seed and round count.

    rounds=N performs exactly N SHA-256 transformations of the seed bytes;
    the returned hex string is the digest after the Nth transformation
    (not one hash more).
    """
    digest = seed.encode("utf-8")
    for _ in range(rounds):
        digest = hashlib.sha256(digest).digest()
    return digest.hex()


def merkle_root(leaves: list[str]) -> str:
    """Toy Merkle root over hex leaf strings. Deterministic."""
    level = [bytes.fromhex(leaf) for leaf in leaves]
    if not level:
        return hashlib.sha256(b"").hexdigest()
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left
            nxt.append(hashlib.sha256(left + right).digest())
        level = nxt
    return level[0].hex()


def canonical_json_digest(obj: object) -> str:
    """SHA-256 over canonical JSON (sort_keys, compact separators, utf-8)."""
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def run(seed: str = "life-episode-001", rounds: int = 20000) -> dict:
    """Execute the bounded workload and return a results dict."""
    chain = sha256_chain(seed, rounds)
    leaves = [sha256_chain(f"{seed}:{i}", 50) for i in range(16)]
    root = merkle_root(leaves)
    payload = {"seed": seed, "rounds": rounds, "chain_head": chain, "merkle_root": root}
    payload["payload_digest"] = canonical_json_digest(
        {k: v for k, v in payload.items() if k != "payload_digest"}
    )
    return payload
