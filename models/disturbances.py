"""
models/disturbances.py

Mathematical model of the door-opening disturbance.

Section 4 of the project brief defines the door as a two-state
variable:

    door = 0   -> DOOR CLOSED -> normal heat leakage only
    door = 1   -> DOOR OPEN   -> extra heat-transfer conductance is
                                  added on top of the normal leakage

We model that "extra conductance" idea with a simple linear
(Newton's-law-of-cooling) term, exactly like the wall-leakage term:

    Q_door(t) = door(t) * UA_door_extra * (T_ambient - T(t))

so the disturbance is completely described by:
    1. WHEN the door is open (a time schedule), and
    2. HOW MUCH extra conductance it adds while open (UA_door_extra).

Phase 1 uses a single scripted open/close event so the physics can be
verified against hand calculations. Later phases (Experiment 3, 6,
Section 11) will reuse this same class with a *list* of open/close
events to script repeated door openings.
"""

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class DoorDisturbance:
    """
    Represents the door state over time and the extra thermal
    conductance it introduces while open.

    Parameters
    ----------
    ua_door_extra_w_per_k : float
        Extra heat-transfer conductance [W/K] added while the door is
        open, on top of the normal wall leakage conductance.
    events : List[Tuple[float, float]]
        List of (open_time_s, duration_s) pairs. Each pair schedules
        one door-opening event: the door is OPEN for
        [open_time_s, open_time_s + duration_s) and CLOSED otherwise.
        Phase 1 typically uses a single event; Experiment 3 (repeated
        door opening) will pass several.
    """

    ua_door_extra_w_per_k: float
    events: List[Tuple[float, float]] = field(default_factory=list)

    def add_event(self, open_time_s: float, duration_s: float) -> None:
        """Schedule one more door-opening event."""
        self.events.append((open_time_s, duration_s))

    def is_open(self, t_s: float) -> bool:
        """
        Return True if the door is open at simulated time t_s.

        A door counts as open during [open_time, open_time + duration).
        """
        for open_time_s, duration_s in self.events:
            if open_time_s <= t_s < (open_time_s + duration_s):
                return True
        return False

    def extra_conductance_w_per_k(self, t_s: float) -> float:
        """
        Return the EXTRA thermal conductance [W/K] contributed by the
        door disturbance at time t_s: UA_door_extra if open, 0 if closed.

        This value is added to the wall-leakage conductance inside the
        plant model (models/refrigeration_model.py) to get the total
        heat gain term Q_leak + Q_door.
        """
        return self.ua_door_extra_w_per_k if self.is_open(t_s) else 0.0
