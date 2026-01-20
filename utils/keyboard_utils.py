"""Keyboard control module for robot and camera - Terminal input version"""
import sys
import select
import termios
import tty
import threading
import numpy as np
from . import viewer_utils
from .color_utils import print_info, print_success, print_warning, Colors
from .display_utils import update_status

# Keyboard control state
keyboard_enabled = False
keyboard_control_camera = False  # Whether keyboard controls camera (R key to toggle)
cmd_step = 0.1  # Step size for velocity command changes
camera_angle_step = 0.05  # Step size for camera angle changes (radians)
camera_distance_step = 0.1  # Step size for camera distance changes (meters)
camera_elevation_step = 0.05  # Step size for camera elevation changes (radians)

# Global command reference for keyboard control
_keyboard_cmd_ref = None  # Reference to the cmd array that keyboard can modify

# Thread control
_keyboard_thread = None
_keyboard_running = False
_old_settings = None


def set_keyboard_cmd_ref(cmd_ref):
    """Set the command reference for keyboard control
    
    Args:
        cmd_ref: Reference to the cmd array [vx, vy, wz]
    """
    global _keyboard_cmd_ref
    _keyboard_cmd_ref = cmd_ref


def _get_key():
    """Get a single keypress from stdin (non-blocking)
    
    Returns:
        Character string or None if no key available
    """
    if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
        return sys.stdin.read(1)
    return None


def _get_key_blocking():
    """Get a single keypress from stdin (blocking)
    For arrow keys, reads the complete ANSI escape sequence
    
    Returns:
        Character string or tuple (arrow_char, True) for arrow keys
    """
    key = sys.stdin.read(1)
    
    # Check if it's the start of an ANSI escape sequence (ESC = \x1b or \033)
    if key == '\x1b' or key == '\033':
        # Read the next character (should be '[' for arrow keys)
        # Use blocking read to ensure we get the complete sequence
        try:
            next_char = sys.stdin.read(1)
            if next_char == '[':
                # Read the arrow key character (blocking)
                arrow = sys.stdin.read(1)
                # Return tuple to indicate this is an arrow key
                return (arrow, True)
            else:
                # Not an arrow key sequence, return ESC as-is
                return key
        except (IOError, OSError):
            # If read fails, just return the ESC character
            return key
    
    return key


def _process_key(key_input):
    """Process a single key input
    
    Args:
        key_input: Character string or tuple (arrow_char, True) for arrow keys
    """
    global keyboard_control_camera, _keyboard_cmd_ref
    
    if not keyboard_enabled:
        return
    
    # Handle arrow keys (tuple format)
    if isinstance(key_input, tuple):
        arrow_char, _ = key_input
        # Arrow keys only work when camera control mode is enabled
        if keyboard_control_camera:
            _handle_arrow_key(arrow_char)
        # Always return for arrow keys (don't process as regular keys)
        return
    
    # Regular character key
    key_char = key_input
    key_lower = key_char.lower()
    
    # Handle camera control toggle (R key)
    if key_lower == 'r':
        keyboard_control_camera = not keyboard_control_camera
        status = "enabled" if keyboard_control_camera else "disabled"
        update_status(status_message=f"Camera control {status}")
        return
    
    # Handle clear all commands (C key)
    if key_lower == 'c':
        if _keyboard_cmd_ref is not None:
            _keyboard_cmd_ref[:] = 0.0
            update_status(status_message="All velocity commands cleared")
        return
    
    # Handle reset robot (B key)
    if key_lower == 'b':
        viewer_utils.reset_requested = True
        update_status(reset_requested=True, status_message="Robot reset requested")
        return
    
    # Handle camera controls (U/O for distance) - only when camera control mode is enabled
    if keyboard_control_camera:
        if key_lower == 'u' or key_lower == 'o':
            _handle_camera_controls_terminal(key_char)
            return
    
    # Handle velocity command controls (always available, regardless of camera control mode)
    if _keyboard_cmd_ref is None:
        return
    
    # W/S: Forward/backward velocity (cmd[0])
    if key_lower == 'w':
        _keyboard_cmd_ref[0] += cmd_step
    elif key_lower == 's':
        _keyboard_cmd_ref[0] -= cmd_step
    
    # A/D: Angular velocity (cmd[2])
    elif key_lower == 'a':
        _keyboard_cmd_ref[2] += cmd_step
    elif key_lower == 'd':
        _keyboard_cmd_ref[2] -= cmd_step
    
    # J/L: Lateral velocity (cmd[1])
    elif key_lower == 'j':
        _keyboard_cmd_ref[1] += cmd_step
    elif key_lower == 'l':
        _keyboard_cmd_ref[1] -= cmd_step


def _handle_arrow_key(arrow_char):
    """Handle arrow key input for camera control
    
    Args:
        arrow_char: Arrow key character ('A'=Up, 'B'=Down, 'C'=Right, 'D'=Left)
    """
    global camera_angle_step, camera_elevation_step
    
    # Up arrow: A, Down arrow: B, Right arrow: C, Left arrow: D
    if arrow_char == 'A':  # Up
        viewer_utils.camera_elevation += camera_elevation_step
        viewer_utils.camera_elevation = np.clip(viewer_utils.camera_elevation, 
                                                np.radians(-89), np.radians(89))
    elif arrow_char == 'B':  # Down
        viewer_utils.camera_elevation -= camera_elevation_step
        viewer_utils.camera_elevation = np.clip(viewer_utils.camera_elevation, 
                                                np.radians(-89), np.radians(89))
    elif arrow_char == 'C':  # Right
        viewer_utils.camera_angle += camera_angle_step
        viewer_utils.camera_angle = viewer_utils.camera_angle % (2 * np.pi)
    elif arrow_char == 'D':  # Left
        viewer_utils.camera_angle -= camera_angle_step
        viewer_utils.camera_angle = viewer_utils.camera_angle % (2 * np.pi)


def _handle_camera_controls_terminal(key_char):
    """Handle camera controls from terminal input (non-arrow keys)
    
    Args:
        key_char: Character string from keyboard input
    """
    global camera_distance_step
    
    # Page Up/Down (not easily detectable in raw mode, use alternative keys)
    # Using 'u' for Page Up (distance decrease) and 'o' for Page Down (distance increase)
    if key_char.lower() == 'u':
        viewer_utils.camera_distance -= camera_distance_step
        viewer_utils.camera_distance = np.clip(viewer_utils.camera_distance, 0.5, 10.0)
    elif key_char.lower() == 'o':
        viewer_utils.camera_distance += camera_distance_step
        viewer_utils.camera_distance = np.clip(viewer_utils.camera_distance, 0.5, 10.0)


def _keyboard_input_thread():
    """Background thread that reads keyboard input from terminal"""
    global _keyboard_running, _old_settings
    
    # Save terminal settings for stdin only
    _old_settings = termios.tcgetattr(sys.stdin)
    
    try:
        # Use cbreak mode instead of raw mode to preserve output processing
        # cbreak mode: characters available immediately, but signals still work
        # This allows ANSI escape codes in stdout to work properly
        tty.setcbreak(sys.stdin.fileno())
        
        while _keyboard_running:
            try:
                key = _get_key_blocking()
                if key:
                    _process_key(key)
            except Exception as e:
                # If there's an error reading, continue
                pass
    except Exception as e:
        print_warning(f"Keyboard input thread error: {e}")
    finally:
        # Restore terminal settings
        if _old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, _old_settings)


def init_keyboard(config=None):
    """Initialize keyboard control
    
    Args:
        config: Configuration dictionary, may contain:
            - keyboard_enabled: Whether keyboard control is enabled
            - cmd_step: Step size for velocity command changes
            - camera_angle_step: Step size for camera angle changes
            - camera_distance_step: Step size for camera distance changes
            - camera_elevation_step: Step size for camera elevation changes
    """
    global keyboard_enabled, cmd_step, camera_angle_step, camera_distance_step, camera_elevation_step
    global _keyboard_thread, _keyboard_running
    
    if config is not None:
        keyboard_enabled = config.get("keyboard_enabled", False)
        cmd_step = config.get("cmd_step", 0.1)
        camera_angle_step = config.get("camera_angle_step", 0.05)
        camera_distance_step = config.get("camera_distance_step", 0.1)
        camera_elevation_step = config.get("camera_elevation_step", 0.05)
    
    if keyboard_enabled:
        print_success("Keyboard control enabled (Terminal input mode)")
        print_keyboard_controls()
        
        # Start keyboard input thread
        _keyboard_running = True
        _keyboard_thread = threading.Thread(target=_keyboard_input_thread, daemon=True)
        _keyboard_thread.start()
    else:
        print_info("Keyboard Control", "Disabled", Colors.CYAN, Colors.WHITE)


def stop_keyboard():
    """Stop keyboard input thread and restore terminal settings"""
    global _keyboard_running, _keyboard_thread, _old_settings
    
    _keyboard_running = False
    
    # Restore terminal settings
    if _old_settings:
        try:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, _old_settings)
        except:
            pass
        _old_settings = None
    
    # Wait for thread to finish (with timeout)
    if _keyboard_thread and _keyboard_thread.is_alive():
        _keyboard_thread.join(timeout=0.5)


def print_keyboard_controls():
    """Print keyboard control instructions"""
    from .color_utils import colored, Colors
    print(colored("=" * 70, Colors.BRIGHT_CYAN))
    print(colored("Keyboard Control Instructions (Terminal Input)", Colors.BOLD + Colors.BRIGHT_CYAN).center(70))
    print(colored("=" * 70, Colors.BRIGHT_CYAN))
    print(colored("  W", Colors.CYAN) + ": Forward velocity")
    print(colored("  S", Colors.CYAN) + ": Backward velocity")
    print(colored("  A", Colors.CYAN) + ": Rotate left (angular velocity)")
    print(colored("  D", Colors.CYAN) + ": Rotate right (angular velocity)")
    print(colored("  J", Colors.CYAN) + ": Move left (lateral velocity)")
    print(colored("  L", Colors.CYAN) + ": Move right (lateral velocity)")
    print(colored("  C", Colors.CYAN) + ": Clear all velocity commands")
    print(colored("  B", Colors.CYAN) + ": Reset robot state")
    print(colored("  R", Colors.CYAN) + ": Toggle camera control mode")
    print(colored("  Arrow Keys", Colors.CYAN) + ": Control camera (when camera mode enabled)")
    print(colored("    ↑/↓", Colors.CYAN) + ": Camera elevation")
    print(colored("    ←/→", Colors.CYAN) + ": Camera angle")
    print(colored("  U/O", Colors.CYAN) + ": Camera distance (decrease/increase)")
    print(colored("  Note:", Colors.YELLOW) + " Type keys in terminal (no Enter needed)")
    print(colored("=" * 70, Colors.BRIGHT_CYAN))


def update_cmd_from_keyboard(cmd):
    """Update velocity command from keyboard input
    
    This function now just sets the command reference.
    Actual keyboard processing happens in the background thread.
    
    Args:
        cmd: Current velocity command [vx, vy, wz]
    
    Returns:
        Updated velocity command (may be modified by background thread)
    """
    global _keyboard_cmd_ref
    
    if not keyboard_enabled:
        return cmd
    
    # Set the command reference so background thread can modify it
    _keyboard_cmd_ref = cmd
    
    return cmd


def create_key_callback():
    """Create a dummy key callback (not used in terminal input mode)
    
    Returns:
        None (terminal input mode doesn't use MuJoCo key callback)
    """
    return None


def disable_mujoco_shortcuts(viewer):
    """Disable MuJoCo viewer keyboard shortcuts (not needed in terminal input mode)
    
    Args:
        viewer: MuJoCo viewer object
    """
    pass  # Terminal input mode doesn't interfere with MuJoCo shortcuts
