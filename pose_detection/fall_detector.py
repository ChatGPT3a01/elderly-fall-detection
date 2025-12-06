"""
跌倒偵測模組 - 異常狀態判斷（含防誤判機制）
整合骨架偵測與角度計算，進行跌倒風險評估
"""

import time
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
from enum import Enum

from .detector import PoseDetector
from .utils import (
    calculate_torso_angle,
    calculate_body_center,
    calculate_head_height_ratio,
    AngleTracker
)


class AlertSeverity(Enum):
    """警示嚴重程度"""
    NONE = 0
    MILD = 1      # 輕微：傾斜角度 35-50 度
    SEVERE = 2    # 嚴重：傾斜角度 > 50 度


@dataclass
class DetectionResult:
    """偵測結果資料結構"""
    is_fall_detected: bool
    severity: AlertSeverity
    torso_angle: Optional[float]
    head_height: Optional[float]
    center_shift: Optional[float]
    trigger_reasons: List[str]
    timestamp: float
    confidence: float


class FallDetector:
    """
    跌倒偵測器 - 整合多項指標進行跌倒判斷

    判斷邏輯（任一條件成立視為可能跌倒）：
    1. 軀幹線段角度 > 閾值
    2. 頭部高度突然下降
    3. 身體中心點大幅偏移

    防誤判機制：
    - 連續多幀確認
    - 冷卻時間（避免重複觸發）
    - 多指標交叉驗證
    """

    def __init__(self,
                 torso_angle_threshold: float = 35.0,
                 head_drop_threshold: float = 0.15,
                 center_shift_threshold: float = 150.0,
                 consecutive_frames: int = 5,
                 cooldown_seconds: float = 30.0,
                 mild_angle_range: Tuple[float, float] = (35.0, 50.0),
                 severe_angle_min: float = 50.0):
        """
        初始化跌倒偵測器

        Args:
            torso_angle_threshold: 軀幹傾斜角度閾值（度數）
            head_drop_threshold: 頭部下降閾值（正規化高度變化）
            center_shift_threshold: 身體中心位移閾值（像素）
            consecutive_frames: 連續幀數確認閾值
            cooldown_seconds: 冷卻時間（秒）
            mild_angle_range: 輕微警示角度範圍
            severe_angle_min: 嚴重警示最小角度
        """
        self.torso_angle_threshold = torso_angle_threshold
        self.head_drop_threshold = head_drop_threshold
        self.center_shift_threshold = center_shift_threshold
        self.consecutive_frames = consecutive_frames
        self.cooldown_seconds = cooldown_seconds
        self.mild_angle_range = mild_angle_range
        self.severe_angle_min = severe_angle_min

        # 追蹤器
        self.angle_tracker = AngleTracker(history_size=30)

        # 連續偵測計數
        self.consecutive_detections = 0

        # 最後警報時間
        self.last_alert_time = 0

        # 基準線（正常站立時的數值）
        self.baseline_head_height: Optional[float] = None
        self.baseline_center: Optional[Tuple[int, int]] = None
        self.is_calibrated = False

    def calibrate(self, head_height: float, center: Tuple[int, int]):
        """
        校準基準線（使用者正常站立時呼叫）

        Args:
            head_height: 正常站立時的頭部高度比例
            center: 正常站立時的身體中心點
        """
        self.baseline_head_height = head_height
        self.baseline_center = center
        self.is_calibrated = True

    def reset_calibration(self):
        """重置校準"""
        self.baseline_head_height = None
        self.baseline_center = None
        self.is_calibrated = False
        self.angle_tracker.reset()

    def _check_torso_angle(self, angle: float) -> Tuple[bool, AlertSeverity]:
        """
        檢查軀幹傾斜角度

        Args:
            angle: 軀幹傾斜角度

        Returns:
            (是否異常, 嚴重程度)
        """
        if angle >= self.severe_angle_min:
            return True, AlertSeverity.SEVERE
        elif angle >= self.mild_angle_range[0]:
            return True, AlertSeverity.MILD
        return False, AlertSeverity.NONE

    def _check_head_drop(self, current_height: float) -> bool:
        """
        檢查頭部是否突然下降

        Args:
            current_height: 當前頭部高度比例

        Returns:
            是否偵測到頭部下降
        """
        # 使用歷史變化檢測
        height_change = self.angle_tracker.get_head_height_change()
        if height_change is not None and height_change > self.head_drop_threshold:
            return True

        # 與基準線比較
        if self.baseline_head_height is not None:
            diff = current_height - self.baseline_head_height
            if diff > self.head_drop_threshold * 2:  # 與基準線差異更大才觸發
                return True

        return False

    def _check_center_shift(self) -> bool:
        """
        檢查身體中心是否大幅偏移

        Returns:
            是否偵測到大幅偏移
        """
        max_shift = self.angle_tracker.get_max_center_shift(frames=5)
        if max_shift is not None and max_shift > self.center_shift_threshold:
            return True
        return False

    def _is_in_cooldown(self) -> bool:
        """檢查是否在冷卻時間內"""
        return (time.time() - self.last_alert_time) < self.cooldown_seconds

    def _calculate_confidence(self, trigger_count: int, severity: AlertSeverity) -> float:
        """
        計算偵測信心度

        Args:
            trigger_count: 觸發條件數量
            severity: 嚴重程度

        Returns:
            信心度 (0.0 ~ 1.0)
        """
        base_confidence = trigger_count / 3.0  # 最多 3 個條件

        # 根據嚴重程度調整
        if severity == AlertSeverity.SEVERE:
            base_confidence *= 1.2
        elif severity == AlertSeverity.MILD:
            base_confidence *= 1.0

        # 根據連續幀數調整
        frame_ratio = min(self.consecutive_detections / self.consecutive_frames, 1.0)
        base_confidence *= (0.5 + 0.5 * frame_ratio)

        return min(base_confidence, 1.0)

    def detect(self,
               landmarks: Dict[str, Tuple[int, int]],
               frame_height: int) -> DetectionResult:
        """
        進行跌倒偵測

        Args:
            landmarks: 關鍵點座標字典
            frame_height: 畫面高度

        Returns:
            DetectionResult 偵測結果
        """
        trigger_reasons = []
        max_severity = AlertSeverity.NONE

        # 計算各項指標
        torso_angle = calculate_torso_angle(landmarks)
        body_center = calculate_body_center(landmarks)
        head_height = calculate_head_height_ratio(landmarks, frame_height)

        # 更新追蹤器
        self.angle_tracker.update(torso_angle, body_center, head_height)

        # 條件 1：檢查軀幹傾斜角度
        if torso_angle is not None:
            is_abnormal, severity = self._check_torso_angle(torso_angle)
            if is_abnormal:
                trigger_reasons.append(f"軀幹傾斜角度異常: {torso_angle:.1f}°")
                if severity.value > max_severity.value:
                    max_severity = severity

        # 條件 2：檢查頭部下降
        if head_height is not None:
            if self._check_head_drop(head_height):
                trigger_reasons.append("頭部高度突然下降")
                if max_severity == AlertSeverity.NONE:
                    max_severity = AlertSeverity.MILD

        # 條件 3：檢查身體中心偏移
        if self._check_center_shift():
            trigger_reasons.append("身體中心大幅偏移")
            if max_severity == AlertSeverity.NONE:
                max_severity = AlertSeverity.MILD

        # 判斷是否觸發警報
        has_trigger = len(trigger_reasons) > 0

        if has_trigger:
            self.consecutive_detections += 1
        else:
            self.consecutive_detections = max(0, self.consecutive_detections - 1)

        # 多條件交叉驗證（至少 2 個條件或連續多幀）
        should_alert = False
        if len(trigger_reasons) >= 2:
            should_alert = True
        elif self.consecutive_detections >= self.consecutive_frames:
            should_alert = True

        # 檢查冷卻時間
        if should_alert and self._is_in_cooldown():
            should_alert = False

        # 如果觸發警報，更新最後警報時間
        if should_alert:
            self.last_alert_time = time.time()

        # 計算信心度
        confidence = self._calculate_confidence(len(trigger_reasons), max_severity)

        return DetectionResult(
            is_fall_detected=should_alert,
            severity=max_severity,
            torso_angle=torso_angle,
            head_height=head_height,
            center_shift=self.angle_tracker.get_center_shift(),
            trigger_reasons=trigger_reasons,
            timestamp=time.time(),
            confidence=confidence
        )

    def get_status_text(self, result: DetectionResult) -> str:
        """
        取得狀態文字描述

        Args:
            result: 偵測結果

        Returns:
            狀態描述文字
        """
        lines = []

        if result.torso_angle is not None:
            lines.append(f"軀幹角度: {result.torso_angle:.1f}°")

        if result.head_height is not None:
            lines.append(f"頭部高度: {result.head_height:.2f}")

        if result.center_shift is not None:
            lines.append(f"中心位移: {result.center_shift:.1f}px")

        lines.append(f"連續偵測: {self.consecutive_detections}/{self.consecutive_frames}")

        if result.is_fall_detected:
            severity_text = "嚴重" if result.severity == AlertSeverity.SEVERE else "輕微"
            lines.append(f"⚠️ 警報: {severity_text} ({result.confidence:.0%})")

        return "\n".join(lines)

    def force_reset_cooldown(self):
        """強制重置冷卻時間"""
        self.last_alert_time = 0
        self.consecutive_detections = 0
