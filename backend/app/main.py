"""FastAPI application entry point: routers, error mapping, startup seeding."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.db import SessionLocal, init_db
from app.core.exceptions import DomainError
from app.modules.accounts.router import router as accounts_router
from app.modules.demo.router import router as demo_router
from app.modules.inventory_ledger.router import router as inventory_router
from app.modules.items_bom.router import router as items_router
from app.modules.journal_entries.router import router as journal_router
from app.modules.opening_balances.router import router as opening_router
from app.modules.production.router import router as production_router
from app.modules.purchases.router import router as purchases_router
from app.modules.reports.router import router as reports_router
from app.modules.sales.router import router as sales_router
from app.modules.settings.router import router as settings_router
from app.modules.users_roles.router import router as access_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create tables and seed demo data on first boot."""
    init_db()
    if settings.auto_seed:
        from app.seed.loader import seed_if_empty

        with SessionLocal() as session:
            report = seed_if_empty(session)
            if report.seeded:
                print(f"[seed] {report.summary()}")

    # Seed configurable settings defaults regardless of workbook data.
    from app.modules.settings import service as settings_service

    with SessionLocal() as session:
        settings_service.seed_defaults(session)
        session.commit()

    yield


app = FastAPI(
    title="RPCI Cloud Accounting & Production ERP (Demo)",
    version="0.1.0",
    description=(
        "Demo build seeded from the client's own workbook: chart of accounts, "
        "opening balances, production runs, sales, and live reports."
    ),
    lifespan=lifespan,
)

_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    # No cookies are used (the acting role travels in a header), so credentials
    # stay off. That keeps the wildcard origin valid for the public demo.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Map business-rule violations onto their HTTP status codes."""
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


@app.get("/healthz", tags=["meta"])
def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


for router in (
    accounts_router,
    opening_router,
    journal_router,
    items_router,
    inventory_router,
    production_router,
    sales_router,
    purchases_router,
    reports_router,
    settings_router,
    access_router,
    demo_router,
):
    app.include_router(router, prefix="/api")


# Serve the built frontend from the same service, so one instance hosts both the
# interface and the API. The asset directory is optional: during development the
# Vite dev server proxies to this API instead, so a missing build is not fatal.
_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if _FRONTEND_DIST.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=_FRONTEND_DIST / "assets"),
        name="assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str) -> FileResponse:
        """Return the single-page app entry point for any non-API route."""
        return FileResponse(_FRONTEND_DIST / "index.html")
