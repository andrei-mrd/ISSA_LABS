# CarSharing – 3-minute presentation template

Use this structure to build the required PowerPoint quickly.

## Slide 1 — Project and team
- Project: CarSharing prototype (Laboratory 1 & 2)
- Team name
- Member 1
- Member 2

## Slide 2 — Software architecture: entities and roles
- Phone application (`client.py` / web UI) — user-facing client
- Company backend (`server.py`) — server and decision point
- Car + telematics model (`Car`, `CarState`) — lock/unlock + state report
- Data stores (in-memory): clients, sessions, cars

## Slide 3 — Communication protocol
- Protocol: HTTP + JSON
- Auth: Bearer token from login
- Message mapping:
  - 0 register client -> `POST /register`
  - 1 query cars -> `GET /cars`
  - 2 start rental -> `POST /rentals/start`
  - 3 end rental -> `POST /rentals/end`
  - 4 success -> HTTP 2xx
  - 5 error -> HTTP 4xx

## Slide 4 — Use-case flows (sequence summary)
- Login: app -> backend auth -> token
- Query: token-authenticated request -> available cars
- Start rental: backend validates availability -> telematics unlock
- End rental: backend checks telematics (doors/lights) -> lock + close rental or reject with issues

## Slide 5 — Technologies used
- Python 3.10+
- Flask backend
- Requests-based CLI client
- HTML/CSS/JavaScript web frontend
- Mermaid UML diagrams in `ARCHITECTURE.md`

## Demo script (3 minutes)
1. Register client
2. Login and show token
3. Query available cars
4. Start rental for one VIN
5. Try end rental with invalid telematics state (expect error)
6. Fix state and end rental successfully
