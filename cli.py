from __future__ import annotations
import argparse
import sys
import shlex
from typing import Optional

from controller import PumpConfig, LiquidTracker, RobotController

TRACKER_FILE = "liquid_tracker.json"

def parse_direction(val: str) -> bool:
    val = val.lower()
    if val in ("in", "ind", "true", "1"):
        return True
    if val in ("out", "ud", "false", "0"):
        return False
    raise argparse.ArgumentTypeError(f"Invalid direction: {val}")

class REPLParser(argparse.ArgumentParser):
    """Custom parser that prevents argparse from calling sys.exit() on bad input."""
    def error(self, message: str) -> None:
        print(f"Error: {message}", file=sys.stderr)
        self.print_help(sys.stderr)
        raise ValueError(message)
    
    def exit(self, status: int = 0, message: Optional[str] = None) -> None:
        if message:
            print(message, file=sys.stderr)
        raise ValueError(message)

def get_interactive_parser() -> argparse.ArgumentParser:
    parser = REPLParser(prog="", description="Lab Auto Robot REPL", add_help=False)
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run a pump (e.g., 'run b ind 100')")
    run_parser.add_argument("pump", choices=["a", "b", "c"], type=str.lower, help="Pump to activate (a, b, c)")
    run_parser.add_argument("direction", type=parse_direction, help="Direction (in/ind/out/ud)")
    run_parser.add_argument("duration", type=int, help="Duration in milliseconds")
    run_parser.add_argument("--speed", type=int, default=4095, help="Motor speed (0-4095)")
    clean_parser = subparsers.add_parser("clean", help="Run the cleaning sequence")
    stats_parser = subparsers.add_parser("stats", help="View liquid usage statistics")
    sensor_parser = subparsers.add_parser("sensor", help="Read the spectral sensor")
    return parser

def main(argv: Optional[list[str]] = None) -> int:
    startup_parser = argparse.ArgumentParser(description="Start the Interactive Lab Auto CLI")
    startup_parser.add_argument("--host", default="localhost", help="API server host (default: localhost)")
    startup_parser.add_argument("--port", type=int, default=8000, help="API server port (default: 8000)")
    startup_args = startup_parser.parse_args(argv)
    
    api_base = f"http://{startup_args.host}:{startup_args.port}"
    
    tracker = LiquidTracker(TRACKER_FILE)
    controller = RobotController(api_base)
    repl_parser = get_interactive_parser()

    print(f"Connected to {api_base}")
    print("Type 'help' for commands, or 'exit'/'quit' to close the CLI.")

    while True:
        try:
            # Read input
            user_input = input("\nlabotomy> ").strip()
            
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                break
            if user_input.lower() in ("help", "?"):
                repl_parser.print_help()
                continue
            try:
                args = repl_parser.parse_args(shlex.split(user_input))
            except ValueError:
                continue
            
            if not args.command:
                continue

            # Execute commands
            if args.command == "run":
                cfg = PumpConfig(
                    pump=args.pump,
                    direction=args.direction,
                    duration=args.duration,
                    speed=args.speed
                )
                controller.run_pump(cfg)
            
            elif args.command == "sensor":
                readings = controller.read_sensor()
                print(f"Readings: {readings}")
                tracker.add_usage(cfg.pump, cfg.duration)
                
            elif args.command == "clean":
                controller.clean()
                
            elif args.command == "stats":
                tracker.print_stats()

        except KeyboardInterrupt:
            controller.stop()
        except EOFError:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)

    return 0

if __name__ == "__main__":
    sys.exit(main())