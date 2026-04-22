from __future__ import annotations

from pathlib import Path

import cv2
import mediapipe as mp

from calibration_store import CALIBRATION_FILE, delete_calibration, load_calibration, save_calibration
from cursor_controller import CursorController
from face_metrics import compute_face_metrics, describe_expression
from face_pose import LANDMARK_IDS, describe_pose, estimate_head_pose, get_face_bbox


WINDOW_NAME = "Face Pose Prototype"
OVERLAY_MODES = ["off", "light", "full"]

CALIBRATION_STEPS = [
    ("neutral", "Look straight and press space"),
    ("left", "Turn head LEFT and press space"),
    ("right", "Turn head RIGHT and press space"),
    ("up", "Look UP and press space"),
    ("down", "Look DOWN and press space"),
    ("tilt_left", "Tilt head toward LEFT shoulder and press space"),
    ("tilt_right", "Tilt head toward RIGHT shoulder and press space"),
]


def draw_text(frame, text: str, origin: tuple[int, int], color=(0, 255, 0)) -> None:
    cv2.putText(
        frame,
        text,
        origin,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        color,
        2,
        cv2.LINE_AA,
    )

def draw_axis_bar(
    frame,
    start: tuple[int, int],
    end: tuple[int, int],
    normalized_value: float,
    color: tuple[int, int, int],
    label: str,
) -> None:
    cv2.line(frame, start, end, (180, 180, 180), 3)
    center_x = int((start[0] + end[0]) / 2)
    center_y = int((start[1] + end[1]) / 2)
    cv2.circle(frame, (center_x, center_y), 4, (220, 220, 220), -1)

    indicator_x = int(center_x + ((end[0] - start[0]) / 2.0) * normalized_value)
    indicator_y = int(center_y + ((end[1] - start[1]) / 2.0) * normalized_value)
    cv2.circle(frame, (indicator_x, indicator_y), 8, color, -1)
    draw_text(frame, label, (start[0] - 10, start[1] - 10), color)


def main() -> None:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open the default camera.")

    mp_face_mesh = mp.solutions.face_mesh
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles
    cursor_controller = CursorController()
    saved_calibration = load_calibration()
    calibration_samples: dict[str, tuple[float, float, float]] = {}
    calibration_index = 0 if saved_calibration is None else len(CALIBRATION_STEPS)
    overlay_mode_index = 0

    if saved_calibration is not None:
        cursor_controller.calibrate(
            neutral_x=saved_calibration.neutral_x,
            neutral_y=saved_calibration.neutral_y,
            roll=saved_calibration.roll,
            left_x=saved_calibration.left_x,
            right_x=saved_calibration.right_x,
            up_y=saved_calibration.up_y,
            down_y=saved_calibration.down_y,
            tilt_left_roll=saved_calibration.tilt_left_roll,
            tilt_right_roll=saved_calibration.tilt_right_roll,
        )
        print(f"Loaded calibration from {CALIBRATION_FILE.resolve()}")

    with mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as face_mesh:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Failed to read frame from camera.")
                break

            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_frame)

            status_color = (0, 200, 255)
            draw_text(
                frame,
                "q quit | s snapshot | c cursor | d overlay mode | r recalibrate | space calibrate",
                (20, 30),
                status_color,
            )

            if results.multi_face_landmarks:
                face_landmarks = results.multi_face_landmarks[0]
                height, width = frame.shape[:2]
                x1, y1, x2, y2 = get_face_bbox(face_landmarks.landmark, width, height)

                overlay_mode = OVERLAY_MODES[overlay_mode_index]
                if overlay_mode == "full":
                    mp_drawing.draw_landmarks(
                        image=frame,
                        landmark_list=face_landmarks,
                        connections=mp_face_mesh.FACEMESH_TESSELATION,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_tesselation_style(),
                    )
                    mp_drawing.draw_landmarks(
                        image=frame,
                        landmark_list=face_landmarks,
                        connections=mp_face_mesh.FACEMESH_CONTOURS,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_contours_style(),
                    )
                    mp_drawing.draw_landmarks(
                        image=frame,
                        landmark_list=face_landmarks,
                        connections=mp_face_mesh.FACEMESH_IRISES,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_iris_connections_style(),
                    )
                elif overlay_mode == "light":
                    mp_drawing.draw_landmarks(
                        image=frame,
                        landmark_list=face_landmarks,
                        connections=mp_face_mesh.FACEMESH_CONTOURS,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_contours_style(),
                    )
                    mp_drawing.draw_landmarks(
                        image=frame,
                        landmark_list=face_landmarks,
                        connections=mp_face_mesh.FACEMESH_IRISES,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=mp_drawing_styles.get_default_face_mesh_iris_connections_style(),
                    )

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                for landmark_id in LANDMARK_IDS.values():
                    lm = face_landmarks.landmark[landmark_id]
                    px = min(int(lm.x * width), width - 1)
                    py = min(int(lm.y * height), height - 1)
                    cv2.circle(frame, (px, py), 4, (255, 255, 0), -1)

                pose = estimate_head_pose(face_landmarks, frame.shape)
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)
                metrics = compute_face_metrics(face_landmarks)
                expression_states = describe_expression(metrics)

                draw_text(frame, f"face center: ({center_x}, {center_y})", (20, 60))
                draw_text(frame, f"bbox: {x2 - x1}x{y2 - y1}", (20, 90))

                if pose is not None:
                    nose_lm = face_landmarks.landmark[LANDMARK_IDS["nose_tip"]]
                    nose_x = min(int(nose_lm.x * width), width - 1)
                    nose_y = min(int(nose_lm.y * height), height - 1)
                    nose_x_norm = float(nose_lm.x)
                    nose_y_norm = float(nose_lm.y)

                    cv2.line(frame, (nose_x, nose_y), pose.nose_end_point, (255, 0, 255), 2)

                    draw_text(frame, f"yaw:   {pose.yaw:6.1f} deg", (20, 130))
                    draw_text(frame, f"pitch: {pose.pitch:6.1f} deg", (20, 160))
                    draw_text(frame, f"roll:  {pose.roll:6.1f} deg", (20, 190))
                    draw_text(frame, describe_pose(pose.yaw, pose.pitch, pose.roll), (20, 220))
                    draw_text(frame, f"left eye open:   {metrics.left_eye_open:0.3f}", (20, 250))
                    draw_text(frame, f"right eye open:  {metrics.right_eye_open:0.3f}", (20, 280))
                    draw_text(frame, f"blink level:     {metrics.blink_level:0.3f}", (20, 310))
                    draw_text(frame, f"mouth open:      {metrics.mouth_open:0.3f}", (20, 340))
                    draw_text(frame, f"mouth width:     {metrics.mouth_wide:0.3f}", (20, 370))
                    draw_text(frame, f"smile level:     {metrics.smile_level:0.3f}", (20, 400))
                    draw_text(frame, f"brow left/right: {metrics.brow_raise_left:0.3f} / {metrics.brow_raise_right:0.3f}", (20, 430))
                    draw_text(frame, f"brow asymmetry:  {metrics.brow_asymmetry:+0.3f}", (20, 460))
                    draw_text(frame, f"nose offset xy:  {metrics.nose_offset_x:+0.3f}, {metrics.nose_offset_y:+0.3f}", (20, 490))
                    draw_text(frame, f"face wh/area:    {metrics.face_width_ratio:0.3f}, {metrics.face_height_ratio:0.3f}, {metrics.face_area_ratio:0.3f}", (20, 520))
                    draw_text(frame, f"cheek asymmetry: {metrics.cheek_asymmetry:+0.3f}", (20, 550))
                    draw_text(
                        frame,
                        f"cursor control: {'ON' if cursor_controller.enabled else 'OFF'}",
                        (20, 580),
                        (0, 255, 0) if cursor_controller.enabled else (0, 165, 255),
                    )
                    draw_text(
                        frame,
                        f"face overlay: {overlay_mode.upper()}",
                        (20, 610),
                        (0, 255, 0) if overlay_mode != "off" else (0, 165, 255),
                    )
                    draw_text(frame, expression_states[0], (20, 640), (255, 255, 0))
                    draw_text(frame, expression_states[1], (20, 670), (255, 255, 0))
                    draw_text(frame, expression_states[2], (20, 700), (255, 255, 0))
                    draw_text(frame, expression_states[3], (20, 730), (255, 255, 0))

                    if cursor_controller.calibration is not None:
                        yaw_norm, pitch_norm = cursor_controller.get_position_norms(nose_x_norm, nose_y_norm)
                        roll_norm = cursor_controller.get_roll_norm(pose.roll)

                        draw_axis_bar(
                            frame,
                            (x1, max(y1 - 30, 40)),
                            (x2, max(y1 - 30, 40)),
                            yaw_norm,
                            (255, 180, 0),
                            "yaw",
                        )
                        draw_axis_bar(
                            frame,
                            (max(x1 - 30, 20), y2),
                            (max(x1 - 30, 20), y1),
                            pitch_norm,
                            (0, 220, 255),
                            "pitch",
                        )
                        diag_start = (min(x2 + 20, width - 80), y1 + 20)
                        diag_end = (min(x2 + 80, width - 20), min(y2 - 20, height - 20))
                        draw_axis_bar(
                            frame,
                            diag_start,
                            diag_end,
                            roll_norm,
                            (255, 0, 255),
                            "roll",
                        )

                    if calibration_index < len(CALIBRATION_STEPS):
                        _, calibration_message = CALIBRATION_STEPS[calibration_index]
                        draw_text(frame, f"calibration: {calibration_message}", (20, 760))
                    elif cursor_controller.calibration is None:
                        draw_text(frame, "calibration: incomplete", (20, 760), (0, 0, 255))
                    else:
                        draw_text(frame, "calibration: ready", (20, 760))
                        pointer_position = cursor_controller.update(nose_x_norm, nose_y_norm, pose.roll)
                        if pointer_position is not None:
                            draw_text(frame, f"mouse: {pointer_position[0]}, {pointer_position[1]}", (20, 790))
                else:
                    draw_text(frame, "pose estimation failed", (20, 130), (0, 0, 255))
            else:
                draw_text(frame, "No face detected", (20, 60), (0, 0, 255))

            cv2.imshow(WINDOW_NAME, frame)
            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break
            if key == ord("s"):
                snapshot_path = Path("snapshot.jpg")
                cv2.imwrite(str(snapshot_path), frame)
                print(f"Saved frame to {snapshot_path.resolve()}")
            if key == ord("c"):
                enabled = cursor_controller.toggle()
                print(f"Cursor control {'enabled' if enabled else 'disabled'}.")
            if key == ord("d"):
                overlay_mode_index = (overlay_mode_index + 1) % len(OVERLAY_MODES)
                print(f"Face overlay mode: {OVERLAY_MODES[overlay_mode_index]}")
            if key == ord("r"):
                calibration_samples.clear()
                calibration_index = 0
                cursor_controller.calibration = None
                delete_calibration()
                print("Calibration reset. Saved settings deleted.")
            if key == 32 and calibration_index < len(CALIBRATION_STEPS) and results.multi_face_landmarks:
                face_landmarks = results.multi_face_landmarks[0]
                pose = estimate_head_pose(face_landmarks, frame.shape)
                if pose is not None:
                    nose_lm = face_landmarks.landmark[LANDMARK_IDS["nose_tip"]]
                    step_name, _ = CALIBRATION_STEPS[calibration_index]
                    calibration_samples[step_name] = (float(nose_lm.x), float(nose_lm.y), pose.roll)
                    calibration_index += 1
                    print(f"Captured calibration step: {step_name}.")

                    if calibration_index == len(CALIBRATION_STEPS):
                        neutral_x, neutral_y, neutral_roll = calibration_samples["neutral"]
                        left_x, _, _ = calibration_samples["left"]
                        right_x, _, _ = calibration_samples["right"]
                        _, up_y, _ = calibration_samples["up"]
                        _, down_y, _ = calibration_samples["down"]
                        _, _, tilt_left_roll = calibration_samples["tilt_left"]
                        _, _, tilt_right_roll = calibration_samples["tilt_right"]
                        cursor_controller.calibrate(
                            neutral_x=neutral_x,
                            neutral_y=neutral_y,
                            roll=neutral_roll,
                            left_x=min(left_x, neutral_x - 0.01),
                            right_x=max(right_x, neutral_x + 0.01),
                            up_y=min(up_y, neutral_y - 0.01),
                            down_y=max(down_y, neutral_y + 0.01),
                            tilt_left_roll=max(tilt_left_roll, neutral_roll + 4.0),
                            tilt_right_roll=min(tilt_right_roll, neutral_roll - 4.0),
                        )
                        save_calibration(cursor_controller.calibration)
                        print("Calibration completed.")
                        print(f"Saved calibration to {CALIBRATION_FILE.resolve()}")
                    else:
                        print(f"Next step: {CALIBRATION_STEPS[calibration_index][1]}")

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
