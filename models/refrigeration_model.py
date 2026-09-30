"""
models/refrigeration_model.py

Simplified first-order thermal model of the refrigeration chamber
(Section 3 of the project brief).

Physical picture
-----------------
Think of the chamber air as a single thermal "capacitor" with
capacitance C. Heat flows in through the walls (leakage) and, when the
door is open, through the doorway too. Heat flows out because the
compressor is actively cooling the chamber. The net heat flow changes
the stored thermal energy, and therefore the temperature:

    C * dT/dt = Q_leak + Q_door - Q_cooling

    Q_leak    = UA_leak       * (T_ambient - T)   [W]   (always present)
    Q_door    = UA_door_extra * (T_ambient - T)   [W]   (only if door open)
    Q_cooling = compressor cooling power           [W]   (Phase 1: constant)

All temperatures are in degrees Celsius (only *differences* matter in
this linear model, so degC and Kelvin give identical results here).

This class knows nothing about controllers or doors directly -- it
just needs to be told, at every time step, how much extra conductance
the door is contributing and how much cooling power is being applied.
That keeps the plant model, the disturbance model and the controller
cleanly separated, as required by the project architecture (Section 15).
"""

from dataclasses import dataclass


@dataclass
class RefrigerationModel:
    """
    First-order thermal model of a refrigeration chamber.

    Parameters
    ----------
    temperature_degc : float
        Current chamber air temperature [degC]. Updated in place by step().
    ambient_temperature_degc : float
        Temperature of the surrounding room / outside air [degC].
    thermal_capacitance_j_per_k : float
        Effective thermal capacitance C of the chamber [J/K].
    ua_leak_w_per_k : float
        Wall/insulation heat-leak conductance [W/K], present at all times.
    """

    temperature_degc: float
    ambient_temperature_degc: float
    thermal_capacitance_j_per_k: float
    ua_leak_w_per_k: float

    def step(
        self,
        dt_s: float,
        cooling_power_w: float,
        extra_conductance_w_per_k: float = 0.0,
    ) -> float:
        """
        Advance the chamber temperature by one time step using the
        explicit Euler method.

        Parameters
        ----------
        dt_s : float
            Integration time step [s]. Keep this small (e.g. 1 s) for
            numerical accuracy with this simple integrator.
        cooling_power_w : float
            Heat removed by the refrigeration unit during this step [W].
            In Phase 1 this is a fixed constant; from Phase 4 onward it
            will come from a controller's compressor command.
        extra_conductance_w_per_k : float, optional
            Extra heat-transfer conductance contributed by an open door
            during this step [W/K]. Zero when the door is closed.

        Returns
        -------
        float
            The updated chamber temperature [degC].

        Why Euler integration?
        -----------------------
        Euler's method approximates dT/dt with (T_next - T) / dt and
        solves for T_next. It is the simplest possible numerical
        integrator. For a first-order linear system like this one, with
        a 1-second step against a time constant of thousands of seconds,
        Euler integration is stable and accurate enough for a mini
        project. (Later, if you switch to python-control's linear
        system objects, you could instead use exact matrix-exponential
        solutions -- but Euler makes every line of the physics visible,
        which matters while you are still learning the model.)
        """
        total_conductance_w_per_k = self.ua_leak_w_per_k + extra_conductance_w_per_k

        # Heat flowing IN through walls and (if open) the doorway.
        q_in_w = total_conductance_w_per_k * (
            self.ambient_temperature_degc - self.temperature_degc
        )

        # Net heat flow into the chamber air.
        q_net_w = q_in_w - cooling_power_w

        # dT/dt = Q_net / C  ->  Euler step: T_next = T + (Q_net/C) * dt
        d_temperature_degc = (q_net_w / self.thermal_capacitance_j_per_k) * dt_s

        self.temperature_degc += d_temperature_degc
        return self.temperature_degc
