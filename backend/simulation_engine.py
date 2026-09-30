"""
backend/simulation_engine.py

Core simulation engine for refrigeration control system.
Integrates physics model, disturbances, controllers, state management,
Special Feature Intelligent Heat Assistant, and Auto Smart Energy Optimizer algorithm selection.
"""

from typing import Dict, Any, List
import pandas as pd
from config import parameters as p
from models.refrigeration_model import RefrigerationModel
from models.disturbances import DoorDisturbance
from controllers.onoff import OnOffController
from controllers.pid import PIDController
from controllers.adaptive_pid import AdaptivePIDController
from controllers.predictive_controller import PredictiveController
from experiments.metrics import compute_simulation_metrics
from special_feature.intelligent_heat_assistant import IntelligentHeatAssistant


class SimulationEngine:
    """
    Simulation Engine running physical refrigeration plant, controllers,
    disturbance logic, Intelligent Heat Assistant, and Auto Smart Energy Optimizer.
    """

    def __init__(self):
        self.intelligent_assistant = IntelligentHeatAssistant()
        self.reset()

    def reset(
        self,
        t_initial_degc: float = p.T_INITIAL_DEGC,
        t_setpoint_degc: float = p.T_SETPOINT_DEGC,
        t_ambient_degc: float = p.T_AMBIENT_DEGC,
        controller_type: str = "auto",
    ) -> None:
        """Reset simulation state and reinitialize controllers."""
        self.t_s = 0.0
        self.setpoint_degc = t_setpoint_degc
        self.ambient_degc = t_ambient_degc
        self.controller_type = controller_type.lower()
        self.manual_door_open = False
        self.q_cooling_max_w = p.Q_COOLING_MAX_W
        self.active_auto_algorithm = "pid"

        # Plant model
        self.plant = RefrigerationModel(
            temperature_degc=t_initial_degc,
            ambient_temperature_degc=self.ambient_degc,
            thermal_capacitance_j_per_k=p.C_THERMAL_J_PER_K,
            ua_leak_w_per_k=p.UA_LEAK_W_PER_K,
        )

        # Scheduled door disturbance
        self.door_disturbance = DoorDisturbance(
            ua_door_extra_w_per_k=p.UA_DOOR_EXTRA_W_PER_K
        )
        self.door_disturbance.add_event(
            open_time_s=p.DOOR_OPEN_AT_SECONDS,
            duration_s=p.DOOR_OPEN_DURATION_SECONDS,
        )

        # Intelligent Heat Assistant Layer reset
        self.intelligent_assistant.reset()

        # Controllers initialization
        self.controllers = {
            "on_off": OnOffController(
                q_cooling_max_w=self.q_cooling_max_w, hysteresis_degc=1.0
            ),
            "pid": PIDController(
                q_cooling_max_w=self.q_cooling_max_w, kp=12.0, ki=0.05, kd=80.0
            ),
            "adaptive_pid": AdaptivePIDController(
                q_cooling_max_w=self.q_cooling_max_w
            ),
            "predictive": PredictiveController(
                q_cooling_max_w=self.q_cooling_max_w,
                ua_leak_w_per_k=p.UA_LEAK_W_PER_K,
                thermal_capacitance_j_per_k=p.C_THERMAL_J_PER_K,
                ambient_temp_degc=self.ambient_degc,
            ),
        }

        # Telemetry history logs
        self.history = {
            "time_s": [],
            "temperature_degc": [],
            "setpoint_degc": [],
            "door_open": [],
            "cooling_power_w": [],
            "q_leak_w": [],
            "q_door_w": [],
        }

        self.last_intelligent_state = self.intelligent_assistant.process_step(
            inside_temp_degc=t_initial_degc,
            ambient_temp_degc=t_ambient_degc,
            setpoint_degc=t_setpoint_degc,
            door_is_open=False,
            current_cooling_power_w=0.0,
            dt_s=0.0,
            sim_time_s=0.0,
        )
        self._record_state(0.0, 0.0, 0.0)

    def set_controller(self, controller_type: str) -> None:
        """Switch controller on the fly."""
        if controller_type.lower() in [
            "auto",
            "open_loop",
            "on_off",
            "pid",
            "adaptive_pid",
            "predictive",
        ]:
            self.controller_type = controller_type.lower()
            if self.controller_type in self.controllers:
                self.controllers[self.controller_type].reset()

    def toggle_door(self) -> bool:
        """Toggle manual door open/close state interactively from UI."""
        self.manual_door_open = not self.manual_door_open
        return self.manual_door_open

    def set_door_state(self, is_open: bool) -> None:
        """Explicitly set door state."""
        self.manual_door_open = is_open

    def update_parameters(
        self,
        setpoint_degc: float = None,
        ambient_degc: float = None,
        ua_door_extra_w_per_k: float = None,
    ) -> None:
        """Update live operating parameters."""
        if setpoint_degc is not None:
            self.setpoint_degc = setpoint_degc
        if ambient_degc is not None:
            self.ambient_degc = ambient_degc
            self.plant.ambient_temperature_degc = ambient_degc
        if ua_door_extra_w_per_k is not None:
            self.door_disturbance.ua_door_extra_w_per_k = ua_door_extra_w_per_k

    def step(self, dt_s: float = p.DT_SECONDS) -> Dict[str, Any]:
        """
        Advance physics simulation by one time step dt_s.
        """
        # Determine total door status (scheduled OR manual override)
        scheduled_open = self.door_disturbance.is_open(self.t_s)
        door_is_open = scheduled_open or self.manual_door_open

        extra_conductance = (
            self.door_disturbance.ua_door_extra_w_per_k if door_is_open else 0.0
        )

        # Determine effective controller strategy (AUTO Smart Energy Optimizer vs Manual)
        effective_controller = self.controller_type
        if self.controller_type == "auto":
            # Smart Energy Optimizer: Auto-switch algorithm based on heat load severity
            if door_is_open or self.plant.temperature_degc > (self.setpoint_degc + 2.0):
                # High disturbance -> Auto-select Predictive MPC for energy-optimal transient suppression
                effective_controller = "predictive"
                self.active_auto_algorithm = "predictive (Auto - Disturbance Suppressor)"
            else:
                # Stable conditions -> Auto-select PID Energy Saver for minimal kWh consumption
                effective_controller = "pid"
                self.active_auto_algorithm = "pid (Auto - Energy Saver)"

        # 1. Compute Feedback Controller Output Command (0 to Q_cooling_max_w)
        if effective_controller == "open_loop":
            u_feedback_w = self.q_cooling_max_w
        elif effective_controller in self.controllers:
            ctrl = self.controllers[effective_controller]
            if effective_controller == "predictive":
                upcoming = self.door_disturbance.is_open(self.t_s + 60.0)
                u_feedback_w = ctrl.compute_cooling_power(
                    self.plant.temperature_degc,
                    self.setpoint_degc,
                    dt_s,
                    door_is_open,
                    upcoming_door_open=upcoming,
                )
            else:
                u_feedback_w = ctrl.compute_cooling_power(
                    self.plant.temperature_degc,
                    self.setpoint_degc,
                    dt_s,
                    door_is_open,
                )
        else:
            u_feedback_w = self.q_cooling_max_w

        # Authoritative Cooling Power (strictly clamped to [0, Q_cooling_max_w])
        total_cooling_power_w = min(
            self.q_cooling_max_w, max(0.0, u_feedback_w)
        )

        # 2. Authoritative Heat Flux Terms
        q_leak_w = self.plant.ua_leak_w_per_k * (
            self.plant.ambient_temperature_degc - self.plant.temperature_degc
        )
        q_door_w = extra_conductance * (
            self.plant.ambient_temperature_degc - self.plant.temperature_degc
        )
        q_in_w = q_leak_w + q_door_w
        q_net_w = q_in_w - total_cooling_power_w
        expected_dt_dt = q_net_w / self.plant.thermal_capacitance_j_per_k

        # 3. Process Intelligent Feature Layer
        intel_state = self.intelligent_assistant.process_step(
            inside_temp_degc=self.plant.temperature_degc,
            ambient_temp_degc=self.plant.ambient_temperature_degc,
            setpoint_degc=self.setpoint_degc,
            door_is_open=door_is_open,
            current_cooling_power_w=total_cooling_power_w,
            dt_s=dt_s,
            sim_time_s=self.t_s,
        )
        self.last_intelligent_state = intel_state

        # 4. Step thermal plant forward with exact cooling power
        t_prev = self.plant.temperature_degc
        self.plant.step(
            dt_s=dt_s,
            cooling_power_w=total_cooling_power_w,
            extra_conductance_w_per_k=extra_conductance,
        )
        t_next = self.plant.temperature_degc

        # Assert physical consistency: sign of dT/dt MUST match sign of Q_net
        actual_dt_dt = (t_next - t_prev) / dt_s if dt_s > 0 else 0.0
        if abs(q_net_w) > 1e-4:
            if q_net_w > 0:
                assert actual_dt_dt >= -1e-7, f"Physical Violation: Q_net > 0 ({q_net_w:.2f} W) but temperature decreased! dT/dt = {actual_dt_dt:.6f}"
            elif q_net_w < 0:
                assert actual_dt_dt <= 1e-7, f"Physical Violation: Q_net < 0 ({q_net_w:.2f} W) but temperature increased! dT/dt = {actual_dt_dt:.6f}"

        self.t_s += dt_s
        self._record_state(total_cooling_power_w, q_leak_w, q_door_w, door_is_open)

        return self.get_current_state()

    def _record_state(
        self,
        cooling_power_w: float,
        q_leak_w: float,
        q_door_w: float,
        door_open: bool = False,
    ) -> None:
        self.history["time_s"].append(round(self.t_s, 1))
        self.history["temperature_degc"].append(round(self.plant.temperature_degc, 2))
        self.history["setpoint_degc"].append(round(self.setpoint_degc, 2))
        self.history["door_open"].append(1 if door_open else 0)
        self.history["cooling_power_w"].append(round(cooling_power_w, 1))
        self.history["q_leak_w"].append(round(q_leak_w, 1))
        self.history["q_door_w"].append(round(q_door_w, 1))

    def get_current_state(self) -> Dict[str, Any]:
        """Get latest real-time telemetry frame for UI rendering."""
        door_open = (
            self.manual_door_open or self.door_disturbance.is_open(self.t_s)
        )
        last_power = (
            self.history["cooling_power_w"][-1]
            if self.history["cooling_power_w"]
            else 0.0
        )
        last_q_leak = (
            self.history["q_leak_w"][-1] if self.history["q_leak_w"] else 0.0
        )
        last_q_door = (
            self.history["q_door_w"][-1] if self.history["q_door_w"] else 0.0
        )

        q_in_w = last_q_leak + last_q_door
        q_net_w = q_in_w - last_power
        dt_dt = q_net_w / p.C_THERMAL_J_PER_K

        return {
            "time_s": round(self.t_s, 1),
            "time_min": round(self.t_s / 60.0, 2),
            "temperature_degc": round(self.plant.temperature_degc, 2),
            "setpoint_degc": round(self.setpoint_degc, 2),
            "ambient_degc": round(self.ambient_degc, 2),
            "door_open": door_open,
            "cooling_power_w": round(last_power, 1),
            "q_leak_w": round(last_q_leak, 1),
            "q_door_w": round(last_q_door, 1),
            "q_in_w": round(q_in_w, 1),
            "q_net_w": round(q_net_w, 1),
            "dt_dt_degc_per_s": round(dt_dt, 5),
            "temp_error_degc": round(self.plant.temperature_degc - self.setpoint_degc, 2),
            "duty_cycle_pct": round((last_power / self.q_cooling_max_w) * 100.0, 1),
            "controller_type": self.controller_type,
            "active_auto_algorithm": self.active_auto_algorithm,
            "intelligent_feature": self.last_intelligent_state,
        }

    def run_full_simulation(
        self, duration_s: float = p.SIM_DURATION_SECONDS, dt_s: float = p.DT_SECONDS
    ) -> pd.DataFrame:
        """Run complete simulation run for analysis and graphing."""
        self.reset(controller_type=self.controller_type)
        n_steps = int(duration_s / dt_s)
        for _ in range(n_steps):
            self.step(dt_s=dt_s)

        return pd.DataFrame(self.history)

    def get_metrics(self) -> Dict[str, Any]:
        """Compute metrics for current run."""
        df = pd.DataFrame(self.history)
        return compute_simulation_metrics(df, setpoint_degc=self.setpoint_degc)
