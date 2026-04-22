from __future__ import annotations

from dataclasses import dataclass

import numpy as np


LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
OUTER_LIPS_INDICES = [61, 13, 291, 14]
INNER_LIPS_INDICES = [78, 13, 308, 14]
LEFT_BROW_INDICES = [70, 63, 105]
RIGHT_BROW_INDICES = [336, 296, 334]
LEFT_EYE_TOP = 159
RIGHT_EYE_TOP = 386
NOSE_TIP = 1
CHIN = 152
FOREHEAD = 10
LEFT_CHEEK = 234
RIGHT_CHEEK = 454
MOUTH_LEFT = 61
MOUTH_RIGHT = 291


@dataclass
class FaceMetrics:
    left_eye_open: float
    right_eye_open: float
    blink_level: float
    mouth_open: float
    mouth_wide: float
    smile_level: float
    brow_raise_left: float
    brow_raise_right: float
    brow_asymmetry: float
    nose_offset_x: float
    nose_offset_y: float
    face_width_ratio: float
    face_height_ratio: float
    face_area_ratio: float
    cheek_asymmetry: float


def compute_face_metrics(face_landmarks) -> FaceMetrics:
    left_eye_open = _eye_aspect_ratio(face_landmarks, LEFT_EYE_INDICES)
    right_eye_open = _eye_aspect_ratio(face_landmarks, RIGHT_EYE_INDICES)
    blink_level = 1.0 - np.clip((left_eye_open + right_eye_open) / 2.0 / 0.32, 0.0, 1.0)

    mouth_open = _mouth_open_ratio(face_landmarks, OUTER_LIPS_INDICES)
    mouth_wide = _mouth_width_ratio(face_landmarks)
    smile_level = _smile_ratio(face_landmarks)

    brow_raise_left = _brow_eye_distance(face_landmarks, LEFT_BROW_INDICES, LEFT_EYE_TOP)
    brow_raise_right = _brow_eye_distance(face_landmarks, RIGHT_BROW_INDICES, RIGHT_EYE_TOP)
    brow_asymmetry = brow_raise_left - brow_raise_right

    nose_x = face_landmarks.landmark[NOSE_TIP].x
    nose_y = face_landmarks.landmark[NOSE_TIP].y
    left_cheek = face_landmarks.landmark[LEFT_CHEEK]
    right_cheek = face_landmarks.landmark[RIGHT_CHEEK]
    forehead = face_landmarks.landmark[FOREHEAD]
    chin = face_landmarks.landmark[CHIN]

    face_width_ratio = abs(right_cheek.x - left_cheek.x)
    face_height_ratio = abs(chin.y - forehead.y)
    face_area_ratio = face_width_ratio * face_height_ratio

    face_center_x = (left_cheek.x + right_cheek.x) / 2.0
    face_center_y = (forehead.y + chin.y) / 2.0
    nose_offset_x = nose_x - face_center_x
    nose_offset_y = nose_y - face_center_y

    left_mouth = face_landmarks.landmark[MOUTH_LEFT]
    right_mouth = face_landmarks.landmark[MOUTH_RIGHT]
    cheek_asymmetry = (left_mouth.y - left_cheek.y) - (right_mouth.y - right_cheek.y)

    return FaceMetrics(
        left_eye_open=float(left_eye_open),
        right_eye_open=float(right_eye_open),
        blink_level=float(blink_level),
        mouth_open=float(mouth_open),
        mouth_wide=float(mouth_wide),
        smile_level=float(smile_level),
        brow_raise_left=float(brow_raise_left),
        brow_raise_right=float(brow_raise_right),
        brow_asymmetry=float(brow_asymmetry),
        nose_offset_x=float(nose_offset_x),
        nose_offset_y=float(nose_offset_y),
        face_width_ratio=float(face_width_ratio),
        face_height_ratio=float(face_height_ratio),
        face_area_ratio=float(face_area_ratio),
        cheek_asymmetry=float(cheek_asymmetry),
    )


def describe_expression(metrics: FaceMetrics) -> list[str]:
    states: list[str] = []

    if metrics.blink_level > 0.55:
        states.append("eyes: mostly closed")
    elif metrics.left_eye_open + metrics.right_eye_open > 0.64:
        states.append("eyes: open")
    else:
        states.append("eyes: mid")

    if metrics.mouth_open > 0.18:
        states.append("mouth: open")
    else:
        states.append("mouth: closed")

    if metrics.smile_level > 0.385:
        states.append("expression: smile-like")
    else:
        states.append("expression: neutral-like")

    if metrics.brow_asymmetry > 0.012:
        states.append("brows: left higher")
    elif metrics.brow_asymmetry < -0.012:
        states.append("brows: right higher")
    else:
        states.append("brows: balanced")

    return states


def _eye_aspect_ratio(face_landmarks, indices: list[int]) -> float:
    points = np.array(
        [(face_landmarks.landmark[index].x, face_landmarks.landmark[index].y) for index in indices],
        dtype=np.float64,
    )
    horizontal = np.linalg.norm(points[0] - points[3])
    if horizontal <= 1e-6:
        return 0.0
    vertical_1 = np.linalg.norm(points[1] - points[5])
    vertical_2 = np.linalg.norm(points[2] - points[4])
    return float((vertical_1 + vertical_2) / (2.0 * horizontal))


def _mouth_open_ratio(face_landmarks, indices: list[int]) -> float:
    left = face_landmarks.landmark[indices[0]]
    top = face_landmarks.landmark[indices[1]]
    right = face_landmarks.landmark[indices[2]]
    bottom = face_landmarks.landmark[indices[3]]
    width = np.linalg.norm(np.array([left.x - right.x, left.y - right.y]))
    height = np.linalg.norm(np.array([top.x - bottom.x, top.y - bottom.y]))
    if width <= 1e-6:
        return 0.0
    return float(height / width)


def _mouth_width_ratio(face_landmarks) -> float:
    left = face_landmarks.landmark[MOUTH_LEFT]
    right = face_landmarks.landmark[MOUTH_RIGHT]
    cheek_left = face_landmarks.landmark[LEFT_CHEEK]
    cheek_right = face_landmarks.landmark[RIGHT_CHEEK]
    mouth_width = np.linalg.norm(np.array([left.x - right.x, left.y - right.y]))
    face_width = np.linalg.norm(np.array([cheek_left.x - cheek_right.x, cheek_left.y - cheek_right.y]))
    if face_width <= 1e-6:
        return 0.0
    return float(mouth_width / face_width)


def _smile_ratio(face_landmarks) -> float:
    mouth_open = _mouth_open_ratio(face_landmarks, INNER_LIPS_INDICES)
    mouth_wide = _mouth_width_ratio(face_landmarks)
    return float(mouth_wide - (mouth_open * 0.35))


def _brow_eye_distance(face_landmarks, brow_indices: list[int], eye_top_index: int) -> float:
    brow_points = np.array(
        [(face_landmarks.landmark[index].x, face_landmarks.landmark[index].y) for index in brow_indices],
        dtype=np.float64,
    )
    brow_center = brow_points.mean(axis=0)
    eye_top = face_landmarks.landmark[eye_top_index]
    return float(np.linalg.norm(brow_center - np.array([eye_top.x, eye_top.y])))
