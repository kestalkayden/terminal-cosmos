"""Base particle class for reusable animation entities."""

from abc import ABC, abstractmethod
from typing import Tuple


class BaseParticle(ABC):
    """Abstract base class for all particle types.

    Provides common position tracking and lifecycle management for particles
    used in object pooling systems. Subclasses must implement reset() and
    update() methods for specific particle behavior.
    """

    def __init__(self):
        """Initialize base particle with default position."""
        self.x = 0.0
        self.y = 0.0
        self.active = True

    @abstractmethod
    def reset(self, *args, **kwargs):
        """Reset particle state for reuse from object pool.

        Subclasses must implement this to reinitialize particle-specific
        attributes without allocating new objects. This is called when
        retrieving a particle from the pool.

        Args:
            *args, **kwargs: Particle-specific initialization parameters
        """
        pass

    @abstractmethod
    def update(self, dt: float, *args, **kwargs):
        """Update particle state for next frame.

        Args:
            dt: Time delta since last update
            *args, **kwargs: Particle-specific update parameters
        """
        pass

    def is_off_screen(self, max_rows: int, max_cols: int) -> bool:
        """Check if particle is off screen with default bounds.

        Default implementation checks if particle is beyond screen bounds
        with small margin. Subclasses can override for custom logic.

        Args:
            max_rows: Maximum row boundary
            max_cols: Maximum column boundary

        Returns:
            True if particle is off screen and can be recycled
        """
        return (self.y > max_rows + 2 or
                self.x > max_cols + 2 or
                self.x < -2 or
                self.y < -2)

    @property
    def row(self) -> int:
        """Get current row as integer."""
        return int(self.y)

    @property
    def col(self) -> int:
        """Get current column as integer."""
        return int(self.x)


class VelocityParticleMixin:
    """Mixin for particles with velocity-based movement.

    Provides vx/vy attributes and basic velocity application.
    Can be mixed with BaseParticle for particles that move.
    """

    def __init__(self):
        """Initialize velocity attributes."""
        self.vx = 0.0
        self.vy = 0.0

    def apply_velocity(self, dt: float, multiplier: float = 1.0):
        """Apply velocity to position.

        Args:
            dt: Time delta
            multiplier: Movement speed multiplier
        """
        self.x += self.vx * dt * multiplier
        self.y += self.vy * dt * multiplier


class AnimatedParticleMixin:
    """Mixin for particles with frame-based animation.

    Provides frame cycling logic for particles with multiple visual states.
    """

    def __init__(self, frames: list, frame_duration: float = 0.067):
        """Initialize animation attributes.

        Args:
            frames: List of animation frame characters/sprites
            frame_duration: Duration of each frame in seconds
        """
        self.animation_frames = frames
        self.frame_index = 0
        self.frame_timer = 0.0
        self.frame_duration = frame_duration

    def update_animation(self, dt: float):
        """Update animation frame.

        Args:
            dt: Time delta since last update
        """
        self.frame_timer += dt
        if self.frame_timer >= self.frame_duration:
            self.frame_index = (self.frame_index + 1) % len(self.animation_frames)
            self.frame_timer = 0.0

    def get_current_frame(self) -> str:
        """Get current animation frame character.

        Returns:
            Current frame character/sprite
        """
        return self.animation_frames[self.frame_index]
