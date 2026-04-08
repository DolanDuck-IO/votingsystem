from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .service import VotingService


class ContestCreateRequest(BaseModel):
    contest_id: str
    title: str
    candidates: list[str]
    min_selections: int = 0
    max_selections: int = 1
    allowed_values: list[int] = Field(default_factory=lambda: [0, 1])


class ElectionCreateRequest(BaseModel):
    election_id: str | None = None
    title: str
    contests: list[ContestCreateRequest]
    metadata: dict[str, Any] = Field(default_factory=dict)


class BallotPrepareRequest(BaseModel):
    selections: dict[str, list[str]]


def create_app(database_path: str | Path = "data/voting.db") -> FastAPI:
    static_dir = Path(__file__).parent / "static"
    app = FastAPI(
        title="VotingSystem API",
        version="0.2.0",
        description="FastAPI + SQLite demo service built on the Haechi-inspired voting framework.",
    )
    service = VotingService(database_path=database_path)
    app.state.voting_service = service
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/app", response_class=FileResponse)
    def frontend() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/")
    def index() -> dict[str, Any]:
        return {
            "name": "VotingSystem API",
            "status": "running",
            "endpoints": [
                "/app",
                "/health",
                "/elections",
                "/elections/{election_id}",
                "/elections/{election_id}/ballots/prepare",
                "/elections/{election_id}/ballots/{ballot_id}/cast",
                "/elections/{election_id}/ballots/{ballot_id}/challenge",
                "/elections/{election_id}/tally",
                "/elections/{election_id}/record",
                "/elections/{election_id}/verify",
                "/elections/{election_id}/audit-logs",
            ],
        }

    @app.get("/elections")
    def list_elections() -> list[dict[str, Any]]:
        return service.list_elections()

    @app.post("/elections")
    def create_election(request: ElectionCreateRequest) -> dict[str, Any]:
        try:
            return service.create_election(request.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/elections/{election_id}")
    def get_election(election_id: str) -> dict[str, Any]:
        try:
            return service.get_election(election_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/elections/{election_id}/ballots/prepare")
    def prepare_ballot(election_id: str, request: BallotPrepareRequest) -> dict[str, Any]:
        try:
            return service.prepare_ballot(election_id, request.selections)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/elections/{election_id}/ballots/{ballot_id}/cast")
    def cast_ballot(election_id: str, ballot_id: str) -> dict[str, Any]:
        try:
            return service.cast_ballot(election_id, ballot_id)
        except KeyError as exc:
            message = str(exc)
            status_code = 404 if "unknown election" in message else 400
            raise HTTPException(status_code=status_code, detail=message) from exc

    @app.post("/elections/{election_id}/ballots/{ballot_id}/challenge")
    def challenge_ballot(election_id: str, ballot_id: str) -> dict[str, Any]:
        try:
            return service.challenge_ballot(election_id, ballot_id)
        except KeyError as exc:
            message = str(exc)
            status_code = 404 if "unknown election" in message else 400
            raise HTTPException(status_code=status_code, detail=message) from exc

    @app.post("/elections/{election_id}/tally")
    def tally_election(election_id: str) -> dict[str, Any]:
        try:
            return service.tally_election(election_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/elections/{election_id}/record")
    def get_record(election_id: str) -> dict[str, Any]:
        try:
            return service.get_record(election_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/elections/{election_id}/verify")
    def verify_election(election_id: str) -> dict[str, Any]:
        try:
            return service.verify_election(election_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/elections/{election_id}/audit-logs")
    def get_audit_logs(election_id: str) -> list[dict[str, Any]]:
        try:
            return service.get_audit_logs(election_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return app
