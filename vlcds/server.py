"""
server.py — OTA Update Server

Simulates the server-side of the VLCDS protocol:
- Manages firmware repository (multiple versions)
- Creates delta patches between firmware versions
- Builds and signs VLCDS manifests
- Serves updates in the two-stage flow:
    Stage 1: Send only the 200-byte manifest
    Stage 2: Send delta patch on device request (after pre-verify passes)

In the ESP32 demo, this runs as an HTTP server on the PC.
"""

from vlcds.crypto_utils import generate_keypair, sha256
from vlcds.manifest import build_manifest, Manifest
from vlcds.delta_engine import create_delta
from vlcds.chain import ManifestChain, GENESIS_HASH


class OTAServer:
    """
    VLCDS OTA Update Server.

    Manages firmware versions, creates delta patches, and signs manifests.
    """

    def __init__(self, verbose=False):
        """
        Initialize the server with a fresh Ed25519 key pair.

        The public key must be pre-provisioned on all devices.
        """
        self.verbose = verbose
        self._private_key, self.public_key = generate_keypair(verbose=verbose)
        self._firmware_repo = {}     # version_number → firmware_bytes
        self._delta_cache = {}       # (v_from, v_to) → delta_bytes
        self._manifest_cache = {}    # (v_from, v_to) → Manifest
        self._chain = ManifestChain()  # Server's view of the chain

        if verbose:
            print(f"\n  OTA Server initialized.")
            print(f"  Public key (provision to devices): {self.public_key.encode().hex()}")

    # ========================================================================
    #  FIRMWARE MANAGEMENT
    # ========================================================================

    def add_firmware(self, version: int, firmware: bytes):
        """
        Register a firmware version in the server's repository.

        Args:
            version: Version number (monotonically increasing)
            firmware: Raw firmware binary
        """
        self._firmware_repo[version] = firmware
        if self.verbose:
            h = sha256(firmware)
            print(f"\n  Registered firmware v{version}:")
            print(f"    Size : {len(firmware):,} bytes")
            print(f"    Hash : {h.hex()}")

    def get_firmware(self, version: int) -> bytes:
        """Get firmware binary for a given version."""
        if version not in self._firmware_repo:
            raise KeyError(f"Firmware v{version} not found in repository")
        return self._firmware_repo[version]

    # ========================================================================
    #  UPDATE PREPARATION
    # ========================================================================

    def prepare_update(self, version_from: int, version_to: int,
                       prev_manifest_hash: bytes = None) -> tuple:
        """
        Prepare a VLCDS update from version_from to version_to.

        This is the server-side logic:
        1. Retrieve both firmware versions
        2. Create delta patch
        3. Build and sign the 6-field manifest
        4. Return (manifest, delta_patch) — manifest sent first in Stage 1

        Args:
            version_from: Device's current firmware version
            version_to: Target firmware version
            prev_manifest_hash: Chain link to previous manifest
                                (None uses server's internal chain)

        Returns:
            tuple: (Manifest, delta_patch_bytes)
        """
        if self.verbose:
            print(f"\n{'=' * 70}")
            print(f"  PREPARING UPDATE: v{version_from} → v{version_to}")
            print(f"{'=' * 70}")

        # Get firmware binaries
        fw_old = self.get_firmware(version_from)
        fw_new = self.get_firmware(version_to)

        # Create delta patch
        cache_key = (version_from, version_to)
        if cache_key not in self._delta_cache:
            delta = create_delta(fw_old, fw_new, verbose=self.verbose)
            self._delta_cache[cache_key] = delta
        else:
            delta = self._delta_cache[cache_key]
            if self.verbose:
                print(f"  Using cached delta: {len(delta):,} bytes")

        # Determine chain link
        if prev_manifest_hash is None:
            prev_manifest_hash = self._chain.head

        # Build and sign manifest
        manifest = build_manifest(
            base_firmware=fw_old,
            delta_patch=delta,
            target_firmware=fw_new,
            version_base=version_from,
            version_target=version_to,
            prev_manifest_hash=prev_manifest_hash,
            private_key=self._private_key,
            verbose=self.verbose,
        )

        # Cache manifest and update server chain
        self._manifest_cache[cache_key] = manifest
        self._chain.record(manifest.serialize(), verbose=self.verbose)

        if self.verbose:
            print(f"\n  Update prepared successfully.")
            print(f"  Manifest size : {len(manifest.serialize())} bytes (Stage 1 packet)")
            print(f"  Delta size    : {len(delta):,} bytes (Stage 2, on request)")
            print(f"{'=' * 70}")

        return manifest, delta

    # ========================================================================
    #  STAGE 1: SERVE MANIFEST
    # ========================================================================

    def get_manifest_bytes(self, version_from: int, version_to: int) -> bytes:
        """
        Get the serialized manifest for Stage 1 transmission.

        Only 200 bytes — sent BEFORE any patch data.
        """
        cache_key = (version_from, version_to)
        if cache_key not in self._manifest_cache:
            self.prepare_update(version_from, version_to)
        return self._manifest_cache[cache_key].serialize()

    # ========================================================================
    #  STAGE 2: SERVE DELTA PATCH
    # ========================================================================

    def get_delta_bytes(self, version_from: int, version_to: int) -> bytes:
        """
        Get the delta patch for Stage 2 transmission.

        This is sent ONLY after the device has pre-verified the manifest.
        """
        cache_key = (version_from, version_to)
        if cache_key not in self._delta_cache:
            self.prepare_update(version_from, version_to)
        return self._delta_cache[cache_key]


# ============================================================================
#  SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  VLCDS OTA Server — Self-Test")
    print("=" * 70)

    server = OTAServer(verbose=True)

    # Register firmware versions
    fw1 = b"ESP32_FIRMWARE_V1_" + bytes(range(256)) * 10 + b"_END_V1"
    fw2 = b"ESP32_FIRMWARE_V2_" + bytes(range(256)) * 10 + b"_UPDATED_END_V2"
    fw3 = b"ESP32_FIRMWARE_V3_" + bytes(range(256)) * 10 + b"_LATEST_END_V3_NEW"

    server.add_firmware(1, fw1)
    server.add_firmware(2, fw2)
    server.add_firmware(3, fw3)

    # Prepare v1→v2 update
    manifest_1, delta_1 = server.prepare_update(1, 2)
    print(f"\n  v1→v2 manifest signature valid: {manifest_1.verify_signature(server.public_key)}")

    # Prepare v2→v3 update
    manifest_2, delta_2 = server.prepare_update(2, 3)
    print(f"  v2→v3 manifest signature valid: {manifest_2.verify_signature(server.public_key)}")

    print("\n" + "=" * 70)
    print("  Self-test complete.")
    print("=" * 70)
