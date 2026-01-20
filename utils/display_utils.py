"""Terminal display utilities - for displaying robot status information at fixed positions"""
import sys
import numpy as np

class TerminalDisplay:
    """Terminal fixed-position display class using ANSI escape codes"""
    
    def __init__(self, filter_alpha=0.3):
        """
        Initialize display class
        
        Args:
            filter_alpha: Low-pass filter smoothing coefficient, range [0, 1], smaller = smoother, default 0.3
        """
        self.is_first_print = True
        # Title area: 3 lines (blank + separator + title + separator)
        # Display area: 4 lines (velocity + mode + camera + message)
        self.display_lines = 7  # Total lines to move up (3 title + 4 display)
        self.filter_alpha = filter_alpha  # Filter coefficient
        self.filtered_vel = None  # Filtered velocity [vx, vy, wz]
        
        # Status information
        self.current_mode = 0  # Current mode
        self.mode_name = "Walk"  # Mode name
        self.track_pelvis = False  # Whether tracking pelvis
        self.show_forces = False  # Whether showing foot forces
        self.show_contacts = False  # Whether showing foot contacts
        self.reset_requested = False  # Whether reset requested
        self.status_message = ""  # Status message (temporary display)
        
        # Camera and disturbance information
        self.camera_angle = 0.0  # Camera horizontal rotation angle (rad)
        self.camera_elevation = -0.5  # Camera elevation angle (rad)
        self.camera_distance = 3.0  # Camera distance (m)
        self.disturbance_force_magnitude = 0.0  # Disturbance force magnitude (N)
    
    def update_mode(self, mode, mode_name):
        """更新当前模式"""
        self.current_mode = mode
        self.mode_name = mode_name
    
    def update_status(self, track_pelvis=None, show_forces=None, show_contacts=None, 
                     reset_requested=None, status_message=None, camera_angle=None,
                     camera_elevation=None, camera_distance=None, disturbance_force_magnitude=None):
        """Update status information"""
        if track_pelvis is not None:
            self.track_pelvis = track_pelvis
        if show_forces is not None:
            self.show_forces = show_forces
        if show_contacts is not None:
            self.show_contacts = show_contacts
        if reset_requested is not None:
            self.reset_requested = reset_requested
        if status_message is not None:
            self.status_message = status_message
        if camera_angle is not None:
            self.camera_angle = camera_angle
        if camera_elevation is not None:
            self.camera_elevation = camera_elevation
        if camera_distance is not None:
            self.camera_distance = camera_distance
        if disturbance_force_magnitude is not None:
            self.disturbance_force_magnitude = disturbance_force_magnitude
    
    def display_all(self, cmd_vel, actual_vel):
        """
        在终端固定位置显示所有信息（速度、模式、状态）
        
        Args:
            cmd_vel: 指令速度 [vx_cmd, vy_cmd, wz_cmd]
            actual_vel: 实际速度 [vx_actual, vy_actual, wz_actual]
        """
        # 如果是第一次打印，先打印标题和分隔线
        if self.is_first_print:
            print("\n" + "=" * 70)
            print(" " * 15 + "Robot Status Display")
            print("=" * 70)
            self.is_first_print = False
        
        # 提取速度分量
        vx_cmd = cmd_vel[0] if len(cmd_vel) > 0 else 0.0
        vy_cmd = cmd_vel[1] if len(cmd_vel) > 1 else 0.0
        wz_cmd = cmd_vel[2] if len(cmd_vel) > 2 else 0.0
        
        vx_actual = actual_vel[0] if len(actual_vel) > 0 else 0.0
        vy_actual = actual_vel[1] if len(actual_vel) > 1 else 0.0
        wz_actual = actual_vel[2] if len(actual_vel) > 2 else 0.0
        
        # 对实际速度进行低通滤波（指数移动平均）
        current_vel = np.array([vx_actual, vy_actual, wz_actual])
        if self.filtered_vel is None:
            self.filtered_vel = current_vel.copy()
        else:
            self.filtered_vel = self.filter_alpha * current_vel + (1 - self.filter_alpha) * self.filtered_vel
        
        vx_filtered = self.filtered_vel[0]
        vy_filtered = self.filtered_vel[1]
        wz_filtered = self.filtered_vel[2]
        
        # 计算误差
        vx_error = vx_filtered - vx_cmd
        vy_error = vy_filtered - vy_cmd
        wz_error = wz_filtered - wz_cmd
        
        # Update display at fixed positions without creating new lines
        # Save current cursor position
        sys.stdout.write('\033[s')
        
        # Move up to first display line (skip 3 title lines: blank + separator + title + separator)
        sys.stdout.write('\033[3A')
        
        # Line 1: Velocity information
        sys.stdout.write('\r\033[2K')  # Clear line and move to start
        sys.stdout.write(f"  Velocity:  Cmd=[{vx_cmd:6.3f}, {vy_cmd:6.3f}, {wz_cmd:6.3f}]  Act=[{vx_filtered:6.3f}, {vy_filtered:6.3f}, {wz_filtered:6.3f}]  Err=[{vx_error:6.3f}, {vy_error:6.3f}, {wz_error:6.3f}]")
        
        # Line 2: Mode and button status
        sys.stdout.write('\033[1B\r\033[2K')  # Move down one line, clear and move to start
        status_parts = [f"Mode:{self.mode_name}({self.current_mode})"]
        if self.track_pelvis:
            status_parts.append("Y:Track")
        if self.show_forces:
            status_parts.append("X:Force")
        if self.show_contacts:
            status_parts.append("A:Contact")
        if self.reset_requested:
            status_parts.append("B:Reset")
        status_str = "  " + " | ".join(status_parts)
        sys.stdout.write(status_str)
        
        # Line 3: Camera and disturbance information
        sys.stdout.write('\033[1B\r\033[2K')  # Move down one line, clear and move to start
        camera_info = f"  Camera: Angle={np.degrees(self.camera_angle):6.1f}° Elev={np.degrees(self.camera_elevation):6.1f}° Dist={self.camera_distance:5.2f}m"
        if self.disturbance_force_magnitude > 1e-6:
            disturbance_info = f" | Disturbance: {self.disturbance_force_magnitude:6.2f}N"
            sys.stdout.write(f"{camera_info}{disturbance_info}")
        else:
            sys.stdout.write(camera_info)
        
        # Line 4: Status message (if any)
        sys.stdout.write('\033[1B\r\033[2K')  # Move down one line, clear and move to start
        if self.status_message:
            sys.stdout.write(f"  Info: {self.status_message}")
            self.status_message = ""  # Clear message (display only once)
        
        # Restore cursor position
        sys.stdout.write('\033[u')
        sys.stdout.flush()

# 全局单例
_display_instance = None

def get_display():
    """获取全局显示实例"""
    global _display_instance
    if _display_instance is None:
        _display_instance = TerminalDisplay()
    return _display_instance

def display_velocity_info(cmd_vel, actual_vel):
    """便捷函数：显示速度信息（兼容旧接口）"""
    display = get_display()
    display.display_all(cmd_vel, actual_vel)

def display_all_info(cmd_vel, actual_vel):
    """便捷函数：显示所有信息"""
    display = get_display()
    display.display_all(cmd_vel, actual_vel)

def update_mode(mode, mode_name):
    """更新模式信息"""
    display = get_display()
    display.update_mode(mode, mode_name)

def update_status(**kwargs):
    """Update status information"""
    display = get_display()
    display.update_status(**kwargs)
