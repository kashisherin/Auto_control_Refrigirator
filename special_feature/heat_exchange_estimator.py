"""
special_feature/heat_exchange_estimator.py

Heat-Exchange Estimator Module (Special Feature).
Physically interpretable estimation of thermal heat influx entering the refrigeration chamber.

Distinguishes:
- Measured values (Inside Temp, Ambient Temp)
- Simulated values (Cooling Power, Door State)
- Estimated values (Estimated Heat Exchange Q_est_door, Q_est_leak, Total Load)
- Assumed parameters (UA_leak, UA_door_extra)
"""

from dataclasses import dataclass
from config import parameters as p


@dataclass
class HeatExchangeEstimate:
    """Dataclass holding interpretable heat exchange estimation results."""

    delta_temp_degc: float
    door_is_open: bool
    door_open_duration_s: float
    temp_rate_degc_per_s: float
    q_est_leak_w: float
    q_est_door_w: float
    q_est_total_w: float
    heat_load_category: str  # "LOW", "MODERATE", "HIGH", "SEVERE"


class HeatExchangeEstimator:
    """
    Estimates real-time heat exchange and thermal disturbance load.
    Uses physically interpretable Newton's law of cooling and conductance models.
    """

    def __init__(
        self,
        ua_leak_w_per_k: float = p.UA_LEAK_W_PER_K,
        ua_door_extra_w_per_k: float = p.UA_DOOR_EXTRA_W_PER_K,
    ):
        self.ua_leak = ua_leak_w_per_k
        self.ua_door_extra = ua_door_extra_w_per_k
        self.prev_inside_temp = None
        self.temp_rate_filtered = 0.0

    def estimate(
        self,
        inside_temp_degc: float,
        ambient_temp_degc: float,
        door_is_open: bool,
        door_open_duration_s: float,
        dt_s: float,
    ) -> HeatExchangeEstimate:
        """
        Compute thermal load estimate from current sensor and state inputs.
        """
        delta_temp = max(0.0, ambient_temp_degc - inside_temp_degc)

        # 1. Temperature Change Rate (dT/dt) with exponential smoothing
        if self.prev_inside_temp is not None and dt_s > 0:
            raw_rate = (inside_temp_degc - self.prev_inside_temp) / dt_s
            alpha = 0.2
            self.temp_rate_filtered = (
                alpha * raw_rate + (1.0 - alpha) * self.temp_rate_filtered
            )
        else:
            self.temp_rate_filtered = 0.0

        self.prev_inside_temp = inside_temp_degc

        # 2. Estimated Heat Leakage through wall insulation
        q_est_leak = self.ua_leak * delta_temp

        # 3. Estimated Heat Exchange through doorway (if open)
        if door_is_open:
            q_est_door = self.ua_door_extra * delta_temp
        else:
            q_est_door = 0.0

        q_est_total = q_est_leak + q_est_door

        # 4. Categorize Heat Load
        if q_est_total < p.WARNING_HEAT_LOAD_W:
            category = "LOW"
        elif q_est_total < 450.0:
            category = "MODERATE"
        elif q_est_total < p.CRITICAL_HEAT_LOAD_W:
            category = "HIGH"
        else:
            category = "SEVERE"

        return HeatExchangeEstimate(
            delta_temp_degc=round(delta_temp, 2),
            door_is_open=door_is_open,
            door_open_duration_s=round(door_open_duration_s, 1),
            temp_rate_degc_per_s=round(self.temp_rate_filtered, 4),
            q_est_leak_w=round(q_est_leak, 1),
            q_est_door_w=round(q_est_door, 1),
            q_est_total_w=round(q_est_total, 1),
            heat_load_category=category,
        )

    def reset(self) -> None:
        self.prev_inside_temp = None
        self.temp_rate_filtered = 0.0
