import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select

from app.config import settings

logger = logging.getLogger("uvicorn.error")

SYNC_INTERVAL_MINUTES = 1


async def _auto_sync_loop():
    """Periodically sync all connected connectors."""
    import datetime

    from app.api.ingest import _run_ingestion
    from app.database import get_session_ctx
    from app.models.connector import Connector

    while True:
        await asyncio.sleep(SYNC_INTERVAL_MINUTES * 60)
        logger.info("Auto-sync: checking for connectors to sync")
        try:
            async with get_session_ctx() as db:
                # Unstick connectors that have been "syncing" for over 5 minutes
                cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=5)
                result = await db.execute(
                    select(Connector).where(
                        Connector.status == "syncing",
                    )
                )
                for stuck in result.scalars().all():
                    logger.warning(
                        f"Auto-sync: resetting stuck connector "
                        f"{stuck.provider}/{stuck.user_id} to 'error'"
                    )
                    stuck.status = "error"
                    stuck.error_message = "Sync timed out"
                await db.commit()

                result = await db.execute(
                    select(Connector).where(
                        Connector.status.in_(["connected", "ready"])
                    )
                )
                connectors = result.scalars().all()

            for conn in connectors:
                logger.info(f"Auto-sync: triggering {conn.provider} for user {conn.user_id}")
                asyncio.create_task(
                    _run_ingestion(str(conn.user_id), conn.provider)
                )
        except Exception:
            logger.exception("Auto-sync loop error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_auto_sync_loop())
    yield
    task.cancel()


app = FastAPI(title="Connective", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from app.api import auth, connectors, chat, scan, ingest  # noqa: E402

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(connectors.router, prefix="/api/connectors", tags=["connectors"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(scan.router, prefix="/api/scan", tags=["scan"])
app.include_router(ingest.router, prefix="/api/ingest", tags=["ingest"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
