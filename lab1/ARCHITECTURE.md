# CarSharing Architecture

This document captures a lightweight architecture for the car sharing prototype. It includes a class diagram and sequence diagrams that cover the main flows: login + query availability, start rental, and end rental.

## Rubric-oriented summary

- **Entities in system**: `PhoneApp`, `BackendAPI`, `AuthService`, `FleetService`, `RentalService`, `TelematicsModule`, `Car`, and `DataStore`.
- **Server**: `BackendAPI` (Flask service) is the central server and approval authority.
- **Clients**: `PhoneApp` (CLI/web UI) is the user-side client; the telematics side acts as a backend-integrated service endpoint for vehicle control/state.
- **Interfaces**: REST HTTP endpoints over JSON.
- **Messages exchanged**:
  - Register client (`POST /register`)
  - Login (`POST /login`)
  - Query cars (`GET /cars`)
  - Query own profile (`GET /me`)
  - Query own rentals (`GET /rentals/me`)
  - Start rental (`POST /rentals/start`)
  - End rental (`POST /rentals/end`)
  - Telematics update (`PATCH /cars/{vin}/telematics`)
  - Car client register (`POST /car/register`)
  - Car command polling (`GET /car/commands`)
  - Car command acknowledgement (`POST /car/ack`)
  - Car heartbeat (`POST /car/heartbeat`)

## Class diagram
```mermaid
classDiagram
    class PhoneApp {
      +registerClient()
      +login()
      +queryAvailableCars(location)
      +requestStartRental(vin)
      +requestEndRental(vin)
    }

    class BackendAPI {
      +POST /register
      +POST /login
      +GET /cars
      +POST /rentals/start
      +POST /rentals/end
    }

    class AuthService {
      +register(profile)
      +login(email, pin)
      +issueToken()
    }

    class FleetService {
      +listAvailable(location)
      +getByVin(vin)
    }

    class RentalService {
      +start(user, car)
      +end(user, carState)
    }

    class Car {
      <<entity>>
      +vin: string
      +location: GeoPoint
      +status: Available|Rented
      +rentedBy?: ClientId
    }

    class TelematicsModule {
      +unlock(vin)
      +lock(vin)
      +reportState(vin)
    }

    class DataStore {
      <<SQLite>>
      +clients
      +cars
      +sessions
      +rentals
      +car_sessions
      +car_commands
    }

    PhoneApp --> BackendAPI : HTTPS/JSON
    BackendAPI --> AuthService
    BackendAPI --> FleetService
    BackendAPI --> RentalService
    FleetService --> Car
    RentalService --> TelematicsModule : control + state check
    TelematicsModule --> Car : lock/unlock + status
    BackendAPI --> DataStore
```

## Sequence diagrams

### Login and query available cars
```mermaid
sequenceDiagram
    actor User
    participant PhoneApp
    participant Backend as Backend API
    participant Auth as Auth Service
    participant Fleet as Fleet Service

    User->>PhoneApp: Enter profile (name, email, license, payment, PIN)
    PhoneApp->>Backend: POST /register
    Backend->>Auth: register(profile)
    Auth-->>Backend: client created
    Backend-->>PhoneApp: 201 Created

    User->>PhoneApp: Tap Login
    PhoneApp->>Backend: POST /login (email, PIN)
    Backend->>Auth: validate + issue token
    Auth-->>Backend: session token
    Backend-->>PhoneApp: token

    PhoneApp->>Backend: GET /cars (Authorization: Bearer token)
    Backend->>Fleet: listAvailable(location)
    Fleet-->>Backend: cars near user
    Backend-->>PhoneApp: list of available cars
```

### Start rental
```mermaid
sequenceDiagram
    actor User
    participant PhoneApp
    participant Backend as Backend API
    participant Fleet as Fleet Service
    participant Rental as Rental Service
    participant Telematics
    participant Car

    User->>PhoneApp: Select car (VIN)
    PhoneApp->>Backend: POST /rentals/start (vin, token)
    Backend->>Fleet: getByVin(vin)
    Fleet-->>Backend: car data
    Backend->>Rental: start(user, car)
    Rental->>Telematics: unlock(vin)
    Telematics->>Car: unlock command
    Car-->>Telematics: unlocked ack
    Telematics-->>Rental: success
    Rental-->>Backend: rental started (car assigned to user)
    Backend-->>PhoneApp: success notification
```

### End rental
```mermaid
sequenceDiagram
    actor User
    participant PhoneApp
    participant Backend as Backend API
    participant Rental as Rental Service
    participant Telematics
    participant Car

    User->>PhoneApp: Request end rental
    PhoneApp->>Backend: POST /rentals/end (vin, token)
    Backend->>Rental: end(user, vin)
    Rental->>Telematics: reportState(vin)
    Telematics->>Car: send state snapshot
    Car-->>Telematics: doors/locks/lights status
    Telematics-->>Rental: state data
    alt State OK
        Rental->>Telematics: lock(vin)
        Telematics->>Car: lock command
        Car-->>Telematics: locked ack
        Rental-->>Backend: rental closed
        Backend-->>PhoneApp: success
    else State not OK
        Rental-->>Backend: reject with reason (e.g., doors open)
        Backend-->>PhoneApp: error + recommended action
    end
```
```
