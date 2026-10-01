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
from app.core.db import SessionLocal, describe_database, describe_timezone, init_db
from app.core.exceptions import DomainError
from app.modules.accounts.router import router as accounts_router
from app.modules.approvals.router import router as approvals_router
from app.modules.auth.router import router as auth_router
from app.modules.data.router import router as data_router
from app.modules.inventory_ledger.router import router as inventory_router
from app.modules.items_bom.router import router as items_router
from app.modules.journal_entries.router import router as journal_router
from app.modules.opening_balances.router import router as opening_router
from app.modules.payroll.router import router as payroll_router
from app.modules.production.router import router as production_router
from app.modules.purchases.router import router as purchases_router
from app.modules.reports.router import router as reports_router
from app.modules.sales.router import router as sales_router
from app.modules.settings.router import router as settings_router
from app.modules.users_roles.router import router as access_router
from app.modules.vat_tax.router import router as vat_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create tables and seed on first boot."""
    from app.core.security import using_ephemeral_secret

    if using_ephemeral_secret():
        print(
            "[auth] RPCI_JWT_SECRET is not set, so a random one was generated for "
            "this process. Sign-ins will not survive a restart. Set it on any "
            "real deployment."
        )

    # Say which database is in use. A sqlite file on a host with no persistent
    # disk means anything entered is lost when the instance restarts, which is
    # worth knowing before someone spends an afternoon testing against it. The
    # timezone is reported too: timestamps are written by the database's now(),
    # and the interface can only show the client's clock if that is UTC.
    print(f"[db] using {describe_database()}")
    print(f"[db] server timezone: {describe_timezone()}")
    init_db()
    # A brand-new database is populated according to RPCI_SEED_MODE: a standard
    # starter chart of accounts (the default), the sample workbook, or nothing.
    if settings.seed_mode == "workbook":
        from app.seed.loader import seed_if_empty

        with SessionLocal() as session:
            report = seed_if_empty(session)
            if report.seeded:
                print(f"[seed] {report.summary()}")
    elif settings.seed_mode == "fresh":
        from app.seed.starter import seed_starter

        with SessionLocal() as session:
            added = seed_starter(session)
            session.commit()
            if added:
                print(f"[seed] starter chart of accounts: {added} accounts")

    # Seed configurable settings defaults regardless of workbook data.
    from app.modules.settings import service as settings_service

    with SessionLocal() as session:
        settings_service.seed_defaults(session)
        session.commit()

    # Repair demo accounts that predate passwords, so a database upgraded from
    # an earlier version can still be signed into.
    from app.seed.loader import ensure_demo_users

    with SessionLocal() as session:
        repaired = ensure_demo_users(session)
        session.commit()
        if repaired:
            print(f"[seed] gave a demo password to: {', '.join(repaired)}")

    yield


app = FastAPI(
    title="RPCI Cloud Accounting & Production ERP",
    version="1.0.0",
    description=(
        "Double-entry accounting and production for a resin manufacturer: chart of "
        "accounts, opening balances, production runs, sales, payroll, and live reports."
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
    auth_router,
    accounts_router,
    opening_router,
    journal_router,
    items_router,
    inventory_router,
    production_router,
    payroll_router,
    sales_router,
    purchases_router,
    reports_router,
    vat_router,
    settings_router,
    access_router,
    approvals_router,
    data_router,
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

    @app.get("/favicon.svg", include_in_schema=False)
    def favicon() -> FileResponse:
        """Serve the site icon, copied from the frontend's public directory."""
        return FileResponse(_FRONTEND_DIST / "favicon.svg")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str) -> FileResponse:
        """Return the single-page app entry point for any non-API route."""
        return FileResponse(_FRONTEND_DIST / "index.html")
