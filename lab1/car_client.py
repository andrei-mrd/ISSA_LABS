"""Simple telematics-side client for a specific car VIN.

This script turns a car into an active client:
- registers the car client session
- sends heartbeat updates
- pulls backend commands (lock/unlock)
- acknowledges executed commands
"""
import argparse
import json
import random
import sys
import time
from typing import Any, Dict, Optional

import requests


DEFAULT_HOST = "http://localhost:5000"
DEFAULT_API_KEY = "car-lab-key"


def print_response(resp: requests.Response) -> Dict[str, Any]:
    print(f"HTTP {resp.status_code}\n")
    try:
        payload = resp.json()
        print(json.dumps(payload, indent=2))
        return payload
    except ValueError:
        print(resp.text)
        return {}


def send(method: str, base_url: str, path: str, *, token: Optional[str] = None, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = base_url.rstrip("/") + path
    resp = requests.request(method, url, headers=headers, json=body)
    payload = print_response(resp)
    if not resp.ok:
        sys.exit(1)
    return payload


def register_car(host: str, vin: str, api_key: str) -> str:
    data = send("POST", host, "/car/register", body={"vin": vin, "api_key": api_key})
    token = data.get("car_token")
    if not token:
        print("Failed to obtain car token")
        sys.exit(1)
    return token


def heartbeat(host: str, token: str, *, locked: Optional[bool], doors_closed: Optional[bool], lights_off: Optional[bool], battery_pct: Optional[int]) -> Dict[str, Any]:
    body: Dict[str, Any] = {}
    if locked is not None:
        body["locked"] = locked
    if doors_closed is not None:
        body["doors_closed"] = doors_closed
    if lights_off is not None:
        body["lights_off"] = lights_off
    if battery_pct is not None:
        body["battery_pct"] = battery_pct
    return send("POST", host, "/car/heartbeat", token=token, body=body)


def pull_commands(host: str, token: str) -> Dict[str, Any]:
    return send("GET", host, "/car/commands", token=token)


def ack(host: str, token: str, command_id: str, success: bool = True, note: Optional[str] = None) -> Dict[str, Any]:
    body: Dict[str, Any] = {"command_id": command_id, "success": success}
    if note:
        body["note"] = note
    return send("POST", host, "/car/ack", token=token, body=body)


def run_loop(host: str, vin: str, api_key: str, interval: float, battery_start: int) -> None:
    token = register_car(host, vin, api_key)
    print(f"\nCar client token: {token}\n")

    locked = True
    doors_closed = True
    lights_off = True
    battery = max(0, min(100, battery_start))

    while True:
        heartbeat(host, token, locked=locked, doors_closed=doors_closed, lights_off=lights_off, battery_pct=battery)
        commands_payload = pull_commands(host, token)
        commands = commands_payload.get("commands", [])

        for command in commands:
            action = command.get("action")
            command_id = command.get("id")
            if action == "unlock":
                locked = False
            elif action == "lock":
                locked = True
            if command_id:
                ack(host, token, command_id, success=True)

        battery = max(0, battery - random.choice([0, 1]))
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Telematics-side car client")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Backend base URL")
    sub = parser.add_subparsers(dest="command", required=True)

    reg = sub.add_parser("register", help="Register car client and print token")
    reg.add_argument("--vin", required=True)
    reg.add_argument("--api-key", default=DEFAULT_API_KEY)

    hb = sub.add_parser("heartbeat", help="Send one heartbeat")
    hb.add_argument("--token", required=True)
    hb.add_argument("--locked", choices=["true", "false"])
    hb.add_argument("--doors", choices=["open", "closed"])
    hb.add_argument("--lights", choices=["on", "off"])
    hb.add_argument("--battery", type=int)

    cmds = sub.add_parser("commands", help="Pull pending commands")
    cmds.add_argument("--token", required=True)

    ack_cmd = sub.add_parser("ack", help="Acknowledge one command")
    ack_cmd.add_argument("--token", required=True)
    ack_cmd.add_argument("--command-id", required=True)
    ack_cmd.add_argument("--success", choices=["true", "false"], default="true")
    ack_cmd.add_argument("--note")

    loop = sub.add_parser("run", help="Run continuous heartbeat + command processing loop")
    loop.add_argument("--vin", required=True)
    loop.add_argument("--api-key", default=DEFAULT_API_KEY)
    loop.add_argument("--interval", type=float, default=2.0)
    loop.add_argument("--battery-start", type=int, default=100)

    args = parser.parse_args()

    if args.command == "register":
        token = register_car(args.host, args.vin, args.api_key)
        print(f"\nCar token: {token}")
    elif args.command == "heartbeat":
        locked = None if args.locked is None else args.locked == "true"
        doors_closed = None if args.doors is None else args.doors == "closed"
        lights_off = None if args.lights is None else args.lights == "off"
        heartbeat(
            args.host,
            args.token,
            locked=locked,
            doors_closed=doors_closed,
            lights_off=lights_off,
            battery_pct=args.battery,
        )
    elif args.command == "commands":
        pull_commands(args.host, args.token)
    elif args.command == "ack":
        ack(args.host, args.token, args.command_id, success=args.success == "true", note=args.note)
    elif args.command == "run":
        run_loop(args.host, args.vin, args.api_key, args.interval, args.battery_start)


if __name__ == "__main__":
    main()
