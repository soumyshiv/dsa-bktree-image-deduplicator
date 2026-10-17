import numpy as np
from PIL import Image, ImageFilter, ImageOps


class PerceptualHash:
    """
    100-Bit Multi-Channel Perceptual Hash compatible with BK-Tree metric space.
    Subtracting two hashes (hash1 - hash2) returns the exact integer Hamming distance (0 to 100).
    """
    def __init__(self, bits: np.ndarray):
        self.bits = bits.astype(np.uint8).flatten()

    def __sub__(self, other):
        if other is None or not isinstance(other, PerceptualHash):
            return 100
        # Exact Hamming distance (number of differing bits out of 100)
        return int(np.count_nonzero(self.bits != other.bits))

    def __eq__(self, other):
        if not isinstance(other, PerceptualHash):
            return False
        return np.array_equal(self.bits, other.bits)

    def __hash__(self):
        return hash(self.bits.tobytes())

    def __str__(self):
        # Convert 100 bits into a clean 25-character hex string for the UI metadata box
        padded = np.pad(self.bits, (0, 4), constant_values=0)
        packed = np.packbits(padded)
        return packed.tobytes().hex()[:25]


def _pool_grid(channel: np.ndarray, rows: int, cols: int) -> np.ndarray:
    """Downsamples a 2D array into a (rows x cols) grid of block averages."""
    h, w = channel.shape
    out = np.zeros((rows, cols), dtype=np.float32)
    for r in range(rows):
        r0, r1 = int(round(r * h / rows)), int(round((r + 1) * h / rows))
        for c in range(cols):
            c0, c1 = int(round(c * w / cols)), int(round((c + 1) * w / cols))
            out[r, c] = np.mean(channel[r0:r1, c0:c1])
    return out


def generate_hash(image_path):
    try:
        img = Image.open(image_path)
        img = ImageOps.exif_transpose(img).convert("RGB")

        # Resize to 64x64 and apply Gaussian blur to absorb handheld burst tilt/shift
        img_small = img.resize((64, 64), Image.Resampling.BILINEAR)
        img_blur = img_small.filter(ImageFilter.GaussianBlur(radius=2.5))

        raw_arr = np.asarray(img_small, dtype=np.float32)
        arr = np.asarray(img_blur, dtype=np.float32)

        R, G, B = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

        # 1. Perceptual Luminance (Y) and Opponent Color Channels (RG, BY)
        L = 0.299 * R + 0.587 * G + 0.114 * B
        RG = R - G
        BY = 0.5 * (R + G) - B

        # High-frequency local edge/detail energy (separates wide group shots from close-ups)
        L_raw = 0.299 * raw_arr[:, :, 0] + 0.587 * raw_arr[:, :, 1] + 0.114 * raw_arr[:, :, 2]
        detail_energy = np.abs(L_raw - L)

        bits = []

        # --- GROUP 1: Coarse 4x4 Smoothed Luminance Layout (16 bits) ---
        luma_4x4 = _pool_grid(L, 4, 4)
        bits.extend((luma_4x4 > np.mean(L)).flatten())

        # --- GROUP 2: Coarse 4x4 Horizontal & Vertical Structural Gradients (24 bits) ---
        # Resilient to slight handheld framing shifts while separating opposite room angles
        h_grad = (luma_4x4[:, 1:] > luma_4x4[:, :-1]).flatten()  # 12 bits
        v_grad = (luma_4x4[1:, :] > luma_4x4[:-1, :]).flatten()  # 12 bits
        bits.extend(h_grad)
        bits.extend(v_grad)

        # --- GROUP 3: Center-Focus 4x4 Subject Grid (16 bits) ---
        center_L = L[12:52, 12:52]
        center_4x4 = _pool_grid(center_L, 4, 4)
        bits.extend((center_4x4 > np.mean(center_L)).flatten())

        # --- GROUP 4: Opponent Color Spatial Layout 3x3 (18 bits) ---
        rg_3x3 = _pool_grid(RG, 3, 3)
        by_3x3 = _pool_grid(BY, 3, 3)
        bits.extend((rg_3x3 > np.mean(RG)).flatten())  # 9 bits
        bits.extend((by_3x3 > np.mean(BY)).flatten())  # 9 bits

        # --- GROUP 5: Zoom/Tilt-Invariant Tonal & Color Profile (14 bits) ---
        l_pcts = np.percentile(L, [10, 25, 40, 50, 60, 75, 90])
        l_anchors = np.array([45.0, 75.0, 105.0, 128.0, 150.0, 175.0, 205.0])
        bits.extend(l_pcts > l_anchors)  # 7 bits

        rg_pcts = np.percentile(RG, [20, 50, 80])
        by_pcts = np.percentile(BY, [20, 50, 80])
        bits.extend(rg_pcts > np.array([-5.0, 5.0, 18.0]))   # 3 bits
        bits.extend(by_pcts > np.array([-10.0, 5.0, 20.0]))  # 3 bits
        bits.append(np.std(L) > 52.0)                        # 1 contrast bit

        # --- GROUP 6: Edge / Detail Texture Distribution 3x4 (12 bits) ---
        detail_3x4 = _pool_grid(detail_energy, 3, 4)
        bits.extend((detail_3x4 > np.mean(detail_energy)).flatten())

        return PerceptualHash(np.array(bits, dtype=np.uint8))

    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None