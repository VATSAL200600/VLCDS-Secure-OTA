"""
delta_engine.py — Delta (Differential) Firmware Patching

Implements a simple but functional binary diff/patch engine suitable
for both PC simulation and MicroPython on ESP32.

Uses bsdiff4-style approach: stores control instructions with
add/insert operations for compact delta representation.

Delta Patch Format:
    Header: "VLCDS_DELTA" (11 bytes) + old_size (4B) + new_size (4B)
    Instructions:
        ADD <length> <diff_bytes>    — XOR differences against base
        INSERT <length> <new_bytes>  — new bytes not in base
        COPY <offset> <length>       — copy from base (optimization)
"""

import struct
import io


# ============================================================================
#  DELTA FORMAT CONSTANTS
# ============================================================================

DELTA_MAGIC = b"VLCDS_DELTA"
HEADER_FORMAT = ">II"  # old_size, new_size (big-endian uint32)
HEADER_SIZE = len(DELTA_MAGIC) + struct.calcsize(HEADER_FORMAT)

# Instruction opcodes
OP_DIFF = 0x01    # Byte-by-byte difference (XOR) against base
OP_INSERT = 0x02  # Inserted bytes not present in base
OP_END = 0xFF     # End of patch


# ============================================================================
#  DELTA CREATION (Server-Side)
# ============================================================================

def create_delta(old_firmware: bytes, new_firmware: bytes, verbose=False) -> bytes:
    """
    Create a delta patch from old firmware to new firmware.

    Algorithm:
    1. For overlapping region (min length), compute XOR differences
    2. For extra bytes in new firmware, use INSERT instructions
    3. Pack into compact binary format

    This is simpler than bsdiff but sufficient for demonstrating
    the VLCDS protocol. In production, use bsdiff/detools.

    Args:
        old_firmware: Current firmware binary
        new_firmware: Target firmware binary
        verbose: Print intermediate values

    Returns:
        bytes: Delta patch in VLCDS_DELTA format
    """
    old_len = len(old_firmware)
    new_len = len(new_firmware)

    if verbose:
        print(f"\n  DELTA CREATION")
        print(f"  {'─' * 50}")
        print(f"    Old firmware size : {old_len:,} bytes")
        print(f"    New firmware size : {new_len:,} bytes")

    patch = io.BytesIO()

    # Write header
    patch.write(DELTA_MAGIC)
    patch.write(struct.pack(HEADER_FORMAT, old_len, new_len))

    # Compute overlapping region differences (XOR-based diff)
    overlap = min(old_len, new_len)

    if overlap > 0:
        # Find contiguous blocks of differences
        diff_blocks = []
        i = 0
        while i < overlap:
            # Find start of a difference block
            if old_firmware[i] != new_firmware[i]:
                block_start = i
                diff_bytes = bytearray()
                while i < overlap and old_firmware[i] != new_firmware[i]:
                    # Store XOR so we can reconstruct: new = old ^ diff
                    diff_bytes.append(old_firmware[i] ^ new_firmware[i])
                    i += 1
                diff_blocks.append((block_start, bytes(diff_bytes)))
            else:
                i += 1

        # Write DIFF instructions
        for offset, diff_data in diff_blocks:
            patch.write(struct.pack("B", OP_DIFF))
            patch.write(struct.pack(">I", offset))   # offset into base
            patch.write(struct.pack(">I", len(diff_data)))  # length
            patch.write(diff_data)

        if verbose:
            print(f"    Diff blocks      : {len(diff_blocks)}")
            total_diff = sum(len(d) for _, d in diff_blocks)
            print(f"    Total diff bytes : {total_diff:,}")

    # Handle extra bytes in new firmware (INSERT)
    if new_len > old_len:
        extra = new_firmware[old_len:]
        patch.write(struct.pack("B", OP_INSERT))
        patch.write(struct.pack(">I", old_len))     # offset = end of old
        patch.write(struct.pack(">I", len(extra)))   # length
        patch.write(extra)

        if verbose:
            print(f"    Inserted bytes   : {len(extra):,} (new firmware is larger)")

    # Handle truncation (new firmware shorter)
    # The new_size in header handles this — patch application uses new_size as final length

    # End marker
    patch.write(struct.pack("B", OP_END))

    patch_bytes = patch.getvalue()

    if verbose:
        ratio = len(patch_bytes) / new_len * 100 if new_len > 0 else 0
        savings = (1 - len(patch_bytes) / new_len) * 100 if new_len > 0 else 0
        print(f"    Delta patch size : {len(patch_bytes):,} bytes")
        print(f"    Compression ratio: {ratio:.1f}% of full image")
        print(f"    Bandwidth saved  : {savings:.1f}%")
        print(f"  {'─' * 50}")

    return patch_bytes


# ============================================================================
#  DELTA APPLICATION (Device-Side)
# ============================================================================

def apply_delta(old_firmware: bytes, delta_patch: bytes, verbose=False) -> bytes:
    """
    Apply a delta patch to reconstruct the new firmware.

    This runs on the device (ESP32) after Stage 1 pre-verify passes.

    Args:
        old_firmware: Current firmware binary on device
        delta_patch: Delta patch received from server

    Returns:
        bytes: Reconstructed new firmware

    Raises:
        ValueError: If patch format is invalid or base size mismatch
    """
    reader = io.BytesIO(delta_patch)

    # Read and verify header
    magic = reader.read(len(DELTA_MAGIC))
    if magic != DELTA_MAGIC:
        raise ValueError(f"Invalid delta magic: expected {DELTA_MAGIC!r}, got {magic!r}")

    old_size, new_size = struct.unpack(HEADER_FORMAT, reader.read(struct.calcsize(HEADER_FORMAT)))

    if len(old_firmware) != old_size:
        raise ValueError(
            f"Base firmware size mismatch: patch expects {old_size} bytes, "
            f"got {len(old_firmware)} bytes"
        )

    if verbose:
        print(f"\n  DELTA APPLICATION")
        print(f"  {'─' * 50}")
        print(f"    Base firmware     : {old_size:,} bytes")
        print(f"    Expected new size : {new_size:,} bytes")

    # Start with a copy of old firmware (padded or truncated to new_size)
    if new_size >= old_size:
        result = bytearray(old_firmware) + bytearray(new_size - old_size)
    else:
        result = bytearray(old_firmware[:new_size])

    instructions_applied = 0

    # Process instructions
    while True:
        op_byte = reader.read(1)
        if not op_byte:
            break

        opcode = struct.unpack("B", op_byte)[0]

        if opcode == OP_END:
            break

        elif opcode == OP_DIFF:
            offset = struct.unpack(">I", reader.read(4))[0]
            length = struct.unpack(">I", reader.read(4))[0]
            diff_data = reader.read(length)

            # Apply XOR differences: new[i] = old[i] ^ diff[i]
            for i in range(length):
                result[offset + i] = result[offset + i] ^ diff_data[i]

            instructions_applied += 1
            if verbose:
                print(f"    DIFF @ offset {offset}: {length} bytes modified")

        elif opcode == OP_INSERT:
            offset = struct.unpack(">I", reader.read(4))[0]
            length = struct.unpack(">I", reader.read(4))[0]
            insert_data = reader.read(length)

            # Write inserted bytes
            for i in range(length):
                result[offset + i] = insert_data[i]

            instructions_applied += 1
            if verbose:
                print(f"    INSERT @ offset {offset}: {length} bytes inserted")

        else:
            raise ValueError(f"Unknown opcode: 0x{opcode:02x}")

    result_bytes = bytes(result[:new_size])

    if verbose:
        print(f"    Instructions     : {instructions_applied}")
        print(f"    Result size      : {len(result_bytes):,} bytes")
        print(f"  {'─' * 50}")

    return result_bytes


# ============================================================================
#  SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  VLCDS Delta Engine — Self-Test")
    print("=" * 70)

    # Create synthetic firmware versions
    fw_v1 = b"FIRMWARE_V1_HEADER_" + bytes(range(256)) * 4 + b"_FOOTER_V1"
    fw_v2 = b"FIRMWARE_V2_HEADER_" + bytes(range(256)) * 4 + b"_FOOTER_V2_EXTRA_DATA"

    print(f"\n  Firmware v1: {len(fw_v1):,} bytes")
    print(f"  Firmware v2: {len(fw_v2):,} bytes")

    # Create delta
    delta = create_delta(fw_v1, fw_v2, verbose=True)

    # Apply delta
    reconstructed = apply_delta(fw_v1, delta, verbose=True)

    # Verify
    if reconstructed == fw_v2:
        print(f"\n  ✓ PATCH VERIFIED: Reconstructed firmware matches target exactly!")
    else:
        print(f"\n  ✗ PATCH FAILED: Mismatch!")
        # Find first difference
        for i in range(min(len(reconstructed), len(fw_v2))):
            if reconstructed[i] != fw_v2[i]:
                print(f"    First diff at byte {i}: got 0x{reconstructed[i]:02x}, expected 0x{fw_v2[i]:02x}")
                break

    print("\n" + "=" * 70)
    print("  Self-test complete.")
    print("=" * 70)
