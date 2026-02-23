import asyncio
import json
from datetime import datetime, timezone
from uuid import uuid4

import websockets


class CarSimulator:
    def __init__(self, vin: str, server_url: str) -> None:
        self.vin = vin
        self.server_url = server_url
        self.client_id = f"car-{vin}"
        self.websocket: websockets.WebSocketClientProtocol | None = None
        self.locked = True
        self.doorsClosed = True
        self.lightsOff = True
        self.engineOff = True

    def build_message(self, message_type: str, payload: dict, correlation_id: str | None = None) -> str:
        message = {
            "clientId": self.client_id,
            "messageId": str(uuid4()),
            "type": message_type,
            "correlationId": correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        return json.dumps(message)

    async def connect(self) -> None:
        self.websocket = await websockets.connect(self.server_url)
        await self.websocket.send(self.build_message("CAR_CONNECT", {"vin": self.vin}))
        print(f"[SIM] Connected as {self.client_id}")
        await asyncio.gather(self.listen(), self.cli_loop())

    async def listen(self) -> None:
        assert self.websocket
        try:
            async for raw in self.websocket:
                msg = json.loads(raw)
                await self.handle_message(msg)
        except websockets.ConnectionClosed:
            print("[SIM] Connection closed")

    async def cli_loop(self) -> None:
        while True:
            print("\n--- Car Simulator ---")
            print("1) Toggle doors (current: {})".format("closed" if self.doorsClosed else "open"))
            print("2) Toggle lights (current: {})".format("off" if self.lightsOff else "on"))
            print("3) Toggle engine (current: {})".format("off" if self.engineOff else "on"))
            print("4) Print state")
            choice = await asyncio.to_thread(input, "Select option: ")
            if choice == "1":
                self.doorsClosed = not self.doorsClosed
                print(f"[SIM] Doors closed: {self.doorsClosed}")
            elif choice == "2":
                self.lightsOff = not self.lightsOff
                print(f"[SIM] Lights off: {self.lightsOff}")
            elif choice == "3":
                self.engineOff = not self.engineOff
                print(f"[SIM] Engine off: {self.engineOff}")
            elif choice == "4":
                self.print_state()

    async def handle_message(self, message: dict) -> None:
        msg_type = message.get("type")
        correlation_id = message.get("messageId")
        if msg_type == "CAR_UNLOCK":
            self.locked = False
            self.doorsClosed = False
            print("[SIM] Received unlock -> doors opened")
        elif msg_type == "CAR_LOCK":
            self.locked = True
            self.doorsClosed = True
            print("[SIM] Received lock")
        elif msg_type == "CAR_STATE_QUERY":
            await self.respond_state(message.get("messageId"))
        elif msg_type == "REGISTER_CLIENT_OK":
            print("[SIM] Backend acknowledged connection")
        elif msg_type == "NOTIFY":
            print(f"[SIM] Notification: {message.get('payload')}")
        if correlation_id and msg_type == "CAR_STATE_QUERY":
            return

    async def respond_state(self, correlation_id: str | None) -> None:
        if not self.websocket:
            return
        payload = {
            "vin": self.vin,
            "doorsClosed": self.doorsClosed,
            "lightsOff": self.lightsOff,
            "engineOff": self.engineOff,
            "locked": self.locked,
        }
        response = {
            "clientId": self.client_id,
            "messageId": str(uuid4()),
            "type": "CAR_STATE_RESPONSE",
            "correlationId": correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        await self.websocket.send(json.dumps(response))

    def print_state(self) -> None:
        print(
            f"[SIM] State -> locked:{self.locked} doorsClosed:{self.doorsClosed} "
            f"lightsOff:{self.lightsOff} engineOff:{self.engineOff}"
        )


async def main() -> None:
    vin = input("Enter VIN: ").strip() or "VIN0001"
    url = input("WebSocket URL [ws://localhost:8000/ws]: ").strip() or "ws://localhost:8000/ws"
    simulator = CarSimulator(vin=vin, server_url=url)
    await simulator.connect()


if __name__ == "__main__":
    asyncio.run(main())
