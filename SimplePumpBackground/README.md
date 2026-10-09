# SimplePumpBackground

A small FastAPI service for controlling the SimplePump hardware through a serial-connected microcontroller.

## How It Works

The application starts in `main.py`:

1. A FastAPI application is created.
2. `RealMicrocontrollerService` is initialized from `driver.py`. It scans for the configured device, opens the serial connection at `115200` baud, and sets up the `PyCmdMessenger` commands.
3. The service reuses the `SimplePump` example and the `Step` model from the `StepExample` to communicate with the hardware.
4. A request sent to `/actions` is validated with the `ActionRequest` model, queued as a background task, and translated into a pump step command.
5. The background task monitors the controller until it reports `kStepDone`, or until the timeout is reached.
6. `/stop` immediately sends `kStop` to stop the pump and clears the busy state.

Only one action can run at a time. While an action is active, another request to `/actions` returns `{"status": "busy"}`. The API does not block.

## Requirements

- Python 3.9 or newer
- A connected and powered SimplePump-compatible microcontroller
- The device must be discoverable through its serial number or description. The current configured identifier is in `driver.py`.

Install the Python dependencies:

```powershell
pip install -r requirements.txt
```

## Running the API

From this directory, start the development server with:

```powershell
uvicorn main:app --reload
```

The API is available at `http://localhost:8000`. Interactive documentation is available at `http://localhost:8000/docs`.

The hardware connection is initialized when `main.py` is imported, so the microcontroller should be connected before starting the server.

## Endpoints

### `POST /actions`

Queues a pump action and returns immediately.

Request body:

```json
{
  "id": "test-run-001",
  "time": 10000,
  "pumpA": {
    "state": true,
    "speed": 2000,
    "dir": true
  }
}
```

`time` is the step duration in milliseconds. `pumpA` is optional; when it is omitted, the driver sends the default inactive pump values.

Successful response:

```json
{
  "status": "accepted",
  "id": "test-run-001"
}
```

### `POST /stop`

Stops the pump immediately and returns:

```json
{
  "status": "stopped"
}
```

### `GET /status`

Returns whether an action is currently running:

```json
{
  "busy": false
}
```

## Project Files

- `main.py`: FastAPI application, endpoints, background execution, and operation monitoring.
- `driver.py`: Serial connection and `PyCmdMessenger` hardware commands.
- `action_models.py`: Pydantic request models for pump actions.
- `find_port.py`: Serial-port discovery and device matching.
- `requirements.txt`: Python dependencies.
