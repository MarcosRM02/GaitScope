"""
Constants used throughout the Video Gait Analyzer application.

This module contains all constant values used for configuration,
including GaitRite carpet dimensions, sampling rates, and UI defaults.
"""

# GaitRite carpet physical dimensions (in centimeters)
CARPET_WIDTH_CM = 61
CARPET_LENGTH_CM = 488
CARPET_RATIO = CARPET_WIDTH_CM / float(CARPET_LENGTH_CM)  # width/height ratio

# Data processing constants
DEFAULT_CSV_SAMPLING_RATE = 64.0  # Hz
DEFAULT_COLUMNS_PER_GROUP = 8
DEFAULT_NUMBER_OF_GROUPS = 4
DEFAULT_MAX_COLUMNS = 32

# Plot visualization constants
DEFAULT_PLOT_WINDOW_SECONDS = 5.0
DEFAULT_R_OFFSET = 80000.0  # Offset for right-side data visualization
PLOT_UPDATE_INTERVAL = 1.0 / 20.0  # 20 Hz update rate for plot markers

# Video playback constants
DEFAULT_FPS = 30.0
DEFAULT_TIMER_INTERVAL = 33  # milliseconds (approximately 30 fps)

# Playback speed options (multipliers)
PLAYBACK_SPEED_OPTIONS = [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 1.5, 2.0]

# Slider interaction constants
DRAG_SEEK_INTERVAL = 1.0 / 10.0  # Maximum 10 seeks per second during dragging

# GaitRite conversion factor
GAITRITE_CONVERSION_FACTOR = 1.27  # Conversion factor for GaitRite units to cm

# Plot colors for different data groups
# Use a pleasant palette suited for white backgrounds (hex colors)
PLOT_COLORS = ['#e74c3c', '#2980b9', '#27ae60', '#8e44ad']  # Red, Blue, Green, Purple

# Cursor and marker colors
CURSOR_COLOR = (255, 200, 0)  # Yellow/Gold
MARKER_LEFT_COLOR = (255, 200, 0)  # Yellow/Gold
MARKER_RIGHT_COLOR = (33, 97, 140)  # Dark blue

# Footprint colors
FOOTPRINT_LEFT_COLOR = '#E74C3C'  # Red
FOOTPRINT_RIGHT_COLOR = '#21618C'  # Dark blue

# File search patterns
VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov']
CSV_FILE_NAMES = ['L.csv', 'R.csv']
GAITRITE_FILE_NAME = 'gaitrite_test.csv'
FOOTPRINT_FILE_NAMES = {
    'left': ['generated_footprints_left.csv', 'footprints_left.csv'],
    'right': ['generated_footprints_right.csv', 'footprints_right.csv']
}

# Directory exclusions
EXCLUDED_DIRECTORIES = {'sitdown', 'stand'}

# UI window defaults
DEFAULT_WINDOW_WIDTH = 1100
DEFAULT_WINDOW_HEIGHT = 800
DEFAULT_VIDEO_BACKGROUND = "black"

# Carpet background for GaitRite plot
CARPET_BACKGROUND_COLOR = (240, 240, 240, 100)  # Light gray with transparency
CARPET_BORDER_COLOR = 'gray'

# Sensor grouping indices for 32-column layout (0-based column indices)
# English names: forefoot, midfoot, hindfoot
LEFT_FOREFOOT_INDICES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 16, 17, 18, 19, 20, 21, 22, 23]
LEFT_MIDFOOT_INDICES = [11, 12, 14, 15]
LEFT_HINDFOOT_INDICES = [13, 24, 25, 26, 27, 28, 29, 30, 31]

RIGHT_FOREFOOT_INDICES = [4, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 24, 25, 26, 27, 28, 29, 30, 31]
RIGHT_MIDFOOT_INDICES = [0, 1, 3, 6]
RIGHT_HINDFOOT_INDICES = [2, 16, 17, 18, 19, 20, 21, 22, 23]
SENSOR_GROUP_LABELS = ['Forefoot', 'Midfoot', 'Hindfoot']

