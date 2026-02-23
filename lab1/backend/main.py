import asyncio
import json
from datetime import date, datetime, timezone
from typing import Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from models import Car, Message, User
from services import DataStore, haversine_km

app = FastAPI(title="Car Sharing Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = DataStore()
pending_state_requests: Dict[str, asyncio.Future] = {}


@app.on_event("startup")
async def startup() -> None:
    store.seed_cars()


def parse_message(data: str) -> Message:
    payload = json.loads(data)
    return Message(**payload)


async def send_message(websocket: WebSocket, message: Message) -> None:
    await websocket.send_text(message.json())


async def send_to_client(client_id: str, message: Message) -> None:
    ws = store.client_connections.get(client_id)
    if not ws:
        return
    try:
        await send_message(ws, message)
    except RuntimeError:
        store.remove_connection(client_id)


async def notify_user(user: User, text: str) -> None:
    if not user.clientId:
        return
    message = Message.build("NOTIFY", {"message": text})
    await send_to_client(user.clientId, message)


def license_expired(license_date: str) -> bool:
    try:
        expiry = date.fromisoformat(license_date.split("T")[0])
    except ValueError:
        return True
    return expiry < date.today()


async def handle_register(websocket: WebSocket, message: Message) -> None:
    store.set_connection(message.clientId, websocket)
    payload = message.payload
    if payload["age"] < 18:
        await send_message(
            websocket,
            Message.build(
                "REGISTER_CLIENT_ERROR",
                {"reason": "Age must be 18+"},
                correlation_id=message.messageId,
            ),
        )
        return
    if license_expired(payload["licenseValidUntil"]):
        await send_message(
            websocket,
            Message.build(
                "REGISTER_CLIENT_ERROR",
                {"reason": "Driving license expired"},
                correlation_id=message.messageId,
            ),
        )
        return
    user = store.create_user(payload, message.clientId)
    await send_message(
        websocket,
        Message.build(
            "REGISTER_CLIENT_OK",
            {"user": user.dict()},
            correlation_id=message.messageId,
        ),
    )


async def handle_query_cars(websocket: WebSocket, message: Message) -> None:
    store.set_connection(message.clientId, websocket)
    user = store.get_user_by_client(message.clientId)
    if not user:
        await send_message(
            websocket,
            Message.build(
                "QUERY_CARS_RESULT",
                {"cars": [], "error": "User not registered"},
                correlation_id=message.messageId,
            ),
        )
        return
    if "location" in message.payload:
        store.update_user_location(message.clientId, message.payload["location"])
        user = store.get_user_by_client(message.clientId) or user
    cars_with_distance = []
    for car in store.cars.values():
        if car.status != "AVAILABLE":
            continue
        distance = haversine_km(
            user.location.lat, user.location.lon, car.location.lat, car.location.lon
        )
        cars_with_distance.append(
            {
                **car.dict(),
                "distanceKm": round(distance, 3),
            }
        )
    cars_with_distance.sort(key=lambda c: c["distanceKm"])
    await send_message(
        websocket,
        Message.build(
            "QUERY_CARS_RESULT",
            {"cars": cars_with_distance},
            correlation_id=message.messageId,
        ),
    )


async def handle_start_rental(websocket: WebSocket, message: Message) -> None:
    user = store.get_user_by_client(message.clientId)
    if not user:
        await send_message(
            websocket,
            Message.build(
                "START_RENTAL_ERROR",
                {"reason": "User not registered"},
                correlation_id=message.messageId,
            ),
        )
        return
    vin = message.payload["vin"]
    car: Optional[Car] = store.cars.get(vin)
    if not car:
        await send_message(
            websocket,
            Message.build(
                "START_RENTAL_ERROR",
                {"reason": "Car not found"},
                correlation_id=message.messageId,
            ),
        )
        return
    if user.activeRentalVin:
        await send_message(
            websocket,
            Message.build(
                "START_RENTAL_ERROR",
                {"reason": "User already has an active rental"},
                correlation_id=message.messageId,
            ),
        )
        return
    if car.status != "AVAILABLE":
        await send_message(
            websocket,
            Message.build(
                "START_RENTAL_ERROR",
                {"reason": "Car is not available"},
                correlation_id=message.messageId,
            ),
        )
        return
    if not car.telematicsClientId or car.telematicsClientId not in store.client_connections:
        await send_message(
            websocket,
            Message.build(
                "START_RENTAL_ERROR",
                {"reason": "Car telematics not connected"},
                correlation_id=message.messageId,
            ),
        )
        return
    distance = haversine_km(
        user.location.lat, user.location.lon, car.location.lat, car.location.lon
    )
    if distance > 2:
        await send_message(
            websocket,
            Message.build(
                "START_RENTAL_ERROR",
                {"reason": "Car is farther than 2 km"},
                correlation_id=message.messageId,
            ),
        )
        return
    rental = store.start_rental(user, car)
    await send_to_client(
        car.telematicsClientId,
        Message.build(
            "CAR_UNLOCK",
            {"vin": car.vin},
            correlation_id=message.messageId,
        ),
    )
    await notify_user(user, f"Car {car.vin} unlocked")
    await send_message(
        websocket,
        Message.build(
            "START_RENTAL_OK",
            {"rental": rental.dict(), "car": car.dict()},
            correlation_id=message.messageId,
        ),
    )


async def request_car_state(car: Car, correlation: str) -> Optional[dict]:
    telematics_id = car.telematicsClientId
    if not telematics_id:
        return None
    ws = store.client_connections.get(telematics_id)
    if not ws:
        return None
    query_message_id = str(uuid4())
    loop = asyncio.get_event_loop()
    future: asyncio.Future = loop.create_future()
    pending_state_requests[query_message_id] = future
    await send_message(
        ws,
        Message.build(
            "CAR_STATE_QUERY",
            {"vin": car.vin},
            correlation_id=correlation,
            message_id=query_message_id,
        ),
    )
    try:
        return await asyncio.wait_for(future, timeout=10)
    except asyncio.TimeoutError:
        pending_state_requests.pop(query_message_id, None)
        return None


async def handle_end_rental(websocket: WebSocket, message: Message) -> None:
    user = store.get_user_by_client(message.clientId)
    if not user:
        await send_message(
            websocket,
            Message.build(
                "END_RENTAL_ERROR",
                {"reason": "User not registered"},
                correlation_id=message.messageId,
            ),
        )
        return
    rental = store.get_rental_by_user(user)
    if not rental:
        await send_message(
            websocket,
            Message.build(
                "END_RENTAL_ERROR",
                {"reason": "No active rental"},
                correlation_id=message.messageId,
            ),
        )
        return
    car = store.cars.get(rental.vin)
    if not car or not car.telematicsClientId or car.telematicsClientId not in store.client_connections:
        await send_message(
            websocket,
            Message.build(
                "END_RENTAL_ERROR",
                {"reason": "Car not connected"},
                correlation_id=message.messageId,
            ),
        )
        return
    state = await request_car_state(car, message.messageId)
    if state is None:
        await send_message(
            websocket,
            Message.build(
                "END_RENTAL_ERROR",
                {"reason": "Car state unavailable"},
                correlation_id=message.messageId,
            ),
        )
        return
    issues = []
    if not state.get("doorsClosed"):
        issues.append("Close all doors")
    if not state.get("lightsOff"):
        issues.append("Turn off lights")
    if not state.get("engineOff"):
        issues.append("Turn off engine")
    if issues:
        await send_message(
            websocket,
            Message.build(
                "END_RENTAL_ERROR",
                {"reason": " ".join(issues), "recommendedAction": "; ".join(issues)},
                correlation_id=message.messageId,
            ),
        )
        await notify_user(user, "; ".join(issues))
        return
    await send_to_client(
        car.telematicsClientId,
        Message.build(
            "CAR_LOCK",
            {"vin": car.vin},
            correlation_id=message.messageId,
        ),
    )
    car.status = "AVAILABLE"
    car.rentedByUserId = None
    user.activeRentalVin = None
    finalized = store.finalize_rental(rental)
    await notify_user(user, f"Rental {rental.id} ended and car locked")
    await send_message(
        websocket,
        Message.build(
            "END_RENTAL_OK",
            {"rental": finalized.dict(), "car": car.dict()},
            correlation_id=message.messageId,
        ),
    )


async def handle_car_connect(websocket: WebSocket, message: Message) -> None:
    store.set_connection(message.clientId, websocket)
    vin = message.payload["vin"]
    car = store.cars.get(vin)
    if car:
        car.telematicsClientId = message.clientId
    await send_message(
        websocket,
        Message.build(
            "REGISTER_CLIENT_OK",
            {"message": f"Car {vin} connected"},
            correlation_id=message.messageId,
        ),
    )


async def handle_car_state_response(message: Message) -> None:
    correlation = message.correlationId
    if not correlation:
        return
    future = pending_state_requests.pop(correlation, None)
    if future and not future.done():
        future.set_result(message.payload)


async def dispatch(websocket: WebSocket, message: Message) -> None:
    if message.type == "REGISTER_CLIENT":
        await handle_register(websocket, message)
    elif message.type == "QUERY_CARS":
        await handle_query_cars(websocket, message)
    elif message.type == "START_RENTAL":
        await handle_start_rental(websocket, message)
    elif message.type == "END_RENTAL":
        await handle_end_rental(websocket, message)
    elif message.type == "CAR_CONNECT":
        await handle_car_connect(websocket, message)
    elif message.type == "CAR_STATE_RESPONSE":
        await handle_car_state_response(message)
    else:
        await send_message(
            websocket,
            Message.build(
                "NOTIFY",
                {"message": f"Unknown message type {message.type}"},
                correlation_id=message.messageId,
            ),
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    last_client: Optional[str] = None
    try:
        while True:
            data = await websocket.receive_text()
            message = parse_message(data)
            last_client = message.clientId
            await dispatch(websocket, message)
    except WebSocketDisconnect:
        if last_client:
            store.remove_connection(last_client)
            for car in store.cars.values():
                if car.telematicsClientId == last_client:
                    car.telematicsClientId = None
    except Exception:
        if last_client:
            store.remove_connection(last_client)
        raise
