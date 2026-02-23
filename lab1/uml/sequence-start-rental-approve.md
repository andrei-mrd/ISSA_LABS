# Sequence Start Rental Approve

Happy path for starting a rental via START_RENTAL from the phone app.
Backend validates availability and distance, then unlocks the car through telematics.
Confirmation flows back with START_RENTAL_OK plus a NOTIFY message for the user.

```mermaid
sequenceDiagram
  participant PhoneApp
  participant BackendServer
  participant CarTelematicsModule

  PhoneApp->>BackendServer: START_RENTAL\n(vin)
  BackendServer->>BackendServer: validate availability & distance
  BackendServer-->>CarTelematicsModule: CAR_UNLOCK\n(vin)
  CarTelematicsModule-->>BackendServer: NOTIFY\n(optional)
  BackendServer-->>PhoneApp: START_RENTAL_OK\n(payload rental, car)
  BackendServer-->>PhoneApp: NOTIFY\n("Car unlocked")
```
