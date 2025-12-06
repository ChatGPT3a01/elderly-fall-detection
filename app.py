"""
樂齡防傾倒 LINE Bot 通知系統 - 主程式
整合攝影機偵測、骨架辨識、傾斜度計算與 LINE Bot 通知功能

設定方式：
1. 使用 .env 檔案（推薦）- 複製 .env.example 為 .env 並填入金鑰
2. 使用 config.json 檔案
"""

import os
import sys

# 修正 Windows 控制台編碼問題
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass

import json
import time
import cv2
import numpy as np
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 添加模組路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pose_detection.detector import PoseDetector
from pose_detection.fall_detector import FallDetector, AlertSeverity
from pose_detection.utils import (
    calculate_torso_angle,
    calculate_body_center,
    get_all_body_angles
)
from line_bot.bot import LineBotNotifier, create_notifier_from_config


class ElderlyFallDetectionSystem:
    """
    樂齡防傾倒偵測系統主類別

    功能：
    1. 攝影機即時影像擷取
    2. 骨架辨識與視覺化
    3. 傾斜角度即時計算
    4. 異常狀態偵測
    5. LINE Bot 警示通知
    """

    def __init__(self, config_path: str = None):
        """
        初始化系統

        Args:
            config_path: 設定檔路徑
        """
        # 載入設定
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')

        self.config = self._load_config(config_path)
        self.config_path = config_path

        # 初始化姿勢偵測器
        self.pose_detector = PoseDetector(
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # 初始化跌倒偵測器
        detection_config = self.config.get('detection', {})
        self.fall_detector = FallDetector(
            torso_angle_threshold=detection_config.get('torso_angle_threshold', 35),
            head_drop_threshold=detection_config.get('head_drop_threshold', 100) / 480,  # 正規化
            center_shift_threshold=detection_config.get('center_shift_threshold', 150),
            consecutive_frames=detection_config.get('consecutive_frames_threshold', 5),
            cooldown_seconds=detection_config.get('cooldown_seconds', 30)
        )

        # 初始化 LINE Bot 通知器
        self.notifier: Optional[LineBotNotifier] = None
        self._init_line_bot()

        # 攝影機設定
        cam_config = self.config.get('camera', {})
        self.camera_id = cam_config.get('device_id', 0)
        self.frame_width = cam_config.get('width', 640)
        self.frame_height = cam_config.get('height', 480)
        self.target_fps = cam_config.get('fps', 30)

        # 截圖目錄
        self.screenshot_dir = os.path.join(os.path.dirname(__file__), 'screenshots')
        os.makedirs(self.screenshot_dir, exist_ok=True)

        # 狀態變數
        self.is_running = False
        self.cap: Optional[cv2.VideoCapture] = None
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0

    def _load_config(self, config_path: str) -> dict:
        """載入設定檔"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"警告：找不到設定檔 {config_path}，使用預設設定")
            return {}
        except json.JSONDecodeError:
            print(f"警告：設定檔格式錯誤，使用預設設定")
            return {}

    def _init_line_bot(self):
        """初始化 LINE Bot（優先使用環境變數，其次使用 config.json）"""
        # 優先從環境變數讀取
        token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')
        secret = os.getenv('LINE_CHANNEL_SECRET', '')
        user_id = os.getenv('LINE_USER_ID', '')

        # 若環境變數未設定，則從 config.json 讀取
        if not token or token == 'your_channel_access_token_here':
            line_config = self.config.get('line_bot', {})
            token = line_config.get('channel_access_token', '')
            secret = line_config.get('channel_secret', '')
            user_id = line_config.get('user_id', '')

        if token and token != 'YOUR_CHANNEL_ACCESS_TOKEN':
            self.notifier = LineBotNotifier(token, secret, user_id)
            print("✅ LINE Bot 已初始化")
        else:
            print("⚠️ LINE Bot 未設定，將不會發送通知")
            print("   請在 .env 或 config.json 中設定 LINE Bot 資訊")

    def _update_fps(self):
        """更新 FPS 計算"""
        self.fps_counter += 1
        elapsed = time.time() - self.fps_start_time

        if elapsed >= 1.0:
            self.current_fps = self.fps_counter / elapsed
            self.fps_counter = 0
            self.fps_start_time = time.time()

    def _draw_info_panel(self, frame: np.ndarray, detection_result) -> np.ndarray:
        """
        繪製資訊面板

        Args:
            frame: 原始影像
            detection_result: 偵測結果

        Returns:
            繪製後的影像
        """
        h, w = frame.shape[:2]
        panel_width = 250
        panel_height = 200

        # 繪製半透明背景
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (10 + panel_width, 10 + panel_height),
                     (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # 文字設定
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        color = (255, 255, 255)
        y_offset = 35

        # 顯示 FPS
        cv2.putText(frame, f"FPS: {self.current_fps:.1f}", (20, y_offset),
                   font, font_scale, color, 1)
        y_offset += 25

        # 顯示軀幹角度
        if detection_result.torso_angle is not None:
            angle_color = (0, 255, 0)  # 綠色
            if detection_result.torso_angle > 50:
                angle_color = (0, 0, 255)  # 紅色
            elif detection_result.torso_angle > 35:
                angle_color = (0, 165, 255)  # 橘色

            cv2.putText(frame, f"Torso Angle: {detection_result.torso_angle:.1f} deg",
                       (20, y_offset), font, font_scale, angle_color, 1)
        else:
            cv2.putText(frame, "Torso Angle: N/A", (20, y_offset),
                       font, font_scale, (128, 128, 128), 1)
        y_offset += 25

        # 顯示頭部高度
        if detection_result.head_height is not None:
            cv2.putText(frame, f"Head Height: {detection_result.head_height:.2f}",
                       (20, y_offset), font, font_scale, color, 1)
        y_offset += 25

        # 顯示中心位移
        if detection_result.center_shift is not None:
            cv2.putText(frame, f"Center Shift: {detection_result.center_shift:.1f}px",
                       (20, y_offset), font, font_scale, color, 1)
        y_offset += 25

        # 顯示連續偵測狀態
        consecutive = self.fall_detector.consecutive_detections
        threshold = self.fall_detector.consecutive_frames
        cv2.putText(frame, f"Consecutive: {consecutive}/{threshold}",
                   (20, y_offset), font, font_scale, color, 1)
        y_offset += 30

        # 顯示警報狀態
        if detection_result.is_fall_detected:
            severity_text = "SEVERE" if detection_result.severity == AlertSeverity.SEVERE else "MILD"
            alert_color = (0, 0, 255) if detection_result.severity == AlertSeverity.SEVERE else (0, 165, 255)

            # 閃爍效果
            if int(time.time() * 2) % 2 == 0:
                cv2.putText(frame, f"ALERT: {severity_text}!", (20, y_offset),
                           font, 0.7, alert_color, 2)

                # 在畫面邊框加紅框
                cv2.rectangle(frame, (0, 0), (w - 1, h - 1), alert_color, 5)

        return frame

    def _save_screenshot(self, frame: np.ndarray) -> str:
        """
        儲存截圖

        Args:
            frame: 影像

        Returns:
            截圖檔案路徑
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fall_alert_{timestamp}.jpg"
        filepath = os.path.join(self.screenshot_dir, filename)
        cv2.imwrite(filepath, frame)
        return filepath

    def _send_alert(self, detection_result, frame: np.ndarray):
        """
        發送警報通知

        Args:
            detection_result: 偵測結果
            frame: 當前影像
        """
        if self.notifier is None:
            print("⚠️ LINE Bot 未設定，無法發送通知")
            return

        try:
            # 判斷嚴重程度
            severity = "severe" if detection_result.severity == AlertSeverity.SEVERE else "mild"

            # 儲存截圖
            screenshot_path = None
            if self.config.get('notification', {}).get('include_screenshot', True):
                screenshot_path = self._save_screenshot(frame)
                print(f"📸 已儲存截圖：{screenshot_path}")

            # 發送 Flex Message（美觀卡片）
            success = self.notifier.send_flex_message(
                severity=severity,
                angle=detection_result.torso_angle,
                timestamp=datetime.now()
            )

            if success:
                print("✅ 已發送 LINE 警報通知")
            else:
                # 備用：發送純文字訊息
                self.notifier.send_fall_alert(
                    severity=severity,
                    angle=detection_result.torso_angle,
                    timestamp=datetime.now(),
                    screenshot_path=screenshot_path
                )

            # 發送截圖到 LINE
            if screenshot_path and os.path.exists(screenshot_path):
                img_success = self.notifier.send_image_message(screenshot_path)
                if img_success:
                    print("✅ 已發送截圖到 LINE")
                else:
                    print("⚠️ 截圖發送失敗")

        except Exception as e:
            print(f"❌ 發送警報時發生錯誤：{e}")
            # 不讓錯誤中斷主程式

    def start(self):
        """啟動系統"""
        print("=" * 50)
        print("樂齡防傾倒 LINE Bot 通知系統")
        print("=" * 50)
        print()

        # 開啟攝影機
        self.cap = cv2.VideoCapture(self.camera_id)

        if not self.cap.isOpened():
            print(f"❌ 無法開啟攝影機 (ID: {self.camera_id})")
            return

        # 設定攝影機參數
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)
        self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"✅ 攝影機已開啟")
        print(f"   解析度：{actual_width} x {actual_height}")
        print()
        print("操作說明：")
        print("  - 按 'q' 或 ESC 鍵退出")
        print("  - 按 'c' 鍵校準（站立時按下）")
        print("  - 按 'r' 鍵重置警報冷卻")
        print("  - 按 's' 鍵手動截圖")
        print("=" * 50)
        print()

        self.is_running = True

        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                print("❌ 無法讀取攝影機畫面")
                break

            # 更新 FPS
            self._update_fps()

            h, w = frame.shape[:2]

            # 進行姿勢偵測
            detected = self.pose_detector.detect(frame)

            # 繪製骨架
            if detected:
                frame = self.pose_detector.draw_skeleton(frame)

                # 取得關鍵點座標
                landmarks = self.pose_detector.get_all_landmarks(w, h)

                # 進行跌倒偵測
                detection_result = self.fall_detector.detect(landmarks, h)

                # 如果偵測到跌倒，發送警報
                if detection_result.is_fall_detected:
                    print(f"⚠️ 偵測到可能跌倒！嚴重程度：{detection_result.severity.name}")
                    for reason in detection_result.trigger_reasons:
                        print(f"   - {reason}")
                    self._send_alert(detection_result, frame)
            else:
                # 未偵測到人體時的預設結果
                from pose_detection.fall_detector import DetectionResult
                detection_result = DetectionResult(
                    is_fall_detected=False,
                    severity=AlertSeverity.NONE,
                    torso_angle=None,
                    head_height=None,
                    center_shift=None,
                    trigger_reasons=[],
                    timestamp=time.time(),
                    confidence=0.0
                )

            # 繪製資訊面板
            frame = self._draw_info_panel(frame, detection_result)

            # 顯示畫面
            cv2.imshow('Elderly Fall Detection System', frame)

            # 處理按鍵
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q') or key == 27:  # q 或 ESC
                print("\n正在關閉系統...")
                self.is_running = False

            elif key == ord('c'):  # 校準
                if detected:
                    landmarks = self.pose_detector.get_all_landmarks(w, h)
                    from pose_detection.utils import calculate_body_center, calculate_head_height_ratio
                    center = calculate_body_center(landmarks)
                    head_height = calculate_head_height_ratio(landmarks, h)
                    if center and head_height:
                        self.fall_detector.calibrate(head_height, center)
                        print("✅ 校準完成")

            elif key == ord('r'):  # 重置冷卻
                self.fall_detector.force_reset_cooldown()
                print("✅ 警報冷卻已重置")

            elif key == ord('s'):  # 手動截圖
                filepath = self._save_screenshot(frame)
                print(f"📸 已儲存截圖：{filepath}")

        self.stop()

    def stop(self):
        """停止系統"""
        self.is_running = False

        if self.pose_detector:
            self.pose_detector.release()

        if self.cap:
            self.cap.release()

        cv2.destroyAllWindows()
        print("✅ 系統已關閉")


def main():
    """主程式進入點"""
    import argparse

    parser = argparse.ArgumentParser(description='樂齡防傾倒 LINE Bot 通知系統')
    parser.add_argument('--config', '-c', type=str,
                       help='設定檔路徑',
                       default=None)
    parser.add_argument('--camera', '-cam', type=int,
                       help='攝影機 ID',
                       default=None)

    args = parser.parse_args()

    # 建立系統實例
    system = ElderlyFallDetectionSystem(config_path=args.config)

    # 覆蓋攝影機 ID（如果有指定）
    if args.camera is not None:
        system.camera_id = args.camera

    # 啟動系統
    try:
        system.start()
    except KeyboardInterrupt:
        print("\n收到中斷訊號，正在關閉系統...")
        system.stop()


if __name__ == '__main__':
    main()
