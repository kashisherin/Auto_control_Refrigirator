"""
controllers/base_controller.py

Abstract base class for all refrigeration controllers (ON/OFF, PID, Adaptive PID, MPC).
All controllers accept current temperature, setpoint, and dt, returning requested cooling power [W].
"""

from abc import ABC, abstractmethod


class BaseController(ABC):
    """Abstract base class for refrigeration temperature controllers."""

    def __init__(self, q_cooling_max_w: float):
        """
        Parameters
        ----------
        q_cooling_max_w : float
            Maximum cooling capacity of the compressor [W].
        """
        self.q_cooling_max_w = q_cooling_max_w

    @abstractmethod
    def compute_cooling_power(
        self,
        current_temp_degc: float,
        setpoint_degc: float,
        dt_s: float,
        door_is_open: bool = False,
    ) -> float:
        """
        Compute required cooling power output [W] in range [0, q_cooling_max_w].

        Parameters
        ----------
        current_temp_degc : float
            Current chamber air temperature [degC].
        setpoint_degc : float
            Target setpoint temperature [degC].
        dt_s : float
            Time step duration [seconds].
        door_is_open : bool
            Whether the door disturbance is currently active.

        Returns
        -------
        float
            Cooling power command [W].
        """
        pass

    def reset(self) -> None:
        """Reset internal states (e.g. integral accumulation, filter states)."""
        pass
