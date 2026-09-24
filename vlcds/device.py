"""
device.py — IoT Device Simulator (VLCDS Client)

Simulates an ESP32-class IoT device running the VLCDS 3-stage
verification protocol.

Three-Stage Verification (from Section 5 of the project report):

    Stage 1 — Pre-Verify (before ANY patch bytes transferred):
        1. Verify Ed25519 signature over 6-field manifest
        2. Check H(base_fw) matches hash of device's current firmware
        3. Check version_base matches device's installed version
        4. Check H(prev_manifest) matches device's chain head
        → If ANY fails: reject immediately, no patch data wasted

    Stage 2 — Patch Transfer & Application:
        1. Request delta patch from server
        2. Verify H(delta) against authenticated hash from Stage 1
        3. Apply delta patch to shadow partition

    Stage 3 — Post-Verify (no second signature needed):
        1. Hash reconstructed image on shadow partition
        2. Compare to H(target) from Stage-1 manifest
        → Only a cheap hash comparison, not a signature verification
        3. If match: flip active boot partition
"""

import time
from vlcds.crypto_utils import sha256, verify
from vlcds.manifest import Manifest
from vlcds.delta_engine import apply_delta
from vlcds.chain import ManifestChain, GENESIS_HASH


# ============================================================================
#  VERIFICATION RESULT
# ============================================================================

class VerificationResult:
    """Result of a stage verification with details for intermediate output."""

    def __init__(self, stage: str, passed: bool, details: dict = None, timing_ms: float = 0):
        self.stage = stage
        self.passed = passed
        self.details = details or {}
        self.timing_ms = timing_ms

    def __repr__(self):
        status = "✓ PASSED" if self.passed else "✗ FAILED"
        return f"<{self.stage}: {status} ({self.timing_ms:.3f} ms)>"


# ============================================================================
#  IOT DEVICE SIMULATOR
# ============================================================================

class IoTDevice:
    """
    Simulates an ESP32-S2 IoT device running VLCDS verification.

    State stored on device:
        - Current firmware binary
        - Current firmware version number
        - Vendor's Ed25519 public key (pre-provisioned)
        - Manifest chain head (for anti-replay)
    """

    def __init__(self, device_id: str, public_key, initial_firmware: bytes,
                 initial_version: int, verbose=False):
        """
        Initialize the device with pre-provisioned state.

        Args:
            device_id: Human-readable device identifier
            public_key: Vendor's Ed25519 VerifyKey (pre-provisioned in flash)
            initial_firmware: Factory firmware binary
            initial_version: Factory firmware version number
            verbose: Print intermediate results at each step
        """
        self.device_id = device_id
        self.public_key = public_key
        self.firmware = initial_firmware
        self.version = initial_version
        self.verbose = verbose

        # Hash-chain for anti-replay (starts at genesis)
        self._chain = ManifestChain()

        # Shadow partition (staging area for new firmware)
        self._shadow_partition = None

        # Staged manifest (kept between stages)
        self._staged_manifest = None

        # Performance counters
        self.stats = {
            'updates_accepted': 0,
            'updates_rejected_stage1': 0,
            'updates_rejected_stage2': 0,
            'updates_rejected_stage3': 0,
            'bytes_saved': 0,  # bytes NOT downloaded due to pre-verify rejection
        }

        if verbose:
            fw_hash = sha256(initial_firmware)
            print(f"\n  DEVICE INITIALIZED: {device_id}")
            print(f"  {'─' * 50}")
            print(f"    Firmware version : v{initial_version}")
            print(f"    Firmware size    : {len(initial_firmware):,} bytes")
            print(f"    Firmware hash    : {fw_hash.hex()}")
            print(f"    Public key       : {public_key.encode().hex()[:32]}...")
            print(f"    Chain head       : {self._chain.head.hex()}")
            print(f"  {'─' * 50}")

    # ========================================================================
    #  STAGE 1 — PRE-VERIFY
    # ========================================================================

    def stage1_pre_verify(self, manifest_bytes: bytes,
                          delta_size_hint: int = 0) -> VerificationResult:
        """
        Stage 1 — Pre-Verify: Verify manifest BEFORE requesting patch data.

        This is the key innovation of VLCDS: all checks are performed on the
        ~200-byte manifest, before any patch bytes are transferred.

        Checks performed (all on fields INSIDE the signed object):
            1. Ed25519 signature verification
            2. H(base_fw) matches device's current firmware hash
            3. version_base matches device's installed version
            4. H(prev_manifest) matches device's chain head

        Args:
            manifest_bytes: Serialized 200-byte manifest from server
            delta_size_hint: Size of delta patch (for bandwidth-saved tracking)

        Returns:
            VerificationResult with pass/fail and detailed check results
        """
        start = time.perf_counter()
        details = {}

        if self.verbose:
            print(f"\n{'=' * 70}")
            print(f"  STAGE 1 — PRE-VERIFY [{self.device_id}]")
            print(f"  Manifest received: {len(manifest_bytes)} bytes")
            print(f"{'=' * 70}")

        # Deserialize manifest
        try:
            manifest = Manifest.deserialize(manifest_bytes)
        except ValueError as e:
            elapsed = (time.perf_counter() - start) * 1000
            if self.verbose:
                print(f"  ✗ REJECTED: Invalid manifest format — {e}")
            self.stats['updates_rejected_stage1'] += 1
            return VerificationResult("Stage 1", False, {"error": str(e)}, elapsed)

        if self.verbose:
            manifest.print_fields("RECEIVED MANIFEST")

        # ── Check 1: Signature Verification ──
        if self.verbose:
            print(f"\n  Check 1/4: Ed25519 Signature Verification")
        sig_valid = manifest.verify_signature(self.public_key, verbose=self.verbose)
        details['signature_valid'] = sig_valid

        if not sig_valid:
            elapsed = (time.perf_counter() - start) * 1000
            if self.verbose:
                print(f"\n  ✗ REJECTED at Check 1: Invalid signature")
                print(f"    → Patch bytes NOT requested (saved {delta_size_hint:,} bytes)")
            self.stats['updates_rejected_stage1'] += 1
            self.stats['bytes_saved'] += delta_size_hint
            return VerificationResult("Stage 1", False, details, elapsed)

        # ── Check 2: Base Firmware Hash ──
        if self.verbose:
            print(f"\n  Check 2/4: H(base_fw) — Does this patch match our firmware?")
        my_fw_hash = sha256(self.firmware, verbose=self.verbose, label="my firmware")
        hash_match = manifest.h_base_fw == my_fw_hash
        details['base_fw_hash_match'] = hash_match
        details['expected_hash'] = manifest.h_base_fw.hex()
        details['actual_hash'] = my_fw_hash.hex()

        if self.verbose:
            status = "✓ MATCH" if hash_match else "✗ MISMATCH"
            print(f"    Manifest H(base_fw): {manifest.h_base_fw.hex()}")
            print(f"    Device firmware hash: {my_fw_hash.hex()}")
            print(f"    Result: {status}")

        if not hash_match:
            elapsed = (time.perf_counter() - start) * 1000
            if self.verbose:
                print(f"\n  ✗ REJECTED at Check 2: Firmware hash mismatch")
                print(f"    → This patch is not for our current firmware!")
                print(f"    → Patch bytes NOT requested (saved {delta_size_hint:,} bytes)")
            self.stats['updates_rejected_stage1'] += 1
            self.stats['bytes_saved'] += delta_size_hint
            return VerificationResult("Stage 1", False, details, elapsed)

        # ── Check 3: Version Number ──
        if self.verbose:
            print(f"\n  Check 3/4: Version binding — Is version_base correct?")
        version_match = manifest.version_base == self.version
        details['version_match'] = version_match
        details['manifest_version_base'] = manifest.version_base
        details['device_version'] = self.version

        if self.verbose:
            status = "✓ MATCH" if version_match else "✗ MISMATCH"
            print(f"    Manifest version_base: v{manifest.version_base}")
            print(f"    Device version       : v{self.version}")
            print(f"    Result: {status}")

        if not version_match:
            elapsed = (time.perf_counter() - start) * 1000
            if self.verbose:
                print(f"\n  ✗ REJECTED at Check 3: Version mismatch")
                print(f"    → Patch bytes NOT requested (saved {delta_size_hint:,} bytes)")
            self.stats['updates_rejected_stage1'] += 1
            self.stats['bytes_saved'] += delta_size_hint
            return VerificationResult("Stage 1", False, details, elapsed)

        # ── Check 4: Chain Link (Anti-Replay) ──
        if self.verbose:
            print(f"\n  Check 4/4: H(prev_manifest) — Chain link / anti-replay check")
        chain_valid = self._chain.verify_link(manifest.h_prev_manifest, verbose=self.verbose)
        details['chain_valid'] = chain_valid

        if not chain_valid:
            elapsed = (time.perf_counter() - start) * 1000
            if self.verbose:
                print(f"\n  ✗ REJECTED at Check 4: Chain link mismatch (possible replay attack!)")
                print(f"    → Patch bytes NOT requested (saved {delta_size_hint:,} bytes)")
            self.stats['updates_rejected_stage1'] += 1
            self.stats['bytes_saved'] += delta_size_hint
            return VerificationResult("Stage 1", False, details, elapsed)

        # All 4 checks passed — stage manifest for Stage 2
        self._staged_manifest = manifest
        elapsed = (time.perf_counter() - start) * 1000

        if self.verbose:
            print(f"\n  ✓ STAGE 1 PASSED — All 4 checks verified ({elapsed:.3f} ms)")
            print(f"    → Device will now request delta patch from server")

        return VerificationResult("Stage 1", True, details, elapsed)

    # ========================================================================
    #  STAGE 2 — PATCH TRANSFER & APPLICATION
    # ========================================================================

    def stage2_patch_and_apply(self, delta_patch: bytes) -> VerificationResult:
        """
        Stage 2 — Receive delta patch, verify its hash, apply to shadow partition.

        The patch itself has no signature — its integrity is guaranteed by
        H(delta) which was already authenticated in Stage 1.

        Args:
            delta_patch: Delta patch bytes from server

        Returns:
            VerificationResult
        """
        start = time.perf_counter()
        details = {}

        if self.verbose:
            print(f"\n{'=' * 70}")
            print(f"  STAGE 2 — PATCH TRANSFER & APPLICATION [{self.device_id}]")
            print(f"  Delta patch received: {len(delta_patch):,} bytes")
            print(f"{'=' * 70}")

        if self._staged_manifest is None:
            elapsed = (time.perf_counter() - start) * 1000
            if self.verbose:
                print(f"  ✗ REJECTED: No staged manifest (Stage 1 not completed)")
            self.stats['updates_rejected_stage2'] += 1
            return VerificationResult("Stage 2", False, {"error": "no staged manifest"}, elapsed)

        manifest = self._staged_manifest

        # ── Check: Delta Hash ──
        if self.verbose:
            print(f"\n  Verifying delta patch integrity via H(delta)...")
        delta_hash = sha256(delta_patch, verbose=self.verbose, label="received delta")
        hash_match = delta_hash == manifest.h_delta
        details['delta_hash_match'] = hash_match

        if self.verbose:
            status = "✓ MATCH" if hash_match else "✗ MISMATCH"
            print(f"    Manifest H(delta)  : {manifest.h_delta.hex()}")
            print(f"    Received delta hash: {delta_hash.hex()}")
            print(f"    Result: {status}")

        if not hash_match:
            elapsed = (time.perf_counter() - start) * 1000
            if self.verbose:
                print(f"\n  ✗ REJECTED at Stage 2: Delta hash mismatch")
                print(f"    → Patch may have been tampered with in transit!")
            self.stats['updates_rejected_stage2'] += 1
            self._staged_manifest = None
            return VerificationResult("Stage 2", False, details, elapsed)

        # ── Apply patch to shadow partition ──
        if self.verbose:
            print(f"\n  Applying delta patch to shadow partition...")
        try:
            self._shadow_partition = apply_delta(self.firmware, delta_patch, verbose=self.verbose)
            details['reconstructed_size'] = len(self._shadow_partition)
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            if self.verbose:
                print(f"\n  ✗ REJECTED: Patch application failed — {e}")
            self.stats['updates_rejected_stage2'] += 1
            self._staged_manifest = None
            return VerificationResult("Stage 2", False, {"error": str(e)}, elapsed)

        elapsed = (time.perf_counter() - start) * 1000
        if self.verbose:
            print(f"\n  ✓ STAGE 2 PASSED — Patch applied to shadow partition ({elapsed:.3f} ms)")
            print(f"    → Proceeding to Stage 3 post-verify")

        return VerificationResult("Stage 2", True, details, elapsed)

    # ========================================================================
    #  STAGE 3 — POST-VERIFY
    # ========================================================================

    def stage3_post_verify(self) -> VerificationResult:
        """
        Stage 3 — Post-Verify: Hash reconstructed image and compare to H(target).

        Key insight from Section 4.2: No second signature verification is needed.
        H(target) was already committed inside the Stage-1 signature, so post-verify
        is just a cheap hash comparison — saving energy on constrained hardware.

        Returns:
            VerificationResult
        """
        start = time.perf_counter()
        details = {}

        if self.verbose:
            print(f"\n{'=' * 70}")
            print(f"  STAGE 3 — POST-VERIFY [{self.device_id}]")
            print(f"{'=' * 70}")

        if self._shadow_partition is None or self._staged_manifest is None:
            elapsed = (time.perf_counter() - start) * 1000
            if self.verbose:
                print(f"  ✗ REJECTED: Shadow partition empty (Stage 2 not completed)")
            self.stats['updates_rejected_stage3'] += 1
            return VerificationResult("Stage 3", False, {"error": "no shadow partition"}, elapsed)

        manifest = self._staged_manifest

        # ── Hash reconstructed image ──
        if self.verbose:
            print(f"\n  Hashing reconstructed firmware on shadow partition...")
            print(f"  (Note: This is ONLY a hash comparison — no second signature needed!)")
        recon_hash = sha256(self._shadow_partition, verbose=self.verbose,
                           label="reconstructed firmware")

        # ── Compare to H(target) from Stage-1 manifest ──
        hash_match = recon_hash == manifest.h_target
        details['target_hash_match'] = hash_match
        details['expected_target'] = manifest.h_target.hex()
        details['actual_target'] = recon_hash.hex()

        if self.verbose:
            status = "✓ MATCH" if hash_match else "✗ MISMATCH"
            print(f"\n  Comparing to H(target) from Stage-1 manifest:")
            print(f"    Manifest H(target)    : {manifest.h_target.hex()}")
            print(f"    Reconstructed hash    : {recon_hash.hex()}")
            print(f"    Result: {status}")

        if not hash_match:
            elapsed = (time.perf_counter() - start) * 1000
            if self.verbose:
                print(f"\n  ✗ REJECTED at Stage 3: Reconstructed image hash mismatch")
                print(f"    → Patch application produced wrong result!")
                print(f"    → Shadow partition will be erased, boot partition unchanged")
            self._shadow_partition = None
            self._staged_manifest = None
            self.stats['updates_rejected_stage3'] += 1
            return VerificationResult("Stage 3", False, details, elapsed)

        # ── SUCCESS: Flip boot partition ──
        old_version = self.version
        self.firmware = self._shadow_partition
        self.version = manifest.version_target

        # Record manifest in chain
        self._chain.record(manifest.serialize(), verbose=self.verbose)

        # Clean up
        self._shadow_partition = None
        self._staged_manifest = None
        self.stats['updates_accepted'] += 1

        elapsed = (time.perf_counter() - start) * 1000

        if self.verbose:
            print(f"\n  ✓ STAGE 3 PASSED — Update complete! ({elapsed:.3f} ms)")
            print(f"    Firmware updated: v{old_version} → v{self.version}")
            print(f"    Boot partition flipped to new image")
            new_hash = sha256(self.firmware)
            print(f"    New firmware hash: {new_hash.hex()}")
            print(f"    Chain head updated: {self._chain.head.hex()}")

        return VerificationResult("Stage 3", True, details, elapsed)

    # ========================================================================
    #  FULL UPDATE FLOW
    # ========================================================================

    def perform_full_update(self, manifest_bytes: bytes, delta_patch: bytes) -> bool:
        """
        Execute the complete 3-stage VLCDS update flow.

        Args:
            manifest_bytes: 200-byte signed manifest (Stage 1)
            delta_patch: Delta patch bytes (Stage 2)

        Returns:
            bool: True if update completed successfully
        """
        # Stage 1
        r1 = self.stage1_pre_verify(manifest_bytes, delta_size_hint=len(delta_patch))
        if not r1.passed:
            return False

        # Stage 2
        r2 = self.stage2_patch_and_apply(delta_patch)
        if not r2.passed:
            return False

        # Stage 3
        r3 = self.stage3_post_verify()
        return r3.passed

    def print_status(self):
        """Print current device status."""
        fw_hash = sha256(self.firmware)
        print(f"\n  DEVICE STATUS: {self.device_id}")
        print(f"  {'─' * 50}")
        print(f"    Version          : v{self.version}")
        print(f"    Firmware size    : {len(self.firmware):,} bytes")
        print(f"    Firmware hash    : {fw_hash.hex()}")
        print(f"    Chain length     : {self._chain.length}")
        print(f"    Chain head       : {self._chain.head.hex()[:32]}...")
        print(f"    Updates accepted : {self.stats['updates_accepted']}")
        print(f"    Rejected (Stage 1): {self.stats['updates_rejected_stage1']}")
        print(f"    Rejected (Stage 2): {self.stats['updates_rejected_stage2']}")
        print(f"    Rejected (Stage 3): {self.stats['updates_rejected_stage3']}")
        print(f"    Bytes saved      : {self.stats['bytes_saved']:,}")
        print(f"  {'─' * 50}")


# ============================================================================
#  SELF-TEST
# ============================================================================

if __name__ == "__main__":
    from vlcds.server import OTAServer

    print("\n" + "=" * 70)
    print("  VLCDS Device Simulator — Self-Test")
    print("=" * 70)

    # Set up server
    server = OTAServer(verbose=True)

    # Create firmware versions
    fw1 = b"ESP32_FW_V1_" + bytes(range(256)) * 8 + b"_END"
    fw2 = b"ESP32_FW_V2_" + bytes(range(256)) * 8 + b"_UPDATED_END"

    server.add_firmware(1, fw1)
    server.add_firmware(2, fw2)

    # Create device
    device = IoTDevice(
        device_id="ESP32-S2-001",
        public_key=server.public_key,
        initial_firmware=fw1,
        initial_version=1,
        verbose=True,
    )

    device.print_status()

    # Prepare and perform update
    manifest, delta = server.prepare_update(1, 2)
    success = device.perform_full_update(manifest.serialize(), delta)

    print(f"\n  Update result: {'SUCCESS' if success else 'FAILED'}")
    device.print_status()

    print("\n" + "=" * 70)
    print("  Self-test complete.")
    print("=" * 70)
