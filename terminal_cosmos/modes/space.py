"""Space starfield animation mode for terminal-cosmos."""

import random
import math
import time
from collections import deque
from typing import List, Dict, Any
from ..core.animation_base import BaseAnimationMode
from ..colors.generator import ColorGenerator
from ..colors.curses_adapter import CursesColorAdapter
from ..utils.color_helpers import clear_color_cache


# Space mode color palettes - 9 cosmic themes
SPACE_PALETTES = {
    'blue': {
        'large_stars': [(0, 150, 255), (200, 100, 255)],  # Blue/purple stars
        'meteor_gradient': [
            (255, 255, 255),    # White head
            (240, 250, 255),    # Pale blue
            (220, 240, 255),    # Light blue
            (180, 220, 255),    # Blue
            (140, 200, 255),    # Medium blue
            (100, 160, 220),    # Darker blue
            (60, 120, 180),     # Dark blue
            (30, 60, 120)       # Very dark blue
        ],
        'streak_color': (100, 200, 255),
        'satellite': (128, 128, 128),
        'planet': (100, 150, 255),
        'alien': (200, 220, 255),
        'starburst_base': (255, 255, 255),
        'starburst_twinkle': (200, 230, 255)
    },
    'red': {
        'large_stars': [(255, 80, 60), (255, 140, 0)],  # Red/orange stars
        'meteor_gradient': [
            (255, 255, 255),    # White head
            (255, 240, 230),    # Pale orange
            (255, 200, 150),    # Light orange
            (255, 160, 100),    # Orange
            (255, 120, 60),     # Red-orange
            (220, 80, 40),      # Red
            (180, 50, 30),      # Dark red
            (120, 30, 20)       # Very dark red
        ],
        'streak_color': (255, 200, 100),
        'satellite': (160, 120, 120),
        'planet': (255, 100, 80),
        'alien': (255, 180, 150),
        'starburst_base': (255, 255, 255),
        'starburst_twinkle': (255, 220, 180)
    },
    'green': {
        'large_stars': [(0, 255, 150), (100, 255, 200)],  # Green/teal stars
        'meteor_gradient': [
            (255, 255, 255),    # White head
            (230, 255, 240),    # Pale green
            (200, 255, 220),    # Light green
            (150, 255, 190),    # Green
            (100, 220, 150),    # Medium green
            (60, 180, 110),     # Darker green
            (40, 130, 80),      # Dark green
            (20, 80, 50)        # Very dark green
        ],
        'streak_color': (150, 255, 200),
        'satellite': (120, 150, 130),
        'planet': (80, 255, 120),
        'alien': (180, 255, 200),
        'starburst_base': (255, 255, 255),
        'starburst_twinkle': (200, 255, 220)
    },
    'yellow': {
        'large_stars': [(255, 255, 100), (255, 200, 80)],  # Yellow/gold stars
        'meteor_gradient': [
            (255, 255, 255),    # White head
            (255, 255, 230),    # Pale yellow
            (255, 255, 180),    # Light yellow
            (255, 240, 120),    # Yellow
            (255, 220, 80),     # Golden yellow
            (220, 180, 60),     # Gold
            (180, 140, 40),     # Dark gold
            (120, 90, 30)       # Very dark gold
        ],
        'streak_color': (255, 255, 150),
        'satellite': (150, 140, 100),
        'planet': (255, 220, 100),
        'alien': (255, 240, 180),
        'starburst_base': (255, 255, 255),
        'starburst_twinkle': (255, 255, 200)
    },
    'purple': {
        'large_stars': [(200, 100, 255), (255, 120, 255)],  # Purple/magenta stars
        'meteor_gradient': [
            (255, 255, 255),    # White head
            (250, 240, 255),    # Pale purple
            (240, 220, 255),    # Light purple
            (220, 180, 255),    # Purple
            (200, 140, 255),    # Medium purple
            (160, 100, 220),    # Darker purple
            (120, 70, 180),     # Dark purple
            (70, 40, 120)       # Very dark purple
        ],
        'streak_color': (220, 150, 255),
        'satellite': (140, 120, 150),
        'planet': (180, 120, 255),
        'alien': (230, 190, 255),
        'starburst_base': (255, 255, 255),
        'starburst_twinkle': (240, 210, 255)
    },
    'cyan': {
        'large_stars': [(0, 255, 255), (100, 220, 255)],  # Cyan/aqua stars
        'meteor_gradient': [
            (255, 255, 255),    # White head
            (240, 255, 255),    # Pale cyan
            (220, 250, 255),    # Light cyan
            (180, 240, 255),    # Cyan
            (120, 220, 255),    # Medium cyan
            (80, 180, 220),     # Darker cyan
            (50, 130, 180),     # Dark cyan
            (30, 80, 120)       # Very dark cyan
        ],
        'streak_color': (150, 240, 255),
        'satellite': (120, 140, 150),
        'planet': (100, 220, 240),
        'alien': (200, 240, 255),
        'starburst_base': (255, 255, 255),
        'starburst_twinkle': (220, 250, 255)
    },
    'gray': {
        'large_stars': [(200, 200, 200), (160, 160, 160)],  # Gray/silver stars
        'meteor_gradient': [
            (255, 255, 255),    # White head
            (240, 240, 240),    # Very light gray
            (220, 220, 220),    # Light gray
            (190, 190, 190),    # Gray
            (160, 160, 160),    # Medium gray
            (130, 130, 130),    # Darker gray
            (100, 100, 100),    # Dark gray
            (60, 60, 60)        # Very dark gray
        ],
        'streak_color': (200, 200, 200),
        'satellite': (140, 140, 140),
        'planet': (180, 180, 180),
        'alien': (210, 210, 210),
        'starburst_base': (255, 255, 255),
        'starburst_twinkle': (230, 230, 230)
    },
    'pink': {
        'large_stars': [(255, 150, 200), (255, 180, 220)],  # Pink/magenta stars
        'meteor_gradient': [
            (255, 255, 255),    # White head
            (255, 240, 250),    # Pale pink
            (255, 220, 240),    # Light pink
            (255, 180, 220),    # Pink
            (255, 140, 200),    # Medium pink
            (220, 100, 160),    # Darker pink
            (180, 70, 120),     # Dark pink
            (120, 40, 80)       # Very dark pink
        ],
        'streak_color': (255, 180, 220),
        'satellite': (150, 120, 140),
        'planet': (255, 150, 200),
        'alien': (255, 200, 230),
        'starburst_base': (255, 255, 255),
        'starburst_twinkle': (255, 220, 240)
    },
    'orange': {
        'large_stars': [(255, 165, 0), (255, 140, 60)],  # Orange/amber stars
        'meteor_gradient': [
            (255, 255, 255),    # White head
            (255, 245, 230),    # Pale orange
            (255, 220, 180),    # Light orange
            (255, 190, 120),    # Orange
            (255, 160, 80),     # Medium orange
            (220, 130, 50),     # Darker orange
            (180, 100, 30),     # Dark orange
            (120, 60, 20)       # Very dark orange
        ],
        'streak_color': (255, 200, 120),
        'satellite': (150, 130, 110),
        'planet': (255, 180, 100),
        'alien': (255, 210, 170),
        'starburst_base': (255, 255, 255),
        'starburst_twinkle': (255, 230, 190)
    }
}


class Star:
    """Simple horizontal scrolling star with pre-calculated values."""

    def __init__(self, screen_width: int, screen_height: int, star_pool_index: int):
        # Pre-calculate all random values to avoid spikes during reset
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.pool_index = star_pool_index

        # Pre-calculated random values
        self.spawn_offset = random.randint(0, 50)
        self.size_level = self._calculate_size_level()
        self.speed = self._calculate_speed()
        self.reset_stagger = (star_pool_index * 0.1) % 2.0  # Stagger resets by pool index

        # Cached color for this star
        self.cached_color_attr = None

        self.reset_position()
        # For initial setup, randomize position across entire screen
        self.x = float(random.randint(0, screen_width - 1))

    def _calculate_size_level(self) -> int:
        """Pre-calculate size level to avoid random calls during reset."""
        rand = random.random()
        if rand < 0.5:      # 50% chance - small
            return 0
        elif rand < 0.75:   # 25% chance - large
            return 1
        else:               # 25% chance - medium
            return 2

    def _calculate_speed(self) -> float:
        """Pre-calculate speed based on size level."""
        if self.size_level == 0:    # Small dots
            return 0.4
        elif self.size_level == 1:  # Large (blue/purple, fastest)
            return 1.0
        else:                       # Medium (darker blue/purple, slowest)
            return 0.7

    def reset_position(self):
        """Reset star to right edge using pre-calculated values."""
        # Use pre-calculated offset (no random calls)
        self.x = float(self.screen_width + self.spawn_offset)
        self.y = random.randint(0, self.screen_height - 1)  # Only random call needed

    def update(self, dt: float):
        """Move star left at its fractional speed with staggered reset."""
        # Direct fractional positioning like rain project
        self.x -= self.speed

        # Staggered reset to avoid CPU spikes
        if self.x < (-10 - self.reset_stagger):
            self.reset_position()
            # Note: cached_color_attr persists across resets (only cleared on color scheme change)

    def get_screen_position(self) -> tuple:
        """Get screen position (convert float to integer for rendering)."""
        return (int(self.x), self.y)

    def get_size_level(self) -> int:
        """Get size level."""
        return self.size_level


class SpaceEvent:
    """Base class for space events like starbursts, supernovas, etc."""

    def __init__(self, center_x: int, center_y: int):
        self.center_x = center_x
        self.center_y = center_y
        self.start_time = time.time()
        self.active = True

    def update(self) -> bool:
        """Update event state. Returns True if event should continue, False if finished."""
        return self.active

    def get_render_points(self) -> List[tuple]:
        """Get list of (x, y, char, color) tuples to render."""
        return []

    def finish(self):
        """Mark event as finished."""
        self.active = False


class HorizontalMeteorEvent(SpaceEvent):
    """Horizontal meteor moving left with gradient trail."""

    def __init__(self, start_x: int, start_y: int, palette: dict):
        super().__init__(start_x, start_y)
        self.x = float(start_x)
        self.y = start_y
        self.speed = 0.8  # Horizontal speed moving left (similar to star speeds)
        self.max_trail_length = 60  # Trail length (almost doubled for horizontal)
        self.trail = deque(maxlen=self.max_trail_length)  # Deque for O(1) operations
        self.trail_timer = 0.0
        self.duration = 8.0  # Event lasts 8 seconds
        self.head_char = '*'
        self.palette = palette

        # Pre-compute gradient colors (eliminates 60 conditional chains per frame)
        self.gradient_colors = palette['meteor_gradient']

    def update(self) -> bool:
        elapsed = time.time() - self.start_time

        if elapsed >= self.duration:
            self.finish()
            return False

        # Store current position before updating
        current_x = int(self.x)
        current_y = self.y

        # Move left
        self.x -= self.speed

        # Add trail points every frame (deque automatically discards oldest when full)
        self.trail.append((current_x, current_y))

        return True

    def get_render_points(self) -> List[tuple]:
        points = []

        # Draw head
        head_x = int(self.x)
        head_y = self.y
        points.append((head_x, head_y, self.head_char, self.gradient_colors[0]))  # White head

        # Draw trail with pre-computed gradient colors (40-50% faster)
        trail_length = len(self.trail)
        trail_length_70 = int(trail_length * 0.7)
        trail_length_90 = int(trail_length * 0.9)

        for i, (trail_x, trail_y) in enumerate(self.trail):
            segments_from_head = trail_length - 1 - i
            trail_progress = segments_from_head / max(trail_length - 1, 1)

            # Map progress directly to gradient index (no conditionals)
            # 8 gradient steps: map 0.0-1.0 to 0-7
            gradient_index = min(int(trail_progress * 7.999), 7)
            trail_color = self.gradient_colors[gradient_index]

            # Use horizontal streak characters
            if segments_from_head <= trail_length_70:
                trail_char = '-'
            elif segments_from_head <= trail_length_90:
                trail_char = '·'
            else:
                trail_char = '•'

            points.append((trail_x, trail_y, trail_char, trail_color))

        return points


class YellowStreakEvent(SpaceEvent):
    """Fast yellow streak with white trail."""

    def __init__(self, start_x: int, start_y: int, palette: dict):
        super().__init__(start_x, start_y)
        self.x = float(start_x)
        self.y = start_y
        self.speed = 1.2  # Faster than comet
        self.max_trail_length = 15  # Quarter of comet length
        self.trail = deque(maxlen=self.max_trail_length)  # Deque for O(1) operations
        self.duration = 6.0  # Event duration
        self.head_char = '𖥔'
        self.palette = palette

    def update(self) -> bool:
        elapsed = time.time() - self.start_time

        if elapsed >= self.duration:
            self.finish()
            return False

        # Store current position before updating
        current_x = int(self.x)
        current_y = self.y

        # Move left fast
        self.x -= self.speed

        # Add trail points every frame (deque automatically discards oldest when full)
        self.trail.append((current_x, current_y))

        return True

    def get_render_points(self) -> List[tuple]:
        points = []

        # Draw head
        head_x = int(self.x)
        head_y = self.y
        points.append((head_x, head_y, self.head_char, self.palette['streak_color']))

        # Draw trail with white gradient (always white for contrast)
        trail_length = len(self.trail)
        for i, (trail_x, trail_y) in enumerate(self.trail):
            segments_from_head = trail_length - 1 - i
            trail_progress = segments_from_head / max(trail_length - 1, 1)

            # White gradient from bright to dimmer
            if trail_progress <= 0.3:  # Bright white: front 30%
                trail_color = (255, 255, 255)
            elif trail_progress <= 0.6:  # Medium white: next 30%
                trail_color = (200, 200, 200)
            else:  # Dimmer white: final 40%
                trail_color = (150, 150, 150)

            # Use horizontal streak characters
            if segments_from_head <= int(trail_length * 0.7):
                trail_char = '-'
            elif segments_from_head <= int(trail_length * 0.9):
                trail_char = '·'
            else:
                trail_char = '•'

            points.append((trail_x, trail_y, trail_char, trail_color))

        return points


class SatelliteEvent(SpaceEvent):
    """Small grey satellite moving horizontally."""

    def __init__(self, start_x: int, start_y: int, palette: dict):
        super().__init__(start_x, start_y)
        self.x = float(start_x)
        self.y = start_y
        self.speed = 0.4  # Same speed as small stars
        self.duration = 10.0  # Moderate duration
        self.satellite_pattern = "=O="
        self.palette = palette

    def update(self) -> bool:
        elapsed = time.time() - self.start_time

        if elapsed >= self.duration:
            self.finish()
            return False

        # Move left slowly
        self.x -= self.speed

        return True

    def get_render_points(self) -> List[tuple]:
        points = []

        # Draw satellite pattern =O=
        satellite_x = int(self.x)
        satellite_y = self.y
        satellite_color = self.palette['satellite']

        for i, char in enumerate(self.satellite_pattern):
            points.append((satellite_x + i - 1, satellite_y, char, satellite_color))  # Center the 3-char pattern

        return points


class PlanetEvent(SpaceEvent):
    """Green planet moving horizontally with 2-line ASCII art."""

    def __init__(self, start_x: int, start_y: int, palette: dict):
        super().__init__(start_x, start_y)
        self.x = float(start_x)
        self.y = start_y
        self.speed = 0.4  # Same speed as small stars
        self.duration = 12.0  # Longer duration for planet
        self.planet_lines = [".-.", "`-'"]
        self.palette = palette

    def update(self) -> bool:
        elapsed = time.time() - self.start_time

        if elapsed >= self.duration:
            self.finish()
            return False

        # Move left slowly
        self.x -= self.speed

        return True

    def get_render_points(self) -> List[tuple]:
        points = []

        # Draw planet as 2-line ASCII art
        planet_x = int(self.x)
        planet_y = self.y
        planet_color = self.palette['planet']

        # Top line: ".-."
        if planet_y > 0:  # Make sure there's space above
            for i, char in enumerate(".-."):
                points.append((planet_x + i, planet_y - 1, char, planet_color))

        # Bottom line: "`-'"
        for i, char in enumerate("`-'"):
            points.append((planet_x + i, planet_y, char, planet_color))

        return points


class AlienEvent(SpaceEvent):
    """Alien event using .-=-. pattern."""

    def __init__(self, start_x: int, start_y: int, palette: dict):
        super().__init__(start_x, start_y)
        self.x = float(start_x)
        self.y = start_y
        self.speed = 0.4  # Same speed as small white stars
        self.duration = 10.0  # Event duration
        self.alien_pattern = ".-=-."
        self.palette = palette

    def update(self) -> bool:
        elapsed = time.time() - self.start_time

        if elapsed >= self.duration:
            self.finish()
            return False

        # Move left slowly
        self.x -= self.speed

        return True

    def get_render_points(self) -> List[tuple]:
        points = []

        # Draw alien pattern
        alien_x = int(self.x)
        alien_y = self.y
        alien_color = self.palette['alien']

        for i, char in enumerate(self.alien_pattern):
            points.append((alien_x + i, alien_y, char, alien_color))

        return points


class StarburstEvent(SpaceEvent):
    """Custom starburst event with specific pattern: . ; - --+- - ! '"""

    def __init__(self, center_x: int, center_y: int, palette: dict):
        super().__init__(center_x, center_y)
        self.phase = "expand"  # expand, twinkle, contract
        self.expand_duration = 0.3
        self.twinkle_duration = 0.2
        self.contract_duration = 0.2

        # Specific pattern relative to center (+) - ordered by distance from center
        self.pattern = [
            (0, 0, '+'),    # Center - distance 0
            (0, -1, ';'),   # Above center - distance 1
            (-1, 0, '-'),   # Left near - distance 1
            (1, 0, '-'),    # Right near - distance 1
            (0, 1, '!'),    # Below center - distance 1
            (-2, 0, '-'),   # Left - distance 2
            (0, -2, '.'),   # Top - distance 2
            (0, 2, "'"),    # Bottom - distance 2
            (3, 0, '-'),    # Right side - distance 3
            (-4, 0, '-'),   # Left side - distance 4
        ]
        self.twinkle_chars = ['+', '*', '◊', '○']
        self.twinkle_frame = 0
        self.palette = palette

    def update(self) -> bool:
        elapsed = time.time() - self.start_time

        if self.phase == "expand" and elapsed >= self.expand_duration:
            self.phase = "twinkle"
            self.start_time = time.time()
        elif self.phase == "twinkle" and elapsed >= self.twinkle_duration:
            self.phase = "contract"
            self.start_time = time.time()
        elif self.phase == "contract" and elapsed >= self.contract_duration:
            self.finish()
            return False

        return True

    def get_render_points(self) -> List[tuple]:
        elapsed = time.time() - self.start_time
        points = []

        if self.phase == "expand":
            # Show pattern appearing gradually
            progress = elapsed / self.expand_duration
            visible_count = int(progress * len(self.pattern))

            for i in range(visible_count):
                dx, dy, char = self.pattern[i]
                x = self.center_x + dx
                y = self.center_y + dy
                color = self.palette['starburst_base']
                points.append((x, y, char, color))

        elif self.phase == "twinkle":
            # Show full pattern with center twinkling
            self.twinkle_frame = int(elapsed * 10) % len(self.twinkle_chars)

            for dx, dy, char in self.pattern:
                x = self.center_x + dx
                y = self.center_y + dy

                # Twinkle only the center + character
                if char == '+':
                    char = self.twinkle_chars[self.twinkle_frame]
                    color = self.palette['starburst_twinkle']
                else:
                    color = self.palette['starburst_base']

                points.append((x, y, char, color))

        elif self.phase == "contract":
            # Show pattern disappearing gradually - from outer elements back to center
            progress = elapsed / self.contract_duration
            visible_count = len(self.pattern) - int(progress * len(self.pattern))

            for i in range(visible_count):
                dx, dy, char = self.pattern[i]
                x = self.center_x + dx
                y = self.center_y + dy
                # Dim the base color for contract phase
                base = self.palette['starburst_base']
                color = (int(base[0] * 0.7), int(base[1] * 0.7), int(base[2] * 0.7))
                points.append((x, y, char, color))

        return points


class Space(BaseAnimationMode):
    """Space starfield animation with cosmic movement and parallax."""

    def __init__(self):
        super().__init__("Space")
        self.stars: List[Star] = []
        self.num_stars = 120  # Reduced for performance
        self.color_adapter = CursesColorAdapter()
        # Event system
        self.events: List[SpaceEvent] = []
        self.event_timer = 0.0
        self.next_event_delay = random.uniform(5.0, 10.0)  # 5-10 seconds between events
        self.intense_mode = False
        # Lookup tables for performance
        self.size_chars = ['.', 'o', '+', '*']  # 0=smallest, 3=largest

        # Color scheme setup
        self.available_colors = ['blue', 'red', 'green', 'yellow', 'purple', 'cyan', 'gray', 'pink', 'orange']
        self.color_scheme = 'blue'  # Default: cool cosmic blue
        self.current_color_index = self.available_colors.index('blue')
        self.current_palette = SPACE_PALETTES['blue']

        # Initialize color table with default palette
        self.color_table = [
            [(255, 255, 255)],                # Level 0: white (small stars)
            self.current_palette['large_stars'],  # Level 1: large colored stars
            [(int(c[0] * 0.7), int(c[1] * 0.7), int(c[2] * 0.7)) for c in self.current_palette['large_stars']],  # Level 2: darker versions
            self.current_palette['large_stars']   # Level 3: unused
        ]

    def set_intense_mode(self, intense: bool):
        """Set intense mode for faster event spawning."""
        self.intense_mode = intense

    def on_color_change(self):
        """Handle color scheme changes."""
        # Update to new palette
        self.current_palette = SPACE_PALETTES[self.color_scheme]

        # Update color table with new palette
        self.color_table = [
            [(255, 255, 255)],                # Level 0: white (small stars)
            self.current_palette['large_stars'],  # Level 1: large colored stars
            [(int(c[0] * 0.7), int(c[1] * 0.7), int(c[2] * 0.7)) for c in self.current_palette['large_stars']],  # Level 2: darker versions
            self.current_palette['large_stars']   # Level 3: unused
        ]

        # Clear color adapter cache and reset counter
        clear_color_cache(self.color_adapter)

        # Regenerate all cached star colors with new palette
        for star in self.stars:
            size_level = star.size_level
            color_options = self.color_table[size_level]
            bold = size_level >= 2
            color = color_options[star.pool_index % len(color_options)]
            star.cached_color_attr = self.color_adapter.get_color_attr(color, bold=bold)

    def initialize_mode_variables(self) -> None:
        """Initialize space mode specific variables."""
        self.stars.clear()
        self.events.clear()
        self.event_timer = 0.0
        # Set initial delay based on intense mode
        if self.intense_mode:
            self.next_event_delay = random.uniform(3.0, 6.0)
        else:
            self.next_event_delay = random.uniform(5.0, 10.0)
        self.color_adapter.initialize_colors()

        # Pre-group stars by size level for optimized rendering
        # Eliminates 3 list allocations + grouping loop per frame
        self.stars_by_level = [[], [], []]

        # Create horizontal scrolling starfield with pool indices
        for i in range(self.num_stars):
            star = Star(self.max_cols, self.max_rows, i)
            self.stars.append(star)

            # Pre-group by size level and pre-compute color attribute
            size_level = star.size_level
            color_options = self.color_table[size_level]
            bold = size_level >= 2
            color = color_options[star.pool_index % len(color_options)]
            star.cached_color_attr = self.color_adapter.get_color_attr(color, bold=bold)

            # Add to appropriate size level group
            self.stars_by_level[size_level].append(star)

    def update_animation_state(self, update_interval: float) -> None:
        """Update space animation state."""
        dt = update_interval

        # Update all stars with dt for staggered timing
        for star in self.stars:
            star.update(dt)

        # Update events
        self.events = [event for event in self.events if event.update()]

        # Spawn new events
        self.event_timer += dt
        if self.event_timer >= self.next_event_delay:
            self._spawn_event()
            self.event_timer = 0.0
            # Set next delay based on intense mode
            if self.intense_mode:
                self.next_event_delay = random.uniform(3.0, 6.0)
            else:
                self.next_event_delay = random.uniform(5.0, 10.0)

    def _spawn_event(self):
        """Spawn a random space event."""
        # Choose event type randomly
        rand = random.random()
        if rand < 0.1:  # 10% chance for starburst
            # Random position near center area (avoid edges)
            center_x = self.max_cols // 2 + random.randint(-10, 10)
            center_y = self.max_rows // 2 + random.randint(-5, 5)
            event = StarburstEvent(center_x, center_y, self.current_palette)
        elif rand < 0.2:  # 10% chance for satellite
            # Start from right edge, random Y position
            start_x = self.max_cols + 5  # Start off-screen right
            start_y = random.randint(2, max(2, self.max_rows - 3))  # Random Y within bounds
            event = SatelliteEvent(start_x, start_y, self.current_palette)
        elif rand < 0.3:  # 10% chance for planet
            # Start from right edge, random Y position (needs space above for 2-line art)
            start_x = self.max_cols + 5  # Start off-screen right
            start_y = random.randint(3, max(3, self.max_rows - 2))  # Random Y with space above/below
            event = PlanetEvent(start_x, start_y, self.current_palette)
        elif rand < 0.35:  # 5% chance for alien
            # Start from right edge, random Y position
            start_x = self.max_cols + 5  # Start off-screen right
            start_y = random.randint(2, max(2, self.max_rows - 3))  # Random Y within bounds
            event = AlienEvent(start_x, start_y, self.current_palette)
        elif rand < 0.65:  # 30% chance for yellow streak
            # Start from right edge, random Y position
            start_x = self.max_cols + 5  # Start off-screen right
            start_y = random.randint(2, max(2, self.max_rows - 3))  # Random Y within bounds
            event = YellowStreakEvent(start_x, start_y, self.current_palette)
        else:  # 35% chance for comet
            # Start from right edge, random Y position
            start_x = self.max_cols + 5  # Start off-screen right
            start_y = random.randint(2, max(2, self.max_rows - 3))  # Random Y within bounds
            event = HorizontalMeteorEvent(start_x, start_y, self.current_palette)

        self.events.append(event)

    def draw_frame(self) -> None:
        """Draw the horizontal scrolling starfield and events."""
        # Draw stars by size level using pre-grouped lists (30-40% faster)
        for size_level in range(3):
            char = self.size_chars[size_level]

            for star in self.stars_by_level[size_level]:
                screen_x, screen_y = star.get_screen_position()
                if 0 <= screen_x < self.max_cols and 0 <= screen_y < self.max_rows:
                    # Use pre-computed color attribute (regenerate if None)
                    if star.cached_color_attr is None:
                        color_options = self.color_table[size_level]
                        bold = size_level >= 2
                        color = color_options[star.pool_index % len(color_options)]
                        star.cached_color_attr = self.color_adapter.get_color_attr(color, bold=bold)
                    self.safe_addstr(screen_y, screen_x, char, star.cached_color_attr)

        # Draw events (rendered on top of stars)
        for event in self.events:
            for x, y, char, color in event.get_render_points():
                if 0 <= x < self.max_cols and 0 <= y < self.max_rows:
                    attr = self.color_adapter.get_color_attr(color, bold=True)
                    self.safe_addstr(y, x, char, attr)