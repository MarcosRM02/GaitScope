# GaitScope

## Description

GaitScope is a video player application with synchronized gait analysis data visualization. It allows playing videos while displaying heatmaps, footprints, and other data related to human gait analysis, using GaitRite data and other SSITH insoles sensors.

The application is built with PyQt5 and uses OpenCV for video processing, numpy and pandas for data handling, and pyqtgraph for graph visualization.

## Installation

### Prerequisites

- Python 3.8 or higher
- pip

### Installation from Source Code

1. Clone the repository:

   ```bash
   git clone https://github.com/MarcosRM02/GaitScope.git
   cd GaitScope
   ```

2. Install dependencies:

   ```bash
   pip install -e .
   ```

   Optionally, install development dependencies:

   ```bash
   pip install -e ".[dev]"
   ```

## Usage

After installation, you can run the application with:

```bash
gaitScope
```

Or directly with Python:

```bash
python -m src.main
```

The application will open a graphical interface where you can load videos and gait analysis data for synchronized visualization.

## Project Structure

- `src/`: Main source code
  - `core/`: Core logic (data_manager, video_player, etc.)
  - `heatmap_generation/`: Heatmap generation and animations
  - `utils/`: Utilities (file_utils, qt_config, etc.)
  - `widgets/`: User interface components
- `data/`: Sample data organized by participants (P1, P10, etc.) with folders for different data types (FP: footprints, NP: normal pressure, etc.)
- `export_yarray_footprints.py`: Script to export footprints
- `pyproject.toml`: Project configuration and dependencies

## Dependencies

- PyQt5: Graphical user interface
- opencv-python-headless: Video processing
- numpy: Numerical computing
- pandas: Data handling
- pyqtgraph: Graph visualization

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

## Authors

- MAmI Lab
