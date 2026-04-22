from __future__ import annotations

import platform
from dataclasses import dataclass
from time import monotonic


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


@dataclass
class Calibration:
    neutral_x: float
    neutral_y: float
    roll: float
    left_x: float
    right_x: float
    up_y: float
    down_y: float
    tilt_left_roll: float
    tilt_right_roll: float


class MouseBackend:
    def screen_size(self) -> tuple[int, int]:
        raise NotImplementedError

    def move_to(self, x: int, y: int) -> None:
        raise NotImplementedError

    def scroll(self, delta: int) -> None:
        raise NotImplementedError

    def left_click(self) -> None:
        raise NotImplementedError

    def right_click(self) -> None:
        raise NotImplementedError


class MacOSMouseBackend(MouseBackend):
    def __init__(self) -> None:
        from Quartz import (
            CGDisplayPixelsHigh,
            CGDisplayPixelsWide,
            CGEventCreateMouseEvent,
            CGEventCreateScrollWheelEvent,
            CGEventPost,
            CGEventGetLocation,
            CGPointMake,
            kCGEventLeftMouseDown,
            kCGEventLeftMouseUp,
            kCGEventMouseMoved,
            kCGEventRightMouseDown,
            kCGEventRightMouseUp,
            kCGHIDEventTap,
            kCGMouseButtonLeft,
            kCGMouseButtonRight,
            kCGScrollEventUnitLine,
            CGMainDisplayID,
            CGEventCreate,
        )
        from AppKit import NSScreen

        self.CGDisplayPixelsHigh = CGDisplayPixelsHigh
        self.CGDisplayPixelsWide = CGDisplayPixelsWide
        self.CGEventCreateMouseEvent = CGEventCreateMouseEvent
        self.CGEventCreateScrollWheelEvent = CGEventCreateScrollWheelEvent
        self.CGEventCreate = CGEventCreate
        self.CGEventGetLocation = CGEventGetLocation
        self.CGEventPost = CGEventPost
        self.CGPointMake = CGPointMake
        self.kCGEventLeftMouseDown = kCGEventLeftMouseDown
        self.kCGEventLeftMouseUp = kCGEventLeftMouseUp
        self.kCGEventMouseMoved = kCGEventMouseMoved
        self.kCGEventRightMouseDown = kCGEventRightMouseDown
        self.kCGEventRightMouseUp = kCGEventRightMouseUp
        self.kCGHIDEventTap = kCGHIDEventTap
        self.kCGMouseButtonLeft = kCGMouseButtonLeft
        self.kCGMouseButtonRight = kCGMouseButtonRight
        self.kCGScrollEventUnitLine = kCGScrollEventUnitLine
        self.display_id = CGMainDisplayID()
        self.NSScreen = NSScreen

    def screen_size(self) -> tuple[int, int]:
        width = int(self.CGDisplayPixelsWide(self.display_id))
        height = int(self.CGDisplayPixelsHigh(self.display_id))
        if width > 0 and height > 0:
            return width, height

        frame = self.NSScreen.mainScreen().frame()
        width = int(frame.size.width)
        height = int(frame.size.height)
        return width, height

    def move_to(self, x: int, y: int) -> None:
        event = self.CGEventCreateMouseEvent(
            None,
            self.kCGEventMouseMoved,
            self.CGPointMake(x, y),
            self.kCGMouseButtonLeft,
        )
        self.CGEventPost(self.kCGHIDEventTap, event)

    def scroll(self, delta: int) -> None:
        event = self.CGEventCreateScrollWheelEvent(
            None,
            self.kCGScrollEventUnitLine,
            1,
            delta,
        )
        self.CGEventPost(self.kCGHIDEventTap, event)

    def left_click(self) -> None:
        self._click(self.kCGEventLeftMouseDown, self.kCGEventLeftMouseUp, self.kCGMouseButtonLeft)

    def right_click(self) -> None:
        self._click(self.kCGEventRightMouseDown, self.kCGEventRightMouseUp, self.kCGMouseButtonRight)

    def _click(self, down_event_type: int, up_event_type: int, button: int) -> None:
        location = self.CGEventGetLocation(self.CGEventCreate(None))
        down = self.CGEventCreateMouseEvent(None, down_event_type, location, button)
        up = self.CGEventCreateMouseEvent(None, up_event_type, location, button)
        self.CGEventPost(self.kCGHIDEventTap, down)
        self.CGEventPost(self.kCGHIDEventTap, up)


class WindowsMouseBackend(MouseBackend):
    def __init__(self) -> None:
        import ctypes

        self.user32 = ctypes.windll.user32
        self.MOUSEEVENTF_WHEEL = 0x0800
        self.MOUSEEVENTF_LEFTDOWN = 0x0002
        self.MOUSEEVENTF_LEFTUP = 0x0004
        self.MOUSEEVENTF_RIGHTDOWN = 0x0008
        self.MOUSEEVENTF_RIGHTUP = 0x0010

    def screen_size(self) -> tuple[int, int]:
        width = int(self.user32.GetSystemMetrics(0))
        height = int(self.user32.GetSystemMetrics(1))
        return width, height

    def move_to(self, x: int, y: int) -> None:
        self.user32.SetCursorPos(x, y)

    def scroll(self, delta: int) -> None:
        self.user32.mouse_event(self.MOUSEEVENTF_WHEEL, 0, 0, delta, 0)

    def left_click(self) -> None:
        self.user32.mouse_event(self.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        self.user32.mouse_event(self.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

    def right_click(self) -> None:
        self.user32.mouse_event(self.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        self.user32.mouse_event(self.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)


def create_mouse_backend() -> MouseBackend:
    system = platform.system()
    if system == "Darwin":
        return MacOSMouseBackend()
    if system == "Windows":
        return WindowsMouseBackend()
    raise RuntimeError(f"Unsupported platform for mouse control: {system}")


class CursorController:
    def __init__(self) -> None:
        self.enabled = False
        self.calibration: Calibration | None = None
        self.mouse = create_mouse_backend()
        self.screen_width, self.screen_height = self.mouse.screen_size()
        self.filtered_x = self.screen_width / 2
        self.filtered_y = self.screen_height / 2
        self.smoothing = 0.22
        self.deadzone_ratio = 0.04
        self.scroll_step = 6
        self.scroll_interval_sec = 0.22
        self.scroll_activation_sec = 0.28
        self.scroll_neutral_gate = 0.32
        self.last_scroll_time = 0.0
        self.scroll_direction: str | None = None
        self.scroll_started_at = 0.0

    def toggle(self) -> bool:
        self.enabled = not self.enabled
        return self.enabled

    def calibrate(
        self,
        neutral_x: float,
        neutral_y: float,
        roll: float,
        left_x: float,
        right_x: float,
        up_y: float,
        down_y: float,
        tilt_left_roll: float,
        tilt_right_roll: float,
    ) -> None:
        self.calibration = Calibration(
            neutral_x=neutral_x,
            neutral_y=neutral_y,
            roll=roll,
            left_x=left_x,
            right_x=right_x,
            up_y=up_y,
            down_y=down_y,
            tilt_left_roll=tilt_left_roll,
            tilt_right_roll=tilt_right_roll,
        )
        self.filtered_x = self.screen_width / 2
        self.filtered_y = self.screen_height / 2
        self.mouse.move_to(int(self.filtered_x), int(self.filtered_y))

    def update(self, nose_x: float, nose_y: float, roll: float) -> tuple[int, int] | None:
        if not self.enabled or self.calibration is None:
            return None

        horizontal_norm, vertical_norm = self.get_position_norms(nose_x, nose_y)
        target_x = self._norm_to_output(horizontal_norm, self.screen_width)
        target_y = self._norm_to_output(vertical_norm, self.screen_height)

        self.filtered_x += (target_x - self.filtered_x) * self.smoothing
        self.filtered_y += (target_y - self.filtered_y) * self.smoothing
        self.mouse.move_to(int(self.filtered_x), int(self.filtered_y))

        self._handle_scroll(roll, horizontal_norm, vertical_norm)
        return int(self.filtered_x), int(self.filtered_y)

    def _handle_scroll(self, roll: float, horizontal_norm: float, vertical_norm: float) -> None:
        if self.calibration is None:
            return

        now = monotonic()
        if abs(horizontal_norm) > self.scroll_neutral_gate or abs(vertical_norm) > self.scroll_neutral_gate:
            self.scroll_direction = None
            self.scroll_started_at = 0.0
            return

        direction = self._scroll_direction(roll)
        if direction is None:
            self.scroll_direction = None
            self.scroll_started_at = 0.0
            return

        if self.scroll_direction != direction:
            self.scroll_direction = direction
            self.scroll_started_at = now
            return

        if now - self.scroll_started_at < self.scroll_activation_sec:
            return
        if now - self.last_scroll_time < self.scroll_interval_sec:
            return

        if direction == "left":
            self.mouse.scroll(self.scroll_step)
        elif direction == "right":
            self.mouse.scroll(-self.scroll_step)
        self.last_scroll_time = now

    def _scroll_direction(self, roll: float) -> str | None:
        if self.calibration is None:
            return None

        left_threshold = self._interpolate(
            self.calibration.roll,
            self.calibration.tilt_left_roll,
            0.72,
        )
        right_threshold = self._interpolate(
            self.calibration.roll,
            self.calibration.tilt_right_roll,
            0.72,
        )

        if roll >= left_threshold:
            return "left"
        if roll <= right_threshold:
            return "right"
        return None

    def get_position_norms(self, nose_x: float, nose_y: float) -> tuple[float, float]:
        if self.calibration is None:
            return 0.0, 0.0

        horizontal = self._normalize_axis(
            value=nose_x,
            center=self.calibration.neutral_x,
            min_value=self.calibration.left_x,
            max_value=self.calibration.right_x,
        )
        vertical = self._normalize_axis(
            value=nose_y,
            center=self.calibration.neutral_y,
            min_value=self.calibration.up_y,
            max_value=self.calibration.down_y,
        )
        return horizontal, vertical

    def get_roll_norm(self, roll: float) -> float:
        if self.calibration is None:
            return 0.0

        if roll >= self.calibration.roll:
            span = max(self.calibration.tilt_left_roll - self.calibration.roll, 1e-6)
            return clamp((roll - self.calibration.roll) / span, 0.0, 1.0)

        span = max(self.calibration.roll - self.calibration.tilt_right_roll, 1e-6)
        return clamp((roll - self.calibration.roll) / span, -1.0, 0.0)

    def _map_axis(
        self,
        value: float,
        center: float,
        min_value: float,
        max_value: float,
        output_size: int,
    ) -> float:
        normalized = self._normalize_axis(value, center, min_value, max_value)
        return self._norm_to_output(normalized, output_size)

    def _normalize_axis(
        self,
        value: float,
        center: float,
        min_value: float,
        max_value: float,
    ) -> float:
        left_span = max(center - min_value, 1e-6)
        right_span = max(max_value - center, 1e-6)
        deadzone = min(left_span, right_span) * self.deadzone_ratio

        if abs(value - center) <= deadzone:
            return 0.0

        if value < center:
            normalized = (value - center) / left_span
        else:
            normalized = (value - center) / right_span

        return clamp(normalized, -1.0, 1.0)

    def _norm_to_output(self, normalized: float, output_size: int) -> float:
        return ((normalized + 1.0) / 2.0) * (output_size - 1)

    def left_click(self) -> None:
        self.mouse.left_click()

    def right_click(self) -> None:
        self.mouse.right_click()

    def _interpolate(self, start: float, end: float, ratio: float) -> float:
        return start + ((end - start) * ratio)
