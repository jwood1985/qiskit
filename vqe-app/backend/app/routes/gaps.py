"""GAPS router — serve the GAPS.md content for the in-app dashboard."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/gaps", tags=["gaps"])

# vqe-app/backend/app/routes/gaps.py → parents[3] = vqe-app/
_GAPS_PATH = Path(__file__).resolve().parents[3] / "GAPS.md"


@router.get("")
def read_gaps() -> dict[str, str]:
    if not _GAPS_PATH.exists():
        logger.error("GAPS.md not found at %s", _GAPS_PATH)
        raise HTTPException(status_code=404, detail="GAPS.md not found")
    return {"markdown": _GAPS_PATH.read_text(encoding="utf-8")}
