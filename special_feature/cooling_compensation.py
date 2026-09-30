"""
special_feature/cooling_compensation.py

Cooling Compensation Module (Special Feature).
Feedforward thermal disturbance compensation layer.
Smoothly ramps cooling requirement up when heat exchange increases,
and gradually returns toward normal control during recovery.
"""

from config import parameters as p
from special_feature.heat_exchange_estimator import HeatExchangeEstimate
from special_feature.thermal_severity import ThermalSeverityResult, SeverityLevel


class CoolingCompensationLayer:
    """
    Feedforward disturbance compensation layer.
    Computes smooth feedforward cooling power demand [W] to add to controller feedback output.
    """

    def __init__(self, q_max_w: float = p.Q_COOLING_MAX_W):
        self.q_max_w = q_max_w
        self.current_compensation_pct = 0.0

    def compute_compensation_w(
        self,
        estimate: HeatExchangeEstimate,
        severity: ThermalSeverityResult,
        dt_s: float,
    ) -> float:
        """
        Compute smooth feedforward compensation cooling power [W].
        """
        # Determine target compensation percentage based on disturbance severity
        if severity.level == SeverityLevel.CRITICAL:
            target_pct = 75.0
        elif severity.level == SeverityLevel.WARNING:
            target_pct = 40.0
        elif severity.level == SeverityLevel.RECOVERING:
            target_pct = 15.0
        else:
            target_pct = 0.0

        # Additional boost proportional to estimated heat influx Q_est_door
        if estimate.door_is_open and self.q_max_w > 0:
            extra_load_pct = (estimate.q_est_door_w / self.q_max_w) * 100.0 * 0.6
            target_pct = min(100.0, target_pct + extra_load_pct)

        # Smooth ramp rate limiting (prevents instant 30% -> 100% jumps)
        max_step_pct = p.COMPENSATION_RAMP_RATE_PCT_PER_S * dt_s

        if target_pct > self.current_compensation_pct:
            self.current_compensation_pct = min(
                target_pct, self.current_compensation_pct + max_step_pct
            )
        else:
            # Gradual return toward normal during recovery
            self.current_compensation_pct = max(
                target_pct, self.current_compensation_pct - (max_step_pct * 0.5)
            )

        compensation_w = (self.current_compensation_pct / 100.0) * self.q_max_w
        return round(compensation_w, 1)

    def reset(self) -> None:
        self.current_compensation_pct = 0.0
