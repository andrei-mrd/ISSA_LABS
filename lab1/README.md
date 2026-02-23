# CarSharing prototype

A small client-server prototype implementing the car sharing flows from the assignment: client login, query available cars, start rental, and end rental. The backend is a Flask service with in-memory data; `client.py` simulates the phone app.

## Setup
1. Use Python 3.10+.
2. Install deps: `pip install -r requirements.txt`

## Run the backend
```bash
python server.py
```
The service listens on `http://localhost:5000` by default.

## Web frontend
Launch the backend, then open the browser at `http://localhost:5000/app` (or the port you chose). The page lets you:
- Register a client profile
- Log in and store a session token
- Fetch available cars
- Start and end rentals
- Toggle telematics state to test approval/denial on end rental

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

# 4) Start rental for a VIN from the list
python client.py start --token "$TOKEN" --vin VIN-001

# 5) End rental for that VIN
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
