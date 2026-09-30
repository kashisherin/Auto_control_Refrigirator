"""
special_feature/thermal_severity.py

Thermal Severity Evaluation Module (Special Feature).
Implements a multi-factor state machine for thermal disturbance assessment.
States: NORMAL, WARNING, CRITICAL, RECOVERING.
"""

from enum import Enum
from dataclasses import dataclass
from config import parameters as p
from special_feature.heat_exchange_estimator import HeatExchangeEstimate


class SeverityLevel(Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    RECOVERING = "RECOVERING"


@dataclass
class ThermalSeverityResult:
    """State result of thermal severity evaluation."""

    level: SeverityLevel
    severity_score: float
    display_title: str
    display_message: str
    heat_exchange_level: str  # LOW, MODERATE, HIGH, SEVERE


class ThermalSeverityEvaluator:
    """
    Evaluates multi-factor thermal severity score and state transitions.
    Combines Door State + Duration + Temp Difference + Temp Rate + Heat Exchange + Temp Error.
    """

    def __init__(self):
        self.current_level = SeverityLevel.NORMAL
        self.was_in_warning_or_critical = False

    def evaluate(
        self,
        inside_temp_degc: float,
        setpoint_degc: float,
        estimate: HeatExchangeEstimate,
        cooling_power_w: float = p.Q_COOLING_MAX_W,
    ) -> ThermalSeverityResult:
        """
        Evaluate thermal disturbance severity score and update state using physical energy balance.
        """
        temp_error = inside_temp_degc - setpoint_degc
        q_in = estimate.q_est_total_w

        # 1. Calculate Multi-Factor Severity Score S in range [0, 100]
        # Formula uses normalized physical quantities
        temp_error_norm = max(0.0, temp_error / (p.T_AMBIENT_DEGC - setpoint_degc))
        load_norm = max(0.0, q_in / p.Q_COOLING_MAX_W)
        rate_norm = max(0.0, estimate.temp_rate_degc_per_s / 0.1)
        door_norm = 1.0 if estimate.door_is_open else 0.0

        raw_score = 100.0 * (
            0.35 * min(1.0, temp_error_norm)
            + 0.35 * min(1.0, max(0.0, load_norm - 1.0))
            + 0.15 * min(1.0, rate_norm)
            + 0.15 * door_norm
        )
        score = round(min(100.0, max(0.0, raw_score)), 1)

        # 2. State Machine Transitions based on ACTUAL simulation physics
        capacity_exceeded = q_in > p.Q_COOLING_MAX_W

        if estimate.door_is_open:
            self.was_in_warning_or_critical = True
            # Brief door opening (<15s) with low temp error -> WARNING; Prolonged or high influx -> CRITICAL
            if score >= p.SEVERITY_SCORE_CRITICAL_THRESHOLD or estimate.door_open_duration_s >= 15.0:
                self.current_level = SeverityLevel.CRITICAL
                title = "CRITICAL - CAPACITY EXCEEDED"
                msg = f"Door OPEN! Heat influx ({q_in:.1f} W) exceeds compressor capacity ({p.Q_COOLING_MAX_W:.1f} W). Temperature is rising."
            else:
                self.current_level = SeverityLevel.WARNING
                title = "WARNING - DOOR OPEN"
                msg = f"Door OPEN ({estimate.door_open_duration_s:.1f}s). Heat exchange is {q_in:.1f} W. Close door to maintain setpoint."
        else:
            # Door is CLOSED
            if abs(temp_error) <= 0.5 and abs(estimate.temp_rate_degc_per_s) <= 0.002:
                self.current_level = SeverityLevel.NORMAL
                self.was_in_warning_or_critical = False
                title = "NORMAL - STABLE"
                msg = "System operating within safe thermal parameters at target setpoint."
            elif temp_error > 0.5:
                # Check if temperature is actively decreasing toward setpoint
                if estimate.temp_rate_degc_per_s < -0.0001:
                    self.current_level = SeverityLevel.RECOVERING
                    title = "RECOVERING - RESTORING SETPOINT"
                    msg = f"Door closed. Compressor cooling ({cooling_power_w:.1f} W) exceeds heat load ({q_in:.1f} W). Temperature is decreasing."
                elif capacity_exceeded:
                    self.current_level = SeverityLevel.WARNING
                    title = "COOLING CAPACITY LIMIT"
                    msg = f"Thermal load ({q_in:.1f} W) exceeds maximum cooling capacity ({p.Q_COOLING_MAX_W:.1f} W). Unable to reduce temperature."
                else:
                    self.current_level = SeverityLevel.WARNING
                    title = "WARNING - TEMPERATURE ABOVE SETPOINT"
                    msg = f"Chamber temperature ({inside_temp_degc:.1f}°C) is above setpoint ({setpoint_degc:.1f}°C)."
            else:
                self.current_level = SeverityLevel.NORMAL
                title = "NORMAL - STABLE"
                msg = "Chamber temperature is stable near setpoint."

        return ThermalSeverityResult(
            level=self.current_level,
            severity_score=score,
            display_title=title,
            display_message=msg,
            heat_exchange_level=estimate.heat_load_category,
        )

    def reset(self) -> None:
        self.current_level = SeverityLevel.NORMAL
        self.was_in_warning_or_critical = False
