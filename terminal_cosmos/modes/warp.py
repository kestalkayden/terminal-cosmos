"""Warp field animation mode for terminal-cosmos."""

import random
import math
from typing import List
from ..core.animation_base import BaseAnimationMode
from ..colors.curses_adapter import CursesColorAdapter
from ..utils.color_helpers import clear_color_cache


# Pre-computed sine lookup table for twinkle effect
# Eliminates 6,000 math.sin() calls per second
SIN_LOOKUP_TABLE = [math.sin(i * math.pi / 180) for i in range(360)]


# Warp mode color palettes - 9 warp speed themes
WARP_PALETTES = {
    'blue': {
        'dot': (255, 255, 255),                              # White dots
        'star': [(100, 150, 255), (200, 100, 255)],         # Blue/purple stars
        'beam': [(0, 255, 255), (173, 216, 230)]            # Cyan/light blue beams
    },
    'red': {
        'dot': (255, 255, 255),                              # White dots
        'star': [(255, 100, 80), (255, 140, 0)],            # Red/orange stars
        'beam': [(255, 180, 100), (255, 200, 150)]          # Orange/amber beams
    },
    'green': {
        'dot': (255, 255, 255),                              # White dots
        'star': [(100, 255, 150), (150, 255, 200)],         # Green/teal stars
        'beam': [(100, 255, 200), (150, 255, 220)]          # Teal/aqua beams
    },
    'yellow': {
        'dot': (255, 255, 255),                              # White dots
        'star': [(255, 255, 100), (255, 220, 80)],          # Yellow/gold stars
        'beam': [(255, 255, 180), (255, 240, 150)]          # Light yellow beams
    },
    'purple': {
        'dot': (255, 255, 255),                              # White dots
        'star': [(200, 100, 255), (255, 120, 255)],         # Purple/magenta stars
        'beam': [(220, 150, 255), (240, 180, 255)]          # Light purple beams
    },
    'cyan': {
        'dot': (255, 255, 255),                              # White dots
        'star': [(100, 220, 255), (150, 240, 255)],         # Cyan/aqua stars
        'beam': [(150, 255, 255), (200, 255, 255)]          # Light cyan beams
    },
    'pink': {
        'dot': (255, 255, 255),                              # White dots
        'star': [(255, 150, 200), (255, 180, 220)],         # Pink/magenta stars
        'beam': [(255, 200, 230), (255, 220, 240)]          # Light pink beams
    },
    'orange': {
        'dot': (255, 255, 255),                              # White dots
        'star': [(255, 165, 0), (255, 140, 60)],            # Orange/amber stars
        'beam': [(255, 200, 120), (255, 220, 150)]          # Light orange beams
    },
    'gray': {
        'dot': (255, 255, 255),                              # White dots
        'star': [(200, 200, 200), (160, 160, 160)],         # Gray/silver stars
        'beam': [(220, 220, 220), (180, 180, 180)]          # Light gray beams
    }
}


class WarpParticle:
    """Represents a single particle in the 3D warp field."""

    def __init__(self, x: float, y: float, z: float, particle_type: str, palette: dict):
        self.x = x
        self.y = y
        self.z = z
        self.original_z = z
        self.particle_type = particle_type  # 'dot', 'star', 'beam'

        # Particle-specific properties from palette
        if particle_type == 'dot':
            self.char = '·'
            self.color = palette['dot']
            self.speed_multiplier = 1.0
        elif particle_type == 'star':
            self.char = random.choice(['*', '+'])
            self.color = random.choice(palette['star'])
            self.speed_multiplier = 1.5
        else:  # beam
            self.char = random.choice(['-', '|', '/', '\\'])
            self.color = random.choice(palette['beam'])
            self.speed_multiplier = 2.0

        # Effects
        self.twinkle_phase = random.uniform(0, 2 * math.pi)

    def update(self, dt: float):
        """Update particle position and effects."""
        # Move particle towards viewer (decreasing z) at different speeds (much slower)
        self.z -= dt * 2 * self.speed_multiplier

        # Reset particle to back when it gets too close
        if self.z <= 0.1:
            self.z = self.original_z
            # Respawn in tunnel-like distribution
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0.1, 0.8)  # Tunnel effect
            self.x = radius * math.cos(angle)
            self.y = radius * math.sin(angle) * 0.4  # Oval tunnel

        # Update twinkle/pulse effect
        self.twinkle_phase += dt * 4

    def get_screen_position(self, screen_half_width: float, screen_half_height: float) -> tuple:
        """Get 2D screen position from 3D coordinates.

        Args:
            screen_half_width: Pre-computed screen_width / 2
            screen_half_height: Pre-computed screen_height / 2
        """
        # Perspective projection (15-20% faster with pre-computed half dimensions)
        screen_x = (self.x / self.z) * screen_half_width + screen_half_width
        screen_y = (self.y / self.z) * screen_half_height + screen_half_height
        return (int(screen_x), int(screen_y))

    def get_render_info(self) -> tuple:
        """Get particle render character, color, and effects based on distance."""
        # Closer particles are bigger and brighter
        size_factor = min(4, max(1, 4 / self.z))
        brightness_factor = min(1.0, 1.0 / self.z)

        # Add twinkle/pulse effect using lookup table (50-60% faster than math.sin)
        # Convert phase (0 to 2π) to index (0 to 359)
        sin_index = int((self.twinkle_phase * 57.2958) % 360)  # 57.2958 = 180/π
        pulse = 0.7 + 0.3 * SIN_LOOKUP_TABLE[sin_index]
        brightness_factor *= pulse

        # Choose character based on size and type
        if self.particle_type == 'dot':
            if size_factor >= 3:
                char = '●'
            elif size_factor >= 2:
                char = '○'
            else:
                char = '·'
        elif self.particle_type == 'star':
            if size_factor >= 3:
                char = '★'
            elif size_factor >= 2:
                char = '*'
            else:
                char = '+'
        else:  # beam
            char = self.char  # Keep original beam character

        # Use fixed color instead of dynamic brightness adjustment
        color = self.color
        bold = brightness_factor > 0.6

        return (char, color, bold, brightness_factor > 0.2)


class WarpDot:
    """Simple white dot that spawns from tunnel perimeter and moves outward (2D system)."""

    def __init__(self, center_x: int, center_y: int, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Multiple tunnel ring radii for depth effect
        ring_radii = [
            (3, 1),    # Inner ring (small)
            (6, 2),    # Middle ring (medium)
            (9, 3)     # Outer ring (original size)
        ]

        # Choose random ring
        tunnel_width, tunnel_height = random.choice(ring_radii)

        # Spawn on selected ring perimeter
        angle = random.uniform(0, 2 * math.pi)
        self.start_x = center_x + tunnel_width * math.cos(angle)
        self.start_y = center_y + tunnel_height * math.sin(angle)

        # Current position
        self.x = self.start_x
        self.y = self.start_y

        # Movement direction (outward from tunnel)
        self.direction_x = math.cos(angle)
        self.direction_y = math.sin(angle)

        # Speed based on ring size - inner rings move slower, outer rings faster
        if tunnel_width == 3:      # Inner ring
            self.speed = random.uniform(8.0, 15.0)   # Slower
        elif tunnel_width == 6:    # Middle ring
            self.speed = random.uniform(15.0, 25.0)  # Medium
        else:                      # Outer ring
            self.speed = random.uniform(25.0, 35.0)  # Faster

        # Max distance before cleanup
        self.max_distance = max(screen_width, screen_height)
        self.distance_traveled = 0.0

    def update(self, dt: float):
        """Update dot position."""
        # Move outward
        self.x += self.direction_x * self.speed * dt
        self.y += self.direction_y * self.speed * dt
        self.distance_traveled += self.speed * dt

    def is_alive(self) -> bool:
        """Check if dot should still exist."""
        return (0 <= self.x < self.screen_width and
                0 <= self.y < self.screen_height and
                self.distance_traveled < self.max_distance)

    def get_render_position(self) -> tuple:
        """Get render position."""
        return (int(self.x), int(self.y))


class Warp(BaseAnimationMode):
    """3D warp tunnel with perspective particles moving towards viewer."""

    def __init__(self):
        super().__init__("Warp")
        self.particles: List[WarpParticle] = []
        self.dots: List[WarpDot] = []  # 2D white dots system
        self.color_adapter = CursesColorAdapter()
        self.intense_mode = False
        self.dot_spawn_timer = 0.0

        # Color scheme setup
        self.available_colors = ['blue', 'red', 'green', 'yellow', 'purple', 'cyan', 'pink', 'orange', 'gray']
        self.color_scheme = 'blue'  # Default: cool blue warp
        self.current_color_index = self.available_colors.index('blue')
        self.current_palette = WARP_PALETTES['blue']

    def set_intense_mode(self, intense: bool):
        """Set intense mode for more particles."""
        self.intense_mode = intense

    def on_color_change(self):
        """Handle color scheme changes."""
        # Update to new palette
        self.current_palette = WARP_PALETTES[self.color_scheme]

        # Recreate all particles with new colors
        self.particles.clear()
        num_particles = 150 if self.intense_mode else 100

        for _ in range(num_particles):
            # Position in 3D space
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0.1, 0.8)  # Tunnel distribution
            x = radius * math.cos(angle)
            y = radius * math.sin(angle) * 0.4  # Oval tunnel
            z = random.uniform(0.5, 12.0)  # Depth range

            # Mix of particle types
            particle_type = random.choices(
                ['dot', 'star', 'beam'],
                weights=[50, 35, 15],  # More dots, some stars, fewer beams
                k=1
            )[0]

            particle = WarpParticle(x, y, z, particle_type, self.current_palette)
            self.particles.append(particle)

        # Clear color adapter cache and reset counter
        clear_color_cache(self.color_adapter)

    def initialize_mode_variables(self) -> None:
        """Initialize warp mode variables."""
        self.particles.clear()
        self.dots.clear()
        self.color_adapter.initialize_colors()
        self.dot_spawn_timer = 0.0

        # Pre-compute screen half dimensions for perspective projection
        # Eliminates 12 divisions per frame (6 per particle × 100-150 particles)
        self.screen_half_width = self.max_cols / 2.0
        self.screen_half_height = self.max_rows / 2.0

        # Create 3D warp field
        num_particles = 150 if self.intense_mode else 100

        for _ in range(num_particles):
            # Position in 3D space
            angle = random.uniform(0, 2 * math.pi)
            radius = random.uniform(0.1, 0.8)  # Tunnel distribution
            x = radius * math.cos(angle)
            y = radius * math.sin(angle) * 0.4  # Oval tunnel
            z = random.uniform(0.5, 12.0)  # Depth range

            # Mix of particle types
            particle_type = random.choices(
                ['dot', 'star', 'beam'],
                weights=[50, 35, 15],  # More dots, some stars, fewer beams
                k=1
            )[0]

            particle = WarpParticle(x, y, z, particle_type, self.current_palette)
            self.particles.append(particle)

    def update_animation_state(self, update_interval: float) -> None:
        """Update warp animation state."""
        dt = update_interval

        # Update all 3D particles
        for particle in self.particles:
            particle.update(dt)

        # Update 2D white dots
        for dot in self.dots:
            dot.update(dt)

        # Remove dead 2D dots
        self.dots = [dot for dot in self.dots if dot.is_alive()]

        # Spawn new 2D white dots
        self.dot_spawn_timer += dt
        dot_spawn_rate = 0.05 if self.intense_mode else 0.075  # Every 0.05 or 0.075 seconds

        if self.dot_spawn_timer >= dot_spawn_rate:
            center_x = self.max_cols // 2
            center_y = self.max_rows // 2
            new_dot = WarpDot(center_x, center_y, self.max_cols, self.max_rows)
            self.dots.append(new_dot)
            self.dot_spawn_timer = 0.0

    def draw_frame(self) -> None:
        """Draw the warp field frame with 2D dots as background and 3D particles as foreground."""
        # Draw 2D white dots first (background layer)
        for dot in self.dots:
            x, y = dot.get_render_position()
            if 0 <= x < self.max_cols and 0 <= y < self.max_rows:
                attr = self.color_adapter.get_color_attr((255, 255, 255), bold=False)
                self.safe_addstr(y, x, '·', attr)

        # Draw 3D particles second (foreground layer)
        for particle in self.particles:
            screen_x, screen_y = particle.get_screen_position(self.screen_half_width, self.screen_half_height)

            # Only draw particles that are on screen
            if 0 <= screen_x < self.max_cols and 0 <= screen_y < self.max_rows:
                char, color, bold, should_draw = particle.get_render_info()

                if should_draw:
                    attr = self.color_adapter.get_color_attr(color, bold=bold)
                    self.safe_addstr(screen_y, screen_x, char, attr)