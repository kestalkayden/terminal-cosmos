"""Shared RainDrop particle class for rain and lightning animations."""

import random
from .base_particle import BaseParticle, VelocityParticleMixin, AnimatedParticleMixin


class RainDrop(VelocityParticleMixin, AnimatedParticleMixin, BaseParticle):
    """Diagonal rain drop with character animation support."""

    def __init__(self, rain_attr):
        # Initialize mixins and base class
        animation_frames = ['·', '′', '/', '╱']  # [·, ′, /, ╱]
        AnimatedParticleMixin.__init__(self, animation_frames, frame_duration=0.067)
        VelocityParticleMixin.__init__(self)
        BaseParticle.__init__(self)

        self.attr = rain_attr  # Pre-calculated attribute

    def reset(self, x: float, y: float):
        """Reset drop for reuse from object pool."""
        self.x = x
        self.y = y
        # Diagonal down-left movement (more noticeable angle)
        self.vx = random.uniform(-1.8, -1.2)  # Consistent left movement (more angle)
        self.vy = random.uniform(1.5, 2.5)  # Downward movement
        # Reset animation
        self.frame_index = 0
        self.frame_timer = 0.0
        self.active = True

    def update(self, dt: float, movement_multiplier: float = 1.0):
        """Update position and animation frame."""
        # Apply velocity using mixin
        self.apply_velocity(dt, movement_multiplier)

        # Update animation frame using mixin
        self.update_animation(dt)

    def get_char(self) -> str:
        """Get current animation frame character."""
        return self.get_current_frame()

    def is_off_screen(self, max_rows: int, max_cols: int) -> bool:
        """Check if drop is off screen (including horizontal bounds)."""
        return self.y > max_rows + 2 or self.x > max_cols + 5 or self.x < -5