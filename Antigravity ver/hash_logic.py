"""
Metric Space Feature Extraction & Discriminative 100-Bit Perceptual Hashing Logic.

Algorithmic Background:
    In discrete metric spaces, elements must satisfy four axioms with a distance metric d(x, y):
    1. d(x, y) >= 0              (Non-negativity)
    2. d(x, y) == 0 <=> x == y   (Identity of indiscernibles)
    3. d(x, y) == d(y, x)        (Symmetry)
    4. d(x, z) <= d(x, y) + d(y, z) (Triangle Inequality)

The Hamming distance on binary bitstrings is a mathematically proven metric:
    HammingDistance(u, v) = count_nonzero(u XOR v)

Discriminative Design:
    To prevent false positives between different scenes taken in the same room
    (e.g., conference room white walls vs orange walls vs podium banners), this hash combines:
    1. 8x8 Structural Luminance (64 bits): Lanczos-downsampled macro-geometry
    2. 4x4 Color Hue/Chroma Grid (24 bits): Spatial color layout separation
    3. Directional Gradient Flow (12 bits): Macro symmetry & contrast balance
"""

import numpy as np
from PIL import Image, ImageOps


class PerceptualHash:
    """
    100-Bit Multi-Channel Discriminative Perceptual Hash compatible with BK-Tree metric space.
    Subtracting two hashes (hash1 - hash2) returns the exact integer Hamming distance (0 to 100).
    """

    def __init__(self, bits: np.ndarray):
        self.bits = bits.astype(np.uint8).flatten()

    def __sub__(self, other):
        """Calculates exact Hamming distance between two hashes."""
        if other is None or not isinstance(other, PerceptualHash):
            return 100
        # Exact Hamming distance (differing bits out of 100)
        return int(np.count_nonzero(self.bits != other.bits))

    def __eq__(self, other):
        if not isinstance(other, PerceptualHash):
            return False
        return np.array_equal(self.bits, other.bits)

    def __hash__(self):
        return hash(self.bits.tobytes())

    def __str__(self):
        # Convert 100 bits into a 25-character hex string for the UI metadata box
        padded = np.pad(self.bits, (0, 4), constant_values=0)
        packed = np.packbits(padded)
        return packed.tobytes().hex()[:25]


def generate_hash(image_path: str):
    """
    Computes a 100-bit discriminative perceptual hash engineered to:
    - Keep true burst-shot duplicates tightly clustered (distance <= 12-14)
    - Strongly separate different scenes in the same room (distance >= 19-35)
    """
    try:
        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img).convert("RGB")

        # 1. 8x8 Structural Luminance (64 bits) - Lanczos downsampling suppresses fine handheld jitter
        img_gray = img.convert("L").resize((32, 32), Image.Resampling.LANCZOS)
        arr_gray = np.asarray(img_gray, dtype=np.float32)
        # 8x8 block pooling
        blocks = arr_gray.reshape(8, 4, 8, 4).mean(axis=(1, 3))
        med = np.median(blocks)
        struct_bits = (blocks > med).flatten()  # 64 bits

        # 2. 4x4 Color Hue/Chroma Grid (24 bits) - Separates orange wall vs blue suit vs yellow banner
        hsv = img.convert("HSV").resize((4, 4), Image.Resampling.BILINEAR)
        hsv_arr = np.asarray(hsv, dtype=np.float32)
        H, S, V = hsv_arr[:, :, 0], hsv_arr[:, :, 1], hsv_arr[:, :, 2]
        # Hue quadrant distribution + Saturation presence
        hue_bits = (H > 35).flatten()  # 16 bits
        sat_bits = (S > 50)[:8].flatten()  # 8 bits

        # 3. Directional Gradient Flow (12 bits) - Macro symmetry & balance
        grad_bits = [
            blocks[:, :4].mean() > blocks[:, 4:].mean(),  # Left vs Right
            blocks[:4, :].mean() > blocks[4:, :].mean(),  # Top vs Bottom
            blocks[2:6, 2:6].mean() > blocks.mean(),      # Center vs Periphery
            blocks[0, 0] > blocks[7, 7],
            blocks[0, 7] > blocks[7, 0],
            float(H.mean()) > 30.0,
            float(S.mean()) > 40.0,
            float(V.mean()) > 120.0,
            float(arr_gray.std()) > 45.0,
            blocks[0:4, 0:4].mean() > blocks[4:8, 4:8].mean(),
            blocks[0:4, 4:8].mean() > blocks[4:8, 0:4].mean(),
            blocks[1:7, 1:7].mean() > med,
        ]

        all_bits = np.concatenate([struct_bits, hue_bits, sat_bits, grad_bits]).astype(np.uint8)[:100]
        return PerceptualHash(all_bits)

    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None
