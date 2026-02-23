import { useEffect, useRef, useState } from "react";
import { Car, Rental, User } from "./types";

type Screen = "login" | "cars" | "rental";

const defaultForm = {
  fullName: "Demo Driver",
  email: "driver@example.com",
  age: 28,
  drivingLicenseNumber: "DL-123-456",
  paymentToken: "tok_sample",
  licenseValidUntil: "2028-12-31",
  lat: 47.16,
  lon: 27.59,
};

const clientIdKey = "carshare-clientId";
const formKey = "carshare-form";
const sessionKey = "carshare-session";
const wsKey = "carshare-ws";

export default function App() {
  const [wsUrl, setWsUrl] = useState<string>(() => localStorage.getItem(wsKey) || "ws://localhost:8000/ws");
  const [clientId, setClientId] = useState<string>(() => localStorage.getItem(clientIdKey) || `user-${crypto.randomUUID()}`);
  const [form, setForm] = useState(() => {
    const saved = localStorage.getItem(formKey);
    return saved ? { ...defaultForm, ...JSON.parse(saved) } : defaultForm;
  });
  const [connected, setConnected] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [screen, setScreen] = useState<Screen>("login");
  const [cars, setCars] = useState<Car[]>([]);
  const [selectedVin, setSelectedVin] = useState("");
  const [rental, setRental] = useState<Rental | null>(null);
  const [status, setStatus] = useState("");
  const [statusTone, setStatusTone] = useState<"" | "ok" | "error">("");
  const [notifications, setNotifications] = useState<string[]>([]);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    localStorage.setItem(clientIdKey, clientId);
  }, [clientId]);

  useEffect(() => {
    localStorage.setItem(formKey, JSON.stringify(form));
  }, [form]);

  useEffect(() => {
    if (user) {
      localStorage.setItem(sessionKey, JSON.stringify({ user }));
    }
  }, [user]);

  useEffect(() => {
    localStorage.setItem(wsKey, wsUrl);
  }, [wsUrl]);

  useEffect(() => {
    return () => {
      socketRef.current?.close();
    };
  }, []);

  const updateStatus = (text: string, tone: "" | "ok" | "error" = "") => {
    setStatus(text);
    setStatusTone(tone);
  };

  const sendMessage = (type: string, payload: Record<string, unknown>, correlationId: string | null = null) => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      updateStatus("WebSocket not connected", "error");
      return;
    }
    const message = {
      clientId,
      messageId: crypto.randomUUID(),
      type,
      correlationId,
      timestamp: new Date().toISOString(),
      payload,
    };
    socketRef.current.send(JSON.stringify(message));
  };

  const connectAndRegister = () => {
    socketRef.current?.close();
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;
    ws.onopen = () => {
      setConnected(true);
      updateStatus("Connected. Sending login...", "ok");
      sendMessage("REGISTER_CLIENT", {
        ...form,
        location: { lat: Number(form.lat), lon: Number(form.lon) },
        age: Number(form.age),
      });
    };
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      handleIncoming(message);
    };
    ws.onclose = () => {
      setConnected(false);
      updateStatus("Disconnected", "error");
    };
    ws.onerror = () => updateStatus("WebSocket error", "error");
  };

  const handleIncoming = (message: any) => {
    const payload = message.payload || {};
    switch (message.type) {
      case "REGISTER_CLIENT_OK":
        setUser(payload.user);
        setScreen("cars");
        updateStatus("Login approved", "ok");
        break;
      case "REGISTER_CLIENT_ERROR":
        updateStatus(payload.reason || "Login denied", "error");
        break;
      case "QUERY_CARS_RESULT":
        setCars(payload.cars || []);
        updateStatus("Cars updated", "ok");
        break;
      case "START_RENTAL_OK":
        setRental(payload.rental);
        setScreen("rental");
        updateStatus("Rental started", "ok");
        break;
      case "START_RENTAL_ERROR":
        updateStatus(payload.reason || "Start rental denied", "error");
        break;
      case "END_RENTAL_OK":
        setRental(payload.rental);
        setScreen("cars");
        setSelectedVin("");
        updateStatus("Rental ended", "ok");
        break;
      case "END_RENTAL_ERROR":
        updateStatus(payload.recommendedAction || payload.reason || "End rental denied", "error");
        break;
      case "NOTIFY":
        appendNotification(payload.message || JSON.stringify(payload));
        break;
      default:
        appendNotification(`Received ${message.type}`);
    }
  };

  const appendNotification = (text: string) => {
    setNotifications((prev) => [text, ...prev].slice(0, 10));
  };

  const onQueryCars = () => {
    if (!user) return;
    sendMessage("QUERY_CARS", { location: { lat: Number(form.lat), lon: Number(form.lon) } });
  };

  const onStartRental = () => {
    if (!selectedVin) return;
    sendMessage("START_RENTAL", { vin: selectedVin });
  };

  const onEndRental = () => {
    sendMessage("END_RENTAL", { vin: rental?.vin });
  };

  const renderLogin = () => (
    <div className="section">
      <h3>Login</h3>
      <div className="grid">
        <div className="input">
          <label>Full Name</label>
          <input value={form.fullName} onChange={(e) => setForm({ ...form, fullName: e.target.value })} />
        </div>
        <div className="input">
          <label>Email</label>
          <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </div>
        <div className="input">
          <label>Age</label>
          <input
            type="number"
            min={16}
            value={form.age}
            onChange={(e) => setForm({ ...form, age: Number(e.target.value) })}
          />
        </div>
        <div className="input">
          <label>Payment Token</label>
          <input value={form.paymentToken} onChange={(e) => setForm({ ...form, paymentToken: e.target.value })} />
        </div>
        <div className="input">
          <label>License Number</label>
          <input
            value={form.drivingLicenseNumber}
            onChange={(e) => setForm({ ...form, drivingLicenseNumber: e.target.value })}
          />
        </div>
        <div className="input">
          <label>License Valid Until</label>
          <input
            type="date"
            value={form.licenseValidUntil}
            onChange={(e) => setForm({ ...form, licenseValidUntil: e.target.value })}
          />
        </div>
        <div className="input">
          <label>Latitude</label>
          <input
            type="number"
            value={form.lat}
            onChange={(e) => setForm({ ...form, lat: Number(e.target.value) })}
          />
        </div>
        <div className="input">
          <label>Longitude</label>
          <input
            type="number"
            value={form.lon}
            onChange={(e) => setForm({ ...form, lon: Number(e.target.value) })}
          />
        </div>
        <div className="input">
          <label>WebSocket URL</label>
          <input value={wsUrl} onChange={(e) => setWsUrl(e.target.value)} />
        </div>
        <div className="input">
          <label>Client ID</label>
          <input value={clientId} onChange={(e) => setClientId(e.target.value)} />
        </div>
      </div>
      <div style={{ marginTop: 12 }}>
        <button className="button" onClick={connectAndRegister}>
          Connect & Login
        </button>
      </div>
    </div>
  );

  const renderCars = () => (
    <div className="section">
      <h3>Cars</h3>
      <div className="small">Hello, {user?.fullName}</div>
      <div className="grid" style={{ marginTop: 8 }}>
        <div className="input">
          <label>Latitude</label>
          <input
            type="number"
            value={form.lat}
            onChange={(e) => setForm({ ...form, lat: Number(e.target.value) })}
          />
        </div>
        <div className="input">
          <label>Longitude</label>
          <input
            type="number"
            value={form.lon}
            onChange={(e) => setForm({ ...form, lon: Number(e.target.value) })}
          />
        </div>
      </div>
      <div style={{ margin: "12px 0" }}>
        <button className="button secondary" onClick={onQueryCars} disabled={!connected}>
          Query Available Cars
        </button>
      </div>
      <div className="card-list">
        {cars.map((car) => (
          <div
            key={car.vin}
            className={`car-card ${selectedVin === car.vin ? "selected" : ""}`}
            onClick={() => setSelectedVin(car.vin)}
          >
            <div className="car-meta">
              <strong>{car.vin}</strong>
              <span className="small">
                {car.location.lat.toFixed(4)}, {car.location.lon.toFixed(4)}
              </span>
              <span className="tag">Status: {car.status}</span>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontWeight: 700 }}>{car.distanceKm?.toFixed(2)} km</div>
            </div>
          </div>
        ))}
        {cars.length === 0 && <div className="small">No cars loaded yet.</div>}
      </div>
      <div style={{ marginTop: 14 }}>
        <button className="button" disabled={!selectedVin || !connected} onClick={onStartRental}>
          Start Rental
        </button>
      </div>
    </div>
  );

  const renderRental = () => (
    <div className="section">
      <h3>Rental</h3>
      {rental ? (
        <>
          <div className="car-meta">
            <strong>VIN: {rental.vin}</strong>
            <span className="small">Rental ID: {rental.id}</span>
            <span className="small">Started: {new Date(rental.startedAt).toLocaleString()}</span>
            {rental.endedAt && <span className="small">Ended: {new Date(rental.endedAt).toLocaleString()}</span>}
          </div>
          {!rental.endedAt && (
            <div style={{ marginTop: 14 }}>
              <button className="button" onClick={onEndRental} disabled={!connected}>
                End Rental
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="small">No active rental.</div>
      )}
    </div>
  );

  return (
    <div className="app-shell">
      <div className="header">
        <div>
          <p className="title">CarSharing Client</p>
          <div className="small">Message-based demo</div>
        </div>
        <div className="pill" style={{ background: connected ? "rgba(47,176,128,0.15)" : "rgba(214,69,69,0.15)", color: connected ? "var(--accent)" : "var(--error)" }}>
          {connected ? "Connected" : "Disconnected"}
        </div>
      </div>
      {status && (
        <div className={`status ${statusTone}`}>
          {status}
        </div>
      )}
      {screen === "login" && renderLogin()}
      {screen === "cars" && renderCars()}
      {screen === "rental" && renderRental()}
      <div className="section">
        <h3>Live Notifications</h3>
        <div className="notif-list">
          {notifications.map((note, idx) => (
            <div key={idx} className="notif">
              {note}
            </div>
          ))}
          {notifications.length === 0 && <div className="small">Waiting for events...</div>}
        </div>
      </div>
    </div>
  );
}
