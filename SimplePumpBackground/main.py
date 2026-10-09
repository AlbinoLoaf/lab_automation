from fastapi import FastAPI, BackgroundTasks
from driver import RealMicrocontrollerService, get_logger
import time
import json
import asyncio

app = FastAPI()
micro = RealMicrocontrollerService()
log = get_logger(__name__)

busy = False
stop_requested = False
main_event_loop = None

@app.on_event("startup")
async def startup_event():
    global main_event_loop
    main_event_loop = asyncio.get_running_loop()

@app.post("/actions")
async def perform_actions(request: dict, background_tasks: BackgroundTasks):
    global busy, stop_requested
    if busy:
        return {"status": "busy"}
    busy = True
    stop_requested = False

    background_tasks.add_task(action_task, request)
    return {"status": "accepted", "id": request.get("id")}

@app.post("/stop")
async def emergency_stop():
    global stop_requested, busy
    stop_requested = True
    busy = False
    log.info("/stop called: busy set to False")
    handle_stop("emergency_stop")
    return {"status": "stopped"}

@app.get("/status")
def get_status():
    global busy
    return {"busy": busy}

@app.get("/sensor", summary="Read Sensor")
def read_sensor():
    readings = micro.read_sensor()
    return {"readings": readings}

# --- Helper methods ---
def send_command_to_hardware(pumpA, pumpB, pumpC, duration):
    stateA = pumpA.get("state", False) if pumpA else False
    speedA = pumpA.get("speed", 0) if pumpA else 0
    dirA = pumpA.get("dir", True) if pumpA else True

    stateB = pumpB.get("state", False) if pumpB else False
    speedB = pumpB.get("speed", 0) if pumpB else 0
    dirB = pumpB.get("dir", True) if pumpB else True

    stateC = pumpC.get("state", False) if pumpC else False
    speedC = pumpC.get("speed", 0) if pumpC else 0
    dirC = pumpC.get("dir", True) if pumpC else True

    micro.set_state(
        stateA, speedA, dirA,
        stateB, speedB, dirB,
        stateC, speedC, dirC,
        duration
    )
    return duration

def handle_stop(job_id):
    micro.stopPumps()
    try:
        current_state = micro.getState()
        log.info(f"Fetched state after stopping everything: {current_state}")
    except Exception as e:
        log.error(f"Error fetching state after stopping everything: {e}")

def monitor_operations(job_id, step_time):
    global busy, stop_requested
    pump_done = False
    start_time = time.time()
    interval = 0.1

    while not pump_done:
        now = time.time()
        elapsed = now - start_time

        if stop_requested:
            busy = False
            log.info("monitor_operations: busy set to False after stop_requested")
            handle_stop(job_id)
            return

        if elapsed >= ((step_time / 1000) + 1):
            log.info("monitor_operations: hard timeout reached, forcing completion")
            handle_stop(job_id)
            pump_done = True
            break

        if not pump_done and micro.check_for_step_done():
            pump_done = True
        time.sleep(interval)

    busy = False
    log.info("monitor_operations: busy set to False after completion")

def action_task(request: dict):
    job_id = request.get("id")
    pumpA = request.get("pumpA")
    pumpB = request.get("pumpB")
    pumpC = request.get("pumpC")
    duration = request.get("time", 0)

    step_time = send_command_to_hardware(pumpA, pumpB, pumpC, duration)
    monitor_operations(job_id, step_time)