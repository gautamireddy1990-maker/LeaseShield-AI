"""FastAPI application and 24-hour temporary-file cleanup task."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import UPLOAD_DIR, router
from backend.api.payments import router as payments_router

logger = logging.getLogger(__name__)
CLEANUP_INTERVAL_SECONDS = 60 * 60
RETENTION = timedelta(hours=24)


def purge_expired_files(directory: Path = UPLOAD_DIR) -> int:
    """Delete files in the app's upload/temp directory older than 24 hours."""
    cutoff = datetime.now().timestamp() - RETENTION.total_seconds()
    deleted = 0
    directory.mkdir(parents=True, exist_ok=True)
    for path in directory.iterdir():
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
                deleted += 1
            elif path.is_dir() and path.stat().st_mtime < cutoff:
                # Only remove old directories within our dedicated temp area.
                import shutil

                shutil.rmtree(path)
                deleted += 1
        except OSError:
            logger.exception("Unable to remove expired temporary path %s", path)
    return deleted


async def _cleanup_loop() -> None:
    while True:
        try:
            count = purge_expired_files()
            if count:
                logger.info("Removed %d expired LeaseShield temporary paths", count)
        except Exception:
            logger.exception("LeaseShield cleanup pass failed")
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Purge immediately on startup, then continue hourly.
    purge_expired_files()
    cleanup_task = asyncio.create_task(_cleanup_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="LeaseShield AI", version="0.1.0", lifespan=lifespan)
allowed_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(payments_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
