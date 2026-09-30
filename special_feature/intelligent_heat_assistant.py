"""
special_feature/intelligent_heat_assistant.py

Intelligent Door Heat-Exchange & Automatic Cooling Assistant (Special Feature).
Orchestrates heat exchange estimation, thermal severity evaluation, alert management,
feedforward cooling compensation, and event logging as an independent modular layer.
"""

from typing import Dict, Any
from special_feature.heat_exchange_estimator import HeatExchangeEstimator
from special_feature.thermal_severity import ThermalSeverityEvaluator
from special_feature.alert_manager import AlertManager
from special_feature.cooling_compensation import CoolingCompensationLayer
from special_feature.event_logger import IntelligentEventLogger


class IntelligentHeatAssistant:
    """
    Intelligent layer sitting on top of main simulation and feedback controller.
    """

    def __init__(self):
        self.estimator = HeatExchangeEstimator()
        self.severity_evaluator = ThermalSeverityEvaluator()
        self.alert_manager = AlertManager()
        self.compensation_layer = CoolingCompensationLayer()
        self.event_logger = IntelligentEventLogger()

        self.door_open_duration_s = 0.0

    def process_step(
        self,
        inside_temp_degc: float,
        ambient_temp_degc: float,
        setpoint_degc: float,
        door_is_open: bool,
        current_cooling_power_w: float,
        dt_s: float,
        sim_time_s: float,
    ) -> Dict[str, Any]:
        """
        Process single simulation step and return intelligent feature outputs.
        """
        # 1. Door Open Duration Counter
        if door_is_open:
            self.door_open_duration_s += dt_s
        else:
            self.door_open_duration_s = 0.0

        # 2. Heat Exchange Estimation
        estimate = self.estimator.estimate(
            inside_temp_degc=inside_temp_degc,
            ambient_temp_degc=ambient_temp_degc,
            door_is_open=door_is_open,
            door_open_duration_s=self.door_open_duration_s,
            dt_s=dt_s,
        )

        # 3. Thermal Severity Evaluation
        severity_res = self.severity_evaluator.evaluate(
            inside_temp_degc=inside_temp_degc,
            setpoint_degc=setpoint_degc,
            estimate=estimate,
        )

        # 4. Alert Status
        alert_status = self.alert_manager.process(severity_res)

        # 5. Feedforward Cooling Compensation
        compensation_w = self.compensation_layer.compute_compensation_w(
            estimate=estimate, severity=severity_res, dt_s=dt_s
        )

        # 6. Event & Telemetry Logging
        self.event_logger.process_step(
            time_s=sim_time_s,
            inside_temp_degc=inside_temp_degc,
            ambient_temp_degc=ambient_temp_degc,
            setpoint_degc=setpoint_degc,
            door_is_open=door_is_open,
            door_open_duration_s=self.door_open_duration_s,
            temp_rate_degc_per_s=estimate.temp_rate_degc_per_s,
            q_est_total_w=estimate.q_est_total_w,
            load_category=estimate.heat_load_category,
            severity_level=severity_res.level.value,
            cooling_power_w=current_cooling_power_w + compensation_w,
            alarm_active=alert_status.should_play_sound,
        )

        # 7. Summary Payload
        return {
            "door_status": "OPEN" if door_is_open else "CLOSED",
            "door_open_duration_s": round(self.door_open_duration_s, 1),
            "estimated_heat_exchange_w": estimate.q_est_total_w,
            "q_est_door_w": estimate.q_est_door_w,
            "q_est_leak_w": estimate.q_est_leak_w,
            "thermal_load_category": estimate.heat_load_category,
            "severity_level": severity_res.level.value,
            "severity_score": severity_res.severity_score,
            "display_title": severity_res.display_title,
            "display_message": severity_res.display_message,
            "compensation_w": compensation_w,
            "audio_pattern": alert_status.audio_pattern,
            "alarm_muted": alert_status.is_muted,
            "should_play_sound": alert_status.should_play_sound,
            "recent_events": self.event_logger.events[-15:],
        }

    def reset(self) -> None:
        self.estimator.reset()
        self.severity_evaluator.reset()
        self.compensation_layer.reset()
        self.event_logger.reset()
        self.door_open_duration_s = 0.0
