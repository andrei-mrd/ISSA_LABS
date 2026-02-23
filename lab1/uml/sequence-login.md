# Sequence Login

Registration handshake where the phone app submits user details to the backend.
Backend validates age and license, returning approval or denial.
All flows use the shared WebSocket channel and the REGISTER_* message types.

```mermaid
sequenceDiagram
  participant PhoneApp
  participant BackendServer
  participant CarTelematicsModule

  PhoneApp->>BackendServer: REGISTER_CLIENT\n(payload user)
  alt approved
    BackendServer-->>PhoneApp: REGISTER_CLIENT_OK\n(payload user)
  else denied
    BackendServer-->>PhoneApp: REGISTER_CLIENT_ERROR\n(reason)
  end
```
