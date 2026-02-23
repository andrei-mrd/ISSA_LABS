# Class Diagram

Core structure of the CarSharing system showing app, backend, and telematics components plus domain entities.
Highlights WebSocket dependencies via the shared Message envelope.
Depicts how the backend owns users, cars, and rentals with multiplicities.

```mermaid
classDiagram
  class PhoneApp {
    +clientId: string
    +connect()
    +queryCars()
    +startRental()
    +endRental()
  }
  class BackendServer {
    +wsEndpoint: "/ws"
    +approveLogin()
    +checkDistance()
    +manageRental()
  }
  class CarTelematicsModule {
    +clientId: string
    +locked: bool
    +doorsClosed: bool
    +lightsOff: bool
    +engineOff: bool
    +respondState()
    +lock()
    +unlock()
  }
  class User {
    +id: string
    +fullName: string
    +email: string
    +age: int
    +drivingLicenseNumber: string
    +paymentToken: string
    +licenseValidUntil: date
    +location: Location
    +activeRentalVin: string
  }
  class Car {
    +vin: string
    +location: Location
    +status: AVAILABLE|RENTED
    +rentedByUserId: string
    +telematicsClientId: string
  }
  class Rental {
    +id: string
    +userId: string
    +vin: string
    +startedAt: datetime
    +endedAt: datetime
  }
  class Message {
    +clientId: string
    +messageId: uuid
    +type: string
    +correlationId: uuid
    +timestamp: ISO-8601
    +payload: object
  }

  PhoneApp ..> Message : sends/receives
  CarTelematicsModule ..> Message : sends/receives
  PhoneApp --> BackendServer : WebSocket
  BackendServer --> CarTelematicsModule : WebSocket
  BackendServer "1" o-- "many" User : manages
  BackendServer "1" o-- "many" Car : manages
  BackendServer "1" o-- "many" Rental : manages
```
