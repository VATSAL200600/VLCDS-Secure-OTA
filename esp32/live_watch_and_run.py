"""
live_watch_and_run.py
Continuously monitors for ESP32 connection on any COM port and automatically
uploads the VLCDS files and runs the verification demo.
"""
import sys
import time
import os
import subprocess

try:
    import serial.tools.list_ports
except ImportError:
    print("pyserial required.")
    sys.exit(1)

PC_IP = "10.187.80.191"
SERVER_URL = f"http://{PC_IP}:5000"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

print("=" * 60)
print("  VLCDS ESP32-S2 Auto-Deploy Daemon Running")
print(f"  Target Server: {SERVER_URL}")
print("  Monitoring all USB ports continuously...")
print("=" * 60)

last_ports = set()
while True:
    try:
        ports = list(serial.tools.list_ports.comports())
        current = {p.device for p in ports}
        
        # Check if new port appeared
        new_ports = current - last_ports
        if new_ports:
            print(f"\n[!] Detected new port(s): {list(new_ports)}")
            for p in ports:
                print(f"    Port: {p.device} | Description: {p.description} | HWID: {p.hwid}")
        
        last_ports = current
        
        # Check for ESP32 candidate
        esp_port = None
        for p in ports:
            desc = (p.description or "").lower()
            hwid = (p.hwid or "").lower()
            if any(k in desc or k in hwid for k in ["cp210", "ch340", "silicon labs", "esp", "usb serial"]):
                esp_port = p.device
                break
        if not esp_port and len(ports) == 1:
            esp_port = ports[0].device
            
        if esp_port:
            print(f"\n[+] ESP32 CONFIRMED ON {esp_port}! Starting deployment...")
            time.sleep(1) # let port settle
            
            # Step 1: Upload files
            files = ["boot.py", "ed25519_mp.py", "vlcds_device.py"]
            success = True
            for f in files:
                fpath = os.path.join(SCRIPT_DIR, f)
                print(f"[*] Uploading {f} to {esp_port}...")
                cmd = [sys.executable, "-m", "mpremote", "connect", esp_port, "cp", fpath, f":{f}"]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode != 0:
                    print(f"    Upload warning for {f}: {res.stderr.strip()}")
                else:
                    print(f"    Uploaded {f} successfully.")
                    
            # Step 2: Execute
            print(f"\n[*] Executing VLCDS on {esp_port}...")
            print("=" * 60)
            exec_code = f"import vlcds_device; vlcds_device.run_demo('{SERVER_URL}')"
            run_cmd = [sys.executable, "-m", "mpremote", "connect", esp_port, "exec", exec_code]
            proc = subprocess.Popen(run_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in iter(proc.stdout.readline, ""):
                print(line, end="", flush=True)
            proc.stdout.close()
            proc.wait()
            print("\n[+] Verification run completed on physical hardware!")
            break
            
        time.sleep(0.8)
    except Exception as e:
        print(f"Error in monitor loop: {e}")
        time.sleep(2)
