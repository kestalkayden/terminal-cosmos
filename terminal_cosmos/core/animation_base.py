"""
Base animation mode class for terminal-cosmos.

Provides the core framework for all animation modes with anti-flicker
double buffering, color management, and safe terminal output. Each mode
inherits from BaseAnimationMode and implements three key methods:
initialize_mode_variables(), update_animation_state(), and draw_frame().

Key classes:
    - BaseAnimationMode: Abstract base with curses setup and animation loop

Key functions:
    - setup_curses: Configures terminal with anti-flicker optimizations
    - run: Main animation loop with double buffering
    - safe_addstr: Bounds-checked terminal output

Integration points:
    - Uses ColorGenerator for RGB color sequences
    - Uses CursesColorAdapter for terminal color conversion
    - Provides framework for all modes in modes/ package

See Also:
    - modes.meteor_shower: Example particle-based implementation
    - colors.generator: Color generation system
    - main.py: Application entry point and mode instantiation
"""

import curses
import time
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple


class BaseAnimationMode(ABC):
    """Abstract base class for all animation modes in terminal-cosmos."""

    def __init__(self, mode_name: str) -> None:
        """Initialize the base animation mode.

        Args:
            mode_name: Name of the animation mode
        """
        self.mode_name = mode_name
        self.stdscr = None
        self.max_rows = 0
        self.max_cols = 0
        self.update_interval = 0.1
        self.last_update_time = 0.0
        self.color_scheme = None  # Will be set by mode or CLI arg
        self.running = True

        # Mode switching
        self.display_name = mode_name
        self.current_mode = self._get_cli_mode_name(mode_name)
        self.next_mode = None

        # Color system
        self.colors_initialized = False
        self.has_256_colors = False
        self.color_palette = []

        # Available color schemes (9 monochrome options)
        self.available_colors = ['red', 'blue', 'green', 'yellow', 'purple', 'cyan', 'gray', 'pink', 'orange']
        self.current_color_index = 0

        # Content bounds for centering
        self.content_bounds = {
            'start_row': 0,
            'end_row': 0,
            'content_width': 0,
            'content_height': 0,
            'start_col': 0,
            'center_row': 0,
            'center_col': 0
        }

    def setup_curses(self, stdscr) -> None:
        """Setup curses with anti-flicker optimizations."""
        self.stdscr = stdscr

        # Hide cursor
        curses.curs_set(0)

        # Non-blocking input with minimal timeout
        stdscr.nodelay(True)
        stdscr.timeout(1)

        # Get screen dimensions
        self.max_rows, self.max_cols = stdscr.getmaxyx()

        # Setup colors
        self._initialize_colors()

        # Calculate content bounds for centering
        self._calculate_content_bounds()

    def _initialize_colors(self) -> None:
        """Initialize color system with terminal capability detection."""
        if not curses.has_colors():
            self.colors_initialized = False
            return

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

        # Pre-compute color palette for performance
        self._generate_color_palette()

    def _generate_color_palette(self) -> None:
        """Generate pre-computed color palette for smooth animations."""
        # This will be filled by color system implementation
        # For now, create basic color pairs
        if self.colors_initialized:
            # Create basic color pairs
            for i in range(1, min(8, curses.COLOR_PAIRS)):
                try:
                    curses.init_pair(i, i, -1)  # Foreground color, default background
                except curses.error:
                    pass

    def _calculate_content_bounds(self) -> None:
        """Calculate content bounds for dynamic content centering."""
        # For dynamic content, use full screen as bounds
        self.content_bounds.update({
            'start_row': 0,
            'end_row': self.max_rows - 1,
            'content_width': self.max_cols,
            'content_height': self.max_rows,
            'start_col': 0,
            'center_row': self.max_rows // 2,
            'center_col': self.max_cols // 2
        })

    def run(self, stdscr, update_interval: float = 0.1,
            color_scheme: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Main animation loop with anti-flicker double buffering.

        Args:
            stdscr: Curses screen object
            update_interval: Time between frame updates in seconds
            color_scheme: Color scheme to use

        Returns:
            Dictionary with next mode information if mode switch requested
        """
        self.setup_curses(stdscr)

        self.update_interval = update_interval
        if color_scheme:
            # Normalize grey to gray for consistency
            normalized_color = 'gray' if color_scheme == 'grey' else color_scheme
            if normalized_color in self.available_colors:
                self.color_scheme = normalized_color
                self.current_color_index = self.available_colors.index(normalized_color)

        # Initialize mode-specific variables
        self.initialize_mode_variables()

        self.last_update_time = time.time()

        try:
            while self.running:
                current_time = time.time()

                # Handle input
                self._handle_input()

                # Update animation state if enough time has passed
                if current_time - self.last_update_time >= self.update_interval:
                    self.update_animation_state(self.update_interval)
                    self.last_update_time = current_time

                # Clear screen gently (anti-flicker technique)
                stdscr.erase()

                # Draw the current frame
                self.draw_frame()

                # Double buffering: prepare changes without refreshing
                stdscr.noutrefresh()

                # Actually update the screen (anti-flicker technique)
                curses.doupdate()

                # Frame rate control
                time.sleep(max(0.001, self.update_interval))

        except KeyboardInterrupt:
            pass

        # Return next mode if mode switching was requested
        if self.next_mode:
            return {'next_mode': self.next_mode}
        return None

    def _handle_input(self) -> None:
        """Handle user input for controls and mode switching."""
        try:
            key = self.stdscr.getch()

            if key == ord('q') or key == ord('Q') or key == 27:  # ESC
                self.running = False
            elif key == ord('c') or key == ord('C'):
                # Cycle to next color scheme
                self.current_color_index = (self.current_color_index + 1) % len(self.available_colors)
                self.color_scheme = self.available_colors[self.current_color_index]
                self.on_color_change()
                self.stdscr.clear()  # Clear screen to prevent ghosting
            elif key == ord('m') or key == ord('M'):
                # Switch to next animation mode
                self._switch_to_next_mode()
            elif key == curses.KEY_RESIZE:
                # Handle terminal resize
                self._handle_resize()
            elif key == curses.KEY_LEFT:
                # Future: Navigate (reserved for potential file/content switching)
                pass
            elif key == curses.KEY_RIGHT:
                # Future: Navigate (reserved for potential file/content switching)
                pass

        except curses.error:
            # No input available
            pass

    def _get_cli_mode_name(self, display_name: str) -> str:
        """Convert display name to CLI mode name."""
        name_mapping = {
            'Meteor Shower': 'meteor',
            'Lightning Storm': 'lightning',
            'Rain': 'rain',
            'Space': 'space',
            'Matrix': 'matrix',
            'Warp': 'warp',
            'Fireworks': 'fireworks',
            'Fireflies': 'fireflies'
        }
        return name_mapping.get(display_name, display_name.lower())

    def _switch_to_next_mode(self) -> None:
        """Switch to the next animation mode."""
        modes = ['meteor', 'lightning', 'rain', 'space', 'matrix', 'warp', 'fireworks', 'fireflies']
        current_mode = getattr(self, 'current_mode', 'meteor')

        if current_mode in modes:
            current_idx = modes.index(current_mode)
            next_idx = (current_idx + 1) % len(modes)
            self.next_mode = modes[next_idx]
            self.running = False  # Exit current mode

    def safe_addstr(self, row: int, col: int, text: str, attr: int = 0) -> None:
        """Safely add string to screen with bounds checking."""
        if (0 <= row < self.max_rows and
            0 <= col < self.max_cols and
            len(text) > 0):
            try:
                # Truncate text if it would exceed screen width
                max_len = self.max_cols - col - 1
                if len(text) > max_len:
                    text = text[:max_len]
                self.stdscr.addstr(row, col, text, attr)
            except curses.error:
                # Ignore errors from attempting to write at screen boundaries
                pass

    def on_color_change(self) -> None:
        """Called when color scheme changes via 'c' key. Override in subclasses to regenerate colors."""
        pass

    def _handle_resize(self) -> None:
        """Handle terminal resize event."""
        # Update terminal dimensions
        self.max_rows, self.max_cols = self.stdscr.getmaxyx()

        # Recalculate content bounds
        self._calculate_content_bounds()

        # Clear screen for clean redraw
        self.stdscr.clear()

        # Allow modes to handle resize-specific logic
        self.on_resize()

    def on_resize(self) -> None:
        """Called when terminal is resized. Override in subclasses for resize-specific logic."""
        pass

    @abstractmethod
    def initialize_mode_variables(self) -> None:
        """Initialize mode-specific variables. Must be implemented by subclasses."""
        pass

    @abstractmethod
    def update_animation_state(self, update_interval: float) -> None:
        """Update animation state for next frame. Must be implemented by subclasses.

        Args:
            update_interval: Time since last update
        """
        pass

    @abstractmethod
    def draw_frame(self) -> None:
        """Draw the current animation frame. Must be implemented by subclasses."""
        pass