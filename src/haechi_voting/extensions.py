from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping

from .models import TallyReport
from .record import ElectionRecord


class PublicVerificationBackend(ABC):
    @abstractmethod
    def describe(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def build_artifacts(self, record: ElectionRecord, tally_report: TallyReport) -> Mapping[str, Any]:
        raise NotImplementedError


@dataclass
class LocalRecordBackend(PublicVerificationBackend):
    def describe(self) -> str:
        return (
            "613-style local verifier: publish commitments, confirmation codes, "
            "challenge openings, and aggregate tally opening on a public record."
        )

    def build_artifacts(self, record: ElectionRecord, tally_report: TallyReport) -> Mapping[str, Any]:
        return {
            "records": len(record.entries),
            "cast_ballots": len(record.cast_entries()),
            "challenged_ballots": len(record.challenge_entries()),
            "aggregate_commitment": tally_report.aggregate_commitment,
        }


@dataclass
class ZeeperioStyleBackend(PublicVerificationBackend):
    """
    Architectural placeholder for paper 565.
    """

    def describe(self) -> str:
        return (
            "565-style verification backend: convert bulletin-board data into "
            "succinct polynomial arguments for automated off-chain/on-chain verification."
        )

    def build_artifacts(self, record: ElectionRecord, tally_report: TallyReport) -> Mapping[str, Any]:
        return {
            "backend": "zeeperio-style",
            "target": "succinct-proof-pipeline",
            "inputs": {
                "record_entries": len(record.entries),
                "cast_ballots": len(record.cast_entries()),
                "tally_slots": len(tally_report.aggregate_vector),
            },
            "notes": [
                "Replace placeholder proofs with KZG/Plonk-style polynomial commitments.",
                "Expose receipt and dispute proofs as separate verifier entrypoints.",
            ],
        }


class AggregationStrategy(ABC):
    @abstractmethod
    def describe(self) -> str:
        raise NotImplementedError


@dataclass
class DirectDeviceAggregation(AggregationStrategy):
    def describe(self) -> str:
        return "613-style direct aggregation on the voting device using homomorphic commitments."


@dataclass
class AggiosStyleAggregation(AggregationStrategy):
    """
    Architectural placeholder for paper 545.
    """

    def describe(self) -> str:
        return (
            "545-style aggregation: voters register to aggregators, aggregators "
            "publish batched tallies and partition proofs, and validators check "
            "eligibility, no-double-voting, and inclusion evidence."
        )
