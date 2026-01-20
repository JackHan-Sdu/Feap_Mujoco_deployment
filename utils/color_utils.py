"""Color utilities for terminal output"""
import sys

# ANSI color codes
class Colors:
    """ANSI color codes for terminal output"""
    # Reset
    RESET = '\033[0m'
    
    # Text colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    
    # Styles
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    STRIKETHROUGH = '\033[9m'


def colored(text, color=None, style=None):
    """Return colored text
    
    Args:
        text: Text to color
        color: Color code (from Colors class)
        style: Style code (from Colors class)
    
    Returns:
        Colored text string
    """
    if not sys.stdout.isatty():
        # If not a terminal, return plain text
        return text
    
    result = text
    if style:
        result = style + result
    if color:
        result = color + result
    if color or style:
        result = result + Colors.RESET
    return result


def print_header(title, width=70):
    """Print a formatted header
    
    Args:
        title: Header title
        width: Header width
    """
    border = colored("=" * width, Colors.CYAN)
    title_line = colored(title.center(width), Colors.BOLD + Colors.CYAN)
    print(f"\n{border}")
    print(title_line)
    print(f"{border}\n")


def print_section(title, color=Colors.CYAN):
    """Print a section title
    
    Args:
        title: Section title
        color: Color for the title
    """
    print(colored(f"\n{title}", Colors.BOLD + color))
    print(colored("-" * len(title), color))


def print_info(label, value, label_color=Colors.CYAN, value_color=Colors.WHITE):
    """Print labeled information
    
    Args:
        label: Label text
        value: Value text
        label_color: Color for label
        value_color: Color for value
    """
    print(f"  {colored(label, label_color)}: {colored(str(value), value_color)}")


def print_success(message):
    """Print success message
    
    Args:
        message: Success message
    """
    print(colored(f"✓ {message}", Colors.BRIGHT_GREEN))


def print_warning(message):
    """Print warning message
    
    Args:
        message: Warning message
    """
    print(colored(f"⚠ {message}", Colors.BRIGHT_YELLOW))


def print_error(message):
    """Print error message
    
    Args:
        message: Error message
    """
    print(colored(f"✗ {message}", Colors.BRIGHT_RED))


def print_feap_banner():
    """Print Feap project banner"""
    banner = f"""
{colored('╔' + '═' * 68 + '╗', Colors.BRIGHT_CYAN)}
{colored('║', Colors.BRIGHT_CYAN)}{colored(' Feap - E3 Humanoid Robot Policy Deployment & Validation', Colors.BOLD + Colors.BRIGHT_CYAN).center(68)}{colored('║', Colors.BRIGHT_CYAN)}
{colored('║', Colors.BRIGHT_CYAN)}{colored(' MuJoCo Simulation Environment', Colors.CYAN).center(68)}{colored('║', Colors.BRIGHT_CYAN)}
{colored('╚' + '═' * 68 + '╝', Colors.BRIGHT_CYAN)}
"""
    print(banner)
