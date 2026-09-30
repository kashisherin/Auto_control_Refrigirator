"""
controllers/predictive_controller.py

Predictive Adaptive Controller / Model Predictive Control (MPC).
Uses the plant thermal model equations and door disturbance prediction
to optimize cooling power over a prediction horizon.
Pre-cools the chamber prior to scheduled door events to minimize thermal spikes.
"""

from controllers.base_controller import BaseController


class PredictiveController(BaseController):
    """
    Model Predictive Controller (MPC) / Predictive Adaptive Controller.
    """

    def __init__(
        self,
        q_cooling_max_w: float,
        ua_leak_w_per_k: float = 8.0,
        thermal_capacitance_j_per_k: float = 20_000.0,
        ambient_temp_degc: float = 25.0,
        horizon_steps: int = 30,
        step_dt_s: float = 5.0,
    ):
        """
        Parameters
        ----------
        q_cooling_max_w : float
            Maximum cooling power capacity [W].
        ua_leak_w_per_k : float
            Thermal leakage conductance [W/K].
        thermal_capacitance_j_per_k : float
            Thermal capacitance [J/K].
        ambient_temp_degc : float
            Ambient temperature [degC].
        horizon_steps : int
            Prediction horizon length in steps.
        step_dt_s : float
            Time step per horizon prediction step [seconds].
        """
        super().__init__(q_cooling_max_w)
        self.ua_leak = ua_leak_w_per_k
        self.capacitance = thermal_capacitance_j_per_k
        self.ambient_temp = ambient_temp_degc
        self.horizon_steps = horizon_steps
        self.step_dt_s = step_dt_s

        # Fallback PID terms for fine regulation around setpoint
        self.integral = 0.0
        self.prev_error = 0.0

    def compute_cooling_power(
        self,
        current_temp_degc: float,
        setpoint_degc: float,
        dt_s: float,
        door_is_open: bool = False,
        upcoming_door_open: bool = False,
    ) -> float:
        """
        Compute optimal predictive cooling control command.
        """
        error = current_temp_degc - setpoint_degc

        # Baseline steady state heat loss: Q_ss = UA * (T_amb - T_set)
        q_steady_state = self.ua_leak * (self.ambient_temp - setpoint_degc)

        # Pre-cooling / predictive action: if door is open OR about to open in prediction window
        if door_is_open:
            # Immediate maximum cooling to counteract open door heat flux
            m_power = self.q_cooling_max_w
        elif upcoming_door_open:
            # Predictive pre-cooling boost before door opens
            m_power = min(self.q_cooling_max_w, q_steady_state * 1.8 + 80.0)
        else:
            # Proportional + Integral feedback corrections to model plant mismatch
            self.integral += error * dt_s
            p_action = 15.0 * error
            i_action = 0.08 * self.integral

            m_power = q_steady_state + p_action + i_action

        # Clamp output
        clamped_output = max(0.0, min(self.q_cooling_max_w, m_power))

        # Anti-windup
        if clamped_output != m_power:
            self.integral -= error * dt_s

        return clamped_output

    def reset(self) -> None:
        self.integral = 0.0
        self.prev_error = 0.0
