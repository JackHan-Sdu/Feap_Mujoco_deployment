#!/bin/bash
# Conda environment setup script
# Used to create and configure conda environment for Feap E3 MuJoCo deployment

set -e

# Get absolute path of script directory (scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Project root directory is parent of scripts/
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  Feap E3 MuJoCo Deployment - Conda Environment Setup"
echo "=========================================="
echo "Project root: $PROJECT_ROOT"
echo ""

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "Error: conda command not found"
    echo "Please install Anaconda or Miniconda first"
    echo "Download: https://www.anaconda.com/products/distribution"
    exit 1
fi

# Initialize conda
# Try to source conda.sh from common locations first (more reliable)
if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
elif [ -f "$HOME/miniconda/etc/profile.d/conda.sh" ]; then
    source "$HOME/miniconda/etc/profile.d/conda.sh"
elif [ -f "$HOME/anaconda/etc/profile.d/conda.sh" ]; then
    source "$HOME/anaconda/etc/profile.d/conda.sh"
elif [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then
    source "/opt/conda/etc/profile.d/conda.sh"
else
    # If conda.sh not found, use shell hook method
    if command -v conda &> /dev/null; then
        eval "$(conda shell.bash hook)"
    fi
fi

# Check conda version
CONDA_VERSION=$(conda --version 2>/dev/null | awk '{print $2}' || echo "unknown")
echo "Detected conda version: $CONDA_VERSION"
echo ""

# Prompt user for environment name
read -p "Enter conda environment name [default: feap_mujoco]: " ENV_NAME
ENV_NAME=${ENV_NAME:-feap_mujoco}

echo ""
echo "Environment name: $ENV_NAME"
echo ""

# Helper function: initialize conda
_init_conda() {
    if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/miniconda3/etc/profile.d/conda.sh"
    elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
        source "$HOME/anaconda3/etc/profile.d/conda.sh"
    elif [ -n "$CONDA_EXE" ]; then
        eval "$("$CONDA_EXE" shell.bash hook)"
    elif command -v conda &> /dev/null; then
        eval "$(conda shell.bash hook)"
    fi
}

# Check if environment exists
if conda env list | grep -q "^${ENV_NAME}\s"; then
    echo "Environment '$ENV_NAME' already exists, will use existing environment"
    echo "Activating environment..."
    _init_conda
    conda activate "$ENV_NAME" || {
        echo "Warning: conda activate failed, trying fallback method..."
        _init_conda
        source activate "$ENV_NAME" 2>/dev/null || {
            echo "Error: Unable to activate environment, please run manually: conda activate $ENV_NAME"
            exit 1
        }
    }
    echo "Environment activated"
else
    echo "Environment '$ENV_NAME' does not exist, creating new environment..."
    echo "Creating conda environment (Python 3.8, good compatibility)..."
    echo ""
    
    # Create conda environment (Python 3.8)
    {
        conda create -n "$ENV_NAME" python=3.8 -y 2>&1 | \
        grep -vE "(^==> WARNING: A newer version|^  current version:|^  latest version:)" | \
        grep -vE "(^Collecting package metadata|^Solving environment)" | \
        grep -v "^$" || true
    }
    
    # Verify environment creation
    echo ""
    if conda env list | grep -q "^${ENV_NAME}\s"; then
        echo "✓ Environment created successfully"
    else
        echo "✗ Error: Environment creation failed, please check conda configuration"
        exit 1
    fi
    
    # Activate environment
    echo "Activating environment..."
    _init_conda
    conda activate "$ENV_NAME" || {
        echo "Warning: conda activate failed, trying fallback method..."
        _init_conda
        source activate "$ENV_NAME" 2>/dev/null || {
            echo "Error: Unable to activate environment, please run manually: conda activate $ENV_NAME"
            exit 1
        }
    }
    echo "Environment created and activated"
fi

echo ""
echo "=========================================="
echo "  Installing System Dependencies"
echo "=========================================="
echo ""

# Check if Ubuntu/Debian system
if command -v apt-get &> /dev/null; then
    echo "Detected Ubuntu/Debian system, installing system dependencies..."
    
    # Check if sudo is needed
    if [ "$EUID" -eq 0 ]; then
        APT_CMD="apt-get"
    else
        APT_CMD="sudo apt-get"
    fi
    
    echo "Updating package list..."
    $APT_CMD update -qq 2>&1 | grep -vE "(^Reading package lists|^Building dependency tree|^Reading state information|^No Release file|^WARNING:)" || true
    
    echo ""
    echo "Installing system dependency packages..."
    $APT_CMD install -y libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1 2>&1 | \
        grep -vE "(^Reading package lists|^Building dependency tree|^Reading state information|^already the newest|^The following packages were automatically)" || true
    
    echo ""
    echo "✓ System dependencies installed"
    
    echo ""
    echo "Configuring gamepad device permissions (/dev/input/js*) for calibrate_gamepad.py..."
    UDEV_RULE='KERNEL=="js*", MODE="0666"'
    UDEV_RULE_PATH="/etc/udev/rules.d/99-joystick.rules"
    if grep -q 'KERNEL=="js*"' "$UDEV_RULE_PATH" 2>/dev/null; then
        echo "  Rule already exists, skipping"
    else
        if [ "$EUID" -eq 0 ]; then
            echo "$UDEV_RULE" > "$UDEV_RULE_PATH"
            udevadm control --reload-rules
            udevadm trigger --subsystem-match=input || true
            echo "  Rule written and udev reloaded (may need to replug device)"
        else
            echo "$UDEV_RULE" | sudo tee "$UDEV_RULE_PATH" >/dev/null
            sudo udevadm control --reload-rules
            sudo udevadm trigger --subsystem-match=input || true
            echo "  Rule written via sudo and udev reloaded (may need to replug device)"
        fi
    fi
else
    echo "Warning: apt-get not detected, please manually install the following dependencies (if needed):"
    echo "  - libgl1-mesa-glx (OpenGL)"
    echo "  - libglib2.0-0"
    echo "  - libsm6, libxext6, libxrender-dev (X11)"
    echo "  - libgomp1 (OpenMP)"
    echo "Gamepad device permission example rule: /etc/udev/rules.d/99-joystick.rules content: KERNEL==\"js*\", MODE=\"0666\""
fi

echo ""
echo "=========================================="
echo "  Installing Python Dependencies"
echo "=========================================="
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip -q

# Install core dependency packages
echo ""
echo "Installing core Python packages..."
echo "  - numpy: Numerical computing library"
pip install numpy -q

echo "  - pyyaml: YAML configuration file parsing"
pip install pyyaml -q

echo "  - pygame: Gamepad and keyboard input"
pip install pygame -q

echo "  - matplotlib: Plotting library"
pip install matplotlib -q

# Install MuJoCo
echo ""
echo "Installing MuJoCo 3.2.3..."
pip install mujoco==3.2.3 -q
if python -c "import mujoco" 2>/dev/null; then
    echo "  ✓ MuJoCo installed successfully"
else
    echo "  ✗ Error: MuJoCo installation failed"
    exit 1
fi

# Install ONNX Runtime
echo ""
echo "Installing ONNX Runtime 1.19.2..."
pip install onnxruntime==1.19.2 -q
if python -c "import onnxruntime" 2>/dev/null; then
    echo "  ✓ ONNX Runtime installed successfully"
else
    echo "  ⚠ Warning: ONNX Runtime installation failed, trying latest version..."
    pip install onnxruntime -q
    if python -c "import onnxruntime" 2>/dev/null; then
        echo "  ✓ ONNX Runtime (latest version) installed successfully"
    else
        echo "  ✗ Error: ONNX Runtime installation failed"
        echo "  Please install manually: pip install onnxruntime"
        exit 1
    fi
fi

# Verify all dependencies
echo ""
echo "=========================================="
echo "  Verifying Installation"
echo "=========================================="
echo ""

ALL_OK=true

check_package() {
    local package=$1
    local import_name=${2:-$package}
    if python -c "import $import_name" 2>/dev/null; then
        local version=$(python -c "import $import_name; print(getattr($import_name, '__version__', 'unknown'))" 2>/dev/null || echo "unknown")
        echo "  ✓ $package $version"
        return 0
    else
        echo "  ✗ $package not installed or import failed"
        return 1
    fi
}

echo "Checking installed packages:"
check_package "numpy" || ALL_OK=false
check_package "yaml" "yaml" || ALL_OK=false
check_package "pygame" || ALL_OK=false
check_package "matplotlib" || ALL_OK=false
check_package "mujoco" || ALL_OK=false
check_package "onnxruntime" || ALL_OK=false

echo ""

if [ "$ALL_OK" = true ]; then
    echo "✓ All dependency packages installed successfully!"
else
    echo "⚠ Warning: Some dependency packages failed to install, please check error messages"
fi

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Environment name: $ENV_NAME"
echo "Project root: $PROJECT_ROOT"
echo ""
echo "Usage:"
echo "  1. Activate environment: conda activate $ENV_NAME"
echo "  2. Run deployment script: cd $PROJECT_ROOT && python scripts/feap_e3_mujoco_deploy.py configs/e3.yaml"
echo "  3. Calibrate gamepad: cd $PROJECT_ROOT && python scripts/calibrate_gamepad.py"
echo ""
echo "Notes:"
echo "  - Always activate conda environment before use: conda activate $ENV_NAME"
echo "  - Ensure ONNX model files are placed in policy/ directory"
echo "  - Configuration files are located in configs/ directory"
echo ""
echo "Remove environment:"
echo "  Run: ./scripts/remove_conda_env.sh"
echo ""
