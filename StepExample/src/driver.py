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

        # Intialize the board connection with the found COM port and set the baud rate to 115200
        ESP32 = PyCmdMessenger.ArduinoBoard(comPort, baud_rate=115200, timeout=3)
        log.debug(f"Using board: {ESP32}")


         # Define the commands that will be used for communication with the microcontroller, these must match the commands defined in the Arduino sketch
        commands = [["kWatchdog", "s"], # Each command is defined with a name and a format string for the type of arguments it takes
                    ["kAcknowledge", "s"],
                    ["kError", "s"],
                    ["kGetState", ""],
                    ["kGetStateResult", "?I?"],
                    ["kGetLastStep", ""],
                    ["kGetLastStepResult", "??L?I?"],
                    ["kStep", "?I?L"],
                    ["kStop", ""],
                    ["kStepDone", ""], ]

        # Initialize the Cmdmessenger commander with the board and the defined commands
        self.comm = PyCmdMessenger.CmdMessenger(ESP32, commands)
        log.info("Messenger initialized")
        # Wait for arduino to come up
        msg = self.comm.receive()
        log.info(f"Initial communication: {msg}")

    def stopPumps(self):
        """Function for stopping all pumps."""
        log.info("Sending stop command to all pumps")
        self.comm.send("kStop")
        try:
            # Wait for a response from the microcontroller after sending the stop command
            # This will block until a response is received or a timeout occurs
            msg = self.comm.receive()
            # Print the response message for debugging purposes
            log.info(f"Stop pumps response: {msg[1]}")
            return msg[1]
        except EOFError as e:
            log.warning(f"No or incomplete response to stop command: {e}")
            return "No response"


    def getState(self):
        """Get the current state of the microcontroller."""
        log.info("Getting microcontroller state")
        # Initialize an empty list to hold the result of the state query
        result = []
        # Send a command to the microcontroller to request its current state
        self.comm.send("kGetState")

        # Receive state data
        msg = self.comm.receive()
        # Strip the first element of the message (the command name) and store the rest in result
        result = msg[1]
        log.info(f"Current state: {result}")

        return result

    def get_state_pretty(self):
        """
        Pretty wrapper for getState
        
        Returns state in a processed format:
        - If state is a list: converts to dictionary with pumpA and pumpB keys
        - Otherwise returns the raw state
        """
        raw_state = self.getState()
        
        # If state is a list in the format [stateA, speedA, dirA, stateB, speedB, dirB]
        if isinstance(raw_state, list) and len(raw_state) >= 3:
            # Convert to dictionary format for easier processing
            return {
                "pumpA": {
                    "state": bool(raw_state[0]),
                    "speed": int(raw_state[1]),
                    "dir": bool(raw_state[2])
                },
                
            }
        # Return raw state if not in expected list format
        return raw_state

    def getLastStep(self):
        """Get the last pump step command sent to the microcontroller."""
        log.info("Getting last step information")
        result = []
        self.comm.send("kGetLastStep")

        # Receive state data
        msg = self.comm.receive()

        result = msg[1]
        log.info(f"Last step: {result}")

        return result


    def set_state(self, stateA: bool = False, speedA: int = 0, dirA: bool = True, stepTime: int = 50000):
        """
        Set the state of pumps A, B, C and the LEDs
        """
        log.info(f"Setting state: A={stateA},{speedA},{dirA} time={stepTime}")
        try:
            # Send the command to set the state of the pumps to the microcontroller
            self.comm.send("kStep", stateA, speedA, dirA, stepTime)
            msg = self.comm.receive()
            log.info(msg)
            log.info(f"State set response: {msg[1]}")
            return True
        except Exception as e:
            log.error(f"Error setting state: {e}")
            return False

    
    def check_for_step_done(self) -> bool:
        """Check if the current step operation has completed."""
        log.debug("Checking for step completion")
        try:
            # Wait for a response from the microcontroller indicating whether the step operation is done
            msg = self.comm.receive()
            # Check for a non empty message
            if msg is not None:
                log.debug(f"Step check message: {msg[0]}")
            # Check if the message has the correct header indicating that the step operation is done
            if msg is not None and msg[0] == "kStepDone":
                log.info("Step operation completed")
                # Fetch the current state after the step is done
                current_state = self.getState()
                log.info(f"Fetched state after stop command: {current_state}")
                return True
        except EOFError as e:
            log.warning(f"Incomplete message when checking for step done: {e}")
        return False

    def close(self):
        """
        Closes the serial connection.
        """
        try:
            self.ser.close()
            log.info("Serial connection closed")
        except Exception as e:
            log.error(f"Error closing connection: {str(e)}")



def main():
    """Main function for testing the service directly."""
    module = RealMicrocontrollerService()
    # Set the state of the pumps and the time for the step, initiates a step operation
    module.set_state(stateA = True, speedA = 4096, dirA = True, stepTime = 50000)

    # Get the last step information
    module.getLastStep()
    state_ = True
    # Wait for a step to complete
    while not module.check_for_step_done():
        log.info("Waiting for step to complete...")
        time.sleep(1)
        state_ = not state_
        module.set_state(stateA = state_, speedA = 4096, dirA = True, stepTime = 50000)




if __name__ == "__main__":
    main()