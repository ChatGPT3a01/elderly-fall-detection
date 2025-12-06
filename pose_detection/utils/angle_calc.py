"""
角度計算模組 - 傾斜度運算邏輯
提供身體傾斜角度計算、向量運算等功能
"""

import numpy as np
from typing import Tuple, Optional, Dict
import math


def calculate_angle_from_vertical(point1: Tuple[int, int], point2: Tuple[int, int]) -> float:
    """
    計算兩點形成的線段相對於垂直線（地面法線）的角度

    角度計算公式：
    - 將兩點形成向量 V = (x2-x1, y2-y1)
    - 垂直向量（向下）為 (0, 1)
    - 使用 arctan2 計算角度

    Args:
        point1: 上方點 (x, y) - 例如肩膀
        point2: 下方點 (x, y) - 例如髖部

    Returns:
        相對於垂直線的角度（度數），0° 表示完全垂直，90° 表示水平
    """
    dx = point2[0] - point1[0]
    dy = point2[1] - point1[1]

    # 計算向量與垂直向下方向的夾角
    # 垂直向下為 (0, 1)，但因為螢幕座標 y 軸向下為正
    # 所以我們計算的是向量與 y 軸正方向的夾角

    angle_rad = math.atan2(abs(dx), abs(dy))
    angle_deg = math.degrees(angle_rad)

    return angle_deg


def calculate_torso_angle(landmarks: Dict[str, Tuple[int, int]]) -> Optional[float]:
    """
    計算軀幹傾斜角度（使用肩膀中點到髖部中點的線段）

    軀幹線段定義：
    - 上端點：左右肩膀的中點
    - 下端點：左右髖部的中點

    Args:
        landmarks: 關鍵點座標字典

    Returns:
        軀幹傾斜角度（度數），若無法計算則返回 None
    """
    required_points = ['left_shoulder', 'right_shoulder', 'left_hip', 'right_hip']

    for point in required_points:
        if point not in landmarks:
            return None

    # 計算肩膀中點
    shoulder_mid_x = (landmarks['left_shoulder'][0] + landmarks['right_shoulder'][0]) / 2
    shoulder_mid_y = (landmarks['left_shoulder'][1] + landmarks['right_shoulder'][1]) / 2

    # 計算髖部中點
    hip_mid_x = (landmarks['left_hip'][0] + landmarks['right_hip'][0]) / 2
    hip_mid_y = (landmarks['left_hip'][1] + landmarks['right_hip'][1]) / 2

    shoulder_mid = (int(shoulder_mid_x), int(shoulder_mid_y))
    hip_mid = (int(hip_mid_x), int(hip_mid_y))

    return calculate_angle_from_vertical(shoulder_mid, hip_mid)


def calculate_shoulder_angle(landmarks: Dict[str, Tuple[int, int]]) -> Optional[float]:
    """
    計算肩膀線的傾斜角度（相對於水平線）

    Args:
        landmarks: 關鍵點座標字典

    Returns:
        肩膀傾斜角度（度數）
    """
    if 'left_shoulder' not in landmarks or 'right_shoulder' not in landmarks:
        return None

    left = landmarks['left_shoulder']
    right = landmarks['right_shoulder']

    dx = right[0] - left[0]
    dy = right[1] - left[1]

    # 計算與水平線的夾角
    angle_rad = math.atan2(abs(dy), abs(dx))
    angle_deg = math.degrees(angle_rad)

    return angle_deg


def calculate_hip_angle(landmarks: Dict[str, Tuple[int, int]]) -> Optional[float]:
    """
    計算髖部線的傾斜角度（相對於水平線）

    Args:
        landmarks: 關鍵點座標字典

    Returns:
        髖部傾斜角度（度數）
    """
    if 'left_hip' not in landmarks or 'right_hip' not in landmarks:
        return None

    left = landmarks['left_hip']
    right = landmarks['right_hip']

    dx = right[0] - left[0]
    dy = right[1] - left[1]

    angle_rad = math.atan2(abs(dy), abs(dx))
    angle_deg = math.degrees(angle_rad)

    return angle_deg


def calculate_leg_angles(landmarks: Dict[str, Tuple[int, int]]) -> Dict[str, Optional[float]]:
    """
    計算左右腿的傾斜角度

    Args:
        landmarks: 關鍵點座標字典

    Returns:
        包含左右腿角度的字典
    """
    result = {'left_leg': None, 'right_leg': None}

    # 左腿：髖部到腳踝
    if 'left_hip' in landmarks and 'left_ankle' in landmarks:
        result['left_leg'] = calculate_angle_from_vertical(
            landmarks['left_hip'],
            landmarks['left_ankle']
        )

    # 右腿：髖部到腳踝
    if 'right_hip' in landmarks and 'right_ankle' in landmarks:
        result['right_leg'] = calculate_angle_from_vertical(
            landmarks['right_hip'],
            landmarks['right_ankle']
        )

    return result


def calculate_body_center(landmarks: Dict[str, Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    """
    使用三角形重心法計算身體中心點

    使用肩膀中點、左髖、右髖形成三角形，計算重心

    Args:
        landmarks: 關鍵點座標字典

    Returns:
        身體中心點座標
    """
    required = ['left_shoulder', 'right_shoulder', 'left_hip', 'right_hip']
    for point in required:
        if point not in landmarks:
            return None

    # 肩膀中點
    shoulder_mid_x = (landmarks['left_shoulder'][0] + landmarks['right_shoulder'][0]) / 2
    shoulder_mid_y = (landmarks['left_shoulder'][1] + landmarks['right_shoulder'][1]) / 2

    # 三角形三個頂點
    p1 = (shoulder_mid_x, shoulder_mid_y)
    p2 = landmarks['left_hip']
    p3 = landmarks['right_hip']

    # 重心 = 三個頂點座標的平均
    center_x = (p1[0] + p2[0] + p3[0]) / 3
    center_y = (p1[1] + p2[1] + p3[1]) / 3

    return (int(center_x), int(center_y))


def calculate_head_height_ratio(landmarks: Dict[str, Tuple[int, int]],
                                 frame_height: int) -> Optional[float]:
    """
    計算頭部高度相對於畫面高度的比例

    用於偵測頭部突然下降的情況

    Args:
        landmarks: 關鍵點座標字典
        frame_height: 畫面高度

    Returns:
        頭部高度比例 (0.0 ~ 1.0)，越接近 1 表示越低
    """
    if 'nose' not in landmarks:
        return None

    nose_y = landmarks['nose'][1]

    # 返回正規化的高度比例（0 = 頂部，1 = 底部）
    return nose_y / frame_height


def calculate_center_shift(current_center: Tuple[int, int],
                           previous_center: Tuple[int, int]) -> float:
    """
    計算身體中心點的位移距離

    Args:
        current_center: 當前中心點
        previous_center: 前一幀中心點

    Returns:
        位移距離（像素）
    """
    dx = current_center[0] - previous_center[0]
    dy = current_center[1] - previous_center[1]

    return math.sqrt(dx * dx + dy * dy)


def get_all_body_angles(landmarks: Dict[str, Tuple[int, int]]) -> Dict[str, Optional[float]]:
    """
    取得所有身體角度資訊

    Args:
        landmarks: 關鍵點座標字典

    Returns:
        包含所有角度資訊的字典
    """
    leg_angles = calculate_leg_angles(landmarks)

    return {
        'torso': calculate_torso_angle(landmarks),
        'shoulder': calculate_shoulder_angle(landmarks),
        'hip': calculate_hip_angle(landmarks),
        'left_leg': leg_angles['left_leg'],
        'right_leg': leg_angles['right_leg']
    }


class AngleTracker:
    """
    角度追蹤器 - 追蹤角度變化歷史
    """

    def __init__(self, history_size: int = 10):
        """
        初始化角度追蹤器

        Args:
            history_size: 歷史記錄大小
        """
        self.history_size = history_size
        self.torso_history = []
        self.center_history = []
        self.head_height_history = []

    def update(self,
               torso_angle: Optional[float],
               center: Optional[Tuple[int, int]],
               head_height: Optional[float]):
        """
        更新追蹤資料

        Args:
            torso_angle: 軀幹角度
            center: 身體中心點
            head_height: 頭部高度比例
        """
        if torso_angle is not None:
            self.torso_history.append(torso_angle)
            if len(self.torso_history) > self.history_size:
                self.torso_history.pop(0)

        if center is not None:
            self.center_history.append(center)
            if len(self.center_history) > self.history_size:
                self.center_history.pop(0)

        if head_height is not None:
            self.head_height_history.append(head_height)
            if len(self.head_height_history) > self.history_size:
                self.head_height_history.pop(0)

    def get_average_torso_angle(self) -> Optional[float]:
        """取得平均軀幹角度"""
        if not self.torso_history:
            return None
        return sum(self.torso_history) / len(self.torso_history)

    def get_torso_angle_change_rate(self) -> Optional[float]:
        """取得軀幹角度變化率"""
        if len(self.torso_history) < 2:
            return None
        return self.torso_history[-1] - self.torso_history[-2]

    def get_center_shift(self) -> Optional[float]:
        """取得最近的中心點位移"""
        if len(self.center_history) < 2:
            return None
        return calculate_center_shift(
            self.center_history[-1],
            self.center_history[-2]
        )

    def get_head_height_change(self) -> Optional[float]:
        """取得頭部高度變化"""
        if len(self.head_height_history) < 2:
            return None
        return self.head_height_history[-1] - self.head_height_history[-2]

    def get_max_center_shift(self, frames: int = 5) -> Optional[float]:
        """
        取得最近 N 幀的最大中心點位移

        Args:
            frames: 要檢查的幀數

        Returns:
            最大位移距離
        """
        if len(self.center_history) < 2:
            return None

        check_frames = min(frames, len(self.center_history) - 1)
        shifts = []

        for i in range(-check_frames, 0):
            shift = calculate_center_shift(
                self.center_history[i],
                self.center_history[i - 1]
            )
            shifts.append(shift)

        return max(shifts) if shifts else None

    def reset(self):
        """重置追蹤器"""
        self.torso_history.clear()
        self.center_history.clear()
        self.head_height_history.clear()
