import json
import os
import sys
import time
import uuid
import requests
import time
from dataclasses import dataclass
from typing import Dict


@dataclass
class PumpConfig:
    pump: str
    direction: bool
    duration: int
    speed: int


class LiquidTracker:
    """Tracks cumulative pump runtimes to estimate liquid usage."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data: Dict[str, int] = {"a": 0, "b": 0, "c": 0}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.data.update(loaded)
            except Exception as e:
                print(
                    f"Warning: Could not load tracker data: {e}", file=sys.stderr)

    def _save(self) -> None:
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(
                f"Warning: Could not save tracker data: {e}", file=sys.stderr)

    def add_usage(self, pump: str, duration_ms: int) -> None:
        pump = pump.lower()
        if pump in self.data:
            self.data[pump] += duration_ms
            self._save()

    def print_stats(self) -> None:
        print("--- Cumulative Pump Usage ---")
        for p, ms in self.data.items():
            print(f"Pump {p.upper()}: {ms / 1000:.1f} seconds")


class RobotController:
    def __init__(self, base_url: str):
        self.base_url = base_url
        path = f"tracking/{time.strftime('%d%m%Y_%H%M')}"
        self.tracker = LiquidTracker(path)

    def wait_until_ready(self) -> None:
        """Blocks until the hardware is no longer busy."""
        while True:
            try:
                resp = requests.get(f"{self.base_url}/status").json()
                if not resp.get("busy"):
                    return
            except requests.ConnectionError:
                print(
                    f"Error: Could not connect to {self.base_url}", file=sys.stderr)
                sys.exit(1)
            time.sleep(0.2)

    def run_pump(self, cfg: PumpConfig) -> None:
        self.wait_until_ready()

        payload = {
            "id": str(uuid.uuid4()),
            "time": cfg.duration
        }

        pump_key = f"pump{cfg.pump.upper()}"
        payload[pump_key] = {
            "state": True,
            "speed": cfg.speed,
            "dir": not cfg.direction if cfg.pump.upper() == "A" else cfg.direction
        }

        print(f"Running Pump {cfg.pump.upper()} for {cfg.duration}ms...")
        self.tracker.add_usage(cfg.pump.upper(), cfg.duration)

        requests.post(f"{self.base_url}/actions", json=payload)
        self.wait_until_ready()
        print("Done.")

    def read_sensor(self) -> list:
        """Retrieves the latest spectral sensor readings."""
        print("Requesting sensor data...", file=sys.stderr)
        try:
            resp = requests.get(
                f"{self.base_url}/sensor",
                headers={"accept": "application/json"}
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") == "error":
                print(f"Sensor Error: {data.get('message')}", file=sys.stderr)
                return data.get("readings", [])

            readings = data.get("readings", [])
            return readings

        except Exception as e:
            print(f"Failed to fetch sensor readings: {e}", file=sys.stderr)
            return []

    def stop(self) -> None:
        """Triggers the emergency stop endpoint."""
        print("\nEmergency stop requested...", file=sys.stderr)
        try:
            requests.post(f"{self.base_url}/stop")
            print("Robot stopped.", file=sys.stderr)
        except Exception as e:
            print(f"Failed to send stop command: {e}", file=sys.stderr)

    def clean(self) -> None:
        self.wait_until_ready()

        """ payload = {
            "id": str(uuid.uuid4()),
            "time": 30000
        }

        pump_key = f"c"
        payload[pump_key] = {
            "state": True,
            "speed": 2000,
            "dir": 1
        }

        requests.post(f"{self.base_url}/actions", json=payload) """
        print(f"Running cleaning process)")
        s = 4095
        reservoir_contains = self.tracker.data.get(
            "a") + self.tracker.data.get("b")
        self.run_pump(PumpConfig("c", 1, reservoir_contains, s))
        # Fill the reservoir tube a little, to remove the excess colored water stuck at the bottom.
        self.run_pump(PumpConfig("b", 1, 5000, s))
        self.run_pump(PumpConfig("c", 1, 8000, s))
        # Fill up the tube with clean water, empty it
        self.run_pump(PumpConfig("b", 1, 40000, s))
        self.run_pump(PumpConfig("c", 1, 45000, s))

        print("Cleaning done.")

    def reset_robot(self) -> None:
        self.clean()
        s = 4095
        self.run_pump(PumpConfig("a", 0, 5000, s))
        self.run_pump(PumpConfig("b", 0, 5000, s))
