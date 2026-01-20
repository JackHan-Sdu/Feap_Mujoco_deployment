# Supplementary Materials for "FEAP: Feature-Enhanced Adversarial Priors for Unified Multistyle Humanoid Locomotion on Complex Terrains"

## Demo Videos

<div align="center">

### Full-Scenario Test Simulation
[![Full-Scenario Test Simulation](https://img.youtube.com/vi/a18HyjLmOHE/0.jpg)](https://www.youtube.com/watch?v=a18HyjLmOHE)

### Omnidirectional Disturbance Test Simulation
[![Omnidirectional Disturbance Test Simulation](https://img.youtube.com/vi/SR4RNRjj9vs/0.jpg)](https://www.youtube.com/watch?v=SR4RNRjj9vs)

### Running Across Terrain Simulation
[![Running Across Terrain Simulation](https://img.youtube.com/vi/eaHBSyXh_Aw/0.jpg)](https://www.youtube.com/watch?v=eaHBSyXh_Aw)

</div>

---

## Overview

This repository provides the deployment and validation framework for **FEAP** (Feature-Enhanced Adversarial Priors), a unified learning framework that enables a single policy to acquire multiple human-like locomotion styles on complex terrains within a single training phase.

### What is FEAP?

FEAP integrates motion priors with a feature-enhanced proprioceptive encoder and a multi-expert, style-consistent adversarial learning module, allowing the policy to capture diverse locomotion styles while maintaining robust stability across challenging environments. The framework enables humanoid robots to:

- **Omnidirectional Locomotion**: Forward, backward, lateral, and rotational movements
- **High-Speed Running**: Up to **3.5 m/s** with natural running gaits
- **Complex Terrain Navigation**: 
  - Stairs up to **18 cm**
  - Slopes up to **35°**
  - Elevated platforms up to **35 cm**
- **Autonomous Style Transitions**: Seamless transitions between walking, running, and terrain-adaptive behaviors based solely on proprioceptive feedback

### Key Innovations

1. **Feature-Enhanced Proprioceptive Encoder**: Leverages modality-specific sub-encoders and FiLM-based feature modulation to recover latent terrain cues under partial observability
2. **Behavior-Clustered Multi-Discriminator AMP**: Stabilizes adversarial training and enables style-consistent imitation across multiple motion behaviors
3. **Adaptive Multi-Style Reward Scheduling**: Ensures balanced learning across diverse locomotion styles

---

## Repository Functionality

This repository provides a comprehensive deployment and validation framework for FEAP policies, enabling researchers to:

- **Deploy trained FEAP policies** in MuJoCo simulation environment
- **Validate policy performance** through interactive control and real-time monitoring
- **Test diverse locomotion behaviors** including walking, running, and terrain navigation
- **Configure and calibrate input devices** (gamepad/keyboard) for robot control
- **Monitor real-time performance metrics** including velocity tracking, camera parameters, and disturbance forces

### Key Features

- ✅ **ONNX Model Deployment**: Direct deployment of trained policies without PyTorch dependencies
- ✅ **Dual Input Control**: Support for both gamepad and keyboard control (mutually exclusive)
- ✅ **Real-Time Visualization**: Terminal-based status display with camera and performance metrics
- ✅ **One-Click Environment Setup**: Automated conda environment configuration
- ✅ **Interactive Camera Control**: Adjustable camera view with pelvis tracking
- ✅ **Disturbance Testing**: Apply external forces for robustness evaluation

---

## Quick Start

### Prerequisites

- **Operating System**: Linux (Ubuntu/Debian recommended)
- **Python**: 3.8
- **Conda**: Anaconda or Miniconda
- **Hardware**: NVIDIA GPU (optional, for training; not required for deployment)

### Installation

1. **Clone the repository**:
   ```bash
   cd Feap_Mujoco_deployment
   ```

2. **Set up conda environment**:
   ```bash
   ./scripts/setup_conda_env.sh
   ```
   This script will:
   - Create a conda environment named `feap_mujoco` (default)
   - Install all required dependencies (MuJoCo, ONNX Runtime, Pygame, etc.)
   - Configure system dependencies and gamepad permissions

3. **Activate the environment**:
   ```bash
   conda activate feap_mujoco
   ```

### Running the Deployment

**Basic usage**:
```bash
python scripts/feap_e3_mujoco_deploy.py e3.yaml
```

**With full config path**:
```bash
python scripts/feap_e3_mujoco_deploy.py configs/e3.yaml
```

---

## Configuration

### Configuration File (`configs/e3.yaml`)

The configuration file controls simulation parameters, control settings, and input device preferences:

```yaml
# Policy and model paths
policy_path: "policy"  # Directory containing ONNX models
xml_path: "e3/scene_terrain.xml"  # MuJoCo scene file

# Simulation parameters
simulation_duration: 600.0  # Simulation duration in seconds
simulation_dt: 0.002  # Simulation timestep
control_decimation: 10  # Control frequency decimation

# Input device settings (mutually exclusive)
gamepad_enabled: False  # Enable gamepad control
keyboard_enabled: True  # Enable keyboard control

# Keyboard control parameters
cmd_step: 0.2  # Velocity command step size
camera_angle_step: 0.2  # Camera angle adjustment step
camera_distance_step: 0.2  # Camera distance adjustment step
camera_elevation_step: 0.2  # Camera elevation adjustment step
```

### Model Files

Place your trained ONNX models in the `policy/` directory:
- `HumanEncodernet.onnx` - Encoder network
- `HumanActornet.onnx` - Actor network

---

## Control Instructions

### Keyboard Control

When `keyboard_enabled: True` in the configuration:

| Key | Function |
|-----|----------|
| **W** | Forward velocity |
| **S** | Backward velocity |
| **A** | Rotate left (angular velocity) |
| **D** | Rotate right (angular velocity) |
| **J** | Move left (lateral velocity) |
| **L** | Move right (lateral velocity) |
| **C** | Clear all velocity commands |
| **B** | Reset robot state |
| **R** | Toggle camera control mode |
| **↑/↓** | Camera elevation (when camera mode enabled) |
| **←/→** | Camera angle (when camera mode enabled) |
| **U/O** | Camera distance decrease/increase |

**Note**: Type keys directly in the terminal (no Enter needed).

### Gamepad Control

When `gamepad_enabled: True` in the configuration:

- **Right Stick**: Forward/backward and lateral velocity control
- **Left Stick**: Angular velocity control (or disturbance force in disturbance mode)
- **D-Pad**: Camera rotation and distance control
- **LB Button**: Switch mode (Walk/Run/Disturbance Test)
- **X Button**: Toggle foot force display
- **Y Button**: Toggle pelvis tracking
- **B Button**: Reset robot state
- **A Button**: Toggle foot contact display

**Gamepad Calibration**: Run `python scripts/calibrate_gamepad.py` to calibrate your gamepad.

---

## Project Structure

```
Feap_Mujoco_deployment/
├── scripts/                          # Main scripts
│   ├── feap_e3_mujoco_deploy.py     # Main deployment script
│   ├── calibrate_gamepad.py         # Gamepad calibration tool
│   ├── setup_conda_env.sh           # Environment setup script
│   └── remove_conda_env.sh          # Environment removal script
├── configs/                          # Configuration files
│   └── e3.yaml                      # E3 robot configuration
├── policy/                           # ONNX model files
│   ├── HumanEncodernet.onnx
│   └── HumanActornet.onnx
├── e3/                               # E3 robot model files
│   ├── scene_terrain.xml            # MuJoCo scene
│   └── meshes/                      # Robot mesh files
├── gamepad_configs/                 # Gamepad calibration files
│   ├── gamepad_calibration_logitech.json
│   └── gamepad_calibration_betop.json
└── utils/                            # Utility modules
    ├── color_utils.py               # Terminal color output
    ├── display_utils.py             # Real-time status display
    ├── gamepad_utils.py             # Gamepad input handling
    ├── keyboard_utils.py            # Keyboard input handling
    ├── viewer_utils.py              # MuJoCo viewer control
    ├── disturbance_utils.py        # Disturbance force application
    ├── mode_utils.py                # Locomotion mode management
    ├── math_utils.py                # Mathematical utilities
    └── plot_utils.py                # Data plotting utilities
```

---

## Real-Time Display

The terminal displays real-time information in a fixed-position format:

```
  Velocity:  Cmd=[ 0.000,  0.000,  0.000]  Act=[ 0.011, -0.036,  0.055]  Err=[ 0.011, -0.036,  0.055]
  Mode:Walk(0) | Y:Track
  Camera: Angle= 299.8° Elev=  -8.6° Dist= 3.40m
```

- **Velocity**: Commanded vs. actual velocity with tracking error
- **Mode**: Current locomotion mode and tracking status
- **Camera**: Current camera view parameters

---

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError: No module named 'utils'**
   - Ensure you run the script from the project root directory
   - The script automatically adds the project root to Python path

2. **Gamepad not detected**
   - Check gamepad connection: `ls /dev/input/js*`
   - Run calibration: `python scripts/calibrate_gamepad.py`
   - Verify permissions: `/etc/udev/rules.d/99-joystick.rules`

3. **Keyboard controls not working**
   - Ensure `keyboard_enabled: True` in config
   - Make sure terminal has focus (not MuJoCo viewer window)
   - Type keys directly in terminal (no Enter needed)

4. **ONNX Runtime errors**
   - Verify ONNX models are in `policy/` directory
   - Check model file names match expected names
   - Ensure ONNX Runtime is installed: `pip install onnxruntime==1.19.2`

### Environment Management

**Remove conda environment**:
```bash
./scripts/remove_conda_env.sh
```

**Recreate environment**:
```bash
./scripts/setup_conda_env.sh
```

