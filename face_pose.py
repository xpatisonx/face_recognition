from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

import cv2
import numpy as np


LANDMARK_IDS: Dict[str, int] = {
    "nose_tip": 1,
    "chin": 152,
    "left_eye_outer": 33,
    "right_eye_outer": 263,
    "mouth_left": 61,
    "mouth_right": 291,
}


MODEL_3D_POINTS = np.array(
    [
        (0.0, 0.0, 0.0),
        (0.0, -63.6, -12.5),
        (-43.3, 32.7, -26.0),
        (43.3, 32.7, -26.0),
        (-28.9, -28.9, -24.1),
        (28.9, -28.9, -24.1),
    ],
    dtype=np.float64,
)


@dataclass
class PoseEstimate:
    yaw: float
    pitch: float
    roll: float
    translation: np.ndarray
    rotation_vector: np.ndarray
    nose_end_point: Tuple[int, int]


def normalized_to_pixel_coordinates(x: float, y: float, width: int, height: int) -> Tuple[int, int]:
    return min(int(x * width), width - 1), min(int(y * height), height - 1)


def get_face_bbox(landmarks: Iterable, width: int, height: int) -> Tuple[int, int, int, int]:
    xs = [min(int(lm.x * width), width - 1) for lm in landmarks]
    ys = [min(int(lm.y * height), height - 1) for lm in landmarks]
    return min(xs), min(ys), max(xs), max(ys)


def estimate_head_pose(face_landmarks, frame_shape: Tuple[int, int, int]) -> PoseEstimate | None:
    height, width = frame_shape[:2]
    image_points = []

    for landmark_id in LANDMARK_IDS.values():
        lm = face_landmarks.landmark[landmark_id]
        image_points.append((lm.x * width, lm.y * height))

    image_points_np = np.array(image_points, dtype=np.float64)

    focal_length = width
    center = (width / 2, height / 2)
    camera_matrix = np.array(
        [
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1],
        ],
        dtype=np.float64,
    )
    dist_coeffs = np.zeros((4, 1), dtype=np.float64)

    success, rotation_vector, translation_vector = cv2.solvePnP(
        MODEL_3D_POINTS,
        image_points_np,
        camera_matrix,
        dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )
    if not success:
        return None

    rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
    angles, *_ = cv2.RQDecomp3x3(rotation_matrix)
    pitch, yaw, roll = [float(angle) for angle in angles]

    nose_end_point_2d, _ = cv2.projectPoints(
        np.array([(0.0, 0.0, 100.0)], dtype=np.float64),
        rotation_vector,
        translation_vector,
        camera_matrix,
        dist_coeffs,
    )
    nose_x, nose_y = image_points_np[0]
    nose_end = tuple(np.round(nose_end_point_2d[0][0]).astype(int))
    return PoseEstimate(
        yaw=yaw,
        pitch=pitch,
        roll=roll,
        translation=translation_vector,
        rotation_vector=rotation_vector,
        nose_end_point=(int(nose_end[0]), int(nose_end[1])),
    )


def describe_pose(yaw: float, pitch: float, roll: float) -> str:
    horizontal = "center"
    vertical = "center"
    tilt = "upright"

    if yaw < -12:
        horizontal = "left"
    elif yaw > 12:
        horizontal = "right"

    if pitch < -10:
        vertical = "down"
    elif pitch > 10:
        vertical = "up"

    if roll < -12:
        tilt = "toward right shoulder"
    elif roll > 12:
        tilt = "toward left shoulder"

    return f"head: {horizontal}, {vertical}, {tilt}"
