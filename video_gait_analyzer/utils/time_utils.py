"""
Time formatting utilities.

This module provides functions for converting between different time representations
used in video playback and data visualization.
"""


def format_time_mmss(seconds: float) -> str:
    """
    Format time in seconds to MM:SS string format.
    
    Args:
        seconds: Time value in seconds
        
    Returns:
        Formatted string in MM:SS format (e.g., "02:35")
        
    Examples:
        >>> format_time_mmss(155.7)
        '02:35'
        >>> format_time_mmss(62.3)
        '01:02'
    """
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"
