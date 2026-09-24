"""
ed25519_mp.py — Pure-Python Ed25519 Verification for MicroPython

A minimal Ed25519 signature VERIFICATION implementation that runs
on MicroPython (ESP32-S2). Only verification is needed on the device;
signing happens on the server (PC).

Based on the Ed25519 reference implementation (RFC 8032).
Optimized for readability, not speed — but verification is still fast
enough for the VLCDS pre-verify step (~200 bytes to verify).

NOTE: This is a well-known reference implementation of Ed25519.
The cryptographic security comes from the algorithm itself, not this code.
"""

import hashlib


# ============================================================================
#  Ed25519 Constants
# ============================================================================

# Prime field: p = 2^255 - 19
P = 2**255 - 19

# Group order
L = 2**252 + 27742317777372353535851937790883648493

# d parameter of the Edwards curve: -121665/121666 mod p
D = -121665 * pow(121666, P - 2, P) % P

# Square root of -1 mod p
I = pow(2, (P - 1) // 4, P)


# ============================================================================
#  Modular Arithmetic
# ============================================================================

def _inv(x):
    """Modular inverse using Fermat's little theorem: x^(p-2) mod p."""
    return pow(x, P - 2, P)


def _recover_x(y, sign):
    """Recover x coordinate from y coordinate and sign bit."""
    if y >= P:
        return None

    x2 = (y * y - 1) * _inv(D * y * y + 1)
    if x2 == 0:
        if sign:
            return None
        return 0

    # Modular square root
    x = pow(x2, (P + 3) // 8, P)
    if (x * x - x2) % P != 0:
        x = x * I % P
    if (x * x - x2) % P != 0:
        return None

    if x & 1 != sign:
        x = P - x

    return x


# ============================================================================
#  Edwards Curve Point Operations
# ============================================================================

# Base point B
By = 4 * _inv(5) % P
Bx = _recover_x(By, 0)
B = (Bx, By, 1, Bx * By % P)  # Extended coordinates (x, y, z, t)


def _edwards_add(p_point, q_point):
    """Add two points on the Edwards curve (extended coordinates)."""
    x1, y1, z1, t1 = p_point
    x2, y2, z2, t2 = q_point

    a = (y1 - x1) * (y2 - x2) % P
    b = (y1 + x1) * (y2 + x2) % P
    c = t1 * 2 * D * t2 % P
    dd = z1 * 2 * z2 % P

    e = b - a
    f = dd - c
    g = dd + c
    h = b + a

    x3 = e * f
    y3 = g * h
    t3 = e * h
    z3 = f * g

    return (x3 % P, y3 % P, z3 % P, t3 % P)


def _scalarmult(point, scalar):
    """Scalar multiplication using double-and-add."""
    # Identity point
    result = (0, 1, 1, 0)
    temp = point

    while scalar > 0:
        if scalar & 1:
            result = _edwards_add(result, temp)
        temp = _edwards_add(temp, temp)
        scalar >>= 1

    return result


# ============================================================================
#  Encoding / Decoding Points
# ============================================================================

def _point_to_bytes(point):
    """Encode a point to 32 bytes."""
    x, y, z, _ = point
    zi = _inv(z)
    x = (x * zi) % P
    y = (y * zi) % P

    bs = y.to_bytes(32, 'little')
    result = bytearray(bs)
    if x & 1:
        result[31] |= 0x80
    return bytes(result)


def _bytes_to_point(data):
    """Decode 32 bytes to a curve point. Returns None if invalid."""
    if len(data) != 32:
        return None

    y = int.from_bytes(data, 'little')
    sign = y >> 255
    y &= (1 << 255) - 1

    x = _recover_x(y, sign)
    if x is None:
        return None

    point = (x, y, 1, x * y % P)

    # Verify point is on curve
    if not _is_on_curve(point):
        return None

    return point


def _is_on_curve(point):
    """Check if a point is on the Edwards curve."""
    x, y, z, t = point
    zi = _inv(z)
    x = x * zi % P
    y = y * zi % P

    return (-x * x + y * y - 1 - D * x * x * y * y) % P == 0


# ============================================================================
#  SHA-512 (used internally by Ed25519)
# ============================================================================

def _sha512(data):
    """SHA-512 hash using hashlib if available, or pure Python fallback."""
    try:
        return hashlib.sha512(data).digest()
    except (AttributeError, ValueError):
        import sha512_mp
        return sha512_mp.sha512(data)


# ============================================================================
#  Ed25519 SIGNATURE VERIFICATION
# ============================================================================

def verify(public_key_bytes, message, signature):
    """
    Verify an Ed25519 signature.

    Args:
        public_key_bytes: 32-byte public key
        message: The signed message (bytes)
        signature: 64-byte signature

    Returns:
        bool: True if the signature is valid
    """
    if len(public_key_bytes) != 32:
        return False
    if len(signature) != 64:
        return False

    # Decode public key point A
    A = _bytes_to_point(public_key_bytes)
    if A is None:
        return False

    # Extract R and S from signature
    R_bytes = signature[:32]
    S_bytes = signature[32:]

    R = _bytes_to_point(R_bytes)
    if R is None:
        return False

    S = int.from_bytes(S_bytes, 'little')
    if S >= L:
        return False

    # Compute h = SHA-512(R || A || message) mod L
    h_input = R_bytes + public_key_bytes + message
    h = int.from_bytes(_sha512(h_input), 'little') % L

    # Verify: [S]B == R + [h]A
    sB = _scalarmult(B, S)
    hA = _scalarmult(A, h)
    RhA = _edwards_add(R, hA)

    return _point_to_bytes(sB) == _point_to_bytes(RhA)


# ============================================================================
#  SELF-TEST (run on ESP32 or PC)
# ============================================================================

if __name__ == "__main__":
    print("Ed25519 Pure-Python Verification — Self-Test")

    # Test vector from RFC 8032 Section 7.1 (TEST 2)
    # This is a well-known test vector
    pub_key = bytes.fromhex(
        "3d4017c3e843895a92b70aa74d1b7ebc"
        "9c982ccf2ec4968cc0cd55f12af4660c"
    )
    msg = bytes([0x72])
    sig = bytes.fromhex(
        "92a009a9f0d4cab8720e820b5f642540"
        "a2b27b5416503f8fb3762223ebdb69da"
        "085ac1e43e159c7e94b2ba1f5c7e2edb"
        "1544e7de361a3e56e085bde5d93a350b"
    )

    result = verify(pub_key, msg, sig)
    print(f"  RFC 8032 test vector: {'PASS' if result else 'FAIL'}")

    # Test with wrong message
    result2 = verify(pub_key, bytes([0x73]), sig)
    print(f"  Wrong message reject: {'PASS' if not result2 else 'FAIL'}")

    print("  Self-test complete.")
