"""Command-line helper that behaves like the phone app for demo purposes."""
import argparse
import json
import sys
from typing import Any, Dict, Optional

import requests


DEFAULT_HOST = "http://localhost:5000"


def print_response(resp: requests.Response) -> None:
    print(f"HTTP {resp.status_code}\n")
    try:
        payload = resp.json()
        print(json.dumps(payload, indent=2))
    except ValueError:
        print(resp.text)


def send(method: str, base_url: str, path: str, *, token: Optional[str] = None, body: Optional[Dict[str, Any]] = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = base_url.rstrip("/") + path
    resp = requests.request(method, url, headers=headers, json=body)
    print_response(resp)
    if not resp.ok:
        sys.exit(1)
    return resp.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Phone app simulator for the car sharing backend")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Backend base URL")
    sub = parser.add_subparsers(dest="command", required=True)

    reg = sub.add_parser("register", help="Create client profile")
    reg.add_argument("--name", required=True)
    reg.add_argument("--email", required=True)
    reg.add_argument("--license", required=True, help="Driver license id")
    reg.add_argument("--payment", required=True, help="Payment method description (card token, etc.)")
    reg.add_argument("--pin", required=True, help="Numeric PIN for login")

    login = sub.add_parser("login", help="Authenticate and get a token")
    login.add_argument("--email", required=True)
    login.add_argument("--pin", required=True)

    cars = sub.add_parser("cars", help="List available cars")
    cars.add_argument("--token", required=True)

    start = sub.add_parser("start", help="Start rental for a VIN")
    start.add_argument("--token", required=True)
    start.add_argument("--vin", required=True)

    end = sub.add_parser("end", help="End rental for a VIN")
    end.add_argument("--token", required=True)
    end.add_argument("--vin", required=True)

    telem = sub.add_parser("set-state", help="Simulate telematics state for a car")
    telem.add_argument("--vin", required=True)
    telem.add_argument("--doors", choices=["open", "closed"], help="Set door state")
    telem.add_argument("--lights", choices=["on", "off"], help="Set light state")
    telem.add_argument("--locked", choices=["true", "false"], help="Force lock state")

    args = parser.parse_args()
    host = args.host

    if args.command == "register":
        send(
            "POST",
            host,
            "/register",
            body={
                "name": args.name,
                "email": args.email,
                "driver_license": args.license,
                "payment_method": args.payment,
                "pin": args.pin,
            },
        )
    elif args.command == "login":
        send("POST", host, "/login", body={"email": args.email, "pin": args.pin})
    elif args.command == "cars":
        send("GET", host, "/cars", token=args.token)
    elif args.command == "start":
        send("POST", host, "/rentals/start", token=args.token, body={"vin": args.vin})
    elif args.command == "end":
        send("POST", host, "/rentals/end", token=args.token, body={"vin": args.vin})
    elif args.command == "set-state":
        body: Dict[str, Any] = {}
        if args.doors:
            body["doors_closed"] = args.doors == "closed"
        if args.lights:
            body["lights_off"] = args.lights == "off"
        if args.locked:
            body["locked"] = args.locked == "true"
        if not body:
            print("No state provided; nothing to update")
            sys.exit(1)
        send("PATCH", host, f"/cars/{args.vin}/telematics", body=body)
    else:
        parser.error("Unsupported command")


if __name__ == "__main__":
    main()
