"""
Main entry point for terminal-cosmos.

Provides command-line interface, environment validation, mode instantiation,
and curses application wrapper. Handles argument parsing for animation modes,
FPS settings, color schemes, and speed controls.

Key functions:
    - parse_arguments: CLI argument parsing with mode-specific defaults
    - validate_environment: TTY and terminal capability validation
    - create_mode_instance: Dynamic animation mode instantiation
    - run_animation: Curses wrapper for animation execution
    - main: Application entry point with error handling

Integration points:
    - Imports and instantiates modes from modes/ package
    - Provides parsed configuration to animation modes
    - Wraps core.animation_base framework in curses environment

Configuration:
    - Supports 4 animation modes: meteor, lightning, space, matrix
    - 18 color schemes from cosmic to traditional
    - Mode-specific optimal FPS: meteor=15, lightning=8, space=30, matrix=12
    - Speed multiplier and manual FPS override options

Environment validation ensures proper TTY support and curses availability
before launching animations. Graceful error handling preserves terminal state.

See Also:
    - modes: Animation mode implementations
    - core.animation_base: Core animation framework
"""

import sys
import os
import argparse
import curses
import random
from typing import Optional


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Terminal Cosmos - Dynamic ASCII terminal animations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available modes:
  meteor     Meteor shower with falling particles
  lightning  Lightning storm with electrical branching
  storm      Alias for lightning mode
  rain       Pure diagonal rainfall without lightning
  space      Starfield with cosmic movement and parallax
  matrix     Matrix-style digital rain effect
  warp       Warp field effect (in development)
  fireworks  Launching rockets with explosive bursts
  fireflies  Peaceful fireflies with realistic blinking
  firefly    Alias for fireflies mode

Examples:
  terminal-cosmos                    # Random mode
  terminal-cosmos --mode meteor      # Specific mode
  terminal-cosmos --mode space --color cyan --intense

All modes run at 60 FPS for optimal performance and visual quality.

Controls (while running):
  Q/ESC      Quit
  C          Cycle through 9 color schemes
  M          Switch animation modes
  Arrow Keys Navigate (future use)
        """
    )

    # Mode selection
    parser.add_argument(
        '--mode',
        choices=['meteor', 'lightning', 'storm', 'rain', 'space', 'matrix', 'warp', 'fireworks', 'fireflies', 'firefly'],
        default=None,
        help='Animation mode to run (default: random mode)'
    )


    # Color schemes
    parser.add_argument(
        '--color', '--color-scheme',
        choices=['red', 'blue', 'green', 'yellow', 'purple', 'cyan', 'gray', 'grey', 'pink', 'orange'],
        default=None,
        help='Color scheme to use (default: mode-specific)'
    )

    # Intense mode
    parser.add_argument(
        '--intense',
        action='store_true',
        help='Enable intense mode for more dramatic effects'
    )

    args = parser.parse_args()

    # Randomly select mode if none specified
    if args.mode is None:
        args.mode = random.choice(['meteor', 'lightning', 'rain', 'space', 'matrix', 'warp', 'fireworks', 'fireflies'])

    # Set fixed 60 FPS for compatibility across all modes
    args.fps = 60

    return args


def validate_environment():
    """Validate that the environment supports terminal-cosmos."""
    # Check if we're in a TTY environment
    if not os.isatty(1):
        print("Error: terminal-cosmos requires a TTY environment", file=sys.stderr)
        print("Please run in a proper terminal, not through pipes or redirects", file=sys.stderr)
        sys.exit(1)

    # Check for dumb terminal
    if os.environ.get('TERM') == 'dumb':
        print("Error: terminal-cosmos does not support dumb terminals", file=sys.stderr)
        print("Please use a terminal with proper capabilities (xterm, etc.)", file=sys.stderr)
        sys.exit(1)

    # Check if curses is available
    try:
        import curses
    except ImportError:
        print("Error: curses library not available", file=sys.stderr)
        print("Please install Python curses support", file=sys.stderr)
        sys.exit(1)


def create_mode_instance(mode_name: str):
    """Create an instance of the specified animation mode.

    Args:
        mode_name: Name of the mode to create

    Returns:
        Animation mode instance
    """
    # Import modes here to avoid circular imports
    try:
        if mode_name == 'meteor':
            from .modes.meteor_shower import MeteorShower
            return MeteorShower()
        elif mode_name in ['lightning', 'storm']:
            from .modes.lightning_storm import LightningStorm
            return LightningStorm()
        elif mode_name == 'rain':
            from .modes.rain import Rain
            return Rain()
        elif mode_name == 'space':
            from .modes.space import Space
            return Space()
        elif mode_name == 'matrix':
            from .modes.matrix import Matrix
            return Matrix()
        elif mode_name == 'warp':
            from .modes.warp import Warp
            return Warp()
        elif mode_name == 'fireworks':
            from .modes.fireworks import Fireworks
            return Fireworks()
        elif mode_name in ['fireflies', 'firefly']:
            from .modes.fireflies import Fireflies
            return Fireflies()
        else:
            raise ValueError(f"Unknown mode: {mode_name}")
    except ImportError as e:
        print(f"Error: Mode '{mode_name}' not yet implemented", file=sys.stderr)
        print("Available modes will be implemented in the next phase", file=sys.stderr)
        sys.exit(1)


def run_animation(stdscr, args):
    """Run the animation in curses environment.

    Args:
        stdscr: Curses screen object
        args: Parsed command line arguments
    """
    try:
        current_mode = args.mode

        # Mode switching loop
        while True:
            # Set mode-specific FPS
            if current_mode == 'matrix':
                fps = 10
            elif current_mode == 'fireworks':
                fps = 30  # Lower FPS for better CPU efficiency
            else:
                fps = args.fps

            # Calculate update interval from mode-specific FPS
            update_interval = 1.0 / fps
            # Clear screen thoroughly for mode transitions
            stdscr.clear()
            stdscr.refresh()

            # Create mode instance
            mode = create_mode_instance(current_mode)

            # Set current mode for mode switching
            mode.current_mode = current_mode

            # Set intense mode for modes that support it
            if current_mode in ['lightning', 'storm', 'rain', 'space', 'matrix', 'warp', 'meteor', 'fireworks', 'fireflies', 'firefly'] and hasattr(mode, 'set_intense_mode'):
                mode.set_intense_mode(args.intense)

            # Run the animation
            result = mode.run(
                stdscr,
                update_interval=update_interval,
                color_scheme=args.color
            )

            # Handle mode switching
            if result and 'next_mode' in result:
                current_mode = result['next_mode']
                continue
            else:
                # User quit normally
                break

    except KeyboardInterrupt:
        pass
    except Exception as e:
        # Clean up curses before showing error
        curses.endwin()
        print(f"Error running animation: {e}", file=sys.stderr)
        raise


def main():
    """Main entry point for terminal-cosmos application."""
    # Validate environment first
    validate_environment()

    # Parse command line arguments
    args = parse_arguments()

    try:
        # Initialize and run curses application
        curses.wrapper(run_animation, args)
    except KeyboardInterrupt:
        print("\nTerminal Cosmos terminated by user")
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()