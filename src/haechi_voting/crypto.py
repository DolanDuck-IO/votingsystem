from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .models import ElectionManifest


RFC3526_GROUP14_PRIME = int(
    "".join(
        [
            "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1",
            "29024E088A67CC74020BBEA63B139B22514A08798E3404DD",
            "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245",
            "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED",
            "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D",
            "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F",
            "83655D23DCA3AD961C62F356208552BB9ED529077096966D",
            "670C354E4ABC9804F1746C08CA237327FFFFFFFFFFFFFFFF",
        ]
    ),
    16,
)


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _serialize(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    if isinstance(value, int):
        width = max(1, (value.bit_length() + 7) // 8)
        return value.to_bytes(width, "big", signed=False)
    if isinstance(value, Mapping):
        return _canonical_json(dict(value)).encode("utf-8")
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return _canonical_json(list(value)).encode("utf-8")
    return _canonical_json(value).encode("utf-8")


def hash_hex(*parts: Any) -> str:
    digest = hashlib.sha256()
    for part in parts:
        payload = _serialize(part)
        digest.update(len(payload).to_bytes(4, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _hash_to_subgroup(domain: str, label: str, p: int) -> int:
    counter = 0
    while True:
        digest = hashlib.sha256(f"{domain}|{label}|{counter}".encode("utf-8")).digest()
        candidate = int.from_bytes(digest, "big") % p
        if candidate in (0, 1, p - 1):
            counter += 1
            continue
        element = pow(candidate, 2, p)
        if element != 1:
            return element
        counter += 1


def add_vectors(left: Sequence[int], right: Sequence[int], modulus: int | None = None) -> list[int]:
    if len(left) != len(right):
        raise ValueError("vector lengths must match")
    if modulus is None:
        return [int(a) + int(b) for a, b in zip(left, right, strict=True)]
    return [(int(a) + int(b)) % modulus for a, b in zip(left, right, strict=True)]


def manifest_fingerprint(manifest: ElectionManifest) -> str:
    payload = {
        "election_id": manifest.election_id,
        "title": manifest.title,
        "contests": [
            {
                "contest_id": contest.contest_id,
                "title": contest.title,
                "candidates": list(contest.candidates),
                "min_selections": contest.min_selections,
                "max_selections": contest.max_selections,
                "allowed_values": list(contest.allowed_values),
            }
            for contest in manifest.contests
        ],
        "metadata": dict(manifest.metadata),
    }
    return hash_hex(payload)


@dataclass(frozen=True)
class PedersenContext:
    p: int
    q: int
    g: int
    slot_generators: tuple[int, ...]
    context_hash: str

    @classmethod
    def from_manifest(cls, manifest: ElectionManifest) -> "PedersenContext":
        p = RFC3526_GROUP14_PRIME
        q = (p - 1) // 2
        manifest_hash = manifest_fingerprint(manifest)
        g = _hash_to_subgroup(manifest_hash, "g", p)
        slot_generators = tuple(
            _hash_to_subgroup(manifest_hash, f"slot:{label}", p)
            for label in manifest.slot_labels()
        )
        return cls(
            p=p,
            q=q,
            g=g,
            slot_generators=slot_generators,
            context_hash=hash_hex("pedersen-context", manifest_hash, g, slot_generators),
        )

    def random_scalar(self) -> int:
        return secrets.randbelow(self.q - 1) + 1

    def commit(self, vector: Sequence[int], randomness: int) -> int:
        if len(vector) != len(self.slot_generators):
            raise ValueError(f"expected vector length {len(self.slot_generators)}, got {len(vector)}")
        acc = pow(self.g, randomness % self.q, self.p)
        for generator, value in zip(self.slot_generators, vector, strict=True):
            acc = (acc * pow(generator, int(value) % self.q, self.p)) % self.p
        return acc

    def verify_opening(self, commitment: int, vector: Sequence[int], randomness: int) -> bool:
        return self.commit(vector, randomness) == commitment

    def aggregate_commitments(self, commitments: Iterable[int]) -> int:
        acc = 1
        for commitment in commitments:
            acc = (acc * commitment) % self.p
        return acc

    def aggregate_randomness(self, values: Iterable[int]) -> int:
        return sum(int(value) for value in values) % self.q


def make_identifier_hash(base_hash: str, ballot_id: str) -> str:
    return hash_hex("identifier", base_hash, ballot_id)


def make_confirmation_code(identifier_hash: str, commitment: int, previous_confirmation_code: str) -> str:
    return hash_hex("confirmation", identifier_hash, commitment, previous_confirmation_code)
