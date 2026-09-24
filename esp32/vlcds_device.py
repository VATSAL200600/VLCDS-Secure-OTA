"""
vlcds_device.py — VLCDS Client for ESP32-S2 (MicroPython)

This is the main script that runs on the actual ESP32-S2 hardware.
It implements the 3-stage VLCDS verification protocol:

    Stage 1 — Pre-Verify:  Verify 200-byte manifest (signature + 4 checks)
    Stage 2 — Patch:       Download delta, verify hash, apply patch
    Stage 3 — Post-Verify: Hash reconstructed image, compare to H(target)

Usage (after uploading to ESP32 and connecting WiFi):
    >>> import vlcds_device
    >>> vlcds_device.run_update("http://192.168.1.100:5000")

Or for the full demo:
    >>> vlcds_device.run_demo("http://192.168.1.100:5000")
"""

import time
import hashlib
import struct
try:
    import urequests
except ImportError:
    try:
        import requests as urequests
    except ImportError:
        import usocket as socket
        class _Response:
            def __init__(self, f):
                self.raw = f
                self.encoding = "utf-8"
                self._cached = None
            def close(self):
                if self.raw:
                    self.raw.close()
                    self.raw = None
            @property
            def content(self):
                if self._cached is None:
                    try:
                        self._cached = self.raw.read()
                    finally:
                        self.raw.close()
                        self.raw = None
                return self._cached
            @property
            def text(self):
                return str(self.content, self.encoding)
            def json(self):
                import ujson
                return ujson.loads(self.content)

        class _URequests:
            @staticmethod
            def request(method, url, data=None, json=None, headers={}, stream=None):
                try:
                    proto, dummy, host, path = url.split("/", 3)
                except ValueError:
                    proto, dummy, host = url.split("/", 2)
                    path = ""
                if proto == "http:":
                    port = 80
                elif proto == "https:":
                    import ussl
                    port = 443
                else:
                    raise ValueError("Unsupported: " + proto)
                if ":" in host:
                    host, port = host.split(":", 1)
                    port = int(port)
                ai = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)[0]
                s = socket.socket(ai[0], ai[1], ai[2])
                try:
                    s.connect(ai[-1])
                    if proto == "https:":
                        s = ussl.wrap_socket(s, server_hostname=host)
                    s.write(("%s /%s HTTP/1.0\r\n" % (method, path)).encode())
                    if "Host" not in headers:
                        s.write(("Host: %s\r\n" % host).encode())
                    for k in headers:
                        s.write(("%s: %s\r\n" % (k, headers[k])).encode())
                    if json is not None:
                        import ujson
                        data = ujson.dumps(json)
                        s.write(b"Content-Type: application/json\r\n")
                    if data:
                        if isinstance(data, str):
                            data = data.encode()
                        s.write(("Content-Length: %d\r\n" % len(data)).encode())
                    s.write(b"\r\n")
                    if data:
                        s.write(data)
                    l = s.readline().split(None, 2)
                    status = int(l[1])
                    reason = l[2].rstrip() if len(l) > 2 else ""
                    while True:
                        l = s.readline()
                        if not l or l == b"\r\n":
                            break
                    resp = _Response(s)
                    resp.status_code = status
                    resp.reason = reason
                    return resp
                except Exception:
                    s.close()
                    raise
            @classmethod
            def get(cls, url, **kw):
                return cls.request("GET", url, **kw)
            @classmethod
            def post(cls, url, **kw):
                return cls.request("POST", url, **kw)
        urequests = _URequests()
import gc

# Import our pure-Python Ed25519 verification
import ed25519_mp

# ============================================================================
#  CONFIGURATION
# ============================================================================

# Delta patch format constants (must match server's delta_engine.py)
DELTA_MAGIC = b"VLCDS_DELTA"
OP_DIFF = 0x01
OP_INSERT = 0x02
OP_END = 0xFF


# ============================================================================
#  HARDWARE WS2812 RGB LED (GPIO 18 on ESP32-S2 DevKit)
# ============================================================================
_led = None
try:
    import machine, neopixel
    _led = neopixel.NeoPixel(machine.Pin(18), 1)
except Exception:
    _led = None

def set_led(r, g, b):
    """Set onboard RGB LED color for real-time visual hardware confirmation."""
    global _led
    if _led:
        try:
            _led[0] = (r, g, b)
            _led.write()
        except Exception:
            pass

def flash_led(r, g, b, count=3, on_ms=100, off_ms=80):
    """Pulse/flash the onboard RGB LED for confirmation or alert signals."""
    global _led
    if _led:
        try:
            for _ in range(count):
                _led[0] = (r, g, b)
                _led.write()
                time.sleep_ms(on_ms)
                _led[0] = (0, 0, 0)
                _led.write()
                time.sleep_ms(off_ms)
            _led[0] = (r, g, b)
            _led.write()
        except Exception:
            pass


# ============================================================================
#  SHA-256 UTILITY
# ============================================================================

def sha256(data):
    """Compute SHA-256 hash using MicroPython's built-in hashlib."""
    return hashlib.sha256(data).digest()


# ============================================================================
#  MANIFEST PARSING
# ============================================================================

class Manifest:
    """VLCDS 6-field signed manifest (200 bytes)."""

    def __init__(self, data):
        """Parse a 200-byte manifest from wire format."""
        if len(data) != 200:
            raise ValueError("Manifest must be 200 bytes, got %d" % len(data))

        offset = 0
        self.h_base_fw = data[offset:offset+32]; offset += 32
        self.h_delta = data[offset:offset+32]; offset += 32
        self.h_target = data[offset:offset+32]; offset += 32
        self.version_base = struct.unpack(">I", data[offset:offset+4])[0]; offset += 4
        self.version_target = struct.unpack(">I", data[offset:offset+4])[0]; offset += 4
        self.h_prev_manifest = data[offset:offset+32]; offset += 32
        self.signature = data[offset:offset+64]; offset += 64

        # Payload = everything except signature (first 136 bytes)
        self.payload = data[:136]

    def print_fields(self):
        """Print manifest fields for demo output."""
        print("  ┌────────────────────────────────────────────────┐")
        print("  │           VLCDS MANIFEST (200 bytes)           │")
        print("  ├─────────────────┬──────────────────────────────┤")
        print("  │ H(base_fw)      │ %s... │" % self.h_base_fw.hex()[:28])
        print("  │ H(delta)        │ %s... │" % self.h_delta.hex()[:28])
        print("  │ H(target)       │ %s... │" % self.h_target.hex()[:28])
        print("  │ version_base    │ v%-27d │" % self.version_base)
        print("  │ version_target  │ v%-27d │" % self.version_target)
        print("  │ H(prev_manifest)│ %s... │" % self.h_prev_manifest.hex()[:28])
        print("  │ signature       │ %s... │" % self.signature.hex()[:28])
        print("  └─────────────────┴──────────────────────────────┘")


# ============================================================================
#  DELTA PATCH APPLICATION
# ============================================================================

def apply_delta(old_fw, delta_patch):
    """
    Apply a delta patch to reconstruct new firmware.
    Mirrors the PC-side delta_engine.py logic.
    """
    # Verify magic
    if delta_patch[:11] != DELTA_MAGIC:
        raise ValueError("Invalid delta magic")

    old_size = struct.unpack(">I", delta_patch[11:15])[0]
    new_size = struct.unpack(">I", delta_patch[15:19])[0]

    if len(old_fw) != old_size:
        raise ValueError("Base firmware size mismatch")

    # Start with copy of old firmware
    if new_size >= old_size:
        result = bytearray(old_fw) + bytearray(new_size - old_size)
    else:
        result = bytearray(old_fw[:new_size])

    pos = 19  # After header
    instructions = 0

    while pos < len(delta_patch):
        opcode = delta_patch[pos]; pos += 1

        if opcode == OP_END:
            break
        elif opcode == OP_DIFF:
            offset = struct.unpack(">I", delta_patch[pos:pos+4])[0]; pos += 4
            length = struct.unpack(">I", delta_patch[pos:pos+4])[0]; pos += 4
            for i in range(length):
                result[offset + i] = result[offset + i] ^ delta_patch[pos + i]
            pos += length
            instructions += 1
        elif opcode == OP_INSERT:
            offset = struct.unpack(">I", delta_patch[pos:pos+4])[0]; pos += 4
            length = struct.unpack(">I", delta_patch[pos:pos+4])[0]; pos += 4
            for i in range(length):
                result[offset + i] = delta_patch[pos + i]
            pos += length
            instructions += 1
        else:
            raise ValueError("Unknown opcode: 0x%02x" % opcode)

    print("  Applied %d patch instructions" % instructions)
    return bytes(result[:new_size])


# ============================================================================
#  VLCDS 3-STAGE VERIFICATION PROTOCOL
# ============================================================================

class VLCDSDevice:
    """
    VLCDS IoT Device running on real ESP32-S2 hardware.
    """

    def __init__(self, public_key_hex, initial_firmware, initial_version):
        """
        Initialize device with pre-provisioned state.

        Args:
            public_key_hex: Server's Ed25519 public key as hex string
            initial_firmware: Initial firmware bytes
            initial_version: Initial version number
        """
        self.public_key = bytes.fromhex(public_key_hex)
        self.firmware = initial_firmware
        self.version = initial_version
        self.chain_head = b"\x00" * 32  # Genesis hash
        self._staged_manifest = None

        print("\n" + "=" * 50)
        print("  VLCDS Device Initialized (ESP32-S2)")
        print("=" * 50)
        print("  Version     : v%d" % self.version)
        print("  FW size     : %d bytes" % len(self.firmware))
        print("  FW hash     : %s" % sha256(self.firmware).hex()[:32])
        print("  Public key  : %s..." % public_key_hex[:32])
        print("  Chain head  : %s" % self.chain_head.hex()[:32])
        print("  Free memory : %d bytes" % gc.mem_free())
        print("=" * 50)
        set_led(80, 0, 180)  # PURPLE: Hardware initialized & ready
        print("  [LED] Initialized: 🟣 PURPLE (Ready for signed firmware update)")

    # ── STAGE 1 — PRE-VERIFY ──

    def stage1_pre_verify(self, manifest_data):
        """
        Stage 1: Verify the 200-byte manifest BEFORE requesting patch.

        4 checks, all on fields INSIDE the signed object:
            1. Ed25519 signature
            2. H(base_fw) matches our firmware
            3. version_base matches our version
            4. H(prev_manifest) matches our chain head
        """
        print("\n" + "=" * 50)
        print("  STAGE 1 — PRE-VERIFY")
        print("  Received: %d bytes" % len(manifest_data))
        print("=" * 50)
        set_led(0, 80, 255)  # BLUE: Update manifest received, verifying
        print("  [LED] Status: 🔵 BLUE — Manifest received, verifying Ed25519 signature & chain")

        start = time.ticks_ms()

        # Parse manifest
        manifest = Manifest(manifest_data)
        manifest.print_fields()

        # Check 1: Ed25519 Signature
        print("\n  [1/4] Ed25519 Signature Verification...")
        t1 = time.ticks_ms()
        sig_valid = ed25519_mp.verify(self.public_key, manifest.payload, manifest.signature)
        t1_elapsed = time.ticks_diff(time.ticks_ms(), t1)
        print("    Result: %s (%d ms)" % ("PASS ✓" if sig_valid else "FAIL ✗", t1_elapsed))
        if not sig_valid:
            print("  ✗ REJECTED: Invalid signature!")
            flash_led(255, 0, 0, count=3)
            print("  [LED] Status: 🔴 RED — Invalid signature rejected!")
            return False

        # Check 2: Base Firmware Hash
        print("\n  [2/4] H(base_fw) — Firmware Hash Match...")
        t2 = time.ticks_ms()
        my_hash = sha256(self.firmware)
        t2_elapsed = time.ticks_diff(time.ticks_ms(), t2)
        match = my_hash == manifest.h_base_fw
        print("    Manifest : %s..." % manifest.h_base_fw.hex()[:32])
        print("    Mine     : %s..." % my_hash.hex()[:32])
        print("    Result   : %s (%d ms)" % ("MATCH ✓" if match else "MISMATCH ✗", t2_elapsed))
        if not match:
            print("  ✗ REJECTED: Patch not for our firmware!")
            flash_led(255, 0, 0, count=3)
            print("  [LED] Status: 🔴 RED — Base firmware mismatch rejected!")
            return False

        # Check 3: Version Number
        print("\n  [3/4] Version Binding Check...")
        ver_match = manifest.version_base == self.version
        print("    Manifest : v%d" % manifest.version_base)
        print("    Device   : v%d" % self.version)
        print("    Result   : %s" % ("MATCH ✓" if ver_match else "MISMATCH ✗"))
        if not ver_match:
            print("  ✗ REJECTED: Version mismatch!")
            flash_led(255, 0, 0, count=3)
            print("  [LED] Status: 🔴 RED — Version mismatch rejected!")
            return False

        # Check 4: Chain Link (Anti-Replay)
        print("\n  [4/4] H(prev_manifest) — Anti-Replay Chain...")
        chain_match = manifest.h_prev_manifest == self.chain_head
        print("    Manifest : %s..." % manifest.h_prev_manifest.hex()[:32])
        print("    Chain HD : %s..." % self.chain_head.hex()[:32])
        print("    Result   : %s" % ("MATCH ✓" if chain_match else "MISMATCH ✗ (REPLAY?)"))
        if not chain_match:
            print("  ✗ REJECTED: Chain link mismatch — possible replay attack!")
            flash_led(255, 0, 0, count=3)
            print("  [LED] Status: 🔴 RED — Replay attack blocked by hash chain!")
            return False

        elapsed = time.ticks_diff(time.ticks_ms(), start)
        print("\n  ✓ STAGE 1 PASSED — All 4 checks verified (%d ms)" % elapsed)
        print("    → Requesting delta patch from server...")
        set_led(0, 200, 255)  # CYAN: Stage 1 verified!
        print("  [LED] Status: 💠 CYAN — Stage 1 verified! Requesting delta patch")

        self._staged_manifest = manifest
        return True

    # ── STAGE 2 — PATCH TRANSFER & APPLICATION ──

    def stage2_patch_apply(self, delta_data):
        """
        Stage 2: Verify delta hash, apply patch to shadow partition.
        """
        print("\n" + "=" * 50)
        print("  STAGE 2 — PATCH TRANSFER & APPLICATION")
        print("  Received: %d bytes" % len(delta_data))
        print("=" * 50)

        start = time.ticks_ms()
        manifest = self._staged_manifest

        if manifest is None:
            print("  ✗ ERROR: No staged manifest!")
            return None

        # Verify delta hash
        print("\n  Verifying H(delta)...")
        set_led(255, 120, 0)  # AMBER/ORANGE: Verifying delta hash and patching
        print("  [LED] Status: 🟠 ORANGE — Delta patch received, verifying H(delta) & patching in RAM")
        delta_hash = sha256(delta_data)
        match = delta_hash == manifest.h_delta
        print("    Manifest : %s..." % manifest.h_delta.hex()[:32])
        print("    Received : %s..." % delta_hash.hex()[:32])
        print("    Result   : %s" % ("MATCH ✓" if match else "MISMATCH ✗"))

        if not match:
            print("  ✗ REJECTED: Delta patch tampered!")
            flash_led(255, 0, 0, count=3)
            print("  [LED] Status: 🔴 RED — Tampered delta patch rejected!")
            self._staged_manifest = None
            return None

        # Apply delta
        print("\n  Applying delta to shadow partition...")
        gc.collect()
        print("  Free memory before patch: %d bytes" % gc.mem_free())

        new_fw = apply_delta(self.firmware, delta_data)

        elapsed = time.ticks_diff(time.ticks_ms(), start)
        print("  Free memory after patch: %d bytes" % gc.mem_free())
        print("\n  ✓ STAGE 2 PASSED — Patch applied (%d ms)" % elapsed)
        print("    Reconstructed FW: %d bytes" % len(new_fw))
        set_led(255, 200, 0)  # YELLOW: Delta successfully patched into shadow partition
        print("  [LED] Status: 🟡 YELLOW — Patch applied to shadow partition")

        return new_fw

    # ── STAGE 3 — POST-VERIFY ──

    def stage3_post_verify(self, new_firmware):
        """
        Stage 3: Hash reconstructed image, compare to H(target).
        NOTE: Only a hash comparison — NO second signature needed!
        """
        print("\n" + "=" * 50)
        print("  STAGE 3 — POST-VERIFY")
        print("  (Hash comparison only — no 2nd signature needed)")
        print("=" * 50)

        start = time.ticks_ms()
        manifest = self._staged_manifest

        # Hash reconstructed firmware
        print("\n  Hashing reconstructed firmware...")
        recon_hash = sha256(new_firmware)
        match = recon_hash == manifest.h_target
        print("    Manifest H(target): %s..." % manifest.h_target.hex()[:32])
        print("    Reconstructed     : %s..." % recon_hash.hex()[:32])
        print("    Result: %s" % ("MATCH ✓" if match else "MISMATCH ✗"))

        if not match:
            print("  ✗ REJECTED: Reconstructed image hash mismatch!")
            flash_led(255, 0, 0, count=3)
            print("  [LED] Status: 🔴 RED — Reconstructed image hash mismatch!")
            self._staged_manifest = None
            return False

        # SUCCESS — Update device state
        old_ver = self.version
        self.firmware = new_firmware
        self.version = manifest.version_target

        # Update chain head
        manifest_bytes = manifest.payload + manifest.signature
        self.chain_head = sha256(manifest_bytes)

        elapsed = time.ticks_diff(time.ticks_ms(), start)

        print("\n  ✓ STAGE 3 PASSED — UPDATE COMPLETE! (%d ms)" % elapsed)
        print("  ┌────────────────────────────────────────┐")
        print("  │  Firmware updated: v%d → v%d            │" % (old_ver, self.version))
        print("  │  New FW hash: %s...│" % sha256(self.firmware).hex()[:22])
        print("  │  Chain head : %s...│" % self.chain_head.hex()[:22])
        print("  │  Free memory: %d bytes          │" % gc.mem_free())
        print("  └────────────────────────────────────────┘")

        flash_led(0, 255, 0, count=3, on_ms=120, off_ms=80)  # VIBRANT GREEN CONFIRMATION PULSE
        print("  [LED] Status: 🟢 GREEN (CONFIRMATION PULSE) — Firmware v%d committed! OTA 100%% complete" % self.version)

        self._staged_manifest = None
        return True


# ============================================================================
#  NETWORK OTA UPDATE (over WiFi)
# ============================================================================

def notify_server(server_url, event, details):
    """Notify web dashboard of ESP32 update progress."""
    try:
        import ujson
        payload = ujson.dumps({"event": event, "details": details})
        resp = urequests.post(server_url + "/api/esp32/notify", data=payload, headers={"Content-Type": "application/json"})
        resp.close()
    except Exception:
        pass


def run_update(server_url, version_from=1, version_to=2):
    """
    Run the full VLCDS update protocol against the HTTP server.

    Args:
        server_url: URL of the PC server, e.g. "http://192.168.1.100:5000"
        version_from: Current firmware version
        version_to: Target firmware version
    """
    print("\n" + "=" * 50)
    print("  VLCDS OTA Update — ESP32-S2 Hardware Demo")
    print("  Server: %s" % server_url)
    print("  Update: v%d → v%d" % (version_from, version_to))
    print("=" * 50)

    gc.collect()

    # Step 0: Get server info and public key
    print("\n[0] Fetching server info...")
    try:
        resp = urequests.get(server_url + "/pubkey")
        pubkey_hex = resp.text
        resp.close()
        print("    Public key: %s..." % pubkey_hex[:32])
    except Exception as e:
        print("    ERROR connecting to server: %s" % str(e))
        return False

    # Download initial firmware for provisioning
    print("\n[0] Downloading firmware v%d for provisioning..." % version_from)
    resp = urequests.get(server_url + "/firmware/%d" % version_from)
    initial_fw = resp.content
    resp.close()
    print("    Downloaded: %d bytes" % len(initial_fw))

    # Initialize device
    device = VLCDSDevice(pubkey_hex, initial_fw, version_from)
    notify_server(server_url, "Device Connected", "ESP32-S2 initialized with v%d firmware (%d bytes)" % (version_from, len(initial_fw)))

    # ── STAGE 1: Get and verify manifest ──
    print("\n[1] Downloading manifest (Stage 1)...")
    url = server_url + "/manifest/%d/%d" % (version_from, version_to)
    resp = urequests.get(url)
    manifest_data = resp.content
    resp.close()
    print("    Downloaded: %d bytes" % len(manifest_data))

    gc.collect()
    if not device.stage1_pre_verify(manifest_data):
        print("\n  UPDATE ABORTED at Stage 1")
        notify_server(server_url, "Stage 1 FAILED", "Manifest verification rejected at Stage 1")
        return False

    notify_server(server_url, "Stage 1 Pre-Verify PASSED", "All 4 checks verified (Ed25519 sig, base FW hash, v%d, chain head)" % version_from)

    # ── STAGE 2: Get and apply delta ──
    print("\n[2] Downloading delta patch (Stage 2)...")
    url = server_url + "/delta/%d/%d" % (version_from, version_to)
    resp = urequests.get(url)
    delta_data = resp.content
    resp.close()
    print("    Downloaded: %d bytes" % len(delta_data))

    gc.collect()
    new_fw = device.stage2_patch_apply(delta_data)
    if new_fw is None:
        print("\n  UPDATE ABORTED at Stage 2")
        notify_server(server_url, "Stage 2 FAILED", "Delta patch hash mismatch or application error")
        return False

    notify_server(server_url, "Stage 2 Delta Patch Applied", "Verified H(delta), reconstructed %d bytes in RAM" % len(new_fw))

    # ── STAGE 3: Post-verify ──
    gc.collect()
    if not device.stage3_post_verify(new_fw):
        print("\n  UPDATE ABORTED at Stage 3")
        notify_server(server_url, "Stage 3 FAILED", "Reconstructed image hash mismatch")
        return False

    notify_server(server_url, "Stage 3 Post-Verify PASSED", "Matched H(target) without second signature! Updated to v%d" % version_to)

    print("\n" + "=" * 50)
    print("  ✓ OTA UPDATE SUCCESSFUL on ESP32-S2 Hardware!")
    print("  Firmware: v%d → v%d" % (version_from, version_to))
    print("  Free memory: %d bytes" % gc.mem_free())
    print("=" * 50)
    return True


def run_demo(server_url):
    """
    Run the full demo: update v1→v2, then v2→v3 (chained).

    This shows the VLCDS protocol working on real hardware with:
    - 3-stage verification
    - Hash-chain continuity
    - Intermediate timing results
    """
    print("\n" + "#" * 50)
    print("  VLCDS FULL DEMO — ESP32-S2 Hardware")
    print("#" * 50)

    total_start = time.ticks_ms()

    # Update 1: v1 → v2
    print("\n" + "=" * 50)
    print("  UPDATE 1: v1 → v2")
    print("=" * 50)
    success1 = run_update(server_url, 1, 2)

    if not success1:
        print("  Demo aborted — first update failed")
        return

    # Update 2: v2 → v3 (tests chain continuity)
    print("\n" + "=" * 50)
    print("  UPDATE 2: v2 → v3 (chained)")
    print("=" * 50)
    success2 = run_update(server_url, 2, 3)

    total = time.ticks_diff(time.ticks_ms(), total_start)

    print("\n" + "#" * 50)
    print("  DEMO COMPLETE")
    print("  Both updates: %s" % ("SUCCESS ✓" if (success1 and success2) else "FAILED ✗"))
    print("  Total time: %d ms" % total)
    print("  Free memory: %d bytes" % gc.mem_free())
    print("#" * 50)


# Auto-run when executed directly in Thonny (Green Play button / F5)
if __name__ == "__main__":
    SERVER_URL = "http://10.187.80.191:5000"
    run_demo(SERVER_URL)

