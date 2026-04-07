from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Sequence

from .crypto import hash_hex, manifest_fingerprint
from .models import ElectionManifest, TallyReport


class WellFormednessProofSystem(ABC):
    @abstractmethod
    def prove(
        self,
        manifest: ElectionManifest,
        commitment: int,
        vector: Sequence[int],
        randomness: int,
    ) -> Mapping[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def verify(
        self,
        manifest: ElectionManifest,
        commitment: int,
        proof: Mapping[str, Any],
    ) -> bool:
        raise NotImplementedError


class TallyProofSystem(ABC):
    @abstractmethod
    def prove(
        self,
        manifest: ElectionManifest,
        aggregate_commitment: int,
        aggregate_vector: Sequence[int],
        aggregate_randomness: int,
    ) -> Mapping[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def verify(
        self,
        manifest: ElectionManifest,
        tally_report: TallyReport,
    ) -> bool:
        raise NotImplementedError


class PlaceholderWellFormednessProofSystem(WellFormednessProofSystem):
    """
    Framework placeholder rather than a real NIZK.

    It intentionally keeps the proof interface stable so a real Haechi
    compressed Sigma proof backend can replace it later.
    """

    name = "placeholder-wf-v1"

    def prove(
        self,
        manifest: ElectionManifest,
        commitment: int,
        vector: Sequence[int],
        randomness: int,
    ) -> Mapping[str, Any]:
        contest_totals = manifest.contest_totals(vector)
        return {
            "scheme": self.name,
            "manifest_hash": manifest_fingerprint(manifest),
            "contest_totals": contest_totals,
            "binding": hash_hex(
                self.name,
                manifest_fingerprint(manifest),
                commitment,
                contest_totals,
                len(vector),
                randomness % 2,
            ),
            "note": (
                "Framework placeholder: replace with Haechi compressed "
                "Sigma well-formedness proofs for production use."
            ),
        }

    def verify(
        self,
        manifest: ElectionManifest,
        commitment: int,
        proof: Mapping[str, Any],
    ) -> bool:
        if proof.get("scheme") != self.name:
            return False
        if proof.get("manifest_hash") != manifest_fingerprint(manifest):
            return False
        contest_totals = proof.get("contest_totals")
        if not isinstance(contest_totals, Mapping):
            return False
        for contest in manifest.contests:
            total = contest_totals.get(contest.contest_id)
            if not isinstance(total, int):
                return False
            if not contest.min_selections <= total <= contest.max_selections:
                return False
        expected_zero = hash_hex(
            self.name,
            manifest_fingerprint(manifest),
            commitment,
            dict(contest_totals),
            manifest.total_slots,
            0,
        )
        expected_one = hash_hex(
            self.name,
            manifest_fingerprint(manifest),
            commitment,
            dict(contest_totals),
            manifest.total_slots,
            1,
        )
        return proof.get("binding") in {expected_zero, expected_one}


class PlaceholderTallyProofSystem(TallyProofSystem):
    name = "placeholder-tally-v1"

    def prove(
        self,
        manifest: ElectionManifest,
        aggregate_commitment: int,
        aggregate_vector: Sequence[int],
        aggregate_randomness: int,
    ) -> Mapping[str, Any]:
        return {
            "scheme": self.name,
            "manifest_hash": manifest_fingerprint(manifest),
            "binding": hash_hex(
                self.name,
                manifest_fingerprint(manifest),
                aggregate_commitment,
                list(aggregate_vector),
                aggregate_randomness,
            ),
        }

    def verify(
        self,
        manifest: ElectionManifest,
        tally_report: TallyReport,
    ) -> bool:
        if tally_report.proof.get("scheme") != self.name:
            return False
        if tally_report.proof.get("manifest_hash") != manifest_fingerprint(manifest):
            return False
        expected = hash_hex(
            self.name,
            manifest_fingerprint(manifest),
            tally_report.aggregate_commitment,
            list(tally_report.aggregate_vector),
            tally_report.aggregate_randomness,
        )
        return tally_report.proof.get("binding") == expected
