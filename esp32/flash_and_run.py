"""
flash_and_run.py — Automated ESP32-S2 Deployment & Execution Runner

1. Detects connected ESP32-S2 COM port.
2. Checks if MicroPython is running.
3. Automatically uploads boot.py, ed25519_mp.py, and vlcds_device.py.
4. Executes the live demo against the PC web server and streams output.
"""

import sys
import time
import os
import subprocess

try:
    import serial.tools.list_ports
except ImportError:
    print("Error: pyserial not installed.")
    sys.exit(1)

PC_IP = "10.187.80.191"
SERVER_URL = f"http://{PC_IP}:5000"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def find_esp32_port():
    """Find the COM port of the connected ESP32."""
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        desc = (p.description or "").lower()
        hwid = (p.hwid or "").lower()
        if any(keyword in desc or keyword in hwid for keyword in [
            "cp210", "ch340", "ch341", "ftdi", "silicon labs", "esp", "usb serial", "usb jtag"
        ]):
            return p.device
    if len(ports) == 1:
        return ports[0].device
    return None


def wait_for_esp32(timeout=120):
    """Wait for ESP32 to be plugged into USB."""
    print("=" * 60)
    print("  ESP32-S2 Hardware Auto-Deploy & Runner")
    print(f"  Target Server: {SERVER_URL}")
    print("=" * 60)
    print("Listening for ESP32-S2 on USB... (unplug & re-plug USB cable now)")

    start = time.time()
    while time.time() - start < timeout:
        port = find_esp32_port()
        if port:
            print(f" Found ESP32 on port: {port}")
            return port
        time.sleep(1)
        print(".", end="", flush=True)

    print("\n No ESP32 detected on active COM port.")
    return None


def run_deployment(port):
    """Upload files and run the demo on the ESP32."""
    print(f"\n[1/3] Checking connection to ESP32 on {port}...")
    
    test_cmd = [sys.executable, "-m", "mpremote", "connect", port, "exec", "print('CONNECTED_TO_ESP32')"]
    try:
        res = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)
        if "CONNECTED_TO_ESP32" in res.stdout:
            print(" MicroPython REPL is responsive!")
        else:
            print("Notice: MicroPython REPL response:")
            print(f"Raw output: {res.stdout.strip()} {res.stderr.strip()}")
    except Exception as e:
        print(f"REPL check note: {e}")

    print("\n[2/3] Uploading VLCDS files to ESP32...")
    files_to_upload = ["boot.py", "ed25519_mp.py", "vlcds_device.py"]
    for f in files_to_upload:
        filepath = os.path.join(SCRIPT_DIR, f)
        if not os.path.exists(filepath):
            print(f" Error: {filepath} not found!")
            return False
        print(f"  Uploading {f} ({os.path.getsize(filepath)} bytes)...")
        up_cmd = [sys.executable, "-m", "mpremote", "connect", port, "cp", filepath, f":{f}"]
        up_res = subprocess.run(up_cmd, capture_output=True, text=True)
        if up_res.returncode != 0:
            print(f"  Note during {f} upload: {up_res.stderr.strip()}")
        else:
            print(f"  - {f} uploaded successfully")

    print("\n[3/3] Launching VLCDS OTA Update on ESP32-S2 Hardware...")
    print(f"  Server URL: {SERVER_URL}")
    print("=" * 60)
    print("  ESP32 LIVE TERMINAL OUTPUT BELOW:")
    print("=" * 60 + "\n")

    exec_code = f"import vlcds_device; vlcds_device.run_demo('{SERVER_URL}')"
    run_cmd = [sys.executable, "-m", "mpremote", "connect", port, "exec", exec_code]
    
    proc = subprocess.Popen(run_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in iter(proc.stdout.readline, ""):
        print(line, end="", flush=True)
    proc.stdout.close()
    proc.wait()

    print("\n" + "=" * 60)
    print("  Execution finished on ESP32-S2 hardware!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    port = wait_for_esp32(timeout=300)
    if port:
        run_deployment(port)
    else:
        print("\nPlease check your USB connection.")
