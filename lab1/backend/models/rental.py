from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Rental(BaseModel):
    id: str
    userId: str
    vin: str
    startedAt: str
    endedAt: Optional[str] = None
