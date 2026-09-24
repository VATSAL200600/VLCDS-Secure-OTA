"""
auto_reconnect_deploy.py
Monitors COM23 for fresh re-connection after unplug/replug,
then immediately uploads all files and runs the demo.
"""
import sys
import time
import os
import subprocess
import serial
import serial.tools.list_ports

PORT = "COM23"
SERVER_URL = "http://10.187.80.191:5000"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

print("=" * 60)
print("  VLCDS ESP32-S2 Auto-Deploy on Reconnect")
print("  Target Server: %s" % SERVER_URL)
print("=" * 60)
print("Waiting for clean USB connection on %s..." % PORT)
print("[ACTION NEEDED] Please UNPLUG the USB cable from your laptop, wait 2 seconds, and PLUG IT BACK IN.")
print("=" * 60)

# Loop until COM23 is cleanly accessible
connected = False
while not connected:
    try:
        # Check if COM23 is in ports
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if PORT in ports:
            # Try a quick open to see if WinError 433 is gone
            s = serial.Serial(PORT, 115200, timeout=0.5)
            s.close()
            connected = True
            print(f"\n[✓] USB connection refreshed and active on {PORT}!")
            break
    except Exception:
        pass
    print(".", end="", flush=True)
    time.sleep(1)

# Allow 1.5 seconds for MicroPython to boot
print("\n[1/3] MicroPython initializing...")
time.sleep(1.5)

# Step 2: Upload files using mpremote
print("\n[2/3] Uploading VLCDS files to ESP32 flash...")
files = ["boot.py", "ed25519_mp.py", "vlcds_device.py"]
for f in files:
    fpath = os.path.join(SCRIPT_DIR, f)
    print(f"  Uploading {f} ({os.path.getsize(fpath)} bytes)...")
    cmd = [sys.executable, "-m", "mpremote", "connect", PORT, "cp", fpath, f":{f}"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print(f"  ✓ {f} uploaded successfully")
    else:
        print(f"  Warning on {f}: {res.stderr.strip()}")

# Step 3: Run the demo
print("\n[3/3] Launching VLCDS 3-Stage Cryptographic OTA Verification...")
print("=" * 60)
print("  LIVE ESP32-S2 HARDWARE TERMINAL OUTPUT:")
print("=" * 60 + "\n")

run_cmd = [
    sys.executable,
    "-m",
    "mpremote",
    "connect",
    PORT,
    "exec",
    f"import vlcds_device; vlcds_device.run_demo('{SERVER_URL}')"
]

proc = subprocess.Popen(run_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
for line in iter(proc.stdout.readline, ""):
    print(line, end="", flush=True)
proc.stdout.close()
proc.wait()

print("\n" + "=" * 60)
print("  VLCDS Demo Completed on Physical Hardware!")
print("=" * 60)
