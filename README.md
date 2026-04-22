# Face Recognition Prototype

Desktop prototype in Python for:

- webcam face detection,
- head pose estimation (`yaw`, `pitch`, `roll`),
- face-state diagnostics overlay,
- cursor control from head movement,
- scroll control from calibrated head tilt.

The project is designed to stay simple, practical, and easy to move between machines.

## Features

- Live webcam preview with face detection.
- MediaPipe Face Mesh landmarks with optional overlay modes:
  - `off`
  - `light`
  - `full`
- Head pose estimation from facial landmarks.
- Face-state metrics:
  - eye openness,
  - blink level,
  - mouth openness,
  - mouth width,
  - smile-like score,
  - eyebrow height and asymmetry,
  - nose offset from face center,
  - face proportions in frame,
  - cheek asymmetry.
- Cursor control from calibrated head position.
- Scroll control from calibrated head tilt.
- Calibration persisted to a local settings file.

## Stack

- `OpenCV` for webcam capture, drawing, windows, and PnP math
- `MediaPipe Face Mesh` for face landmarks
- `NumPy` for numerical calculations
- `Quartz` on macOS for mouse control
- `ctypes` on Windows for mouse control

## Project Structure

- `main.py` - app entry point, webcam loop, overlays, calibration flow
- `face_pose.py` - head pose estimation
- `face_metrics.py` - face-state metrics
- `cursor_controller.py` - cursor movement and scroll logic
- `calibration_store.py` - save/load calibration settings
- `run.sh` - local launcher
- `run_in_terminal.sh` - macOS launcher via `Terminal.app`

## Requirements

- Python `3.9`
- A working webcam
- macOS or Windows 11

Notes:

- The current dependency set is tested in this project with Python `3.9`.
- On macOS, webcam and accessibility permissions may be required.

## Setup

1. Clone the repository:

```bash
git clone <YOUR_REPO_URL>
cd face_recognition
```

2. Create a virtual environment:

```bash
python3 -m venv .venv
```

3. Activate it:

macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

The project keeps runtime configuration intentionally small.

### Calibration File

Calibration is stored in:

```text
calibration_settings.json
```

This file is created automatically after calibration and is intentionally ignored by git, because it is machine- and user-specific.

If the file does not exist:

- the app starts in an uncalibrated state,
- calibration is required before cursor control works correctly.

If the file exists:

- the app loads it on startup,
- the app starts as already calibrated.

### Overlay Mode

Overlay mode is not persisted yet. Every start begins with:

- `OFF`

You can cycle modes during runtime:

- `off -> light -> full`

### Mouse / Scroll Tuning

The current tuning lives in code inside `cursor_controller.py`, including:

- smoothing,
- deadzone,
- scroll activation hold time,
- scroll interval,
- neutral gating for scroll.

If needed, these can be exposed later as a config file.

## Running

Standard:

```bash
./run.sh
```

Direct Python run:

```bash
./.venv/bin/python main.py
```

macOS fallback through `Terminal.app`:

```bash
./run_in_terminal.sh
```

The `run_in_terminal.sh` launcher is useful on macOS when camera permission is granted to `Terminal.app`.

## Controls

- `q` - quit
- `s` - save current frame to `snapshot.jpg`
- `c` - toggle cursor control
- `d` - cycle face overlay mode: `off -> light -> full`
- `r` - reset calibration and delete saved calibration file
- `space` - advance calibration steps

## Calibration Flow

If no saved calibration file is present, perform:

1. `neutral`
2. `left`
3. `right`
4. `up`
5. `down`
6. `tilt_left`
7. `tilt_right`

Each step is confirmed with `space`.

After calibration:

- settings are saved automatically,
- future runs reuse the saved calibration,
- scroll uses the calibrated tilt range,
- axis bars use the same normalized calibration space as control.

## Face-State Diagnostics

The app displays:

- face bounding box,
- selected landmark points,
- head pose values,
- normalized axis bars near the face,
- face-state metrics,
- expression-like status labels,
- calibration status,
- cursor status,
- overlay mode.

## System Permissions

### macOS

You may need to allow:

- Camera
- Accessibility

Locations:

- `System Settings > Privacy & Security > Camera`
- `System Settings > Privacy & Security > Accessibility`

If camera access behaves oddly in the current shell app, reset permissions:

```bash
tccutil reset Camera
```

Then reopen the terminal app and run again.

## Portability Notes

This repo is intended to be portable across machines.

Portable:

- source files,
- launch scripts,
- requirements,
- README,
- calibration logic.

Not committed on purpose:

- virtual environment,
- IDE files,
- matplotlib cache,
- snapshots,
- local calibration file.

The macOS launcher uses the script's own directory instead of a hard-coded local path, so it can be moved or cloned elsewhere.

## Known Limitations

- Mouse backends currently target macOS and Windows.
- Scroll tuning may still require per-user adjustment.
- The diagnostics are geometric heuristics, not a full facial-expression model.
- The app currently focuses on a single face.

## Next Ideas

- CSV logging of metrics over time
- GUI in `PySide6`
- Exposed config file for tuning values
- Multi-face support
- Packaging for easier installation
