from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class Contest:
    contest_id: str
    title: str
    candidates: tuple[str, ...]
    min_selections: int = 0
    max_selections: int = 1
    allowed_values: tuple[int, int] = (0, 1)

    def __post_init__(self) -> None:
        if not self.candidates:
            raise ValueError(f"contest {self.contest_id} must contain at least one candidate")
        if self.min_selections < 0:
            raise ValueError("min_selections must be non-negative")
        if self.max_selections < self.min_selections:
            raise ValueError("max_selections must be >= min_selections")


@dataclass(frozen=True)
class ElectionManifest:
    election_id: str
    title: str
    contests: tuple[Contest, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.contests:
            raise ValueError("manifest must contain at least one contest")
        ids = [contest.contest_id for contest in self.contests]
        if len(ids) != len(set(ids)):
            raise ValueError("contest ids must be unique")

    @property
    def total_slots(self) -> int:
        return sum(len(contest.candidates) for contest in self.contests)

    def slot_labels(self) -> list[str]:
        labels: list[str] = []
        for contest in self.contests:
            for candidate in contest.candidates:
                labels.append(f"{contest.contest_id}:{candidate}")
        return labels

    def normalize_ballot(self, selections: Mapping[str, Sequence[str]]) -> dict[str, list[str]]:
        normalized = {contest.contest_id: list(selections.get(contest.contest_id, ())) for contest in self.contests}
        for contest in self.contests:
            chosen = normalized[contest.contest_id]
            if len(chosen) != len(set(chosen)):
                raise ValueError(f"contest {contest.contest_id} contains duplicated selections")
            unknown = sorted(set(chosen) - set(contest.candidates))
            if unknown:
                raise ValueError(f"contest {contest.contest_id} contains unknown candidates: {unknown}")
            if not contest.min_selections <= len(chosen) <= contest.max_selections:
                raise ValueError(
                    f"contest {contest.contest_id} requires between "
                    f"{contest.min_selections} and {contest.max_selections} selections"
                )
        extra_contests = sorted(set(selections) - {contest.contest_id for contest in self.contests})
        if extra_contests:
            raise ValueError(f"ballot contains unknown contests: {extra_contests}")
        return normalized

    def encode_ballot(self, selections: Mapping[str, Sequence[str]]) -> list[int]:
        normalized = self.normalize_ballot(selections)
        vector: list[int] = []
        for contest in self.contests:
            chosen = set(normalized[contest.contest_id])
            min_value, max_value = contest.allowed_values
            for candidate in contest.candidates:
                value = 1 if candidate in chosen else 0
                if not min_value <= value <= max_value:
                    raise ValueError(f"candidate value for {contest.contest_id}:{candidate} is outside allowed range")
                vector.append(value)
        return vector

    def decode_vector(self, vector: Sequence[int]) -> dict[str, dict[str, int]]:
        if len(vector) != self.total_slots:
            raise ValueError(f"expected vector length {self.total_slots}, got {len(vector)}")
        result: dict[str, dict[str, int]] = {}
        index = 0
        for contest in self.contests:
            result[contest.contest_id] = {}
            for candidate in contest.candidates:
                result[contest.contest_id][candidate] = int(vector[index])
                index += 1
        return result

    def contest_totals(self, vector: Sequence[int]) -> dict[str, int]:
        decoded = self.decode_vector(vector)
        return {
            contest.contest_id: sum(decoded[contest.contest_id][candidate] for candidate in contest.candidates)
            for contest in self.contests
        }

    def zero_vector(self) -> list[int]:
        return [0] * self.total_slots


@dataclass(frozen=True)
class PendingBallot:
    sequence_no: int
    ballot_id: str
    selections: Mapping[str, Sequence[str]]
    vector: tuple[int, ...]
    randomness: int
    commitment: int
    proof: Mapping[str, Any]
    identifier_hash: str
    confirmation_code: str
    previous_confirmation_code: str


@dataclass(frozen=True)
class BallotOpening:
    vector: tuple[int, ...]
    randomness: int
    previous_confirmation_code: str


@dataclass(frozen=True)
class PublishedBallotRecord:
    sequence_no: int
    ballot_id: str
    status: str
    identifier_hash: str
    commitment: int
    confirmation_code: str
    proof: Mapping[str, Any]
    opening: BallotOpening | None = None


@dataclass(frozen=True)
class TallyReport:
    aggregate_commitment: int
    aggregate_randomness: int
    aggregate_vector: tuple[int, ...]
    tally_by_contest: Mapping[str, Mapping[str, int]]
    cast_ballot_count: int
    proof: Mapping[str, Any]


@dataclass(frozen=True)
class VerificationReport:
    success: bool
    checks: Mapping[str, bool]
    errors: tuple[str, ...]
