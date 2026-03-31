from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from middleware_control_plane.config import load_config
from middleware_control_plane.engine import ControlPlaneEngine

app = FastAPI(title="Middleware Control Plane API", version="0.1.0")


class PlanRequest(BaseModel):
    config_path: str
    dry_run: Optional[bool] = None


class ScaleRequest(BaseModel):
    config_path: str
    target_count: Optional[int] = Field(default=None, ge=0, le=100)
    dry_run: Optional[bool] = None
    reason: str = "manual_api_request"


class ConfigRequest(BaseModel):
    config_path: str


class BenchmarkRequest(BaseModel):
    url: str
    concurrency: int = Field(default=5, ge=1, le=500)
    requests: int = Field(default=100, ge=1, le=100000)
    timeout_seconds: float = Field(default=5.0, gt=0.0, le=120.0)


def _load_engine(config_path: str, dry_run: Optional[bool] = None) -> ControlPlaneEngine:
    path = Path(config_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Config not found: {config_path}")
    cfg = load_config(str(path))
    if dry_run is not None:
        cfg.dry_run = dry_run
    return ControlPlaneEngine(cfg)


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True}


@app.post("/config/resolved")
def resolved_config(request: ConfigRequest) -> dict:
    engine = _load_engine(request.config_path)
    return engine.cfg.to_dict()


@app.post("/plan")
def plan(request: PlanRequest) -> dict:
    engine = _load_engine(request.config_path, request.dry_run)
    state, snapshot, probes, decision = engine.plan()
    return {
        "state": asdict(state),
        "snapshot": snapshot.to_dict(),
        "decision": asdict(decision),
        "probes": [asdict(p) for p in probes],
        "dry_run": engine.cfg.dry_run,
    }


@app.get("/status")
def status(config_path: str, dry_run: Optional[bool] = None) -> dict:
    engine = _load_engine(config_path, dry_run)
    state, snapshot, probes, decision = engine.plan()
    return {
        "platform": engine.cfg.platform,
        "snapshot": snapshot.to_dict(),
        "decision": asdict(decision),
        "probes": [asdict(p) for p in probes],
        "state": asdict(state),
        "dry_run": engine.cfg.dry_run,
    }


@app.post("/scale")
def scale(request: ScaleRequest) -> dict:
    engine = _load_engine(request.config_path, request.dry_run)
    if request.target_count is None:
        rc = engine.run_once()
        return {"return_code": rc, "mode": "policy_driven", "dry_run": engine.cfg.dry_run}
    return engine.scale_to(request.target_count, reason=request.reason)
