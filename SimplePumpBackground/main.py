from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException
from driver import RealMicrocontrollerService, get_logger

import time
from typing import Set
import json

from action_models import ActionRequest

import asyncio
import os
import httpx

## Create a FastAPI instance
app = FastAPI()
# Start the microcontroller service
micro = RealMicrocontrollerService() # Uses the same step model as the StepExample

# Set the namespace for logging
log = get_logger(__name__)
# Set global flags for busy state and stop request
busy = False
stop_requested = False

# Global variable to hold the main event loop
main_event_loop = None

# Function that runs on app startup to get the main event loop
@app.on_event("startup")
async def startup_event():
    global main_event_loop
    # Get the current running asyncio event loop and store it in the global variable
    main_event_loop = asyncio.get_running_loop()

# API Endpoints, run http://localhost:8000/docs for quick documentation and testing
@app.post("/actions")
async def perform_actions(request: ActionRequest, background_tasks: BackgroundTasks): # Use the ActionRequest model for request validation and background_tasks for async processing
    global busy, stop_requested
    if busy:
        return {"status": "busy"}
    busy = True
    stop_requested = False

    # Run the action_task in the background to avoid blocking the main thread
    background_tasks.add_task(action_task, request)
    return {"status": "accepted", "id": request.id}

@app.post("/stop")
async def emergency_stop(): # Trigger an emergency stop of the pump and reset busy state
    global stop_requested, busy
    stop_requested = True
    busy = False  # Fallback: ensure busy is reset if stop is called
    log.info("/stop called: busy set to False")
    handle_stop("emergency_stop")  # Handle stopping everything and logging state
    return {"status": "stopped"}

# Returns the current busy state of the system
@app.get("/status")
def get_status():
    global busy
    return {"busy": busy} 

# --- Helper methods ---
def send_command_to_hardware(pumpA, duration):
    # Extract pump parameters
    stateA = pumpA.state if pumpA else False
    speedA = pumpA.speed if pumpA else 0
    dirA = pumpA.dir if pumpA else True
    
    
    # Send command to hardware
    micro.set_state(
        stateA, speedA, dirA,
        duration
    )
    
    return duration

def handle_stop(job_id):
    """Handles stopping everything, fetching/logging/streaming state, and sending notifications."""
    micro.stopPumps()  # Stop all pumps and steps
    try:
        # Get the current state after stopping everything
        current_state = micro.getState()
        log.info(f"Fetched state after stopping everything: {current_state}")
        state_msg = json.dumps({
            "event": "state_update",
            "state": current_state,
            "timestamp": time.time()
        })
    except Exception as e:
        log.error(f"Error fetching state after stopping everything: {e}")

def monitor_operations(job_id, pumpA, step_time):
    global busy, stop_requested
    pump_done = False
    start_time = time.time()

    # Check at regular intervals if the operation is complete or if a stop has been requested
    interval = 0.1


    while not (pump_done):
        now = time.time()
        elapsed = now - start_time
        # Stop requested: handle stop and exit
        if stop_requested:
            busy = False
            log.info("monitor_operations: busy set to False after stop_requested")
            handle_stop(job_id)  # Handle stopping everything and logging state
            return  # Exit the function gracefully after handling stop
        # --- HARD TIMEOUT ---
        # If the elapsed time exceeds the step_time plus a buffer, force completion
        if elapsed >= ((step_time / 1000)+1):
            log.info("monitor_operations: hard timeout reached, forcing completion")
            handle_stop(job_id)  # Handle stopping everything and logging state
            if not pump_done:
                pump_done = True
            break
        # --- NORMAL COMPLETION ---
        if not pump_done and micro.check_for_step_done():
            pump_done = True
        time.sleep(interval)

    busy = False
    log.info("monitor_operations: busy set to False after completion")

# --- Unified background task ---
def action_task(request: ActionRequest): # Filter pump and duration information from the request and send to hardware
    job_id = request.id
    pumpA = request.pumpA
    duration = request.time
    # Send motor command
    step_time = send_command_to_hardware(pumpA, duration)
    # Monitor operation
    monitor_operations(job_id, pumpA, step_time)



