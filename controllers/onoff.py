"""
controllers/onoff.py

ON/OFF (Bang-Bang) Controller with Hysteresis.
Turns compressor fully ON (q_cooling_max) when chamber temp is above (setpoint + hysteresis/2),
and fully OFF (0 W) when chamber temp drops below (setpoint - hysteresis/2).
"""

from controllers.base_controller import BaseController


class OnOffController(BaseController):
    """
    ON/OFF Hysteresis Controller for industrial refrigeration.
    """

    def __init__(self, q_cooling_max_w: float, hysteresis_degc: float = 1.0):
        """
        Parameters
        ----------
        q_cooling_max_w : float
            Maximum cooling capacity [W].
        hysteresis_degc : float
            Total hysteresis band width [degC] (e.g. 1.0 °C means ±0.5 °C band).
        """
        super().__init__(q_cooling_max_w)
        self.hysteresis_degc = hysteresis_degc
        self.is_on = False

    def compute_cooling_power(
        self,
        current_temp_degc: float,
        setpoint_degc: float,
        dt_s: float,
        door_is_open: bool = False,
    ) -> float:
        upper_threshold = setpoint_degc + self.hysteresis_degc / 2.0
        lower_threshold = setpoint_degc - self.hysteresis_degc / 2.0

        if current_temp_degc >= upper_threshold:
            self.is_on = True
        elif current_temp_degc <= lower_threshold:
            self.is_on = False

        return self.q_cooling_max_w if self.is_on else 0.0

    def reset(self) -> None:
        self.is_on = False
