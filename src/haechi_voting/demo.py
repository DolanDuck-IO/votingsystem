from __future__ import annotations

import json

from .device import VotingDevice
from .models import Contest, ElectionManifest
from .verifier import ElectionVerifier


def build_demo_manifest() -> ElectionManifest:
    return ElectionManifest(
        election_id="demo-2026",
        title="Campus Council Election",
        contests=(
            Contest(
                contest_id="chair",
                title="Chairperson",
                candidates=("alice", "bob", "carol"),
                min_selections=1,
                max_selections=1,
            ),
            Contest(
                contest_id="budget",
                title="Budget Proposal",
                candidates=("approve", "reject"),
                min_selections=1,
                max_selections=1,
            ),
        ),
    )


def run_demo() -> dict[str, object]:
    manifest = build_demo_manifest()
    device = VotingDevice(manifest=manifest)

    cast_1 = device.prepare_ballot({"chair": ["alice"], "budget": ["approve"]})
    device.cast_ballot(cast_1.ballot_id)

    challenged = device.prepare_ballot({"chair": ["bob"], "budget": ["reject"]})
    device.challenge_ballot(challenged.ballot_id)

    cast_2 = device.prepare_ballot({"chair": ["carol"], "budget": ["approve"]})
    device.cast_ballot(cast_2.ballot_id)

    tally_report = device.tally()
    verifier = ElectionVerifier(manifest=manifest, commitment_context=device.commitment_context)
    verification = verifier.verify(device.record, tally_report)

    return {
        "manifest": {
            "election_id": manifest.election_id,
            "title": manifest.title,
            "contests": [
                {
                    "contest_id": contest.contest_id,
                    "title": contest.title,
                    "candidates": list(contest.candidates),
                }
                for contest in manifest.contests
            ],
        },
        "record_size": len(device.record.entries),
        "cast_ballots": len(device.record.cast_entries()),
        "challenged_ballots": len(device.record.challenge_entries()),
        "tally": tally_report.tally_by_contest,
        "verification": {
            "success": verification.success,
            "checks": dict(verification.checks),
            "errors": list(verification.errors),
        },
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2, sort_keys=True))
