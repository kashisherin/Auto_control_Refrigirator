"""
special_feature module initialization
"""

from special_feature.intelligent_heat_assistant import IntelligentHeatAssistant
from special_feature.heat_exchange_estimator import HeatExchangeEstimator
from special_feature.thermal_severity import ThermalSeverityEvaluator, SeverityLevel
from special_feature.alert_manager import AlertManager
from special_feature.cooling_compensation import CoolingCompensationLayer
from special_feature.event_logger import IntelligentEventLogger

__all__ = [
    "IntelligentHeatAssistant",
    "HeatExchangeEstimator",
    "ThermalSeverityEvaluator",
    "SeverityLevel",
    "AlertManager",
    "CoolingCompensationLayer",
    "IntelligentEventLogger",
]
