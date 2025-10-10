"""Generic particle pool for efficient memory management."""

from typing import TypeVar, Generic, List, Callable, Optional


T = TypeVar('T')


class ParticlePool(Generic[T]):
    """Generic object pool for particle management.

    Eliminates repeated allocation/deallocation by maintaining a pool of
    reusable particle objects. Particles are retrieved from the pool when
    needed and returned when off-screen, achieving zero allocations during
    steady-state animation.

    Type Parameters:
        T: Particle class type (must have a reset() method)

    Example:
        >>> class Meteor:
        ...     def reset(self, x, y):
        ...         self.x = x
        ...         self.y = y
        ...
        >>> pool = ParticlePool(Meteor, size=10)
        >>> meteor = pool.acquire()
        >>> if meteor:
        ...     meteor.reset(100, 50)
        ...     pool.active.append(meteor)
        >>> # When meteor is off-screen:
        >>> pool.release(meteor)
    """

    def __init__(self, particle_class: Callable[..., T], size: int, *init_args, **init_kwargs):
        """Initialize particle pool.

        Args:
            particle_class: Class or factory function for creating particles
            size: Number of particles to pre-allocate
            *init_args: Arguments passed to particle_class constructor
            **init_kwargs: Keyword arguments passed to particle_class constructor
        """
        self.particle_class = particle_class
        self.pool: List[T] = []
        self.active: List[T] = []

        # Pre-allocate particles
        for _ in range(size):
            self.pool.append(particle_class(*init_args, **init_kwargs))

    def acquire(self) -> Optional[T]:
        """Get a particle from the pool.

        Returns:
            Particle instance if available, None if pool is exhausted
        """
        if not self.pool:
            return None
        return self.pool.pop()

    def release(self, particle: T):
        """Return a particle to the pool.

        Args:
            particle: Particle to return to pool
        """
        self.pool.append(particle)

    def update_active(self, dt: float, *update_args, **update_kwargs):
        """Update all active particles and recycle off-screen ones.

        Automatically calls update() on each active particle and removes
        particles that are off-screen (if they have is_off_screen method).

        Args:
            dt: Time delta since last update
            *update_args: Additional arguments passed to particle.update()
            **update_kwargs: Additional keyword arguments passed to particle.update()
        """
        i = 0
        while i < len(self.active):
            particle = self.active[i]

            # Update particle
            particle.update(dt, *update_args, **update_kwargs)

            # Check if particle should be recycled
            should_recycle = False
            if hasattr(particle, 'is_off_screen') and hasattr(particle, 'x'):
                # Particle has bounds checking - use it
                # Get screen bounds from kwargs if provided
                max_rows = update_kwargs.get('max_rows')
                max_cols = update_kwargs.get('max_cols')
                if max_rows is not None and max_cols is not None:
                    should_recycle = particle.is_off_screen(max_rows, max_cols)
            elif hasattr(particle, 'active'):
                # Particle has active flag
                should_recycle = not particle.active

            if should_recycle:
                # Return to pool and remove from active
                self.pool.append(self.active.pop(i))
            else:
                i += 1

    def clear(self):
        """Clear all active particles and return them to pool."""
        self.pool.extend(self.active)
        self.active.clear()

    def resize(self, new_size: int, *init_args, **init_kwargs):
        """Resize the pool capacity.

        Args:
            new_size: New pool size
            *init_args: Arguments for creating new particles if expanding
            **init_kwargs: Keyword arguments for creating new particles
        """
        current_total = len(self.pool) + len(self.active)

        if new_size > current_total:
            # Expand pool
            additional = new_size - current_total
            for _ in range(additional):
                self.pool.append(self.particle_class(*init_args, **init_kwargs))
        elif new_size < current_total:
            # Shrink pool (only remove from inactive pool, preserve active)
            excess = current_total - new_size
            # Only remove from pool, not from active particles
            remove_count = min(excess, len(self.pool))
            self.pool = self.pool[remove_count:]

    @property
    def available_count(self) -> int:
        """Get number of available particles in pool."""
        return len(self.pool)

    @property
    def active_count(self) -> int:
        """Get number of active particles."""
        return len(self.active)

    @property
    def total_capacity(self) -> int:
        """Get total pool capacity (active + available)."""
        return len(self.pool) + len(self.active)

    def __len__(self) -> int:
        """Get number of active particles."""
        return len(self.active)

    def __iter__(self):
        """Iterate over active particles."""
        return iter(self.active)
