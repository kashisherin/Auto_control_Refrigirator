"""
main_phase1.py

PHASE 1 -- PROJECT FOUNDATION
=============================

A minimal, GUI-free simulation that proves the basic physics is
correct before anything else (controllers, prediction, GUI) is built
on top of it.

What this script does
----------------------
1. Builds the chamber plant model (models/refrigeration_model.py)
   starting at ambient temperature (a "cold start").
2. Applies a FIXED (not yet controlled) compressor cooling power,
   sized so the chamber settles at the setpoint with the door closed.
3. Schedules a single door-opening disturbance
   (models/disturbances.py) partway through the run.
4. Integrates the temperature forward in time, second by second.
5. Saves the results to data/simulation_data.csv.
6. Plots chamber temperature vs. time, with the door-open window
   shaded, and saves the figure to data/phase1_temperature_response.png.

Run it with:
    python main_phase1.py

No controller logic lives in this file -- Stage 1 (ON/OFF) arrives in
Phase 4. This script exists purely to validate the plant + disturbance
model in isolation.
"""

import pandas as pd
import matplotlib.pyplot as plt

from config import parameters as p
from models.refrigeration_model import RefrigerationModel
from models.disturbances import DoorDisturbance


def run_simulation() -> pd.DataFrame:
    """Run the Phase 1 open-loop simulation and return a results table."""

    # --- Build the plant, starting at ambient temperature -------------
    plant = RefrigerationModel(
        temperature_degc=p.T_INITIAL_DEGC,
        ambient_temperature_degc=p.T_AMBIENT_DEGC,
        thermal_capacitance_j_per_k=p.C_THERMAL_J_PER_K,
        ua_leak_w_per_k=p.UA_LEAK_W_PER_K,
    )

    # --- Build the door disturbance schedule ---------------------------
    door = DoorDisturbance(ua_door_extra_w_per_k=p.UA_DOOR_EXTRA_W_PER_K)
    door.add_event(
        open_time_s=p.DOOR_OPEN_AT_SECONDS,
        duration_s=p.DOOR_OPEN_DURATION_SECONDS,
    )

    # --- Time-stepping loop ---------------------------------------------
    n_steps = int(p.SIM_DURATION_SECONDS / p.DT_SECONDS)

    time_log = []
    temperature_log = []
    door_state_log = []
    cooling_power_log = []

    t_s = 0.0
    for _ in range(n_steps + 1):
        # Log the CURRENT state before stepping forward.
        time_log.append(t_s)
        temperature_log.append(plant.temperature_degc)
        door_state_log.append(1 if door.is_open(t_s) else 0)
        cooling_power_log.append(p.Q_COOLING_MAX_W)

        # Advance the plant by one time step.
        extra_conductance = door.extra_conductance_w_per_k(t_s)
        plant.step(
            dt_s=p.DT_SECONDS,
            cooling_power_w=p.Q_COOLING_MAX_W,
            extra_conductance_w_per_k=extra_conductance,
        )
        t_s += p.DT_SECONDS

    results = pd.DataFrame(
        {
            "time_s": time_log,
            "temperature_degc": temperature_log,
            "door_open": door_state_log,
            "cooling_power_w": cooling_power_log,
        }
    )
    return results


def plot_results(results: pd.DataFrame) -> None:
    """Plot chamber temperature vs. time and shade the door-open window."""

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(
        results["time_s"] / 60.0,
        results["temperature_degc"],
        label="Chamber temperature",
        color="tab:blue",
        linewidth=2,
    )
    ax.axhline(
        p.T_SETPOINT_DEGC,
        color="tab:green",
        linestyle="--",
        label=f"Setpoint ({p.T_SETPOINT_DEGC:.1f} \u00b0C)",
    )

    # Shade every interval where the door is open.
    door_open_mask = results["door_open"] == 1
    if door_open_mask.any():
        open_times_min = results.loc[door_open_mask, "time_s"] / 60.0
        ax.axvspan(
            open_times_min.min(),
            open_times_min.max(),
            color="orange",
            alpha=0.25,
            label="Door open",
        )

    ax.set_xlabel("Time (minutes)")
    ax.set_ylabel("Temperature (\u00b0C)")
    ax.set_title("Phase 1: Open-loop chamber temperature response")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig("data/phase1_temperature_response.png", dpi=150)
    print("Saved plot to data/phase1_temperature_response.png")
    plt.show()


def main():
    results = run_simulation()

    # Save the raw data for later phases (metrics, comparison plots).
    results.to_csv("data/simulation_data.csv", index=False)
    print("Saved data to data/simulation_data.csv")

    # Quick sanity-check numbers printed to the console.
    settled = results[results["time_s"] < p.DOOR_OPEN_AT_SECONDS]
    peak_during_disturbance = results[
        (results["time_s"] >= p.DOOR_OPEN_AT_SECONDS)
        & (results["time_s"] <= p.DOOR_OPEN_AT_SECONDS + 600)
    ]["temperature_degc"].max()

    print("\n--- Phase 1 sanity check ---")
    print(f"Initial temperature      : {p.T_INITIAL_DEGC:.2f} degC")
    print(f"Setpoint                 : {p.T_SETPOINT_DEGC:.2f} degC")
    print(f"Temperature just before door opens : "
          f"{settled['temperature_degc'].iloc[-1]:.2f} degC")
    print(f"Peak temperature during/after door-opening event : "
          f"{peak_during_disturbance:.2f} degC")

    plot_results(results)


if __name__ == "__main__":
    main()
