from __future__ import annotations

from dataclasses import dataclass, field

from .crypto import (
    PedersenContext,
    hash_hex,
    make_confirmation_code,
    make_identifier_hash,
    manifest_fingerprint,
)
from .models import ElectionManifest, TallyReport, VerificationReport
from .proofs import (
    PlaceholderTallyProofSystem,
    PlaceholderWellFormednessProofSystem,
    TallyProofSystem,
    WellFormednessProofSystem,
)
from .record import ElectionRecord


@dataclass
class ElectionVerifier:
    manifest: ElectionManifest
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
        self.confirmation_seed = hash_hex("confirmation-seed", self.base_hash)

    def verify(self, record: ElectionRecord, tally_report: TallyReport) -> VerificationReport:
        checks: dict[str, bool] = {}
        errors: list[str] = []

        running_confirmation_code = self.confirmation_seed
        id_hash_ok = True
        confirmation_chain_ok = True
        proofs_ok = True
        challenged_openings_ok = True

        for entry in record.entries:
            expected_id_hash = make_identifier_hash(self.base_hash, entry.ballot_id)
            if entry.identifier_hash != expected_id_hash:
                id_hash_ok = False
                errors.append(f"ballot {entry.ballot_id} has incorrect identifier hash")

            expected_conf = make_confirmation_code(
                entry.identifier_hash,
                entry.commitment,
                running_confirmation_code,
            )
            if entry.confirmation_code != expected_conf:
                confirmation_chain_ok = False
                errors.append(f"ballot {entry.ballot_id} breaks the confirmation-code chain")

            if not self.well_formedness_proof_system.verify(
                self.manifest,
                entry.commitment,
                entry.proof,
            ):
                proofs_ok = False
                errors.append(f"ballot {entry.ballot_id} has an invalid well-formedness proof")

            if entry.status == "challenged":
                if entry.opening is None:
                    challenged_openings_ok = False
                    errors.append(f"challenged ballot {entry.ballot_id} is missing its opening")
                elif not self.commitment_context.verify_opening(
                    entry.commitment,
                    entry.opening.vector,
                    entry.opening.randomness,
                ):
                    challenged_openings_ok = False
                    errors.append(f"challenged ballot {entry.ballot_id} does not open correctly")

            running_confirmation_code = entry.confirmation_code

        cast_commitments = [entry.commitment for entry in record.cast_entries()]
        aggregate_commitment = self.commitment_context.aggregate_commitments(cast_commitments)
        aggregate_commitment_ok = aggregate_commitment == tally_report.aggregate_commitment
        if not aggregate_commitment_ok:
            errors.append("aggregate commitment does not match the product of cast commitments")

        tally_opening_ok = self.commitment_context.verify_opening(
            tally_report.aggregate_commitment,
            tally_report.aggregate_vector,
            tally_report.aggregate_randomness,
        )
        if not tally_opening_ok:
            errors.append("aggregate tally opening is invalid")

        tally_vector_shape_ok = len(tally_report.aggregate_vector) == self.manifest.total_slots
        if not tally_vector_shape_ok:
            errors.append("aggregate tally vector has incorrect length")

        tally_decode_ok = True
        try:
            decoded = self.manifest.decode_vector(tally_report.aggregate_vector)
        except ValueError:
            tally_decode_ok = False
            decoded = {}
            errors.append("aggregate tally vector could not be decoded against the manifest")

        tally_mapping_ok = decoded == dict(tally_report.tally_by_contest)
        if not tally_mapping_ok:
            errors.append("published tally map is inconsistent with aggregate vector")

        tally_proof_ok = self.tally_proof_system.verify(self.manifest, tally_report)
        if not tally_proof_ok:
            errors.append("tally proof is invalid")

        checks["identifier_hashes"] = id_hash_ok
        checks["confirmation_chain"] = confirmation_chain_ok
        checks["ballot_proofs"] = proofs_ok
        checks["challenged_openings"] = challenged_openings_ok
        checks["aggregate_commitment"] = aggregate_commitment_ok
        checks["tally_opening"] = tally_opening_ok
        checks["tally_vector_shape"] = tally_vector_shape_ok
        checks["tally_decode"] = tally_decode_ok
        checks["tally_mapping"] = tally_mapping_ok
        checks["tally_proof"] = tally_proof_ok

        success = all(checks.values())
        return VerificationReport(success=success, checks=checks, errors=tuple(errors))
