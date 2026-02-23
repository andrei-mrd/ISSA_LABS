# Sequence Query Cars

Phone app requests nearby vehicles with QUERY_CARS and a location payload.
Backend filters AVAILABLE cars using Haversine distance and sorts them.
Results are returned via QUERY_CARS_RESULT on the WebSocket channel.

```mermaid
sequenceDiagram
  participant PhoneApp
  participant BackendServer
  participant CarTelematicsModule

  PhoneApp->>BackendServer: QUERY_CARS\n(payload location)
  BackendServer->>BackendServer: compute distance (Haversine)
  BackendServer-->>PhoneApp: QUERY_CARS_RESULT\n(sorted cars with distance)
```
