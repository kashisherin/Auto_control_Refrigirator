"""
controllers/adaptive_pid.py

Adaptive PID Controller with Gain Scheduling & Disturbance Feedforward.
Dynamically adjusts gains (Kp, Ki, Kd) based on temperature error magnitude
and door-open disturbance detection to rapidly suppress thermal transients.
"""

from controllers.base_controller import BaseController


class AdaptivePIDController(BaseController):
    """
    Adaptive PID Controller with dynamic gain scheduling & disturbance feedforward.
    """

    def __init__(
        self,
        q_cooling_max_w: float,
        kp_base: float = 12.0,
        ki_base: float = 0.05,
        kd_base: float = 80.0,
        door_kp_boost: float = 2.5,
        door_kd_boost: float = 3.0,
    ):
        """
        Parameters
        ----------
        q_cooling_max_w : float
            Max cooling capacity [W].
        kp_base, ki_base, kd_base : float
            Nominal steady-state gains.
        door_kp_boost, door_kd_boost : float
            Multipliers applied to Kp and Kd when door disturbance is active.
        """
        super().__init__(q_cooling_max_w)
        self.kp_base = kp_base
        self.ki_base = ki_base
        self.kd_base = kd_base
        self.door_kp_boost = door_kp_boost
        self.door_kd_boost = door_kd_boost

        self.integral = 0.0
        self.prev_error = 0.0
        self.filtered_derivative = 0.0

        # Current active gains (logged for UI telemetry)
        self.active_kp = kp_base
        self.active_ki = ki_base
        self.active_kd = kd_base

    def compute_cooling_power(
        self,
        current_temp_degc: float,
        setpoint_degc: float,
        dt_s: float,
        door_is_open: bool = False,
    ) -> float:
        error = current_temp_degc - setpoint_degc
        abs_error = abs(error)

        # Gain scheduling adaptation logic
        # 1. Error-dependent boost: larger error = aggressive proportional response
        error_scale = 1.0 + min(3.0, abs_error / 2.0)

        # 2. Disturbance-dependent boost: door open triggers immediate aggressive cooling
        door_scale_p = self.door_kp_boost if door_is_open else 1.0
        door_scale_d = self.door_kd_boost if door_is_open else 1.0

        self.active_kp = self.kp_base * error_scale * door_scale_p
        self.active_ki = self.ki_base * (1.5 if door_is_open else 1.0)
        self.active_kd = self.kd_base * error_scale * door_scale_d

        q_ss = 8.0 * (25.0 - setpoint_degc)
        feedforward_w = (40.0 * (25.0 - current_temp_degc)) if door_is_open else 0.0

        p_term = self.active_kp * error
        i_term = self.active_ki * self.integral

        # Filtered Derivative
        if dt_s > 0:
            raw_derivative = (error - self.prev_error) / dt_s
            alpha = 0.15 if door_is_open else 0.10
            self.filtered_derivative = (
                alpha * raw_derivative + (1.0 - alpha) * self.filtered_derivative
            )
        else:
            self.filtered_derivative = 0.0

        d_term = self.active_kd * self.filtered_derivative
        self.prev_error = error

        raw_output = q_ss + p_term + i_term + d_term + feedforward_w
        clamped_output = max(0.0, min(self.q_cooling_max_w, raw_output))

        # Anti-windup conditional integration
        is_saturated_high = (raw_output >= self.q_cooling_max_w) and (error > 0)
        is_saturated_low = (raw_output <= 0.0) and (error < 0)

        if not (is_saturated_high or is_saturated_low):
            self.integral += error * dt_s

        return clamped_output

    def reset(self) -> None:
        self.integral = 0.0
        self.prev_error = 0.0
        self.filtered_derivative = 0.0
        self.active_kp = self.kp_base
        self.active_ki = self.ki_base
        self.active_kd = self.kd_base
