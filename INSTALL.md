# Installation Guide

## Requirements

- Python 3.8 or higher
- pip (Python package installer)

## Installation Methods

### Method 1: User Installation (Recommended)

Install the package system-wide or in a virtual environment:

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package
pip install .
```

### Method 2: Development Installation

For developers who want to modify the code:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode with development dependencies
pip install -e ".[dev]"
```

### Method 3: Direct Execution

Run without installation:

```bash
# Install dependencies only
pip install PyQt5 opencv-python numpy pandas pyqtgraph

# Run directly
python -m video_gait_analyzer.main
```

## Verify Installation

After installation, verify by running:

```bash
video-gait-analyzer --help
# Or
video-gait-analyzer
```

## Common Issues

### Qt Plugin Issues

If you see Qt plugin errors:

```bash
# On Linux, install Qt dependencies
sudo apt-get install libxcb-xinerama0

# On macOS, ensure XCode command line tools are installed
xcode-select --install
```

### OpenCV Issues

If OpenCV fails to import:

```bash
# Try headless version
pip uninstall opencv-python
pip install opencv-python-headless
```

### Permission Issues

If you get permission errors during installation:

```bash
# Use --user flag
pip install --user .

# Or use virtual environment (recommended)
```

## Upgrading

To upgrade to the latest version:

```bash
pip install --upgrade .
```

## Uninstallation

```bash
pip uninstall video-gait-analyzer
```

## Dependencies

The package will automatically install:

- PyQt5 (>= 5.15.0)
- opencv-python (>= 4.5.0)
- numpy (>= 1.20.0)
- pandas (>= 1.3.0)
- pyqtgraph (>= 0.12.0)

Development dependencies (with `.[dev]`):

- pytest (>= 7.0)
- pytest-qt (>= 4.0)
- black (>= 22.0)
- flake8 (>= 4.0)
- mypy (>= 0.950)

## Next Steps

After installation, see:

- [README.md](README.md) for usage instructions
- [MIGRATION.md](MIGRATION.md) for migration from old version
- [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines
