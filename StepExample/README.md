# StepExample

PlatformIO firmware example for an Adafruit Metro ESP32-S2 that controls pumps over a serial connection, using steps as the main model to trigger actions in the pumps

## Basic functionality

- Initializes the pump driver and serial communication when the board starts.
- Accepts a timed `kStep` command containing pump A's requested state, speed, direction, and duration.
- Starts or stops pump A immediately according to the command.
- Stops the active pumps automatically when the step duration expires.
- Sends `kStepDone` when a step finishes.
- Accepts `kStop` to stop all pumps and clear the active step.
- Reports the current pump output with `kGetState`.
- Reports the most recently received step with `kGetLastStep`.
- Rejects a new step while another step is running and returns `kError: Busy`.

This example currently reads, applies, and reports pump A in the command handlers. 

## Step versus pump state

A **step** is a timed operation request. It describes what a pump should do and how long the operation should run. The current step includes:

- Requested pump A state: on or off
- Requested speed
- Requested direction
- Duration in milliseconds
- Lifecycle information: running or not, complete or not, and start time

Pump **state** is the current hardware/output condition. For pump A it includes:

- `state`: whether the pump is enabled
- `speed`: the configured PWM value
- `dir`: the configured direction

The distinction matters because a step is a command with a timer, while pump state is the result currently applied to the motor driver. When a step starts, its requested values are copied to the pump state and the output is changed immediately. When the timer expires, the firmware stops the pumps and sends `kStepDone`; the step then becomes inactive. A stop command can also change the pump state before the requested step duration has elapsed.

## Serial commands

The Python command definitions use these payload formats:

| Command | Payload | Purpose |
| --- | --- | --- |
| `kStep` | `bool stateA`, `uint16 speedA`, `bool dirA`, `unsigned long time` | Start a timed pump A operation |
| `kStop` | none | Stop all pumps immediately |
| `kGetState` | none | Request current pump state |
| `kGetLastStep` | none | Request current step information |
| `kWatchdog` | none | Request the board identifier |


## Building and uploading

Use the control buttons at the bottom of VSCode or run the following commands in the terminal

```bash
# build
platformio run
# build and upload (choose your environment in platformio.ini)
platformio run --target upload
```

## Python host service

Install the Python dependencies listed in `requirements.txt`:

```text
python -m pip install -r requirements.txt
```

`RealMicrocontrollerService` discovers the serial port, connects at `115200` baud, and provides methods to set state, read state, read the last step, stop the pumps, and wait for `kStepDone`.

## Typical workflow

1. Build/upload firmware to your board with PlatformIO.
2. Run the Python driver to exercise commands and observe responses:

```bash
# (with venv activated)
python src/driver.py
```