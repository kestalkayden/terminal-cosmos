"""Rain animation mode for terminal-cosmos."""

import random
import curses
from typing import List, Tuple
from ..core.animation_base import BaseAnimationMode
from ..colors.curses_adapter import CursesColorAdapter
from ..particles import RainDrop, ParticlePool
from ..utils.color_helpers import normalize_color_scheme, get_palette_color, clear_color_cache


# Rain-specific color palettes - calm, muted, gentle gradients
# Shared between Rain mode and Lightning Storm mode's rain drops
# Each palette has 4 color stops for gradient interpolation
RAIN_PALETTES = {
    'cyan': [(80, 100, 120), (100, 120, 140), (120, 140, 160), (140, 160, 180)],        # Pale blue-green water (default - kept muted)
    'blue': [(90, 110, 180), (110, 140, 210), (130, 160, 230), (150, 180, 245)],        # Vibrant water blue
    'green': [(100, 150, 120), (120, 180, 140), (140, 210, 160), (160, 230, 180)],      # Bright aqua-green
    'gray': [(100, 100, 100), (130, 130, 130), (160, 160, 160), (190, 190, 190)],       # Bright misty gray
    'purple': [(130, 100, 180), (150, 120, 210), (170, 140, 230), (190, 160, 245)],     # Vivid lavender
    'pink': [(180, 120, 150), (210, 140, 180), (230, 160, 200), (245, 180, 220)],       # Bright rose
    'yellow': [(170, 170, 110), (200, 200, 130), (220, 220, 150), (240, 240, 180)],     # Bright lemon
    'orange': [(140, 110, 80), (160, 130, 100), (180, 150, 120), (200, 170, 140)],      # Soft amber (kept as-is per request)
    'red': [(170, 100, 100), (200, 120, 120), (220, 140, 140), (240, 160, 160)]         # Bright coral-red
}

# Bright contrasting lightning colors for each rain scheme (used by Lightning Storm mode)
LIGHTNING_CONTRAST_COLORS = {
    'cyan': (255, 255, 255),      # Bright white for cyan rain
    'blue': (255, 255, 100),      # Bright yellow for blue rain
    'green': (255, 255, 255),     # Bright white for green rain
    'gray': (200, 200, 255),      # Bright blue-white for gray rain
    'purple': (255, 255, 150),    # Bright yellow-white for purple rain
    'pink': (255, 255, 255),      # Bright white for pink rain
    'yellow': (150, 150, 255),    # Bright blue for yellow rain
    'orange': (200, 230, 255),    # Bright cyan-white for orange rain
    'red': (255, 255, 255)        # Bright white for red rain
}


class Rain(BaseAnimationMode):
    """Pure rain animation with diagonal rainfall."""

    def __init__(self):
        super().__init__("Rain")
        # Set default color scheme for Rain mode
        self.color_scheme = 'cyan'
        self.current_color_index = self.available_colors.index('cyan')
        self.rain_drops: List[RainDrop] = []
        self.rain_timer = 0.0
        # Rain spawn rate
        self.rain_spawn_rate = 0.010  # Spawn every 0.010 seconds (100 per second)
        self.intense_mode = False
        self.color_adapter = CursesColorAdapter()
        self.rain_attr = 0  # Pre-calculated rain attribute
        # Particle pool for performance
        self.rain_pool: ParticlePool[RainDrop] = None

    def _get_rain_color(self) -> Tuple[int, int, int]:
        """Get rain color from palette (middle tone)."""
        return get_palette_color(RAIN_PALETTES, self.color_scheme, 'cyan', index=1)

    def initialize_mode_variables(self) -> None:
        """Initialize rain specific variables."""
        self.rain_drops.clear()
        self.rain_timer = 0.0
        self.color_adapter.initialize_colors()

        # Pre-calculate rain attribute from palette
        rain_color = self._get_rain_color()
        self.rain_attr = self.color_adapter.get_color_attr(rain_color, bold=False)

        # Initialize particle pool (create 200 reusable RainDrop objects)
        self.rain_pool = ParticlePool(RainDrop, size=200, rain_attr=self.rain_attr)

    def set_intense_mode(self, intense: bool):
        """Set intense mode for more dramatic rain."""
        self.intense_mode = intense
        if intense:
            self.rain_spawn_rate = 0.006  # Intense rain - spawn every 0.006 seconds (167 per second)
        else:
            self.rain_spawn_rate = 0.010  # Normal rain - spawn every 0.010 seconds (100 per second)

    def update_animation_state(self, update_interval: float) -> None:
        """Update rain animation state."""
        dt = update_interval

        # Pre-calculate movement multiplier once
        movement_multiplier = 20.0  # Fixed multiplier for consistent rain speed

        # Update rain drops using particle pool
        i = 0
        while i < len(self.rain_pool.active):
            drop = self.rain_pool.active[i]
            drop.update(dt, movement_multiplier)
            if drop.is_off_screen(self.max_rows, self.max_cols):
                # Return to pool instead of deleting
                self.rain_pool.release(self.rain_pool.active.pop(i))
            else:
                i += 1

        # Spawn new rain drops
        self.rain_timer += dt

        while self.rain_timer >= self.rain_spawn_rate:
            self._spawn_rain_drop()
            self.rain_timer -= self.rain_spawn_rate

    def _spawn_rain_drop(self) -> None:
        """Spawn a new rain drop using particle pool."""
        # Get object from pool
        drop = self.rain_pool.acquire()
        if not drop:
            return  # Pool exhausted, skip spawn to maintain performance

        # Smart dual spawn pattern for diagonal rain coverage
        if random.random() < 0.7:
            # Top edge spawn (70% of drops)
            start_x = random.uniform(-2, self.max_cols + 2)
            start_y = random.uniform(-1, -0.1)
        else:
            # Right edge spawn (30% of drops) - covers bottom-right area
            start_x = random.uniform(self.max_cols, self.max_cols + 5)
            start_y = random.uniform(0, self.max_rows * 0.7)  # Don't spawn too low

        drop.reset(start_x, start_y)
        self.rain_pool.active.append(drop)

    def on_color_change(self) -> None:
        """Called when user presses 'c' to cycle colors."""
        # Clear color adapter cache AND reset counter
        clear_color_cache(self.color_adapter)

        # Regenerate rain attribute with new color
        rain_color = self._get_rain_color()
        self.rain_attr = self.color_adapter.get_color_attr(rain_color, bold=False)

        # Update all existing drops with new color
        for drop in self.rain_pool.pool:
            drop.attr = self.rain_attr
        for drop in self.rain_pool.active:
            drop.attr = self.rain_attr

    def draw_frame(self) -> None:
        """Draw the rain frame."""
        # Draw rain drops
        for drop in self.rain_pool.active:
            row, col = int(drop.y), int(drop.x)
            try:
                self.stdscr.addstr(row, col, drop.get_char(), drop.attr)
            except curses.error:
                pass