# Video Gait Analyzer

A comprehensive video player application with synchronized gait analysis data visualization, built with clean architecture principles and modular design.

![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 🌟 Features

- **📹 Advanced Video Playback**: Frame-by-frame control with variable playback speed (0.01x to 2.0x)
- **🔄 Real-time Synchronization**: Automatic synchronization between video frames and sensor data
- **📊 Pressure Sensor Visualization**: Multi-channel pressure sensor data plotting with interactive cursor
- **👣 GaitRite Analysis**: Footprint contour visualization and trajectory analysis
- **📁 Dataset Management**: Intuitive navigation through subjects, categories, and sessions
- **⌨️ Keyboard Shortcuts**: Efficient control with keyboard shortcuts
- **🎨 Modern UI**: Clean, responsive interface built with PyQt5

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Data Format](#data-format)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Quick Install

```bash
# Clone the repository
git clone <repository-url>
cd Visualizador_Videos

# Install the package
pip install .
```

### Development Install

```bash
# Install with development dependencies
pip install -e ".[dev]"
```

For detailed installation instructions, see [INSTALL.md](INSTALL.md).

## 🎯 Quick Start

### Running the Application

```bash
# After installation
video-gait-analyzer

# Or run directly
python -m video_gait_analyzer.main

# Or use the run script
python run.py
```

### Loading a Dataset

1. Click on the **Subject** dropdown and select a participant (e.g., P1, P2)
2. Select a **Category** (e.g., FP, NP, SP)
3. Select a **Session** (e.g., 1, 2, 3)
4. Click **Load Dataset**

The application will automatically load:

- Video file (\*.mp4)
- Pressure sensor data (L.csv, R.csv)
- GaitRite footprint data (if available)

## 📖 Usage

### Video Controls

- **▶ Play/⏸ Pause**: Start or pause video playback
- **◀ Frame / Frame ▶**: Navigate frame by frame
- **⏹ Reset**: Return to beginning
- **Speed**: Adjust playback speed (0.01x to 2.0x)

### Keyboard Shortcuts

- `Space`: Play/Pause toggle
- `Left Arrow`: Previous frame
- `Right Arrow`: Next frame
- Click on slider: Jump to position

### Data Visualization

- **Upper Plot**: GaitRite footprint visualization with trajectory
- **Lower Plot**: Synchronized pressure sensor data (4 groups per side)
- **Yellow Cursor**: Current position synchronized across video and plots

## 📂 Project Structure

```
video_gait_analyzer/
├── __init__.py              # Package initialization
├── main.py                  # Application entry point
├── constants.py             # Configuration constants
├── core/                    # Core application logic
│   ├── __init__.py
│   ├── video_player.py      # Main window (UI + coordination)
│   ├── video_controller.py  # Video playback logic
│   ├── data_manager.py      # Data loading and processing
│   └── plot_manager.py      # Plot visualization management
├── widgets/                 # Custom Qt widgets
│   ├── __init__.py
│   ├── clickable_slider.py  # Enhanced slider widget
│   └── time_axis.py         # Time-formatted axis
└── utils/                   # Utility functions
    ├── __init__.py
    ├── qt_config.py         # Qt plugin configuration
    ├── time_utils.py        # Time formatting utilities
    └── file_utils.py        # File discovery utilities
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

## 📊 Data Format

### Pressure Sensor CSV Files

- **L.csv**: Left side sensor data (up to 32 columns)
- **R.csv**: Right side sensor data (up to 32 columns)
- Sampling rate: 64 Hz (configurable in constants.py)
- Format: CSV with numeric values

### GaitRite Data Files

- **gaitrite_test.csv**: Main analysis data
  - Columns: Gait_Id, Event, Foot, Xback, Xfront, Ybottom, Ytop, Yarray
  - Delimiter: semicolon (;)
- **generated_footprints_left.csv**: Left foot contours
  - Columns: x_cm, y_cm, gait_id, event, sample_idx
- **generated_footprints_right.csv**: Right foot contours
  - Columns: x_cm, y_cm, gait_id, event, sample_idx

### Directory Structure

```
data/
├── P1/                    # Participant 1
│   ├── FP/               # Fast Pace
│   │   ├── 1/           # Session 1
│   │   │   ├── video.mp4
│   │   │   ├── L.csv
│   │   │   ├── R.csv
│   │   │   └── gaitrite_test.csv
│   │   └── 2/           # Session 2
│   ├── NP/               # Normal Pace
│   └── SP/               # Slow Pace
└── P2/                   # Participant 2
    └── ...
```

## 🛠️ Development

### Setting Up Development Environment

```bash
# Clone repository
git clone <repository-url>
cd Visualizador_Videos

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

### Using Make Commands

```bash
make help           # Show available commands
make install-dev    # Install with dev dependencies
make test           # Run tests
make lint           # Run linters
make format         # Format code with Black
make run            # Run application
make clean          # Clean build artifacts
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=video_gait_analyzer

# Run specific test
pytest tests/test_utils.py -v
```

### Code Style

- Follow PEP 8 style guide
- Use Black for code formatting
- Use type hints where appropriate
- Write docstrings for all public functions/classes
- Keep functions focused and modular

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Contribution Guide

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linters
5. Commit your changes (`git commit -m 'feat: Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📚 Documentation

- [Installation Guide](INSTALL.md)
- [Migration Guide](MIGRATION.md) - For users migrating from old version
- [Contributing Guidelines](CONTRIBUTING.md)
- [Architecture Documentation](ARCHITECTURE.md) (coming soon)

## 🔄 Migrating from Old Version

If you're upgrading from the old `ephy.py` monolithic version, see [MIGRATION.md](MIGRATION.md) for a detailed guide.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

**Gait Analysis Team**

## 🙏 Acknowledgments

- Built with PyQt5 for the user interface
- OpenCV for video processing
- PyQtGraph for high-performance plotting
- Pandas and NumPy for data processing

## 📧 Support

For questions or issues:

- Open an issue on GitHub
- Contact the development team

---

**Note**: This is a complete rewrite of the original `ephy.py` with improved modularity, clean architecture, and comprehensive documentation.
