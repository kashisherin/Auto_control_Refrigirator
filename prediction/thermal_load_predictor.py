"""
prediction/thermal_load_predictor.py

Thermal Load & Disturbance Predictor.
Uses historical simulation logs and door state trends to predict incoming thermal load spikes
and estimated recovery duration.
"""

import numpy as np


class ThermalLoadPredictor:
    """
    Predicts thermal load spikes (W) and temperature rise (°C) based on door disturbance history.
    """

    def __init__(self, ua_door_extra_w_per_k: float = 40.0):
        self.ua_door_extra = ua_door_extra_w_per_k
        self.history = []

    def record_observation(
        self,
        time_s: float,
        temp_degc: float,
        door_open: bool,
        cooling_power_w: float,
    ) -> None:
        """Store historical time-series observation."""
        self.history.append(
            {
                "time_s": time_s,
                "temp_degc": temp_degc,
                "door_open": door_open,
                "cooling_power_w": cooling_power_w,
            }
        )
        if len(self.history) > 1000:
            self.history.pop(0)

    def predict_heat_flux_w(
        self, current_temp_degc: float, ambient_temp_degc: float, door_open: bool
    ) -> float:
        """
        Predict net heat influx [W] into the chamber.
        """
        extra_conductance = self.ua_door_extra if door_open else 0.0
        return (8.0 + extra_conductance) * (ambient_temp_degc - current_temp_degc)

    def estimate_recovery_time_s(
        self, temp_spike_degc: float, setpoint_degc: float, cooling_capacity_w: float
    ) -> float:
        """
        Estimate time required [seconds] to return to within 0.5 °C of setpoint.
        """
        delta_t = max(0.0, temp_spike_degc - setpoint_degc)
        if delta_t <= 0.5:
            return 0.0

        # Approximate thermal time constant tau = C / (UA + cooling_derivative)
        tau_approx = 20000.0 / 8.0  # ~ 2500 s
        return min(3600.0, tau_approx * np.log(delta_t / 0.5))
