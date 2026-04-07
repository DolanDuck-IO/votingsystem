from __future__ import annotations

from dataclasses import dataclass, field

from .models import PublishedBallotRecord


@dataclass
class ElectionRecord:
    entries: list[PublishedBallotRecord] = field(default_factory=list)

    def append(self, entry: PublishedBallotRecord) -> None:
        self.entries.append(entry)

    def cast_entries(self) -> list[PublishedBallotRecord]:
        return [entry for entry in self.entries if entry.status == "cast"]

    def challenge_entries(self) -> list[PublishedBallotRecord]:
        return [entry for entry in self.entries if entry.status == "challenged"]

    def next_sequence_no(self) -> int:
        return len(self.entries) + 1
