"""
Curses color adaptation for terminal-cosmos.

Converts RGB colors to terminal-compatible curses attributes with support
for both 8-color and 256-color terminals. Includes caching system for
performance and automatic fallback for limited terminal capabilities.

Key classes:
    - CursesColorAdapter: RGB to curses color conversion with caching
    - CursesRainbowSequence: Optimized rainbow color sequence generator

Key functions:
    - initialize_colors: Set up curses color system
    - rgb_to_color_pair: Convert RGB to cached curses color pair
    - get_color_attr: Get complete curses attribute with bold option
    - _rgb_to_256_color: Map RGB to 256-color palette index

Integration points:
    - Consumes RGB colors from colors.generator.ColorGenerator
    - Provides curses attributes to animation modes for rendering
    - Used by all modes for terminal-compatible color display

Features:
    - Automatic 256-color vs 8-color detection
    - Color pair caching for performance
    - Graceful fallback for unsupported terminals
    - Euclidean distance color matching for 8-color mode

The adapter handles all terminal color complexity, allowing animation modes
to work with simple RGB values while ensuring compatibility across terminals.

See Also:
    - colors.generator: RGB color generation
    - core.animation_base: Framework using color attributes
"""

import curses
import math
from typing import Dict, Tuple, List, Optional


class CursesColorAdapter:
    """Adapts RGB colors to terminal curses color capabilities."""

    def __init__(self):
        """Initialize the color adapter."""
        self.colors_initialized = False
        self.has_256_colors = False
        self.color_pair_cache: Dict[Tuple[int, int, int], int] = {}
        self.next_color_pair = 1

        # Standard 8-color palette for fallback
        self.standard_colors = [
            (0, 0, 0),       # Black
            (128, 0, 0),     # Red
            (0, 128, 0),     # Green
            (128, 128, 0),   # Yellow
            (0, 0, 128),     # Blue
            (128, 0, 128),   # Magenta
            (0, 128, 128),   # Cyan
            (192, 192, 192), # White
        ]

    def initialize_colors(self) -> bool:
        """Initialize curses color system.

        Returns:
            True if colors were successfully initialized
        """
        if not curses.has_colors():
            return False

        try:
            curses.start_color()

            # Check for 256-color support
            self.has_256_colors = curses.COLORS >= 256

            # Use default colors if supported for transparent backgrounds
            if hasattr(curses, 'use_default_colors'):
                try:
                    curses.use_default_colors()
                except curses.error:
                    pass

            self.colors_initialized = True
            return True

        except curses.error:
            return False

    def _find_closest_standard_color(self, rgb: Tuple[int, int, int]) -> int:
        """Find closest standard 8-color match using Euclidean distance.

        Args:
            rgb: RGB color tuple

        Returns:
            Curses color constant (0-7)
        """
        r, g, b = rgb
        min_distance = float('inf')
        closest_color = 0

        for i, (sr, sg, sb) in enumerate(self.standard_colors):
            # Euclidean distance in RGB space
            distance = math.sqrt((r - sr)**2 + (g - sg)**2 + (b - sb)**2)
            if distance < min_distance:
                min_distance = distance
                closest_color = i

        return closest_color

    def _rgb_to_256_color(self, rgb: Tuple[int, int, int]) -> int:
        """Convert RGB to 256-color palette index.

        Args:
            rgb: RGB color tuple

        Returns:
            256-color palette index
        """
        r, g, b = rgb

        # Convert to 6x6x6 color cube (colors 16-231)
        # Each component is mapped to 0-5 range
        if r == g == b:
            # Grayscale colors (232-255) - 24 shades of gray
            gray_value = r
            if gray_value < 8:
                return 16  # Black
            elif gray_value > 248:
                return 231  # White
            else:
                # Map gray_value (8-248) to grayscale indices (232-255)
                # 240 possible values mapped to 24 grayscale slots (0-23)
                gray_index = min(23, ((gray_value - 8) * 24) // 240)
                return 232 + gray_index
        else:
            # Color cube
            r_cube = (r * 5) // 255
            g_cube = (g * 5) // 255
            b_cube = (b * 5) // 255
            return 16 + (36 * r_cube) + (6 * g_cube) + b_cube

    def rgb_to_color_pair(self, rgb: Tuple[int, int, int]) -> int:
        """Get or create a color pair for the given RGB color.

        Args:
            rgb: RGB color tuple

        Returns:
            Curses color pair number
        """
        if not self.colors_initialized:
            return 0

        # Check cache first
        if rgb in self.color_pair_cache:
            return self.color_pair_cache[rgb]

        # Avoid using too many color pairs
        if self.next_color_pair >= curses.COLOR_PAIRS:
            # Reuse existing pairs by cycling
            self.next_color_pair = 1
            self.color_pair_cache.clear()

        try:
            if self.has_256_colors:
                # Use 256-color mode
                color_index = self._rgb_to_256_color(rgb)
                curses.init_pair(self.next_color_pair, color_index, -1)
            else:
                # Fallback to 8-color mode
                color_index = self._find_closest_standard_color(rgb)
                curses.init_pair(self.next_color_pair, color_index, -1)

            # Cache the result
            self.color_pair_cache[rgb] = self.next_color_pair
            pair_number = self.next_color_pair
            self.next_color_pair += 1

            return pair_number

        except curses.error:
            # Fall back to default color
            return 0

    def get_color_attr(self, rgb: Tuple[int, int, int], bold: bool = True) -> int:
        """Get curses color attribute for the given RGB color.

        Args:
            rgb: RGB color tuple
            bold: Whether to apply bold attribute

        Returns:
            Curses color attribute
        """
        if not self.colors_initialized:
            return curses.A_BOLD if bold else 0

        color_pair = self.rgb_to_color_pair(rgb)
        attr = curses.color_pair(color_pair)

        if bold:
            attr |= curses.A_BOLD

        return attr

    def get_bg_color_attr(self, rgb: Tuple[int, int, int]) -> int:
        """Get curses color attribute with both foreground and background set to same color.

        This is useful for filling areas with solid color blocks using space characters.

        Args:
            rgb: RGB color tuple

        Returns:
            Curses color attribute with matching fg and bg
        """
        if not self.colors_initialized:
            return 0

        # Create cache key for bg colors
        cache_key = ('bg', rgb)

        # Check cache first
        if cache_key in self.color_pair_cache:
            return curses.color_pair(self.color_pair_cache[cache_key])

        # Avoid using too many color pairs
        if self.next_color_pair >= curses.COLOR_PAIRS:
            self.next_color_pair = 1
            self.color_pair_cache.clear()

        try:
            if self.has_256_colors:
                color_index = self._rgb_to_256_color(rgb)
                # Set both foreground AND background to same color
                curses.init_pair(self.next_color_pair, color_index, color_index)
            else:
                color_index = self._find_closest_standard_color(rgb)
                curses.init_pair(self.next_color_pair, color_index, color_index)

            # Cache the result
            self.color_pair_cache[cache_key] = self.next_color_pair
            pair_number = self.next_color_pair
            self.next_color_pair += 1

            return curses.color_pair(pair_number)

        except curses.error:
            return 0

    def create_color_sequence_attrs(self, colors: List[Tuple[int, int, int]],
                                  bold: bool = True) -> List[int]:
        """Create a list of curses attributes for a color sequence.

        Args:
            colors: List of RGB color tuples
            bold: Whether to apply bold attribute

        Returns:
            List of curses color attributes
        """
        return [self.get_color_attr(color, bold) for color in colors]


class CursesRainbowSequence:
    """Optimized rainbow color sequence generator for curses."""

    def __init__(self, adapter: CursesColorAdapter, length: int = 360):
        """Initialize rainbow sequence.

        Args:
            adapter: Color adapter instance
            length: Number of colors in the sequence
        """
        self.adapter = adapter
        self.length = length
        self._cached_attrs: Optional[List[int]] = None

    def get_attrs(self, offset: float = 0.0, bold: bool = True) -> List[int]:
        """Get cached rainbow color attributes.

        Args:
            offset: Animation offset (0.0 to 1.0)
            bold: Whether to apply bold attribute

        Returns:
            List of curses color attributes
        """
        if self._cached_attrs is None:
            from .generator import ColorGenerator
            colors = ColorGenerator.generate_rainbow_sequence(self.length)
            self._cached_attrs = self.adapter.create_color_sequence_attrs(colors, bold)

        if offset == 0.0:
            return self._cached_attrs

        # Apply offset by rotating the sequence
        offset_steps = int(offset * self.length)
        return (self._cached_attrs[offset_steps:] +
                self._cached_attrs[:offset_steps])

    def get_attr_at_position(self, position: float, bold: bool = True) -> int:
        """Get color attribute at a specific position.

        Args:
            position: Position in sequence (0.0 to 1.0)
            bold: Whether to apply bold attribute

        Returns:
            Curses color attribute
        """
        attrs = self.get_attrs(bold=bold)
        index = int(position * len(attrs)) % len(attrs)
        return attrs[index]