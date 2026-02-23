from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import WebSocket

from models import Car, Location, Rental, User


class DataStore:
    def __init__(self) -> None:
        self.users: Dict[str, User] = {}
        self.cars: Dict[str, Car] = {}
        self.rentals: Dict[str, Rental] = {}
        self.client_connections: Dict[str, WebSocket] = {}
        self.user_by_client: Dict[str, str] = {}
        self.pending_car_queries: Dict[str, Any] = {}

    def seed_cars(self) -> None:
        base_lat = 47.16
        base_lon = 27.59
        for i in range(6):
            vin = f"VIN{i+1:04d}"
            delta_lat = random.uniform(-0.01, 0.01)
            delta_lon = random.uniform(-0.01, 0.01)
            car = Car(
                vin=vin,
                location=Location(lat=base_lat + delta_lat, lon=base_lon + delta_lon),
                status="AVAILABLE",
                rentedByUserId=None,
                telematicsClientId=None,
            )
            self.cars[vin] = car

    def set_connection(self, client_id: str, websocket: WebSocket) -> None:
        self.client_connections[client_id] = websocket

    def remove_connection(self, client_id: str) -> None:
        self.client_connections.pop(client_id, None)
        self.user_by_client.pop(client_id, None)

    def create_user(self, payload: dict, client_id: str) -> User:
        user_id = str(uuid4())
        user = User(
            id=user_id,
            fullName=payload["fullName"],
            email=payload["email"],
            age=payload["age"],
            drivingLicenseNumber=payload["drivingLicenseNumber"],
            paymentToken=payload["paymentToken"],
            licenseValidUntil=payload["licenseValidUntil"],
            location=Location(**payload["location"]),
            activeRentalVin=None,
            clientId=client_id,
        )
        self.users[user_id] = user
        self.user_by_client[client_id] = user_id
        return user

    def get_user_by_client(self, client_id: str) -> Optional[User]:
        user_id = self.user_by_client.get(client_id)
        if not user_id:
            return None
        return self.users.get(user_id)

    def update_user_location(self, client_id: str, location: dict) -> None:
        user = self.get_user_by_client(client_id)
        if not user:
            return
        user.location = Location(**location)
        self.users[user.id] = user

    def start_rental(self, user: User, car: Car) -> Rental:
        rental_id = str(uuid4())
        started_at = datetime.now(timezone.utc).isoformat()
        rental = Rental(id=rental_id, userId=user.id, vin=car.vin, startedAt=started_at, endedAt=None)
        self.rentals[rental_id] = rental
        user.activeRentalVin = car.vin
        car.status = "RENTED"
        car.rentedByUserId = user.id
        return rental

    def finalize_rental(self, rental: Rental) -> Rental:
        rental.endedAt = datetime.now(timezone.utc).isoformat()
        self.rentals[rental.id] = rental
        return rental

    def get_rental_by_user(self, user: User) -> Optional[Rental]:
        if not user.activeRentalVin:
            return None
        for rental in self.rentals.values():
            if rental.userId == user.id and rental.vin == user.activeRentalVin and rental.endedAt is None:
                return rental
        return None
