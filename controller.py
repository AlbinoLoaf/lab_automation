import json
import os
import sys
import time
import uuid
import requests
from dataclasses import dataclass
from typing import Dict
import numpy as np
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
        self.data: int = 0
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.data = int(loaded)
            except Exception as e:
                print(
                    f"Warning: Could not load tracker data: {e}", file=sys.stderr)

    def _save(self) -> None:
        try:
            parent_dir = os.path.dirname(self.filepath)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(
                f"Warning: Could not save tracker data: {e}", file=sys.stderr)

    def add_usage(self, pump: str, duration_ms: int) -> None:
        pump = pump.lower()
        if pump == "pumpc":
            duration_ms = -duration_ms
        if self.data + duration_ms > 0:
            self.data += duration_ms
        else:
            self.data = 0
        self._save()

    def print_stats(self) -> None:
        print("--- Cumulative Liquid Tracker ---")
        print(f"Current Volume: {self.data} ms")


class SensorReadings:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data: Dict[str, list] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.data.update(loaded)
            except Exception as e:
                print(
                    f"Warning: Could not load sensor data: {e}", file=sys.stderr)

    def _save(self) -> None:
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(
                f"Warning: Could not save tracker data: {e}", file=sys.stderr)

    def add_reading(self, reading_nr, sensor_data) -> None:
        self.data.update({reading_nr: sensor_data})
        self._save()


class RobotController:
    def __init__(self, base_url: str):
        self.base_url = base_url
        curr_time = time.strftime('%d%m%Y_%H%M')
        self.tracker = LiquidTracker(f"tracking/{curr_time}")
        self.sensor_readings = SensorReadings(f"sensor_readings/{curr_time}")
        self.reading_nr = 1
        self.opt = BayesianOptimiser(bounds=[(500.0, 5000.0), (500.0, 5000.0)])

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

        requests.post(f"{self.base_url}/actions", json=payload)
        self.wait_until_ready()
        self.tracker.add_usage(pump_key,cfg.duration)
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
            self.sensor_readings.add_reading(self.reading_nr, readings)
            self.reading_nr += 1
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
    
    def run_pump_by_params(self, pump: str, direction: bool, duration: int, speed: int = 4095) -> None:
        self.run_pump(PumpConfig(pump=pump, direction=direction, duration=duration, speed=speed))