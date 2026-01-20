"""Feap E3 Humanoid Robot Policy Deployment & Validation Script for MuJoCo Simulation"""
import time
import mujoco.viewer
import mujoco
import numpy as np
import yaml
import pygame
import os
import sys

# Add project root directory to Python path so utils module can be imported
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)  # Parent directory of scripts/
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import onnxruntime
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    raise ImportError("onnxruntime is not installed. ONNX model support is unavailable. Install with 'pip install onnxruntime'.")

# Import utility modules
from utils.color_utils import (
    print_feap_banner, print_header, print_section, print_info,
    print_success, print_warning, print_error, Colors, colored
)
from utils.math_utils import get_gravity_orientation, pd_control, quat_to_rot_matrix
from utils.gamepad_utils import (
    init_gamepad, update_cmd_from_gamepad, joystick,
    get_current_mode
)
from utils.keyboard_utils import (
    init_keyboard, update_cmd_from_keyboard, stop_keyboard, set_keyboard_cmd_ref
)
from utils.mode_utils import mode_names
from utils.disturbance_utils import apply_disturbance_force, set_disturbance_body_id
from utils.plot_utils import (
    recording, record_start_time, record_duration,
    tau_history, dqj_history, time_history, plot_data, reset_recording
)
import utils.plot_utils as plot_utils  # For modifying global variables
import utils.viewer_utils as viewer_utils  # For accessing and modifying viewer-related global variables
from utils.display_utils import display_all_info, update_mode, update_status  # For displaying information
from utils.math_utils import quat_to_rot_matrix  # For coordinate system transformation

# ==================== Main Program ====================
if __name__ == "__main__":
    # Print Feap banner
    print_feap_banner()
    
    # Get config file name from command line
    import argparse

    parser = argparse.ArgumentParser(description="Feap E3 Humanoid Robot Policy Deployment & Validation")
    parser.add_argument("config_file", type=str, help="config file name (e.g., e3.yaml or configs/e3.yaml)")
    args = parser.parse_args()
    config_file = args.config_file
    
    # Get script directory (scripts/) and project root directory
    # Note: script_dir and project_root are already defined at the top of the file
    # Handle both cases: "e3.yaml" or "configs/e3.yaml"
    if config_file.startswith("configs/"):
        config_path = os.path.join(project_root, config_file)
    else:
        config_path = os.path.join(project_root, "configs", config_file)
    
    print_section("Configuration Loading", Colors.BRIGHT_CYAN)
    
    with open(config_path, "r", encoding='utf-8') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
        # policy_path now points to the folder containing ONNX files
        policy_dir = config["policy_path"]
        xml_path = config["xml_path"]
        
        # Convert relative paths to absolute paths (relative to project root)
        if not os.path.isabs(policy_dir):
            policy_dir = os.path.join(project_root, policy_dir)
        if not os.path.isabs(xml_path):
            xml_path = os.path.join(project_root, xml_path)

        simulation_duration = config["simulation_duration"]
        simulation_dt = config["simulation_dt"]
        control_decimation = config["control_decimation"]
        kps = np.array(config["kps"], dtype=np.float32)
        kds = np.array(config["kds"], dtype=np.float32)

        default_angles = np.array(config["default_angles"], dtype=np.float32)
        print_info("Default Joint Angles", f"{len(default_angles)} DOF", Colors.CYAN, Colors.WHITE)

        ang_vel_scale = config["ang_vel_scale"]
        dof_pos_scale = config["dof_pos_scale"]
        dof_vel_scale = config["dof_vel_scale"]
        action_scale = config["action_scale"]
        cmd_scale = np.array(config["cmd_scale"], dtype=np.float32)

        num_actions = config["num_actions"]
        # Read whether to include phase from config, default to False if not present
        include_phase = config.get("include_phase_in_obs", False)
        # If phase is included, add 2 to the base observation dimension
        num_obs = config["num_obs"]
        if include_phase:
            num_obs += 2
        
        print_info("Actions", num_actions, Colors.CYAN, Colors.WHITE)
        print_info("Observations", num_obs, Colors.CYAN, Colors.WHITE)
        print_info("Include Phase", include_phase, Colors.CYAN, Colors.WHITE)
        
        cmd = np.array(config["cmd_init"], dtype=np.float32)

    # Define context variables
    action = np.zeros(num_actions, dtype=np.float32)
    target_dof_pos = default_angles.copy()
    obs = np.zeros(num_obs, dtype=np.float32)

    counter = 0

    # Load robot model
    print_section("MuJoCo Model Loading", Colors.BRIGHT_CYAN)
    print_info("XML Path", xml_path, Colors.CYAN, Colors.WHITE)
    m = mujoco.MjModel.from_xml_path(xml_path)
    d = mujoco.MjData(m)
    m.opt.timestep = simulation_dt
    print_success(f"Robot model loaded successfully (dt={simulation_dt}s)")
    
    # Save initial state for reset
    initial_qpos = d.qpos.copy()
    initial_qvel = d.qvel.copy()
    initial_cmd = cmd.copy()  # Save initial velocity command

    # Load ONNX policy models
    print_section("ONNX Policy Model Loading", Colors.BRIGHT_CYAN)
    if not ONNX_AVAILABLE:
        raise RuntimeError("ONNX models require onnxruntime, but it is not installed. Install with 'pip install onnxruntime'.")
    
    # For ONNX, need to load two models: encoder and actor
    # policy_dir is now directly the folder path containing ONNX files
    encoder_path = os.path.join(policy_dir, "HumanEncodernet.onnx")
    actor_path = os.path.join(policy_dir, "HumanActornet.onnx")
    
    if not os.path.exists(encoder_path):
        raise FileNotFoundError(f"Encoder ONNX model not found: {encoder_path}")
    if not os.path.exists(actor_path):
        raise FileNotFoundError(f"Actor ONNX model not found: {actor_path}")
    
    # Create ONNX Runtime sessions
    encoder_session = ort.InferenceSession(encoder_path)
    actor_session = ort.InferenceSession(actor_path)
    
    # Initialize RNN hidden states
    # Encoder: (1, 1, 256)
    encoder_h0 = np.zeros((1, 1, 256), dtype=np.float32)
    encoder_c0 = np.zeros((1, 1, 256), dtype=np.float32)
    # Actor: (1, 1, 64)
    actor_h0 = np.zeros((1, 1, 64), dtype=np.float32)
    actor_c0 = np.zeros((1, 1, 64), dtype=np.float32)
    
    print_success("ONNX models loaded successfully")
    print_info("Encoder", encoder_path, Colors.GREEN, Colors.WHITE)
    print_info("Actor", actor_path, Colors.GREEN, Colors.WHITE)
    
    # Initialize input device (gamepad or keyboard, mutually exclusive)
    keyboard_enabled = config.get("keyboard_enabled", False)
    gamepad_enabled = config.get("gamepad_enabled", True)  # Default to True if not specified
    
    # If keyboard is enabled, disable gamepad (mutually exclusive)
    if keyboard_enabled:
        gamepad_enabled = False
        config["gamepad_enabled"] = False  # Update config to reflect the change
        print_section("Keyboard Initialization", Colors.BRIGHT_CYAN)
        init_keyboard(config)
    elif gamepad_enabled:
        # Initialize gamepad only if keyboard is not enabled
        print_section("Gamepad Initialization", Colors.BRIGHT_CYAN)
        init_gamepad(config)
    else:
        print_info("Input Control", "No input device enabled (using default commands)", Colors.YELLOW, Colors.WHITE)
    
    # Find pelvis body ID
    pelvis_body_id = None
    try:
        pelvis_body_id = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "pelvis_link")
    except Exception:
        try:
            pelvis_body_id = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "base_link")
        except Exception:
            print_warning("pelvis_link or base_link not found, using body 0")
            pelvis_body_id = 0
    
    if pelvis_body_id >= 0:
        print_info("Pelvis Body ID", pelvis_body_id, Colors.CYAN, Colors.WHITE)
    else:
        print_warning("Pelvis body not found")
        pelvis_body_id = 0
    
    # Initialize disturbance body ID
    set_disturbance_body_id(m)
    
    phase = 0.0
    last_gamepad_update = time.time()
    gamepad_update_interval = 0.02  # Gamepad update interval (50Hz)
    
    current_mode = get_current_mode()
    # Initialize mode information in display
    update_mode(current_mode, mode_names[current_mode])
    
    # Initialize display status with camera parameters and tracking state
    import utils.viewer_utils as viewer_utils
    update_status(
        track_pelvis=viewer_utils.track_pelvis,
        camera_angle=viewer_utils.camera_angle,
        camera_elevation=viewer_utils.camera_elevation,
        camera_distance=viewer_utils.camera_distance
    )
    
    print_section("Simulation Starting", Colors.BRIGHT_GREEN)
    print_info("Duration", f"{simulation_duration}s", Colors.GREEN, Colors.WHITE)
    print_info("Control Frequency", f"{1.0/(simulation_dt * control_decimation):.1f} Hz", Colors.GREEN, Colors.WHITE)
    print_info("Camera Tracking", "Enabled (pelvis)", Colors.GREEN, Colors.WHITE)
    print(colored("\n" + "="*70, Colors.BRIGHT_CYAN))
    print(colored("Simulation is running. Press Ctrl+C to exit.", Colors.BOLD + Colors.BRIGHT_GREEN))
    print(colored("="*70 + "\n", Colors.BRIGHT_CYAN))
    
    # Set command reference for keyboard control (terminal input mode)
    if config.get("keyboard_enabled", False):
        set_keyboard_cmd_ref(cmd)
    
    try:
        with mujoco.viewer.launch_passive(m, d) as viewer:
            # Close the viewer automatically after simulation_duration wall-seconds.
            start = time.time()
            while viewer.is_running() and time.time() - start < simulation_duration:
                step_start = time.time()
                
                # Handle reset request
                if viewer_utils.reset_requested:
                    # Reset robot state
                    d.qpos[:] = initial_qpos
                    d.qvel[:] = initial_qvel
                    # Reset velocity command
                    cmd[:] = initial_cmd
                    # Reset action and target position
                    action[:] = 0.0
                    target_dof_pos[:] = default_angles.copy()
                    # Reset phase
                    phase = 0.0
                    # Reset counter
                    counter = 0
                    # Reset data recording
                    reset_recording()
                    # Clear external forces
                    d.xfrc_applied[:] = 0.0
                    # Reset RNN hidden states
                    encoder_h0 = np.zeros((1, 1, 256), dtype=np.float32)
                    encoder_c0 = np.zeros((1, 1, 256), dtype=np.float32)
                    actor_h0 = np.zeros((1, 1, 64), dtype=np.float32)
                    actor_c0 = np.zeros((1, 1, 64), dtype=np.float32)
                    # Reset reset flag and update display
                    viewer_utils.reset_requested = False
                    update_status(reset_requested=False, status_message="Robot state reset")
                    # Execute one simulation step to apply reset
                    mujoco.mj_step(m, d)
                    viewer.sync()
                    continue
                
                # Update input device (gamepad or keyboard, mutually exclusive)
                if keyboard_enabled:
                    # Update keyboard input (if enabled)
                    # Terminal input is handled in background thread, we just update the command reference
                    cmd = update_cmd_from_keyboard(cmd)
                    set_keyboard_cmd_ref(cmd)
                elif gamepad_enabled:
                    # Periodically update gamepad input
                    current_time = time.time()
                    if current_time - last_gamepad_update >= gamepad_update_interval:
                        cmd = update_cmd_from_gamepad(cmd)
                        cmd[0] *= 1.0
                        last_gamepad_update = current_time
                
                # Apply disturbance force (if in disturbance mode)
                force_base, torso_pos = apply_disturbance_force(m, d)
                
                tau = pd_control(target_dof_pos, d.qpos[7:], kps, np.zeros_like(kds), d.qvel[6:], kds)
                d.ctrl[:] = tau
                # Execute one simulation step
                mujoco.mj_step(m, d)

                counter += 1
                if counter % control_decimation == 0:
                    # create observation
                    qj = d.qpos[7:]
                    dqj = d.qvel[6:]
                    quat = d.qpos[3:7]
                    omega = d.qvel[3:6]

                    qj = (qj - default_angles) * dof_pos_scale
                    dqj = dqj * dof_vel_scale
                    gravity_orientation = get_gravity_orientation(quat)
                    omega = omega * ang_vel_scale

                    walk_period = 0.8
                    run_period = 0.7

                    # Get velocity in world frame
                    world_lin_vel = d.qvel[0:3]  # Linear velocity in world frame
                    world_ang_vel = d.qvel[3:6]  # Angular velocity in world frame
                    
                    # Transform world frame velocity to base frame
                    # Get base rotation quaternion (MuJoCo format: [w, x, y, z])
                    base_quat = d.qpos[3:7]
                    # Convert to rotation matrix
                    rot_matrix = quat_to_rot_matrix(base_quat)
                    # Transform world frame velocity to base frame (requires inverse rotation)
                    rot_matrix_inv = rot_matrix.T  # Transpose of rotation matrix equals its inverse
                    base_lin_vel = rot_matrix_inv @ world_lin_vel
                    base_ang_vel = rot_matrix_inv @ world_ang_vel
                    
                    vx = base_lin_vel[0]   # Base linear velocity in x
                    vy = base_lin_vel[1]   # Base linear velocity in y
                    wz = base_ang_vel[2]   # Base angular velocity around z
                    
                    # Update status information and display all information
                    cmd_vel = np.array([cmd[0], cmd[1], cmd[2] if len(cmd) > 2 else 0.0])
                    actual_vel = np.array([vx, vy, wz])
                    
                    # Sync viewer state to display
                    import utils.viewer_utils as viewer_utils
                    
                    # Calculate disturbance force magnitude
                    disturbance_force_magnitude = 0.0
                    if force_base is not None:
                        disturbance_force_magnitude = np.linalg.norm(force_base)
                    
                    update_status(
                        track_pelvis=viewer_utils.track_pelvis,
                        show_forces=viewer_utils.show_forces,
                        show_contacts=viewer_utils.show_contacts,
                        reset_requested=viewer_utils.reset_requested,
                        camera_angle=viewer_utils.camera_angle,
                        camera_elevation=viewer_utils.camera_elevation,
                        camera_distance=viewer_utils.camera_distance,
                        disturbance_force_magnitude=disturbance_force_magnitude
                    )
                    # Note: reset_requested will be cleared during reset handling, no need to clear here
                    
                    # Display all information
                    display_all_info(cmd_vel, actual_vel)
                    
                    planar_twist_norm = np.linalg.norm([vx, vy, wz])
                    # Determine if stationary
                    if (planar_twist_norm > 0.2) or (np.linalg.norm(cmd) > 0.1):
                        speed_cmd = abs(cmd[0])
                        period = run_period if speed_cmd > 1.1 else walk_period
                        phase += (simulation_dt * control_decimation) / period
                        phase %= 1.0
                    else:
                        phase *= 0.5
                        if phase < 1e-3:   # Threshold cutoff
                            phase = 0.0

                    obs[:3] = omega
                    obs[3:6] = gravity_orientation
                    obs[6:9] = cmd * cmd_scale
                    obs[9:9 + num_actions] = qj
                    obs[9 + num_actions:9 + 2 * num_actions] = dqj
                    obs[9 + 2 * num_actions:9 + 3 * num_actions] = action
                    
                    # Include phase in observation based on configuration
                    if include_phase:
                        # Calculate sine and cosine phase
                        sin_phase = np.sin(2 * np.pi * phase)
                        cos_phase = np.cos(2 * np.pi * phase)
                        # Add phase to observation
                        obs[9 + 3 * num_actions:9 + 3 * num_actions + 2] = np.array([sin_phase, cos_phase])
                    
                    # ONNX policy inference: first through encoder, then through actor
                    obs_input = obs.astype(np.float32).reshape(1, -1)
                    
                    # Encoder inference
                    encoder_inputs = {
                        "obs": obs_input,
                        "h0": encoder_h0,
                        "c0": encoder_c0
                    }
                    encoder_outputs = encoder_session.run(None, encoder_inputs)
                    latent = encoder_outputs[0]  # (1, 37)
                    encoder_h0 = encoder_outputs[1]  # Update hidden state
                    encoder_c0 = encoder_outputs[2]  # Update cell state
                    
                    # Actor inference
                    actor_inputs = {
                        "obs": obs_input,
                        "latent": latent,
                        "h0": actor_h0,
                        "c0": actor_c0
                    }
                    actor_outputs = actor_session.run(None, actor_inputs)
                    action = actor_outputs[0].squeeze()  # (21,)
                    actor_h0 = actor_outputs[1]  # Update hidden state
                    actor_c0 = actor_outputs[2]  # Update cell state
                    
                    # Transform action to target_dof_pos
                    target_dof_pos = action * action_scale + default_angles

                    # Record tau and dqj data if recording and within 5 seconds
                    if plot_utils.recording:
                        current_time = time.time() - plot_utils.record_start_time
                        if current_time <= plot_utils.record_duration:
                            time_history.append(current_time)
                            tau_history.append(tau.copy())
                            dqj_history.append((dqj / dof_vel_scale).copy())
                        else:
                            # Stop recording and plot after 5 seconds
                            plot_utils.recording = False
                            print("Recording finished, plotting data...")
                            plot_data()

                # Update viewer settings
                viewer_utils.update_viewer_settings(viewer, pelvis_body_id, d)
                
                # Update viewer, capture GUI changes and disturbances
                viewer.sync()

                # Control step size
                time_until_next_step = m.opt.timestep - (time.time() - step_start)
                if time_until_next_step > 0:
                    time.sleep(time_until_next_step)
    except KeyboardInterrupt:
        print_info("\nSimulation", "Interrupted by user", Colors.YELLOW, Colors.WHITE)
    finally:
        # Cleanup keyboard input thread and restore terminal settings
        if config.get("keyboard_enabled", False):
            stop_keyboard()
        
        # Cleanup pygame
        if joystick is not None:
            joystick.quit()
        pygame.quit()
