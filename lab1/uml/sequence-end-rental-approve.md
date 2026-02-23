# Sequence End Rental Approve

Successful rental closure starting with END_RENTAL from the phone app.
Backend queries telematics for CAR_STATE_RESPONSE and verifies all safety flags.
Car is locked, then END_RENTAL_OK and NOTIFY confirm completion to the user.

```mermaid
sequenceDiagram
  participant PhoneApp
  participant BackendServer
  participant CarTelematicsModule

  PhoneApp->>BackendServer: END_RENTAL\n(vin)
  BackendServer-->>CarTelematicsModule: CAR_STATE_QUERY\n(correlation=end request)
  CarTelematicsModule-->>BackendServer: CAR_STATE_RESPONSE\n(doorsClosed,lightsOff,engineOff)
  BackendServer-->>CarTelematicsModule: CAR_LOCK\n(vin)
  BackendServer-->>PhoneApp: END_RENTAL_OK\n(payload rental, car)
  BackendServer-->>PhoneApp: NOTIFY\n("Car locked")
```
