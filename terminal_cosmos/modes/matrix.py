"""Matrix digital rain animation mode for terminal-cosmos."""

import random
import time
import curses
from typing import List
from ..core.animation_base import BaseAnimationMode
from ..colors.curses_adapter import CursesColorAdapter
from ..utils.color_helpers import clear_color_cache


# Matrix mode color palettes - 9 digital rain themes
MATRIX_PALETTES = {
    'green': {
        'head': (255, 255, 255),      # White head
        'bright': (150, 255, 150),    # Bright green
        'medium': (80, 220, 80),      # Medium green
        'dark': (40, 150, 40),        # Dark green
        'darker': (20, 100, 20)       # Darker green
    },
    'blue': {
        'head': (255, 255, 255),      # White head
        'bright': (150, 200, 255),    # Bright blue
        'medium': (80, 150, 255),     # Medium blue
        'dark': (40, 100, 200),       # Dark blue
        'darker': (20, 60, 150)       # Darker blue
    },
    'red': {
        'head': (255, 255, 255),      # White head
        'bright': (255, 150, 150),    # Bright red
        'medium': (255, 80, 80),      # Medium red
        'dark': (200, 40, 40),        # Dark red
        'darker': (150, 20, 20)       # Darker red
    },
    'cyan': {
        'head': (255, 255, 255),      # White head
        'bright': (150, 255, 255),    # Bright cyan
        'medium': (80, 220, 220),     # Medium cyan
        'dark': (40, 150, 150),       # Dark cyan
        'darker': (20, 100, 100)      # Darker cyan
    },
    'yellow': {
        'head': (255, 255, 255),      # White head
        'bright': (255, 255, 150),    # Bright yellow
        'medium': (255, 255, 80),     # Medium yellow
        'dark': (200, 200, 40),       # Dark yellow
        'darker': (150, 150, 20)      # Darker yellow
    },
    'purple': {
        'head': (255, 255, 255),      # White head
        'bright': (220, 150, 255),    # Bright purple
        'medium': (180, 80, 255),     # Medium purple
        'dark': (130, 40, 200),       # Dark purple
        'darker': (90, 20, 150)       # Darker purple
    },
    'pink': {
        'head': (255, 255, 255),      # White head
        'bright': (255, 150, 220),    # Bright pink
        'medium': (255, 80, 180),     # Medium pink
        'dark': (200, 40, 130),       # Dark pink
        'darker': (150, 20, 90)       # Darker pink
    },
    'orange': {
        'head': (255, 255, 255),      # White head
        'bright': (255, 200, 150),    # Bright orange
        'medium': (255, 160, 80),     # Medium orange
        'dark': (200, 120, 40),       # Dark orange
        'darker': (150, 80, 20)       # Darker orange
    },
    'gray': {
        'head': (255, 255, 255),      # White head
        'bright': (220, 220, 220),    # Bright gray
        'medium': (160, 160, 160),    # Medium gray
        'dark': (100, 100, 100),      # Dark gray
        'darker': (60, 60, 60)        # Darker gray
    }
}


class MatrixColumn:
    """Simple column with falling binary trail."""

    # Matrix character set - cached to avoid duplication
    MATRIX_CHARS = [
        # Katakana characters
        'ア', 'イ', 'ウ', 'エ', 'オ', 'カ', 'キ', 'ク', 'ケ', 'コ',
        'サ', 'シ', 'ス', 'セ', 'ソ', 'タ', 'チ', 'ツ', 'テ', 'ト',
        'ナ', 'ニ', 'ヌ', 'ネ', 'ノ', 'ハ', 'ヒ', 'フ', 'ヘ', 'ホ',
        'マ', 'ミ', 'ム', 'メ', 'モ', 'ヤ', 'ユ', 'ヨ', 'ラ', 'リ',
        'ル', 'レ', 'ロ', 'ワ', 'ヲ', 'ン',
        # Numbers and symbols
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
        'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
        'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T',
        'U', 'V', 'W', 'X', 'Y', 'Z'
    ]

    FALLBACK_CHARS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    def __init__(self, x: int, max_rows: int, intense_mode: bool = False):
        self.x = x
        self.max_rows = max_rows
        self.trail_length = random.randint(15, 25)
        self.y = -self.trail_length  # Start above screen
        self.speed = random.uniform(6, 12)  # Characters per second

        # Create characters with Unicode fallback handling
        self.characters = []
        self.display_characters = []

        for _ in range(self.trail_length):
            char = random.choice(self.MATRIX_CHARS)
            self.characters.append(char)
            # Pre-compute safe display character
            try:
                char.encode('utf-8')
                self.display_characters.append(char)  # Use katakana directly
            except UnicodeEncodeError:
                self.display_characters.append(random.choice(self.FALLBACK_CHARS))
        self.active = True
        self.wait_time = 0
        self.wait_delay = 0.4 if intense_mode else 0.8  # 20% faster spawning (reduced delay)
        self.initial_spawn = True  # Track if this is initial spawn

        # Head randomization timing
        self.head_randomize_timer = 0.0
        self.head_randomize_interval = 0.2  # Every 0.2 seconds
        self.head_randomize_count = 0
        self.head_randomize_cycle_duration = 0.8  # 0.8 second cycle

    def update(self, dt: float):
        """Update column position."""
        if not self.active:
            # Waiting period (either initial stagger or after trail cleared)
            self.wait_time -= dt
            if self.wait_time <= 0:
                if self.initial_spawn:
                    # First activation - start trail
                    self.active = True
                    self.initial_spawn = False
                else:
                    # Normal reset after completion
                    self.reset()
            return

        # Move trail down
        self.y += self.speed * dt

        # Head randomization timing - continuously every 0.2s
        self.head_randomize_timer += dt
        if self.head_randomize_timer >= self.head_randomize_interval:
            # Randomize only the head character (last in trail)
            head_idx = self.trail_length - 1
            char = random.choice(self.MATRIX_CHARS)
            self.characters[head_idx] = char
            # Update safe display character
            try:
                char.encode('utf-8')
                self.display_characters[head_idx] = char
            except UnicodeEncodeError:
                self.display_characters[head_idx] = random.choice(self.FALLBACK_CHARS)

            self.head_randomize_timer = 0.0

        # Check if trail has completely cleared the screen
        if self.y > self.max_rows:
            self.active = False
            self.wait_time = self.wait_delay

    def reset(self):
        """Reset trail for new cycle."""
        self.trail_length = random.randint(15, 25)
        self.y = -self.trail_length
        self.speed = random.uniform(6, 12)

        # Safely create both character arrays
        self.characters = []
        self.display_characters = []

        for _ in range(self.trail_length):
            char = random.choice(self.MATRIX_CHARS)
            self.characters.append(char)
            # Pre-compute safe display character
            try:
                char.encode('utf-8')
                self.display_characters.append(char)  # Use katakana directly
            except UnicodeEncodeError:
                self.display_characters.append(random.choice(self.FALLBACK_CHARS))

        self.active = True
        self.wait_time = 0
        self.initial_spawn = False  # No longer initial spawn after reset

        # Reset head randomization timing
        self.head_randomize_timer = 0.0
        self.head_randomize_count = 0

    def randomize_char_at_index(self, index: int):
        """Randomize character at specific index in trail."""
        if 0 <= index < self.trail_length:
            char = random.choice(self.MATRIX_CHARS)
            self.characters[index] = char
            # Update safe display character
            try:
                char.encode('utf-8')
                self.display_characters[index] = char
            except UnicodeEncodeError:
                self.display_characters[index] = random.choice(self.FALLBACK_CHARS)

    def get_visible_chars(self):
        """Get visible characters with positions and intensities."""
        if not self.active:
            return []

        visible = []
        for i, char in enumerate(self.display_characters):
            # Fix positioning: only render when actual position is >= 0
            actual_y = self.y + i
            char_y = int(actual_y)
            if actual_y >= 0 and char_y < self.max_rows:
                # Head is at the bottom (highest index), tail at top
                if i == self.trail_length - 1:
                    intensity = 1.0  # White head (bottommost)
                    is_head = True
                elif i == self.trail_length - 2:
                    intensity = 0.7  # Medium green (second from bottom)
                    is_head = False
                else:
                    # Gradient from dark green (top) to medium green (toward bottom)
                    progress = i / (self.trail_length - 3) if self.trail_length > 2 else 0
                    intensity = 0.2 + progress * 0.5  # Dark to medium as we go down
                    is_head = False

                visible.append((char_y, char, intensity, is_head))
        return visible


class Matrix(BaseAnimationMode):
    """Matrix-style digital rain animation."""

    def __init__(self):
        super().__init__("Matrix")
        self.columns: List[MatrixColumn] = []
        self.intense_mode = False
        self.color_adapter = CursesColorAdapter()

        # Color scheme setup
        self.available_colors = ['green', 'blue', 'red', 'cyan', 'yellow', 'purple', 'pink', 'orange', 'gray']
        self.color_scheme = 'green'  # Default: classic Matrix green
        self.current_color_index = self.available_colors.index('green')
        self.current_palette = MATRIX_PALETTES['green']

        # Screen-wide trail randomization
        self.trail_flicker_timer = 0.0
        self.trail_flicker_interval = 0.15  # Every 0.15 seconds
        self.trail_flicker_count = 40  # Change 40 characters at once

    def set_intense_mode(self, intense: bool) -> None:
        """Set intense mode for faster trail spawning."""
        self.intense_mode = intense

    def on_color_change(self):
        """Handle color scheme changes."""
        # Update to new palette
        self.current_palette = MATRIX_PALETTES[self.color_scheme]

        # Clear color adapter cache and reset counter
        clear_color_cache(self.color_adapter)

        # Regenerate pre-computed intensity attributes with new palette
        palette = self.current_palette
        self.intensity_attrs = {
            'head': self.color_adapter.get_color_attr(palette['head'], bold=True),
            'bright': self.color_adapter.get_color_attr(palette['bright'], bold=True),
            'medium': self.color_adapter.get_color_attr(palette['medium'], bold=False),
            'dark': self.color_adapter.get_color_attr(palette['dark'], bold=False),
            'darker': self.color_adapter.get_color_attr(palette['darker'], bold=False)
        }

    def initialize_mode_variables(self) -> None:
        """Initialize matrix mode variables."""
        self.columns.clear()
        self.color_adapter.initialize_colors()

        # Pre-compute color attributes for all 5 intensity levels
        # This eliminates 3,000+ color generations per second
        palette = self.current_palette
        self.intensity_attrs = {
            'head': self.color_adapter.get_color_attr(palette['head'], bold=True),
            'bright': self.color_adapter.get_color_attr(palette['bright'], bold=True),
            'medium': self.color_adapter.get_color_attr(palette['medium'], bold=False),
            'dark': self.color_adapter.get_color_attr(palette['dark'], bold=False),
            'darker': self.color_adapter.get_color_attr(palette['darker'], bold=False)
        }

        # Create one column per every 2 screen columns (50% density)
        for x in range(0, self.max_cols, 2):
            column = MatrixColumn(x, self.max_rows, self.intense_mode)
            # Stagger initial starts over 4-5 seconds
            column.y = random.randint(-column.trail_length * 2, -column.trail_length)
            column.active = False  # Start inactive
            column.wait_time = random.uniform(0, 5.0)  # Random delay 0-5 seconds
            self.columns.append(column)

    def update_animation_state(self, update_interval: float) -> None:
        """Update animation state."""
        dt = update_interval

        for column in self.columns:
            column.update(dt)

        # Screen-wide trail character flickering
        self.trail_flicker_timer += dt
        if self.trail_flicker_timer >= self.trail_flicker_interval:
            # Collect all active columns with visible trails
            active_columns = [col for col in self.columns if col.active and col.trail_length > 1]

            if active_columns:
                # Build list of all possible (column, char_index) pairs
                flicker_candidates = []
                for col in active_columns:
                    # Exclude head (last index)
                    for char_idx in range(col.trail_length - 1):
                        flicker_candidates.append((col, char_idx))

                # Randomly sample 40 unique characters to flicker
                if flicker_candidates:
                    sample_size = min(self.trail_flicker_count, len(flicker_candidates))
                    selections = random.sample(flicker_candidates, sample_size)
                    for column, char_index in selections:
                        column.randomize_char_at_index(char_index)

            self.trail_flicker_timer = 0.0

    def draw_frame(self) -> None:
        """Draw the matrix frame."""
        for column in self.columns:
            visible_chars = column.get_visible_chars()

            for row, char, intensity, is_head in visible_chars:
                # Use pre-computed attributes - no color generation needed
                if is_head:
                    attr = self.intensity_attrs['head']
                elif intensity >= 0.7:
                    attr = self.intensity_attrs['bright']
                elif intensity >= 0.5:
                    attr = self.intensity_attrs['medium']
                elif intensity >= 0.3:
                    attr = self.intensity_attrs['dark']
                else:
                    attr = self.intensity_attrs['darker']

                self.safe_addstr(row, column.x, char, attr)