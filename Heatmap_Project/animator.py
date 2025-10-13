import numpy as np
import cv2
from collections import deque
from typing import List, Tuple
from heatmap import precompute_kernels, render_heatmap_from_flatZ, compute_cop, create_colorbar, draw_indices


class Animator:
    def __init__(self, params, coords_left: List[Tuple[float,float]], coords_right: List[Tuple[float,float]]):
        self.params = params
        self.coords_left = coords_left
        self.coords_right = coords_right
        self.left_seq = []
        self.right_seq = []
        self.frame_idx = 0
        self.trail_len = params["trailLength"]
        self.left_trail = deque(maxlen=self.trail_len)
        self.right_trail = deque(maxlen=self.trail_len)
        # precompute kernels
        self.K_left = precompute_kernels(coords_left, params["gridW"], params["gridH"], params["wFinal"], params["hFinal"], params["radius"], params["smoothness"]) if coords_left else np.zeros((0, params["gridW"]*params["gridH"]), dtype=np.float32)
        self.K_right = precompute_kernels(coords_right, params["gridW"], params["gridH"], params["wFinal"], params["hFinal"], params["radius"], params["smoothness"]) if coords_right else np.zeros((0, params["gridW"]*params["gridH"]), dtype=np.float32)

    def load_sequences(self, left_seq: List[List[int]], right_seq: List[List[int]]):
        self.left_seq = left_seq
        self.right_seq = right_seq
        self.frame_idx = 0
        self.left_trail.clear()
        self.right_trail.clear()

    def reset(self):
        self.frame_idx = 0
        self.left_trail.clear()
        self.right_trail.clear()

    def n_frames(self):
        return max(len(self.left_seq), len(self.right_seq))

    def _render_side(self, seq, K, coords):
        if not seq or K.shape[0] == 0:
            blank = np.zeros((self.params["hFinal"], self.params["wFinal"], 3), dtype=np.uint8)
            return blank, (0, 0)
        frame = seq[self.frame_idx % len(seq)]
        p = np.asarray(frame, dtype=np.float32)
        if p.size != K.shape[0]:
            # pad or trim
            if p.size < K.shape[0]:
                tmp = np.zeros((K.shape[0],), dtype=np.float32)
                tmp[:p.size] = p
                p = tmp
            else:
                p = p[:K.shape[0]]
        Z_flat = p.dot(K)
        img = render_heatmap_from_flatZ(Z_flat, self.params["wFinal"], self.params["hFinal"], self.params["gridW"], self.params["gridH"])  # BGR
        cop = compute_cop(frame, coords)
        return img, cop

    def get_frame(self) -> np.ndarray:
        # render left and right
        left_img, left_cop = self._render_side(self.left_seq, self.K_left, self.coords_left)
        right_img, right_cop = self._render_side(self.right_seq, self.K_right, self.coords_right)
        # update trails
        self.left_trail.append(left_cop)
        self.right_trail.append(right_cop)
        # compose final image
        w = self.params["wFinal"]
        h = self.params["hFinal"]
        margin = self.params["margin"]
        legendW = self.params["legendWidth"]
        # create colorbar (may return height != h)
        cb = create_colorbar(h, legendW)
        cb_h, cb_w = cb.shape[:2]
        # final image height must fit the taller of heatmaps and colorbar, plus margins
        content_h = max(h, cb_h)
        final_h = content_h + margin * 2
        final_w = w * 2 + margin * 3 + cb_w
        out = np.full((final_h, final_w, 3), 255, dtype=np.uint8)
        # vertical offsets to center left/right images within content area
        ly = margin + (content_h - h) // 2
        cb_y = margin + (content_h - cb_h) // 2
        # place left image
        lx = margin
        out[ly:ly+h, lx:lx+w] = left_img
        # place right image
        rx = lx + w + margin
        out[ly:ly+h, rx:rx+w] = right_img
        # place colorbar to the right of right image with margin
        cb_x = rx + w + margin
        out[cb_y:cb_y+cb_h, cb_x:cb_x+cb_w] = cb
         # draw indices
        draw_indices(out, self.coords_left, offset=(lx, ly))
        draw_indices(out, self.coords_right, offset=(rx, ly))
        # draw trails as filled pink points with decreasing size (newest -> largest)
        pink = (203, 105, 255)
        # left trail (smaller sizes, no outline)
        nL = len(self.left_trail)
        if nL > 0:
            max_size = 8
            min_size = 2
            for i, pt in enumerate(reversed(self.left_trail)):
                # newer points are larger
                size = int(min_size + ((nL - i) / nL) * (max_size - min_size))
                x = int(pt[0]) + lx
                y = int(pt[1]) + ly
                cv2.circle(out, (x, y), size, pink, -1)
        # right trail (smaller sizes, no outline)
        nR = len(self.right_trail)
        if nR > 0:
            max_size = 8
            min_size = 2
            for i, pt in enumerate(reversed(self.right_trail)):
                size = int(min_size + ((nR - i) / nR) * (max_size - min_size))
                x = int(pt[0]) + rx
                y = int(pt[1]) + ly
                cv2.circle(out, (x, y), size, pink, -1)
        # draw COP as filled pink points (BGR)
        pink = (203, 105, 255)
        if left_cop != (0, 0):
            cv2.circle(out, (left_cop[0]+lx, left_cop[1]+ly), 8, pink, -1)
        if right_cop != (0, 0):
            cv2.circle(out, (right_cop[0]+rx, right_cop[1]+ly), 8, pink, -1)

        # Frame index and time counter removed per user request
        return out

    def step(self, delta=1):
        # Advance frame index but clamp to [0, n_frames-1] (no looping)
        n = max(1, self.n_frames())
        new_idx = self.frame_idx + delta
        if new_idx < 0:
            new_idx = 0
        if new_idx > n - 1:
            new_idx = n - 1
        self.frame_idx = new_idx

    def set_frame(self, idx: int):
        self.frame_idx = max(0, min(idx, max(0, self.n_frames()-1)))
