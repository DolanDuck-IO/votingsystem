from __future__ import annotations

from typing import Any, Mapping

from .device import VotingDevice
from .models import (
    BallotOpening,
    Contest,
    ElectionManifest,
    PendingBallot,
    PublishedBallotRecord,
    TallyReport,
    VerificationReport,
)
from .record import ElectionRecord


def contest_to_dict(contest: Contest) -> dict[str, Any]:
    return {
        "contest_id": contest.contest_id,
        "title": contest.title,
        "candidates": list(contest.candidates),
        "min_selections": contest.min_selections,
        "max_selections": contest.max_selections,
        "allowed_values": list(contest.allowed_values),
    }


def contest_from_dict(data: Mapping[str, Any]) -> Contest:
    return Contest(
        contest_id=str(data["contest_id"]),
        title=str(data["title"]),
        candidates=tuple(str(value) for value in data["candidates"]),
        min_selections=int(data.get("min_selections", 0)),
        max_selections=int(data.get("max_selections", 1)),
        allowed_values=tuple(int(value) for value in data.get("allowed_values", (0, 1))),
    )


def manifest_to_dict(manifest: ElectionManifest) -> dict[str, Any]:
    return {
        "election_id": manifest.election_id,
        "title": manifest.title,
        "contests": [contest_to_dict(contest) for contest in manifest.contests],
        "metadata": dict(manifest.metadata),
    }


def manifest_from_dict(data: Mapping[str, Any]) -> ElectionManifest:
    return ElectionManifest(
        election_id=str(data["election_id"]),
        title=str(data["title"]),
        contests=tuple(contest_from_dict(item) for item in data["contests"]),
        metadata=dict(data.get("metadata", {})),
    )


def pending_ballot_to_dict(ballot: PendingBallot) -> dict[str, Any]:
    return {
        "sequence_no": ballot.sequence_no,
        "ballot_id": ballot.ballot_id,
        "selections": {key: list(values) for key, values in ballot.selections.items()},
        "vector": list(ballot.vector),
        "randomness": ballot.randomness,
        "commitment": ballot.commitment,
        "proof": dict(ballot.proof),
        "identifier_hash": ballot.identifier_hash,
        "confirmation_code": ballot.confirmation_code,
        "previous_confirmation_code": ballot.previous_confirmation_code,
    }


def pending_ballot_from_dict(data: Mapping[str, Any]) -> PendingBallot:
    return PendingBallot(
        sequence_no=int(data["sequence_no"]),
        ballot_id=str(data["ballot_id"]),
        selections={key: list(values) for key, values in dict(data["selections"]).items()},
        vector=tuple(int(value) for value in data["vector"]),
        randomness=int(data["randomness"]),
        commitment=int(data["commitment"]),
        proof=dict(data["proof"]),
        identifier_hash=str(data["identifier_hash"]),
        confirmation_code=str(data["confirmation_code"]),
        previous_confirmation_code=str(data["previous_confirmation_code"]),
    )


def opening_to_dict(opening: BallotOpening) -> dict[str, Any]:
    return {
        "vector": list(opening.vector),
        "randomness": opening.randomness,
        "previous_confirmation_code": opening.previous_confirmation_code,
    }


def opening_from_dict(data: Mapping[str, Any]) -> BallotOpening:
    return BallotOpening(
        vector=tuple(int(value) for value in data["vector"]),
        randomness=int(data["randomness"]),
        previous_confirmation_code=str(data["previous_confirmation_code"]),
    )


def published_record_to_dict(record: PublishedBallotRecord) -> dict[str, Any]:
    payload = {
        "sequence_no": record.sequence_no,
        "ballot_id": record.ballot_id,
        "status": record.status,
        "identifier_hash": record.identifier_hash,
        "commitment": record.commitment,
        "confirmation_code": record.confirmation_code,
        "proof": dict(record.proof),
        "opening": None,
    }
    if record.opening is not None:
        payload["opening"] = opening_to_dict(record.opening)
    return payload


def published_record_from_dict(data: Mapping[str, Any]) -> PublishedBallotRecord:
    opening_data = data.get("opening")
    return PublishedBallotRecord(
        sequence_no=int(data["sequence_no"]),
        ballot_id=str(data["ballot_id"]),
        status=str(data["status"]),
        identifier_hash=str(data["identifier_hash"]),
        commitment=int(data["commitment"]),
        confirmation_code=str(data["confirmation_code"]),
        proof=dict(data["proof"]),
        opening=opening_from_dict(opening_data) if opening_data else None,
    )


def tally_to_dict(tally: TallyReport) -> dict[str, Any]:
    return {
        "aggregate_commitment": tally.aggregate_commitment,
        "aggregate_randomness": tally.aggregate_randomness,
        "aggregate_vector": list(tally.aggregate_vector),
        "tally_by_contest": {contest_id: dict(values) for contest_id, values in tally.tally_by_contest.items()},
        "cast_ballot_count": tally.cast_ballot_count,
        "proof": dict(tally.proof),
    }


def tally_from_dict(data: Mapping[str, Any]) -> TallyReport:
    return TallyReport(
        aggregate_commitment=int(data["aggregate_commitment"]),
        aggregate_randomness=int(data["aggregate_randomness"]),
        aggregate_vector=tuple(int(value) for value in data["aggregate_vector"]),
        tally_by_contest={
            contest_id: {candidate: int(value) for candidate, value in dict(values).items()}
            for contest_id, values in dict(data["tally_by_contest"]).items()
        },
        cast_ballot_count=int(data["cast_ballot_count"]),
        proof=dict(data["proof"]),
    )


def verification_to_dict(report: VerificationReport) -> dict[str, Any]:
    return {
        "success": report.success,
        "checks": dict(report.checks),
        "errors": list(report.errors),
    }


def verification_from_dict(data: Mapping[str, Any]) -> VerificationReport:
    return VerificationReport(
        success=bool(data["success"]),
        checks={str(key): bool(value) for key, value in dict(data["checks"]).items()},
        errors=tuple(str(value) for value in data["errors"]),
    )


def election_record_to_dict(record: ElectionRecord) -> dict[str, Any]:
    return {"entries": [published_record_to_dict(entry) for entry in record.entries]}


def election_record_from_dict(data: Mapping[str, Any]) -> ElectionRecord:
    return ElectionRecord(entries=[published_record_from_dict(entry) for entry in data.get("entries", [])])


def device_state_to_dict(device: VotingDevice) -> dict[str, Any]:
    return {
        "current_confirmation_code": device.current_confirmation_code,
        "running_tally": list(device.running_tally),
        "running_randomness": device.running_randomness,
        "record": election_record_to_dict(device.record),
        "pending_ballots": {
            ballot_id: pending_ballot_to_dict(ballot)
            for ballot_id, ballot in device.pending_ballots.items()
        },
    }


def restore_device(manifest: ElectionManifest, state: Mapping[str, Any] | None) -> VotingDevice:
    device = VotingDevice(manifest=manifest)
    if not state:
        return device
    device.current_confirmation_code = str(state["current_confirmation_code"])
    device.running_tally = [int(value) for value in state["running_tally"]]
    device.running_randomness = int(state["running_randomness"])
    device.record = election_record_from_dict(dict(state["record"]))
    device.pending_ballots = {
        ballot_id: pending_ballot_from_dict(ballot)
        for ballot_id, ballot in dict(state.get("pending_ballots", {})).items()
    }
    return device
