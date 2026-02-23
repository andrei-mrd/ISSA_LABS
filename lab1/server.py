"""Minimal car sharing backend exposing the flows from the assignment.

Run with `python server.py` and use the companion client, curl, or the bundled
web frontend at `/app` to hit the API. The service keeps everything in memory
for simplicity.
"""
from dataclasses import dataclass, field
from typing import Dict, Optional
from uuid import uuid4

from flask import Flask, jsonify, request, send_from_directory


app = Flask(__name__, static_folder="static", static_url_path="/static")


# --- Data models -----------------------------------------------------------

@dataclass
class ClientProfile:
    name: str
    email: str
    driver_license: str
    payment_method: str
    pin: str  # demo-only; do not store PINs like this in real systems


@dataclass
class CarState:
    locked: bool = True
    doors_closed: bool = True
    lights_off: bool = True

    def as_dict(self) -> Dict[str, bool]:
        return {
            "locked": self.locked,
            "doors_closed": self.doors_closed,
            "lights_off": self.lights_off,
        }


@dataclass
class Car:
    vin: str
    model: str
    location: str
    telematics: CarState = field(default_factory=CarState)
    rented_by: Optional[str] = None

    def availability(self) -> str:
        if self.rented_by:
            return f"rented_by_{self.rented_by}"
        return "available"


# --- In-memory stores ------------------------------------------------------

clients: Dict[str, ClientProfile] = {}
sessions: Dict[str, str] = {}  # token -> email
cars: Dict[str, Car] = {
    "VIN-001": Car(vin="VIN-001", model="Hatchback", location="Bucharest"),
    "VIN-002": Car(vin="VIN-002", model="SUV", location="Cluj"),
    "VIN-003": Car(vin="VIN-003", model="Sedan", location="Timisoara"),
}


# --- Helpers ---------------------------------------------------------------

def require_fields(payload: Dict, fields):
    missing = [f for f in fields if not payload.get(f)]
    if missing:
        return False, missing
    return True, []


def auth_from_header() -> Optional[ClientProfile]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    email = sessions.get(token)
    if not email:
        return None
    return clients.get(email)


def require_auth():
    user = auth_from_header()
    if not user:
        return None, (jsonify({"error": "Unauthorized"}), 401)
    return user, None


# --- Routes ----------------------------------------------------------------

@app.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    ok, missing = require_fields(payload, ["name", "email", "driver_license", "payment_method", "pin"])
    if not ok:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    email = payload["email"].lower()
    if email in clients:
        return jsonify({"error": "Client already exists"}), 409

    clients[email] = ClientProfile(
        name=payload["name"],
        email=email,
        driver_license=payload["driver_license"],
        payment_method=payload["payment_method"],
        pin=str(payload["pin"]),
    )
    return jsonify({"message": "Client registered"}), 201


@app.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    ok, missing = require_fields(payload, ["email", "pin"])
    if not ok:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    email = payload["email"].lower()
    client = clients.get(email)
    if not client or client.pin != str(payload["pin"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = str(uuid4())
    sessions[token] = email
    return jsonify({"token": token, "client": {"name": client.name, "email": client.email}})


@app.get("/cars")
def list_cars():
    user, error = require_auth()
    if error:
        return error

    available = [
        {
            "vin": car.vin,
            "model": car.model,
            "location": car.location,
            "status": car.availability(),
        }
        for car in cars.values()
        if car.rented_by is None
    ]
    return jsonify({"cars": available, "client": user.email})


@app.post("/rentals/start")
def start_rental():
    user, error = require_auth()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    ok, missing = require_fields(payload, ["vin"])
    if not ok:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    car = cars.get(payload["vin"])
    if not car:
        return jsonify({"error": "Car not found"}), 404
    if car.rented_by:
        return jsonify({"error": "Car already rented"}), 409

    car.rented_by = user.email
    car.telematics.locked = False  # simulate unlock

    return jsonify({
        "message": "Rental started",
        "vin": car.vin,
        "telematics": car.telematics.as_dict(),
    }), 200


@app.post("/rentals/end")
def end_rental():
    user, error = require_auth()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    ok, missing = require_fields(payload, ["vin"])
    if not ok:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    car = cars.get(payload["vin"])
    if not car:
        return jsonify({"error": "Car not found"}), 404
    if car.rented_by != user.email:
        return jsonify({"error": "You do not have an active rental for this car"}), 403

    # Consult telematics to decide if we can close the rental.
    issues = []
    if not car.telematics.doors_closed:
        issues.append("Doors are open; please close them")
    if not car.telematics.lights_off:
        issues.append("Exterior lights are on; please switch them off")

    if issues:
        return jsonify({"status": "error", "issues": issues}), 400

    car.telematics.locked = True
    car.rented_by = None

    return jsonify({
        "status": "ok",
        "message": "Rental ended and car locked",
        "telematics": car.telematics.as_dict(),
    })


@app.patch("/cars/<vin>/telematics")
def update_telematics(vin: str):
    """Simulate the car sending its latest state.

    This endpoint is intentionally simple so tests and demos can toggle states.
    """
    car = cars.get(vin)
    if not car:
        return jsonify({"error": "Car not found"}), 404
    payload = request.get_json(silent=True) or {}
    for field in ["locked", "doors_closed", "lights_off"]:
        if field in payload:
            setattr(car.telematics, field, bool(payload[field]))
    return jsonify({"vin": car.vin, "telematics": car.telematics.as_dict()})


@app.get("/")
def health():
    return jsonify({"status": "ok", "clients": len(clients), "cars": len(cars)})


@app.get("/app")
@app.get("/ui")
def serve_ui():
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
