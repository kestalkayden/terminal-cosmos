"""Trail rendering utilities for consistent particle trail effects."""

from typing import Deque, Tuple, List, Callable, Optional


def render_gradient_trail(
    stdscr,
    trail: Deque[Tuple[float, float]],
    color_cache: List[Tuple[int, int]],
    max_rows: int,
    max_cols: int,
    char_selector: Optional[Callable[[int, int, float], str]] = None,
    visibility_threshold: float = 0.05,
    bold_threshold: float = 0.6
):
    """Render a particle trail with gradient color fading.

    Used by modes with pre-computed gradient color caches (Meteor, Fireworks).
    Provides consistent trail rendering with configurable character selection.

    Args:
        stdscr: Curses screen object
        trail: Deque of (x, y) position tuples
        color_cache: Pre-computed gradient cache [(attr_normal, attr_bold), ...]
        max_rows: Maximum row boundary
        max_cols: Maximum column boundary
        char_selector: Optional function(trail_idx, trail_len, progress) -> char
                      If None, uses default '·' character
        visibility_threshold: Skip trail segments dimmer than this (0.0-1.0)
        bold_threshold: Use bold attribute for segments brighter than this (0.0-1.0)

    Example:
        >>> # Simple trail with default character
        >>> render_gradient_trail(stdscr, meteor.trail, cache, 24, 80)
        >>>
        >>> # Custom character selection (Meteor mode pattern)
        >>> def meteor_chars(idx, length, progress):
        ...     connected_len = int(length * 0.7)
        ...     segments_from_head = length - 1 - idx
        ...     if segments_from_head <= connected_len:
        ...         return '╱'
        ...     elif segments_from_head <= connected_len + int(length * 0.2):
        ...         return '/'
        ...     return '′'
        >>> render_gradient_trail(stdscr, trail, cache, 24, 80,
        ...                       char_selector=meteor_chars)
    """
    import curses

    trail_length = len(trail)
    if trail_length == 0:
        return

    for i, (trail_x, trail_y) in enumerate(trail):
        # Bounds checking
        int_x, int_y = int(trail_x), int(trail_y)
        if not (0 <= int_y < max_rows and 0 <= int_x < max_cols):
            continue

        # Calculate position in trail (0.0 = oldest, 1.0 = newest)
        trail_pos = i / max(trail_length - 1, 1) if trail_length > 1 else 0

        # Skip very dim segments
        if trail_pos <= visibility_threshold:
            continue

        # Calculate progress for gradient (0.0 = head/bright, 1.0 = tail/dim)
        segments_from_head = trail_length - 1 - i
        trail_progress = segments_from_head / max(trail_length - 1, 1)

        # Look up color from pre-computed cache
        cache_index = min(int(trail_progress * (len(color_cache) - 1)), len(color_cache) - 1)
        bold_index = 1 if trail_pos > bold_threshold else 0  # 1=bold, 0=normal
        attr = color_cache[cache_index][bold_index]

        # Get character for this trail segment
        if char_selector:
            char = char_selector(i, trail_length, trail_progress)
        else:
            char = '·'  # Default trail character

        # Render
        try:
            stdscr.addstr(int_y, int_x, char, attr)
        except curses.error:
            pass  # Ignore boundary errors


def render_fading_trail(
    stdscr,
    trail: Deque[Tuple[float, float]],
    color_cache: List[Tuple[int, int]],
    brightness: float,
    max_rows: int,
    max_cols: int,
    trail_chars: Optional[List[str]] = None,
    max_visible: int = 5
):
    """Render a motion blur trail with brightness-based fading.

    Used by modes where trail brightness depends on particle state (Fireworks, Fireflies).
    Renders only the N most recent trail positions.

    Args:
        stdscr: Curses screen object
        trail: Deque of (x, y) position tuples
        color_cache: Pre-computed gradient cache [(attr_normal, attr_bold), ...]
        brightness: Current brightness of particle head (0.0-1.0)
        max_rows: Maximum row boundary
        max_cols: Maximum column boundary
        trail_chars: List of characters for trail progression (oldest to newest)
                    If None, uses ['.', '*'] for 2-level fade
        max_visible: Maximum number of trail positions to render

    Example:
        >>> # Fireflies motion blur
        >>> if firefly.char in ['+', '@']:  # Only render trail if bright
        ...     render_fading_trail(stdscr, firefly.trail, cache,
        ...                         firefly.brightness, 24, 80,
        ...                         trail_chars=['.', '*'])
    """
    import curses

    if trail_chars is None:
        trail_chars = ['.', '*']

    trail_length = len(trail)
    if trail_length == 0:
        return

    # Render only last max_visible positions
    start_idx = max(0, trail_length - max_visible)

    for idx in range(start_idx, trail_length):
        trail_x, trail_y = trail[idx]
        int_x, int_y = int(trail_x), int(trail_y)

        # Bounds checking
        if not (0 <= int_y < max_rows and 0 <= int_x < max_cols):
            continue

        # Calculate trail position (0.0 = oldest, 1.0 = newest in visible window)
        visible_length = trail_length - start_idx
        relative_idx = idx - start_idx
        trail_progress = relative_idx / max(visible_length - 1, 1) if visible_length > 1 else 0

        # Scale brightness by position and particle brightness
        trail_brightness = brightness * trail_progress * 0.20  # Keep trails dim

        # Look up color from cache
        color_idx = int(trail_brightness * (len(color_cache) - 1))
        color_idx = max(0, min(color_idx, len(color_cache) - 1))
        attr_normal, _ = color_cache[color_idx]

        # Select character based on position
        char_idx = min(relative_idx, len(trail_chars) - 1)
        char = trail_chars[char_idx]

        # Render
        try:
            stdscr.addstr(int_y, int_x, char, attr_normal)
        except curses.error:
            pass


def render_simple_trail(
    stdscr,
    trail: Deque[Tuple[float, float]],
    color_attr: int,
    max_rows: int,
    max_cols: int,
    char: str = '*',
    max_visible: int = 5
):
    """Render a simple trail with single color and character.

    Lightweight utility for basic trails without gradient effects.
    Used when consistent color/character is desired (e.g., rocket trails).

    Args:
        stdscr: Curses screen object
        trail: Deque of (x, y) position tuples
        color_attr: Curses color attribute (single color for entire trail)
        max_rows: Maximum row boundary
        max_cols: Maximum column boundary
        char: Character to use for all trail segments
        max_visible: Maximum number of trail positions to render

    Example:
        >>> # Simple rocket trail
        >>> render_simple_trail(stdscr, rocket.trail, rocket_attr,
        ...                     24, 80, char='*', max_visible=3)
    """
    import curses

    trail_length = len(trail)
    if trail_length == 0:
        return

    # Render only last max_visible positions
    start_idx = max(0, trail_length - max_visible)

    for idx in range(start_idx, trail_length):
        trail_x, trail_y = trail[idx]
        int_x, int_y = int(trail_x), int(trail_y)

        # Bounds checking
        if not (0 <= int_y < max_rows and 0 <= int_x < max_cols):
            continue

        # Render
        try:
            stdscr.addstr(int_y, int_x, char, color_attr)
        except curses.error:
            pass
