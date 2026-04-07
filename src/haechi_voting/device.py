from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from .crypto import (
    PedersenContext,
    add_vectors,
    hash_hex,
    make_confirmation_code,
    make_identifier_hash,
    manifest_fingerprint,
)
from .models import (
    BallotOpening,
    ElectionManifest,
    PendingBallot,
    PublishedBallotRecord,
    TallyReport,
)
from .proofs import (
    PlaceholderTallyProofSystem,
    PlaceholderWellFormednessProofSystem,
    TallyProofSystem,
    WellFormednessProofSystem,
)
from .record import ElectionRecord


@dataclass
class VotingDevice:
    manifest: ElectionManifest
    record: ElectionRecord = field(default_factory=ElectionRecord)
    commitment_context: PedersenContext | None = None
    well_formedness_proof_system: WellFormednessProofSystem = field(
        default_factory=PlaceholderWellFormednessProofSystem
    )
    tally_proof_system: TallyProofSystem = field(default_factory=PlaceholderTallyProofSystem)

    def __post_init__(self) -> None:
        if self.commitment_context is None:
            self.commitment_context = PedersenContext.from_manifest(self.manifest)
        self.base_hash = hash_hex(
            "haechi-base-hash",
            manifest_fingerprint(self.manifest),
            self.commitment_context.context_hash,
        )
        self.current_confirmation_code = hash_hex("confirmation-seed", self.base_hash)
        self.running_tally = self.manifest.zero_vector()
        self.running_randomness = 0
        self.pending_ballots: dict[str, PendingBallot] = {}

    def prepare_ballot(self, selections: Mapping[str, Sequence[str]]) -> PendingBallot:
        vector = self.manifest.encode_ballot(selections)
        randomness = self.commitment_context.random_scalar()
        commitment = self.commitment_context.commit(vector, randomness)
        proof = self.well_formedness_proof_system.prove(
            manifest=self.manifest,
            commitment=commitment,
            vector=vector,
            randomness=randomness,
        )
        ballot_id = secrets.token_hex(8)
        identifier_hash = make_identifier_hash(self.base_hash, ballot_id)
        sequence_no = self.record.next_sequence_no() + len(self.pending_ballots)
        confirmation_code = make_confirmation_code(
            identifier_hash,
            commitment,
            self.current_confirmation_code,
        )
        pending = PendingBallot(
            sequence_no=sequence_no,
            ballot_id=ballot_id,
            selections=dict(selections),
            vector=tuple(vector),
            randomness=randomness,
            commitment=commitment,
            proof=proof,
            identifier_hash=identifier_hash,
            confirmation_code=confirmation_code,
            previous_confirmation_code=self.current_confirmation_code,
        )
        self.pending_ballots[pending.ballot_id] = pending
        return pending

    def cast_ballot(self, ballot_id: str) -> PublishedBallotRecord:
        pending = self._consume_pending(ballot_id)
        entry = PublishedBallotRecord(
            sequence_no=self.record.next_sequence_no(),
            ballot_id=pending.ballot_id,
            status="cast",
            identifier_hash=pending.identifier_hash,
            commitment=pending.commitment,
            confirmation_code=pending.confirmation_code,
            proof=pending.proof,
        )
        self.record.append(entry)
        self.current_confirmation_code = pending.confirmation_code
        self.running_tally = add_vectors(self.running_tally, pending.vector)
        self.running_randomness = (self.running_randomness + pending.randomness) % self.commitment_context.q
        return entry

    def challenge_ballot(self, ballot_id: str) -> PublishedBallotRecord:
        pending = self._consume_pending(ballot_id)
        entry = PublishedBallotRecord(
            sequence_no=self.record.next_sequence_no(),
            ballot_id=pending.ballot_id,
            status="challenged",
            identifier_hash=pending.identifier_hash,
            commitment=pending.commitment,
            confirmation_code=pending.confirmation_code,
            proof=pending.proof,
            opening=BallotOpening(
                vector=pending.vector,
                randomness=pending.randomness,
                previous_confirmation_code=pending.previous_confirmation_code,
            ),
        )
        self.record.append(entry)
        self.current_confirmation_code = pending.confirmation_code
        return entry

    def tally(self) -> TallyReport:
        cast_entries = self.record.cast_entries()
        aggregate_commitment = self.commitment_context.aggregate_commitments(
            entry.commitment for entry in cast_entries
        )
        proof = self.tally_proof_system.prove(
            manifest=self.manifest,
            aggregate_commitment=aggregate_commitment,
            aggregate_vector=self.running_tally,
            aggregate_randomness=self.running_randomness,
        )
        return TallyReport(
            aggregate_commitment=aggregate_commitment,
            aggregate_randomness=self.running_randomness,
            aggregate_vector=tuple(self.running_tally),
            tally_by_contest=self.manifest.decode_vector(self.running_tally),
            cast_ballot_count=len(cast_entries),
            proof=proof,
        )

    def _consume_pending(self, ballot_id: str) -> PendingBallot:
        try:
            return self.pending_ballots.pop(ballot_id)
        except KeyError as exc:
            raise KeyError(f"unknown pending ballot: {ballot_id}") from exc
