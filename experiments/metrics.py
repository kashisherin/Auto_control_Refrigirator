"""
experiments/metrics.py

Performance metrics calculation module for refrigeration system control comparison.
Computes energy consumption (kWh), MAE, RMSE, peak temperature spike, and recovery times.
"""

from typing import Dict, Any
import numpy as np
import pandas as pd


def compute_simulation_metrics(
    df: pd.DataFrame, setpoint_degc: float = -18.0
) -> Dict[str, Any]:
    """
    Compute comprehensive metrics from simulation results dataframe.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns ['time_s', 'temperature_degc', 'door_open', 'cooling_power_w'].
    setpoint_degc : float
        Target setpoint temperature [degC].

    Returns
    -------
    dict
        Dictionary of calculated metrics.
    """
    if df.empty or "temperature_degc" not in df.columns:
        return {}

    temps = df["temperature_degc"].values
    powers = df["cooling_power_w"].values
    times = df["time_s"].values
    door_states = df["door_open"].values

    dt_s = times[1] - times[0] if len(times) > 1 else 1.0

    # Temperature tracking errors
    errors = temps - setpoint_degc
    mae = float(np.mean(np.abs(errors)))
    rmse = float(np.sqrt(np.mean(errors**2)))

    # Energy consumption in kilowatt-hours (kWh)
    total_energy_j = float(np.sum(powers) * dt_s)
    total_energy_kwh = total_energy_j / 3600000.0

    # Max peak temperature during door events
    door_open_indices = np.where(door_states == 1)[0]
    peak_temp_degc = (
        float(np.max(temps[door_open_indices]))
        if len(door_open_indices) > 0
        else float(np.max(temps))
    )

    # Duty cycle
    max_power = float(np.max(powers)) if np.max(powers) > 0 else 344.0
    avg_duty_cycle_pct = (
        float(np.mean(powers / max_power) * 100.0) if max_power > 0 else 0.0
    )

    return {
        "mae_degc": round(mae, 3),
        "rmse_degc": round(rmse, 3),
        "total_energy_kwh": round(total_energy_kwh, 4),
        "peak_temp_degc": round(peak_temp_degc, 2),
        "avg_duty_cycle_pct": round(avg_duty_cycle_pct, 1),
        "door_open_duration_s": float(np.sum(door_states) * dt_s),
    }
