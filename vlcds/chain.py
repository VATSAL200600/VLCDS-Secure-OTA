"""
chain.py — Manifest Hash-Chain Tracker (Anti-Replay)

Implements the hash-chain mechanism from Section 4.2 of the project report:
    Each manifest includes H(prev_manifest) — the SHA-256 hash of the
    previously accepted manifest — creating a cryptographic chain that
    prevents replay of old, validly-signed updates.

Chain Structure:
    Genesis (v0)     → Manifest_1 (v1→v2)  → Manifest_2 (v2→v3)  → ...
    H(prev) = 0x00*32   H(prev) = H(M_0)      H(prev) = H(M_1)

An attacker replaying Manifest_1 after Manifest_2 has been accepted
will fail because the device's stored chain head is now H(M_2),
not the H(M_0) that Manifest_1 expects.
"""

from vlcds.crypto_utils import sha256


# ============================================================================
#  GENESIS CONSTANT
# ============================================================================

# The first update in the chain uses 32 zero bytes as the "previous" hash.
# This is a well-known constant, not a secret.
GENESIS_HASH = b"\x00" * 32


# ============================================================================
#  CHAIN TRACKER
# ============================================================================

class ManifestChain:
    """
    Tracks the hash-chain of accepted manifests.

    Stored on the device to detect replay attacks:
    - After each successful update, the device stores the hash of
      the accepted manifest.
    - The next update's manifest must contain this hash in its
      H(prev_manifest) field.
    - An old manifest cannot satisfy this check because it was
      created with an older chain head.
    """

    def __init__(self):
        """Initialize chain with genesis hash."""
        self._chain = [GENESIS_HASH]  # History of all manifest hashes
        self._current = GENESIS_HASH   # Latest accepted manifest hash

    @property
    def head(self) -> bytes:
        """Get the current chain head (hash of last accepted manifest)."""
        return self._current

    @property
    def length(self) -> int:
        """Number of manifests in the chain (including genesis)."""
        return len(self._chain)

    def record(self, manifest_bytes: bytes, verbose=False) -> bytes:
        """
        Record a newly accepted manifest in the chain.

        Called after a successful Stage 3 (Post-Verify) completes.

        Args:
            manifest_bytes: Serialized manifest bytes (200 bytes)
            verbose: Print intermediate values

        Returns:
            bytes: Hash of the recorded manifest (new chain head)
        """
        manifest_hash = sha256(manifest_bytes)
        self._chain.append(manifest_hash)
        self._current = manifest_hash

        if verbose:
            print(f"  CHAIN UPDATE:")
            print(f"    Chain length : {self.length}")
            print(f"    New head     : {manifest_hash.hex()}")

        return manifest_hash

    def verify_link(self, claimed_prev_hash: bytes, verbose=False) -> bool:
        """
        Verify that a manifest's H(prev_manifest) matches the current chain head.

        This is part of Stage 1 (Pre-Verify) — if this fails, the manifest
        is a replay of an old update or was crafted for a different chain state.

        Args:
            claimed_prev_hash: The H(prev_manifest) field from the incoming manifest
            verbose: Print intermediate values

        Returns:
            bool: True if the chain link is valid
        """
        match = claimed_prev_hash == self._current

        if verbose:
            status = "✓ VALID" if match else "✗ CHAIN MISMATCH (possible replay attack)"
            print(f"  CHAIN LINK CHECK:")
            print(f"    Expected (head) : {self._current.hex()}")
            print(f"    Claimed (manifest): {claimed_prev_hash.hex()}")
            print(f"    Result          : {status}")

        return match

    def get_history(self) -> list:
        """Return the full chain history as a list of hex strings."""
        return [h.hex() for h in self._chain]

    def print_chain(self):
        """Print the full chain for debugging."""
        print(f"\n  MANIFEST CHAIN ({self.length} entries)")
        print(f"  {'─' * 50}")
        for i, h in enumerate(self._chain):
            label = "GENESIS" if i == 0 else f"Update #{i}"
            marker = " ← HEAD" if i == len(self._chain) - 1 else ""
            print(f"    [{i}] {label}: {h.hex()[:32]}...{marker}")
        print(f"  {'─' * 50}")


# ============================================================================
#  SELF-TEST
# ============================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  VLCDS Manifest Chain — Self-Test")
    print("=" * 70)

    chain = ManifestChain()

    print(f"\n  Initial chain head (genesis): {chain.head.hex()}")
    assert chain.head == GENESIS_HASH

    # Simulate accepting 3 updates
    for i in range(1, 4):
        fake_manifest = f"manifest_update_{i}".encode() + bytes(200)
        print(f"\n  Recording update #{i}...")
        chain.record(fake_manifest, verbose=True)

    chain.print_chain()

    # Test valid chain link
    print("\n  Testing valid chain link...")
    valid = chain.verify_link(chain.head, verbose=True)
    assert valid, "Valid chain link should pass"

    # Test invalid chain link (replay attack simulation)
    print("\n  Testing replay attack (old chain head)...")
    old_hash = bytes.fromhex(chain.get_history()[1])  # Use hash from update #1
    replay = chain.verify_link(old_hash, verbose=True)
    assert not replay, "Replay should be rejected"

    print(f"\n  ✓ All chain tests passed!")
    print("\n" + "=" * 70)
    print("  Self-test complete.")
    print("=" * 70)
