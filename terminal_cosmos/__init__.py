"""
Terminal Cosmos - Dynamic ASCII terminal animations.

A TUI application creating dynamic ASCII animations with anti-flicker
technology and 8 animation modes. Built on a modular framework
with particle systems, adaptive color management, and optimized rendering.

Modules:
    - core: Animation framework with anti-flicker double buffering
    - modes: 8 animation modes (meteor, lightning, rain, space, matrix, warp, fireworks, fireflies)
    - colors: RGB color generation and terminal adaptation
    - ui: User interface components
    - main: CLI application entry point

Features:
    - Anti-flicker double buffering for smooth animations
    - Mode-specific FPS (matrix 10, fireworks 30, others 60)
    - 18 color schemes including cosmic and traditional palettes
    - 8-color and 256-color terminal support with automatic fallback
    - Particle-based physics systems for realistic effects
    - Safe terminal output with bounds checking

Usage:
    python -m terminal_cosmos [--mode NAME] [--color SCHEME] [--intense]

See Also:
    - main.py: CLI interface and mode selection
    - core.animation_base: Core framework documentation
"""

__version__ = "0.1.0"
__author__ = "Terminal Cosmos Development Team"
__description__ = "A TUI application creating dynamic ASCII animations with 4 cosmic modes"