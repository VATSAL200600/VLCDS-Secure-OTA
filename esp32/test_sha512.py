"""Test pure Python SHA-512 against hashlib.sha512"""
import struct

# Initial hash values
_H = [
    0x6a09e667f3bcc908, 0xbb67ae8584caa73b, 0x3c6ef372fe94f82b, 0xa54ff53a5f1d36f1,
    0x510e527fade682d1, 0x9b05688c2b3e6c1f, 0x1f83d9abfb41bd6b, 0x5be0cd19137e2179
]

# Round constants
_K = [
    0x428a2f98d728ae22, 0x7137449123ef65cd, 0xb5c0fbcfec4d3b2f, 0xe9b5dba58189dbbc,
    0x3956c25bf348b538, 0x59f111f1b605d019, 0x923f82a4af1934e1, 0xab1c5ed5da6d8118,
    0xd807aa98a3030242, 0x12835b0145706fbe, 0x243185be4ee4b28c, 0x550c7dc3d5ffb4e2,
    0x72be5d74f27b896f, 0x80deb1fe3b1696b1, 0x9bdc06a725c71235, 0xc19bf174cf692694,
    0xe49b69c19ef14ad2, 0xefbe4786384f25e3, 0x0fc19dc68b8cd5b5, 0x240ca1cc77ac9c65,
    0x2de92c6f592b0275, 0x4a7484aa6ea6e483, 0x5cb0a9dcbd41fbd4, 0x76f988da831153b5,
    0x983e5152ee66dfab, 0xa831c66d2db43210, 0xb00327c898fb213f, 0xbf597fc7beef0ee4,
    0xc6e00bf33da88fc2, 0xd5a79147930aa725, 0x06ca6351e003826f, 0x142929670a0e6e70,
    0x27b70a8546d22ffc, 0x2e1b21385c26c926, 0x4d2c6dfc5ac42aed, 0x53380d139d95b3df,
    0x650a73548baf63de, 0x766a0abb3c77b2a8, 0x81c2c92e47865746, 0x92722c85129ff577,
    0xa2bfe8a14cf1a564, 0xa81a664bbc423001, 0xc2478792006ff82e, 0xc76c51a30654be30,
    0xd192e819d6ef5218, 0xd69906245565a910, 0xf40e35855771202a, 0x106aa07032bbd1b8,
    0x19a4c116b8d2d0c8, 0x1e376c085141ab53, 0x2748774cdf8eeb99, 0x34b0bcb5e19b48a8,
    0x391c0cb3c5c95a63, 0x4ed8aa4ae3418acb, 0x5b9cca4f7763e373, 0x682e6ff3d6b2b8a3,
    0x748f82ee5defb2fc, 0x78a5636f43172f60, 0x84c87814a1f0ab72, 0x8cc702081a6439ec,
    0x90befffa23631e28, 0xa4506cebde82bde9, 0xbef9a3f7b2c67915, 0xc67178f2e372532b,
    0xca273eceea26619c, 0xd186b8c721c0c207, 0xeada7dd6cde0eb1e, 0xf57d4f7fee6ed178,
    0x06f067aa72176fba, 0x0a637dc5a2c898a6, 0x113f9804bef90dae, 0x1b710b35131c471b,
    0x28db77f523047d84, 0x32caab7b40c72493, 0x3c9ebe0a15c9bebc, 0x431d67c49c100d4c,
    0x4cc5d4becb3e42b6, 0x597f299cfc657e2a, 0x5fcb6fab3ad6faec, 0x6c44198c4a475817
]

MASK64 = 0xFFFFFFFFFFFFFFFF

def _rotr(x, n):
    return ((x >> n) | (x << (64 - n))) & MASK64

def pure_sha512(data):
    if isinstance(data, str):
        data = data.encode('utf-8')
    orig_len = len(data)
    # Padding: 1 byte 0x80, padding zeros, 16 bytes big-endian length in bits
    pad_len = (128 - ((orig_len + 1 + 16) % 128)) % 128
    data = data + b'\x80' + b'\x00' * pad_len + struct.pack('>QQ', 0, orig_len * 8)
    
    h = list(_H)
    w = [0] * 80
    
    for i in range(0, len(data), 128):
        block = data[i:i+128]
        for t in range(16):
            w[t] = struct.unpack('>Q', block[t*8:(t+1)*8])[0]
        for t in range(16, 80):
            s0 = _rotr(w[t-15], 1) ^ _rotr(w[t-15], 8) ^ (w[t-15] >> 7)
            s1 = _rotr(w[t-2], 19) ^ _rotr(w[t-2], 61) ^ (w[t-2] >> 6)
            w[t] = (w[t-16] + s0 + w[t-7] + s1) & MASK64
            
        a, b, c, d, e, f, g, h_val = h
        
        for t in range(80):
            S1 = _rotr(e, 14) ^ _rotr(e, 18) ^ _rotr(e, 41)
            ch = (e & f) ^ ((~e) & g)
            temp1 = (h_val + S1 + ch + _K[t] + w[t]) & MASK64
            S0 = _rotr(a, 28) ^ _rotr(a, 34) ^ _rotr(a, 39)
            maj = (a & b) ^ (a & c) ^ (b & c)
            temp2 = (S0 + maj) & MASK64
            
            h_val = g
            g = f
            f = e
            e = (d + temp1) & MASK64
            d = c
            c = b
            b = a
            a = (temp1 + temp2) & MASK64
            
        h[0] = (h[0] + a) & MASK64
        h[1] = (h[1] + b) & MASK64
        h[2] = (h[2] + c) & MASK64
        h[3] = (h[3] + d) & MASK64
        h[4] = (h[4] + e) & MASK64
        h[5] = (h[5] + f) & MASK64
        h[6] = (h[6] + g) & MASK64
        h[7] = (h[7] + h_val) & MASK64
        
    return struct.pack('>8Q', *h)

if __name__ == '__main__':
    import hashlib
    test_msgs = [b"", b"abc", b"message digest", b"VLCDS_MANIFEST_TEST_1234567890"]
    for m in test_msgs:
        ref = hashlib.sha512(m).digest()
        calc = pure_sha512(m)
        assert ref == calc, f"Mismatch on {m}!"
    print("ALL SHA-512 TESTS PASSED PERFECTLY!")
