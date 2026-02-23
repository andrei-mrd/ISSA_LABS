"""Car sharing backend with SQLite persistence.

Run with `python server.py` and use the companion CLI/web clients.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import sqlite3
from typing import Dict, List, Optional
from uuid import uuid4

from flask import Flask, jsonify, request, send_from_directory


app = Flask(__name__, static_folder="static", static_url_path="/static")

DB_PATH = "carsharing.db"
CAR_CLIENT_KEY = "car-lab-key"
INITIAL_CARS = [
    ("VIN-001", "Hatchback", "Bucharest"),
    ("VIN-002", "SUV", "Cluj"),
    ("VIN-003", "Sedan", "Timisoara"),
]


@dataclass
class ClientProfile:
    name: str
    email: str
    driver_license: str
    payment_method: str
    pin: str


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS clients (
                email TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                driver_license TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                pin TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (email) REFERENCES clients(email)
            );

            CREATE TABLE IF NOT EXISTS cars (
                vin TEXT PRIMARY KEY,
                model TEXT NOT NULL,
                location TEXT NOT NULL,
                locked INTEGER NOT NULL DEFAULT 1,
                doors_closed INTEGER NOT NULL DEFAULT 1,
                lights_off INTEGER NOT NULL DEFAULT 1,
                rented_by TEXT,
                last_seen_at TEXT,
                battery_pct INTEGER NOT NULL DEFAULT 100
            );

            CREATE TABLE IF NOT EXISTS rentals (
                rental_id TEXT PRIMARY KEY,
                client_email TEXT NOT NULL,
                vin TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                status TEXT NOT NULL,
                FOREIGN KEY (client_email) REFERENCES clients(email),
                FOREIGN KEY (vin) REFERENCES cars(vin)
            );

            CREATE TABLE IF NOT EXISTS car_sessions (
                token TEXT PRIMARY KEY,
                vin TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (vin) REFERENCES cars(vin)
            );

            CREATE TABLE IF NOT EXISTS car_commands (
                id TEXT PRIMARY KEY,
                vin TEXT NOT NULL,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                acked_at TEXT,
                success INTEGER,
                note TEXT,
                FOREIGN KEY (vin) REFERENCES cars(vin)
            );
            """
        )

        for vin, model, location in INITIAL_CARS:
            conn.execute(
                """
                INSERT OR IGNORE INTO cars (vin, model, location, locked, doors_closed, lights_off, battery_pct)
                VALUES (?, ?, ?, 1, 1, 1, 100)
                """,
                (vin, model, location),
            )


def require_fields(payload: Dict, fields):
    missing = [f for f in fields if not payload.get(f)]
    if missing:
        return False, missing
    return True, []


def to_bool(value: int) -> bool:
    return bool(int(value))


def car_telematics_dict(row: sqlite3.Row) -> Dict[str, bool]:
    return {
        "locked": to_bool(row["locked"]),
        "doors_closed": to_bool(row["doors_closed"]),
        "lights_off": to_bool(row["lights_off"]),
    }


def car_status(row: sqlite3.Row) -> str:
    if row["rented_by"]:
        return f"rented_by_{row['rented_by']}"
    return "available"


def auth_from_header() -> Optional[ClientProfile]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1]
    with db_conn() as conn:
        row = conn.execute(
            """
            SELECT c.name, c.email, c.driver_license, c.payment_method, c.pin
            FROM sessions s
            JOIN clients c ON c.email = s.email
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()

    if not row:
        return None

    return ClientProfile(
        name=row["name"],
        email=row["email"],
        driver_license=row["driver_license"],
        payment_method=row["payment_method"],
        pin=row["pin"],
    )


def car_auth_from_header() -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1]
    with db_conn() as conn:
        row = conn.execute("SELECT vin FROM car_sessions WHERE token = ?", (token,)).fetchone()
    return row["vin"] if row else None


def require_auth():
    user = auth_from_header()
    if not user:
        return None, (jsonify({"error": "Unauthorized"}), 401)
    return user, None


def require_car_auth():
    vin = car_auth_from_header()
    if not vin:
        return None, (jsonify({"error": "Unauthorized car client"}), 401)
    return vin, None


def enqueue_command(vin: str, action: str) -> Dict[str, str]:
    command = {
        "id": str(uuid4()),
        "action": action,
        "status": "pending",
        "created_at": now_iso(),
    }
    with db_conn() as conn:
        conn.execute(
            """
            INSERT INTO car_commands (id, vin, action, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (command["id"], vin, action, command["status"], command["created_at"]),
        )
    return command


@app.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    ok, missing = require_fields(payload, ["name", "email", "driver_license", "payment_method", "pin"])
    if not ok:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    email = payload["email"].lower()
    with db_conn() as conn:
        exists = conn.execute("SELECT 1 FROM clients WHERE email = ?", (email,)).fetchone()
        if exists:
            return jsonify({"error": "Client already exists"}), 409

        conn.execute(
            """
            INSERT INTO clients (email, name, driver_license, payment_method, pin)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                email,
                payload["name"],
                payload["driver_license"],
                payload["payment_method"],
                str(payload["pin"]),
            ),
        )

    return jsonify({"message": "Client registered"}), 201


@app.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    ok, missing = require_fields(payload, ["email", "pin"])
    if not ok:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    email = payload["email"].lower()
    with db_conn() as conn:
        row = conn.execute("SELECT name, email, pin FROM clients WHERE email = ?", (email,)).fetchone()
        if not row or row["pin"] != str(payload["pin"]):
            return jsonify({"error": "Invalid credentials"}), 401

        token = str(uuid4())
        conn.execute(
            "INSERT INTO sessions (token, email, created_at) VALUES (?, ?, ?)",
            (token, email, now_iso()),
        )

    return jsonify({"token": token, "client": {"name": row["name"], "email": row["email"]}})


@app.get("/cars")
def list_cars():
    user, error = require_auth()
    if error:
        return error

    with db_conn() as conn:
        rows = conn.execute(
            """
            SELECT vin, model, location, locked, doors_closed, lights_off, rented_by, last_seen_at, battery_pct
            FROM cars
            WHERE rented_by IS NULL
            ORDER BY vin
            """
        ).fetchall()

    available = [
        {
            "vin": row["vin"],
            "model": row["model"],
            "location": row["location"],
            "status": car_status(row),
            "telematics": car_telematics_dict(row),
            "last_seen_at": row["last_seen_at"],
            "battery_pct": row["battery_pct"],
        }
        for row in rows
    ]

    return jsonify({"cars": available, "client": user.email})


@app.get("/me")
def me():
    user, error = require_auth()
    if error:
        return error
    return jsonify(
        {
            "name": user.name,
            "email": user.email,
            "driver_license": user.driver_license,
            "payment_method": user.payment_method,
        }
    )


@app.get("/rentals/me")
def my_rentals():
    user, error = require_auth()
    if error:
        return error

    with db_conn() as conn:
        rows = conn.execute(
            """
            SELECT rental_id, client_email, vin, started_at, ended_at, status
            FROM rentals
            WHERE client_email = ?
            ORDER BY started_at DESC
            """,
            (user.email,),
        ).fetchall()

    rentals = [
        {
            "rental_id": row["rental_id"],
            "client_email": row["client_email"],
            "vin": row["vin"],
            "started_at": row["started_at"],
            "ended_at": row["ended_at"],
            "status": row["status"],
        }
        for row in rows
    ]

    return jsonify({"rentals": rentals})


@app.post("/rentals/start")
def start_rental():
    user, error = require_auth()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    ok, missing = require_fields(payload, ["vin"])
    if not ok:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    vin = payload["vin"]
    with db_conn() as conn:
        row = conn.execute(
            "SELECT vin, locked, doors_closed, lights_off, rented_by FROM cars WHERE vin = ?",
            (vin,),
        ).fetchone()
        if not row:
            return jsonify({"error": "Car not found"}), 404
        if row["rented_by"]:
            return jsonify({"error": "Car already rented"}), 409

        conn.execute("UPDATE cars SET rented_by = ? WHERE vin = ?", (user.email, vin))

        rental_id = str(uuid4())
        conn.execute(
            """
            INSERT INTO rentals (rental_id, client_email, vin, started_at, status)
            VALUES (?, ?, ?, ?, 'active')
            """,
            (rental_id, user.email, vin, now_iso()),
        )

    command = enqueue_command(vin, "unlock")

    return jsonify(
        {
            "message": "Rental started",
            "vin": vin,
            "rental_id": rental_id,
            "car_command": command,
            "telematics": {
                "locked": to_bool(row["locked"]),
                "doors_closed": to_bool(row["doors_closed"]),
                "lights_off": to_bool(row["lights_off"]),
            },
        }
    ), 200


@app.post("/rentals/end")
def end_rental():
    user, error = require_auth()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    ok, missing = require_fields(payload, ["vin"])
    if not ok:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    vin = payload["vin"]
    with db_conn() as conn:
        row = conn.execute(
            "SELECT vin, locked, doors_closed, lights_off, rented_by FROM cars WHERE vin = ?",
            (vin,),
        ).fetchone()
        if not row:
            return jsonify({"error": "Car not found"}), 404
        if row["rented_by"] != user.email:
            return jsonify({"error": "You do not have an active rental for this car"}), 403

        issues = []
        if not to_bool(row["doors_closed"]):
            issues.append("Doors are open; please close them")
        if not to_bool(row["lights_off"]):
            issues.append("Exterior lights are on; please switch them off")

        if issues:
            return jsonify({"status": "error", "issues": issues}), 400

        conn.execute(
            """
            UPDATE rentals
            SET status = 'ended', ended_at = ?
            WHERE rental_id = (
                SELECT rental_id FROM rentals
                WHERE client_email = ? AND vin = ? AND status = 'active'
                ORDER BY started_at DESC
                LIMIT 1
            )
            """,
            (now_iso(), user.email, vin),
        )

        conn.execute("UPDATE cars SET rented_by = NULL, locked = 1 WHERE vin = ?", (vin,))

    command = enqueue_command(vin, "lock")

    return jsonify(
        {
            "status": "ok",
            "message": "Rental ended and car locked",
            "car_command": command,
            "telematics": {
                "locked": True,
                "doors_closed": to_bool(row["doors_closed"]),
                "lights_off": to_bool(row["lights_off"]),
            },
        }
    )


@app.patch("/cars/<vin>/telematics")
def update_telematics(vin: str):
    car_payload = request.get_json(silent=True) or {}

    updates = []
    params: List[object] = []
    for field in ["locked", "doors_closed", "lights_off"]:
        if field in car_payload:
            updates.append(f"{field} = ?")
            params.append(1 if bool(car_payload[field]) else 0)

    if "battery_pct" in car_payload:
        try:
            battery = int(car_payload["battery_pct"])
        except (TypeError, ValueError):
            return jsonify({"error": "battery_pct must be an integer"}), 400
        battery = max(0, min(100, battery))
        updates.append("battery_pct = ?")
        params.append(battery)

    updates.append("last_seen_at = ?")
    params.append(now_iso())
    params.append(vin)

    with db_conn() as conn:
        exists = conn.execute("SELECT 1 FROM cars WHERE vin = ?", (vin,)).fetchone()
        if not exists:
            return jsonify({"error": "Car not found"}), 404

        conn.execute(f"UPDATE cars SET {', '.join(updates)} WHERE vin = ?", params)

        row = conn.execute(
            "SELECT vin, locked, doors_closed, lights_off, battery_pct, last_seen_at FROM cars WHERE vin = ?",
            (vin,),
        ).fetchone()

    return jsonify(
        {
            "vin": row["vin"],
            "telematics": car_telematics_dict(row),
            "battery_pct": row["battery_pct"],
            "last_seen_at": row["last_seen_at"],
        }
    )


@app.post("/car/register")
def register_car_client():
    payload = request.get_json(silent=True) or {}
    ok, missing = require_fields(payload, ["vin", "api_key"])
    if not ok:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    vin = payload["vin"]
    if payload["api_key"] != CAR_CLIENT_KEY:
        return jsonify({"error": "Invalid car api key"}), 401

    with db_conn() as conn:
        row = conn.execute("SELECT 1 FROM cars WHERE vin = ?", (vin,)).fetchone()
        if not row:
            return jsonify({"error": "Car not found"}), 404

        token = str(uuid4())
        conn.execute(
            "INSERT INTO car_sessions (token, vin, created_at) VALUES (?, ?, ?)",
            (token, vin, now_iso()),
        )
        conn.execute("UPDATE cars SET last_seen_at = ? WHERE vin = ?", (now_iso(), vin))

    return jsonify({"vin": vin, "car_token": token})


@app.get("/car/commands")
def pull_car_commands():
    vin, error = require_car_auth()
    if error:
        return error

    with db_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, action, status, created_at
            FROM car_commands
            WHERE vin = ? AND status = 'pending'
            ORDER BY created_at ASC
            """,
            (vin,),
        ).fetchall()

        conn.execute("UPDATE cars SET last_seen_at = ? WHERE vin = ?", (now_iso(), vin))

    commands = [
        {
            "id": row["id"],
            "action": row["action"],
            "status": row["status"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
    return jsonify({"vin": vin, "commands": commands})


@app.post("/car/ack")
def ack_car_command():
    vin, error = require_car_auth()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    ok, missing = require_fields(payload, ["command_id"])
    if not ok:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    command_id = payload["command_id"]
    success = bool(payload.get("success", True))
    note = str(payload.get("note", "")).strip() or None

    with db_conn() as conn:
        command = conn.execute(
            "SELECT id, action FROM car_commands WHERE id = ? AND vin = ?",
            (command_id, vin),
        ).fetchone()
        if not command:
            return jsonify({"error": "Command not found"}), 404

        conn.execute(
            """
            UPDATE car_commands
            SET status = 'acked', acked_at = ?, success = ?, note = ?
            WHERE id = ?
            """,
            (now_iso(), 1 if success else 0, note, command_id),
        )

        if success and command["action"] == "unlock":
            conn.execute("UPDATE cars SET locked = 0 WHERE vin = ?", (vin,))
        if success and command["action"] == "lock":
            conn.execute("UPDATE cars SET locked = 1 WHERE vin = ?", (vin,))

        conn.execute("UPDATE cars SET last_seen_at = ? WHERE vin = ?", (now_iso(), vin))

        updated = conn.execute(
            "SELECT id, action, status, created_at, acked_at, success, note FROM car_commands WHERE id = ?",
            (command_id,),
        ).fetchone()

    return jsonify(
        {
            "vin": vin,
            "command": {
                "id": updated["id"],
                "action": updated["action"],
                "status": updated["status"],
                "created_at": updated["created_at"],
                "acked_at": updated["acked_at"],
                "success": bool(updated["success"]) if updated["success"] is not None else None,
                "note": updated["note"],
            },
        }
    )


@app.post("/car/heartbeat")
def car_heartbeat():
    vin, error = require_car_auth()
    if error:
        return error

    payload = request.get_json(silent=True) or {}
    updates = []
    params: List[object] = []

    for field in ["locked", "doors_closed", "lights_off"]:
        if field in payload:
            updates.append(f"{field} = ?")
            params.append(1 if bool(payload[field]) else 0)

    if "battery_pct" in payload:
        try:
            battery = int(payload["battery_pct"])
        except (TypeError, ValueError):
            return jsonify({"error": "battery_pct must be an integer"}), 400
        updates.append("battery_pct = ?")
        params.append(max(0, min(100, battery)))

    updates.append("last_seen_at = ?")
    params.append(now_iso())
    params.append(vin)

    with db_conn() as conn:
        conn.execute(f"UPDATE cars SET {', '.join(updates)} WHERE vin = ?", params)
        row = conn.execute(
            "SELECT vin, locked, doors_closed, lights_off, battery_pct, last_seen_at FROM cars WHERE vin = ?",
            (vin,),
        ).fetchone()
        pending_row = conn.execute(
            "SELECT COUNT(*) AS count FROM car_commands WHERE vin = ? AND status = 'pending'",
            (vin,),
        ).fetchone()

    return jsonify(
        {
            "vin": row["vin"],
            "status": "ok",
            "pending_commands": int(pending_row["count"]),
            "telematics": car_telematics_dict(row),
            "battery_pct": row["battery_pct"],
            "last_seen_at": row["last_seen_at"],
        }
    )


@app.get("/")
def health():
    with db_conn() as conn:
        clients_count = conn.execute("SELECT COUNT(*) AS count FROM clients").fetchone()["count"]
        cars_count = conn.execute("SELECT COUNT(*) AS count FROM cars").fetchone()["count"]
    return jsonify({"status": "ok", "clients": clients_count, "cars": cars_count})


@app.get("/app")
@app.get("/ui")
def serve_ui():
    return send_from_directory(app.static_folder, "index.html")


init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
