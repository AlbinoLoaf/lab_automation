#include <Arduino.h>
#include <Wire.h>
#include <SparkFun_AS7343.h>
#include <CmdMessenger.h>
#include "dataModel.h"
#include "df4MotorDriver.h"

CmdMessenger cmdMessenger(Serial, ',', ';', '/');
SfeAS7343ArdI2C sensor;

// This is the list of recognized commands. These can be commands that can either be sent or received.
// In order to receive, attach a callback function to these events
void OnUnknownCommand();
void OnWatchdogRequest();
void OnArduinoReady();
void OnGetState();
void OnGetLastStep();
void OnReceiveStep();
void OnReceiveStop();
void OnReadSensor();


void returnState();
void returnLastStep();
void receiveStep();
void receiveStop();

// Command IDs for the commands we send from the Arduino and want to receive on the PC.
enum
{
  // Commands
  kWatchdog,          // Command to request application ID
  kAcknowledge,       // Command to acknowledge a received command
  kError,             // Command to message that an error has occurred
  kGetState,          // Command to get the pump states
  kGetStateResult,    // Command to send the full state of the pumps
  kGetLastStep,       // Command to get the current step
  kGetLastStepResult, // Command to send the current step
  kStep,              // Command to receive a step (pump state + time), should always contain the full state of the pumps
  kStop,              // Command to stop all pumps
  kStepDone,          // Command to signal a step done
  kReadSensor,
  kSensorResult
  
};

// Commands we send from the PC and want to receive on the Arduino.
// We must define a callback function in our Arduino program for each entry in the list below.
void attachCommandCallbacks()
{
  // Attach callback methods
  cmdMessenger.attach(OnUnknownCommand);
  cmdMessenger.attach(kWatchdog, OnWatchdogRequest);
  cmdMessenger.attach(kGetState, OnGetState);
  cmdMessenger.attach(kGetLastStep, OnGetLastStep);
  cmdMessenger.attach(kStep, OnReceiveStep);
  cmdMessenger.attach(kStop, OnReceiveStop);
  cmdMessenger.attach(kReadSensor, OnReadSensor); 
}

// ------------------  C A L L B A C K S -----------------------


// Called when a received command has no attached function
void OnUnknownCommand()
{
  cmdMessenger.sendCmd(kError, "Command without attached callback");
}

// Called when a received command is a watchdog request
void OnWatchdogRequest()
{
  // Will respond with same command ID and Unique device identifier.
  cmdMessenger.sendCmd(kWatchdog, "0000000-0000-0000-0000-00000000001");
}

// Callback function that responds that Arduino is ready (has booted up)
void OnArduinoReady()
{
  cmdMessenger.sendCmd(kAcknowledge, "Arduino ready");
}

// Callback function that responds with the current state of the pumps
void OnGetState()
{
  returnState();
}
// Callback function that responds with the last run step of the pumps
void OnGetLastStep()
{
  returnLastStep();
}

// Callback function that receives a step command, sets the pumps accordingly and starts a timer to stop the pumps after the specified time
void OnReceiveStep()
{
  receiveStep();
}

// Callback function that receives a stop command and stops all pumps
void OnReceiveStop()
{
  receiveStop();
}

void OnReadSensor()
{
  uint16_t readings[18] = {0};

  if (sensor.readSpectraDataFromSensor() &&
      sensor.getData(readings, 18) == 18)
  {
    cmdMessenger.sendCmdStart(kSensorResult);
    for (int i = 0; i < 18; i++)
    {
      cmdMessenger.sendCmdBinArg<uint16_t>(readings[i]);
    }
    cmdMessenger.sendCmdEnd();
  }
  else
  {
    cmdMessenger.sendCmd(kError, "Sensor read failed");
  }
}

void setup() {
  // Start the serial port
  Serial.begin(115200);
  Wire.begin();

  if (!sensor.begin())
  {
    cmdMessenger.sendCmd(kError, "AS7343 initialization failed");
  }


  // Setup the IO pins for the pumps and initialize the pump state
  setupPumps();
  
  //  Do not print newLine at end of command,
  //  in order to reduce data being sent
  cmdMessenger.printLfCr(false);
  
  // Attach my application's user-defined callback methods
  attachCommandCallbacks();

  // Send a command to the PC to indicate that the Arduino has started
  cmdMessenger.sendCmd(kAcknowledge, "Arduino has started!");
 
}

void loop() {
  
  // Wait for a command to arrive, and call the appropriate callback function when it does.
  cmdMessenger.feedinSerialData();

  // Check if a step is currently running and if it has completed
  if (currentStep.state)
  {
    // Check if the step has completed by comparing the current time with the start time and the duration of the step
    if (!currentStep.done)
    {
      // Check if the current time minus the start time is greater than or equal to the duration of the step
      if (millis() - currentStep.stepStartTime >= currentStep.time)
      {
        // If the step has completed, set the done flag to true, stop all pumps, and send a command to the PC indicating that the step is done
        currentStep.done = true;
        stopPumps();
        cmdMessenger.sendCmd(kStepDone);
      }
    }
    else
    {
      // If the step is done, reset the state of the current step to false
      currentStep.state = false;
    }
  }

}

// ------------------  C O M M A N D   H A N D L I N G -----------------------
// Callback function that responds with the current state of the pumps
void returnState()
{
  // Send the state result header
  cmdMessenger.sendCmdStart(kGetStateResult);

  // Send the state of pump A as the body of the message, including the state, speed, and direction of the pump
  cmdMessenger.sendCmdBinArg<bool>(pumpA.state);
  cmdMessenger.sendCmdBinArg<uint16_t>(pumpA.speed);
  cmdMessenger.sendCmdBinArg<bool>(pumpA.dir);
  
  // Send the end of the message
  cmdMessenger.sendCmdEnd();
}

// Callback function that responds with the last run step of the pumps
void returnLastStep()
{
  cmdMessenger.sendCmdStart(kGetLastStepResult);

  // Send the state of the current step as the body of the message, including the state, done flag, time, and the state, speed, and direction of pump A
  cmdMessenger.sendCmdBinArg<bool>(currentStep.state);
  cmdMessenger.sendCmdBinArg<bool>(currentStep.done);
  cmdMessenger.sendCmdBinArg<unsigned long>(currentStep.time);

  cmdMessenger.sendCmdBinArg<bool>(currentStep.stateA);
  cmdMessenger.sendCmdBinArg<uint16_t>(currentStep.speedA);
  cmdMessenger.sendCmdBinArg<bool>(currentStep.dirA);
  
  // Send the end of the message
  cmdMessenger.sendCmdEnd();
}

// Callback function that receives a step command, sets the pumps accordingly and starts a timer to stop the pumps after the specified time
void receiveStep()
{
   
  // Check if a step is currently running and if it has completed
  if (currentStep.state && !currentStep.done)
  { 
    // Read the arguments from the command message, but do not use them since a step is already running
    cmdMessenger.readBinArg<bool>();
    cmdMessenger.readBinArg<uint16_t>();
    cmdMessenger.readBinArg<bool>();

    cmdMessenger.readBinArg<unsigned long>();
    // Send an error message back to the PC indicating that a step is already running and cannot be started again
    cmdMessenger.sendCmd(kError, "Busy");

  }
  else
  { 
    // Read the arguments from the command message and set the state, speed, and direction of pump A accordingly
    currentStep.stateA = cmdMessenger.readBinArg<bool>();
    currentStep.speedA = cmdMessenger.readBinArg<uint16_t>();
    currentStep.dirA = cmdMessenger.readBinArg<bool>();
    
    currentStep.stateB = cmdMessenger.readBinArg<bool>();
    currentStep.speedB = cmdMessenger.readBinArg<uint16_t>();
    currentStep.dirB = cmdMessenger.readBinArg<bool>();
    
    currentStep.stateC = cmdMessenger.readBinArg<bool>();
    currentStep.speedC = cmdMessenger.readBinArg<uint16_t>();
    currentStep.dirC = cmdMessenger.readBinArg<bool>();
    
    currentStep.time = cmdMessenger.readBinArg<unsigned long>(); 
    // Change the state of pump A based on the received command
    if (currentStep.stateA) StartPumpA(currentStep.speedA, currentStep.dirA); else StopPumpA();
    if (currentStep.stateB) StartPumpB(currentStep.speedB, currentStep.dirB); else StopPumpB();
    if (currentStep.stateC) StartPumpC(currentStep.speedC, currentStep.dirC); else StopPumpC();
    currentStep.state = true;
  currentStep.done = false;
  currentStep.stepStartTime = millis();

  cmdMessenger.sendCmd(kAcknowledge, "Step started");
}
}

// Callback function that receives a stop command and stops all pumps
void receiveStop()
{
  
  stopPumps();
  
  currentStep.done = true;
  currentStep.state = false;
  cmdMessenger.sendCmd(kAcknowledge, "Stopped");
}

