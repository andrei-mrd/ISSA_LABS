# Sequence End Rental Deny

Failure path for ending a rental when the vehicle is not secure (doors open, lights on, or engine running).
Backend returns END_RENTAL_ERROR with recommendations to the user.
After fixes in the simulator, a retry flows through to END_RENTAL_OK.

```mermaid
sequenceDiagram
  participant PhoneApp
  participant BackendServer
  participant CarTelematicsModule

  PhoneApp->>BackendServer: END_RENTAL\n(vin)
  BackendServer-->>CarTelematicsModule: CAR_STATE_QUERY
  CarTelematicsModule-->>BackendServer: CAR_STATE_RESPONSE\n(doors open / lights on)
  BackendServer-->>PhoneApp: END_RENTAL_ERROR\n(recommended action)
  Note over PhoneApp,CarTelematicsModule: Driver fixes via simulator CLI
  PhoneApp->>BackendServer: END_RENTAL (retry)
  BackendServer-->>CarTelematicsModule: CAR_STATE_QUERY
  CarTelematicsModule-->>BackendServer: CAR_STATE_RESPONSE\n(all closed/off)
  BackendServer-->>CarTelematicsModule: CAR_LOCK
  BackendServer-->>PhoneApp: END_RENTAL_OK
```
