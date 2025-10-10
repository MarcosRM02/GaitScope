"""
Time formatting utilities.

This module provides functions for converting between different time representations
used in video playback and data visualization.
"""


def format_time_mmss(seconds: float) -> str:
    """
    Format time in seconds to MM:SS.mmm string format with millisecond precision.

    Args:
        seconds: Time value in seconds

    Returns:
        Formatted string in MM:SS.mmm format (e.g., "02:35.120")
    """
    try:
        # Round to nearest millisecond using integer arithmetic to avoid floating rounding issues
        total_ms = int(round(float(seconds) * 1000.0))
    except Exception:
        total_ms = 0

    mins = total_ms // 60000
    secs = (total_ms // 1000) % 60
    ms = total_ms % 1000
    return f"{mins:02d}:{secs:02d}.{ms:03d}"
