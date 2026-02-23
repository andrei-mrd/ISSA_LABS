# CarSharing prototype

A small client-server prototype implementing the car sharing flows from the assignment: client login, query available cars, start rental, and end rental. The backend is a Flask service backed by SQLite; `client.py` simulates the phone app.

The backend persists data in SQLite (`carsharing.db`) so clients, sessions, rentals, and car telemetry survive restarts.

## Assignment coverage

This prototype covers all required Exercise 2 use-cases:

- Login of a client in the phone application (`POST /login`, `python client.py login ...`)
- Query cars available for rental (`GET /cars`, `python client.py cars ...`)
- Start rental (`POST /rentals/start`, `python client.py start ...`)
- End rental with telematics validation (`POST /rentals/end`, `python client.py end ...`)

Preconditions are enforced by the backend:

- `cars`, `start`, and `end` require a valid Bearer token from `login`
- `end` requires an active rental by the same authenticated user

## Communication protocol (implemented)

Transport and format:

- HTTP/1.1 + JSON payloads
- Authentication via `Authorization: Bearer <token>`

Logical message identifiers (mapped to API):

- `0` register client -> `POST /register`
- `1` query available cars -> `GET /cars`
- `2` start rental -> `POST /rentals/start`
- `3` end rental -> `POST /rentals/end`
- `4` success notification -> `2xx` JSON responses with `message` or `status: ok`
- `5` error notification -> `4xx` JSON responses with `error` or `issues`

## Setup
1. Use Python 3.10+.
2. Install deps: `pip install -r requirements.txt`

## Run the backend
```bash
python server.py
```
The service listens on `http://localhost:5000` by default.

On first run, the backend auto-creates SQLite schema and seeds initial cars.

## Web frontend
Launch the backend, then open the browser at `http://localhost:5000/app` (or the port you chose). The page lets you:
- Register a client profile
- Log in and store a session token
- Fetch available cars
- Start and end rentals
- Toggle telematics state to test approval/denial on end rental
- View authenticated profile and rental history
- Register a car-side client token, send heartbeat, and poll/ack lock-unlock commands

## Run the client
Each command hits the backend using JSON over HTTP. Add `--host` if you run on a different base URL.

```bash
# 1) Create profile (name, email, driver license, payment method, PIN)
python client.py register --name "Ada Driver" --email ada@example.com --license RO-DRIV-1 --payment "visa-1234" --pin 1111

# 2) Login and capture the token from the response
python client.py login --email ada@example.com --pin 1111
TOKEN=<token-from-login>

# 3) Query available cars (requires token)
python client.py cars --token "$TOKEN"

# 3b) Query current profile and rental history
python client.py me --token "$TOKEN"
python client.py rentals --token "$TOKEN"

# 4) Start rental for a VIN from the list
python client.py start --token "$TOKEN" --vin VIN-001

# 5) End rental for that VIN
python client.py end --token "$TOKEN" --vin VIN-001
```

## Car telematics client

The project now includes a dedicated car-side client (`car_client.py`) that behaves like the vehicle telematics module.

```bash
# Register car client (default api key: car-lab-key)
python car_client.py register --vin VIN-001

# Run continuous loop: heartbeat + pull commands + ack commands
python car_client.py run --vin VIN-001 --interval 2
```

You can also use one-shot commands:

```bash
python car_client.py heartbeat --token <car-token> --doors closed --lights off --locked true --battery 95
python car_client.py commands --token <car-token>
python car_client.py ack --token <car-token> --command-id <command-id>
```

## Demo flow (3-minute grading run)

Use this exact sequence during demo:

```bash
# optional: reset by restarting backend
python server.py

# register
python client.py register --name "Ada Driver" --email ada@example.com --license RO-DRIV-1 --payment "visa-1234" --pin 1111

# login
python client.py login --email ada@example.com --pin 1111
TOKEN=<token-from-login>

# query cars
python client.py cars --token "$TOKEN"

# start rental
python client.py start --token "$TOKEN" --vin VIN-001

# simulate invalid end-rental state
python client.py set-state --vin VIN-001 --doors open --lights on
python client.py end --token "$TOKEN" --vin VIN-001

# fix state and end rental
python client.py set-state --vin VIN-001 --doors closed --lights off
python client.py end --token "$TOKEN" --vin VIN-001
```

## Simulating telematics checks
Ending a rental can fail if doors are open or lights are on. You can toggle telematics state (as if sent by the car) before ending the rental:
```bash
# Mark doors open and lights on for VIN-001
python client.py set-state --vin VIN-001 --doors open --lights on

# Retry end rental will now return issues until you set the states back
python client.py set-state --vin VIN-001 --doors closed --lights off
python client.py end --token "$TOKEN" --vin VIN-001
```

## Architecture
See `ARCHITECTURE.md` for the Mermaid-based class and sequence diagrams covering the system roles and interactions.
