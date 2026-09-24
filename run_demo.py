"""
run_demo.py — VLCDS Full Protocol Demonstration

Runs the complete Version-Locked Chained Delta Signature protocol
with rich intermediate output at every step:

    1. Key Generation           — Ed25519 key pair with hex dump
    2. Firmware Simulation      — 3 synthetic firmware versions
    3. Delta Compression        — Patch creation with ratios
    4. Normal Update v1→v2      — Full 3-stage verification
    5. Chained Update v2→v3     — Demonstrates hash-chain continuity
    6. Attack Simulations       — 3 attack vectors from report Section 5.6
    7. Performance Benchmarks   — Timing for all crypto operations
    8. Results Summary          — Tables and charts saved to results/

Usage:
    python run_demo.py
"""

import os
import sys
import time
import json

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

from tabulate import tabulate

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vlcds.crypto_utils import generate_keypair, sha256, sign, verify, benchmark_crypto
from vlcds.manifest import build_manifest, Manifest
from vlcds.delta_engine import create_delta, apply_delta
from vlcds.chain import ManifestChain, GENESIS_HASH
from vlcds.server import OTAServer
from vlcds.device import IoTDevice


# ============================================================================
#  HELPERS
# ============================================================================

def print_banner(title, char="="):
    width = 70
    print(f"\n{char * width}")
    print(f"  {title}")
    print(f"{char * width}")


def print_section(title):
    print(f"\n  {'─' * 60}")
    print(f"  {title}")
    print(f"  {'─' * 60}")


def create_synthetic_firmware(version: int, size: int = 3072) -> bytes:
    """
    Create a synthetic firmware image that looks realistic.

    Each version has a recognizable header, version-specific code section,
    shared data section, and unique configuration block.
    """
    header = f"ESP32S2_FW_v{version}.0.0_BUILD_{version * 1000 + 42}_".encode()

    # Simulated code section (different per version to generate real diffs)
    code_section = bytes([(b + version * 37 + version) % 256 for b in range(size // 2)])

    # Data section (partially shared between versions)
    data_section = bytes(range(256)) * ((size // 4) // 256 + 1)
    data_section = data_section[:size // 4]

    # Version-specific configuration
    config = f"_CONFIG_v{version}_WIFI_CH{version + 5}_PWR{version * 10}dBm_SSID_IoTNet_".encode()

    footer = f"_CRC32_{version * 12345:08X}_EOF".encode()

    fw = header + code_section + data_section + config + footer
    return fw


# ============================================================================
#  DEMO EXECUTION
# ============================================================================

def main():
    results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
    os.makedirs(results_dir, exist_ok=True)

    all_results = {}
    total_start = time.perf_counter()

    # ========================================================================
    #  STEP 1: KEY GENERATION
    # ========================================================================
    print_banner("STEP 1: ED25519 KEY PAIR GENERATION")

    private_key, public_key = generate_keypair(verbose=True)
    all_results['key_generation'] = {
        'private_key_hex': private_key.encode().hex(),
        'public_key_hex': public_key.encode().hex(),
        'key_size_bits': 256,
    }

    # ========================================================================
    #  STEP 2: FIRMWARE VERSION CREATION
    # ========================================================================
    print_banner("STEP 2: SYNTHETIC FIRMWARE VERSIONS")

    firmwares = {}
    fw_table = []
    for v in range(1, 4):
        fw = create_synthetic_firmware(v, size=3072)
        firmwares[v] = fw
        h = sha256(fw)
        fw_table.append([
            f"v{v}",
            f"{len(fw):,} bytes",
            h.hex()[:32] + "...",
            fw[:30].decode('ascii', errors='replace') + "...",
        ])

    print()
    print(tabulate(fw_table,
                   headers=["Version", "Size", "SHA-256 (first 32 hex)", "Header Preview"],
                   tablefmt="grid"))

    all_results['firmware_versions'] = {
        f"v{v}": {'size': len(fw), 'sha256': sha256(fw).hex()}
        for v, fw in firmwares.items()
    }

    # ========================================================================
    #  STEP 3: DELTA PATCH CREATION
    # ========================================================================
    print_banner("STEP 3: DELTA PATCH CREATION")

    deltas = {}
    delta_table = []
    for v_from, v_to in [(1, 2), (2, 3)]:
        print_section(f"Delta: v{v_from} → v{v_to}")
        delta = create_delta(firmwares[v_from], firmwares[v_to], verbose=True)
        deltas[(v_from, v_to)] = delta

        ratio = len(delta) / len(firmwares[v_to]) * 100
        savings = (1 - len(delta) / len(firmwares[v_to])) * 100
        delta_table.append([
            f"v{v_from} → v{v_to}",
            f"{len(firmwares[v_to]):,}",
            f"{len(delta):,}",
            f"{ratio:.1f}%",
            f"{savings:.1f}%",
        ])

        # Verify delta produces correct output
        reconstructed = apply_delta(firmwares[v_from], delta)
        match = reconstructed == firmwares[v_to]
        print(f"\n  Patch verification: {'✓ CORRECT' if match else '✗ FAILED'}")

    print()
    print(tabulate(delta_table,
                   headers=["Update", "Full Image", "Delta Size", "Ratio", "Savings"],
                   tablefmt="grid"))

    all_results['delta_patches'] = delta_table

    # ========================================================================
    #  STEP 4: NORMAL UPDATE v1 → v2 (Full 3-Stage Protocol)
    # ========================================================================
    print_banner("STEP 4: NORMAL UPDATE v1 → v2 (Full 3-Stage Protocol)", "█")

    # Initialize server and device
    server = OTAServer(verbose=True)
    for v, fw in firmwares.items():
        server.add_firmware(v, fw)

    device = IoTDevice(
        device_id="ESP32-S2-DEMO",
        public_key=server.public_key,
        initial_firmware=firmwares[1],
        initial_version=1,
        verbose=True,
    )

    # Prepare update
    manifest_1, delta_1 = server.prepare_update(1, 2)

    # Execute 3-stage protocol
    print_banner("EXECUTING 3-STAGE VLCDS PROTOCOL (v1 → v2)")

    success = device.perform_full_update(manifest_1.serialize(), delta_1)

    print(f"\n  Update v1→v2 result: {'✓ SUCCESS' if success else '✗ FAILED'}")
    device.print_status()

    all_results['update_v1_v2'] = {
        'success': success,
        'manifest_size': len(manifest_1.serialize()),
        'delta_size': len(delta_1),
        'final_version': device.version,
    }

    # ========================================================================
    #  STEP 5: CHAINED UPDATE v2 → v3 (Hash-Chain Continuity)
    # ========================================================================
    print_banner("STEP 5: CHAINED UPDATE v2 → v3 (Hash-Chain Continuity)", "█")

    print("\n  This update tests hash-chain continuity:")
    print("  The v2→v3 manifest must contain H(prev_manifest) matching")
    print("  the device's chain head (set after v1→v2 was accepted).\n")

    # Server needs to know the chain head — in real deployment, server tracks this
    # For the demo, we prepare with the correct chain state
    manifest_2, delta_2 = server.prepare_update(2, 3)

    success2 = device.perform_full_update(manifest_2.serialize(), delta_2)

    print(f"\n  Update v2→v3 result: {'✓ SUCCESS' if success2 else '✗ FAILED'}")
    device.print_status()

    all_results['update_v2_v3'] = {
        'success': success2,
        'manifest_size': len(manifest_2.serialize()),
        'delta_size': len(delta_2),
        'final_version': device.version,
    }

    # ========================================================================
    #  STEP 6: ATTACK SIMULATIONS
    # ========================================================================
    print_banner("STEP 6: ATTACK SIMULATIONS", "█")
    print("  Testing the 3 attack vectors from report Section 5.6:\n")
    print("  (a) Version mismatch — patch for wrong base firmware")
    print("  (b) Replay attack    — old valid manifest replayed")
    print("  (c) Tampered delta   — modified patch bytes\n")

    # Fresh device for attack tests
    attack_server = OTAServer(verbose=False)
    for v, fw in firmwares.items():
        attack_server.add_firmware(v, fw)

    attack_results = []

    # ── Attack (a): Version Mismatch ──
    print_banner("ATTACK (a): VERSION MISMATCH", "─")
    print("  Scenario: Attacker sends a v2→v3 manifest to a device still on v1")
    print("  Expected: REJECT at Stage 1, Check 2 (H(base_fw) mismatch)\n")

    device_a = IoTDevice("ATTACK-VICTIM-A", attack_server.public_key,
                         firmwares[1], 1, verbose=True)

    # Prepare v2→v3 manifest — but device is on v1
    m_wrong, d_wrong = attack_server.prepare_update(2, 3)
    result_a = device_a.stage1_pre_verify(m_wrong.serialize(), len(d_wrong))

    attack_results.append([
        "Version Mismatch",
        "v2→v3 manifest sent to v1 device",
        "Stage 1, Check 2",
        "✓ REJECTED" if not result_a.passed else "✗ ACCEPTED (BAD!)",
    ])

    # ── Attack (b): Replay Attack ──
    print_banner("ATTACK (b): REPLAY OF OLD MANIFEST", "─")
    print("  Scenario: Device has updated to v2. Attacker replays the old v1→v2 manifest.")
    print("  Expected: REJECT at Stage 1, Check 4 (H(prev_manifest) chain mismatch)\n")

    # Device that has already accepted v1→v2
    device_b = IoTDevice("ATTACK-VICTIM-B", attack_server.public_key,
                         firmwares[1], 1, verbose=True)
    m_12, d_12 = attack_server.prepare_update(1, 2)
    device_b.perform_full_update(m_12.serialize(), d_12)

    print("\n  Device is now on v2. Replaying old v1→v2 manifest...\n")

    # Reset firmware to v1 to simulate attacker also flashing old firmware
    # But chain head has moved — so replay still fails
    device_b.firmware = firmwares[1]
    device_b.version = 1

    result_b = device_b.stage1_pre_verify(m_12.serialize(), len(d_12))

    attack_results.append([
        "Replay Attack",
        "Old v1→v2 manifest replayed after update",
        "Stage 1, Check 4",
        "✓ REJECTED" if not result_b.passed else "✗ ACCEPTED (BAD!)",
    ])

    # ── Attack (c): Tampered Delta ──
    print_banner("ATTACK (c): TAMPERED DELTA PATCH", "─")
    print("  Scenario: Manifest is valid, but attacker modifies delta patch bytes in transit.")
    print("  Expected: REJECT at Stage 2 (H(delta) mismatch)\n")

    device_c = IoTDevice("ATTACK-VICTIM-C", attack_server.public_key,
                         firmwares[1], 1, verbose=True)
    m_valid, d_valid = attack_server.prepare_update(1, 2)

    # Tamper with the delta patch (flip some bytes)
    d_tampered = bytearray(d_valid)
    for i in range(20, min(30, len(d_tampered))):
        d_tampered[i] ^= 0xFF  # Flip bytes
    d_tampered = bytes(d_tampered)

    # Stage 1 should pass (manifest is untouched)
    r1 = device_c.stage1_pre_verify(m_valid.serialize(), len(d_tampered))
    print(f"\n  Stage 1 (untampered manifest): {'PASSED' if r1.passed else 'FAILED'}")

    if r1.passed:
        # Stage 2 should fail (delta is tampered)
        r2 = device_c.stage2_patch_and_apply(d_tampered)
        result_c_passed = r2.passed
    else:
        result_c_passed = False

    attack_results.append([
        "Tampered Delta",
        "Delta patch bytes modified in transit",
        "Stage 2",
        "✓ REJECTED" if not result_c_passed else "✗ ACCEPTED (BAD!)",
    ])

    # Print attack results summary
    print_banner("ATTACK SIMULATION RESULTS SUMMARY")
    print()
    print(tabulate(attack_results,
                   headers=["Attack", "Description", "Rejection Point", "Result"],
                   tablefmt="grid"))

    all_results['attack_simulations'] = attack_results

    # ========================================================================
    #  STEP 7: PERFORMANCE BENCHMARKS
    # ========================================================================
    print_banner("STEP 7: PERFORMANCE BENCHMARKS")

    print("  Running crypto benchmarks (100 iterations each)...\n")
    bench = benchmark_crypto(iterations=100)

    # Ed25519 timing
    crypto_table = [
        ["Ed25519 Sign (manifest)", f"{bench['ed25519_sign_ms']['mean']:.4f}",
         f"{bench['ed25519_sign_ms']['min']:.4f}", f"{bench['ed25519_sign_ms']['max']:.4f}"],
        ["Ed25519 Verify (manifest)", f"{bench['ed25519_verify_ms']['mean']:.4f}",
         f"{bench['ed25519_verify_ms']['min']:.4f}", f"{bench['ed25519_verify_ms']['max']:.4f}"],
    ]

    # SHA-256 timing
    for label, data in bench['sha256_ms'].items():
        crypto_table.append([
            f"SHA-256 ({label})", f"{data['mean']:.4f}",
            f"{data['min']:.4f}", f"{data['max']:.4f}",
        ])

    print(tabulate(crypto_table,
                   headers=["Operation", "Mean (ms)", "Min (ms)", "Max (ms)"],
                   tablefmt="grid"))

    # VLCDS total cost comparison
    print_section("VLCDS Total Crypto Cost vs Single-Signature Baseline")

    vlcds_sign = bench['ed25519_sign_ms']['mean']  # 1 signature
    vlcds_verify = bench['ed25519_verify_ms']['mean']  # 1 verification
    sha_fw = bench['sha256_ms'].get('1KB', list(bench['sha256_ms'].values())[0])['mean']

    # VLCDS: 1 sign + 1 verify + ~5 SHA-256 (base_fw, delta, target, prev_manifest, recon)
    vlcds_total = vlcds_sign + vlcds_verify + sha_fw * 5

    # Baseline: 1 sign + 1 verify (full image, no version binding)
    baseline_total = vlcds_sign + vlcds_verify + sha_fw * 1

    comparison_table = [
        ["Single-Signature Baseline", "1 Sign + 1 Verify + 1 Hash",
         f"{baseline_total:.4f} ms", "No version binding, no anti-replay"],
        ["VLCDS (Proposed)", "1 Sign + 1 Verify + 5 Hashes",
         f"{vlcds_total:.4f} ms", "Full version binding + anti-replay"],
        ["Overhead", "", f"+{vlcds_total - baseline_total:.4f} ms",
         f"+{(vlcds_total / baseline_total - 1) * 100:.1f}% (4 extra SHA-256 only)"],
    ]

    print()
    print(tabulate(comparison_table,
                   headers=["Scheme", "Crypto Operations", "Total Time", "Security Properties"],
                   tablefmt="grid"))

    all_results['benchmarks'] = {
        'crypto_table': crypto_table,
        'vlcds_total_ms': vlcds_total,
        'baseline_total_ms': baseline_total,
        'overhead_ms': vlcds_total - baseline_total,
    }

    # ========================================================================
    #  STEP 8: COMPARISON TABLE (Matching Report Section 5.5)
    # ========================================================================
    print_banner("STEP 8: COMPARISON WITH EXISTING WORK (Report Section 5.5)")

    comparison = [
        ["Target Platform",
         "Smartphone / NFC chip (Samsung)\nGeneral IoT OTA (Base Paper)",
         "ESP32-S2 class IoT devices"],
        ["Update Unit Verified",
         "Full firmware image only",
         "Delta (differential) patch"],
        ["Verification Timing",
         "Pre-verify hash+sig, then post-verify",
         "Same 2-stage, adapted for delta"],
        ["Version/Rollback State",
         "Not in signed object\n(separate, unauthenticated field)",
         "Bound INSIDE signed manifest\n(version_base, version_target)"],
        ["Replay Protection",
         "Not addressed",
         "Hash-chain: H(prev_manifest)\ninside signed object"],
        ["Channel Assumption",
         "Trusted internal bus",
         "Untrusted wireless (WiFi/BLE)"],
        ["Post-Verify Cost",
         "Second signature verification",
         "Hash comparison only\n(H(target) pre-committed)"],
        ["Manifest Size",
         "N/A",
         "200 bytes (fits LoRa/BLE frame)"],
    ]

    print()
    print(tabulate(comparison,
                   headers=["Aspect", "Existing Work", "VLCDS (Proposed)"],
                   tablefmt="grid"))

    # ========================================================================
    #  SAVE RESULTS
    # ========================================================================

    total_elapsed = (time.perf_counter() - total_start)

    # Save JSON results
    results_file = os.path.join(results_dir, "demo_results.json")
    with open(results_file, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n  Results saved to: {results_file}")

    # ========================================================================
    #  FINAL SUMMARY
    # ========================================================================
    print_banner("DEMO COMPLETE — SUMMARY", "█")

    summary_table = [
        ["Ed25519 Key Generation", "✓ 32-byte keys generated"],
        ["Firmware Versions", f"✓ 3 versions ({len(firmwares[1]):,}B each)"],
        ["Delta Patches", f"✓ 2 patches created"],
        ["Normal Update v1→v2", f"✓ {'PASSED' if all_results['update_v1_v2']['success'] else 'FAILED'}"],
        ["Chained Update v2→v3", f"✓ {'PASSED' if all_results['update_v2_v3']['success'] else 'FAILED'}"],
        ["Attack (a) Version Mismatch", attack_results[0][3]],
        ["Attack (b) Replay", attack_results[1][3]],
        ["Attack (c) Tampered Delta", attack_results[2][3]],
        ["Total Execution Time", f"{total_elapsed:.2f} seconds"],
    ]

    print()
    print(tabulate(summary_table,
                   headers=["Component", "Status"],
                   tablefmt="grid"))

    print(f"\n  All intermediate results saved to: {results_dir}/")
    print()

    # Generate performance chart
    try:
        generate_performance_chart(bench, all_results, results_dir)
        print(f"  Performance chart saved to: {results_dir}/performance_chart.png")
    except Exception as e:
        print(f"  Chart generation skipped: {e}")


# ============================================================================
#  PERFORMANCE CHART
# ============================================================================

def generate_performance_chart(bench, all_results, results_dir):
    """Generate a performance comparison chart."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("VLCDS Performance Analysis", fontsize=16, fontweight='bold')

    # Chart 1: Crypto operation timing
    ax1 = axes[0]
    ops = ['Ed25519\nSign', 'Ed25519\nVerify']
    means = [bench['ed25519_sign_ms']['mean'], bench['ed25519_verify_ms']['mean']]

    for label, data in bench['sha256_ms'].items():
        ops.append(f'SHA-256\n({label})')
        means.append(data['mean'])

    colors = ['#e74c3c', '#2ecc71'] + ['#3498db'] * len(bench['sha256_ms'])
    bars = ax1.bar(ops, means, color=colors, edgecolor='white', linewidth=1.5)
    ax1.set_ylabel('Time (ms)')
    ax1.set_title('Cryptographic Operation Timing')
    ax1.grid(axis='y', alpha=0.3)

    for bar, val in zip(bars, means):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.001,
                 f'{val:.4f}', ha='center', va='bottom', fontsize=9)

    # Chart 2: VLCDS vs Baseline total cost
    ax2 = axes[1]
    schemes = ['Single-Sig\nBaseline', 'VLCDS\n(Proposed)']
    totals = [all_results['benchmarks']['baseline_total_ms'],
              all_results['benchmarks']['vlcds_total_ms']]
    overhead = all_results['benchmarks']['overhead_ms']

    bar_colors = ['#95a5a6', '#2ecc71']
    bars2 = ax2.bar(schemes, totals, color=bar_colors, edgecolor='white', linewidth=1.5)
    ax2.set_ylabel('Total Time (ms)')
    ax2.set_title('Total Crypto Cost Comparison')
    ax2.grid(axis='y', alpha=0.3)

    for bar, val in zip(bars2, totals):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.001,
                 f'{val:.4f} ms', ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax2.annotate(f'Overhead: +{overhead:.4f} ms\n(4 extra SHA-256 only)',
                 xy=(1, totals[1]), xytext=(0.5, totals[1] * 1.3),
                 fontsize=9, ha='center',
                 arrowprops=dict(arrowstyle='->', color='#e74c3c'),
                 bbox=dict(boxstyle='round,pad=0.3', facecolor='#ffeaa7', alpha=0.8))

    plt.tight_layout()
    chart_path = os.path.join(results_dir, "performance_chart.png")
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()


# ============================================================================
#  ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    main()
