"""Fireworks animation mode for terminal-cosmos."""

import random
import math
from collections import deque
from typing import List, Tuple
from ..core.animation_base import BaseAnimationMode
from ..colors.curses_adapter import CursesColorAdapter
from ..utils.color_helpers import clear_color_cache, build_multi_gradient_cache


# Fireworks mode color palettes - 9 celebratory schemes
FIREWORKS_PALETTES = {
    'red': [(255, 50, 50), (255, 100, 80), (255, 180, 150), (255, 220, 200)],
    'blue': [(50, 100, 255), (80, 150, 255), (150, 200, 255), (200, 230, 255)],
    'green': [(50, 255, 100), (100, 255, 150), (150, 255, 200), (200, 255, 230)],
    'yellow': [(255, 220, 50), (255, 240, 100), (255, 250, 180), (255, 255, 220)],
    'purple': [(180, 50, 255), (200, 100, 255), (220, 150, 255), (240, 200, 255)],
    'cyan': [(50, 255, 255), (100, 255, 255), (180, 255, 255), (220, 255, 255)],
    'pink': [(255, 100, 180), (255, 150, 200), (255, 200, 230), (255, 230, 245)],
    'orange': [(255, 140, 50), (255, 180, 100), (255, 210, 150), (255, 235, 200)],
    'gray': [(150, 150, 150), (180, 180, 180), (210, 210, 210), (240, 240, 240)],
    'white': [(200, 200, 200), (220, 220, 220), (240, 240, 240), (255, 255, 255)]  # For crackling whistlers
}


class FireworkParticle:
    """Particle from firework explosion with trail."""

    # Pre-computed character choices (class variable)
    CHARS = ['.', '*', '+', 'o']

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0  # Velocity X
        self.vy = 0.0  # Velocity Y
        self.life = 0.0  # Remaining lifetime
        self.max_life = 0.0
        self.trail = deque(maxlen=12)  # Longer trails for visible streaks
        self.active = False
        self.char = '*'  # Pre-computed character for this particle
        self.color_scheme = 'red'  # Color scheme for this particle's explosion

    def reset(self, x: float, y: float, angle: float, speed: float, life: float, color_scheme: str = 'red', horizontal_bias: float = 1.0):
        """Reset particle for explosion."""
        self.x = x
        self.y = y
        # Convert angle to velocity components
        base_vx = math.cos(angle) * speed
        base_vy = math.sin(angle) * speed

        # Apply horizontal bias (emphasize horizontal spread, reduce vertical)
        self.vx = base_vx * horizontal_bias
        self.vy = base_vy * (1.0 / horizontal_bias)  # Reduce vertical proportionally

        self.life = life
        self.max_life = life
        self.trail.clear()
        self.active = True
        # Pre-compute character once per particle
        self.char = random.choice(self.CHARS)
        self.color_scheme = color_scheme

    def update(self, dt: float, gravity: float = 2.5):
        """Update particle position with reduced gravity for floaty feel."""
        if not self.active:
            return

        # Apply velocity
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Apply gravity (downward) - reduced to 2.5 for very floaty feel
        self.vy += gravity * dt

        # Store trail position
        self.trail.append((int(self.x), int(self.y)))

        # Decrease life
        self.life -= dt
        if self.life <= 0:
            self.active = False


class CrackleBurst:
    """Delayed crackle burst point for chain reaction effect."""

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.delay = 0.0  # Time until this burst activates
        self.active = False

    def reset(self, x: float, y: float, delay: float):
        """Reset crackle burst with position and delay."""
        self.x = x
        self.y = y
        self.delay = delay
        self.active = True

    def update(self, dt: float):
        """Update delay timer."""
        if self.active:
            self.delay -= dt
            if self.delay <= 0:
                return True  # Ready to burst
        return False


class Rocket:
    """Rocket that launches and explodes."""

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.vy = 0.0  # Upward velocity
        self.target_y = 0
        self.trail = deque(maxlen=5)  # Shorter trail for rocket
        self.active = False
        self.exploded = False

    def reset(self, x: float, y: float, target_y: int, speed: float):
        """Reset rocket for launch."""
        self.x = x
        self.y = y
        self.vy = -speed  # Negative for upward movement
        self.target_y = target_y
        self.trail.clear()
        self.active = True
        self.exploded = False

    def update(self, dt: float):
        """Update rocket position."""
        if not self.active or self.exploded:
            return

        # Move upward
        self.y += self.vy * dt

        # Store trail position
        self.trail.append((int(self.x), int(self.y)))

        # Check if reached target height
        if self.y <= self.target_y:
            self.exploded = True
            self.active = False


class Fireworks(BaseAnimationMode):
    """Fireworks animation with launching rockets and explosive particles."""

    def __init__(self):
        super().__init__("Fireworks")
        self.color_adapter = CursesColorAdapter()

        # Color scheme setup (rainbow = multi-color mode)
        # Note: 'rainbow' is internal default, not in available_colors for CLI cycling
        self.available_colors = ['red', 'blue', 'green', 'yellow', 'purple', 'cyan', 'gray', 'pink', 'orange']
        self.color_scheme = 'rainbow'  # Default: multi-color fireworks!
        self.current_color_index = 0  # When cycling, starts at 'red'
        self.current_palette = None  # Not used in rainbow mode

        # Animation state
        self.rockets: List[Rocket] = []
        self.particles: List[FireworkParticle] = []
        self.crackle_bursts: List[CrackleBurst] = []
        self.rocket_pool: List[Rocket] = []
        self.particle_pool: List[FireworkParticle] = []
        self.crackle_burst_pool: List[CrackleBurst] = []

        self.launch_timer = 0.0
        self.intense_mode = False
        self.launch_interval = 0.8  # Launch rocket every 0.8 seconds (0.4 in intense mode)

        # Pre-computed trail colors (one cache per actual color)
        self.trail_color_caches = {}  # Dict mapping color_scheme -> trail_color_cache
        # Single color schemes for random selection in rainbow mode (not including white - that's for crackles)
        self.single_color_schemes = ['red', 'blue', 'green', 'yellow', 'purple', 'cyan', 'pink', 'orange', 'gray']

    def set_intense_mode(self, intense: bool) -> None:
        """Set intense mode for faster rocket launches."""
        self.intense_mode = intense

    def on_color_change(self):
        """Handle color scheme changes."""
        # Clear color adapter cache
        clear_color_cache(self.color_adapter)

        # Rebuild trail color caches
        self._build_trail_color_caches()

    def initialize_mode_variables(self) -> None:
        """Initialize fireworks mode variables."""
        self.color_adapter.initialize_colors()

        # Build trail color caches for all colors
        self._build_trail_color_caches()

        # Initialize object pools
        # Rocket pool (up to 4 simultaneous rockets)
        self.rocket_pool = [Rocket() for _ in range(4)]
        self.rockets = []

        # Particle pool (up to 600 particles total for burst + crackle fireworks)
        self.particle_pool = [FireworkParticle() for _ in range(600)]
        self.particles = []

        # Crackle burst pool (delayed burst points for chain reaction)
        self.crackle_burst_pool = [CrackleBurst() for _ in range(70)]
        self.crackle_bursts = []

        self.launch_timer = 0.0

    def _build_trail_color_caches(self):
        """Pre-compute trail colors for all color schemes."""
        # Build cache for each actual color (not rainbow) + white for crackles
        all_colors = self.single_color_schemes + ['white']
        fireworks_palettes_subset = {k: FIREWORKS_PALETTES[k] for k in all_colors}

        # Use utility function to build all gradient caches
        self.trail_color_caches = build_multi_gradient_cache(
            self.color_adapter,
            fireworks_palettes_subset,
            steps=20,
            with_bold=True
        )

    def _launch_rocket(self):
        """Launch a new rocket from bottom of screen."""
        if not self.rocket_pool:
            return

        # Pop rocket from pool
        rocket = self.rocket_pool.pop()

        # Random x position
        x = random.randint(10, max(10, self.max_cols - 10))

        # Start from bottom
        y = self.max_rows - 1

        # Random target height (upper third of screen)
        target_y = random.randint(5, max(5, self.max_rows // 3))

        # Slower launch speed for graceful rise
        speed = random.uniform(20, 30)

        rocket.reset(x, y, target_y, speed)
        self.rockets.append(rocket)

    def _explode_rocket(self, rocket: Rocket):
        """Create standard burst explosion at rocket position."""
        explosion_x = rocket.x
        explosion_y = rocket.y

        # Pick color for this explosion
        if self.color_scheme == 'rainbow':
            # Random color for each firework in rainbow mode
            explosion_color = random.choice(self.single_color_schemes)
        else:
            # Use selected single color
            explosion_color = self.color_scheme

        # Number of particles in explosion (balanced for performance)
        num_particles = random.randint(60, 100)

        for _ in range(num_particles):
            if not self.particle_pool:
                break

            # Pop particle from pool
            particle = self.particle_pool.pop()

            # Random angle (full circle)
            angle = random.uniform(0, 2 * math.pi)

            # Wide speed variation creates filled center effect
            # 40% slow (stay near center), 60% fast (expand outward)
            if random.random() < 0.4:
                # Slow particles - stay near center, fill the core
                speed = random.uniform(1.5, 5)
            else:
                # Fast particles - expand to outer shell
                speed = random.uniform(6, 12)

            # Longer lifetime so particles stay visible longer
            life = random.uniform(1.2, 2.0)

            # More balanced spread (reduced horizontal bias for more vertical spread too)
            particle.reset(explosion_x, explosion_y, angle, speed, life, explosion_color, horizontal_bias=1.3)
            self.particles.append(particle)

    def _explode_rocket_crackle(self, rocket: Rocket):
        """Create crackling whistler explosion - chain reaction of staggered white bursts."""
        center_x = rocket.x
        center_y = rocket.y

        # Create 25-32 burst points spread over wider area with staggered delays
        num_bursts = random.randint(25, 32)

        for i in range(num_bursts):
            if not self.crackle_burst_pool:
                break

            # Pop burst from pool
            burst = self.crackle_burst_pool.pop()

            # Spread bursts over wider area (up to 8 chars horizontally, 5 vertically)
            burst_x = center_x + random.uniform(-8, 8)
            burst_y = center_y + random.uniform(-5, 5)

            # Staggered delays create chain reaction effect
            # Earlier bursts = shorter delay, creating a cascading effect
            delay = i * random.uniform(0.02, 0.05)  # 0.02-0.05s between each burst

            burst.reset(burst_x, burst_y, delay)
            self.crackle_bursts.append(burst)

    def _trigger_crackle_burst(self, burst: CrackleBurst):
        """Trigger a single crackle burst - creates small particle explosion."""
        # Crackle fireworks are always white
        explosion_color = 'white'

        # Each burst point creates 6-10 particles
        num_particles = random.randint(6, 10)

        for _ in range(num_particles):
            if not self.particle_pool:
                break

            particle = self.particle_pool.pop()

            # Random angle from burst point
            angle = random.uniform(0, 2 * math.pi)

            # Very low speed - minimal expansion for tight crackle
            speed = random.uniform(0.5, 2.5)

            # Very short lifetime for quick pop effect
            life = random.uniform(0.3, 0.6)

            particle.reset(burst.x, burst.y, angle, speed, life, explosion_color)
            self.particles.append(particle)

    def update_animation_state(self, update_interval: float) -> None:
        """Update fireworks animation state."""
        dt = update_interval

        # Launch timer
        self.launch_timer += dt
        if self.launch_timer >= self.launch_interval:
            self._launch_rocket()
            self.launch_timer = 0.0
            # Vary launch interval slightly (faster in intense mode)
            if self.intense_mode:
                self.launch_interval = random.uniform(0.25, 0.55)  # 2x faster
            else:
                self.launch_interval = random.uniform(0.5, 1.1)

        # Update rockets
        i = 0
        while i < len(self.rockets):
            rocket = self.rockets[i]
            rocket.update(dt)

            if rocket.exploded:
                # 10% chance of crackling whistler, 90% normal burst
                if random.random() < 0.10:
                    self._explode_rocket_crackle(rocket)
                else:
                    self._explode_rocket(rocket)
                # Return to pool
                self.rockets.pop(i)
                self.rocket_pool.append(rocket)
            else:
                i += 1

        # Update particles
        i = 0
        while i < len(self.particles):
            particle = self.particles[i]
            particle.update(dt)

            if not particle.active:
                # Return to pool
                self.particles.pop(i)
                self.particle_pool.append(particle)
            else:
                i += 1

        # Update crackle bursts (delayed chain reaction)
        i = 0
        while i < len(self.crackle_bursts):
            burst = self.crackle_bursts[i]

            if burst.update(dt):  # Returns True when ready to burst
                # Trigger the burst
                self._trigger_crackle_burst(burst)
                # Return to pool
                self.crackle_bursts.pop(i)
                self.crackle_burst_pool.append(burst)
            else:
                i += 1

    def draw_frame(self) -> None:
        """Draw fireworks frame."""
        # Use first available color cache for rockets (they're just launch trails)
        default_cache = self.trail_color_caches.get('red', list(self.trail_color_caches.values())[0])

        # Draw rockets
        for rocket in self.rockets:
            if rocket.active and not rocket.exploded:
                # Draw trail (only last 3 positions for performance)
                trail_len = len(rocket.trail)
                start_idx = max(0, trail_len - 3)

                for idx in range(start_idx, trail_len):
                    trail_x, trail_y = rocket.trail[idx]
                    if 0 <= trail_y < self.max_rows and 0 <= trail_x < self.max_cols:
                        # Fade trail based on age
                        progress = idx / max(1, trail_len - 1)
                        color_idx = int(progress * (len(default_cache) - 1))
                        attr_normal, _ = default_cache[color_idx]

                        try:
                            self.stdscr.addstr(trail_y, trail_x, '*', attr_normal)
                        except:
                            pass

                # Draw rocket head
                head_y = int(rocket.y)
                head_x = int(rocket.x)
                if 0 <= head_y < self.max_rows and 0 <= head_x < self.max_cols:
                    _, attr_bold = default_cache[-1]
                    try:
                        self.stdscr.addstr(head_y, head_x, '^', attr_bold)
                    except:
                        pass

        # Draw particles with visible trailing streaks
        for particle in self.particles:
            if particle.active:
                life_progress = particle.life / particle.max_life

                # Initial white flash for regular bursts (first 12% of lifetime)
                if particle.color_scheme != 'white' and life_progress > 0.88:
                    # Use white color cache for initial flash
                    particle_cache = self.trail_color_caches.get('white', default_cache)
                else:
                    # Use correct color cache for this particle
                    particle_cache = self.trail_color_caches.get(particle.color_scheme, default_cache)

                # Draw last 5 trail positions for visible streaks (balanced performance)
                trail_len = len(particle.trail)
                start_idx = max(0, trail_len - 5)

                for idx in range(start_idx, trail_len):
                    trail_x, trail_y = particle.trail[idx]
                    if 0 <= trail_y < self.max_rows and 0 <= trail_x < self.max_cols:
                        # Trail fade calculation
                        trail_progress = idx / max(1, trail_len - 1)

                        # Trails stay in very dark range (0.0-0.20) for depth
                        trail_brightness = life_progress * trail_progress * 0.20
                        color_idx = int(trail_brightness * (len(particle_cache) - 1))
                        color_idx = max(0, min(color_idx, len(particle_cache) - 1))
                        attr_normal, _ = particle_cache[color_idx]

                        try:
                            # Use streak character for trails
                            self.stdscr.addstr(trail_y, trail_x, '·', attr_normal)
                        except:
                            pass

                # Draw particle head (bright)
                head_y = int(particle.y)
                head_x = int(particle.x)
                if 0 <= head_y < self.max_rows and 0 <= head_x < self.max_cols:
                    # Initial white flash at full brightness
                    if particle.color_scheme != 'white' and life_progress > 0.88:
                        # White flash at maximum brightness
                        head_brightness = 1.0
                    else:
                        # Normal fade behavior after initial flash
                        if particle.color_scheme != 'white':
                            head_brightness = life_progress * 0.65  # Darker than full brightness
                        else:
                            head_brightness = life_progress  # White crackles stay bright

                    color_idx = int(head_brightness * (len(particle_cache) - 1))
                    _, attr_bold = particle_cache[color_idx]

                    try:
                        # Use particle's pre-computed character for variety
                        self.stdscr.addstr(head_y, head_x, particle.char, attr_bold)
                    except:
                        pass