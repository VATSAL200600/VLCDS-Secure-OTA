"""
crypto_utils.py — Core Cryptographic Primitives for VLCDS

Provides Ed25519 digital signatures and SHA-256 hashing.
All functions support verbose mode for intermediate result output.

Cryptographic Grounding (from project report Section 4.3):
  - Ed25519: Twisted-Edwards curve signature scheme (RFC 8032)
    * 256-bit security level, 64-byte signatures, 32-byte keys
    * Deterministic signing (no random nonce needed)
  - SHA-256: NIST FIPS 180-4 hash function
    * 256-bit output, collision-resistant
"""

import hashlib
import time
from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError


# ============================================================================
#  KEY GENERATION
# ============================================================================

def generate_keypair(verbose=False, seed=None):
    """
    Generate an Ed25519 key pair for the OTA update server.

    Args:
        verbose (bool): Print keypair details.
        seed (bytes, optional): 32-byte seed for deterministic key generation.

    Returns:
        tuple: (SigningKey, VerifyKey) — private key for signing, public key for verification

    The server holds the SigningKey (private); the device stores only the VerifyKey (public).
    """
    if seed:
        private_key = SigningKey(seed)
    else:
        private_key = SigningKey.generate()
    public_key = private_key.verify_key

    if verbose:
        print("=" * 70)
        print("  ED25519 KEY PAIR GENERATION")
        print("=" * 70)
        print(f"  Private Key (hex): {private_key.encode().hex()}")
        print(f"  Public Key  (hex): {public_key.encode().hex()}")
        print(f"  Key Size:          32 bytes (256 bits) each")
        print("=" * 70)

    return private_key, public_key


# ============================================================================
#  SHA-256 HASHING
# ============================================================================

def sha256(data: bytes, verbose=False, label="") -> bytes:
    """
    Compute SHA-256 hash of input data.

    Args:
        data: Raw bytes to hash
        verbose: If True, print intermediate values
        label: Descriptive label for verbose output

    Returns:
        bytes: 32-byte SHA-256 digest
    """
    digest = hashlib.sha256(data).digest()

    if verbose:
        tag = f" [{label}]" if label else ""
        print(f"  SHA-256{tag}:")
        print(f"    Input size : {len(data)} bytes")
        print(f"    First 16B  : {data[:16].hex()}...")
        print(f"    Digest     : {digest.hex()}")

    return digest


def sha256_hex(data: bytes) -> str:
    """Return the SHA-256 hash as a hex string."""
    return hashlib.sha256(data).digest().hex()


# ============================================================================
#  ED25519 SIGNING
# ============================================================================

def sign(private_key: SigningKey, data: bytes, verbose=False) -> bytes:
    """
    Sign data with Ed25519 private key.

    Args:
        private_key: Ed25519 SigningKey
        data: Bytes to sign
        verbose: If True, print intermediate values

    Returns:
        bytes: 64-byte Ed25519 signature
    """
    start = time.perf_counter()
    signed_message = private_key.sign(data)
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Extract just the signature (first 64 bytes of signed message)
    signature = signed_message.signature

    if verbose:
        print(f"  ED25519 SIGN:")
        print(f"    Data size     : {len(data)} bytes")
        print(f"    Data (hex)    : {data.hex()}")
        print(f"    Signature     : {signature.hex()}")
        print(f"    Sig size      : {len(signature)} bytes")
        print(f"    Time          : {elapsed_ms:.3f} ms")

    return signature


# ============================================================================
#  ED25519 VERIFICATION
# ============================================================================

def verify(public_key: VerifyKey, data: bytes, signature: bytes, verbose=False) -> bool:
    """
    Verify an Ed25519 signature.

    Args:
        public_key: Ed25519 VerifyKey (stored on device)
        data: Original signed data
        signature: 64-byte signature to verify
        verbose: If True, print intermediate values

    Returns:
        bool: True if signature is valid, False otherwise
    """
    start = time.perf_counter()
    try:
        public_key.verify(data, signature)
        valid = True
    except BadSignatureError:
        valid = False
    elapsed_ms = (time.perf_counter() - start) * 1000

    if verbose:
        status = "✓ VALID" if valid else "✗ INVALID"
        print(f"  ED25519 VERIFY:")
        print(f"    Public Key    : {public_key.encode().hex()}")
        print(f"    Data size     : {len(data)} bytes")
        print(f"    Signature     : {signature[:16].hex()}...{signature[-16:].hex()}")
        print(f"    Result        : {status}")
        print(f"    Time          : {elapsed_ms:.3f} ms")

    return valid


# ============================================================================
#  PERFORMANCE BENCHMARKING
# ============================================================================

def benchmark_crypto(iterations=100, firmware_sizes=None):
    """
    Benchmark Ed25519 and SHA-256 performance.

    Returns:
        dict: Timing results for sign, verify, and hash operations
    """
    if firmware_sizes is None:
        firmware_sizes = [1024, 10240, 102400, 1048576]  # 1KB, 10KB, 100KB, 1MB

    results = {}

    # Benchmark Ed25519 sign/verify
    private_key, public_key = generate_keypair()
    test_data = b"benchmark_manifest_data_" + b"\x00" * 200

    # Sign benchmark
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        sig = sign(private_key, test_data)
        times.append((time.perf_counter() - start) * 1000)
    results['ed25519_sign_ms'] = {
        'mean': sum(times) / len(times),
        'min': min(times),
        'max': max(times),
    }

    # Verify benchmark
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        verify(public_key, test_data, sig)
        times.append((time.perf_counter() - start) * 1000)
    results['ed25519_verify_ms'] = {
        'mean': sum(times) / len(times),
        'min': min(times),
        'max': max(times),
    }

    # SHA-256 benchmark for different firmware sizes
    results['sha256_ms'] = {}
    for size in firmware_sizes:
        test_fw = bytes(range(256)) * (size // 256) + bytes(range(size % 256))
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            sha256(test_fw)
            times.append((time.perf_counter() - start) * 1000)
        label = f"{size // 1024}KB" if size >= 1024 else f"{size}B"
        results['sha256_ms'][label] = {
            'mean': sum(times) / len(times),
            'min': min(times),
            'max': max(times),
        }

    return results


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  VLCDS Cryptographic Utilities — Self-Test")
    print("=" * 70 + "\n")

    # 1. Key generation
    priv, pub = generate_keypair(verbose=True)

    # 2. Hash test
    print()
    test_data = b"ESP32 firmware version 1.0.0 binary content..."
    h = sha256(test_data, verbose=True, label="test firmware")

    # 3. Sign/verify test
    print()
    sig = sign(priv, test_data, verbose=True)
    print()
    result = verify(pub, test_data, sig, verbose=True)
    print(f"\n  Signature verification: {'PASSED' if result else 'FAILED'}")

    # 4. Tampered data test
    print()
    tampered = test_data + b"X"
    result2 = verify(pub, tampered, sig, verbose=True)
    print(f"  Tampered verification: {'PASSED (BAD!)' if result2 else 'CORRECTLY REJECTED'}")

    print("\n" + "=" * 70)
    print("  Self-test complete.")
    print("=" * 70)
