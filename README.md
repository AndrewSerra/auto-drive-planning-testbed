# Autonomous Path Planning Testbed

> Built at Rochester Institute of Technology as an Independent Study

## Description

A testbed for developing and testing autonomous path planning algorithms. A Python server processes a live camera feed to calibrate the workspace, detect boundaries, and compute a grid-based planning environment. It then communicates planned paths to a small ESP32-based car over WiFi/WebSocket.

The goal is a closed-loop system: the camera acts as the "eyes," the server acts as the "brain," and the car acts as the "body."

## Components

### Testbed Server (`testbed-server/`)

Python-based vision and planning server.

- **Camera Calibration** — Uses AprilTag markers (36H11 family) placed at workspace corners to compute a bird's-eye homography transform, correcting for camera perspective
- **Boundary Detection** — Derives the physical workspace boundary from the calibrated AprilTag positions
- **Grid-Based Planning Workspace** — Projects the workspace onto a configurable grid (default 50×50, set in `config.json`) for use by path planning algorithms
- **WebSocket Communication** *(in progress)* — Sends planned paths to the car over WiFi via a WebSocket server

**Key dependencies:** OpenCV 4.13, NumPy, websockets, asyncio

### Car Software (`car-software/`)

Firmware for the ESP32 microcontroller, written in C using ESP-IDF.

- **FreeRTOS State Machine** — Task-based architecture managing the car's operating states
- **WiFi Connectivity** — Connects to a local network to receive commands from the testbed server
- **LED State Indicators** — Visual feedback of the current system state via onboard LEDs
- **Hardware Timer-Driven I/O** — Precise motor and sensor control via hardware timers

**Toolchain:** ESP32, ESP-IDF, FreeRTOS, C, CMake

## How It Works

1. **Calibrate** — AprilTag markers (36H11 family) are placed at the corners of the physical workspace. The server detects them and computes a homography to produce a bird's-eye view.
2. **Detect Boundary** — The server derives the workspace boundary from the tag positions.
3. **Build Grid** — The flattened workspace is mapped onto a 2D grid for planning.
4. **Plan** — A path planning algorithm computes a route across the grid.
5. **Send to Car** — The planned path is transmitted to the ESP32 car over WebSocket.
6. **Execute** — The car drives the received path using its FreeRTOS state machine.

## Project Structure

```
auto-planning-software-testbed/
├── testbed-server/          # Python vision + planning server
│   ├── config.json          # Grid size and runtime config
│   ├── pyproject.toml       # Python dependencies (uv)
│   └── ...
├── car-software/            # ESP32 firmware (ESP-IDF/C)
│   ├── CMakeLists.txt
│   └── ...
└── README.md
```

## Setup & Build

### Testbed Server

Install Python dependencies using [uv](https://docs.astral.sh/uv/):

```bash
cd testbed-server
uv sync
```

Key dependencies: `opencv-python` (4.13), `numpy`, `websockets`

### Car Software

Requires the [ESP-IDF toolchain](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/).

```bash
cd car-software
idf.py build
idf.py flash
```
