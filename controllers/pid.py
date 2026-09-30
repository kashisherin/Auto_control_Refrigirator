"""
controllers/pid.py

Standard Proportional-Integral-Derivative (PID) controller with anti-windup clamping
and derivative filtering for temperature control.
"""

from controllers.base_controller import BaseController


class PIDController(BaseController):
    """
    Standard PID Controller with clamping anti-windup and first-order derivative filtering.
    """

    def __init__(
        self,
        q_cooling_max_w: float,
        ua_leak_w_per_k: float = 8.0,
        ambient_temp_degc: float = 25.0,
        kp: float = 12.0,
        ki: float = 0.05,
        kd: float = 80.0,
        filter_alpha: float = 0.1,
    ):
        """
        Parameters
        ----------
        q_cooling_max_w : float
            Max compressor power [W].
        ua_leak_w_per_k : float
            Wall heat-leak conductance [W/K].
        ambient_temp_degc : float
            Ambient temperature [degC].
        kp : float
            Proportional gain [W/K].
        ki : float
            Integral gain [W/(K*s)].
        kd : float
            Derivative gain [W*s/K].
        filter_alpha : float
            Derivative low-pass filter coefficient (0 < alpha <= 1).
        """
        super().__init__(q_cooling_max_w)
        self.ua_leak = ua_leak_w_per_k
        self.ambient_temp = ambient_temp_degc
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.filter_alpha = filter_alpha

        self.integral = 0.0
        self.prev_error = 0.0
        self.filtered_derivative = 0.0

    def compute_cooling_power(
        self,
        current_temp_degc: float,
        setpoint_degc: float,
        dt_s: float,
        door_is_open: bool = False,
    ) -> float:
        # Error e = T - T_set (positive when chamber is warmer than setpoint -> need cooling)
        error = current_temp_degc - setpoint_degc

        # Baseline steady state heat loss: Q_ss = UA * (T_amb - T_set)
        q_ss = self.ua_leak * (self.ambient_temp - setpoint_degc)

        # Proportional term
        p_term = self.kp * error

        # Derivative term with first-order exponential smoothing filter
        if dt_s > 0:
            raw_derivative = (error - self.prev_error) / dt_s
            self.filtered_derivative = (
                self.filter_alpha * raw_derivative
                + (1.0 - self.filter_alpha) * self.filtered_derivative
            )
        else:
            self.filtered_derivative = 0.0

        d_term = self.kd * self.filtered_derivative
        self.prev_error = error

        # Current integral term
        i_term = self.ki * self.integral

        # Raw output command with steady state feedforward
        raw_output = q_ss + p_term + i_term + d_term

        # Clamp output to [0, q_cooling_max_w]
        clamped_output = max(0.0, min(self.q_cooling_max_w, raw_output))

        # Anti-windup conditional integration:
        # Only integrate when not pushing further into saturation
        is_saturated_high = (raw_output >= self.q_cooling_max_w) and (error > 0)
        is_saturated_low = (raw_output <= 0.0) and (error < 0)

        if not (is_saturated_high or is_saturated_low):
            self.integral += error * dt_s

        return clamped_output

    def reset(self) -> None:
        self.integral = 0.0
        self.prev_error = 0.0
        self.filtered_derivative = 0.0
