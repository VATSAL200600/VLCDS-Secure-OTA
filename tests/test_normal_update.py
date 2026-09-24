"""
test_normal_update.py — Tests for the happy-path VLCDS update flow.

Tests:
    - Single update v1 → v2
    - Chained update v1 → v2 → v3
    - Manifest serialization round-trip
    - Delta patch correctness
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from vlcds.crypto_utils import generate_keypair, sha256
from vlcds.manifest import build_manifest, Manifest
from vlcds.delta_engine import create_delta, apply_delta
from vlcds.chain import ManifestChain, GENESIS_HASH
from vlcds.server import OTAServer
from vlcds.device import IoTDevice


# ============================================================================
#  FIXTURES
# ============================================================================

def make_firmware(version, size=2048):
    """Create synthetic firmware for a given version."""
    header = f"FW_v{version}_".encode()
    body = bytes([(b + version * 37) % 256 for b in range(size)])
    footer = f"_END_v{version}".encode()
    return header + body + footer


@pytest.fixture
def firmwares():
    return {v: make_firmware(v) for v in range(1, 4)}


@pytest.fixture
def keypair():
    return generate_keypair()


@pytest.fixture
def server(firmwares):
    srv = OTAServer(verbose=False)
    for v, fw in firmwares.items():
        srv.add_firmware(v, fw)
    return srv


# ============================================================================
#  DELTA PATCH TESTS
# ============================================================================

class TestDeltaPatch:
    """Test delta patch creation and application."""

    def test_delta_same_size(self, firmwares):
        """Delta patch works when firmware sizes are equal."""
        fw1 = firmwares[1]
        fw2 = make_firmware(2, size=len(fw1) - len("FW_v1_") - len("_END_v1") + len("FW_v2_") + len("_END_v2"))
        # Use firmwares of different content but test apply
        delta = create_delta(firmwares[1], firmwares[2])
        result = apply_delta(firmwares[1], delta)
        assert result == firmwares[2]

    def test_delta_new_larger(self):
        """Delta patch works when new firmware is larger."""
        old = b"OLD_FW_" + bytes(100)
        new = b"NEW_FW_" + bytes(200) + b"_EXTRA_DATA"
        delta = create_delta(old, new)
        result = apply_delta(old, delta)
        assert result == new

    def test_delta_new_smaller(self):
        """Delta patch works when new firmware is smaller."""
        old = b"OLD_FW_" + bytes(200) + b"_LONG"
        new = b"NEW_FW_" + bytes(50)
        delta = create_delta(old, new)
        result = apply_delta(old, delta)
        assert result == new

    def test_delta_identical(self):
        """Delta of identical firmware should produce valid (minimal) patch."""
        fw = b"IDENTICAL_FW_" + bytes(100)
        delta = create_delta(fw, fw)
        result = apply_delta(fw, delta)
        assert result == fw

    def test_delta_compression(self, firmwares):
        """Delta should be smaller than full firmware when images share content."""
        # Use larger firmware with significant shared sections (realistic)
        fw_a = b"SHARED_HEADER_" + bytes(range(256)) * 20 + b"_V1_unique_tail"
        fw_b = b"SHARED_HEADER_" + bytes(range(256)) * 20 + b"_V2_unique_tail_extra"
        delta = create_delta(fw_a, fw_b)
        assert len(delta) < len(fw_b), (
            f"Delta ({len(delta)}B) should be smaller than full image ({len(fw_b)}B) "
            f"when firmware versions share significant content"
        )


# ============================================================================
#  MANIFEST TESTS
# ============================================================================

class TestManifest:
    """Test manifest construction, serialization, and verification."""

    def test_manifest_build_and_verify(self, firmwares, keypair):
        """Build a manifest and verify its signature."""
        priv, pub = keypair
        delta = create_delta(firmwares[1], firmwares[2])

        m = build_manifest(
            firmwares[1], delta, firmwares[2], 1, 2, GENESIS_HASH, priv
        )

        assert m.verify_signature(pub)
        assert m.version_base == 1
        assert m.version_target == 2

    def test_manifest_serialization_roundtrip(self, firmwares, keypair):
        """Serialize and deserialize should produce identical manifest."""
        priv, pub = keypair
        delta = create_delta(firmwares[1], firmwares[2])
        m = build_manifest(firmwares[1], delta, firmwares[2], 1, 2, GENESIS_HASH, priv)

        serialized = m.serialize()
        assert len(serialized) == 200  # Exact wire format size

        m2 = Manifest.deserialize(serialized)
        assert m2.h_base_fw == m.h_base_fw
        assert m2.h_delta == m.h_delta
        assert m2.h_target == m.h_target
        assert m2.version_base == m.version_base
        assert m2.version_target == m.version_target
        assert m2.h_prev_manifest == m.h_prev_manifest
        assert m2.signature == m.signature

    def test_manifest_wrong_key_rejects(self, firmwares, keypair):
        """Manifest signed with one key should fail verification with another."""
        priv, pub = keypair
        delta = create_delta(firmwares[1], firmwares[2])
        m = build_manifest(firmwares[1], delta, firmwares[2], 1, 2, GENESIS_HASH, priv)

        # Generate a different key pair
        _, wrong_pub = generate_keypair()
        assert not m.verify_signature(wrong_pub)


# ============================================================================
#  CHAIN TESTS
# ============================================================================

class TestChain:
    """Test manifest hash-chain tracker."""

    def test_genesis_hash(self):
        """Chain starts with genesis hash (32 zero bytes)."""
        chain = ManifestChain()
        assert chain.head == GENESIS_HASH
        assert chain.length == 1

    def test_chain_growth(self):
        """Chain grows with each recorded manifest."""
        chain = ManifestChain()
        chain.record(b"manifest_1" + bytes(190))
        assert chain.length == 2
        chain.record(b"manifest_2" + bytes(190))
        assert chain.length == 3

    def test_chain_link_valid(self):
        """Valid chain link passes verification."""
        chain = ManifestChain()
        assert chain.verify_link(GENESIS_HASH)

    def test_chain_link_invalid(self):
        """Invalid chain link (replay) is rejected."""
        chain = ManifestChain()
        chain.record(b"manifest_1" + bytes(190))
        # Old genesis hash should no longer be valid
        assert not chain.verify_link(GENESIS_HASH)


# ============================================================================
#  FULL UPDATE FLOW TESTS
# ============================================================================

class TestFullUpdateFlow:
    """Test the complete 3-stage VLCDS update protocol."""

    def test_single_update_v1_to_v2(self, firmwares, server):
        """Full update from v1 to v2 should succeed."""
        device = IoTDevice("test-device", server.public_key,
                          firmwares[1], 1, verbose=False)

        manifest, delta = server.prepare_update(1, 2)
        success = device.perform_full_update(manifest.serialize(), delta)

        assert success
        assert device.version == 2
        assert device.firmware == firmwares[2]

    def test_chained_update_v1_v2_v3(self, firmwares, server):
        """Chained update v1→v2→v3 should succeed."""
        device = IoTDevice("test-device", server.public_key,
                          firmwares[1], 1, verbose=False)

        # Update v1 → v2
        m1, d1 = server.prepare_update(1, 2)
        assert device.perform_full_update(m1.serialize(), d1)
        assert device.version == 2

        # Update v2 → v3
        m2, d2 = server.prepare_update(2, 3)
        assert device.perform_full_update(m2.serialize(), d2)
        assert device.version == 3
        assert device.firmware == firmwares[3]

    def test_device_stats_tracking(self, firmwares, server):
        """Device should track update statistics."""
        device = IoTDevice("test-device", server.public_key,
                          firmwares[1], 1, verbose=False)

        m, d = server.prepare_update(1, 2)
        device.perform_full_update(m.serialize(), d)

        assert device.stats['updates_accepted'] == 1
        assert device.stats['updates_rejected_stage1'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
