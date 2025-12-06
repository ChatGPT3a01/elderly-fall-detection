"""
骨架偵測模組 - 使用 MediaPipe Pose
提供即時人體骨架辨識功能
"""

import cv2
import mediapipe as mp
import numpy as np
from typing import Optional, Tuple, Dict, List


class PoseDetector:
    """
    人體姿勢偵測器
    使用 MediaPipe Pose 進行骨架辨識
    """

    # MediaPipe Pose 關鍵點索引
    LANDMARKS = {
        'nose': 0,
        'left_eye_inner': 1,
        'left_eye': 2,
        'left_eye_outer': 3,
        'right_eye_inner': 4,
        'right_eye': 5,
        'right_eye_outer': 6,
        'left_ear': 7,
        'right_ear': 8,
        'mouth_left': 9,
        'mouth_right': 10,
        'left_shoulder': 11,
        'right_shoulder': 12,
        'left_elbow': 13,
        'right_elbow': 14,
        'left_wrist': 15,
        'right_wrist': 16,
        'left_pinky': 17,
        'right_pinky': 18,
        'left_index': 19,
        'right_index': 20,
        'left_thumb': 21,
        'right_thumb': 22,
        'left_hip': 23,
        'right_hip': 24,
        'left_knee': 25,
        'right_knee': 26,
        'left_ankle': 27,
        'right_ankle': 28,
        'left_heel': 29,
        'right_heel': 30,
        'left_foot_index': 31,
        'right_foot_index': 32
    }

    # 骨架連線定義（用於繪製骨架線段）
    SKELETON_CONNECTIONS = [
        # 頭部
        ('nose', 'left_eye'),
        ('nose', 'right_eye'),
        ('left_eye', 'left_ear'),
        ('right_eye', 'right_ear'),
        # 軀幹
        ('left_shoulder', 'right_shoulder'),
        ('left_shoulder', 'left_hip'),
        ('right_shoulder', 'right_hip'),
        ('left_hip', 'right_hip'),
        # 左手臂
        ('left_shoulder', 'left_elbow'),
        ('left_elbow', 'left_wrist'),
        # 右手臂
        ('right_shoulder', 'right_elbow'),
        ('right_elbow', 'right_wrist'),
        # 左腿
        ('left_hip', 'left_knee'),
        ('left_knee', 'left_ankle'),
        # 右腿
        ('right_hip', 'right_knee'),
        ('right_knee', 'right_ankle'),
    ]

    def __init__(self,
                 static_image_mode: bool = False,
                 model_complexity: int = 1,
                 min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5):
        """
        初始化姿勢偵測器

        Args:
            static_image_mode: 是否為靜態圖片模式
            model_complexity: 模型複雜度 (0, 1, 2)
            min_detection_confidence: 最小偵測信心度
            min_tracking_confidence: 最小追蹤信心度
        """
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        self.pose = self.mp_pose.Pose(
            static_image_mode=static_image_mode,
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

        self.results = None
        self.landmarks = None

    def detect(self, frame: np.ndarray) -> bool:
        """
        偵測畫面中的人體姿勢

        Args:
            frame: BGR 格式的影像

        Returns:
            是否偵測到人體
        """
        # 轉換為 RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 進行姿勢偵測
        self.results = self.pose.process(rgb_frame)

        if self.results.pose_landmarks:
            self.landmarks = self.results.pose_landmarks.landmark
            return True

        self.landmarks = None
        return False

    def get_landmark_position(self,
                              landmark_name: str,
                              frame_width: int,
                              frame_height: int) -> Optional[Tuple[int, int]]:
        """
        取得指定關鍵點的像素座標

        Args:
            landmark_name: 關鍵點名稱
            frame_width: 畫面寬度
            frame_height: 畫面高度

        Returns:
            (x, y) 像素座標，若無法取得則返回 None
        """
        if self.landmarks is None:
            return None

        if landmark_name not in self.LANDMARKS:
            return None

        idx = self.LANDMARKS[landmark_name]
        landmark = self.landmarks[idx]

        x = int(landmark.x * frame_width)
        y = int(landmark.y * frame_height)

        return (x, y)

    def get_all_landmarks(self,
                          frame_width: int,
                          frame_height: int) -> Dict[str, Tuple[int, int]]:
        """
        取得所有關鍵點的像素座標

        Args:
            frame_width: 畫面寬度
            frame_height: 畫面高度

        Returns:
            關鍵點名稱與座標的字典
        """
        landmarks_dict = {}

        if self.landmarks is None:
            return landmarks_dict

        for name, idx in self.LANDMARKS.items():
            landmark = self.landmarks[idx]
            x = int(landmark.x * frame_width)
            y = int(landmark.y * frame_height)
            landmarks_dict[name] = (x, y)

        return landmarks_dict

    def get_landmark_visibility(self, landmark_name: str) -> float:
        """
        取得指定關鍵點的可見度

        Args:
            landmark_name: 關鍵點名稱

        Returns:
            可見度 (0.0 ~ 1.0)
        """
        if self.landmarks is None:
            return 0.0

        if landmark_name not in self.LANDMARKS:
            return 0.0

        idx = self.LANDMARKS[landmark_name]
        return self.landmarks[idx].visibility

    def draw_skeleton(self,
                      frame: np.ndarray,
                      draw_points: bool = True,
                      draw_lines: bool = True,
                      point_color: Tuple[int, int, int] = (0, 255, 0),
                      line_color: Tuple[int, int, int] = (255, 255, 0),
                      point_radius: int = 5,
                      line_thickness: int = 2) -> np.ndarray:
        """
        在畫面上繪製骨架

        Args:
            frame: 原始影像
            draw_points: 是否繪製關鍵點
            draw_lines: 是否繪製骨架線段
            point_color: 關鍵點顏色 (BGR)
            line_color: 線段顏色 (BGR)
            point_radius: 關鍵點半徑
            line_thickness: 線段粗細

        Returns:
            繪製後的影像
        """
        output = frame.copy()

        if self.landmarks is None:
            return output

        h, w = frame.shape[:2]
        landmarks_pos = self.get_all_landmarks(w, h)

        # 繪製骨架線段
        if draw_lines:
            for start_name, end_name in self.SKELETON_CONNECTIONS:
                if start_name in landmarks_pos and end_name in landmarks_pos:
                    start_pos = landmarks_pos[start_name]
                    end_pos = landmarks_pos[end_name]

                    # 檢查可見度
                    start_vis = self.get_landmark_visibility(start_name)
                    end_vis = self.get_landmark_visibility(end_name)

                    if start_vis > 0.5 and end_vis > 0.5:
                        cv2.line(output, start_pos, end_pos, line_color, line_thickness)

        # 繪製關鍵點
        if draw_points:
            for name, pos in landmarks_pos.items():
                visibility = self.get_landmark_visibility(name)
                if visibility > 0.5:
                    cv2.circle(output, pos, point_radius, point_color, -1)

        return output

    def get_body_center(self, frame_width: int, frame_height: int) -> Optional[Tuple[int, int]]:
        """
        計算身體中心點（使用肩膀和髖部的重心）

        Args:
            frame_width: 畫面寬度
            frame_height: 畫面高度

        Returns:
            身體中心點座標
        """
        key_points = ['left_shoulder', 'right_shoulder', 'left_hip', 'right_hip']
        positions = []

        for point in key_points:
            pos = self.get_landmark_position(point, frame_width, frame_height)
            if pos and self.get_landmark_visibility(point) > 0.5:
                positions.append(pos)

        if len(positions) < 3:
            return None

        center_x = int(np.mean([p[0] for p in positions]))
        center_y = int(np.mean([p[1] for p in positions]))

        return (center_x, center_y)

    def get_head_position(self, frame_width: int, frame_height: int) -> Optional[Tuple[int, int]]:
        """
        取得頭部位置（使用鼻子作為參考）

        Args:
            frame_width: 畫面寬度
            frame_height: 畫面高度

        Returns:
            頭部位置座標
        """
        nose_pos = self.get_landmark_position('nose', frame_width, frame_height)
        if nose_pos and self.get_landmark_visibility('nose') > 0.5:
            return nose_pos
        return None

    def release(self):
        """釋放資源"""
        self.pose.close()


def main():
    """測試骨架偵測功能"""
    cap = cv2.VideoCapture(0)
    detector = PoseDetector()

    print("按 'q' 鍵退出")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 偵測姿勢
        detected = detector.detect(frame)

        # 繪製骨架
        if detected:
            frame = detector.draw_skeleton(frame)

            # 顯示頭部和身體中心
            h, w = frame.shape[:2]
            head_pos = detector.get_head_position(w, h)
            center_pos = detector.get_body_center(w, h)

            if head_pos:
                cv2.circle(frame, head_pos, 10, (0, 0, 255), -1)
                cv2.putText(frame, "Head", (head_pos[0] + 10, head_pos[1]),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            if center_pos:
                cv2.circle(frame, center_pos, 10, (255, 0, 0), -1)
                cv2.putText(frame, "Center", (center_pos[0] + 10, center_pos[1]),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        cv2.imshow('Pose Detection', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    detector.release()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
