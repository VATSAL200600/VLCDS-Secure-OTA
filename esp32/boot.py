"""
boot.py — ESP32-S2 MicroPython Boot Script

Connects to WiFi and prints network info.
Upload this to the ESP32-S2 root filesystem.

CONFIGURATION:
    Change SSID and PASSWORD below to match your WiFi network.
"""

import network
import time

# ============================================================================
#  WiFi Configuration — CHANGE THESE TO YOUR NETWORK
# ============================================================================

SSID = "BATMAN"
PASSWORD = "rinkoo78"


# ============================================================================
#  WiFi Connection
# ============================================================================

def connect_wifi():
    """Connect to WiFi and return the IP address."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print("[WiFi] Already connected")
        print(f"[WiFi] IP: {wlan.ifconfig()[0]}")
        return wlan.ifconfig()[0]

    print(f"[WiFi] Connecting to '{SSID}'...")
    wlan.connect(SSID, PASSWORD)

    # Wait for connection (timeout 15 seconds)
    timeout = 15
    start = time.time()
    while not wlan.isconnected():
        if time.time() - start > timeout:
            print("[WiFi] Connection TIMEOUT!")
            return None
        time.sleep(0.5)
        print(".", end="")

    ip = wlan.ifconfig()[0]
    print(f"\n[WiFi] Connected! IP: {ip}")
    return ip


# ============================================================================
#  Auto-connect on boot
# ============================================================================

print("\n" + "=" * 50)
print("  VLCDS IoT Device — ESP32-S2")
print("  MicroPython Boot")
print("=" * 50)

ip = connect_wifi()

if ip:
    print(f"\n  Device ready at {ip}")
    print(f"  Run: import vlcds_device")
    print(f"  Then: vlcds_device.run_update('http://<PC_IP>:5000')")
else:
    print("\n  WiFi failed — check SSID/PASSWORD in boot.py")
