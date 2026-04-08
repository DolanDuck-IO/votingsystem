from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .device import VotingDevice
from .models import ElectionManifest
from .serialization import (
    device_state_to_dict,
    manifest_from_dict,
    manifest_to_dict,
    restore_device,
    tally_from_dict,
    tally_to_dict,
    verification_to_dict,
)
from .verifier import ElectionVerifier


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class VotingService:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        self._lock = threading.RLock()
        self._ensure_parent()
        self._initialize_schema()

    def _ensure_parent(self) -> None:
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_schema(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS elections (
                    election_id TEXT PRIMARY KEY,
                    manifest_json TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    tally_json TEXT,
                    verification_json TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    election_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(election_id) REFERENCES elections(election_id)
                );
                """
            )
            connection.commit()

    def _write_audit_log(self, connection: sqlite3.Connection, election_id: str, event_type: str, payload: Mapping[str, Any]) -> None:
        connection.execute(
            """
            INSERT INTO audit_logs (election_id, event_type, payload_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (election_id, event_type, json.dumps(dict(payload), ensure_ascii=False, sort_keys=True), utc_now_iso()),
        )

    def _load_election_row(self, connection: sqlite3.Connection, election_id: str) -> sqlite3.Row:
        row = connection.execute(
            """
            SELECT election_id, manifest_json, state_json, tally_json, verification_json, status, created_at, updated_at
            FROM elections
            WHERE election_id = ?
            """,
            (election_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown election: {election_id}")
        return row

    def _load_device(self, row: sqlite3.Row) -> tuple[ElectionManifest, VotingDevice]:
        manifest = manifest_from_dict(json.loads(row["manifest_json"]))
        state = json.loads(row["state_json"])
        device = restore_device(manifest, state)
        return manifest, device

    def _persist_device(
        self,
        connection: sqlite3.Connection,
        election_id: str,
        device: VotingDevice,
        *,
        status: str,
        tally: Mapping[str, Any] | None = None,
        verification: Mapping[str, Any] | None = None,
    ) -> None:
        connection.execute(
            """
            UPDATE elections
            SET state_json = ?, tally_json = COALESCE(?, tally_json), verification_json = COALESCE(?, verification_json),
                status = ?, updated_at = ?
            WHERE election_id = ?
            """,
            (
                json.dumps(device_state_to_dict(device), ensure_ascii=False, sort_keys=True),
                json.dumps(dict(tally), ensure_ascii=False, sort_keys=True) if tally is not None else None,
                json.dumps(dict(verification), ensure_ascii=False, sort_keys=True) if verification is not None else None,
                status,
                utc_now_iso(),
                election_id,
            ),
        )

    def list_elections(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT election_id, manifest_json, tally_json, verification_json, status, created_at, updated_at
                FROM elections
                ORDER BY created_at ASC
                """
            ).fetchall()
        return [self._summarize_row(row) for row in rows]

    def create_election(self, manifest_data: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock, closing(self._connect()) as connection:
            payload = dict(manifest_data)
            if not payload.get("election_id"):
                payload["election_id"] = str(uuid.uuid4())
            manifest = manifest_from_dict(payload)
            existing = connection.execute(
                "SELECT 1 FROM elections WHERE election_id = ?",
                (manifest.election_id,),
            ).fetchone()
            if existing is not None:
                raise ValueError(f"election {manifest.election_id} already exists")
            device = VotingDevice(manifest=manifest)
            now = utc_now_iso()
            connection.execute(
                """
                INSERT INTO elections (election_id, manifest_json, state_json, tally_json, verification_json, status, created_at, updated_at)
                VALUES (?, ?, ?, NULL, NULL, ?, ?, ?)
                """,
                (
                    manifest.election_id,
                    json.dumps(manifest_to_dict(manifest), ensure_ascii=False, sort_keys=True),
                    json.dumps(device_state_to_dict(device), ensure_ascii=False, sort_keys=True),
                    "open",
                    now,
                    now,
                ),
            )
            self._write_audit_log(
                connection,
                manifest.election_id,
                "election_created",
                {"title": manifest.title, "contest_count": len(manifest.contests)},
            )
            connection.commit()
            row = self._load_election_row(connection, manifest.election_id)
        return self._detail_from_row(row)

    def get_election(self, election_id: str) -> dict[str, Any]:
        with closing(self._connect()) as connection:
            row = self._load_election_row(connection, election_id)
        return self._detail_from_row(row)

    def prepare_ballot(self, election_id: str, selections: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock, closing(self._connect()) as connection:
            row = self._load_election_row(connection, election_id)
            manifest, device = self._load_device(row)
            pending = device.prepare_ballot(selections)
            self._persist_device(connection, election_id, device, status=row["status"])
            self._write_audit_log(
                connection,
                election_id,
                "ballot_prepared",
                {"ballot_id": pending.ballot_id, "sequence_no": pending.sequence_no},
            )
            connection.commit()
        return {
            "ballot_id": pending.ballot_id,
            "sequence_no": pending.sequence_no,
            "confirmation_code": pending.confirmation_code,
            "identifier_hash": pending.identifier_hash,
            "commitment": pending.commitment,
            "proof": dict(pending.proof),
            "contest_totals": manifest.contest_totals(pending.vector),
            "status": "pending",
        }

    def cast_ballot(self, election_id: str, ballot_id: str) -> dict[str, Any]:
        with self._lock, closing(self._connect()) as connection:
            row = self._load_election_row(connection, election_id)
            _, device = self._load_device(row)
            entry = device.cast_ballot(ballot_id)
            self._persist_device(connection, election_id, device, status=row["status"])
            self._write_audit_log(
                connection,
                election_id,
                "ballot_cast",
                {"ballot_id": ballot_id, "sequence_no": entry.sequence_no},
            )
            connection.commit()
        return {
            "ballot_id": entry.ballot_id,
            "sequence_no": entry.sequence_no,
            "status": entry.status,
            "confirmation_code": entry.confirmation_code,
        }

    def challenge_ballot(self, election_id: str, ballot_id: str) -> dict[str, Any]:
        with self._lock, closing(self._connect()) as connection:
            row = self._load_election_row(connection, election_id)
            _, device = self._load_device(row)
            entry = device.challenge_ballot(ballot_id)
            self._persist_device(connection, election_id, device, status=row["status"])
            self._write_audit_log(
                connection,
                election_id,
                "ballot_challenged",
                {"ballot_id": ballot_id, "sequence_no": entry.sequence_no},
            )
            connection.commit()
        return {
            "ballot_id": entry.ballot_id,
            "sequence_no": entry.sequence_no,
            "status": entry.status,
            "opening": {
                "vector": list(entry.opening.vector) if entry.opening else None,
                "randomness": entry.opening.randomness if entry.opening else None,
                "previous_confirmation_code": entry.opening.previous_confirmation_code if entry.opening else None,
            },
        }

    def tally_election(self, election_id: str) -> dict[str, Any]:
        with self._lock, closing(self._connect()) as connection:
            row = self._load_election_row(connection, election_id)
            _, device = self._load_device(row)
            tally = device.tally()
            tally_payload = tally_to_dict(tally)
            self._persist_device(connection, election_id, device, status="tallied", tally=tally_payload)
            self._write_audit_log(
                connection,
                election_id,
                "election_tallied",
                {"cast_ballot_count": tally.cast_ballot_count},
            )
            connection.commit()
        return tally_payload

    def verify_election(self, election_id: str) -> dict[str, Any]:
        with self._lock, closing(self._connect()) as connection:
            row = self._load_election_row(connection, election_id)
            manifest, device = self._load_device(row)
            tally_json = row["tally_json"]
            if tally_json is None:
                tally = device.tally()
                tally_payload = tally_to_dict(tally)
                self._persist_device(connection, election_id, device, status="tallied", tally=tally_payload)
            else:
                tally = tally_from_dict(json.loads(tally_json))
                tally_payload = tally_to_dict(tally)
            verifier = ElectionVerifier(manifest=manifest, commitment_context=device.commitment_context)
            report = verifier.verify(device.record, tally)
            verification_payload = verification_to_dict(report)
            self._persist_device(
                connection,
                election_id,
                device,
                status="verified" if report.success else row["status"],
                tally=tally_payload,
                verification=verification_payload,
            )
            self._write_audit_log(
                connection,
                election_id,
                "election_verified",
                {"success": report.success},
            )
            connection.commit()
        return verification_payload

    def get_record(self, election_id: str) -> dict[str, Any]:
        with closing(self._connect()) as connection:
            row = self._load_election_row(connection, election_id)
            _, device = self._load_device(row)
        entries = [
            {
                "sequence_no": entry.sequence_no,
                "ballot_id": entry.ballot_id,
                "status": entry.status,
                "identifier_hash": entry.identifier_hash,
                "commitment": entry.commitment,
                "confirmation_code": entry.confirmation_code,
                "proof": dict(entry.proof),
                "opening": None
                if entry.opening is None
                else {
                    "vector": list(entry.opening.vector),
                    "randomness": entry.opening.randomness,
                    "previous_confirmation_code": entry.opening.previous_confirmation_code,
                },
            }
            for entry in device.record.entries
        ]
        return {
            "election_id": election_id,
            "entries": entries,
            "cast_ballot_count": len(device.record.cast_entries()),
            "challenged_ballot_count": len(device.record.challenge_entries()),
            "pending_ballot_count": len(device.pending_ballots),
        }

    def get_audit_logs(self, election_id: str) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            self._load_election_row(connection, election_id)
            rows = connection.execute(
                """
                SELECT id, event_type, payload_json, created_at
                FROM audit_logs
                WHERE election_id = ?
                ORDER BY id ASC
                """,
                (election_id,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "event_type": row["event_type"],
                "payload": json.loads(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def _detail_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        manifest, device = self._load_device(row)
        tally = json.loads(row["tally_json"]) if row["tally_json"] else None
        verification = json.loads(row["verification_json"]) if row["verification_json"] else None
        return {
            "election_id": row["election_id"],
            "title": manifest.title,
            "status": row["status"],
            "manifest": manifest_to_dict(manifest),
            "cast_ballot_count": len(device.record.cast_entries()),
            "challenged_ballot_count": len(device.record.challenge_entries()),
            "pending_ballot_count": len(device.pending_ballots),
            "has_tally": tally is not None,
            "has_verification": verification is not None,
            "tally": tally,
            "verification": verification,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def _summarize_row(self, row: sqlite3.Row) -> dict[str, Any]:
        manifest = manifest_from_dict(json.loads(row["manifest_json"]))
        verification = json.loads(row["verification_json"]) if row["verification_json"] else None
        tally = json.loads(row["tally_json"]) if row["tally_json"] else None
        return {
            "election_id": row["election_id"],
            "title": manifest.title,
            "status": row["status"],
            "has_tally": tally is not None,
            "has_verification": verification is not None,
            "verification_success": None if verification is None else bool(verification["success"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
