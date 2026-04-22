from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from cursor_controller import Calibration


CALIBRATION_FILE = Path("calibration_settings.json")


def load_calibration(calibration_path: Path = CALIBRATION_FILE) -> Calibration | None:
    if not calibration_path.exists():
        return None

    data = json.loads(calibration_path.read_text(encoding="utf-8"))
    required_keys = {
        "neutral_x",
        "neutral_y",
        "roll",
        "left_x",
        "right_x",
        "up_y",
        "down_y",
    }
    if not required_keys.issubset(data):
        return None

    roll = float(data["roll"])
    tilt_left_roll = float(data.get("tilt_left_roll", roll + 16.0))
    tilt_right_roll = float(data.get("tilt_right_roll", roll - 16.0))

    return Calibration(
        neutral_x=float(data["neutral_x"]),
        neutral_y=float(data["neutral_y"]),
        roll=roll,
        left_x=float(data["left_x"]),
        right_x=float(data["right_x"]),
        up_y=float(data["up_y"]),
        down_y=float(data["down_y"]),
        tilt_left_roll=tilt_left_roll,
        tilt_right_roll=tilt_right_roll,
    )


def save_calibration(calibration: Calibration, calibration_path: Path = CALIBRATION_FILE) -> None:
    calibration_path.write_text(
        json.dumps(asdict(calibration), indent=2),
        encoding="utf-8",
    )


def delete_calibration(calibration_path: Path = CALIBRATION_FILE) -> None:
    if calibration_path.exists():
        calibration_path.unlink()
