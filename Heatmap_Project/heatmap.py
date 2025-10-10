import numpy as np
import cv2
from typing import List, Tuple


def precompute_kernels(coords: List[Tuple[float, float]], gW: int, gH: int, wFinal: int, hFinal: int, radius: float, smooth: float):
    """Precompute kernel per sensor. Returns K shape (nSensors, gH*gW) dtype float32."""
    n = len(coords)
    gx = (np.arange(gW) + 0.5) / gW * wFinal
    gy = (np.arange(gH) + 0.5) / gH * hFinal
    Xg, Yg = np.meshgrid(gx, gy)
    grid = np.stack((Xg.ravel(), Yg.ravel()), axis=1)  # (gH*gW,2)
    radius2 = radius * radius
    K = np.empty((n, grid.shape[0]), dtype=np.float32)
    for i, (x0, y0) in enumerate(coords):
        dx = grid[:, 0] - x0
        dy = grid[:, 1] - y0
        dist2 = (dx * dx + dy * dy)
        K[i, :] = np.exp(-smooth * (dist2 / radius2)).astype(np.float32)
    return K


def render_heatmap_from_flatZ(Z_flat: np.ndarray, wFinal: int, hFinal: int, gW: int, gH: int) -> np.ndarray:
    """Z_flat shape (gH*gW,) -> returns BGR uint8 image (hFinal,wFinal,3)"""
    Z = Z_flat.reshape((gH, gW))
    Z = np.clip(Z, 0, 4095)
    gray = (Z * (255.0 / 4095.0)).astype(np.uint8)
    color = cv2.applyColorMap(gray, cv2.COLORMAP_JET)
    color = cv2.resize(color, (wFinal, hFinal), interpolation=cv2.INTER_LINEAR)
    return color


def compute_cop(pressures: List[int], coords: List[Tuple[float, float]]) -> Tuple[int, int]:
    # allow pressures to be list or numpy array and handle length mismatch with coords
    if coords is None or len(coords) == 0:
        return (0, 0)
    coords_arr = np.asarray(coords, dtype=np.float32)
    ps = np.asarray(pressures, dtype=np.float32)
    n_coords = coords_arr.shape[0]
    if ps.size < n_coords:
        # pad with zeros
        tmp = np.zeros((n_coords,), dtype=np.float32)
        tmp[:ps.size] = ps
        ps = tmp
    elif ps.size > n_coords:
        ps = ps[:n_coords]
    s = ps.sum()
    if s <= 0:
        return (0, 0)
    x = (coords_arr[:, 0] * ps).sum() / s
    y = (coords_arr[:, 1] * ps).sum() / s
    return (int(round(x)), int(round(y)))


def create_colorbar(height: int, width: int, ticks=None) -> np.ndarray:
    """Return a compact colorbar image; stripe slightly thicker than before."""
    # slightly thicker compact colorbar: stripe ~8 px (or width-8), labels right
    if ticks is None:
        ticks = list(range(0, 4096, 500))

    # gradient (flip so top shows high values)
    bar_vals = np.linspace(0, 4095, height).astype(np.float32)
    gray = (bar_vals * (255.0 / 4095.0)).astype(np.uint8)
    gray = np.flipud(gray)

    # make stripe a bit thicker than before (prefer ~8 px)
    preferred = 8
    stripe_w = max(preferred, min(preferred + 4, max(4, width - 8)))
    stripe = cv2.applyColorMap(gray.reshape(-1, 1), cv2.COLORMAP_JET)
    stripe = cv2.resize(stripe, (stripe_w, height), interpolation=cv2.INTER_LINEAR)

    # compact layout
    pad_left = 3
    pad_right = 6
    top = 6
    label_area_w = width - stripe_w + pad_right
    out_w = pad_left + stripe_w + label_area_w
    out_h = height + top + 4
    out = np.full((out_h, out_w, 3), 255, dtype=np.uint8)

    # place stripe
    out[top:top+height, pad_left:pad_left+stripe_w] = stripe

    # thin border for stripe
    cv2.rectangle(out, (pad_left, top), (pad_left+stripe_w-1, top+height-1), (120,120,120), 1)

    # ticks and labels to the right with slightly larger font to match stripe
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.34
    thickness_text = 1
    x_tick_start = pad_left + stripe_w
    for t in ticks:
        y = top + int((1.0 - (t / 4095.0)) * (height - 1))
        # small tick
        cv2.line(out, (x_tick_start, y), (x_tick_start+4, y), (120,120,120), 1)
        txt = str(t)
        tx = x_tick_start + 6
        ty = y + 4
        cv2.putText(out, txt, (tx, ty), font, font_scale, (80,80,80), thickness_text, cv2.LINE_AA)

    return out


def draw_indices(img: np.ndarray, coords: List[Tuple[float, float]], offset=(0,0)):
    # Draw small markers for sensor positions without numeric labels
    for (x, y) in coords:
        x_off = int(round(x + offset[0]))
        y_off = int(round(y + offset[1]))
        # white filled circle with thin black border for visibility
        cv2.circle(img, (x_off, y_off), 6, (255, 255, 255), -1)
        cv2.circle(img, (x_off, y_off), 6, (0, 0, 0), 1)

