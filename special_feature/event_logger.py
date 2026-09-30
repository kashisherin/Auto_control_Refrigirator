"""
special_feature/event_logger.py

Event Logger & Telemetry Data Logging Module (Special Feature).
Logs state change events with formatted timestamps and records continuous telemetry
for export to CSV.
"""

from typing import List, Dict, Any
from datetime import datetime
import pandas as pd


class IntelligentEventLogger:
    """
    Manages human-readable event logging and continuous engineering telemetry data logging.
    """

    def __init__(self):
        self.events: List[Dict[str, str]] = []
        self.telemetry_data: List[Dict[str, Any]] = []

        self.prev_door_state = False
        self.prev_load_category = "LOW"
        self.prev_severity_level = "NORMAL"

    def log_event(self, message: str, time_s: float = 0.0) -> None:
        """Add timestamped human-readable log entry."""
        time_str = datetime.now().strftime("%H:%M:%S")
        sim_time_str = f"t={time_s:.0f}s"
        self.events.append(
            {"real_time": time_str, "sim_time": sim_time_str, "message": message}
        )
        if len(self.events) > 500:
            self.events.pop(0)

    def process_step(
        self,
        time_s: float,
        inside_temp_degc: float,
        ambient_temp_degc: float,
        setpoint_degc: float,
        door_is_open: bool,
        door_open_duration_s: float,
        temp_rate_degc_per_s: float,
        q_est_total_w: float,
        load_category: str,
        severity_level: str,
        cooling_power_w: float,
        alarm_active: bool,
    ) -> None:
        """
        Record continuous telemetry and check for state transitions to generate events.
        """
        # 1. Continuous Telemetry Record
        record = {
            "timestamp_s": round(time_s, 1),
            "inside_temperature_degc": round(inside_temp_degc, 2),
            "ambient_temperature_degc": round(ambient_temp_degc, 2),
            "setpoint_degc": round(setpoint_degc, 2),
            "door_state": "OPEN" if door_is_open else "CLOSED",
            "door_open_duration_s": round(door_open_duration_s, 1),
            "temperature_rate_degc_per_s": round(temp_rate_degc_per_s, 4),
            "estimated_heat_exchange_w": round(q_est_total_w, 1),
            "thermal_severity": severity_level,
            "cooling_power_w": round(cooling_power_w, 1),
            "alarm_state": "ACTIVE" if alarm_active else "OFF",
        }
        self.telemetry_data.append(record)

        # 2. State Transition Events
        if door_is_open and not self.prev_door_state:
            self.log_event("Door opened", time_s)
        elif not door_is_open and self.prev_door_state:
            self.log_event("Door closed", time_s)

        if load_category != self.prev_load_category:
            self.log_event(
                f"Thermal load: {self.prev_load_category} → {load_category}", time_s
            )

        if severity_level != self.prev_severity_level:
            if severity_level == "WARNING":
                self.log_event("WARNING: Thermal load increasing", time_s)
            elif severity_level == "CRITICAL":
                self.log_event("CRITICAL: High heat exchange detected!", time_s)
            elif severity_level == "RECOVERING":
                self.log_event("System recovering", time_s)
            elif severity_level == "NORMAL":
                self.log_event("System normal", time_s)

        self.prev_door_state = door_is_open
        self.prev_load_category = load_category
        self.prev_severity_level = severity_level

    def export_to_csv(self, filepath: str = "data/intelligent_feature_log.csv") -> str:
        """Export telemetry data log to CSV."""
        df = pd.DataFrame(self.telemetry_data)
        df.to_csv(filepath, index=False)
        return filepath

    def reset(self) -> None:
        self.events.clear()
        self.telemetry_data.clear()
        self.prev_door_state = False
        self.prev_load_category = "LOW"
        self.prev_severity_level = "NORMAL"
