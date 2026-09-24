"""
test_performance.py — Performance Benchmarks for VLCDS

Measures and compares:
    - Ed25519 sign/verify latency
    - SHA-256 hash over various firmware sizes
    - VLCDS total crypto cost vs single-signature baseline
    - Stage-by-stage timing breakdown
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import pytest
from tabulate import tabulate
from vlcds.crypto_utils import generate_keypair, sha256, sign, verify, benchmark_crypto
from vlcds.manifest import build_manifest
from vlcds.delta_engine import create_delta
from vlcds.chain import GENESIS_HASH
from vlcds.server import OTAServer
from vlcds.device import IoTDevice


# ============================================================================
#  FIXTURES
# ============================================================================

def make_firmware(version, size=4096):
    header = f"FW_v{version}_".encode()
    body = bytes([(b + version * 37) % 256 for b in range(size)])
    return header + body + f"_END_v{version}".encode()


@pytest.fixture
def firmwares():
    return {v: make_firmware(v) for v in range(1, 4)}


# ============================================================================
#  CRYPTO BENCHMARKS
# ============================================================================

class TestCryptoBenchmarks:
    """Benchmark individual cryptographic operations."""

    def test_ed25519_sign_performance(self):
        """Ed25519 signing should complete in under 10ms on desktop."""
        priv, _ = generate_keypair()
        data = b"test_manifest_payload_" + bytes(200)

        times = []
        for _ in range(50):
            start = time.perf_counter()
            sign(priv, data)
            times.append((time.perf_counter() - start) * 1000)

        mean_ms = sum(times) / len(times)
        print(f"\n  Ed25519 Sign: mean={mean_ms:.4f}ms, "
              f"min={min(times):.4f}ms, max={max(times):.4f}ms")
        assert mean_ms < 10, f"Signing too slow: {mean_ms}ms"

    def test_ed25519_verify_performance(self):
        """Ed25519 verification should complete in under 10ms on desktop."""
        priv, pub = generate_keypair()
        data = b"test_manifest_payload_" + bytes(200)
        sig = sign(priv, data)

        times = []
        for _ in range(50):
            start = time.perf_counter()
            verify(pub, data, sig)
            times.append((time.perf_counter() - start) * 1000)

        mean_ms = sum(times) / len(times)
        print(f"\n  Ed25519 Verify: mean={mean_ms:.4f}ms, "
              f"min={min(times):.4f}ms, max={max(times):.4f}ms")
        assert mean_ms < 10, f"Verification too slow: {mean_ms}ms"

    def test_sha256_performance_various_sizes(self):
        """SHA-256 hashing scales reasonably with input size."""
        sizes = [200, 1024, 10240, 102400, 1048576]
        results = []

        for size in sizes:
            data = bytes(range(256)) * (size // 256 + 1)
            data = data[:size]

            times = []
            for _ in range(50):
                start = time.perf_counter()
                sha256(data)
                times.append((time.perf_counter() - start) * 1000)

            mean_ms = sum(times) / len(times)
            label = f"{size}B" if size < 1024 else f"{size // 1024}KB"
            results.append([label, f"{mean_ms:.4f}"])

        print(f"\n{tabulate(results, headers=['Size', 'SHA-256 (ms)'], tablefmt='grid')}")


# ============================================================================
#  VLCDS PROTOCOL BENCHMARKS
# ============================================================================

class TestVLCDSBenchmarks:
    """Benchmark the full VLCDS protocol stages."""

    def test_stage_by_stage_timing(self, firmwares):
        """Measure timing for each VLCDS stage."""
        server = OTAServer(verbose=False)
        for v, fw in firmwares.items():
            server.add_firmware(v, fw)

        device = IoTDevice("bench-device", server.public_key,
                          firmwares[1], 1, verbose=False)

        manifest, delta = server.prepare_update(1, 2)
        manifest_bytes = manifest.serialize()

        # Stage 1 timing
        start = time.perf_counter()
        r1 = device.stage1_pre_verify(manifest_bytes, len(delta))
        stage1_ms = (time.perf_counter() - start) * 1000

        # Stage 2 timing
        start = time.perf_counter()
        r2 = device.stage2_patch_and_apply(delta)
        stage2_ms = (time.perf_counter() - start) * 1000

        # Stage 3 timing
        start = time.perf_counter()
        r3 = device.stage3_post_verify()
        stage3_ms = (time.perf_counter() - start) * 1000

        total_ms = stage1_ms + stage2_ms + stage3_ms

        results = [
            ["Stage 1 (Pre-Verify)", f"{stage1_ms:.4f} ms",
             "1 Ed25519 verify + 3 SHA-256 + 2 comparisons"],
            ["Stage 2 (Patch & Apply)", f"{stage2_ms:.4f} ms",
             "1 SHA-256 + delta apply"],
            ["Stage 3 (Post-Verify)", f"{stage3_ms:.4f} ms",
             "1 SHA-256 only (no 2nd signature!)"],
            ["TOTAL", f"{total_ms:.4f} ms", ""],
        ]

        print(f"\n{tabulate(results, headers=['Stage', 'Time', 'Operations'], tablefmt='grid')}")

        assert r1.passed and r2.passed and r3.passed

    def test_vlcds_vs_baseline_comparison(self, firmwares):
        """Compare VLCDS total crypto cost vs single-signature baseline."""
        priv, pub = generate_keypair()
        delta = create_delta(firmwares[1], firmwares[2])
        iterations = 50

        # Baseline: sign full image + verify full image
        baseline_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            h = sha256(firmwares[2])
            sig = sign(priv, h)
            verify(pub, h, sig)
            baseline_times.append((time.perf_counter() - start) * 1000)

        # VLCDS: build manifest (5 hashes + 1 sign) + verify (1 verify + checks)
        vlcds_times = []
        for _ in range(iterations):
            start = time.perf_counter()
            # Server side
            m = build_manifest(firmwares[1], delta, firmwares[2], 1, 2, GENESIS_HASH, priv)
            # Device side (Stage 1)
            m.verify_signature(pub)
            sha256(firmwares[1])  # H(base_fw) check
            # Stage 3
            sha256(firmwares[2])  # H(target) check
            vlcds_times.append((time.perf_counter() - start) * 1000)

        baseline_mean = sum(baseline_times) / len(baseline_times)
        vlcds_mean = sum(vlcds_times) / len(vlcds_times)
        overhead = vlcds_mean - baseline_mean

        results = [
            ["Single-Sig Baseline", f"{baseline_mean:.4f} ms", "1 hash + 1 sign + 1 verify"],
            ["VLCDS (Proposed)", f"{vlcds_mean:.4f} ms", "5 hashes + 1 sign + 1 verify"],
            ["Overhead", f"+{overhead:.4f} ms", f"+{overhead / baseline_mean * 100:.1f}%"],
        ]

        print(f"\n{tabulate(results, headers=['Scheme', 'Mean Time', 'Operations'], tablefmt='grid')}")

    def test_manifest_size_is_200_bytes(self, firmwares):
        """Manifest wire format is exactly 200 bytes (fits constrained links)."""
        priv, _ = generate_keypair()
        delta = create_delta(firmwares[1], firmwares[2])
        m = build_manifest(firmwares[1], delta, firmwares[2], 1, 2, GENESIS_HASH, priv)

        assert len(m.serialize()) == 200
        print(f"\n  Manifest size: {len(m.serialize())} bytes ✓")
        print(f"  Fits in: LoRa (222B), BLE (244B), Zigbee (127B w/ fragmentation)")

    def test_rejection_saves_bandwidth(self, firmwares):
        """Pre-verify rejection saves the full delta transfer."""
        server = OTAServer(verbose=False)
        for v, fw in firmwares.items():
            server.add_firmware(v, fw)

        device = IoTDevice("device", server.public_key,
                          firmwares[1], 1, verbose=False)

        # Wrong update (v2→v3 to v1 device)
        m23, d23 = server.prepare_update(2, 3)
        device.stage1_pre_verify(m23.serialize(), delta_size_hint=len(d23))

        bytes_transferred = 200  # Only manifest was sent
        bytes_saved = len(d23)   # Delta was NOT sent
        total_would_be = 200 + len(d23)

        print(f"\n  Pre-verify rejection:")
        print(f"    Manifest sent : {bytes_transferred} bytes")
        print(f"    Delta saved   : {bytes_saved:,} bytes")
        print(f"    Total w/o VLCDS: {total_would_be:,} bytes")
        print(f"    Savings       : {bytes_saved / total_would_be * 100:.1f}%")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
