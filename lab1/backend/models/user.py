from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Location(BaseModel):
    lat: float
    lon: float


class User(BaseModel):
    id: str
    fullName: str
    email: str
    age: int
    drivingLicenseNumber: str
    paymentToken: str
    licenseValidUntil: str
    location: Location
    activeRentalVin: Optional[str] = None
    clientId: Optional[str] = None
