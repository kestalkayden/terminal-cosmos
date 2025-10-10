"""Fireflies animation mode - peaceful blinking particles."""

import curses
import random
import math
from collections import deque
from ..core.animation_base import BaseAnimationMode
from ..colors.curses_adapter import CursesColorAdapter
from ..utils.color_helpers import clear_color_cache, build_color_variations


# Firefly color palettes - 9 schemes with adjacent/complementary colors
# Each scheme has 4 colors for natural variation
FIREFLY_PALETTES = {
    'yellow': {
        'color1': (255, 255, 100),   # Bright yellow
        'color2': (255, 191, 0),     # Amber/gold
        'color3': (200, 255, 100),   # Yellow-green
        'color4': (150, 255, 50)     # Lime green
    },
    'red': {
        'color1': (255, 100, 100),   # Bright red
        'color2': (255, 140, 60),    # Red-orange
        'color3': (255, 120, 150),   # Pink-red
        'color4': (255, 160, 80)     # Warm amber
    },
    'blue': {
        'color1': (100, 150, 255),   # Bright blue
        'color2': (120, 200, 255),   # Cyan-blue
        'color3': (150, 180, 255),   # Light blue
        'color4': (180, 160, 255)    # Periwinkle
    },
    'green': {
        'color1': (100, 255, 100),   # Bright green
        'color2': (150, 255, 50),    # Lime
        'color3': (180, 255, 100),   # Yellow-green
        'color4': (100, 255, 180)    # Teal-green
    },
    'purple': {
        'color1': (200, 100, 255),   # Bright purple
        'color2': (255, 100, 200),   # Magenta
        'color3': (180, 120, 255),   # Violet
        'color4': (220, 150, 255)    # Lavender
    },
    'cyan': {
        'color1': (100, 255, 255),   # Bright cyan
        'color2': (100, 200, 200),   # Teal
        'color3': (150, 255, 240),   # Aqua
        'color4': (120, 240, 255)    # Light cyan
    },
    'gray': {
        'color1': (255, 255, 255),   # White
        'color2': (200, 200, 220),   # Cool white
        'color3': (180, 180, 180),   # Light gray
        'color4': (220, 220, 230)    # Silver
    },
    'pink': {
        'color1': (255, 150, 200),   # Bright pink
        'color2': (255, 100, 180),   # Magenta-pink
        'color3': (255, 180, 200),   # Rose
        'color4': (255, 160, 140)    # Coral-pink
    },
    'orange': {
        'color1': (255, 180, 100),   # Bright orange
        'color2': (255, 140, 80),    # Red-orange
        'color3': (255, 200, 100),   # Gold
        'color4': (255, 190, 120)    # Warm amber
    }
}

# Characters for different brightness levels (fade effect)
# Using ASCII-safe characters for better compatibility
BRIGHTNESS_CHARS = [
    ' ',   # 0% - invisible
    '.',   # 25% - very dim
    '*',   # 50% - medium
    '+',   # 75% - bright
    '@'    # 100% - full brightness
]

# Flash pattern states
FLASH_CHARGING = 0  # Building up to flash
FLASH_ON = 1        # Quick bright flash
FLASH_FADING = 2    # Slow fade after flash
FLASH_PAUSE = 3     # Long pause between flashes


class Firefly:
    """A single firefly with position and oscillating brightness."""

    def __init__(self, row, col, color_name, max_rows, max_cols, attraction_points, intense_mode=False):
        """Initialize a firefly.

        Args:
            row: Row position
            col: Column position
            color_name: Color key from current palette (color1-color4)
            max_rows: Maximum row boundary
            max_cols: Maximum column boundary
            attraction_points: List of (x, y) attraction points for clustering
            intense_mode: If True, fireflies flash more frequently
        """
        self.x = float(col)  # Use float for smooth sub-character movement
        self.y = float(row)
        self.color_name = color_name  # Actually color_key (color1-color4)
        self.max_rows = max_rows
        self.max_cols = max_cols
        self.attraction_points = attraction_points
        self.intense_mode = intense_mode

        # Depth/parallax (0.3 = far/slow/dim, 1.0 = close/fast/bright)
        self.depth = random.uniform(0.3, 1.0)

        # Motion blur trail (last 3 positions)
        self.trail = deque(maxlen=3)

        # Realistic flash pattern state machine
        # Randomize initial state so fireflies aren't synchronized
        self.flash_state = random.choice([FLASH_PAUSE, FLASH_PAUSE, FLASH_PAUSE, FLASH_FADING])  # 75% start dark
        self.flash_timer = random.uniform(0, 2.0)  # Random position in cycle
        # Flash timing: intense mode is 2x faster (1-3s vs 3-6s)
        if intense_mode:
            self.flash_duration = random.uniform(1.0, 3.0)  # Faster pauses in intense mode
        else:
            self.flash_duration = random.uniform(3.0, 6.0)  # Normal pauses: 3-6 seconds
        self.flash_pattern = random.choice(['single', 'double'])  # Different species
        self.flash_count = 0  # For double flash pattern
        self.brightness = 0.0

        # Some fireflies sync with others (10% chance)
        self.sync_group = random.randint(0, 9)  # 0-9, where 0 means synchronized

        # Floating movement with gentle corrections
        # Speed scaled by depth (closer = faster) - increased for smoother motion
        base_speed = random.uniform(2.0, 5.0)  # Increased from 1-3 to 2-5
        speed = base_speed * self.depth
        angle = random.uniform(0, 2 * math.pi)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 0.3 * self.depth  # Slight upward bias

        self.drift_timer = 0.0
        self.drift_interval = random.uniform(1.0, 3.0)  # Adjust course every 1-3 seconds

    @property
    def row(self):
        """Get current row as integer."""
        return int(self.y)

    @property
    def col(self):
        """Get current column as integer."""
        return int(self.x)

    def update(self, dt):
        """Update firefly brightness and position.

        Args:
            dt: Time delta since last update
        """
        # === REALISTIC FLASH PATTERN STATE MACHINE ===
        self.flash_timer += dt

        if self.flash_state == FLASH_PAUSE:
            # Long dark pause (2-5 seconds)
            self.brightness = 0.0
            if self.flash_timer > self.flash_duration:
                self.flash_timer = 0.0
                self.flash_duration = 0.1  # Charging duration
                self.flash_state = FLASH_CHARGING
                self.flash_count = 0

        elif self.flash_state == FLASH_CHARGING:
            # Quick ramp up (0.1 seconds)
            self.brightness = min(1.0, self.flash_timer / 0.1)
            if self.flash_timer > self.flash_duration:
                self.flash_timer = 0.0
                self.flash_duration = 0.15  # Flash on duration
                self.flash_state = FLASH_ON

        elif self.flash_state == FLASH_ON:
            # Quick bright flash (0.15 seconds)
            self.brightness = 1.0
            if self.flash_timer > self.flash_duration:
                self.flash_timer = 0.0
                self.flash_duration = 0.6  # Fade duration
                self.flash_state = FLASH_FADING

        elif self.flash_state == FLASH_FADING:
            # Slow fade (0.6 seconds)
            self.brightness = max(0.0, 1.0 - (self.flash_timer / self.flash_duration))
            if self.flash_timer > self.flash_duration:
                self.flash_timer = 0.0
                self.flash_count += 1

                # Check if double flash pattern
                if self.flash_pattern == 'double' and self.flash_count < 2:
                    # Do another flash quickly
                    self.flash_duration = 0.1  # Charging for 2nd flash
                    self.flash_state = FLASH_CHARGING
                else:
                    # Go back to pause (intense mode: 1-3s, normal: 3-6s)
                    if self.intense_mode:
                        self.flash_duration = random.uniform(1.0, 3.0)  # Faster in intense mode
                    else:
                        self.flash_duration = random.uniform(3.0, 6.0)  # Normal pause duration
                    self.flash_state = FLASH_PAUSE

        # Don't scale brightness by depth here - do it only for display in get_char()

        # === MOVEMENT WITH CLUSTERING ===

        # Add small random flutter (erratic movement) scaled by depth
        flutter_strength = 1.0 * self.depth  # Increased flutter for more visible movement
        self.vx += random.uniform(-flutter_strength, flutter_strength) * dt
        self.vy += random.uniform(-flutter_strength, flutter_strength) * dt

        # Gentle attraction toward nearest clustering point
        if self.attraction_points:
            # Find nearest attraction point
            min_dist = float('inf')
            nearest_point = None
            for point in self.attraction_points:
                dx = point[0] - self.x
                dy = point[1] - self.y
                dist = math.sqrt(dx**2 + dy**2)
                if dist < min_dist:
                    min_dist = dist
                    nearest_point = point

            if nearest_point:
                # Gentle pull toward attraction point (very subtle)
                attraction_strength = 0.3 * self.depth
                dx = nearest_point[0] - self.x
                dy = nearest_point[1] - self.y
                dist = math.sqrt(dx**2 + dy**2)
                if dist > 0:
                    self.vx += (dx / dist) * attraction_strength * dt
                    self.vy += (dy / dist) * attraction_strength * dt

        # Update drift timer
        self.drift_timer += dt

        # Periodically adjust course (gentle corrections)
        if self.drift_timer >= self.drift_interval:
            self.drift_timer = 0.0
            self.drift_interval = random.uniform(1.0, 3.0)

            # Make a gentle course correction
            current_speed = math.sqrt(self.vx**2 + self.vy**2)

            # Adjust angle by -30 to +30 degrees
            angle_adjustment = random.uniform(-math.pi/6, math.pi/6)
            current_angle = math.atan2(self.vy, self.vx)
            new_angle = current_angle + angle_adjustment

            # Adjust speed slightly, scaled by depth
            new_speed = current_speed + random.uniform(-1.0, 1.0)
            max_speed = 6.0 * self.depth  # Increased max speed
            new_speed = max(1.0 * self.depth, min(max_speed, new_speed))

            # Apply new velocity with slight upward bias
            self.vx = math.cos(new_angle) * new_speed
            self.vy = math.sin(new_angle) * new_speed - 0.2 * self.depth

        # Store current position in trail before moving
        self.trail.append((self.x, self.y))

        # Update position based on velocity (scaled by depth for parallax)
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Gentle bounce off boundaries
        if self.x < 0:
            self.x = 0
            self.vx = abs(self.vx) * 0.8
        elif self.x >= self.max_cols:
            self.x = self.max_cols - 1
            self.vx = -abs(self.vx) * 0.8

        if self.y < 0:
            self.y = 0
            self.vy = abs(self.vy) * 0.8
        elif self.y >= self.max_rows:
            self.y = self.max_rows - 1
            self.vy = -abs(self.vy) * 0.8

    def get_char(self):
        """Get character based on current brightness.

        Returns:
            Character representing current brightness
        """
        # Scale brightness by depth (distant fireflies slightly dimmer)
        # Less aggressive scaling: 0.7 to 1.0 range instead of 0.4 to 1.0
        display_brightness = self.brightness * (0.7 + 0.3 * self.depth)

        # Map brightness (0.0 to 1.0) to character index
        index = int(display_brightness * (len(BRIGHTNESS_CHARS) - 1))
        index = min(index, len(BRIGHTNESS_CHARS) - 1)
        return BRIGHTNESS_CHARS[index]


class Fireflies(BaseAnimationMode):
    """Fireflies mode with peaceful blinking particles."""

    def __init__(self):
        super().__init__("Fireflies")
        self.color_scheme = 'yellow'  # Default to yellow palette
        self.current_color_index = self.available_colors.index('yellow')  # Sync with color scheme
        self.color_adapter = CursesColorAdapter()

        # Firefly management
        self.fireflies = []
        self.color_attrs = {}  # {color_key: [variations]}

        # Clustering attraction points (slowly moving)
        self.attraction_points = []
        self.attraction_update_timer = 0.0

        # Intense mode flag
        self.intense_mode = False

    def initialize_mode_variables(self) -> None:
        """Initialize fireflies mode variables."""
        self.color_adapter.initialize_colors()
        self._build_color_attrs()
        self._init_attraction_points()
        self._spawn_fireflies()

    def _build_color_attrs(self):
        """Pre-compute color attributes with temperature variations."""
        self.color_attrs = {}

        # Get current color scheme palette
        palette = FIREFLY_PALETTES.get(self.color_scheme, FIREFLY_PALETTES['yellow'])

        # Create variations for each of the 4 colors in the palette using utility
        for color_key, base_rgb in palette.items():
            self.color_attrs[color_key] = build_color_variations(
                self.color_adapter,
                base_rgb,
                variations=10,
                variance=15,
                bold=True
            )

    def _init_attraction_points(self):
        """Initialize clustering attraction points."""
        self.attraction_points = []
        # Create 3-5 attraction points spread across screen
        num_points = random.randint(3, 5)
        for _ in range(num_points):
            x = random.uniform(0, self.max_cols)
            y = random.uniform(0, self.max_rows)
            self.attraction_points.append([x, y])  # Use list so we can modify

    def _spawn_fireflies(self):
        """Spawn fireflies across the screen."""
        self.fireflies = []

        # Spawn fireflies: intense mode = 80-120, normal = 40-80
        if self.intense_mode:
            num_fireflies = random.randint(80, 120)
        else:
            num_fireflies = random.randint(40, 80)

        # Ensure we don't spawn too many for small terminals
        max_fireflies = (self.max_rows * self.max_cols) // 20
        num_fireflies = min(num_fireflies, max_fireflies)

        for _ in range(num_fireflies):
            row = random.randint(0, max(0, self.max_rows - 1))
            col = random.randint(0, max(0, self.max_cols - 1))

            # Random color selection with weighted probabilities from current palette
            # Weighted toward color1 and color2 for more cohesive look
            color_choice = random.random()
            if color_choice < 0.4:
                color_key = 'color1'
            elif color_choice < 0.7:
                color_key = 'color2'
            elif color_choice < 0.9:
                color_key = 'color3'
            else:
                color_key = 'color4'

            firefly = Firefly(row, col, color_key, self.max_rows, self.max_cols, self.attraction_points, self.intense_mode)

            # Assign random color variation to each firefly
            firefly.color_variation_index = random.randint(0, 9)

            self.fireflies.append(firefly)

        # Synchronize some fireflies for occasional group flashing
        # Set 10% to start in FLASH_ON state
        for firefly in self.fireflies:
            if firefly.sync_group == 0:  # 10% of fireflies
                firefly.flash_state = FLASH_ON
                firefly.flash_timer = 0.0

    def update_animation_state(self, update_interval: float) -> None:
        """Update all fireflies and attraction points."""
        # Update fireflies
        for firefly in self.fireflies:
            firefly.update(update_interval)

        # Slowly drift attraction points (every 10-15 seconds)
        self.attraction_update_timer += update_interval
        if self.attraction_update_timer > random.uniform(10.0, 15.0):
            self.attraction_update_timer = 0.0

            # Move each attraction point slightly
            for point in self.attraction_points:
                # Small random drift
                point[0] += random.uniform(-10, 10)
                point[1] += random.uniform(-5, 5)

                # Keep within bounds
                point[0] = max(0, min(self.max_cols, point[0]))
                point[1] = max(0, min(self.max_rows, point[1]))

    def on_color_change(self) -> None:
        """Called when user presses 'c' to cycle colors."""
        # Regenerate fireflies with new random positions
        clear_color_cache(self.color_adapter)
        self._build_color_attrs()
        self._init_attraction_points()
        self._spawn_fireflies()

    def set_intense_mode(self, intense: bool) -> None:
        """Set intense mode for more fireflies and faster flash cycles.

        Args:
            intense: If True, spawns 80-120 fireflies with 1-3s flash cycles.
                    If False, spawns 40-80 fireflies with 3-6s flash cycles.
        """
        self.intense_mode = intense

    def on_resize(self) -> None:
        """Handle terminal resize by updating attraction points and firefly bounds."""
        # Update attraction points to fit new screen size
        self._init_attraction_points()

        # Update firefly boundaries (they'll naturally clip to new bounds)
        for firefly in self.fireflies:
            firefly.max_rows = self.max_rows
            firefly.max_cols = self.max_cols

    def draw_frame(self) -> None:
        """Draw all fireflies with motion blur trails."""
        for firefly in self.fireflies:
            # Get current character and brightness
            char = firefly.get_char()

            # Skip completely if invisible (including trail)
            if char == ' ':
                continue

            # Get color attribute with temperature variation
            color_variations = self.color_attrs.get(firefly.color_name, [])
            if color_variations:
                color_attr = color_variations[firefly.color_variation_index]
            else:
                color_attr = 0

            # Draw motion blur trail only if firefly is bright enough (not . or *)
            if char in ['+', '@'] and len(firefly.trail) >= 2:
                # Trail positions are stored from oldest to newest
                trail_chars = ['.', '*']  # Dimmer chars for trail
                for i, (trail_x, trail_y) in enumerate(firefly.trail):
                    if i < len(trail_chars):
                        trail_char = trail_chars[i]
                        trail_row = int(trail_y)
                        trail_col = int(trail_x)

                        # Draw trail with same color but dimmer char
                        try:
                            self.stdscr.addstr(trail_row, trail_col, trail_char, color_attr)
                        except curses.error:
                            pass

            # Draw the firefly head (current position)
            try:
                self.stdscr.addstr(firefly.row, firefly.col, char, color_attr)
            except curses.error:
                pass
