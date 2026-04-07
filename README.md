# VotingSystem

A research-oriented verifiable voting project inspired by three papers in this repository:

- `2026-613.pdf` — Haechi: a keyless, commitment-based, in-person verifiable election design
- `2026-565.pdf` — Zeeperio: succinct proof generation and automated verification for election audits
- `2026-545.pdf` — Aggios: aggregator-based voting with partition proofs for scalable public verification

This project currently implements a runnable Python framework based primarily on the `2026-613` design and keeps explicit extension points for integrating ideas from `2026-565` and `2026-545`.

## Project Status

Current status: `working prototype`

What is already available:

- end-to-end demo flow
- election manifest and ballot encoding
- Pedersen-style vector commitment layer
- cast / challenge workflow
- public election record
- aggregate tally opening and verification
- extension interfaces for future proof backends and aggregation backends

What is not yet production-grade:

- real zero-knowledge proof backend
- service deployment layer
- database persistence
- user-facing web UI
- on-chain or smart-contract verifier
- aggregator workflow from Aggios

So this repository should be understood as a strong architectural prototype, not a final election product.

## Why This Repository Exists

The goal of this project is to evolve from a paper-study prototype into a competition-ready information security project with:

- a clear cryptographic story
- a verifiable end-to-end voting workflow
- modular proof and verification backends
- room for system engineering, interface design, and security demonstrations

In other words, the project is designed to be a practical foundation for a serious security competition submission rather than just a one-off script.

## Core Design Choice

The current implementation uses `2026-613 / Haechi` as the system backbone because it gives the cleanest high-level architecture:

1. load an election manifest
2. collect a voter's selections on a device
3. encode the whole ballot as a vector
4. create one commitment for the whole ballot
5. generate a confirmation-code chain
6. let the voter either cast or challenge
7. publish cast ballots to a public record
8. open the aggregate commitment after voting ends
9. let public verifiers check tally consistency

This model is simpler to implement and easier to explain than starting directly from zk-SNARK tooling or aggregator-heavy workflows.

## Architecture Overview

The current codebase is organized around the following components:

- `ElectionManifest`
  Defines contests, candidates, and ballot rules.

- `VotingDevice`
  Simulates a Haechi-style polling device that prepares ballots, issues confirmation codes, supports cast/challenge, and maintains the running tally.

- `PedersenContext`
  Implements the commitment layer used for whole-ballot commitments and aggregate openings.

- `ElectionRecord`
  Stores the public election record, including cast ballots and challenged ballots.

- `ElectionVerifier`
  Verifies the confirmation-code chain, challenged openings, aggregate commitment, and tally opening.

- `Proof Backends`
  The current implementation uses placeholder proof objects so the full data flow can run end-to-end. These interfaces are intentionally pluggable.

## Repository Layout

```text
.
|-- 2026-545.pdf
|-- 2026-565.pdf
|-- 2026-613.pdf
|-- PAPER_ANALYSIS.md
|-- README.md
|-- pyproject.toml
|-- src/
|   `-- haechi_voting/
|       |-- __init__.py
|       |-- crypto.py
|       |-- demo.py
|       |-- device.py
|       |-- extensions.py
|       |-- models.py
|       |-- proofs.py
|       |-- record.py
|       `-- verifier.py
`-- tests/
    `-- test_demo_flow.py
```

## Quick Start

Requirements:

- Python `3.10+`

Run the demo from PowerShell:

```powershell
$env:PYTHONPATH = "src"
python -m haechi_voting.demo
```

Run the test suite:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

## Demo Output

The current demo simulates:

- one cast ballot
- one challenged ballot
- one additional cast ballot
- final tally publication
- public verification of the election record

Expected high-level result:

- `2` cast ballots
- `1` challenged ballot
- verification passes successfully

## Paper-to-System Mapping

### 1. Paper 613: Haechi

This paper is the current foundation of the project.

Implemented ideas:

- commitment-based whole-ballot recording
- cast-or-challenge workflow
- public election record
- aggregate commitment opening
- public tally verification

### 2. Paper 565: Zeeperio

This paper is treated as a future verification upgrade.

Planned use inside this repository:

- replace placeholder proof objects with succinct proof artifacts
- introduce separate receipt and dispute proof interfaces
- optionally add automated or on-chain verification

Current integration hook:

- `src/haechi_voting/extensions.py`

### 3. Paper 545: Aggios

This paper is treated as a future aggregation upgrade.

Planned use inside this repository:

- add aggregator roles
- support batch publication
- add inclusion acknowledgements and dispute handling
- add partition-proof-based verification for large-scale voting

Current integration hook:

- `src/haechi_voting/extensions.py`

## Security Notes

This repository currently demonstrates architecture, workflow, and commitment-based verification mechanics. It does **not** yet implement the full cryptographic security promised by the papers.

Important limitations:

- proof systems are placeholders
- there is no hardened deployment model
- there is no trusted setup management
- there is no real voter authentication subsystem
- there is no adversarial network or device model beyond basic simulation

For that reason, this repository must not be used as a real election platform.

## Development Roadmap

Recommended next steps for turning this into a competition-ready system:

1. Replace placeholder proofs with a real proof backend.
2. Add a service layer such as `FastAPI`.
3. Add persistent storage such as `SQLite` or `PostgreSQL`.
4. Build a reviewer-friendly web UI for device, administrator, and verifier roles.
5. Integrate a Zeeperio-style succinct verification backend.
6. Add an Aggios-style aggregator module for scalable batch submission.
7. Expand the test suite to include adversarial and failure scenarios.
8. Add deployment scripts, reproducible demo data, and architecture diagrams.

## Documentation

- `README.md`
  Project overview and usage guide.

- `PAPER_ANALYSIS.md`
  Detailed analysis of how the three papers map into the system architecture and how future integration should be done.

## Collaboration

Recommended team workflow:

- keep the Python framework as the main integration layer
- isolate heavy cryptographic components into separate modules or services
- use pull requests for feature branches
- treat proof backends and aggregation backends as independent subsystems

This makes it much easier for multiple teammates to collaborate without breaking the full system.

## License

No license has been added yet.

If you plan to make this repository public or collaborate across teams, adding a clear open-source or competition-compatible license should be one of the next steps.
