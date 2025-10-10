"""Lightning storm animation mode for terminal-cosmos."""

import random
import math
import curses
from typing import List, Dict, Any, Tuple
from ..core.animation_base import BaseAnimationMode
from ..colors.generator import ColorGenerator
from ..colors.curses_adapter import CursesColorAdapter
from ..particles import RainDrop, ParticlePool
from ..utils.color_helpers import get_palette_color, clear_color_cache
from .rain import RAIN_PALETTES, LIGHTNING_CONTRAST_COLORS


class LightningBranch:
    """Represents a lightning branch."""

    def __init__(self, start_x: int, start_y: int, end_x: int, end_y: int,
                 intensity: float, life: float, is_main_branch: bool = False):
        self.start_x = start_x
        self.start_y = start_y
        self.end_x = end_x
        self.end_y = end_y
        self.intensity = intensity
        self.life = life
        self.max_life = life
        self.age = 0.0  # Track age for white flash effect
        self.is_main_branch = is_main_branch
        self.points = self._generate_branch_points()
        # Character rotation for charm (updates every few frames)
        self.chars = ['|', '/', '\\', '-', '+']
        self.char_index = 0
        self.char_update_timer = 0.0
        # Cache intensity calculation
        self.cached_intensity = intensity
        self.last_intensity_update = 0.0

    def _generate_branch_points(self) -> List[Tuple[int, int]]:
        """Generate points along the lightning branch."""
        points = []
        steps = max(abs(self.end_x - self.start_x), abs(self.end_y - self.start_y))

        if steps == 0:
            return [(self.start_x, self.start_y)]

        # Main branches get full density, secondary branches are simplified
        step_size = 1 if self.is_main_branch else 2
        for i in range(0, steps + 1, step_size):
            t = i / steps
            # Add some randomness for jagged lightning effect
            jitter_x = random.randint(-1, 1) if i > 0 and i < steps else 0
            jitter_y = random.randint(-1, 1) if i > 0 and i < steps else 0

            x = int(self.start_x + t * (self.end_x - self.start_x) + jitter_x)
            y = int(self.start_y + t * (self.end_y - self.start_y) + jitter_y)
            points.append((x, y))

        return points

    def update(self, dt: float):
        """Update lightning branch with cached intensity and character rotation."""
        self.life -= dt
        self.age += dt

        # Update cached intensity less frequently (every 50ms)
        if self.age - self.last_intensity_update >= 0.05:
            self.cached_intensity = (self.life / self.max_life) * self.intensity
            self.last_intensity_update = self.age

        # Rotate character every 100ms for visual charm (reduced from every frame)
        self.char_update_timer += dt
        if self.char_update_timer >= 0.1:
            self.char_index = (self.char_index + 1) % len(self.chars)
            self.char_update_timer = 0.0

    def is_alive(self) -> bool:
        """Check if branch is still alive."""
        return self.life > 0

    def get_intensity(self) -> float:
        """Get cached intensity for performance."""
        return max(0.0, self.cached_intensity)


class LightningStorm(BaseAnimationMode):
    """Lightning storm animation with electrical branching effects."""

    def __init__(self):
        super().__init__("Lightning Storm")
        # Set default color scheme for Lightning Storm mode
        self.color_scheme = 'cyan'
        self.current_color_index = self.available_colors.index('cyan')
        self.branches: List[LightningBranch] = []
        self.rain_drops: List[RainDrop] = []
        self.flash_timer = 0.0
        self.rain_timer = 0.0
        # Slower default lightning timing
        self.next_flash_delay = random.uniform(2.0, 5.0)  # Normal: 2-5 seconds
        self.rain_spawn_rate = 0.010  # Increased rain - spawn every 0.010 seconds (100 per second)
        self.intense_mode = False
        self.color_adapter = CursesColorAdapter()
        # Cached lightning colors
        self.cached_lightning_colors = []
        self.rain_attr = 0  # Pre-calculated rain attribute
        self.lightning_attr = 0  # Pre-calculated lightning attribute (bright contrast)
        self.lightning_attrs = []  # Pre-calculated lightning attributes
        # Particle pool for performance
        self.rain_pool: ParticlePool[RainDrop] = None

    def _get_rain_color(self) -> Tuple[int, int, int]:
        """Get rain color from palette (middle tone)."""
        return get_palette_color(RAIN_PALETTES, self.color_scheme, 'cyan', index=1)

    def _get_lightning_color(self) -> Tuple[int, int, int]:
        """Get bright contrasting lightning color for current scheme."""
        return get_palette_color(LIGHTNING_CONTRAST_COLORS, self.color_scheme, 'cyan')

    def initialize_mode_variables(self) -> None:
        """Initialize lightning storm specific variables."""
        self.branches.clear()
        self.rain_drops.clear()
        self.flash_timer = 0.0
        self.rain_timer = 0.0
        self.color_adapter.initialize_colors()

        # Pre-calculate rain attribute from palette
        rain_color = self._get_rain_color()
        self.rain_attr = self.color_adapter.get_color_attr(rain_color, bold=False)

        # Pre-calculate lightning attribute (bright contrasting color)
        lightning_color = self._get_lightning_color()
        self.lightning_attr = self.color_adapter.get_color_attr(lightning_color, bold=True)

        # Lightning attrs: just use the main bright color (simplified from old gradient system)
        self.lightning_attrs = [self.lightning_attr]

        # Initialize particle pool (create 200 reusable RainDrop objects)
        self.rain_pool = ParticlePool(RainDrop, size=200, rain_attr=self.rain_attr)

    def set_intense_mode(self, intense: bool):
        """Set intense mode for more dramatic effects."""
        self.intense_mode = intense
        if intense:
            self.next_flash_delay = random.uniform(1.0, 2.5)  # Intense: 1-2.5 seconds
            self.rain_spawn_rate = 0.006  # Intense rain - spawn every 0.006 seconds (167 per second)
        else:
            self.next_flash_delay = random.uniform(2.0, 5.0)  # Normal: 2-5 seconds
            self.rain_spawn_rate = 0.010  # Increased rain - spawn every 0.010 seconds (100 per second)

    def update_animation_state(self, update_interval: float) -> None:
        """Update lightning storm animation state."""
        dt = update_interval

        # Update existing branches
        for branch in self.branches[:]:
            branch.update(dt)
            if not branch.is_alive():
                self.branches.remove(branch)

        # Pre-calculate movement multiplier once
        movement_multiplier = 20.0  # Fixed multiplier, no scaling

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

        # No area scaling - fixed spawn rate
        self.rain_timer += dt

        while self.rain_timer >= self.rain_spawn_rate:
            self._spawn_rain_drop()
            self.rain_timer -= self.rain_spawn_rate

        # Create new lightning flashes with variable timing
        self.flash_timer += dt
        if self.flash_timer >= self.next_flash_delay:
            self._create_lightning_flash()
            self.flash_timer = 0.0
            # Reset timing based on intense mode
            if self.intense_mode:
                self.next_flash_delay = random.uniform(1.0, 2.5)
            else:
                self.next_flash_delay = random.uniform(2.0, 5.0)

    def _create_lightning_flash(self) -> None:
        """Create a new lightning flash with branches."""
        # Allow multiple lightning strikes to exist simultaneously
        # Only create new one if we don't have too many active
        if len(self.branches) > 15:  # Limit active branches to prevent overwhelming
            return

        # Main lightning bolt with variable height
        min_x = self.max_cols // 4
        max_x = max(min_x, 3 * self.max_cols // 4)
        start_x = random.randint(min_x, max_x)
        start_y = 0  # Always start from top of terminal

        # Horizontal variation based on terminal height
        horizontal_variation = min(20, max(10, self.max_rows // 4))
        end_x = start_x + random.randint(-horizontal_variation, horizontal_variation)

        # Variable end height - lightning doesn't always reach bottom
        min_height = self.max_rows // 2
        end_y = random.randint(min_height, self.max_rows - 1)

        # Create main branch with variable duration
        main_duration = random.uniform(0.8, 1.6)  # 0.8s to 1.6s (up to 2x longer)
        main_branch = LightningBranch(start_x, start_y, end_x, end_y, 1.0, main_duration, is_main_branch=True)
        self.branches.append(main_branch)

        # Create smaller branches
        num_branches = random.randint(2, 5)
        for _ in range(num_branches):
            # Branch off from random point on main bolt
            min_y = self.max_rows // 4
            max_y = max(min_y, 3 * self.max_rows // 4)
            branch_start_y = random.randint(min_y, max_y)
            branch_start_x = start_x + int((end_x - start_x) * (branch_start_y / self.max_rows))

            branch_end_x = branch_start_x + random.randint(-15, 15)
            branch_end_y = branch_start_y + random.randint(5, 15)

            intensity = random.uniform(0.3, 0.7)
            life = random.uniform(0.4, 0.8)  # 0.4s to 0.8s

            branch = LightningBranch(branch_start_x, branch_start_y,
                                   branch_end_x, branch_end_y, intensity, life)
            self.branches.append(branch)

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

        # Regenerate lightning attribute with new contrasting color
        lightning_color = self._get_lightning_color()
        self.lightning_attr = self.color_adapter.get_color_attr(lightning_color, bold=True)
        self.lightning_attrs = [self.lightning_attr]

        # Update all existing rain drops with new color
        for drop in self.rain_pool.pool:
            drop.attr = self.rain_attr
        for drop in self.rain_pool.active:
            drop.attr = self.rain_attr

    def draw_frame(self) -> None:
        """Ultra-fast drawing with no bounds checking."""
        # Draw rain (no bounds checking - let terminal handle clipping)
        for drop in self.rain_pool.active:
            row, col = int(drop.y), int(drop.x)
            try:
                self.stdscr.addstr(row, col, drop.get_char(), drop.attr)
            except curses.error:
                pass

        # Draw lightning using cached colors and attributes
        for branch in self.branches:
            intensity = branch.get_intensity()

            # White flash effect for first few frames
            if branch.age < 0.05:  # First 50ms are white
                attr = self.lightning_attrs[0]  # Pre-calculated white
            else:
                color_idx = int(intensity * (len(self.lightning_attrs) - 2)) + 1
                attr = self.lightning_attrs[min(color_idx, len(self.lightning_attrs) - 1)]

            # Draw branch points using rotating character
            current_char = branch.chars[branch.char_index]
            for x, y in branch.points:
                try:
                    self.stdscr.addstr(y, x, current_char, attr)
                except curses.error:
                    pass