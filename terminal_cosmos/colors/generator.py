"""
Color generation utilities for terminal-cosmos.

Provides RGB color generation for animation sequences with support for
cosmic themes, traditional monochromatic schemes, and rainbow gradients.
Includes pre-defined color palettes optimized for terminal animations.

Key classes:
    - ColorGenerator: Static methods for color sequence generation

Key functions:
    - generate_cosmic_sequence: Generate themed color sequences
    - generate_rainbow_sequence: Generate rainbow color gradients
    - generate_monochromatic_gradient: Generate single-hue gradients
    - hsv_to_rgb: HSV to RGB color space conversion

Integration points:
    - Provides RGB colors to colors.curses_adapter for terminal conversion
    - Used by animation modes for particle and element coloring
    - Supports 18 color schemes including cosmic and traditional

Color palettes:
    - COSMIC_PALETTES: Space-themed colors (deep_space, stellar, nebula, etc.)
    - MONOCHROMATIC_PALETTES: Traditional single-hue schemes

All color generation is RGB-based and gets converted to terminal colors
by CursesColorAdapter for cross-terminal compatibility.

See Also:
    - colors.curses_adapter: Terminal color conversion and caching
    - modes.meteor_shower: Example usage for particle coloring
"""

import colorsys
import math
from typing import List, Tuple


class ColorGenerator:
    """Generates color sequences for terminal animations."""

    # Cosmic color palettes
    COSMIC_PALETTES = {
        'deep_space': [(0, 0, 20), (0, 0, 40), (20, 20, 60), (40, 40, 80)],
        'stellar': [(255, 255, 255), (255, 255, 200), (255, 200, 100), (200, 100, 50)],
        'nebula': [(100, 50, 150), (150, 75, 200), (200, 100, 255), (150, 200, 255)],
        'void': [(0, 0, 0), (20, 20, 20), (40, 40, 40), (60, 60, 60)],
        'meteor': [(255, 100, 0), (255, 150, 50), (255, 200, 100), (255, 255, 200)],
        'lightning': [(255, 255, 255), (200, 200, 255), (150, 150, 255), (100, 100, 200)],
        'matrix': [(0, 255, 0), (0, 200, 0), (0, 150, 0), (0, 100, 0)]
    }

    # Traditional color palettes from terminal-flow
    MONOCHROMATIC_PALETTES = {
        'red': [(139, 0, 0), (255, 0, 0), (255, 69, 0), (255, 140, 0)],
        'blue': [(0, 0, 139), (0, 0, 255), (30, 144, 255), (135, 206, 250)],
        'green': [(0, 100, 0), (0, 128, 0), (34, 139, 34), (144, 238, 144)],
        'yellow': [(184, 134, 11), (255, 215, 0), (255, 255, 0), (255, 255, 224)],
        'purple': [(75, 0, 130), (138, 43, 226), (147, 112, 219), (221, 160, 221)],
        'cyan': [(0, 139, 139), (0, 255, 255), (64, 224, 208), (175, 238, 238)],
        'gray': [(47, 79, 79), (105, 105, 105), (169, 169, 169), (211, 211, 211)],
        'pink': [(199, 21, 133), (255, 20, 147), (255, 105, 180), (255, 182, 193)],
        'orange': [(255, 69, 0), (255, 140, 0), (255, 165, 0), (255, 215, 0)]
    }

    @staticmethod
    def hsv_to_rgb(hue: float, saturation: float = 1.0, value: float = 1.0) -> Tuple[int, int, int]:
        """Convert HSV color to RGB.

        Args:
            hue: Hue value (0.0 to 1.0)
            saturation: Saturation value (0.0 to 1.0)
            value: Value/brightness (0.0 to 1.0)

        Returns:
            RGB tuple with values 0-255
        """
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        return (int(r * 255), int(g * 255), int(b * 255))

    @staticmethod
    def generate_rainbow_color(position: float, saturation: float = 1.0, value: float = 1.0) -> Tuple[int, int, int]:
        """Generate a rainbow color at a specific position.

        Args:
            position: Position in rainbow (0.0 to 1.0)
            saturation: Color saturation (0.0 to 1.0)
            value: Color brightness (0.0 to 1.0)

        Returns:
            RGB tuple with values 0-255
        """
        hue = position % 1.0
        return ColorGenerator.hsv_to_rgb(hue, saturation, value)

    @staticmethod
    def generate_rainbow_sequence(length: int, offset: float = 0.0,
                                 saturation: float = 1.0, value: float = 1.0) -> List[Tuple[int, int, int]]:
        """Generate a sequence of rainbow colors.

        Args:
            length: Number of colors to generate
            offset: Starting position offset (0.0 to 1.0)
            saturation: Color saturation (0.0 to 1.0)
            value: Color brightness (0.0 to 1.0)

        Returns:
            List of RGB tuples
        """
        if length <= 0:
            return []

        colors = []
        for i in range(length):
            position = (i / length + offset) % 1.0
            colors.append(ColorGenerator.generate_rainbow_color(position, saturation, value))

        return colors

    @staticmethod
    def generate_monochromatic_gradient(color_name: str, length: int, offset: float = 0.0) -> List[Tuple[int, int, int]]:
        """Generate a monochromatic gradient.

        Args:
            color_name: Name of the color palette
            length: Number of colors to generate
            offset: Position offset for animation (0.0 to 1.0)

        Returns:
            List of RGB tuples
        """
        if length <= 0:
            return []

        # Get base palette
        if color_name in ColorGenerator.COSMIC_PALETTES:
            base_colors = ColorGenerator.COSMIC_PALETTES[color_name]
        elif color_name in ColorGenerator.MONOCHROMATIC_PALETTES:
            base_colors = ColorGenerator.MONOCHROMATIC_PALETTES[color_name]
        else:
            # Default to blue if unknown
            base_colors = ColorGenerator.MONOCHROMATIC_PALETTES['blue']

        if not base_colors:
            return [(255, 255, 255)] * length

        colors = []
        for i in range(length):
            # Calculate position with offset
            position = (i / length + offset) % 1.0

            # Map position to palette
            palette_pos = position * (len(base_colors) - 1)
            base_idx = int(palette_pos)
            blend_factor = palette_pos - base_idx

            # Get two colors to blend
            color1 = base_colors[base_idx]
            color2 = base_colors[(base_idx + 1) % len(base_colors)]

            # Blend colors
            r = int(color1[0] * (1 - blend_factor) + color2[0] * blend_factor)
            g = int(color1[1] * (1 - blend_factor) + color2[1] * blend_factor)
            b = int(color1[2] * (1 - blend_factor) + color2[2] * blend_factor)

            colors.append((r, g, b))

        return colors

    @staticmethod
    def generate_cosmic_sequence(scheme: str, length: int, offset: float = 0.0,
                               intensity: float = 1.0) -> List[Tuple[int, int, int]]:
        """Generate a cosmic-themed color sequence.

        Args:
            scheme: Cosmic color scheme name
            length: Number of colors to generate
            offset: Animation offset (0.0 to 1.0)
            intensity: Color intensity multiplier (0.0 to 1.0)

        Returns:
            List of RGB tuples
        """
        if scheme == 'rainbow':
            return ColorGenerator.generate_rainbow_sequence(length, offset, 1.0, intensity)
        else:
            colors = ColorGenerator.generate_monochromatic_gradient(scheme, length, offset)
            # Apply intensity
            if intensity != 1.0:
                colors = [(int(r * intensity), int(g * intensity), int(b * intensity))
                         for r, g, b in colors]
            return colors

    @staticmethod
    def interpolate_color(color1: Tuple[int, int, int], color2: Tuple[int, int, int],
                         factor: float) -> Tuple[int, int, int]:
        """Interpolate between two colors.

        Args:
            color1: First RGB color
            color2: Second RGB color
            factor: Interpolation factor (0.0 to 1.0)

        Returns:
            Interpolated RGB color
        """
        factor = max(0.0, min(1.0, factor))
        r = int(color1[0] * (1 - factor) + color2[0] * factor)
        g = int(color1[1] * (1 - factor) + color2[1] * factor)
        b = int(color1[2] * (1 - factor) + color2[2] * factor)
        return (r, g, b)