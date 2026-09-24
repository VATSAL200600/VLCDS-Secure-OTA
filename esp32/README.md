# ESP32-S2 DevKit M1 — VLCDS Setup Guide

## Overview

This guide covers how to set up and run the VLCDS (Version-Locked Chained Delta Signature) 
OTA update demo on your **ESP32-S2 DevKit M1** hardware.

**Architecture:**
```
┌──────────────────┐         WiFi          ┌──────────────────┐
│   PC (Server)    │ ◄──────────────────► │  ESP32-S2 Device │
│                  │                       │                  │
│ • Flask HTTP     │  1. Manifest (200B)   │ • Stage 1: Verify│
│ • Sign manifests │ ──────────────────►   │   manifest       │
│ • Create deltas  │                       │                  │
│ • Serve updates  │  2. Delta Patch       │ • Stage 2: Apply │
│                  │ ──────────────────►   │   delta patch    │
│                  │                       │                  │
│                  │                       │ • Stage 3: Post- │
│                  │                       │   verify hash    │
└──────────────────┘                       └──────────────────┘
```

## Prerequisites

- ESP32-S2 DevKit M1 board
- USB cable (USB-C or Micro-USB depending on your board)
- Python 3.10+ on PC
- WiFi network (both PC and ESP32 on same network)

## Step 1: Flash MicroPython on ESP32-S2

### 1a. Download MicroPython firmware

Visit: https://micropython.org/download/ESP32_GENERIC_S2/

Download the latest `.bin` file for ESP32-S2 (e.g., `ESP32_GENERIC_S2-20240602-v1.23.0.bin`).

### 1b. Install esptool

```bash
pip install esptool
```

### 1c. Put ESP32-S2 into bootloader mode

1. Hold the **BOOT** (or **0**) button on the board
2. While holding, press and release the **RESET** (or **RST**) button
3. Release the BOOT button
4. The board is now in bootloader mode

### 1d. Erase flash and flash MicroPython

```bash
# Find your COM port (check Device Manager on Windows)
# Replace COM3 with your actual port

# Erase flash
esptool --chip esp32s2 --port COM3 erase_flash

# Flash MicroPython
esptool --chip esp32s2 --port COM3 --baud 460800 write_flash -z 0x1000 ESP32_GENERIC_S2-20240602-v1.23.0.bin
```

### 1e. Verify MicroPython is running

Press RESET on the board, then connect with a serial terminal:

```bash
# Using Python's built-in serial terminal
python -m serial.tool COM3 115200
```

You should see the MicroPython REPL (`>>>`).

## Step 2: Install ampy (File Upload Tool)

```bash
pip install adafruit-ampy
```

## Step 3: Configure WiFi

Edit `esp32/boot.py` — change the WiFi credentials:

```python
SSID = "YourWiFiName"
PASSWORD = "YourWiFiPassword"
```

## Step 4: Upload Files to ESP32-S2

```bash
# Replace COM3 with your actual port

# Upload boot script (WiFi connection)
ampy --port COM3 put esp32/boot.py boot.py

# Upload Ed25519 verification (pure Python)
ampy --port COM3 put esp32/ed25519_mp.py ed25519_mp.py

# Upload VLCDS device client
ampy --port COM3 put esp32/vlcds_device.py vlcds_device.py
```

## Step 5: Start the PC Server

First, find your PC's IP address:

```bash
# Windows
ipconfig
# Look for "IPv4 Address" under your WiFi adapter
# Example: 192.168.1.100
```

Start the OTA server:

```bash
cd d:\PROJECTS\CRY
python server_http.py
```

You should see:
```
  VLCDS HTTP OTA Server — Initializing
  ...
  Starting HTTP server on 0.0.0.0:5000
  ESP32 should connect to: http://<YOUR_PC_IP>:5000
```

## Step 6: Run the Demo on ESP32-S2

Connect to the ESP32 serial terminal and run:

```python
>>> import vlcds_device
>>> vlcds_device.run_update("http://192.168.1.100:5000")  # Use YOUR PC's IP
```

**For the full demo (v1→v2→v3 chained):**

```python
>>> vlcds_device.run_demo("http://192.168.1.100:5000")
```

## Expected Output

You will see the full 3-stage VLCDS protocol running on real hardware:

```
  STAGE 1 — PRE-VERIFY
  ┌────────────────────────────────────────────────┐
  │           VLCDS MANIFEST (200 bytes)           │
  ├─────────────────┬──────────────────────────────┤
  │ H(base_fw)      │ a1b2c3d4e5f6...             │
  │ H(delta)        │ 1234abcd5678...             │
  │ ...             │                              │
  
  [1/4] Ed25519 Signature Verification...
    Result: PASS ✓ (237 ms)
  
  [2/4] H(base_fw) — Firmware Hash Match...
    Result: MATCH ✓ (12 ms)
  
  [3/4] Version Binding Check...
    Result: MATCH ✓
  
  [4/4] H(prev_manifest) — Anti-Replay Chain...
    Result: MATCH ✓
  
  ✓ STAGE 1 PASSED — All 4 checks verified (253 ms)
```

## Troubleshooting

### "Cannot connect to server"
- Ensure PC and ESP32 are on the same WiFi network
- Check if Windows Firewall is blocking port 5000
- Try: `python -m http.server 5000` to test basic connectivity

### "Out of memory"
- The ESP32-S2 has 320KB SRAM — firmware images must stay small
- Use `gc.collect()` before operations
- Reduce firmware size in `server_http.py` if needed

### "Ed25519 verification is slow"
- Pure-Python Ed25519 is expected to take ~200-500ms on ESP32-S2
- This is still acceptable for the pre-verify step (runs once per update)
- In production, a C-compiled module would be much faster

### "esptool can't find the board"
- Try holding BOOT button while plugging in USB
- Check Device Manager for the correct COM port
- Install USB drivers if needed: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s2/get-started/establish-serial-connection.html
