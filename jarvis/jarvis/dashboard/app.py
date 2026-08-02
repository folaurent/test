"""Dashboard v0 — FastAPI avec sections imposées.

Sections : Live, Agents, Runs, Gaps, Violations, Reflections, Evals, Health,
Data, Budget, Builds, Zones, Campaigns, Conversations, Compliance, Voice.

Phase 1.1 : stubs JSON + auth Bearer. UI HTML arrive Phase 1.2.
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from jarvis.core.budget import BudgetManager
from jarvis.core.config import Settings, get_settings
from jarvis.security.kill_switch import KillSwitch


def _require_auth(request: Request, settings: Settings) -> None:
    expected = settings.dashboard_auth_token.get_secret_value()
    if not expected:
        return  # dev mode
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer ") or header[7:] != expected:
        raise HTTPException(status_code=401, detail="unauthorized")


def create_app(budget: BudgetManager | None = None) -> FastAPI:
    app = FastAPI(title="Jarvis Dashboard v0", version="0.1.0")
    settings = get_settings()
    kill = KillSwitch()

    def auth_dep(request: Request) -> None:
        _require_auth(request, settings)

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse(
            {
                "ok": True,
                "kill_switch": kill.engaged(),
                "env": settings.env,
                "dry_run": settings.dry_run,
            }
        )

    @app.get("/api/live", dependencies=[Depends(auth_dep)])
    async def live() -> dict:
        return {"runs_active": 0, "messages_pending": 0, "agents_online": 0}

    @app.get("/api/agents", dependencies=[Depends(auth_dep)])
    async def agents_list() -> dict:
        return {"agents": [{"name": "Jarvis", "autonomy": 1}, {"name": "Builder", "autonomy": 1}]}

    @app.get("/api/violations", dependencies=[Depends(auth_dep)])
    async def violations() -> dict:
        return {"scope_violations": 0, "voice_lint_blocks": 0, "injection_attempts": 0}

    @app.get("/api/budget", dependencies=[Depends(auth_dep)])
    async def budget_snap() -> dict:
        if budget is None:
            return {"note": "budget manager non initialisé (Phase 1.1 stub)"}
        return budget.snapshot()

    @app.get("/api/zones", dependencies=[Depends(auth_dep)])
    async def zones_stats() -> dict:
        from jarvis.voice.zones import all_zones

        return {
            "zones": [
                {"code": z.code, "formality": z.formality, "active": z.code == "FR"}
                for z in all_zones()
            ]
        }

    @app.get("/api/voice_health", dependencies=[Depends(auth_dep)])
    async def voice_health() -> dict:
        return {
            "messages_scanned_24h": 0,
            "block_rate": 0.0,
            "banned_phrases_detected_24h": 0,
        }

    @app.get("/api/compliance", dependencies=[Depends(auth_dep)])
    async def compliance_status() -> dict:
        return {"zones": {"FR": {"registre_art30": False, "dpa_anthropic": False}}}

    @app.get("/api/builds", dependencies=[Depends(auth_dep)])
    async def builds() -> dict:
        return {"history": []}

    @app.get("/api/conversations", dependencies=[Depends(auth_dep)])
    async def conversations() -> dict:
        return {"active": 0, "avg_score": 0.0, "awaiting_human": 0}

    return app
