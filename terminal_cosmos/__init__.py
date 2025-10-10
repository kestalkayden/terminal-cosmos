"""
Terminal Cosmos - Dynamic ASCII terminal animations.

A TUI application creating dynamic ASCII animations with anti-flicker
technology and 4 cosmic animation modes. Built on a modular framework
with particle systems, adaptive color management, and optimized rendering.

Modules:
    - core: Animation framework with anti-flicker double buffering
    - modes: 4 cosmic animation modes (meteor, lightning, space, matrix)
    - colors: RGB color generation and terminal adaptation
    - ui: User interface components
    - main: CLI application entry point

Features:
    - Anti-flicker double buffering for smooth animations
    - Mode-specific FPS optimization (8-30 FPS range)
    - 18 color schemes including cosmic and traditional palettes
    - 8-color and 256-color terminal support with automatic fallback
    - Particle-based physics systems for realistic effects
    - Safe terminal output with bounds checking

Usage:
    python -m terminal_cosmos <mode> [--fps N] [--color scheme] [--speed N]

See Also:
    - main.py: CLI interface and mode selection
    - core.animation_base: Core framework documentation
"""

__version__ = "0.1.0"
__author__ = "Terminal Cosmos Development Team"
__description__ = "A TUI application creating dynamic ASCII animations with 4 cosmic modes"