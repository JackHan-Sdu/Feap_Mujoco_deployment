"""Viewer control and camera settings module"""
import numpy as np
import mujoco

# Viewer control related global variables
track_pelvis = True  # Whether to track pelvis (default: enabled)
show_contacts = False  # Whether to show contact status
show_forces = False  # Whether to show foot forces

# Use polar coordinate system to control camera (around pelvis root node)
# Default camera settings: Angle=299.8°, Elev=-8.6°, Dist=3.40m
camera_angle = np.radians(299.8)  # Horizontal rotation angle around robot (radians), 0 means in front of robot
camera_elevation = np.radians(-8.6)  # Camera elevation angle (radians), negative means looking down
camera_distance = 3.40  # Camera distance from robot (meters)
camera_angle_speed = 0.05  # Angle increment per rotation (radians)
camera_distance_speed = 0.1  # Step size for distance adjustment (meters)

# Reset related global variables
reset_requested = False  # Whether reset is requested

# Camera initialization flag
_camera_initialized = False  # Track if camera has been initialized


def update_viewer_settings(viewer, pelvis_body_id, d):
    """Update viewer settings (camera tracking and display options)
    
    When tracking is enabled, the camera will always look at pelvis (root),
    but mouse drag is allowed to rotate the camera around it.
    """
    global track_pelvis, show_contacts, show_forces
    global camera_angle, camera_elevation, camera_distance
    global _camera_initialized
    
    # Set camera to track pelvis and rotate around it
    if track_pelvis and pelvis_body_id >= 0:
        # Get pelvis position (d.xpos is an array of shape (nbody, 3))
        pelvis_pos = d.xpos[pelvis_body_id].copy()
        # Try to set camera tracking (MuJoCo viewer API may vary by version)
        try:
            if hasattr(viewer, 'cam'):
                # Set tracking target and mode (only need to set once, or when track_pelvis changes)
                viewer.cam.trackbodyid = pelvis_body_id
                viewer.cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING
                
                # Always set lookat to pelvis position (camera always looks at pelvis)
                viewer.cam.lookat[:] = pelvis_pos
                
                # Set camera parameters - always apply gamepad-controlled values
                # This allows both gamepad and mouse to control the camera
                viewer.cam.distance = camera_distance
                viewer.cam.azimuth = np.degrees(camera_angle)
                viewer.cam.elevation = np.degrees(camera_elevation)
                
                # After setting, sync back from viewer to allow mouse drag to update our variables
                # This creates a two-way sync: gamepad -> viewer, mouse -> our variables
                if _camera_initialized:
                    # Sync camera angles from viewer (allows mouse drag to update our variables)
                    camera_angle = np.radians(viewer.cam.azimuth)
                    camera_elevation = np.radians(viewer.cam.elevation)
                    camera_distance = viewer.cam.distance
                else:
                    _camera_initialized = True
                
                # Always ensure lookat is set to pelvis (in case mouse drag changed it)
                viewer.cam.lookat[:] = pelvis_pos
        except Exception:
            pass  # If API not supported, ignore error
    else:
        # If tracking is disabled, reset initialization flag so it reinitializes when re-enabled
        _camera_initialized = False
    
    # Set display options (contacts and forces)
    try:
        if hasattr(viewer, 'opt'):
            viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = (
                show_contacts
            )
            viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTFORCE] = (
                show_forces
            )
    except Exception:
        pass  # If API not supported, ignore error

