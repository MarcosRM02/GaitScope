# GaitScope

[![Top language](https://img.shields.io/github/languages/top/MarcosRM02/GaitScope)](https://github.com/MarcosRM02/GaitScope) [![License](https://img.shields.io/github/license/MarcosRM02/GaitScope)](LICENSE) [![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/) [![Issues](https://img.shields.io/github/issues/MarcosRM02/GaitScope)](https://github.com/MarcosRM02/GaitScope/issues) [![Stars](https://img.shields.io/github/stars/MarcosRM02/GaitScope?style=social)](https://github.com/MarcosRM02/GaitScope/stargazers) [![Last commit](https://img.shields.io/github/last-commit/MarcosRM02/GaitScope)](https://github.com/MarcosRM02/GaitScope/commits/main)

GaitScope is a desktop application for playing videos synchronized with gait analysis data (heatmaps, GaitRite footprints, time-series plots, etc.). It is built with PyQt5, OpenCV and pyqtgraph, and is intended to visualize data from insoles/sensors and systems like GaitRite.

---

## Table of contents

- [Requirements](#requirements)
- [Create and activate a virtual environment](#create-and-activate-a-virtual-environment)
- [Install dependencies](#install-dependencies)
- [Run the application](#run-the-application)
- [Deactivate the virtual environment](#deactivate-the-virtual-environment)
- [Project structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---

## Requirements

- Python 3.8 or newer
- pip
- (Optional) git to clone the repository

Check your Python version:

```bash
python --version
```

---

## Create and activate a virtual environment

It is recommended to create a dedicated virtual environment per project to isolate dependencies.

Linux / macOS (zsh, bash):

```bash
# From the project root
python -m venv .venv
# Activate the environment
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Notes:

- `.venv` is a common convention; you can use `venv`, `env` or any name you prefer.
- After activation your shell prompt usually shows the environment name.

---

## Install dependencies

This project uses `pyproject.toml`. The recommended way to install dependencies is with pip in editable mode.

1. (Optional) Upgrade pip and setuptools:

```bash
python -m pip install --upgrade pip setuptools
```

2. Install the package and its dependencies:

```bash
# Production / normal install
pip install -e .

# Install with development extras (if defined in pyproject)
pip install -e ".[dev]"
```

Alternative: if you have a `requirements.txt`, use:

```bash
pip install -r requirements.txt
```

Common notes / troubleshooting:

- If you have issues with OpenCV and Qt, consider using `opencv-python-headless` when you do not need OpenCV's GUI integration.
- If building a package fails (binary extension compilation), install system-level build dependencies first (e.g. `build-essential`, `libgl1-mesa-dev`, etc.), depending on your distribution and the failing package.

---

## Run the application

With the virtual environment activated and dependencies installed, run:

```bash
# Option 1: entry point (if package is installed)
gaitScope

# Option 2: run the module directly
python -m src.main
```

The application will open a graphical window where you can load datasets (CSV, heatmaps, footprints) and videos.

---

## Deactivate the virtual environment

When you are done, deactivate the environment with:

```bash
deactivate
```

This restores the system Python in the current terminal session.

---

## Project structure

- `src/` — Main source code
  - `core/` — Core logic (video_player, data_manager, controllers)
  - `heatmap_generation/` — Heatmap generation and animation code
  - `utils/` — Utilities (file management, Qt configuration helpers, etc.)
  - `widgets/` — Custom UI components
- `data/` — Example data organized by participant
- `pyproject.toml` — Package configuration and dependencies
- `export_yarray_footprints.py` — Helper script to export footprints

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---
