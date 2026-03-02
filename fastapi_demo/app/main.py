"""SAPL FastAPI Demo -- main application entry point.

Configures SAPL PEP integration with all 7 constraint handler types
and includes routers for basic, constraint, content filtering, and
streaming enforcement demos.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from sapl_fastapi.config import SaplConfig
from sapl_fastapi.dependencies import cleanup_sapl, configure_sapl, register_constraint_handler

from app.handlers.audit_trail import AuditTrailHandler
from app.handlers.cap_transfer import CapTransferHandler
from app.handlers.classification_filter import ClassificationFilterHandler
from app.handlers.enrich_error import EnrichErrorHandler
from app.handlers.inject_timestamp import InjectTimestampHandler
from app.handlers.log_access import LogAccessHandler
from app.handlers.log_stream_event import LogStreamEventHandler
from app.handlers.notify_on_error import NotifyOnErrorHandler
from app.handlers.redact_fields import RedactFieldsHandler

from app.routers import basic, constraints, services, streaming

log = structlog.get_logger()

load_dotenv()

# Module-level handler instance so the audit-log endpoint can access it
audit_trail_handler = AuditTrailHandler()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: configure SAPL and register constraint handlers."""
    config = SaplConfig(
        base_url=os.getenv("SAPL_PDP_URL", "http://localhost:8443"),
        allow_insecure_connections=True,
    )
    configure_sapl(config)

    # 1. RunnableConstraintHandlerProvider (ON_DECISION)
    register_constraint_handler(LogAccessHandler(), "runnable")

    # 2. ConsumerConstraintHandlerProvider
    register_constraint_handler(audit_trail_handler, "consumer")

    # 3. MappingConstraintHandlerProvider
    register_constraint_handler(RedactFieldsHandler(), "mapping")

    # 4. FilterPredicateConstraintHandlerProvider
    register_constraint_handler(ClassificationFilterHandler(), "filter_predicate")

    # 5. MethodInvocationConstraintHandlerProvider (inject timestamp)
    register_constraint_handler(InjectTimestampHandler(), "method_invocation")

    # 5b. MethodInvocationConstraintHandlerProvider (cap transfer amount)
    register_constraint_handler(CapTransferHandler(), "method_invocation")

    # 6. ErrorHandlerProvider
    register_constraint_handler(NotifyOnErrorHandler(), "error_handler")

    # 7. ErrorMappingConstraintHandlerProvider
    register_constraint_handler(EnrichErrorHandler(), "error_mapping")

    # 8. ConsumerConstraintHandlerProvider (streaming log)
    register_constraint_handler(LogStreamEventHandler(), "consumer")

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
app.include_router(services.router)


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
