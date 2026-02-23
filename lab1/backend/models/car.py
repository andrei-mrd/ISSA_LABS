from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from .user import Location


class Car(BaseModel):
    vin: str
    location: Location
    status: str = "AVAILABLE"
    rentedByUserId: Optional[str] = None
    telematicsClientId: Optional[str] = None
