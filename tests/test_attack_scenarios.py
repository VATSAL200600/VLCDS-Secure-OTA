"""
test_attack_scenarios.py — Security Tests for VLCDS

Tests the 3 attack vectors from report Section 5.6:
    (a) Version Mismatch: patch for wrong base firmware → reject Stage 1
    (b) Replay Attack: old valid manifest replayed → reject Stage 1 (chain)
    (c) Tampered Delta: modified patch bytes → reject Stage 2

Attacker model: Dolev-Yao network attacker (as specified in report Section 5.6)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from vlcds.crypto_utils import generate_keypair, sha256
from vlcds.manifest import build_manifest, Manifest
from vlcds.delta_engine import create_delta
from vlcds.chain import GENESIS_HASH
from vlcds.server import OTAServer
from vlcds.device import IoTDevice


# ============================================================================
#  FIXTURES
# ============================================================================

def make_firmware(version, size=2048):
    header = f"FW_v{version}_".encode()
    body = bytes([(b + version * 37) % 256 for b in range(size)])
    return header + body + f"_END_v{version}".encode()


@pytest.fixture
def firmwares():
    return {v: make_firmware(v) for v in range(1, 4)}


@pytest.fixture
def server(firmwares):
    srv = OTAServer(verbose=False)
    for v, fw in firmwares.items():
        srv.add_firmware(v, fw)
    return srv


# ============================================================================
#  ATTACK (a): VERSION MISMATCH
# ============================================================================

class TestVersionMismatchAttack:
    """
    Attack: Send a manifest built for fw_v2→v3 to a device running fw_v1.

    The patch was computed against fw_v2, so H(base_fw) inside the manifest
    will be SHA-256(fw_v2), which differs from SHA-256(fw_v1) on the device.

    Expected: REJECT at Stage 1, Check 2 (H(base_fw) mismatch).
    """

    def test_wrong_base_rejected_at_stage1(self, firmwares, server):
        """v2→v3 manifest sent to v1 device is rejected at pre-verify."""
        device = IoTDevice("victim", server.public_key,
                          firmwares[1], 1, verbose=False)

        # Build v2→v3 update
        m23, d23 = server.prepare_update(2, 3)

        # Send to device still on v1
        result = device.stage1_pre_verify(m23.serialize(), len(d23))

        assert not result.passed, "Version mismatch should be rejected at Stage 1"
        assert device.stats['updates_rejected_stage1'] == 1
        assert device.stats['bytes_saved'] == len(d23)  # Delta NOT downloaded

    def test_wrong_version_number_rejected(self, firmwares):
        """Manifest with incorrect version_base is rejected."""
        priv, pub = generate_keypair()

        delta = create_delta(firmwares[1], firmwares[2])

        # Build manifest with correct hashes but wrong version_base (3 instead of 1)
        m = build_manifest(
            firmwares[1], delta, firmwares[2],
            version_base=3,  # WRONG — device is on v1
            version_target=4,
            prev_manifest_hash=GENESIS_HASH,
            private_key=priv,
        )

        device = IoTDevice("victim", pub, firmwares[1], 1, verbose=False)
        result = device.stage1_pre_verify(m.serialize())
        assert not result.passed

    def test_correct_version_accepted(self, firmwares, server):
        """Correct version binding passes Stage 1."""
        device = IoTDevice("device", server.public_key,
                          firmwares[1], 1, verbose=False)

        m, d = server.prepare_update(1, 2)
        result = device.stage1_pre_verify(m.serialize(), len(d))

        assert result.passed


# ============================================================================
#  ATTACK (b): REPLAY ATTACK
# ============================================================================

class TestReplayAttack:
    """
    Attack: After device has updated from v1→v2, replay the old v1→v2 manifest.

    The old manifest's H(prev_manifest) = genesis hash (0x00*32), but the
    device's chain head has moved to H(manifest_v1v2) after the first update.

    Expected: REJECT at Stage 1, Check 4 (H(prev_manifest) chain mismatch).
    """

    def test_replay_old_manifest_rejected(self, firmwares, server):
        """Replaying an old manifest after update is rejected via chain."""
        device = IoTDevice("victim", server.public_key,
                          firmwares[1], 1, verbose=False)

        # Legitimate update v1→v2
        m12, d12 = server.prepare_update(1, 2)
        success = device.perform_full_update(m12.serialize(), d12)
        assert success
        assert device.version == 2

        # Attacker replays the SAME v1→v2 manifest
        # Even if attacker also downgrades firmware, chain head has moved
        device.firmware = firmwares[1]  # Simulate downgrade
        device.version = 1

        result = device.stage1_pre_verify(m12.serialize(), len(d12))

        assert not result.passed, "Replay of old manifest should be rejected"
        assert not result.details.get('chain_valid', True), \
            "Rejection should be at chain link check"

    def test_replay_after_two_updates(self, firmwares, server):
        """Replay of v1→v2 after v1→v2→v3 is also rejected."""
        device = IoTDevice("victim", server.public_key,
                          firmwares[1], 1, verbose=False)

        # Two legitimate updates
        m12, d12 = server.prepare_update(1, 2)
        device.perform_full_update(m12.serialize(), d12)

        m23, d23 = server.prepare_update(2, 3)
        device.perform_full_update(m23.serialize(), d23)
        assert device.version == 3

        # Replay v1→v2 (very old)
        device.firmware = firmwares[1]
        device.version = 1
        result = device.stage1_pre_verify(m12.serialize())
        assert not result.passed

        # Replay v2→v3 (previous update)
        device.firmware = firmwares[2]
        device.version = 2
        result2 = device.stage1_pre_verify(m23.serialize())
        assert not result2.passed


# ============================================================================
#  ATTACK (c): TAMPERED DELTA PATCH
# ============================================================================

class TestTamperedDeltaAttack:
    """
    Attack: Valid manifest, but delta patch bytes are modified in transit.

    The manifest's H(delta) was computed over the original patch. Tampering
    changes the SHA-256 hash, which fails the check in Stage 2.

    Expected: Stage 1 PASSES (manifest is authentic), Stage 2 REJECTS.
    """

    def test_tampered_delta_rejected_at_stage2(self, firmwares, server):
        """Tampered delta is detected and rejected at Stage 2."""
        device = IoTDevice("victim", server.public_key,
                          firmwares[1], 1, verbose=False)

        m, d = server.prepare_update(1, 2)

        # Tamper with delta bytes
        d_tampered = bytearray(d)
        d_tampered[20] ^= 0xFF
        d_tampered[21] ^= 0xFF
        d_tampered = bytes(d_tampered)

        # Stage 1 should pass (manifest is untouched)
        r1 = device.stage1_pre_verify(m.serialize(), len(d_tampered))
        assert r1.passed, "Stage 1 should pass with valid manifest"

        # Stage 2 should reject (delta hash mismatch)
        r2 = device.stage2_patch_and_apply(d_tampered)
        assert not r2.passed, "Tampered delta should be rejected at Stage 2"

    def test_single_bit_flip_detected(self, firmwares, server):
        """Even a single bit flip in the delta is detected."""
        device = IoTDevice("victim", server.public_key,
                          firmwares[1], 1, verbose=False)

        m, d = server.prepare_update(1, 2)

        # Single bit flip
        d_flipped = bytearray(d)
        d_flipped[len(d) // 2] ^= 0x01  # Flip one bit
        d_flipped = bytes(d_flipped)

        r1 = device.stage1_pre_verify(m.serialize())
        assert r1.passed

        r2 = device.stage2_patch_and_apply(d_flipped)
        assert not r2.passed, "Single bit flip should be detected"

    def test_valid_delta_accepted(self, firmwares, server):
        """Untampered delta passes both Stage 2 and Stage 3."""
        device = IoTDevice("device", server.public_key,
                          firmwares[1], 1, verbose=False)

        m, d = server.prepare_update(1, 2)

        r1 = device.stage1_pre_verify(m.serialize())
        assert r1.passed

        r2 = device.stage2_patch_and_apply(d)
        assert r2.passed

        r3 = device.stage3_post_verify()
        assert r3.passed
        assert device.version == 2


# ============================================================================
#  ADDITIONAL SECURITY TESTS
# ============================================================================

class TestAdditionalSecurity:
    """Additional security edge cases."""

    def test_forged_manifest_rejected(self, firmwares):
        """Manifest with forged signature is rejected."""
        priv, pub = generate_keypair()
        delta = create_delta(firmwares[1], firmwares[2])

        m = build_manifest(firmwares[1], delta, firmwares[2], 1, 2, GENESIS_HASH, priv)

        # Forge: change version_target but keep old signature
        forged = bytearray(m.serialize())
        forged[100] ^= 0xFF  # Corrupt a byte in the payload
        forged = bytes(forged)

        device = IoTDevice("victim", pub, firmwares[1], 1, verbose=False)
        result = device.stage1_pre_verify(forged)
        assert not result.passed

    def test_wrong_server_key_rejected(self, firmwares):
        """Manifest signed by unknown server is rejected."""
        # Server A signs the manifest
        priv_a, pub_a = generate_keypair()
        delta = create_delta(firmwares[1], firmwares[2])
        m = build_manifest(firmwares[1], delta, firmwares[2], 1, 2, GENESIS_HASH, priv_a)

        # Device only trusts server B
        _, pub_b = generate_keypair()
        device = IoTDevice("victim", pub_b, firmwares[1], 1, verbose=False)
        result = device.stage1_pre_verify(m.serialize())
        assert not result.passed

    def test_bandwidth_saved_on_rejection(self, firmwares, server):
        """Bytes saved counter tracks bandwidth saved by pre-verify rejection."""
        device = IoTDevice("device", server.public_key,
                          firmwares[1], 1, verbose=False)

        # Send wrong update (v2→v3 to v1 device)
        m23, d23 = server.prepare_update(2, 3)
        device.stage1_pre_verify(m23.serialize(), delta_size_hint=len(d23))

        assert device.stats['bytes_saved'] == len(d23)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
