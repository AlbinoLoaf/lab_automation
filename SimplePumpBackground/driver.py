import os
import PyCmdMessenger
import time
import logging
from find_port import find_port

def get_logger(name):
    logging.basicConfig(level=logging.DEBUG)
    return logging.getLogger(name)

log = get_logger(__name__)

class RealMicrocontrollerService:
    """
    The actual microcontroller service for connecting to hardware.
    """

    def __init__(self):
        log.info("Initializing microcontroller service")
        found, comPort = find_port("0000000-0000-0000-0000-00000000001")

        if found:
            log.info(f"Connected to the device: {comPort}")
        else:
            log.error("No suitable device found.")
            exit()

        self._current_port_id = 1

        # Initialize the board connection
        ESP32 = PyCmdMessenger.ArduinoBoard(comPort, baud_rate=115200, timeout=3)
        log.debug(f"Using board: {ESP32}")

        # Command schema matching Arduino enums and binary payloads
        commands = [
            ["kWatchdog", "s"],
            ["kAcknowledge", "s"],
            ["kError", "s"],
            ["kGetState", ""],
            ["kGetStateResult", "?I?"],
            ["kGetLastStep", ""],
            ["kGetLastStepResult", "??L?I?"],
            ["kStep", "?I??I??I?L"],  # Pumps A, B, C (state, speed, dir) + duration
            ["kStop", ""],
            ["kStepDone", ""],
            ["kReadSensor", ""],
            ["kSensorResult", "18H"],
        ]

        self.comm = PyCmdMessenger.CmdMessenger(ESP32, commands)
        log.info("Messenger initialized")

        # Wait for arduino boot message
        msg = self.comm.receive()
        log.info(f"Initial communication: {msg}")

    def read_sensor(self):
        """Read spectral data from the AS7343 sensor."""
        log.info("Requesting sensor reading")
        try:
            self.comm.send("kReadSensor")
            msg = self.comm.receive()
            if msg and msg[0] == "kSensorResult":
                return list(msg[1])
            if msg and msg[0] == "kError":
                log.error(f"Sensor error from Arduino: {msg[1]}")
            return []
        except Exception as e:
            log.error(f"Error reading sensor: {e}")
            return []

    def stopPumps(self):
        """Function for stopping all pumps."""
        log.info("Sending stop command to all pumps")
        self.comm.send("kStop")
        try:
            msg = self.comm.receive()
            log.info(f"Stop pumps response: {msg[1] if msg else 'None'}")
            return msg[1] if msg else "No response"
        except EOFError as e:
            log.warning(f"No or incomplete response to stop command: {e}")
            return "No response"

    def getState(self):
        """Get the current state of the microcontroller."""
        log.info("Getting microcontroller state")
        self.comm.send("kGetState")
        msg = self.comm.receive()
        result = msg[1] if msg else []
        log.info(f"Current state: {result}")
        return result

    def get_state_pretty(self):
        raw_state = self.getState()
        if isinstance(raw_state, list) and len(raw_state) >= 3:
            return {
                "pumpA": {
                    "state": bool(raw_state[0]),
                    "speed": int(raw_state[1]),
                    "dir": bool(raw_state[2])
                }
            }
        return raw_state

    def getLastStep(self):
        log.info("Getting last step information")
        self.comm.send("kGetLastStep")
        msg = self.comm.receive()
        result = msg[1] if msg else []
        log.info(f"Last step: {result}")
        return result

    def set_state(
        self,
        stateA: bool = False, speedA: int = 0, dirA: bool = True,
        stateB: bool = False, speedB: int = 0, dirB: bool = True,
        stateC: bool = False, speedC: int = 0, dirC: bool = True,
        stepTime: int = 50000
    ):
        """Set the state of pumps A, B, C and run duration."""
        log.info(
            f"Setting state: A=({stateA},{speedA},{dirA}), "
            f"B=({stateB},{speedB},{dirB}), "
            f"C=({stateC},{speedC},{dirC}), time={stepTime}"
        )
        try:
            self.comm.send(
                "kStep",
                stateA, speedA, dirA,
                stateB, speedB, dirB,
                stateC, speedC, dirC,
                stepTime
            )
            msg = self.comm.receive()
            log.info(f"State set response: {msg}")
            return True
        except Exception as e:
            log.error(f"Error setting state: {e}")
            return False

    def check_for_step_done(self) -> bool:
        """Check if the current step operation has completed."""
        try:
            msg = self.comm.receive()
            if msg is not None:
                log.debug(f"Step check message: {msg[0]}")
            if msg is not None and msg[0] == "kStepDone":
                log.info("Step operation completed")
                return True
        except EOFError as e:
            log.warning(f"Incomplete message when checking for step done: {e}")
        return False

    def close(self):
        try:
            self.comm.board.close()
            log.info("Serial connection closed")
        except Exception as e:
            log.error(f"Error closing connection: {str(e)}")