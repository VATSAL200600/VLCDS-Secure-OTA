"""
server_http.py — HTTP OTA Server for ESP32-S2 Device

Runs on PC and serves VLCDS updates to the real ESP32-S2 over WiFi.

Endpoints:
    GET  /info                     → Server info and available updates
    GET  /manifest/<from>/<to>     → Stage 1: Get 200-byte signed manifest
    GET  /delta/<from>/<to>        → Stage 2: Get delta patch (only after pre-verify)
    GET  /pubkey                   → Get server's Ed25519 public key (hex)
    GET  /firmware/<version>       → Get full firmware (for initial provisioning)

The ESP32 connects to these endpoints over WiFi to perform the
3-stage VLCDS update protocol.
"""

import json
import os
import time
from flask import Flask, Response, jsonify, request
from vlcds.server import OTAServer
from vlcds.crypto_utils import sha256

app = Flask(__name__)

# ============================================================================
#  SERVER INITIALIZATION
# ============================================================================

# Global server instance
ota_server = None
firmware_versions = {}

def initialize_server():
    """Initialize the OTA server with sample firmware versions."""
    global ota_server, firmware_versions

    print("\n" + "=" * 70)
    print("  VLCDS HTTP OTA Server — Initializing")
    print("=" * 70)

    ota_server = OTAServer(verbose=True)

    # Create synthetic firmware versions that simulate real ESP32 firmware
    # Each version has a recognizable header + body + footer
    firmware_versions = {}

    for v in range(1, 4):
        # Simulate firmware with version-specific content
        header = f"ESP32S2_FW_v{v}.0.0_BUILD_{v * 1000}_".encode()
        # Simulated code section (different per version)
        code_section = bytes([(b + v * 37) % 256 for b in range(2048)])
        # Data section (partially shared between versions)
        data_section = bytes(range(256)) * 4
        # Version-specific configuration
        config = f"_CONFIG_v{v}_WIFI_CH{v + 5}_PWR{v * 10}dBm_".encode()
        footer = f"_CHECKSUM_v{v}_EOF".encode()

        fw = header + code_section + data_section + config + footer
        firmware_versions[v] = fw
        ota_server.add_firmware(v, fw)

    # Pre-compute updates
    print("\n  Pre-computing delta updates...")
    ota_server.prepare_update(1, 2)
    ota_server.prepare_update(2, 3)

    print("\n  Server ready!")
    print(f"  Public key: {ota_server.public_key.encode().hex()}")
    print(f"  Firmware versions: {list(firmware_versions.keys())}")
    for v, fw in firmware_versions.items():
        print(f"    v{v}: {len(fw):,} bytes — SHA256: {sha256(fw).hex()[:16]}...")
    print("=" * 70)


# ============================================================================
#  API ENDPOINTS
# ============================================================================

@app.route("/")
def index():
    """Server landing page."""
    return jsonify({
        "server": "VLCDS OTA Update Server",
        "protocol": "Version-Locked Chained Delta Signature",
        "endpoints": {
            "/info": "Server info",
            "/pubkey": "Ed25519 public key (hex)",
            "/manifest/<from>/<to>": "Stage 1: Signed manifest (200 bytes)",
            "/delta/<from>/<to>": "Stage 2: Delta patch",
            "/firmware/<version>": "Full firmware binary",
        }
    })


@app.route("/info")
def server_info():
    """Return server information and available firmware versions."""
    versions = {}
    for v, fw in firmware_versions.items():
        versions[str(v)] = {
            "size": len(fw),
            "sha256": sha256(fw).hex(),
        }
    return jsonify({
        "available_versions": versions,
        "public_key": ota_server.public_key.encode().hex(),
    })


@app.route("/pubkey")
def get_public_key():
    """Return the server's Ed25519 public key in hex."""
    return Response(
        ota_server.public_key.encode().hex(),
        mimetype="text/plain"
    )


@app.route("/manifest/<int:version_from>/<int:version_to>")
def get_manifest(version_from, version_to):
    """
    Stage 1 endpoint: Return the 200-byte signed manifest.

    This is sent FIRST, before any patch data.
    The ESP32 will pre-verify this before requesting the delta.
    """
    try:
        manifest_bytes = ota_server.get_manifest_bytes(version_from, version_to)
        print(f"\n  [HTTP] Stage 1: Sent manifest v{version_from}→v{version_to} "
              f"({len(manifest_bytes)} bytes)")
        return Response(manifest_bytes, mimetype="application/octet-stream")
    except KeyError as e:
        return jsonify({"error": str(e)}), 404


@app.route("/delta/<int:version_from>/<int:version_to>")
def get_delta(version_from, version_to):
    """
    Stage 2 endpoint: Return the delta patch.

    The device should ONLY call this after Stage 1 pre-verify passes.
    """
    try:
        delta_bytes = ota_server.get_delta_bytes(version_from, version_to)
        print(f"\n  [HTTP] Stage 2: Sent delta v{version_from}→v{version_to} "
              f"({len(delta_bytes):,} bytes)")
        return Response(delta_bytes, mimetype="application/octet-stream")
    except KeyError as e:
        return jsonify({"error": str(e)}), 404


@app.route("/firmware/<int:version>")
def get_firmware(version):
    """Return full firmware binary (for initial provisioning or recovery)."""
    if version not in firmware_versions:
        return jsonify({"error": f"Firmware v{version} not found"}), 404

    fw = firmware_versions[version]
    print(f"\n  [HTTP] Sent full firmware v{version} ({len(fw):,} bytes)")
    return Response(fw, mimetype="application/octet-stream")


# ============================================================================
#  MAIN
# ============================================================================

if __name__ == "__main__":
    initialize_server()

    print("\n" + "=" * 70)
    print("  Starting HTTP server on 0.0.0.0:5000")
    print("  ESP32 should connect to: http://<YOUR_PC_IP>:5000")
    print("=" * 70 + "\n")

    # Run on all interfaces so ESP32 can reach it over WiFi
    app.run(host="0.0.0.0", port=5000, debug=False)
