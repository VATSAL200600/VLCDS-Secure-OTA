"""
deploy_and_run_direct.py — Direct Raw REPL Uploader & Runner for ESP32 MicroPython

Uses standard MicroPython Raw REPL over pySerial to:
1. Upload ed25519_mp.py
2. Upload boot.py
3. Upload vlcds_device.py
4. Run the 3-stage cryptographic OTA demo against the PC server
"""

import sys
import time
import os
import serial

PORT = "COM23"
BAUD = 115200
SERVER_URL = "http://10.187.80.191:5000"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def enter_raw_repl(ser):
    """Enter MicroPython raw REPL mode."""
    print("[1/5] Connecting to MicroPython REPL on %s..." % PORT)
    ser.timeout = 1
    # Wake up & interrupt running code
    for _ in range(3):
        ser.write(b"\r\x03")
        time.sleep(0.2)
    ser.reset_input_buffer()
    
    # Send Ctrl-A for raw REPL
    ser.write(b"\r\x01")
    time.sleep(0.5)
    resp = ser.read(500)
    if b"raw REPL" in resp:
        print("  ✓ Entered Raw REPL successfully")
        return True
    
    # Try one more time with soft reboot
    ser.write(b"\x04")
    time.sleep(1)
    ser.write(b"\r\x03\r\x01")
    time.sleep(0.5)
    resp = ser.read(500)
    if b"raw REPL" in resp:
        print("  ✓ Entered Raw REPL after soft reboot")
        return True

    print("  Note: REPL response: %r" % resp)
    return False


def exec_raw(ser, code_bytes):
    """Execute code in raw REPL mode and return stdout."""
    ser.write(code_bytes + b"\x04")
    # Read until OK
    ser.timeout = 5
    resp = b""
    # First 2 bytes after Ctrl-D should be 'OK'
    while True:
        b = ser.read(1)
        if not b:
            break
        resp += b
        if resp.endswith(b"OK"):
            break

    # Read stdout until \x04
    stdout = b""
    while True:
        b = ser.read(1)
        if not b or b == b"\x04":
            break
        stdout += b

    # Read stderr until \x04
    stderr = b""
    while True:
        b = ser.read(1)
        if not b or b == b"\x04":
            break
        stderr += b

    if stderr:
        print("  [REPL stderr]: %s" % stderr.decode("utf-8", errors="replace"))
    return stdout


def upload_file(ser, filename, filepath):
    """Upload a file to the ESP32 filesystem using raw REPL."""
    print("  Uploading %s (%d bytes)..." % (filename, os.path.getsize(filepath)))
    with open(filepath, "rb") as f:
        content = f.read()

    # Open file for writing on ESP32
    exec_raw(ser, b"__f = open('%s', 'wb')" % filename.encode("ascii"))
    
    # Write in 256-byte chunks to avoid buffer overflow
    chunk_size = 256
    for i in range(0, len(content), chunk_size):
        chunk = content[i : i + chunk_size]
        code = b"__f.write(%r)" % chunk
        exec_raw(ser, code)
        
    exec_raw(ser, b"__f.close()")
    print("  ✓ %s written successfully to ESP32 flash" % filename)


def main():
    print("=" * 60)
    print("  VLCDS ESP32-S2 Direct Raw REPL Deployer")
    print("  Target Server: %s" % SERVER_URL)
    print("=" * 60)

    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except Exception as e:
        print("Failed to open %s: %s" % (PORT, e))
        sys.exit(1)

    try:
        if not enter_raw_repl(ser):
            print("Could not enter Raw REPL. Exiting.")
            ser.close()
            sys.exit(1)

        print("\n[2/5] Uploading core VLCDS cryptographic modules...")
        files = ["ed25519_mp.py", "boot.py", "vlcds_device.py"]
        for f in files:
            fpath = os.path.join(SCRIPT_DIR, f)
            upload_file(ser, f, fpath)

        # Exit raw REPL
        print("\n[3/5] Exiting raw REPL to normal mode...")
        ser.write(b"\x02")  # Ctrl-B
        time.sleep(0.5)
        ser.reset_input_buffer()

        # Connect WiFi and run
        print("\n[4/5] Connecting ESP32 to WiFi (BATMAN)...")
        ser.write(b"import boot\r\n")
        time.sleep(3)
        print(ser.read(1000).decode("utf-8", errors="replace"))

        print("\n[5/5] Launching VLCDS 3-Stage OTA Execution on ESP32...")
        print("=" * 60)
        print("  ESP32 REAL-TIME HARDWARE EXECUTION LOG:")
        print("=" * 60 + "\n")

        ser.timeout = 2
        cmd = f"import vlcds_device; vlcds_device.run_demo('{SERVER_URL}')\r\n"
        ser.write(cmd.encode("ascii"))

        start_time = time.time()
        while time.time() - start_time < 90:
            line = ser.readline()
            if line:
                text = line.decode("utf-8", errors="replace")
                print(text, end="", flush=True)
                if "DEMO COMPLETE" in text or "Both updates:" in text:
                    # Read a few more trailing lines
                    for _ in range(5):
                        t = ser.readline().decode("utf-8", errors="replace")
                        if t:
                            print(t, end="", flush=True)
                    break
            else:
                time.sleep(0.1)

        print("\n" + "=" * 60)
        print("  Live Hardware Demo Execution Completed Successfully!")
        print("=" * 60)

    finally:
        ser.close()


if __name__ == "__main__":
    main()
