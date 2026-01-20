"""Gamepad-related functions and state module"""
import pygame
import numpy as np
import json
import os
from .mode_utils import MODE_WALK, MODE_RUN, MODE_DISTURBANCE, mode_names, get_cmd_max_for_mode
from .viewer_utils import (
    track_pelvis, show_contacts, show_forces, reset_requested,
    camera_angle, camera_elevation, camera_distance,
    camera_angle_speed, camera_distance_speed
)
from . import viewer_utils  # For modifying global variables
from .color_utils import print_info, print_success, print_warning, Colors, colored

# Gamepad-related global variables
joystick = None
deadzone = 0.1  # Joystick deadzone, values below this are considered no input
button_states = {}  # Button state cache for detecting button press events (from release to press)
gamepad_calibration = None  # Gamepad calibration data
# Axis mapping: determined by gamepad type (left stick X, left stick Y, right stick X, right stick Y)
axis_mapping = [0, 1, 2, 3]  # Default Logitech mapping

# Mode control (imported from mode_utils, but needs local state)
current_mode = MODE_WALK  # Current mode

# Disturbance test related (imported from disturbance_utils)
disturbance_force_scale = 100.0  # Disturbance force scaling factor (N)
disturbance_body_name = "torso_link"  # Default body to apply disturbance force

# Running mode filter related
run_mode_filter_alpha = 0.02  # Filter coefficient for x-direction command in running mode (0-1, larger = faster response)
prev_cmd_x = 0.0  # Previous frame's x-direction command value


def set_axis_mapping_from_type(gamepad_type, axis_mapping_custom=None):
    """Set axis mapping based on gamepad type
    
    Args:
        gamepad_type: Gamepad type ('logitech', 'betop', 'custom')
        axis_mapping_custom: Custom axis mapping [left stick X, left stick Y, right stick X, right stick Y],
                             only used when gamepad_type='custom'
    """
    global axis_mapping
    
    if gamepad_type == 'betop':
        axis_mapping = [0, 1, 3, 4]  # Betop: left stick 0,1, right stick 3,4
        print_info("Gamepad Type", f"Betop - Axis mapping: Left({axis_mapping[0]},{axis_mapping[1]}), Right({axis_mapping[2]},{axis_mapping[3]})", Colors.CYAN, Colors.WHITE)
    elif gamepad_type == 'custom':
        if axis_mapping_custom is not None and len(axis_mapping_custom) == 4:
            axis_mapping = axis_mapping_custom
            print_info("Gamepad Type", f"Custom - Axis mapping: Left({axis_mapping[0]},{axis_mapping[1]}), Right({axis_mapping[2]},{axis_mapping[3]})", Colors.CYAN, Colors.WHITE)
        else:
            print_warning("Custom gamepad type specified but no axis mapping provided, using default (Logitech)")
            axis_mapping = [0, 1, 2, 3]
    else:
        axis_mapping = [0, 1, 2, 3]  # Default Logitech
        print_info("Gamepad Type", f"Logitech - Axis mapping: Left({axis_mapping[0]},{axis_mapping[1]}), Right({axis_mapping[2]},{axis_mapping[3]})", Colors.CYAN, Colors.WHITE)


def get_calibration_file_path(gamepad_type=None, custom_path=None):
    """Get calibration file path
    
    Args:
        gamepad_type: Gamepad type, if provided generates corresponding filename
        custom_path: Custom calibration file path (read from yaml config)
    
    Returns:
        Calibration file path
    """
    # Get deploy directory (parent directory of utils)
    deploy_dir = os.path.dirname(os.path.dirname(__file__))
    # Calibration files are stored in gamepad_configs folder
    gamepad_configs_dir = os.path.join(deploy_dir, "gamepad_configs")
    
    # If custom path is specified, use it directly
    if custom_path:
        # If relative path, relative to deploy directory
        if not os.path.isabs(custom_path):
            return os.path.join(deploy_dir, custom_path)
        return custom_path
    
    # If gamepad type is specified, generate corresponding filename
    if gamepad_type:
        base_name = f"gamepad_calibration_{gamepad_type}.json"
        return os.path.join(gamepad_configs_dir, base_name)
    
    # Default return None, let caller handle
    return None


def load_gamepad_calibration(config=None):
    """Load gamepad calibration file and configuration
    
    Args:
        config: Configuration dictionary, may contain:
            - gamepad_type: Gamepad type
            - axis_mapping: Custom axis mapping
            - gamepad_calibration_file: Calibration file path (optional, if specified use this file)
    """
    global gamepad_calibration, axis_mapping
    
    # Priority: calibration file in config > gamepad_type in config > calibration file > default
    gamepad_type = None
    axis_mapping_custom = None
    calibration_file_path = None
    
    # 1. First read from config file
    if config is not None:
        # Priority: read specified calibration file path
        calibration_file_path = config.get('gamepad_calibration_file')
        gamepad_type = config.get('gamepad_type')
        axis_mapping_custom = config.get('axis_mapping')
        
        # If calibration file path is specified, load directly
        if calibration_file_path:
            calibration_file = get_calibration_file_path(custom_path=calibration_file_path)
            if os.path.exists(calibration_file):
                try:
                    with open(calibration_file, 'r', encoding='utf-8') as f:
                        gamepad_calibration = json.load(f)
                    print_info("Calibration File", f"Loaded from config: {calibration_file}", Colors.GREEN, Colors.WHITE)
                    print_info("  Joystick Name", gamepad_calibration.get('joystick_name', 'Unknown'), Colors.CYAN, Colors.WHITE)
                    print_info("  Calibration Date", gamepad_calibration.get('calibration_date', 'Unknown'), Colors.CYAN, Colors.WHITE)
                    
                    # Get gamepad type from calibration file (if not specified in config)
                    if not gamepad_type:
                        gamepad_type = gamepad_calibration.get('gamepad_type', 'logitech')
                    
                    # 处理自定义映射
                    if gamepad_type == 'custom':
                        axes = gamepad_calibration.get('axes', {})
                        if len(axes) >= 4 and not axis_mapping_custom:
                            axis_mapping_custom = [None, None, None, None]
                            for axis_id_str, axis_cal in axes.items():
                                axis_id = int(axis_id_str)
                                name = axis_cal.get('name', '')
                                if '左摇杆X' in name or '角速度' in name:
                                    axis_mapping_custom[0] = axis_id
                                elif '左摇杆Y' in name or '扰动力' in name:
                                    axis_mapping_custom[1] = axis_id
                                elif '右摇杆X' in name or '左右速度' in name:
                                    axis_mapping_custom[2] = axis_id
                                elif '右摇杆Y' in name or '前后速度' in name:
                                    axis_mapping_custom[3] = axis_id
                            
                            if None in axis_mapping_custom:
                                axis_ids = sorted([int(k) for k in axes.keys()])
                                if len(axis_ids) >= 4:
                                    axis_mapping_custom = axis_ids[:4]
                    
                    set_axis_mapping_from_type(gamepad_type, axis_mapping_custom)
                    return gamepad_calibration
                except Exception as e:
                    print_warning(f"Failed to load calibration file: {e}")
                    gamepad_calibration = None
        
        # If gamepad_type is specified in config but no calibration file, generate filename based on type
        if gamepad_type and not calibration_file_path:
            print_info("Gamepad Type", f"Read from config: {gamepad_type}", Colors.CYAN, Colors.WHITE)
            if axis_mapping_custom:
                print_info("Custom Axis Mapping", f"Read from config: {axis_mapping_custom}", Colors.CYAN, Colors.WHITE)
            set_axis_mapping_from_type(gamepad_type, axis_mapping_custom)
            
            # Generate calibration file path based on gamepad_type
            calibration_file = get_calibration_file_path(gamepad_type=gamepad_type)
            if os.path.exists(calibration_file):
                try:
                    with open(calibration_file, 'r', encoding='utf-8') as f:
                        gamepad_calibration = json.load(f)
                    print_success(f"Calibration file loaded (for button and axis center calibration): {calibration_file}")
                except Exception as e:
                    print_warning(f"Failed to load calibration file: {e}")
            else:
                print_warning(f"Calibration file not found: {calibration_file}")
                print_info("", "Run calibrate_gamepad.py to calibrate", Colors.YELLOW, Colors.WHITE)
            return gamepad_calibration
    
    # 2. If no config file or nothing in config, try reading from calibration files (try by priority)
    if gamepad_type is None:
        # Try loading by priority: betop > logitech > custom
        for gp_type in ['betop', 'logitech', 'custom']:
            calibration_file = get_calibration_file_path(gamepad_type=gp_type)
            if os.path.exists(calibration_file):
                try:
                    with open(calibration_file, 'r', encoding='utf-8') as f:
                        gamepad_calibration = json.load(f)
                    print_success(f"Calibration file loaded: {calibration_file}")
                    print_info("  Joystick Name", gamepad_calibration.get('joystick_name', 'Unknown'), Colors.CYAN, Colors.WHITE)
                    print_info("  Calibration Date", gamepad_calibration.get('calibration_date', 'Unknown'), Colors.CYAN, Colors.WHITE)
                    
                    # Get gamepad type from calibration file
                    gamepad_type = gamepad_calibration.get('gamepad_type', 'logitech')
                    
                    if gamepad_type == 'custom':
                        # Custom mapping, extract from calibrated axes by function order
                        axes = gamepad_calibration.get('axes', {})
                        if len(axes) >= 4:
                            # Match by function name: left stick X, left stick Y, right stick X, right stick Y
                            axis_mapping_custom = [None, None, None, None]
                            for axis_id_str, axis_cal in axes.items():
                                axis_id = int(axis_id_str)
                                name = axis_cal.get('name', '')
                                if '左摇杆X' in name or '角速度' in name or 'angular' in name.lower():
                                    axis_mapping_custom[0] = axis_id
                                elif '左摇杆Y' in name or '扰动力' in name or 'disturbance' in name.lower():
                                    axis_mapping_custom[1] = axis_id
                                elif '右摇杆X' in name or '左右速度' in name or 'lateral' in name.lower():
                                    axis_mapping_custom[2] = axis_id
                                elif '右摇杆Y' in name or '前后速度' in name or 'forward' in name.lower():
                                    axis_mapping_custom[3] = axis_id
                            
                            # If matching fails, sort by axis ID as fallback
                            if None in axis_mapping_custom:
                                axis_ids = sorted([int(k) for k in axes.keys()])
                                if len(axis_ids) >= 4:
                                    axis_mapping_custom = axis_ids[:4]
                    
                    set_axis_mapping_from_type(gamepad_type, axis_mapping_custom)
                    break
                except Exception as e:
                    print_warning(f"Failed to load calibration file: {e}")
                    gamepad_calibration = None
                    continue
        
        if gamepad_calibration is None:
            print_warning("No calibration file found")
            print_info("", "Run calibrate_gamepad.py to calibrate", Colors.YELLOW, Colors.WHITE)
    
    # 3. If nothing found, use default
    if gamepad_type is None:
        print_info("Axis Mapping", "Using default (Logitech: left stick 0,1, right stick 2,3)", Colors.CYAN, Colors.WHITE)
        set_axis_mapping_from_type('logitech')
    
    return gamepad_calibration


def apply_axis_calibration(axis_id, raw_value):
    """应用轴校准：减去中位值（不再反转方向）"""
    global gamepad_calibration
    
    if gamepad_calibration is None:
        return raw_value
    
    axes = gamepad_calibration.get('axes', {})
    # 尝试字符串键和整数键
    axis_cal = axes.get(str(axis_id)) or axes.get(axis_id)
    
    if axis_cal is None:
        return raw_value
    
    # 减去中位值（不再反转方向）
    calibrated_value = raw_value - axis_cal.get('center', 0.0)
    
    return calibrated_value


def get_calibrated_button_id(button_name, default_ids=None):
    """获取校准后的按钮ID
    
    Args:
        button_name: 按钮名称 ('LB', 'RB', 'X', 'Y', 'B', 'A')
        default_ids: 默认按钮ID列表（如果未校准，尝试这些ID）
    
    Returns:
        按钮ID，如果未找到返回None
    """
    global gamepad_calibration
    
    if gamepad_calibration is None:
        # 未校准，使用默认ID
        if default_ids is not None:
            return default_ids
        return None
    
    buttons = gamepad_calibration.get('buttons', {})
    button_cal = buttons.get(button_name)
    
    if button_cal is not None:
        return button_cal.get('button_id')
    
    # 如果未找到校准，使用默认ID
    if default_ids is not None:
        return default_ids
    return None


def init_gamepad(config=None):
    """初始化游戏手柄
    
    Args:
        config: 配置文件字典，可能包含 gamepad_type 和 axis_mapping 配置
    """
    global joystick
    pygame.init()
    pygame.joystick.init()
    
    # Check if gamepad is connected
    if pygame.joystick.get_count() == 0:
        print_warning("No gamepad detected, will use default velocity commands")
        return None
    
    # Initialize first gamepad
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print_success(f"Gamepad connected: {joystick.get_name()}")
    
    # Load calibration file and configuration
    load_gamepad_calibration(config)
    
    print_gamepad_controls()
    return joystick


def print_gamepad_controls():
    """Print gamepad control instructions"""
    print(colored("=" * 70, Colors.BRIGHT_CYAN))
    print(colored("Gamepad Control Instructions", Colors.BOLD + Colors.BRIGHT_CYAN).center(70))
    print(colored("=" * 70, Colors.BRIGHT_CYAN))
    print(colored("  Right Stick Up/Down", Colors.CYAN) + ": Control forward/backward velocity (cmd[0])")
    print(colored("  Right Stick Left/Right", Colors.CYAN) + ": Control left/right velocity (cmd[1])")
    print(colored("  Left Stick Left/Right", Colors.CYAN) + ": Control angular velocity (cmd[2]), disabled in disturbance mode")
    print(colored("  Left Stick", Colors.CYAN) + ": Control disturbance force in disturbance mode (X=left/right, Y=forward/backward)")
    print(colored("  D-Pad Left/Right", Colors.CYAN) + ": Rotate camera around robot (when tracking pelvis)")
    print(colored("  D-Pad Up/Down", Colors.CYAN) + ": Control camera distance (when tracking pelvis)")
    print(colored("  LB Button", Colors.CYAN) + ": Switch mode (Walk/Run/Disturbance Test)")
    print(colored("  X Button", Colors.CYAN) + ": Toggle foot force display")
    print(colored("  Y Button", Colors.CYAN) + ": Toggle pelvis tracking")
    print(colored("  B Button", Colors.CYAN) + ": Reset robot state")
    print(colored("  A Button", Colors.CYAN) + ": Toggle foot contact display")
    print(colored("=" * 70, Colors.BRIGHT_CYAN))


def handle_mode_switch():
    """处理模式切换（LB按钮）"""
    global current_mode
    if joystick is None:
        return
    
    # 获取LB按钮ID（校准后或默认值）
    lb_button_ids = get_calibrated_button_id('LB', default_ids=[4, 6])
    if lb_button_ids is None:
        return
    
    # 支持单个ID或ID列表
    if isinstance(lb_button_ids, list):
        lb_pressed = False
        for button_id in lb_button_ids:
            if joystick.get_numbuttons() > button_id:
                if joystick.get_button(button_id):
                    lb_pressed = True
                    break
    else:
        button_id = lb_button_ids
        lb_pressed = joystick.get_button(button_id) if joystick.get_numbuttons() > button_id else False
    
    if lb_pressed and not button_states.get('lb', False):
        current_mode = (current_mode + 1) % 3  # 循环切换：0->1->2->0
        # 更新显示中的模式信息
        try:
            from .display_utils import update_mode, update_status
            update_mode(current_mode, mode_names[current_mode])
            if current_mode == MODE_DISTURBANCE:
                update_status(status_message=f"抗扰动模式: 扰动力施加在 {disturbance_body_name}")
            else:
                update_status(status_message=f"模式已切换: {mode_names[current_mode]}")
        except ImportError:
            pass  # 如果显示工具不可用，忽略
    
    # 更新按钮状态
    button_states['lb'] = lb_pressed


def handle_viewer_controls():
    """处理viewer相关的按钮控制"""
    if joystick is None:
        return
    
    # 如果跟踪pelvis，使用方向键（D-pad/hat）调节视角
    if viewer_utils.track_pelvis and joystick.get_numhats() > 0:
        hat = joystick.get_hat(0)  # 读取第一个 hat switch
        hat_x, hat_y = hat
        
        # 方向键左右：围绕机器人旋转视角（调整水平角度）
        if hat_x != 0:
            viewer_utils.camera_angle += hat_x * viewer_utils.camera_angle_speed
            # 将角度限制在 [0, 2π] 范围内
            viewer_utils.camera_angle = viewer_utils.camera_angle % (2 * np.pi)
        
        # 方向键上下：控制视角远近（调整距离）
        if hat_y != 0:
            viewer_utils.camera_distance += hat_y * viewer_utils.camera_distance_speed
            # 限制距离范围
            viewer_utils.camera_distance = np.clip(viewer_utils.camera_distance, 0.5, 10.0)
    
    # X按钮: 切换显示足底力
    x_button_id = get_calibrated_button_id('X', default_ids=[0])
    if x_button_id is not None and joystick.get_numbuttons() > x_button_id:
        button_x_pressed = joystick.get_button(x_button_id)
        if button_x_pressed and not button_states.get('x', False):
            viewer_utils.show_forces = not viewer_utils.show_forces
            try:
                from .display_utils import update_status
                update_status(show_forces=viewer_utils.show_forces, 
                            status_message=f"{'已启用' if viewer_utils.show_forces else '已禁用'}足底力显示")
            except ImportError:
                pass
        button_states['x'] = button_x_pressed
    
    # Y按钮: 切换是否跟踪pelvis
    y_button_id = get_calibrated_button_id('Y', default_ids=[3])
    if y_button_id is not None and joystick.get_numbuttons() > y_button_id:
        button_y_pressed = joystick.get_button(y_button_id)
        if button_y_pressed and not button_states.get('y', False):
            viewer_utils.track_pelvis = not viewer_utils.track_pelvis
            if viewer_utils.track_pelvis:
                # 重置为初始视角（正对机器人）
                viewer_utils.camera_angle = 0.0
                viewer_utils.camera_elevation = -0.15
                viewer_utils.camera_distance = 3.0
            try:
                from .display_utils import update_status
                update_status(track_pelvis=viewer_utils.track_pelvis,
                            status_message=f"{'已启用' if viewer_utils.track_pelvis else '已禁用'}pelvis跟踪")
            except ImportError:
                pass
        button_states['y'] = button_y_pressed
    
    # B按钮: 重置机器人状态
    b_button_id = get_calibrated_button_id('B', default_ids=[2])
    if b_button_id is not None and joystick.get_numbuttons() > b_button_id:
        button_b_pressed = joystick.get_button(b_button_id)
        if button_b_pressed and not button_states.get('b', False):
            viewer_utils.reset_requested = True
            try:
                from .display_utils import update_status
                update_status(reset_requested=True, status_message="请求重置机器人状态")
            except ImportError:
                pass
        button_states['b'] = button_b_pressed
    
    # A按钮: 切换显示足端接触状态
    a_button_id = get_calibrated_button_id('A', default_ids=[1])
    if a_button_id is not None and joystick.get_numbuttons() > a_button_id:
        button_a_pressed = joystick.get_button(a_button_id)
        if button_a_pressed and not button_states.get('a', False):
            viewer_utils.show_contacts = not viewer_utils.show_contacts
            try:
                from .display_utils import update_status
                update_status(show_contacts=viewer_utils.show_contacts,
                            status_message=f"{'已启用' if viewer_utils.show_contacts else '已禁用'}足端接触显示")
            except ImportError:
                pass
        button_states['a'] = button_a_pressed


def update_cmd_from_gamepad(cmd):
    """从游戏手柄读取输入并更新速度命令
    
    轴映射（根据手柄类型）:
    - 右摇杆 Y轴: 前后速度 (cmd[0]), 向上为负值，向下为正值
    - 右摇杆 X轴: 左右速度 (cmd[1]), 向左为负值，向右为正值
    - 左摇杆 X轴: 角速度 (cmd[2]), 向左为负值，向右为正值
    - 左摇杆 Y轴: 抗扰动模式下控制扰动力（向上为负，向下为正）
    """
    global current_mode
    
    if joystick is None:
        return cmd
    
    # 处理 pygame 事件（必须调用以更新游戏手柄状态）
    pygame.event.pump()
    
    # 处理模式切换
    handle_mode_switch()
    
    # 处理viewer控制
    handle_viewer_controls()
    
    # 根据模式获取速度限制
    cmd_max = get_cmd_max_for_mode(current_mode)
    
    # 读取摇杆输入（使用校准后的轴映射）
    # axis_mapping: [左摇杆X, 左摇杆Y, 右摇杆X, 右摇杆Y]
    raw_right_stick_y = -joystick.get_axis(axis_mapping[3])  # 右摇杆Y轴
    raw_right_stick_x = -joystick.get_axis(axis_mapping[2])  # 右摇杆X轴
    raw_left_stick_x = -joystick.get_axis(axis_mapping[0])   # 左摇杆X轴
    
    # 应用校准（使用实际的轴ID）
    right_stick_y = apply_axis_calibration(axis_mapping[3], raw_right_stick_y)
    right_stick_x = apply_axis_calibration(axis_mapping[2], raw_right_stick_x)
    left_stick_x = apply_axis_calibration(axis_mapping[0], raw_left_stick_x)
    
    # 应用默认方向（如果未校准，保持原有逻辑）
    if gamepad_calibration is None:
        # 未校准时的默认处理
        right_stick_y = -right_stick_y  # 取反，因为向上推时轴值为负
        right_stick_x = -right_stick_x
        left_stick_x = -left_stick_x
    # 如果已校准，方向已在 apply_axis_calibration 中处理
    
    # 应用死区
    if abs(right_stick_y) < deadzone:
        right_stick_y = 0.0
    if abs(right_stick_x) < deadzone:
        right_stick_x = 0.0
    if abs(left_stick_x) < deadzone:
        left_stick_x = 0.0
    
    # 根据模式更新速度命令
    # 所有模式都允许控制速度（包括抗扰动模式）
    # 对于x方向，需要区分前进和后退
    global prev_cmd_x
    if right_stick_y >= 0:
        # 前进：使用前进最大速度
        raw_cmd_x = right_stick_y * cmd_max[0]
    else:
        # 后退：使用后退最大速度
        raw_cmd_x = right_stick_y * cmd_max[1]
    
    # 在奔跑模式下对 x 方向指令应用滤波（仅对增大时滤波，减小时不滤波）
    if current_mode == MODE_RUN:
        if raw_cmd_x > prev_cmd_x:
            # x 方向增大时：应用滤波，使加速更平滑
            cmd[0] = run_mode_filter_alpha * raw_cmd_x + (1.0 - run_mode_filter_alpha) * prev_cmd_x
        else:
            # x 方向减小或不变时：直接使用新值，保持快速响应
            cmd[0] = raw_cmd_x
        prev_cmd_x = cmd[0]  # 更新上一帧值
    else:
        # 其他模式直接使用原始值
        cmd[0] = raw_cmd_x
        prev_cmd_x = raw_cmd_x  # 更新上一帧值（用于模式切换时的平滑过渡）
    
    cmd[1] = right_stick_x * cmd_max[2]  # y速度
    
    # 角速度控制：抗扰动模式下不使用角速度
    if current_mode == MODE_DISTURBANCE:
        cmd[2] = 0.0  # 抗扰动模式下不控制角速度
    else:
        cmd[2] = left_stick_x * cmd_max[3]  # 其他模式下使用左摇杆X轴控制角速度
    
    return cmd


def get_disturbance_force_base():
    """获取抗扰动模式下的扰动力（基于左摇杆输入），返回base坐标系下的力"""
    global current_mode
    
    if joystick is None or current_mode != MODE_DISTURBANCE:
        return np.zeros(3)
    
    # 在抗扰动模式下：
    # - 左摇杆X轴：控制扰动力左右方向
    # - 左摇杆Y轴：控制扰动力前后方向
    # - 右摇杆：控制速度命令（x, y方向）
    # - 不使用角速度
    # 使用校准后的轴映射
    raw_left_stick_x = joystick.get_axis(axis_mapping[0])  # 左摇杆X轴：左右方向的扰动力
    raw_left_stick_y = joystick.get_axis(axis_mapping[1])  # 左摇杆Y轴：前后方向的扰动力
    
    # 应用校准（使用实际的轴ID）
    left_stick_x = apply_axis_calibration(axis_mapping[0], raw_left_stick_x)
    left_stick_y = apply_axis_calibration(axis_mapping[1], raw_left_stick_y)
    
    # 应用默认方向（如果未校准，保持原有逻辑）
    # if gamepad_calibration is None:
        # 未校准时的默认处理
    left_stick_x = -left_stick_x
    left_stick_y = -left_stick_y
    # 如果已校准，方向已在 apply_axis_calibration 中处理
    
    # 应用死区
    if abs(left_stick_x) < deadzone:
        left_stick_x = 0.0
    if abs(left_stick_y) < deadzone:
        left_stick_y = 0.0
    
    # 计算扰动力大小（摇杆幅度）
    force_magnitude = np.sqrt(left_stick_x**2 + left_stick_y**2)
    force_magnitude = np.clip(force_magnitude, 0.0, 1.0)  # 限制在[0, 1]
    
    # 计算扰动力方向（摇杆方向）
    if force_magnitude > 0:
        # 归一化方向向量
        direction_x = left_stick_x / force_magnitude if force_magnitude > 0 else 0.0
        direction_y = left_stick_y / force_magnitude if force_magnitude > 0 else 0.0
    else:
        direction_x = 0.0
        direction_y = 0.0
    
    # 构建扰动力向量（在base坐标系下，水平面内，x和y方向）
    # 注意：base坐标系中，x通常是前进方向，y是左右方向
    force_base = np.array([
        direction_y * force_magnitude * disturbance_force_scale,  # 前后方向（左摇杆Y轴）
        direction_x * force_magnitude * disturbance_force_scale,  # 左右方向（左摇杆X轴）
        0.0  # z方向不施加力（只施加水平力）
    ])
    
    return force_base


def get_current_mode():
    """获取当前模式"""
    return current_mode

