"""
special_feature/alert_manager.py

Alert Manager Module (Special Feature).
Manages visual and audio alert states, alarm muting toggle (🔊 Alarm: ON/OFF),
and audio signal patterns for web audio synthesis.
"""

from dataclasses import dataclass
from special_feature.thermal_severity import SeverityLevel, ThermalSeverityResult


@dataclass
class AlertStatus:
    """Dataclass holding current visual and audio alert status."""

    severity_level: str
    display_title: str
    display_message: str
    audio_pattern: str  # "NONE", "PERIODIC_BEEP", "REPEATED_ALARM"
    alarm_enabled: bool
    is_muted: bool
    should_play_sound: bool


class AlertManager:
    """
    Manages operator alerts, visual warnings, and audio alarm states.
    Muting alarm silences audio but leaves visual warnings active.
    """

    def __init__(self):
        self.alarm_enabled = True
        self.is_muted = False

    def toggle_mute(self) -> bool:
        """Toggle alarm mute state (🔊 Alarm: ON/OFF)."""
        self.is_muted = not self.is_muted
        return self.is_muted

    def set_mute(self, is_muted: bool) -> None:
        """Set alarm mute state."""
        self.is_muted = is_muted

    def process(self, severity_res: ThermalSeverityResult) -> AlertStatus:
        """
        Process current thermal severity result and determine audio/visual alert payload.
        """
        level = severity_res.level

        if level == SeverityLevel.NORMAL:
            pattern = "NONE"
        elif level == SeverityLevel.WARNING:
            pattern = "PERIODIC_BEEP"
        elif level == SeverityLevel.CRITICAL:
            pattern = "REPEATED_ALARM"
        else:  # RECOVERING
            pattern = "NONE"

        should_play = (
            self.alarm_enabled
            and not self.is_muted
            and pattern != "NONE"
        )

        return AlertStatus(
            severity_level=level.value,
            display_title=severity_res.display_title,
            display_message=severity_res.display_message,
            audio_pattern=pattern,
            alarm_enabled=self.alarm_enabled,
            is_muted=self.is_muted,
            should_play_sound=should_play,
        )
