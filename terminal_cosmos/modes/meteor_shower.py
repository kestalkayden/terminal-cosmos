"""Meteor shower animation mode for terminal-cosmos."""

import random
import math
import curses
import time
from collections import deque
from typing import List, Dict, Any, Tuple
from ..core.animation_base import BaseAnimationMode
from ..colors.generator import ColorGenerator
from ..colors.curses_adapter import CursesColorAdapter
from ..particles import ParticlePool
from ..utils.color_helpers import interpolate_gradient, get_palette_color, clear_color_cache, build_gradient_cache


# Meteor-specific color palettes - bright, fiery, high-intensity gradients
# Each palette has 4 color stops for gradient interpolation
METEOR_PALETTES = {
    'orange': [(255, 100, 0), (255, 150, 50), (255, 200, 100), (255, 255, 200)],     # Bright fiery orange (default)
    'red': [(139, 0, 0), (220, 20, 20), (255, 69, 0), (255, 140, 0)],                # Deep red to orange-red
    'blue': [(70, 130, 255), (100, 170, 255), (150, 200, 255), (200, 230, 255)],     # Bright electric blue
    'green': [(0, 200, 0), (50, 255, 50), (100, 255, 100), (200, 255, 200)],         # Toxic neon green
    'yellow': [(255, 200, 0), (255, 230, 50), (255, 255, 100), (255, 255, 220)],     # Bright golden yellow
    'purple': [(138, 43, 226), (160, 80, 240), (200, 120, 255), (230, 180, 255)],    # Bright purple-magenta
    'cyan': [(0, 200, 255), (50, 220, 255), (100, 240, 255), (200, 250, 255)],       # Electric cyan
    'gray': [(100, 100, 100), (150, 150, 150), (200, 200, 200), (255, 255, 255)],    # Monochrome intensity
    'pink': [(255, 20, 147), (255, 105, 180), (255, 160, 200), (255, 220, 240)]      # Hot pink to light pink
}


class Meteor:
    """Diagonal meteor with trail support."""

    def __init__(self, meteor_attr):
        self.attr = meteor_attr  # Pre-calculated attribute
        # Initialize with dummy values - will be reset when used
        self.x = 0.0
        self.y = 0.0
        self.velocity_x = 1.0
        self.velocity_y = 2.0
        # Animation frames for connected meteor streak
        self.streak_chars = ['╱', '/', '′', '·']  # Connected streak characters (removed blocky chars)
        self.head_chars = ['●', '*', '◉', '+', '○']  # More distinct bulbous fireball heads
        self.frame_index = 0
        self.frame_timer = 0.0
        self.frame_duration = 0.1  # 100ms per frame (slower than rain)
        # Assign meteor characteristics
        self.head_char = random.choice(self.head_chars)  # Fixed head for this meteor
        # Trail support - using deque for O(1) popleft() performance
        self.max_trail_length = random.randint(26, 30)  # Variable trail length 26-30 segments
        self.trail = deque(maxlen=self.max_trail_length)  # Deque automatically discards oldest when full
        self.trail_timer = 0.0  # Timer for FPS-independent trail accumulation

    def reset(self, x: float, y: float):
        """Reset meteor for reuse from object pool."""
        self.x = x
        self.y = y
        # Back to original 45-degree angle
        self.velocity_x = -1.0  # Left movement
        self.velocity_y = 1.0   # Downward movement (45-degree angle)
        # Reset animation
        self.frame_index = 0
        self.frame_timer = 0.0
        # Randomize trail length and recreate deque with new maxlen
        self.max_trail_length = random.randint(26, 30)
        self.trail = deque(maxlen=self.max_trail_length)
        self.trail_timer = 0.0  # Reset trail timer
        self.head_char = random.choice(self.head_chars)
        # Debug: Print which head char was chosen
        # print(f"Meteor head: {self.head_char}")

    def update(self, dt: float, movement_multiplier: float):
        """Update position and animation frame."""
        # Store current integer position BEFORE updating (this is where head is currently drawn)
        current_head_x = int(self.x)
        current_head_y = int(self.y)

        # Update position diagonally
        self.x += self.velocity_x * dt * movement_multiplier
        self.y += self.velocity_y * dt * movement_multiplier

        # Update animation frame for streak characters
        self.frame_timer += dt
        if self.frame_timer >= self.frame_duration:
            self.frame_index = (self.frame_index + 1) % len(self.streak_chars)
            self.frame_timer = 0.0

        # Add trail points every 80ms for FPS independence
        self.trail_timer += dt
        if self.trail_timer >= 0.08:  # 80ms between trail points
            # Deque with maxlen automatically discards oldest when full (O(1) operation)
            self.trail.append((current_head_x, current_head_y))
            self.trail_timer = 0.0

    def get_char(self) -> str:
        """Get current streak character."""
        return self.streak_chars[self.frame_index]

    def get_head_char(self) -> str:
        """Get the bulbous fireball head character."""
        return self.head_char

    def is_off_screen(self, max_rows: int, max_cols: int) -> bool:
        """Check if meteor is off screen when ALL trail segments are gone."""
        # Check if meteor head is way off screen (bottom/right)
        if self.y > max_rows + 30 or self.x > max_cols + 30:
            return True

        # For left edge, only remove when all trail segments are off-screen
        if self.x < 1:
            # Check if any trail segments are still visible (x >= 1)
            for trail_x, trail_y in self.trail:
                if trail_x >= 1:
                    return False  # Keep meteor alive, some trail still visible
            return True  # All trail segments are off-screen, remove meteor

        return False


class MeteorShower(BaseAnimationMode):
    """Meteor shower animation with streaking meteors."""

    def __init__(self):
        super().__init__("Meteor Shower")
        # Set default color scheme for Meteor mode
        self.color_scheme = 'orange'
        self.current_color_index = self.available_colors.index('orange')  # Sync index with scheme
        self.meteors: List[Meteor] = []
        self.meteor_timer = 0.0
        # Intense mode flag
        self.intense_mode = False
        # Variable spawn rate for dramatic effect (1-2 meteors on screen normal, 3-4 intense)
        self.next_meteor_delay = random.uniform(0.8, 1.5)  # Random delay between 0.8-1.5 seconds
        self.color_adapter = CursesColorAdapter()
        # Cached meteor colors
        self.cached_meteor_colors = []
        self.meteor_attr = 0  # Pre-calculated meteor attribute
        # Particle pool for performance
        self.meteor_pool: ParticlePool[Meteor] = None
        # Smart spawn distribution to prevent clumping (deque with maxlen for O(1) operations)
        self.recent_spawn_positions = deque(maxlen=3)  # Track last 3 spawn X coordinates
        # Fractured meteor system
        self.pending_meteors = []  # Queue of meteors scheduled to spawn later
        self.meteor_chains = {}  # Track column occupancy and chain status per meteor group
        self.chain_counter = 0  # Unique ID for each meteor chain
        # Static star field
        self.static_stars = []  # List of (x, y, char, color) for background stars

    def initialize_mode_variables(self) -> None:
        """Initialize meteor shower specific variables."""
        self.meteors.clear()
        self.recent_spawn_positions.clear()
        self.pending_meteors.clear()
        self.meteor_chains.clear()
        self.chain_counter = 0
        self.meteor_timer = 0.0
        self.color_adapter.initialize_colors()

        # Pre-calculate meteor attribute (white for tip)
        meteor_color = (255, 255, 255)
        self.meteor_attr = self.color_adapter.get_color_attr(meteor_color, bold=True)

        # Pre-compute trail color lookup table (eliminates 7,200 calculations/sec)
        self._precompute_trail_colors()

        # Initialize particle pool (create 10 reusable Meteor objects)
        self.meteor_pool = ParticlePool(Meteor, size=10, meteor_attr=self.meteor_attr)

        # Generate static star field
        self._generate_static_stars()

    def update_animation_state(self, update_interval: float) -> None:
        """Update meteor shower animation state."""
        dt = update_interval

        # Pre-calculate movement multiplier (balanced speed for good alignment)
        movement_multiplier = 12.0  # Balanced speed that maintains trail alignment

        # Update meteor drops using particle pool
        i = 0
        while i < len(self.meteor_pool.active):
            meteor = self.meteor_pool.active[i]
            meteor.update(dt, movement_multiplier)
            if meteor.is_off_screen(self.max_rows, self.max_cols):
                # Return to pool instead of deleting
                self.meteor_pool.release(self.meteor_pool.active.pop(i))
            else:
                i += 1

        # Process pending fractured meteors
        current_time = time.time()
        i = 0
        while i < len(self.pending_meteors):
            pending = self.pending_meteors[i]
            if current_time >= pending['spawn_time']:
                self._spawn_fractured_meteor(pending)
                self.pending_meteors.pop(i)
            else:
                i += 1

        # Spawn new meteors with variable timing
        self.meteor_timer += dt
        if self.meteor_timer >= self.next_meteor_delay:
            self._spawn_meteor()
            self.meteor_timer = 0.0
            # Set new random delay for next meteor (faster in intense mode)
            if self.intense_mode:
                self.next_meteor_delay = random.uniform(0.4, 0.8)  # 2x faster spawning
            else:
                self.next_meteor_delay = random.uniform(0.8, 1.5)

    def _spawn_meteor(self) -> None:
        """Spawn a new meteor using particle pool."""
        # Limit to 4 meteors on screen
        if len(self.meteor_pool.active) >= 4:
            return

        # Get object from pool
        meteor = self.meteor_pool.acquire()
        if not meteor:
            return  # Pool exhausted, skip spawn to maintain performance

        # Smart spawn distribution to prevent clumping
        min_distance = self.max_cols // 4  # Minimum distance between meteors (25% of screen width)
        max_attempts = 10  # Don't try forever

        for attempt in range(max_attempts):
            # Generate potential spawn position
            start_x = float(random.randint(-2, self.max_cols + 2))
            start_y = float(random.randint(-1, 0))

            # Check distance from recent spawn positions
            too_close = False
            for recent_x in self.recent_spawn_positions:
                if abs(start_x - recent_x) < min_distance:
                    too_close = True
                    break

            if not too_close:
                # Good position found, use it
                break

        # Add new position to tracking (deque with maxlen=3 automatically discards oldest)
        self.recent_spawn_positions.append(start_x)

        meteor.reset(start_x, start_y)
        self.meteor_pool.active.append(meteor)

        # Plan fractured meteor chain
        self._plan_fractured_chain(start_x, start_y)

    def _plan_fractured_chain(self, main_x: float, main_y: float) -> None:
        """Plan and schedule fractured meteors for this chain."""
        current_time = time.time()
        chain_id = self.chain_counter
        self.chain_counter += 1

        # Track occupied columns for this chain
        occupied_columns = [int(main_x)]

        # Determine entire chain upfront
        chain_plan = {"secondary": False, "tertiary": False, "quaternary": False}

        if random.random() < 0.3:  # 30% chance for secondary
            chain_plan["secondary"] = True
            if random.random() < 0.6:  # 60% chance for tertiary
                chain_plan["tertiary"] = True
                if random.random() < 0.8:  # 80% chance for quaternary
                    chain_plan["quaternary"] = True

        # Schedule secondary (0.2-0.6s delay)
        if chain_plan["secondary"]:
            secondary_delay = random.uniform(0.2, 0.6)
            secondary_x = self._find_available_column(main_x, occupied_columns, range_offset=2)
            if secondary_x is not None:
                occupied_columns.append(secondary_x)
                self.pending_meteors.append({
                    'spawn_time': current_time + secondary_delay,
                    'x': secondary_x,
                    'y': main_y,
                    'trail_length': random.randint(14, 18),
                    'chain_id': chain_id,
                    'is_last': not chain_plan["tertiary"]
                })

        # Schedule tertiary (0.4-1.5s delay)
        if chain_plan["tertiary"]:
            tertiary_delay = random.uniform(0.4, 1.5)
            tertiary_x = self._find_available_column(main_x, occupied_columns, range_offset=2)
            if tertiary_x is not None:
                occupied_columns.append(tertiary_x)
                self.pending_meteors.append({
                    'spawn_time': current_time + tertiary_delay,
                    'x': tertiary_x,
                    'y': main_y,
                    'trail_length': random.randint(8, 12),
                    'chain_id': chain_id,
                    'is_last': not chain_plan["quaternary"]
                })

        # Schedule quaternary(s) (0.7-1.8s delay) - tertiary can spawn 2 quaternaries
        if chain_plan["quaternary"]:
            num_quaternaries = 2 if random.random() < 0.5 else 1  # 50% chance for 2 quaternaries

            for q in range(num_quaternaries):
                quaternary_delay = random.uniform(0.7, 1.8)
                quaternary_x = self._find_available_column(main_x, occupied_columns, range_offset=3)
                if quaternary_x is not None:
                    occupied_columns.append(quaternary_x)
                    is_last_quaternary = (q == num_quaternaries - 1)  # Only last quaternary cleans up
                    self.pending_meteors.append({
                        'spawn_time': current_time + quaternary_delay,
                        'x': quaternary_x,
                        'y': main_y,
                        'trail_length': random.randint(4, 8),
                        'chain_id': chain_id,
                        'is_last': is_last_quaternary
                    })

        # Store chain info for occupancy tracking
        self.meteor_chains[chain_id] = {
            'occupied_columns': occupied_columns,
            'completed': False
        }

    def _find_available_column(self, main_x: float, occupied_columns: list, range_offset: int) -> int:
        """Find an available column within range that's not occupied."""
        main_col = int(main_x)
        available_columns = []

        for offset in range(-range_offset, range_offset + 1):
            col = main_col + offset
            if col not in occupied_columns:
                available_columns.append(col)

        return random.choice(available_columns) if available_columns else None

    def _spawn_fractured_meteor(self, pending: dict) -> None:
        """Spawn a fractured meteor from the pending queue."""
        # Get meteor from pool
        meteor = self.meteor_pool.acquire()
        if not meteor:
            return  # Pool exhausted

        # Reset meteor at specified position
        meteor.reset(pending['x'], pending['y'])

        # Set custom trail length for fractured meteor AFTER reset (which overwrites it)
        meteor.max_trail_length = pending['trail_length']

        self.meteor_pool.active.append(meteor)

        # If this is the last meteor in chain, reset column occupancy
        if pending['is_last']:
            chain_id = pending['chain_id']
            if chain_id in self.meteor_chains:
                del self.meteor_chains[chain_id]

    def _get_trail_color(self, trail_progress: float) -> Tuple[int, int, int]:
        """
        Get trail color from mode-specific palette based on position.

        Args:
            trail_progress: Position in trail (0.0 = head, 1.0 = tail)

        Returns:
            RGB color tuple
        """
        # Get palette for current color scheme, fallback to orange if not found
        palette = get_palette_color(METEOR_PALETTES, self.color_scheme, 'orange')

        # Interpolate with reverse=True so head (0.0) is brightest
        return interpolate_gradient(palette, trail_progress, reverse=True)

    def _precompute_trail_colors(self):
        """Pre-compute trail color attributes for all trail positions.

        Creates lookup table with 30 gradient steps, each with bold and non-bold versions.
        Eliminates 7,200 color calculations per second (4 meteors × 30 segments × 60 FPS).
        """
        # Get palette for current color scheme
        palette = get_palette_color(METEOR_PALETTES, self.color_scheme, 'orange')

        # Use utility function to build gradient cache (with reverse=True for head-to-tail)
        self.trail_color_cache = build_gradient_cache(
            self.color_adapter,
            palette,
            steps=30,
            with_bold=True,
            reverse=True  # Head (index 0) should be brightest
        )

    def set_intense_mode(self, intense: bool) -> None:
        """Set intense mode for faster meteor spawning."""
        self.intense_mode = intense

    def on_color_change(self) -> None:
        """Called when user presses 'c' to cycle colors."""
        # Clear color adapter cache AND reset counter to reuse color pairs from start
        clear_color_cache(self.color_adapter)

        # Regenerate trail color cache with new color scheme
        self._precompute_trail_colors()

    def _generate_static_stars(self) -> None:
        """Generate a static star field for background."""
        self.static_stars.clear()
        num_stars = min(80, self.max_rows * self.max_cols // 40)  # About 1 star per 40 positions

        star_chars = ['.', '*', '·']  # Small white/grey star characters
        star_colors = [
            (255, 255, 255),  # White
            (200, 200, 200),  # Light grey
            (160, 160, 160)   # Grey
        ]

        # Pre-compute color attributes for static stars (they never change)
        for _ in range(num_stars):
            x = random.randint(0, self.max_cols - 1)
            y = random.randint(0, self.max_rows - 1)
            char = random.choice(star_chars)
            color = random.choice(star_colors)
            # Cache the attribute instead of the color - eliminates 4,800 lookups/sec
            attr = self.color_adapter.get_color_attr(color, bold=False)
            self.static_stars.append((x, y, char, attr))

    def draw_frame(self) -> None:
        """Ultra-fast drawing with red-to-white gradient."""
        # Draw static star field background first
        for x, y, char, attr in self.static_stars:
            # Attribute is pre-cached - no color lookup needed
            self.safe_addstr(y, x, char, attr)

        # Draw meteors with trails (no separate fireball)
        for meteor in self.meteor_pool.active:
            # Draw trail with red-to-white gradient
            trail_length = len(meteor.trail)
            for i, (trail_x, trail_y) in enumerate(meteor.trail):
                # Filter out trail segments at problematic left edge (x < 1) and normal bounds
                if 0 <= trail_y < self.max_rows and 1 <= trail_x < self.max_cols:
                    # Calculate position in trail (0.0 = oldest/reddest, 1.0 = newest/whitest)
                    trail_pos = i / max(trail_length - 1, 1) if trail_length > 1 else 0

                    # Percentage-based gradient for consistent dark tails regardless of length
                    segments_from_head = trail_length - 1 - i  # 0 = oldest, trail_length-1 = newest
                    trail_progress = segments_from_head / max(trail_length - 1, 1)  # 0.0 = head, 1.0 = tail

                    # Skip only the very dimmest trail parts to show full length
                    if trail_pos > 0.05:
                        # Use pre-computed color attributes from cache (60-70% faster)
                        cache_index = min(int(trail_progress * 29), 29)
                        bold_index = 1 if trail_pos > 0.6 else 0  # 1=bold, 0=normal
                        attr = self.trail_color_cache[cache_index][bold_index]

                        # Use connected streak that gradually breaks up (70% connected, 20% transition, 10% tail)
                        connected_length = int(trail_length * 0.7)  # 70% connected
                        transition_length = int(trail_length * 0.2)  # 20% transition

                        if segments_from_head <= connected_length:  # Connected streak (70%)
                            trail_char = meteor.streak_chars[0]  # ╱
                        elif segments_from_head <= connected_length + transition_length:  # Transition (20%)
                            trail_char = meteor.streak_chars[1]  # /
                        else:  # Tail end (10%)
                            trail_char = meteor.streak_chars[2]  # ′

                        try:
                            self.stdscr.addstr(trail_y, trail_x, trail_char, attr)
                        except curses.error:
                            pass