import argparse
from io_utils import read_points, read_sequence
from animator import Animator
from gui import MainWindow
from PySide6 import QtWidgets
import sys


def default_params():
    return {
        "wFinal": 175,
        "hFinal": 520,
        "gridW": 20,
        "gridH": 69,
        "trailLength": 10,
        "margin": 50,
        "legendWidth": 80,
        "radius": 70.0,
        "smoothness": 2.0,
        "fps": 64,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--L", default="L.csv")
    p.add_argument("--R", default="R.csv")
    p.add_argument("--left", default="in/leftPoints.json")
    p.add_argument("--right", default="in/rightPoints.json")
    args = p.parse_args()
    params = default_params()
    left_pts = read_points(args.left)
    right_pts = read_points(args.right)
    left_seq = read_sequence(args.L)
    right_seq = read_sequence(args.R)
    animator = Animator(params, left_pts, right_pts)
    animator.load_sequences(left_seq, right_seq)
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow(animator)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
