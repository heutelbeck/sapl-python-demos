"""SAPL FastAPI Demo -- main application entry point.

Configures SAPL PEP integration with a set of `ConstraintHandlerProvider`
implementations covering DECISION runners, INPUT/OUTPUT/ERROR mappers and
consumers, and registers routers for basic, constraint, content filtering,
and streaming enforcement demos.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from sapl_fastapi import SaplConfig
from sapl_fastapi.dependencies import cleanup_sapl, configure_sapl, register_provider

from app.handlers.audit_trail import AuditTrailHandler
from app.handlers.cap_transfer import CapTransferHandler
from app.handlers.classification_filter import ClassificationFilterHandler
from app.handlers.enrich_error import EnrichErrorHandler
from app.handlers.inject_timestamp import InjectTimestampHandler
from app.handlers.log_access import LogAccessHandler
from app.handlers.log_stream_event import LogStreamEventHandler
from app.handlers.notify_on_error import NotifyOnErrorHandler
from app.handlers.redact_fields import RedactFieldsHandler

from app.routers import basic, constraints, streaming

log = structlog.get_logger()

load_dotenv()

# Module-level handler instance so the audit-log endpoint can access it
audit_trail_handler = AuditTrailHandler()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: configure SAPL and register constraint handlers."""
    config = SaplConfig(
        base_url=os.getenv("SAPL_PDP_URL", "http://localhost:8443"),
    )
    configure_sapl(config)

    register_provider(LogAccessHandler())
    register_provider(audit_trail_handler)
    register_provider(RedactFieldsHandler())
    register_provider(ClassificationFilterHandler())
    register_provider(InjectTimestampHandler())
    register_provider(CapTransferHandler())
    register_provider(NotifyOnErrorHandler())
    register_provider(LogStreamEventHandler())
    register_provider(EnrichErrorHandler())

    log.info("SAPL configured with all constraint handlers registered")

    yield

    await cleanup_sapl()
    log.info("SAPL resources cleaned up")


app = FastAPI(
    title="SAPL FastAPI Demo",
    description="Demo API with SAPL policy enforcement",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(basic.router)
app.include_router(constraints.router)
app.include_router(streaming.router)


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    """Convert RuntimeError to 500 with the error message in the response body."""
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Health check / root endpoint."""
    return {"status": "ok", "application": "SAPL FastAPI Demo"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "3000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
