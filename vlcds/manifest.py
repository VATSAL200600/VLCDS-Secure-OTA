"""
manifest.py — VLCDS Six-Field Signed Manifest

Implements the core signed object from Section 4 of the project report:

    M = Sign_privkey( H(base_fw) ‖ H(delta) ‖ H(target) ‖ version_base ‖ version_target ‖ H(prev_manifest) )

This single signature makes it computationally infeasible to satisfy verification
unless all six bound facts are simultaneously true.

Packet Structure (from Section 5.4):
    ┌─────────────────┬───────┐
    │ Field           │ Size  │
    ├─────────────────┼───────┤
    │ H(base_fw)      │ 32 B  │
    │ H(delta)        │ 32 B  │
    │ H(target)       │ 32 B  │
    │ version_base    │  4 B  │
    │ version_target  │  4 B  │
    │ H(prev_manifest)│ 32 B  │
    │ signature       │ 64 B  │
    ├─────────────────┼───────┤
    │ TOTAL           │ 200 B │
    └─────────────────┴───────┘
"""

import struct
from dataclasses import dataclass
from vlcds.crypto_utils import sha256, sign, verify


# ============================================================================
#  MANIFEST DATA STRUCTURE
# ============================================================================

# Wire format: 6 fields (136 bytes payload) + 64 bytes signature = 200 bytes total
MANIFEST_PAYLOAD_SIZE = 136  # 32*4 + 4*2
MANIFEST_TOTAL_SIZE = 200    # 136 + 64
VERSION_FORMAT = ">I"        # unsigned 32-bit big-endian integer


@dataclass
class Manifest:
    """
    VLCDS Six-Field Signed Manifest.

    Binds firmware content, version state, and update history
    into a single cryptographically authenticated object.
    """
    h_base_fw: bytes        # SHA-256 of current firmware on device (32 bytes)
    h_delta: bytes          # SHA-256 of the delta patch (32 bytes)
    h_target: bytes         # SHA-256 of expected firmware after patching (32 bytes)
    version_base: int       # Version number device should currently be on
    version_target: int     # Version number after this update
    h_prev_manifest: bytes  # SHA-256 of previous accepted manifest (32 bytes) — chain link
    signature: bytes        # Ed25519 signature over concatenated fields (64 bytes)

    def get_payload(self) -> bytes:
        """
        Serialize the 6 fields into the canonical byte sequence for signing.

        Returns the concatenation:
            H(base_fw) ‖ H(delta) ‖ H(target) ‖ version_base ‖ version_target ‖ H(prev_manifest)
        """
        return (
            self.h_base_fw +
            self.h_delta +
            self.h_target +
            struct.pack(VERSION_FORMAT, self.version_base) +
            struct.pack(VERSION_FORMAT, self.version_target) +
            self.h_prev_manifest
        )

    def serialize(self) -> bytes:
        """
        Serialize the full manifest (payload + signature) to wire format.

        Total: 200 bytes — small enough for LoRa, Zigbee, BLE, or any constrained link.
        """
        return self.get_payload() + self.signature

    @classmethod
    def deserialize(cls, data: bytes) -> 'Manifest':
        """
        Deserialize a manifest from wire-format bytes.

        Args:
            data: Exactly 200 bytes

        Returns:
            Manifest instance

        Raises:
            ValueError: If data is not exactly 200 bytes
        """
        if len(data) != MANIFEST_TOTAL_SIZE:
            raise ValueError(
                f"Manifest must be exactly {MANIFEST_TOTAL_SIZE} bytes, "
                f"got {len(data)}"
            )

        offset = 0

        h_base_fw = data[offset:offset + 32]; offset += 32
        h_delta = data[offset:offset + 32]; offset += 32
        h_target = data[offset:offset + 32]; offset += 32
        version_base = struct.unpack(VERSION_FORMAT, data[offset:offset + 4])[0]; offset += 4
        version_target = struct.unpack(VERSION_FORMAT, data[offset:offset + 4])[0]; offset += 4
        h_prev_manifest = data[offset:offset + 32]; offset += 32
        signature = data[offset:offset + 64]

        return cls(
            h_base_fw=h_base_fw,
            h_delta=h_delta,
            h_target=h_target,
            version_base=version_base,
            version_target=version_target,
            h_prev_manifest=h_prev_manifest,
            signature=signature,
        )

    def verify_signature(self, public_key, verbose=False) -> bool:
        """
        Verify the Ed25519 signature over the manifest payload.

        This is the first operation in Stage 1 (Pre-Verify).
        """
        payload = self.get_payload()
        result = verify(public_key, payload, self.signature, verbose=verbose)
        return result

    def get_manifest_hash(self) -> bytes:
        """
        Compute SHA-256 of the full serialized manifest.
        Used as the chain link (H(prev_manifest)) for the next update.
        """
        return sha256(self.serialize())

    def print_fields(self, title="MANIFEST FIELDS"):
        """
        Print a detailed field-by-field breakdown for intermediate results.
        """
        print(f"\n  {'─' * 66}")
        print(f"  {title}")
        print(f"  {'─' * 66}")
        print(f"  │ Field           │ Value (hex)                                          │ Size  │")
        print(f"  ├─────────────────┼──────────────────────────────────────────────────────┼───────┤")
        print(f"  │ H(base_fw)      │ {self.h_base_fw.hex()[:50]} │ 32 B  │")
        print(f"  │ H(delta)        │ {self.h_delta.hex()[:50]} │ 32 B  │")
        print(f"  │ H(target)       │ {self.h_target.hex()[:50]} │ 32 B  │")
        print(f"  │ version_base    │ {self.version_base:<52} │  4 B  │")
        print(f"  │ version_target  │ {self.version_target:<52} │  4 B  │")
        print(f"  │ H(prev_manifest)│ {self.h_prev_manifest.hex()[:50]} │ 32 B  │")
        print(f"  │ signature       │ {self.signature.hex()[:50]} │ 64 B  │")
        print(f"  ├─────────────────┼──────────────────────────────────────────────────────┼───────┤")
        print(f"  │ TOTAL ON WIRE   │ {MANIFEST_TOTAL_SIZE} bytes (fits LoRa/BLE/Zigbee single frame){' ' * 6}│       │")
        print(f"  {'─' * 66}")


# ============================================================================
#  MANIFEST BUILDER (Server-Side)
# ============================================================================

def build_manifest(
    base_firmware: bytes,
    delta_patch: bytes,
    target_firmware: bytes,
    version_base: int,
    version_target: int,
    prev_manifest_hash: bytes,
    private_key,
    verbose=False,
) -> Manifest:
    """
    Build and sign a VLCDS manifest.

    This is called on the OTA update server. It:
    1. Computes SHA-256 hashes of all firmware artifacts
    2. Concatenates the 6 fields into the canonical payload
    3. Signs the payload with the server's Ed25519 private key

    Args:
        base_firmware: Binary content of the firmware currently on the device
        delta_patch: Binary content of the delta patch
        target_firmware: Binary content of the firmware after patching
        version_base: Current version number
        version_target: Target version number
        prev_manifest_hash: SHA-256 of the previous manifest (32 bytes, or 32 zero bytes for genesis)
        private_key: Ed25519 SigningKey

    Returns:
        Signed Manifest instance
    """
    if verbose:
        print("\n" + "=" * 70)
        print("  BUILDING VLCDS MANIFEST (Server-Side)")
        print("=" * 70)

    # Step 1: Compute hashes of all firmware artifacts
    h_base = sha256(base_firmware, verbose=verbose, label="H(base_fw)")
    h_delta = sha256(delta_patch, verbose=verbose, label="H(delta)")
    h_target = sha256(target_firmware, verbose=verbose, label="H(target)")

    if verbose:
        print(f"\n  Version binding: v{version_base} → v{version_target}")
        print(f"  Chain link H(prev): {prev_manifest_hash.hex()[:32]}...")

    # Step 2: Construct payload
    payload = (
        h_base + h_delta + h_target +
        struct.pack(VERSION_FORMAT, version_base) +
        struct.pack(VERSION_FORMAT, version_target) +
        prev_manifest_hash
    )

    if verbose:
        print(f"\n  Concatenated payload: {len(payload)} bytes")
        print(f"    = 32 + 32 + 32 + 4 + 4 + 32 = {32+32+32+4+4+32}")

    # Step 3: Sign
    if verbose:
        print(f"\n  Signing payload with Ed25519...")
    signature = sign(private_key, payload, verbose=verbose)

    # Step 4: Construct manifest
    manifest = Manifest(
        h_base_fw=h_base,
        h_delta=h_delta,
        h_target=h_target,
        version_base=version_base,
        version_target=version_target,
        h_prev_manifest=prev_manifest_hash,
        signature=signature,
    )

    if verbose:
        manifest.print_fields()
        serialized = manifest.serialize()
        print(f"\n  Serialized manifest: {len(serialized)} bytes")
        print(f"  Manifest hash (for next chain link): {manifest.get_manifest_hash().hex()}")

    return manifest


if __name__ == "__main__":
    from vlcds.crypto_utils import generate_keypair

    print("\n" + "=" * 70)
    print("  VLCDS Manifest Module — Self-Test")
    print("=" * 70)

    # Generate keys
    priv, pub = generate_keypair(verbose=True)

    # Create test data
    fw_v1 = b"FIRMWARE_V1_" + bytes(range(256)) * 4
    fw_v2 = b"FIRMWARE_V2_" + bytes(range(256)) * 4
    delta = b"DELTA_PATCH_CONTENT_v1_to_v2"
    genesis_hash = b"\x00" * 32  # First update has no previous manifest

    # Build manifest
    m = build_manifest(
        base_firmware=fw_v1,
        delta_patch=delta,
        target_firmware=fw_v2,
        version_base=1,
        version_target=2,
        prev_manifest_hash=genesis_hash,
        private_key=priv,
        verbose=True,
    )

    # Verify signature
    print("\n  Verifying manifest signature...")
    valid = m.verify_signature(pub, verbose=True)
    print(f"  Result: {'✓ VALID' if valid else '✗ INVALID'}")

    # Test serialization round-trip
    serialized = m.serialize()
    m2 = Manifest.deserialize(serialized)
    assert m2.h_base_fw == m.h_base_fw
    assert m2.version_base == m.version_base
    assert m2.signature == m.signature
    print(f"\n  Serialization round-trip: ✓ PASSED")

    print("\n" + "=" * 70)
    print("  Self-test complete.")
    print("=" * 70)
