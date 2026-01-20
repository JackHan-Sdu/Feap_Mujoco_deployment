#!/bin/bash
# Conda environment removal script
# Used to remove conda environment for Feap E3 MuJoCo deployment

set -e

echo "=========================================="
echo "  Feap E3 MuJoCo Deployment - Conda Environment Removal"
echo "=========================================="
echo ""

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "Error: conda command not found"
    echo "Please install Anaconda or Miniconda first"
    echo "Download: https://www.anaconda.com/products/distribution"
    exit 1
fi

# Initialize conda
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
    if command -v conda &> /dev/null; then
        eval "$(conda shell.bash hook)"
    fi
fi

# List all environments
echo "Available conda environments:"
echo ""
conda env list
echo ""

# Prompt user for environment name
read -p "Enter conda environment name to remove [default: feap_mujoco]: " ENV_NAME
ENV_NAME=${ENV_NAME:-feap_mujoco}

if [ -z "$ENV_NAME" ]; then
    echo "Error: Environment name cannot be empty"
    exit 1
fi

echo ""
echo "Environment name: $ENV_NAME"
echo ""

# Check if environment exists
if ! conda env list | grep -q "^${ENV_NAME}\s"; then
    echo "Environment '$ENV_NAME' does not exist, no need to remove"
    exit 0
fi

# If currently using this environment, deactivate first
if [ -n "$CONDA_DEFAULT_ENV" ] && [ "$CONDA_DEFAULT_ENV" = "$ENV_NAME" ]; then
    echo "Warning: Currently using environment '$ENV_NAME'"
    echo "Deactivating environment..."
    conda deactivate 2>/dev/null || true
    echo "Environment deactivated"
    echo ""
fi

# Confirm removal
echo "=========================================="
echo "  Confirm Removal"
echo "=========================================="
echo ""
echo "About to remove environment: $ENV_NAME"
echo ""
read -p "Are you sure you want to remove it? (yes/no) [default: no]: " CONFIRM
CONFIRM=${CONFIRM:-no}

if [ "$CONFIRM" != "yes" ] && [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Operation cancelled"
    exit 0
fi

echo ""
echo "=========================================="
echo "  Removing Environment"
echo "=========================================="
echo ""

# Remove environment
echo "Removing environment '$ENV_NAME'..."
conda env remove -n "$ENV_NAME" -y

# Verify removal success
echo ""
if conda env list | grep -q "^${ENV_NAME}\s"; then
    echo "⚠ Warning: Environment '$ENV_NAME' may not be completely removed, please check manually"
    exit 1
else
    echo "=========================================="
    echo "  Removal Complete!"
    echo "=========================================="
    echo ""
    echo "Environment '$ENV_NAME' has been successfully removed"
    echo ""
fi
